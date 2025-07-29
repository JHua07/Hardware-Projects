# RINEX 数据解析器包

## 项目概述

本项目提供了一套完整的RINEX 3.02格式数据解析器，专门用于处理Unicore接收机的OBSVMA和OBSVBASEA观测数据。项目包含两个主要解析器：流动站解析器和基站解析器，支持动态坐标计算和批处理功能。

## 功能特性

### ✨ 核心功能
- **RINEX 3.02标准兼容** - 完全符合RINEX 3.02观测数据格式标准
- **多星座支持** - 支持GPS、GLONASS、BDS、Galileo、QZSS等卫星系统
- **批处理能力** - 一次性处理数百个观测记录
- **动态坐标计算** - 流动站自动从BESTNAVXYZA数据计算平均坐标
- **智能数据过滤** - 自动过滤低质量观测数据
- **精确时间转换** - GPS时间到UTC时间的精确转换

### 🎯 技术亮点
- **智能卫星标识** - 根据跟踪状态位自动识别卫星系统和PRN编号
- **质量控制** - 基于载噪比、跟踪状态等多重过滤机制
- **坐标区分** - 流动站使用动态计算坐标，基站使用固定参考坐标
- **精度保证** - 厘米级坐标精度，满足RTK应用需求

## 文件结构

```
RINEX_Parser_Package/
├── README.md                              # 项目说明文档
├── all.log                               # 示例数据文件
├── scripts/                              # 脚本文件夹
│   ├── RINEX_Multi_Rover_OBS_Original.py # 流动站解析器
│   └── RINEX_Multi_Base_OBS_Original.py  # 基站解析器
└── output/                               # 输出文件夹
```

## 脚本说明

### 1. 流动站解析器 (RINEX_Multi_Rover_OBS_Original.py)

**功能描述：**
- 处理OBSVMA观测数据
- 从BESTNAVXYZA记录动态计算流动站坐标
- 生成包含计算坐标的RINEX观测文件

**关键特性：**
- **动态坐标计算** - 基于BESTNAVXYZA数据计算平均坐标
- **坐标精度** - 毫米级精度的坐标计算
- **质量统计** - 显示坐标计算所用的记录数量

**使用方法：**
```bash
python scripts/RINEX_Multi_Rover_OBS_Original.py all.log output/rover_obs.25O
```

### 2. 基站解析器 (RINEX_Multi_Base_OBS_Original.py)

**功能描述：**
- 处理OBSVBASEA观测数据
- 使用预定义的固定参考坐标
- 生成标准基站RINEX观测文件

**关键特性：**
- **固定坐标** - 使用预设的基站参考坐标
- **基站标识** - 明确标识为基站类型
- **同步处理** - 与流动站数据时间同步

**使用方法：**
```bash
python scripts/RINEX_Multi_Base_OBS_Original.py all.log output/base_obs.25O
```

## 技术规格

### 支持的数据格式
- **输入格式** - Unicore OBSVMA/OBSVBASEA ASCII消息
- **输出格式** - RINEX 3.02观测数据文件
- **坐标系统** - WGS84大地坐标系
- **时间系统** - GPS时间，自动转换为UTC

### 卫星系统支持
| 系统 | 前缀 | PRN范围 | 频点支持 |
|------|------|---------|----------|
| GPS | G | 01-32 | L1C/A, L2P(Y) |
| GLONASS | R | 01-24 | G1, G2 |
| BDS | C | 01-63 | B1I, B2I, B3I |
| Galileo | E | 01-36 | E1, E5a |
| QZSS | J | 01-10 | L1C/A, L2C |

### 数据质量过滤标准
- **载噪比阈值** - CN0 ≥ 25.0 dB-Hz
- **跟踪状态** - 伪距和载波相位有效标志位检查
- **数据完整性** - 必需观测值完整性验证

## 使用示例

### 基本使用流程

1. **准备数据文件**
   ```bash
   # 确保数据文件包含OBSVMA、OBSVBASEA和BESTNAVXYZA记录
   ls -la all.log
   ```

2. **处理流动站数据**
   ```bash
   python scripts/RINEX_Multi_Rover_OBS_Original.py all.log output/rover_obs.25O
   ```

3. **处理基站数据**
   ```bash
   python scripts/RINEX_Multi_Base_OBS_Original.py all.log output/base_obs.25O
   ```

### 输出示例

**流动站处理输出：**
```
Converting all.log to RINEX 3.02 format...
找到 622 个BESTNAVXYZA记录
计算得到流动站平均坐标:
  X: -1326002.8464m
  Y: 5323044.2529m
  Z: 3243889.2835m
  (基于 622 个BESTNAVXYZA记录)
找到 622 个OBSVMA记录
正在处理第 1/622 个OBSVMA记录...
成功解析了 60 个卫星观测数据
过滤了 11 个低质量观测数据
...
成功解析了 622 个历元的数据
成功创建RINEX文件: output/rover_obs.25O
包含 622 个历元的观测数据
```

**基站处理输出：**
```
Converting all.log to RINEX 3.02 format...
找到 622 个OBSVBASEA记录
正在处理第 1/622 个OBSVBASEA记录...
成功解析了 58 个卫星观测数据
过滤了 13 个低质量观测数据
...
成功解析了 622 个历元的数据
成功创建RINEX文件: output/base_obs.25O
包含 622 个历元的观测数据
```

