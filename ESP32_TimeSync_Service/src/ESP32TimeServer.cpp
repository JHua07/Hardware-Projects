#include "ESP32TimeServerKeySettings.h"
#include "GPS_Module.h"
#include <Ethernet.h>

// ESP32Time real time clock 定义
ESP32Time rtc(0);  // 定义rtc对象

// 定义全局变量（只在这个文件中定义一次）
bool debugIsOn = false;  // 根据需要设置默认值
int SerialMonitorSpeed = 115200;

// 定义时区
TimeChangeRule myDST = {"EDT", Second, Sun, Mar, 2, -240};  // 根据需要调整
TimeChangeRule mySTD = {"EST", First, Sun, Nov, 2, -300};
Timezone myTZ(myDST, mySTD);

SemaphoreHandle_t mutex;
TaskHandle_t taskHandle1;
TimeChangeRule *tcr;

EthernetUDP Udp;
byte packetBuffer[48];

// GPS模块相关变量
volatile bool SafeGuardTripped = false;
volatile bool theTimeSettingProcessIsUnderway = false;

// Ethernet variables
bool eth_connected = false;
bool eth_got_IP = false;
String ip = "";
byte mac[] = {0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED};

void turnOffWifiAndBluetooth()
{
    // wifi and bluetooth aren't needed so turn them off
    WiFi.mode(WIFI_OFF);
    btStop();
}

void startAnOngoingTaskToRefreshTheDateAndTimeFromTheGPS()
{
    ///@brief 启动一个持续的任务，以从GPS刷新日期和时间
    ///@param 任务函数指针、任务名称、分配给任务的堆栈内存大小、参数、优先级（越大越高,max25）、任务句柄和核心编号
    xTaskCreatePinnedToCore(
        setDateAndTimeFromGPS,
        "Set Date and Time from GPS",
        3000,
        NULL,
        20, // task priority must be reasonably high or the queues from which the gps data is drawn will not be adequately replenished
        &taskHandle1,
        1 // use core 1 to split the load with updateTheDisplay
    );
};

void setupEthernet()
{
    printf("Setting up Ethernet with static IP...\n");
    
    // 初始化SPI和重置芯片的代码保持不变...
    SPI.begin(W5500_SCK, W5500_MISO, W5500_MOSI, W5500_CS);
    pinMode(W5500_RST, OUTPUT);
    digitalWrite(W5500_RST, LOW);
    delay(100);
    digitalWrite(W5500_RST, HIGH);
    delay(1000);
    Ethernet.init(W5500_CS);

    // 使用头文件中定义的静态IP配置
    IPAddress staticIP = ETHERNET_STATIC_IP;
    IPAddress gateway = ETHERNET_GATEWAY;
    IPAddress subnet = ETHERNET_SUBNET;
    IPAddress dns = ETHERNET_DNS;

    printf("Configuring static IP: %s\n", staticIP.toString().c_str());
    
    // 直接使用静态IP初始化（移除所有DHCP相关代码）
    Ethernet.begin(mac, staticIP, dns, gateway, subnet);
    
    // 其余验证代码保持不变...
    delay(3000);
    
    // 检查以太网硬件状态
    if (Ethernet.hardwareStatus() == EthernetNoHardware) 
    {
        printf("ERROR: Ethernet shield was not found!\n");
        return;
    }

    // 检查以太网连接状态
    if (Ethernet.linkStatus() == LinkOFF) 
    {
        printf("WARNING: Ethernet cable is not connected!\n");
    }

    // 检查以太网是否成功连接
    IPAddress localIP = Ethernet.localIP();
    if (localIP == staticIP) 
    {
        printf("Static IP configured successfully: %s\n", localIP.toString().c_str());
        eth_connected = true;
        eth_got_IP = true;
        ip = localIP.toString();
    }
    else
    {
        printf("ERROR: Static IP configuration failed!\n");
        eth_connected = false;
        eth_got_IP = false;
    }
}

void startUDPServer()
{
    printf("Starting UDP server...");
    
    if (Udp.begin(NTP_PORT))
    {
        printf("UDP server started on port %d\n", NTP_PORT);
    }
    else
    {
        printf("Failed to start UDP server!\n");
    }
}

// 获取系统运行时间的函数
// 返回格式为 "X days HH:MM:SS"
// 例如 "2 12:34:56" 表示2天12小时34分钟56秒
String GetUpTime()
{

  unsigned long ms = millis();

  const int oneSecond = 1000;
  const int oneMinute = oneSecond * 60;
  const int oneHour = oneMinute * 60;
  const int oneDay = oneHour * 24;

  int numberOfDays = ms / oneDay;
  ms = ms - numberOfDays * oneDay;

  int numberOfHours = ms / oneHour;
  ms = ms - numberOfHours * oneHour;

  int numberOfMinutes = ms / oneMinute;
  ms = ms - numberOfMinutes * oneMinute;

  int numberOfSeconds = ms / oneSecond;

  String returnValue = "";

  char buffer[21];

  sprintf(buffer, "%d %02d:%02d:%02d", numberOfDays, numberOfHours, numberOfMinutes, numberOfSeconds);

  returnValue = String(buffer);
  return returnValue;
}

