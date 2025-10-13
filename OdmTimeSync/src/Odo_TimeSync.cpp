#include "Odo_TimeSync.h"

#include <fcntl.h>
#include <sys/time.h>
#include <termios.h>
#include <unistd.h>

#include <chrono>
#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <cctype>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>

namespace {

constexpr speed_t kBaudRate = B115200;
constexpr auto kThreadSleep = std::chrono::milliseconds(1000);

void configure_serial_port(int fd) {
	termios options{};

    tcflush(fd, TCIOFLUSH); // 清除输入输出缓冲区，防止旧数据干扰
	if (tcgetattr(fd, &options) != 0) {
		throw std::runtime_error("Failed to get UART attributes: " + std::string(std::strerror(errno)));
	}

	cfmakeraw(&options);
	cfsetispeed(&options, kBaudRate);
	cfsetospeed(&options, kBaudRate);

	options.c_cflag |= (CLOCAL | CREAD);
	options.c_cflag &= ~PARENB;
	options.c_cflag &= ~CSTOPB;
	options.c_cflag &= ~CSIZE;
	options.c_cflag |= CS8;

	options.c_cc[VMIN] = 0;
	options.c_cc[VTIME] = 1;

	if (tcsetattr(fd, TCSANOW, &options) != 0) {
		throw std::runtime_error("Failed to set UART attributes: " + std::string(std::strerror(errno)));
	}
}

}  // namespace

namespace h2o {

Odo_TimeSync::Odo_TimeSync(std::string uart_device, std::string gpio_pin)
	: uart_device_(std::move(uart_device)),
	  gpio_pin_(std::move(gpio_pin)),
	  uart_fd_(-1),
	  running_(false) {}

Odo_TimeSync::~Odo_TimeSync() { stop(); }

bool Odo_TimeSync::start() {
	if (running_.load()) {
		return true;
	}

	try {
		if (!init_uart()) {
			return false;
		}
		const auto parsed_gpio = parse_gpio(gpio_pin_);
		if (!init_gpio(parsed_gpio)) {
			stop();
			return false;
		}
	} catch (const std::exception& ex) {
		std::cerr << "Failed to initialize time sync: " << ex.what() << std::endl;
		return false;
	}

	running_.store(true);
	monitor_thread_ = std::thread(&Odo_TimeSync::monitor_loop, this);
	return true;
}

void Odo_TimeSync::stop() {
	const bool was_running = running_.exchange(false);
	if (was_running && monitor_thread_.joinable()) {
		monitor_thread_.join();
	}

	if (gpio_line_ && gpio_line_.is_requested()) {
		gpio_line_.release();
	}

	gpio_chip_.reset();

	if (uart_fd_ >= 0) {
		::close(uart_fd_);
		uart_fd_ = -1;
	}
}

bool Odo_TimeSync::init_uart() {
	uart_fd_ = ::open(uart_device_.c_str(), O_RDWR | O_NOCTTY | O_NDELAY);
	if (uart_fd_ < 0) {
		std::cerr << "Failed to open UART port: " << uart_device_ << ": " << std::strerror(errno) << std::endl;
		return false;
	}

	try {
		configure_serial_port(uart_fd_);
	} catch (const std::exception& ex) {
		std::cerr << ex.what() << std::endl;
		::close(uart_fd_);
		uart_fd_ = -1;
		return false;
	}

	return true;
}

bool Odo_TimeSync::init_gpio(const ParsedGpio& parsed_gpio) {
	try {
		gpio_chip_ = std::make_unique<gpiod::chip>(parsed_gpio.chip_name, gpiod::chip::OPEN_BY_NAME);
		gpio_line_ = gpio_chip_->get_line(parsed_gpio.line_number);

		if (!gpio_line_) {
			throw std::runtime_error("Failed to acquire GPIO line");
		}

		gpiod::line_request request{};
		request.consumer = "Odo_TimeSync_Monitor";
		request.request_type = gpiod::line_request::EVENT_RISING_EDGE;
		request.flags = 0;

		gpio_line_.request(request);
	} catch (const std::exception& ex) {
		std::cerr << "Failed to initialize GPIO line: " << ex.what() << std::endl;
		if (gpio_line_ && gpio_line_.is_requested()) {
			gpio_line_.release();
		}
		gpio_line_ = gpiod::line{};
		gpio_chip_.reset();
		return false;
	}

	std::cout << "Init odometry time sync on " << parsed_gpio.chip_name << " line " << parsed_gpio.line_number << std::endl;
	return true;
}

void Odo_TimeSync::monitor_loop() {
	int signal_num = 0;

	while (running_.load()) {
		auto event_available = gpio_line_.event_wait(kThreadSleep);
		if (!event_available) {
			continue;
		}

		gpiod::line_event event;
		try {
			event = gpio_line_.event_read();
		} catch (const std::exception& ex) {
			std::cerr << "GPIO event read failed: " << ex.what() << std::endl;
			continue;
		}

		if (event.event_type != gpiod::line_event::RISING_EDGE) {
			continue;
		}

		struct timeval tv;
		gettimeofday(&tv, nullptr);
		signal_num++;

		std::ostringstream oss;
		oss << std::fixed << std::setprecision(6)
		    << "signal=" << signal_num
		    << " sec=" << tv.tv_sec
		    << " usec=" << tv.tv_usec
		    << "\r\n";

		send_time_via_serial(oss.str());
	}
}

void Odo_TimeSync::send_time_via_serial(const std::string& payload) {
	if (uart_fd_ < 0) {
		return;
	}

	const auto* data = payload.c_str();
	const auto size = payload.size();
	ssize_t bytes_written = ::write(uart_fd_, data, size);
	if (bytes_written < 0) {
		std::cerr << "Failed to write to UART: " << std::strerror(errno) << std::endl;
	} else if (static_cast<size_t>(bytes_written) != size) {
		std::cerr << "Partial UART write: " << bytes_written << " / " << size << std::endl;
	} else {
		if (tcdrain(uart_fd_) != 0) {
			std::cerr << "UART drain failed: " << std::strerror(errno) << std::endl;
		}
		std::cout << "Sent time: " << payload;
	}
}

Odo_TimeSync::ParsedGpio Odo_TimeSync::parse_gpio(const std::string& gpio_pin) {
	constexpr int kLinesPerBank = 8;
	if (gpio_pin.size() != 8 || gpio_pin.substr(0, 4) != "GPIO") {
		throw std::invalid_argument("GPIO pin must match format GPIO<chip>_<bank><line>");
	}

	const char chip_char = gpio_pin[4];
	const char separator = gpio_pin[5];
	const char bank_char = gpio_pin[6];
	const char line_char = gpio_pin[7];

	if (!std::isdigit(static_cast<unsigned char>(chip_char)) || separator != '_' ||
	    bank_char < 'A' || bank_char > 'Z' || !std::isdigit(static_cast<unsigned char>(line_char))) {
		throw std::invalid_argument("GPIO pin must match format GPIO<chip>_<bank><line>");
	}

	const int chip_number = chip_char - '0';
	const int bank_number = bank_char - 'A';
	const int line_number = line_char - '0';

	if (bank_number < 0 || line_number < 0 || line_number >= kLinesPerBank) {
		throw std::invalid_argument("GPIO pin contains out-of-range bank or line");
	}

	ParsedGpio parsed{};
	parsed.chip_name = "gpiochip" + std::to_string(chip_number);
	parsed.line_number = static_cast<unsigned int>(bank_number * kLinesPerBank + line_number);
	return parsed;
}

}  // namespace h2o
