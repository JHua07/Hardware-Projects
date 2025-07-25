#ifndef GPS_MODULE_H
#define GPS_MODULE_H
#include <Arduino.h>
#include <ESP32Time.h>

// 改为extern声明
extern volatile bool SafeGuardTripped;
extern volatile bool theTimeSettingProcessIsUnderway;

// 函数声明
void init_GPS_module();
void setup_GPS();
void setDateAndTimeFromGPS(void *parameter);
bool setTheGPSBaudRate(int maxAattemptsToChangeTheBaudRate);
bool TestGPSConnection(int gpsBaud, int timeoutMs = 5000);
void sendBaudRateChangeCommand(int newBaudRate);
bool getGPSFixType(String gpsData);
void ppsHandlerRising();

class GNRMC{
public:
    // 构造函数
    GNRMC() : valid(false), latitude(0.0), lat_dir('N'), longitude(0.0), lon_dir('E'),
              speed(0.0), course(0.0), day(1), month(1), year(2000),
              hour(0), minute(0), second(0), variation(0.0), var_dir('E') {}

    // 成员变量
    bool valid;           // 数据有效性
    float latitude;       // 纬度
    char lat_dir;         // 纬度方向 (N/S)
    float longitude;      // 经度
    char lon_dir;         // 经度方向 (E/W)
    float speed;          // 速度 (节)
    float course;         // 航向 (度)
    int day;              // 日
    int month;            // 月
    int year;             // 年
    int hour;             // 时
    int minute;           // 分
    int second;           // 秒
    float variation;      // 磁偏角
    char var_dir;         // 磁偏角方向

    bool parseGNRMC(String nmeaSentence);
    bool getLocate();

    
    // 获取GPS时间数据的辅助函数
    bool getDateValid(GNRMC &gnrmcData) {
        return gnrmcData.valid && (gnrmcData.year > 2020);
    }

    bool getTimeValid(GNRMC &gnrmcData) {
        return gnrmcData.valid && (gnrmcData.hour < 24) && (gnrmcData.minute < 60) && (gnrmcData.second < 60);
    }

    // 获取具体时间数据的函数 (替代原Ublox库函数)
    uint16_t getYear(GNRMC &gnrmcData) {
        return gnrmcData.year;
    }

    uint8_t getMonth(GNRMC &gnrmcData) {
        return gnrmcData.month;
    }

    uint8_t getDay(GNRMC &gnrmcData) {
        return gnrmcData.day;
    }

    uint8_t getHour(GNRMC &gnrmcData) {
        return gnrmcData.hour;
    }

    uint8_t getMinute(GNRMC &gnrmcData) {
        return gnrmcData.minute;
    }

    uint8_t getSecond(GNRMC &gnrmcData) {
        return gnrmcData.second;
    }

    // 获取位置数据的函数
    float getLatitude(GNRMC &gnrmcData) {
        return gnrmcData.latitude;
    }

    float getLongitude(GNRMC &gnrmcData) {
        return gnrmcData.longitude;
    }

    float getSpeed(GNRMC &gnrmcData) {
        return gnrmcData.speed;  // 节
    }

    float getCourse(GNRMC &gnrmcData) {
        return gnrmcData.course;  // 度
    }

    // GPS数据有效性检查
    bool isGPSDataValid(GNRMC &gnrmcData) {
        return gnrmcData.valid;
    }

};


#endif