// 将UTC时间转换为本地时间并格式化为日期和时间字符串
void GetAdjustedDateAndTimeStrings(time_t UTC_Time, String &dateString, String &timeString)
{

  // adjust utc time to local time
  time_t now_Local_Time = myTZ.toLocal(UTC_Time, &tcr);

  // format dateLine

  dateString = String(year(now_Local_Time));

  dateString.concat("-");

  if (month(now_Local_Time) < 10)
    dateString.concat("0");

  dateString.concat(String(month(now_Local_Time)));

  dateString.concat("-");

  if (day(now_Local_Time) < 10)
    dateString.concat("0");

  dateString.concat(String(day(now_Local_Time)));

  // format timeLine

  timeString = String(hourFormat12(now_Local_Time) + 4);

  timeString.concat(":");

  if (minute(now_Local_Time) < 10)
    timeString.concat("0");

  timeString.concat(String(minute(now_Local_Time)));

  timeString.concat(":");

  if (second(now_Local_Time) < 10)
    timeString.concat("0");

  timeString.concat(String(second(now_Local_Time)));

  if (isAM(now_Local_Time))
    timeString.concat(" AM ");
  else
    timeString.concat(" PM ");
};

uint64_t getCurrentTimeInNTP64BitFormat()
{
  // 设置NTP时间起点偏移量，NTP时间起点是1900年1月1日，而Unix时间起点是1970年1月1日
  // 两者相差2208988800秒（70年的秒数）
  const uint64_t numberOfSecondsBetween1900and1970 = 2208988800;
  
  // 获取当前RTC时间的秒数和微秒数
  // 如果GPS提供的是本地时间（中国时间），需要减去8小时转换为UTC
  const int UTC_OFFSET_HOURS = 8; // 中国时区是UTC+8
  const int UTC_OFFSET_SECONDS = UTC_OFFSET_HOURS * 3600; // 8小时 = 28800秒
  
  // 如果RTC存储的是本地时间，需要减去8小时得到UTC时间
  uint64_t clockSecondsSinceEpoch = numberOfSecondsBetween1900and1970 + 
                                   (uint64_t)rtc.getEpoch() - UTC_OFFSET_SECONDS;
  
  long clockMicroSeconds = (long)rtc.getMicros();

  // 标准化微秒处理（保持原有逻辑）
  while (clockMicroSeconds > oneSecond_inMicroseconds_L)
  {
    clockSecondsSinceEpoch++;
    clockMicroSeconds -= oneSecond_inMicroseconds_L;
  }

  while (clockMicroSeconds < 0L)
  {
    clockSecondsSinceEpoch--;
    clockMicroSeconds += oneSecond_inMicroseconds_L;
  }

  // 将微秒转换为NTP格式的小数部分
  double clockMicroSeconds_D = (double)clockMicroSeconds * (double)(4294.967296);

  // 组合成64位NTP时间戳
  uint64_t ntpts = ((uint64_t)clockSecondsSinceEpoch << 32) | (uint64_t)(clockMicroSeconds_D);

  return ntpts;
}

