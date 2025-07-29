#!/bin/bash
# RINEX解析器使用示例脚本
# 使用方法: ./run_example.sh

echo "=== RINEX数据解析器使用示例 ==="
echo ""

# 检查Python环境
echo "1. 检查Python环境..."
python --version
if [ $? -ne 0 ]; then
    echo "错误：未找到Python环境，请先安装Python 3.6+"
    exit 1
fi
echo ""

# 检查输入文件
echo "2. 检查输入数据文件..."
if [ ! -f "all.log" ]; then
    echo "错误：未找到输入文件 all.log"
    exit 1
fi
echo "输入文件检查完成"
echo ""

# 创建输出目录
echo "3. 创建输出目录..."
mkdir -p output
echo "输出目录准备完成"
echo ""

# 处理流动站数据
echo "4. 处理流动站数据..."
echo "运行命令: python scripts/RINEX_Multi_Rover_OBS_Original.py all.log output/rover_obs.25O"
python scripts/RINEX_Multi_Rover_OBS_Original.py all.log output/rover_obs.25O
if [ $? -eq 0 ]; then
    echo "✓ 流动站数据处理完成"
else
    echo "✗ 流动站数据处理失败"
fi
echo ""

# 处理基站数据
echo "5. 处理基站数据..."
echo "运行命令: python scripts/RINEX_Multi_Base_OBS_Original.py all.log output/base_obs.25O"
python scripts/RINEX_Multi_Base_OBS_Original.py all.log output/base_obs.25O
if [ $? -eq 0 ]; then
    echo "✓ 基站数据处理完成"
else
    echo "✗ 基站数据处理失败"
fi
echo ""

# 显示结果
echo "6. 处理结果："
echo "输出文件列表："
ls -la output/
echo ""

echo "=== 处理完成 ==="
echo "生成的RINEX文件位于 output/ 目录中"
echo "请查看 README.md 获取详细说明"
