#include <Arduino.h>
#include "GPS_Module.h"
#include "ESP32TimeServerKeySettings.h"

GNRMC gnrmcData;
volatile bool ppsFlag = false; // PPS标志，表示PPS信号已接收

void init_GPS_module()
{
    // Initialize the GPS module
    pinMode(GPS_RX_PIN, INPUT);
    pinMode(GPS_TX_PIN, OUTPUT);

    GPS_DEVICE.setRxBufferSize(2048); // 默认256，增加到1024
    GPS_DEVICE.setTxBufferSize(512);  // 发送缓冲区也适当增加

    // 初始化GPS串口 (使用Serial2)
    GPS_DEVICE.begin(GPS_BAUD, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
    GPS_DEVICE.setTimeout(100); // 设置读取超时时间为0.1秒

    // Additional initialization code can go here if needed
    // 中断，上升沿将ppsFlag设置为true
    pinMode(GPS_PPS_PIN, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(GPS_PPS_PIN), ppsHandlerRising, RISING);
    printf(("PPS interrupt attached to PIN " + String(GPS_PPS_PIN) + "\n").c_str());
}

void setup_GPS()
{
    // 尝试设置GPS设备的波特率为预定义的GPSBaud值，最多尝试10次
    if (!setTheGPSBaudRate(10))
    {
        // 如果波特率设置失败，显示错误信息
        printf("Error: Unable to set GPS baud rate to %d\n", GPS_BAUD);
        // 冻结程序，因为无法与GPS设备通信
        while (true)
            ;
    };

    // 等待GPS获取定位信号
    printf("start waiting for GPS Fix.....\n");

    // unsigned long nextCheck = millis() + oneSecond_inMilliseconds;
    // 定义变量存储GPS定位类型
    bool fixType = false;

    // 循环等待GPS获取有效定位信号
    // 设置循环控制变量，当获取到定位信号时退出循环
    bool continueWaitingForAFix = true;
    String receivedData = ""; // 用于存储接收到的GPS数据
    bool readflag = false;
    while (continueWaitingForAFix)
    {
        if(!GPS_DEVICE.available()) // 检查是否有可读数据
        {
            delay(100); // 如果没有数据，稍作延时
            continue; // 继续下一次循环
        }
        int c = GPS_DEVICE.read();
        // printf("%c", c); // 打印接收到的字符到串口调试器
        if(c == '$')
        {
            readflag = true;
        }
        if (readflag)
        {
            receivedData += static_cast<char>(c);
            // 检查是否接收到完整的NMEA语句
            if (c == '\n')
            {
                if(debugIsOn)
                {
                    printf("Received Data: ");
                    printf(receivedData.c_str()); // 打印接收到的字符到串口调试器
                }
                // 验证是否为有效的NMEA格式
                if (receivedData.startsWith("$GNRMC") && receivedData.indexOf('*') > 0)
                {
                    if(debugIsOn)
                    {
                        printf("Starting GPS Fixtype Get  .....  \n");
                    }
                    // 获取GPS定位类型
                    fixType = getGPSFixType(receivedData);
                    printf("GPS Fix Type: %s\n", fixType ? "Valid" : "Invalid");
                    if (fixType)
                    {
                        // 如果获取到有效定位信号，退出循环
                        continueWaitingForAFix = false;
                        printf("GPS Fix acquired!");
                    }
                    else
                    {
                        // 如果没有获取到有效定位信号，继续等待
                        printf("Waiting for GPS Fix...");
                    }
                }
                receivedData = ""; // 重置缓冲区
                readflag = false; // 重置读取标志
            }
        }
    };
}

void setDateAndTimeFromGPS(void *parameter)
{
    // ===============================
    // GPS时间同步任务：后台持续运行的核心时间同步功能
    // ===============================
    // 初始化：第一次启动时的标记和安全阈值设置
    static bool thisIsTheFirstTimeSetBeingMadeAtStartup = true;
    // 安全阈值：确保GPS时间刷新只在新旧时间差异合理（1s）的情况下进行
    const time_t safeguardThresholdHigh = safeguardThresholdInSeconds;
    const time_t safeguardThresholdLow = -1 * safeguardThresholdInSeconds;

    time_t candidateDateAndTime;

    if (debugIsOn)
    {
        printf("Start setDateAndTimeFromGPS task\n");
    }

    ppsFlag = false; // 重置PPS标志

    while (true)
    {
        // 标记时间设置过程开始
        theTimeSettingProcessIsUnderway = true;
        while (!ppsFlag)
        {
            if (debugIsOn)
            {
                printf("Starting GPS time synchronization...\n");
            }
            
            // 开始获取GNRMC的时间数据
            if (gnrmcData.getLocate())
            {
                if (debugIsOn)
                {
                    printf("Get valid GNRMC data\n");
                }
                if (gnrmcData.getDateValid(gnrmcData) && gnrmcData.getTimeValid(gnrmcData))
                {
                    struct tm wt;
                    wt.tm_year = gnrmcData.getYear(gnrmcData);  // tm_year是从1900年开始的
                    wt.tm_mon = gnrmcData.getMonth(gnrmcData);  // tm_mon
                    wt.tm_mday = gnrmcData.getDay(gnrmcData);   // tm_mday
                    wt.tm_hour = gnrmcData.getHour(gnrmcData);  // tm_hour
                    wt.tm_min = gnrmcData.getMinute(gnrmcData); // tm_min
                    wt.tm_sec = gnrmcData.getSecond(gnrmcData); // tm_sec

                    if ((wt.tm_year > 2022) && (wt.tm_mon > 0) && (wt.tm_mon < 13) && (wt.tm_mday > 0) && (wt.tm_mday < 32) && (wt.tm_hour < 24) && (wt.tm_min < 60) && (wt.tm_sec < 61))
                    {
                        // 步骤G：格式化时间数据为系统可用格式
                        wt.tm_year -= 1900;                     // 调整年份（标准时间库格式）
                        wt.tm_mon -= 1;                         // 调整月份（1月=0）
                        wt.tm_hour += 8; 
                        candidateDateAndTime = mktime(&wt) + 1; // 转换为时间戳

                        if (debugIsOn)
                        {
                            String timeStr = "Candidate date and time " + String(wt.tm_year) + " " + String(wt.tm_mon) + " " + String(wt.tm_mday) + " " + String(wt.tm_hour) + " " + String(wt.tm_min) + " " + String(wt.tm_sec) + "\n";
                            printf(timeStr.c_str());
                        }

                        time_t wt = candidateDateAndTime;
                        time_t candidateDateAndTime_t = time(&wt);

                        // 等待PPS引脚复位
                        vTaskDelay(200 / portTICK_PERIOD_MS);

                        // 等待下一次PPS信号
                        ppsFlag = false;
                        while (!ppsFlag)
                            ;

                        // 记录处理开始时间（用于补偿处理延迟）
                        unsigned long pegProcessingAdjustmentStartTime = micros();

                        // 进行安全检查
                        bool SanityCheckPassed;
                        time_t updateDelta;

                        if (thisIsTheFirstTimeSetBeingMadeAtStartup)
                        {
                            // 第一次设置时跳过安全检查
                            SanityCheckPassed = true;
                        }
                        else
                        {
                            // 检查新时间与当前时间的差异是否在合理范围内
                            time_t currentRTC_t = rtc.getEpoch();
                            time_t currentRTCDateAndTime_t = time(&currentRTC_t);
                            updateDelta = currentRTCDateAndTime_t - candidateDateAndTime_t;
                            bool SanityCheckPassed = (((updateDelta >= safeguardThresholdLow) && (updateDelta <= safeguardThresholdHigh)));
                        }

                        // 如果安全检查通过，更新RTC时间
                        if (SanityCheckPassed)
                        {
                            if (xSemaphoreTake(mutex, portMAX_DELAY) == pdTRUE)
                            {
                                // 计算和应用处理延迟补偿
                                unsigned long pegProcessingAdjustmentEndTime = micros();
                                unsigned long ProcessingAdjustment = pegProcessingAdjustmentEndTime - pegProcessingAdjustmentStartTime;

                                // 设置系统实时时钟
                                rtc.setTime((unsigned long)candidateDateAndTime, (int)ProcessingAdjustment);
                                xSemaphoreGive(mutex);

                                if (debugIsOn)
                                {
                                    printf("Date and time set to ");
                                    String ws = rtc.getDateTime(true);
                                    ws.trim();
                                    printf((ws + " (UTC)\n").c_str());
                                };
                                // 重置状态标记
                                SafeGuardTripped = false;
                                theTimeSettingProcessIsUnderway = false;
                                thisIsTheFirstTimeSetBeingMadeAtStartup = false;
                                if(debugIsOn)
                                {
                                    printf("Waiting for next sync period...\n");
                                }

                                // 等待下一个同步周期（30分钟）
                                vTaskDelay(periodicTimeRefreshPeriod / portTICK_PERIOD_MS);
                            }
                            else
                            {
                                // 无法获取互斥锁（可能NTP请求正在进行）
                                if (debugIsOn)
                                {
                                    printf("Could not refresh the time as a NTP request was underway\n");
                                    printf("Will try again\n");
                                }
                            }
                        }
                        else
                        {
                            // 异常处理 - 安全检查失败
                            if (debugIsOn)
                            {
                                String message = "This date and time refresh failed its sanity check with a time delta of " + String(updateDelta) + " seconds";
                                printf(message.c_str());
                                printf("The time was not refreshed.");
                                printf("Date and time are ");
                                String ws = rtc.getDateTime(true);
                                ws.trim();
                                String timeMessage = ws + " (UTC)";
                                printf(timeMessage.c_str());
                                printf("Will try again");
                            };

                            // 设置安全保护标志
                            SafeGuardTripped = true;
                        }
                    }
                }
            }
        }
    }
}

bool setTheGPSBaudRate(int maxAttemptsToChangeTheBaudRate)
{
    // 假设波特率需要设置（true表示需要设置）
    bool buadRateNeedsToBeSet = true;
    // 初始化尝试次数计数器
    int attemptsToChangeTheBaudRate = 0;

    // 循环尝试设置波特率，直到成功或达到最大尝试次数
    while ((buadRateNeedsToBeSet) && (attemptsToChangeTheBaudRate < maxAttemptsToChangeTheBaudRate))
    {
        // 步骤3：显示当前尝试信息（调试模式下）
        if (debugIsOn)
        {
            printf("Attempt %d of %d:\n", attemptsToChangeTheBaudRate + 1, maxAttemptsToChangeTheBaudRate);
        }

        // 步骤4：尝试以目标波特率连接GPS设备
        // 设置GPS设备的波特率
        GPS_DEVICE.begin(GPS_BAUD);
        delay(100); // 等待100毫秒让设备稳定

        // 步骤5：检查GPS设备是否响应
        if (TestGPSConnection(GPS_BAUD, 5000))
        {
            // 步骤5：如果连接成功，标记波特率设置完成
            buadRateNeedsToBeSet = false;
            if (debugIsOn)
            {
                printf(("  Successfully connected at " + String(GPS_BAUD) + " baud\n").c_str());
            }
        }
        else
        {
            // 如果目标波特率失败，尝试9600
            if (debugIsOn)
            {
                printf(("  Could not connect at " + String(GPS_BAUD) + " baud, trying 9600\n").c_str());
            }

            if (TestGPSConnection(9600, 5000))
            {
                // 如果9600连接成功，发送波特率切换命令
                if (debugIsOn)
                {
                    printf(("  Connected at 9600 baud, switching to " + String(GPS_BAUD) + "\n").c_str());
                }

                // 发送NMEA命令切换波特率
                sendBaudRateChangeCommand(GPS_BAUD);
                delay(500); // 等待GPS处理命令

                // 验证切换是否成功
                if (TestGPSConnection(GPS_BAUD, 3000))
                {
                    buadRateNeedsToBeSet = false;
                    if (debugIsOn)
                    {
                        printf(("  Baud rate successfully changed to " + String(GPS_BAUD) + "\n").c_str());
                    }
                }
            }
            else
            {
                if (debugIsOn)
                {
                    printf("  Could not connect at 9600 baud either\n");
                }
            }

            attemptsToChangeTheBaudRate++;
        }
        if (buadRateNeedsToBeSet && attemptsToChangeTheBaudRate < maxAttemptsToChangeTheBaudRate)
        {
            delay(2000); // 重试前等待
        }
    }
    return !buadRateNeedsToBeSet; // 返回是否成功设置波特率
}

bool TestGPSConnection(int gpsbaud, int timeoutMs)
{
    // 设置GPS设备的波特率
    GPS_DEVICE.begin(gpsbaud);
    delay(100); // 等待设备稳定

    unsigned long startTime = millis();
    String receivedData = "";

    // 在指定时间内尝试接收GPS数据
    while (millis() - startTime < timeoutMs)
    {
        if (GPS_DEVICE.available())
        {
            char c = GPS_DEVICE.read();
            receivedData += c;

            // 检查是否接收到完整的NMEA语句
            if (c == '\n')
            {
                if(debugIsOn)
                {
                    printf(receivedData.c_str()); // 打印接收到的字符到串口调试器
                }
                // 验证是否为有效的NMEA格式
                if (receivedData.startsWith("$") && receivedData.indexOf('*') > 0)
                {
                    if (debugIsOn)
                    {
                        printf(("GPS connection successful at " + String(gpsbaud) + " baud").c_str());
                        printf(("Received: " + receivedData).c_str());
                    }
                    return true; // 连接成功
                }
                receivedData = ""; // 重置缓冲区
            }
        }
        delay(10); // 短暂延迟避免过度占用CPU
    }

    return false; // 连接失败
}

void sendBaudRateChangeCommand(int newBaudRate)
{
    // 对于大多数GPS模块，可以使用PMTK命令($PAIR864,0,0,<baudrate>*<checksum>)来更改波特率,第一个0指模式为UART,第二个0指定为UART0
    String command = "$PAIR864,0,0," + String(newBaudRate) + "*";

    // 计算校验和
    int checksum = 0;
    for (int i = 1; i < command.length() - 1; i++)
    {
        checksum ^= command[i];
    }

    command += String(checksum, HEX);
    command += "\r\n";

    GPS_DEVICE.print(command);

    if (debugIsOn)
    {
        printf(("  Sent baud rate change command: " + command).c_str());
    }
}

// 获取GPS定位类型，返回1表示有效定位，0表示无效定位
bool getGPSFixType(String gpsData)
{
    // 解析NMEA语句，使用GNRMC语句
    // GNRMC格式: $GNRMC,时间,状态,纬度,N/S,经度,E/W,速度,航向,日期,磁偏角,E/W,模式*校验和
    // 状态字段在第2个逗号后：A=有效定位，V=无效定位
    int firstComma = gpsData.indexOf(',');
    if (firstComma != -1)
    {
        int statusIndex = gpsData.indexOf(',', firstComma + 1);
        if (statusIndex != -1)
        {
            int nextComma = gpsData.indexOf(',', statusIndex + 1);
            if (nextComma != -1)
            {
                String statusStr = gpsData.substring(statusIndex + 1, nextComma);
                // A = 有效定位(返回1)，V = 无效定位(返回0)
                return (statusStr == "A") ? 1 : 0;
            }
        }
    }
    return 0; // 如果没有获取到定位状态，返回0
}

// 解析GNRMC语句并获取位置信息
bool GNRMC::parseGNRMC(String nmeaSentence)
{
    // 检查是否为GNRMC语句
    if (!nmeaSentence.startsWith("$GNRMC"))
    {
        if(debugIsOn)
        {
            printf("Not GNRMC sentence\n");
        }
        
        return false;
    }
    if (debugIsOn)
    {
        printf("Parsing GNRMC data: %s\n", nmeaSentence.c_str());
    }
    // 清除换行符
    nmeaSentence.trim();

    // 分割NMEA语句
    int fieldIndex = 0;
    int startPos = 0;
    String fields[15]; // GNRMC最多有15个字段

    // 解析所有字段
    for (int i = 0; i < nmeaSentence.length(); i++)
    {
        if (nmeaSentence[i] == ',' || i == nmeaSentence.length() - 1)
        {
            if (i == nmeaSentence.length() - 1)
            {
                fields[fieldIndex] = nmeaSentence.substring(startPos);
            }
            else
            {
                fields[fieldIndex] = nmeaSentence.substring(startPos, i);
            }
            fieldIndex++;
            startPos = i + 1;

            if (fieldIndex >= 15)
                break; // 防止数组越界
        }
    }

    // 检查数据有效性 (字段2)
    if (fields[2] != "A")
    {
        gnrmcData.valid = false;
        return false;
    }

    gnrmcData.valid = true;

    // 解析时间 (字段1: HHMMSS.SSS)
    if (fields[1].length() >= 6)
    {
        gnrmcData.hour = fields[1].substring(0, 2).toInt();
        gnrmcData.minute = fields[1].substring(2, 4).toInt();
        gnrmcData.second = fields[1].substring(4, 6).toInt();
    }

    // 解析纬度 (字段3: DDMM.MMMM)
    if (fields[3].length() > 0)
    {
        float rawLat = fields[3].toFloat();
        int degrees = (int)(rawLat / 100);
        float minutes = rawLat - (degrees * 100);
        gnrmcData.latitude = degrees + (minutes / 60.0);
        gnrmcData.lat_dir = fields[4].length() > 0 ? fields[4][0] : 'N';

        // 如果是南纬，转换为负值
        if (gnrmcData.lat_dir == 'S')
        {
            gnrmcData.latitude = -gnrmcData.latitude;
        }
    }

    // 解析经度 (字段5: DDDMM.MMMM)
    if (fields[5].length() > 0)
    {
        float rawLon = fields[5].toFloat();
        int degrees = (int)(rawLon / 100);
        float minutes = rawLon - (degrees * 100);
        gnrmcData.longitude = degrees + (minutes / 60.0);
        gnrmcData.lon_dir = fields[6].length() > 0 ? fields[6][0] : 'E';

        // 如果是西经，转换为负值
        if (gnrmcData.lon_dir == 'W')
        {
            gnrmcData.longitude = -gnrmcData.longitude;
        }
    }

    // 解析速度 (字段7: 节)
    if (fields[7].length() > 0)
    {
        gnrmcData.speed = fields[7].toFloat();
    }

    // 解析航向 (字段8: 度)
    if (fields[8].length() > 0)
    {
        gnrmcData.course = fields[8].toFloat();
    }

    // 解析日期 (字段9: DDMMYY)
    if (fields[9].length() >= 6)
    {
        gnrmcData.day = fields[9].substring(0, 2).toInt();
        gnrmcData.month = fields[9].substring(2, 4).toInt();
        gnrmcData.year = 2000 + fields[9].substring(4, 6).toInt();
    }

    // 解析磁偏角 (字段10和11)
    if (fields[10].length() > 0)
    {
        gnrmcData.variation = fields[10].toFloat();
        gnrmcData.var_dir = fields[11].length() > 0 ? fields[11][0] : 'E';
    }

    return true;
}

bool GNRMC::getLocate()
{
    unsigned long startTime = millis();
    String nmeaBuffer = "";
    bool readflag = false;
    // 清空GPS串口缓冲区中的旧数据
    while (GPS_DEVICE.available())
    {
        GPS_DEVICE.read();
    }
    
    while(true || (millis() - startTime < 60000)) // 循环直到超时或获取到数据
    {
        if(!GPS_DEVICE.available()) // 检查是否有可读数据
        {
            delay(100); // 如果没有数据，稍作延时
            continue; // 继续下一次循环
        }

        int c = GPS_DEVICE.read();
        if(debugIsOn)
        {
            printf("%c", c); // 打印接收到的字符到串口调试器
        }

        if(c == '$')
        {
            readflag = true;
        }
        if (readflag)
        {
            nmeaBuffer += static_cast<char>(c);
            // 检查是否接收到完整的NMEA语句
            if (c == '\n')
            {
                if(debugIsOn)
                {
                    printf(nmeaBuffer.c_str()); // 打印接收到的字符到串口调试器
                }
                // 验证是否为有效的NMEA格式
                if (nmeaBuffer.startsWith("$GNRMC") && nmeaBuffer.indexOf('*') > 0)
                {
                    if(parseGNRMC(nmeaBuffer))
                    {
                        if(debugIsOn)
                        {
                            printf("GNRMC parsed successfully:");
                            printf(("  Latitude: " + String(gnrmcData.latitude, 6)).c_str());
                            printf(("  Longitude: " + String(gnrmcData.longitude, 6)).c_str());
                            printf(("  Speed: " + String(gnrmcData.speed, 2) + " knots").c_str());
                            printf(("  Course: " + String(gnrmcData.course, 1) + "°").c_str());
                            printf(("  Time: " + String(gnrmcData.hour) + ":" +
                                            String(gnrmcData.minute) + ":" + String(gnrmcData.second)).c_str());
                            printf(("  Date: " + String(gnrmcData.day) + "/" +
                                            String(gnrmcData.month) + "/" + String(gnrmcData.year)).c_str());
                        }
                        return true; // 成功获取数据
                    }
                }
                nmeaBuffer = ""; // 重置缓冲区
                readflag = false; // 重置读取标志
            }
        }
    }
    delay(10); // 短暂延迟避免过度占用CPU
    return false; // 超时或无有效数据
}

void ppsHandlerRising() {
    ppsFlag = true;
}