// 发送NTP响应包
void sendNTPpacket(IPAddress remoteIP, int remotePort)
{
  // set the receive time to the current time
  // 设置接收时间为当前时间（T2,表示服务器接收到包的时间）
  uint64_t receiveTime_uint64_t = getCurrentTimeInNTP64BitFormat();

  // Initialize values needed to form NTP request

  // LI:闰秒指示符，0表示无闰秒警告、1表示有闰秒警告
  // Version: NTP版本号，4表示NTPv4
  // Mode: 模式，3表示客户端请求，4表示服务器响应
  // LI: 0, Version: 4, Mode: 4 (server)
  // packetBuffer[0] = 0b00100100;
  // LI: 0, Version: 3, Mode: 4 (server)
  // 0 0 | 0 1 1 | 1 0 0 
  packetBuffer[0] = 0b00011100;

  // Stratum, or type of clock（设置为一级时间服务器）
  packetBuffer[1] = 0b00000001;

  // Polling Interval（轮询间隔2^4 = 16秒）
  packetBuffer[2] = 4;

  // Peer Clock Precision 设置时钟精度
  // log2(sec)
  // 0xF6 <--> -10 <--> 0.0009765625 s
  // 0xF7 <--> -9 <--> 0.001953125 s
  // 0xF8 <--> -8 <--> 0.00390625 s
  // 0xF9 <--> -7 <--> 0.0078125 s
  // 0xFA <--> -6 <--> 0.0156250 s
  // 0xFB <--> -5 <--> 0.0312500 s
  packetBuffer[3] = 0xF7;

  // 8 bytes for Root Delay & Root Dispersion（根延迟和根扩散）
  // root delay（根延迟设置为0，表示无延迟）
  packetBuffer[4] = 0;
  packetBuffer[5] = 0;
  packetBuffer[6] = 0;
  packetBuffer[7] = 0;

  // root dispersion（根扩散设置为0，表示无扩散，)
  // 高16位表示根扩散的整数部分，低16位表示根扩散的小数部分
  packetBuffer[8] = 0;
  packetBuffer[9] = 0;
  packetBuffer[10] = 0;
  packetBuffer[11] = 0x50;// 0x50 = 80 (decimal), 约有80微秒的时间不确定性

  // time source (namestring)时间源标识为"GPS"
  packetBuffer[12] = 71; // G
  packetBuffer[13] = 80; // P
  packetBuffer[14] = 83; // S
  packetBuffer[15] = 0;

  // get the current time and write it out as the reference time to bytes 16 to 23 of the response packet
  // 获取当前时间并将其写入响应包的字节16到23作为参考时间
  uint64_t referenceTime_uint64_t = getCurrentTimeInNTP64BitFormat();

  packetBuffer[16] = (int)((referenceTime_uint64_t >> 56) & 0xFF);
  packetBuffer[17] = (int)((referenceTime_uint64_t >> 48) & 0xFF);
  packetBuffer[18] = (int)((referenceTime_uint64_t >> 40) & 0xFF);
  packetBuffer[19] = (int)((referenceTime_uint64_t >> 32) & 0xFF);
  packetBuffer[20] = (int)((referenceTime_uint64_t >> 24) & 0xFF);
  packetBuffer[21] = (int)((referenceTime_uint64_t >> 16) & 0xFF);
  packetBuffer[22] = (int)((referenceTime_uint64_t >> 8) & 0xFF);
  packetBuffer[23] = (int)(referenceTime_uint64_t & 0xFF);

  // copy transmit time from the NTP original request to bytes 24 to 31 of the response packet
  // 将NTP原始请求中的传输时间复制到响应包的字节24到31（这个时间实际就是T1，也就是客户端发送包的时间）
  packetBuffer[24] = packetBuffer[40];
  packetBuffer[25] = packetBuffer[41];
  packetBuffer[26] = packetBuffer[42];
  packetBuffer[27] = packetBuffer[43];
  packetBuffer[28] = packetBuffer[44];
  packetBuffer[29] = packetBuffer[45];
  packetBuffer[30] = packetBuffer[46];
  packetBuffer[31] = packetBuffer[47];

  // write out the receive time (it was set above) to bytes 32 to 39 of the response packet
  // 将接收时间（上面设置的）写入响应包的字节32到39（T2,表示服务器接收到包的时间）
  packetBuffer[32] = (int)((receiveTime_uint64_t >> 56) & 0xFF);
  packetBuffer[33] = (int)((receiveTime_uint64_t >> 48) & 0xFF);
  packetBuffer[34] = (int)((receiveTime_uint64_t >> 40) & 0xFF);
  packetBuffer[35] = (int)((receiveTime_uint64_t >> 32) & 0xFF);
  packetBuffer[36] = (int)((receiveTime_uint64_t >> 24) & 0xFF);
  packetBuffer[37] = (int)((receiveTime_uint64_t >> 16) & 0xFF);
  packetBuffer[38] = (int)((receiveTime_uint64_t >> 8) & 0xFF);
  packetBuffer[39] = (int)(receiveTime_uint64_t & 0xFF);

  // get the current time and write it out as the transmit time to bytes 40 to 47 of the response packet
  // (T3，表示服务器发送包的时间)
  uint64_t transmitTime_uint64_t = getCurrentTimeInNTP64BitFormat();

  packetBuffer[40] = (int)((transmitTime_uint64_t >> 56) & 0xFF);
  packetBuffer[41] = (int)((transmitTime_uint64_t >> 48) & 0xFF);
  packetBuffer[42] = (int)((transmitTime_uint64_t >> 40) & 0xFF);
  packetBuffer[43] = (int)((transmitTime_uint64_t >> 32) & 0xFF);
  packetBuffer[44] = (int)((transmitTime_uint64_t >> 24) & 0xFF);
  packetBuffer[45] = (int)((transmitTime_uint64_t >> 16) & 0xFF);
  packetBuffer[46] = (int)((transmitTime_uint64_t >> 8) & 0xFF);
  packetBuffer[47] = (int)(transmitTime_uint64_t & 0xFF);

  // send the reply
  Udp.beginPacket(remoteIP, remotePort); // 指定IP地址和端口，并开始发送
  Udp.write(packetBuffer, NTP_PACKET_SIZE); // 将NTP响应数据包写入UDP数据包
  Udp.endPacket(); // 结束UDP数据包发送
}

