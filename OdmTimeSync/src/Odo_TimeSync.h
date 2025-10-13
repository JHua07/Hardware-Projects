#pragma once
#include <atomic>
#include <chrono>
#include <memory>
#include <string>
#include <thread>

#include <gpiod.hpp>

namespace h2o {

class Odo_TimeSync {
public:
	Odo_TimeSync(std::string uart_device, std::string gpio_pin);
	~Odo_TimeSync();

	Odo_TimeSync(const Odo_TimeSync&) = delete;
	Odo_TimeSync& operator=(const Odo_TimeSync&) = delete;

	bool start();
	void stop();

private:
	struct ParsedGpio {
		std::string chip_name;
		unsigned int line_number;
	};

	bool init_uart();
	bool init_gpio(const ParsedGpio& parsed_gpio);
	void monitor_loop();
	void send_time_via_serial(const std::string& payload);
	static ParsedGpio parse_gpio(const std::string& gpio_pin);

	std::string uart_device_;
	std::string gpio_pin_;
	int uart_fd_;
	std::unique_ptr<gpiod::chip> gpio_chip_;
	gpiod::line gpio_line_;
	std::atomic<bool> running_;
	std::thread monitor_thread_;
};
}