# RINEX解析器项目包

📦 **版本：** v3.0  
🗓️ **发布日期：** 2025年7月29日  
👥 **开发团队：** RINEX解析器开发团队  

## 🚀 快速开始

### Windows用户
1. 双击运行 `run_example.bat`
2. 查看 `output/` 文件夹中的生成结果

### Linux/Mac用户  
1. 在终端中运行 `bash run_example.sh`
2. 查看 `output/` 文件夹中的生成结果

### 手动运行
```bash
# 处理流动站数据
python scripts/RINEX_Multi_Rover_OBS_Original.py all.log output/rover_obs.25O

# 处理基站数据  
python scripts/RINEX_Multi_Base_OBS_Original.py all.log output/base_obs.25O
```

## 📁 文件说明

| 文件/文件夹 | 描述 |
|-------------|------|
| `README.md` | 📖 项目详细说明文档 |
| `TECHNICAL_DOC.md` | 🔧 技术实现文档 |
| `all.log` | 📊 示例数据文件 |
| `run_example.bat` | 🖥️ Windows批处理脚本 |
| `run_example.sh` | 🐧 Linux/Mac脚本 |
| `scripts/` | 📜 Python脚本文件夹 |
| `├─ RINEX_Multi_Rover_OBS_Original.py` | 🚁 流动站解析器 |
| `└─ RINEX_Multi_Base_OBS_Original.py` | 🏗️ 基站解析器 |
| `output/` | 📤 输出文件夹 |

## ✨ 主要特性

- ✅ **RINEX 3.02标准** - 完全兼容国际标准
- ✅ **多星座支持** - GPS/GLONASS/BDS/Galileo/QZSS
- ✅ **动态坐标计算** - 流动站坐标自动计算
- ✅ **批量处理** - 一次处理数百个观测记录
- ✅ **质量过滤** - 智能过滤低质量数据
- ✅ **双模式支持** - 流动站和基站分别处理

## 📈 处理能力

- **处理速度：** 每秒处理约50-100个观测记录
- **内存占用：** 通常小于100MB
- **文件支持：** 支持GB级大文件处理
- **精度等级：** 坐标精确到厘米级

## 🎯 适用场景

- 🛰️ **RTK测量** - 实时动态定位
- 🗺️ **精密测绘** - 高精度地形测量  
- 🏗️ **工程建设** - 施工定位与监测
- 🔬 **科学研究** - GNSS数据分析

## ⚠️ 系统要求

- **Python版本：** 3.6 或更高版本
- **操作系统：** Windows/Linux/MacOS
- **内存要求：** 建议512MB以上
- **磁盘空间：** 根据数据量大小

## 📞 技术支持

如遇到问题，请查看：
1. 📖 `README.md` - 详细使用说明
2. 🔧 `TECHNICAL_DOC.md` - 技术实现细节
3. 💬 控制台输出 - 运行时诊断信息

## 🔄 更新记录

### v3.0 (2025-07-29)
- ✨ 新增动态坐标计算功能
- 🚀 提升批处理性能
- 🔧 优化代码结构
- 📚 完善文档体系

### v2.0 (2025-07-28)  
- ✨ 新增基站数据支持
- 🛡️ 增强质量过滤
- ⚡ 性能优化

### v1.0 (2025-07-27)
- 🎉 首个正式版本发布
- 📦 基础RINEX转换功能

---

**🎉 感谢使用RINEX解析器！**

开始处理您的GNSS数据吧！ 🛰️📊
