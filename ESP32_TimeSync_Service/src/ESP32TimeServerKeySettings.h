#ifndef ESP32TIMESERVERKEYSETTINGS_H
#define ESP32TIMESERVERKEYSETTINGS_H

#include <Arduino.h>
#include <WiFi.h>
// #include <ETH.h>
#include <SPI.h>
#include <WiFiUdp.h>
#include <TimeLib.h>
#include <Timezone.h>
#include <ESP32Time.h>
#include <Ethernet.h>

// GPS 硬件配置
#define GPS_RX_PIN 44      // GPS模块RX引脚
#define GPS_TX_PIN 43      // GPS模块TX引脚
#define GPS_PPS_PIN 1     // GPS模块PPS引脚
#define GPS_BAUD 115200      // GPS模块波特率

// NTP 服务器配置
#define NTP_PORT 123       // NTP标准端口
#define NTP_PACKET_SIZE 48 // NTP数据包大小

// GPS设备串口定义
#define GPS_DEVICE Serial1  // 使用Serial作为GPS设备

// Define W5500 pin assignments
#define W5500_CS    14  // Chip Select pin
#define W5500_RST    9  // Reset pin
#define W5500_INT   10  // Interrupt pin
#define W5500_MISO  12  // MISO pin
#define W5500_MOSI  11  // MOSI pin
#define W5500_SCK   13  // Clock pin

// 在头文件中添加静态IP配置
#define STATIC_IP_ADDR    192, 168, 120, 77  // 您的静态IP
#define STATIC_GATEWAY    192, 168, 120, 1   // 网关地址
#define STATIC_SUBNET     255, 255, 255, 0   // 子网掩码
#define STATIC_DNS        192, 168, 120, 1   // DNS服务器

// 或者定义为宏
#define ETHERNET_STATIC_IP    IPAddress(192, 168, 120, 77)
#define ETHERNET_GATEWAY      IPAddress(192, 168, 120, 1)
#define ETHERNET_SUBNET       IPAddress(255, 255, 255, 0)
#define ETHERNET_DNS          IPAddress(192, 168, 120, 1)


extern volatile bool ppsFlag;
extern bool debugIsOn;
extern int SerialMonitorSpeed;

extern TimeChangeRule myDST;
extern TimeChangeRule mySTD;
extern Timezone myTZ;

extern SemaphoreHandle_t mutex;
extern TaskHandle_t taskHandle1;

extern TimeChangeRule *tcr;

extern byte packetBuffer[];

extern ESP32Time rtc;

const unsigned long oneSecond_inMilliseconds = 1000;
const unsigned long oneMinute_inMilliseconds = 60 * oneSecond_inMilliseconds;
const unsigned long thirtyMinutes_inMilliseconds = 30 * oneMinute_inMilliseconds;
const unsigned long fiveMinutes_inMilliseconds = 5 * oneMinute_inMilliseconds;
const long oneSecond_inMicroseconds_L = 1000000;
const double oneSecond_inMicroseconds_D = 1000000.0;

// const unsigned long periodicTimeRefreshPeriod = thirtyMinutes_inMilliseconds;
const unsigned long periodicTimeRefreshPeriod = fiveMinutes_inMilliseconds; // 5分钟周期
const time_t safeguardThresholdInSeconds = 1;


#endif



