#include "Odo_TimeSync.h"

#include <atomic>
#include <chrono>
#include <csignal>
#include <iostream>
#include <thread>

namespace {
	std::atomic<bool> g_keep_running{true};

	void signal_handler(int) {
		g_keep_running.store(false);
	}
}  // namespace

int main(int argc, char** argv) {
	const char* default_uart = "/dev/ttyS0";
	const char* default_gpio = "GPIO3_C1";

	const char* uart_device = (argc > 1) ? argv[1] : default_uart;
	const char* gpio_pin = (argc > 2) ? argv[2] : default_gpio;

	h2o::Odo_TimeSync time_sync(uart_device, gpio_pin);
	if (!time_sync.start()) {
		return 1;
	}

	std::signal(SIGINT, signal_handler);
	std::signal(SIGTERM, signal_handler);
	std::cout << "Time sync running. Press Ctrl+C to stop." << std::endl;

	// Keep the process alive while the monitoring thread runs.
	while (g_keep_running.load()) {
		std::this_thread::sleep_for(std::chrono::milliseconds(200));
	}

	std::cout << "Stopping time sync..." << std::endl;
	time_sync.stop();

	return 0;
}