void processNTPRequests()
{
    // ===============================
    // NTP请求处理：响应网络时间同步请求
    // ===============================

    // 记录处理开始时间（用于性能监控）
    unsigned long replyStartTime = micros();

    // 检查是否有UDP数据包到达
    int packetSize = Udp.parsePacket();
    
    // 添加调试信息（仅在有数据包时输出）
    if (packetSize > 0) {
        printf("Received UDP packet: size=%d bytes\n", packetSize);
        printf("From IP: %s, Port: %d\n", Udp.remoteIP().toString().c_str(), Udp.remotePort());
    }

    // 验证是否为有效的NTP请求
    if (packetSize == NTP_PACKET_SIZE) // 标准NTP数据包大小为48字节
    {
        if(debugIsOn)
        {
            printf("Received NTP request packet\n");
        }
        // ===============================
        // NTP请求数据处理
        // ===============================

        // 获取请求来源的IP地址
        IPAddress remoteIP = Udp.remoteIP();

        // 读取NTP请求数据到缓冲区
        Udp.read(packetBuffer, NTP_PACKET_SIZE);

        // ===============================
        // 原子性时间响应
        // ===============================

        // 等待获取互斥锁，确保时间数据一致性
        // 防止在构建响应包时时间被GPS同步任务修改
        if (xSemaphoreTake(mutex, portMAX_DELAY) == pdTRUE)
        {
            // 发送NTP响应包
            sendNTPpacket(remoteIP, Udp.remotePort());

            // 释放互斥锁
            xSemaphoreGive(mutex);
        };

        // ===============================
        // 日志记录
        // ===============================

        // 记录请求日志（调试模式下）
        // 注意：这会轻微影响后续NTP请求的响应时间（约1毫秒）
        // if (debugIsOn)
        // {
        //     String dateLine = "";
        //     String timeLine = "";
        //     GetAdjustedDateAndTimeStrings(rtc.getEpoch(), dateLine, timeLine);
        //     String updatemessage = "Query from " + remoteIP.toString() + " on " + dateLine + " at " + timeLine;
        //     printf("%s\n", updatemessage.c_str());
        // };
        String dateLine = "";
        String timeLine = "";
        GetAdjustedDateAndTimeStrings(rtc.getEpoch(), dateLine, timeLine);
        String updatemessage = "Query from " + remoteIP.toString() + " on " + dateLine + " at " + timeLine;
        printf("%s\n", updatemessage.c_str());
    }
    else
    {
        // ===============================
        // 异常数据包处理
        // ===============================

        // 处理非NTP数据包
        if (packetSize > 0)
        {
            // 丢弃无效数据包
            Udp.flush(); // 清空缓冲区中的无效数据

            // 记录无效请求日志
            if (debugIsOn)
                printf(("Invalid request received on port " + String(NTP_PORT) + ", length =" + String(packetSize)).c_str());
        };
    };
}

void setup()
{
    delay(3000); // 延时3秒，确保系统稳定
    if (debugIsOn)
        printf("ESP32 Time Server starting setup ...\n");

    // 关闭不需要的WiFi和蓝牙功能（节省资源）
    turnOffWifiAndBluetooth();

    printf("GPS Setup underway...\n");

    // 设置GPS模块的引脚
    init_GPS_module();
    printf("GPS module initialized\n");

    // 设置GPS模块定位状态
    setup_GPS();
    printf("GPS module setup complete\n");

    // 时间同步系统初始化

    // 创建互斥锁 避免NTP请求与时间刷新冲突
    mutex = xSemaphoreCreateMutex();

    // 启动GPS时间同步任务（后台任务，持续运行）
    startAnOngoingTaskToRefreshTheDateAndTimeFromTheGPS();

    // 步骤11：等待首次时间设置完成
    while (theTimeSettingProcessIsUnderway)
        delay(10);

    printf("GPS time first setting process complete\n");

    // 设置以太网连接
    setupEthernet();
    printf("Ethernet setup complete\n");
    
    // 步骤14：启动UDP服务器（监听NTP请求）
    startUDPServer();
    printf("UDP server started on port %d\n", NTP_PORT);

    printf("ESP32 Time Server setup complete - listening for NTP requests now\n");
}

void loop()
{
    // printf("ESP32 Time Server loop running...\n");
    // ESP32作为NTP服务器响应时间请求
    processNTPRequests();

}