## RINEX文件格式示例

### 文件头部格式
```
     3.02           OBSERVATION DATA    M                   RINEX VERSION / TYPE
G = GPS,  R = GLONASS,  E = GALILEO,  C = BDS,  M = MIXED   COMMENT             
UnicoreConvert      Unicore             20250729 100837 UTC PGM / RUN BY / DATE
UnicoreRoof 001                                             MARKER NAME         
GEODETIC                                                    MARKER TYPE         
Unicore-001         Unicore HPL EVT                         OBSERVER / AGENCY   
Unicore#001         GEODETIC            Unicore UB4B0       REC # / TYPE / VERS 
Ant001              ROVER                                   ANT # / TYPE        
 -1326002.8464  5323044.2529  3243889.2835                  APPROX POSITION XYZ 
        0.0000        0.0000        0.0000                  ANTENNA: DELTA H/E/N
G    8 C1C L1C D1C S1C C2W L2W D2W S2W                      SYS / # / OBS TYPES 
R    8 C1C L1C D1C S1C C2C L2C D2C S2C                      SYS / # / OBS TYPES 
C   16 C1I L1I D1I S1I C7I L7I D7I S7I C6I L6I D6I S6I C1Q  SYS / # / OBS TYPES 
       L1Q D1Q S1Q                                          SYS / # / OBS TYPES 
E    8 C1C L1C D1C S1C C7Q L7Q D7Q S7Q                      SYS / # / OBS TYPES 
J    8 C1C L1C D1C S1C C2L L2L D2L S2L                      SYS / # / OBS TYPES 
  2025     5    29     9     1    48.0000000     GPS         TIME OF FIRST OBS    
  2025     5    29     9    12     9.0000000     GPS         TIME OF LAST OBS     
     0                                                      RCV CLOCK OFFS APPL  
                                                            END OF HEADER        
```

### 观测数据格式
```
> 2025 05 29 09 01  48.0000000  0 29
G05  21712605.036   114100483.70898      -2570.827                41.170    21712619.639   88909519.91518      -2003.385                34.040  
G13  20565517.067   108072511.79512      -2815.220                41.350    20565528.455   84212410.65373      -2193.643                33.730  
G15  19709951.021   103576497.55305       -532.398                48.990    19709966.421   80709018.99428       -414.847                44.850  
...
```

## 坐标计算详解

### 流动站坐标计算原理

1. **数据提取** - 从所有BESTNAVXYZA记录中提取坐标信息
2. **质量筛选** - 仅使用NARROW_INT（窄巷整数解）状态的高精度坐标
3. **统计计算** - 对所有有效坐标进行算术平均
4. **精度评估** - 基于样本数量评估坐标可靠性

### 坐标精度指标

| 参数 | 流动站 | 基站 |
|------|--------|------|
| 坐标来源 | BESTNAVXYZA动态计算 | 固定参考坐标 |
| 精度等级 | 厘米级 | 固定值 |
| 更新方式 | 每次运行重新计算 | 预设固定值 |
| 适用场景 | 移动平台定位 | 参考站定位 |

## 系统要求

### 软件环境
- **Python版本** - Python 3.6+
- **依赖库** - 无第三方依赖，仅使用标准库
- **操作系统** - Windows/Linux/MacOS

### 硬件要求
- **内存** - 建议512MB以上可用内存
- **存储** - 足够存储输入和输出文件的磁盘空间
- **处理器** - 现代多核处理器（推荐）

## 故障排除

### 常见问题

**1. 未找到BESTNAVXYZA记录**
```
解决方案：检查输入文件是否包含导航解算数据，或使用默认坐标
影响：流动站将使用预设默认坐标
```

**2. 观测数据解析失败**
```
解决方案：检查数据格式是否为标准Unicore ASCII格式
影响：跳过格式错误的记录，继续处理其他数据
```

**3. 输出文件权限错误**
```
解决方案：确保输出目录具有写入权限
影响：程序无法生成RINEX文件
```

### 调试建议

1. **详细日志** - 运行时注意观察控制台输出的统计信息
2. **数据验证** - 使用RINEX验证工具检查输出文件格式
3. **对比测试** - 与其他RINEX转换工具的结果进行对比验证

## 开发信息

### 版本历史
- **v1.0** - 基础OBSVMA解析功能
- **v2.0** - 增加批处理和质量过滤
- **v3.0** - 添加动态坐标计算和基站支持

### 技术架构
```
数据输入 → 格式解析 → 质量过滤 → 坐标计算 → RINEX生成 → 文件输出
```

### 核心算法
1. **卫星标识算法** - 基于跟踪状态位的系统和PRN识别
2. **坐标计算算法** - BESTNAVXYZA数据统计处理
3. **时间转换算法** - GPS时间到UTC时间的精确转换
4. **质量评估算法** - 多维度观测质量评价

## 联系与支持

如有技术问题或改进建议，请通过以下方式联系：

- **项目仓库** - [GitHub Repository]
- **技术支持** - 提交Issue或Pull Request
- **文档更新** - 欢迎贡献文档改进

---

**最后更新：** 2025年7月29日  
**版本：** v3.0  
**作者：** RINEX解析器开发团队
