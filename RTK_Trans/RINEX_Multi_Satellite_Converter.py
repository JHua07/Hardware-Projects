#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多卫星系统RINEX转换脚本
支持GPS、Galileo(GAL)、BDS星历数据的自动识别和转换
"""

import os
import re
import argparse
import sys
from datetime import datetime
from include.RINEX_Rover_NAV_GPS import parse_eph_seg_ascii as parse_gps, convert_to_nav_seg as convert_gps
from include.RINEX_Rover_NAV_GAL import parse_eph_seg_ascii as parse_gal, convert_to_nav_seg as convert_gal
from include.RINEX_Rover_NAV_BDS import parse_eph_seg_ascii as parse_bds, convert_to_nav_seg as convert_bds

class MultiSatelliteConverter:
    """多卫星系统RINEX转换器"""
    
    def __init__(self):
        self.satellite_systems = {
            'GPS': {
                'prefix': '#GPSEPHA',
                'parser': parse_gps,
                'converter': convert_gps,
                'output_suffix': '_gps.nav'
            },
            'GAL': {
                'prefix': '#GALEPHA', 
                'parser': parse_gal,
                'converter': convert_gal,
                'output_suffix': '_gal.nav'
            },
            'BDS': {
                'prefix': '#BDSEPHA',
                'parser': parse_bds,
                'converter': convert_bds,
                'output_suffix': '_bds.nav'
            }
        }
    
    def identify_satellite_types(self, data_text):
        """
        识别数据中包含的卫星系统类型
        :param data_text: 原始星历数据文本
        :return: 包含的卫星系统列表
        """
        found_systems = []
        lines = data_text.strip().split('\n')
        
        for system_name, system_info in self.satellite_systems.items():
            prefix = system_info['prefix']
            for line in lines:
                if line.startswith(prefix):
                    if system_name not in found_systems:
                        found_systems.append(system_name)
                    break
        
        return found_systems
    
    def extract_satellite_data(self, data_text, satellite_type):
        """
        从混合数据中提取特定卫星系统的数据
        :param data_text: 原始星历数据文本
        :param satellite_type: 卫星系统类型 ('GPS', 'GAL', 'BDS')
        :return: 该卫星系统的数据文本
        """
        if satellite_type not in self.satellite_systems:
            return ""
        
        prefix = self.satellite_systems[satellite_type]['prefix']
        lines = data_text.strip().split('\n')
        extracted_lines = []
        
        for line in lines:
            if line.startswith(prefix):
                extracted_lines.append(line)
        
        return '\n'.join(extracted_lines)
    
    def convert_single_system(self, data_text, satellite_type, output_dir, output_prefix=None):
        """
        转换单个卫星系统的数据
        :param data_text: 该卫星系统的数据文本
        :param satellite_type: 卫星系统类型
        :param output_dir: 输出目录
        :param output_prefix: 输出文件前缀
        :return: 转换结果信息
        """
        if satellite_type not in self.satellite_systems:
            return f"不支持的卫星系统: {satellite_type}"
        
        system_info = self.satellite_systems[satellite_type]
        
        try:
            # 解析星历数据
            eph_list = system_info['parser'](data_text)
            
            if not eph_list:
                return f"{satellite_type}: 未找到有效的星历数据"
            
            # 转换为RINEX格式
            rinex_content = system_info['converter'](data_text)
            
            # 生成输出文件名
            if output_prefix is None:
                output_prefix = f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            output_filename = f"{output_prefix}{system_info['output_suffix']}"
            output_path = os.path.join(output_dir, output_filename)
            
            # 保存文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(rinex_content)
            
            satellite_count = len(eph_list)
            return f"{satellite_type}: 成功转换 {satellite_count} 颗卫星的数据 -> {output_path}"
            
        except Exception as e:
            return f"{satellite_type}: 转换失败 - {str(e)}"
    
    def convert_all_systems(self, input_file, output_dir=None, output_prefix=None, create_mixed=False):
        """
        转换所有卫星系统的数据
        :param input_file: 输入文件路径
        :param output_dir: 输出目录，默认为输入文件所在目录
        :param output_prefix: 输出文件前缀，默认为当前时间戳
        :param create_mixed: 是否创建混合导航文件
        :return: 转换结果列表
        """
        # 读取输入文件
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                data_text = f.read()
        except FileNotFoundError:
            return [f"错误: 找不到输入文件 {input_file}"]
        except Exception as e:
            return [f"错误: 读取文件失败 - {str(e)}"]
        
        # 设置输出目录
        if output_dir is None:
            output_dir = os.path.dirname(input_file)
        
        # 如果输出目录为空字符串，使用当前目录
        if not output_dir:
            output_dir = os.getcwd()
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 设置输出文件前缀
        if output_prefix is None:
            output_prefix = f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 识别卫星系统类型
        found_systems = self.identify_satellite_types(data_text)
        
        if not found_systems:
            return ["错误: 未找到任何支持的卫星系统数据"]
        
        results = []
        results.append(f"检测到的卫星系统: {', '.join(found_systems)}")
        results.append("-" * 60)
        
        # 逐个转换各卫星系统
        for system_type in found_systems:
            # 提取该系统的数据
            system_data = self.extract_satellite_data(data_text, system_type)
            
            if system_data:
                # 转换数据
                result = self.convert_single_system(system_data, system_type, output_dir, output_prefix)
                results.append(result)
            else:
                results.append(f"{system_type}: 未找到数据")
        
        # 创建混合导航文件
        if create_mixed:
            results.append("-" * 60)
            mixed_result = self.create_mixed_nav_file(input_file, output_dir, output_prefix)
            results.append(mixed_result)
        
        return results
    
    def show_statistics(self, input_file):
        """
        显示输入文件的统计信息
        :param input_file: 输入文件路径
        :return: 统计信息
        """
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                data_text = f.read()
        except Exception as e:
            return [f"错误: 无法读取文件 - {str(e)}"]
        
        lines = data_text.strip().split('\n')
        stats = []
        stats.append(f"文件: {input_file}")
        stats.append(f"总行数: {len(lines)}")
        stats.append("-" * 40)
        
        # 统计各卫星系统的数据量
        for system_name, system_info in self.satellite_systems.items():
            prefix = system_info['prefix']
            count = sum(1 for line in lines if line.startswith(prefix))
            if count > 0:
                stats.append(f"{system_name}: {count} 条记录")
        
        # 提取时间范围信息
        gps_weeks = []
        for line in lines:
            if any(line.startswith(prefix) for prefix in ['#GPSEPHA', '#GALEPHA', '#BDSEPHA']):
                # 解析头部信息中的GPS周数
                try:
                    parts = line.split(',')
                    if len(parts) >= 5:
                        week = int(parts[4])
                        gps_weeks.append(week)
                except:
                    continue
        
        if gps_weeks:
            stats.append(f"GPS周数范围: {min(gps_weeks)} - {max(gps_weeks)}")
        
        return stats

    def create_mixed_nav_file(self, input_file, output_dir, output_prefix=None):
        """
        创建混合的RINEX导航文件，包含所有卫星系统的数据
        :param input_file: 输入文件路径
        :param output_dir: 输出目录
        :param output_prefix: 输出文件前缀
        :return: 转换结果信息
        """
        try:
            # 读取输入文件
            with open(input_file, 'r', encoding='utf-8') as f:
                data_text = f.read()
            
            # 识别卫星系统类型
            found_systems = self.identify_satellite_types(data_text)
            
            if not found_systems:
                return "错误: 未找到任何支持的卫星系统数据"
            
            # 设置输出文件前缀
            if output_prefix is None:
                output_prefix = f"mixed_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # 创建混合RINEX导航文件头部
            mixed_content = self.create_mixed_rinex_header()
            
            # 收集所有卫星系统的导航数据
            all_nav_entries = []
            
            for system_type in found_systems:
                # 提取该系统的数据
                system_data = self.extract_satellite_data(data_text, system_type)
                
                if system_data:
                    # 使用原始转换函数获取RINEX格式数据
                    system_info = self.satellite_systems[system_type]
                    rinex_content = system_info['converter'](system_data)
                    
                    # 提取导航条目（跳过头部）
                    nav_entries = self.extract_nav_entries_from_rinex(rinex_content, system_type)
                    all_nav_entries.extend(nav_entries)
            
            # 按时间排序所有导航条目
            all_nav_entries.sort(key=lambda x: x['time'])
            
            # 添加所有导航条目到混合文件
            for entry in all_nav_entries:
                mixed_content += entry['content']
            
            # 生成输出文件名
            output_filename = f"{output_prefix}.nav"
            output_path = os.path.join(output_dir, output_filename)
            
            # 保存混合文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(mixed_content)
            
            return f"MIXED: 成功创建混合导航文件，包含 {len(all_nav_entries)} 个导航条目 -> {output_path}"
            
        except Exception as e:
            return f"MIXED: 创建混合文件失败 - {str(e)}"
    
    def extract_nav_entries_from_rinex(self, rinex_content, system_type):
        """
        从RINEX内容中提取导航条目
        :param rinex_content: RINEX格式内容
        :param system_type: 卫星系统类型
        :return: 导航条目列表
        """
        nav_entries = []
        lines = rinex_content.split('\n')
        
        # 跳过头部，找到END OF HEADER
        header_end = 0
        for i, line in enumerate(lines):
            if 'END OF HEADER' in line:
                header_end = i + 1
                break
        
        # 处理导航条目
        i = header_end
        while i < len(lines):
            line = lines[i]
            
            # 检查是否是导航条目的开始行
            if line and len(line) > 0 and line[0] in 'GECR':
                # 提取时间信息用于排序
                try:
                    time_str = line[4:23]  # 时间部分
                    time_obj = datetime.strptime(time_str, '%Y %m %d %H %M %S')
                    
                    # 提取完整的导航条目（通常是8行）
                    entry_lines = []
                    for j in range(8):
                        if i + j < len(lines):
                            entry_lines.append(lines[i + j])
                    
                    nav_entry = {
                        'time': time_obj,
                        'content': '\n'.join(entry_lines) + '\n'
                    }
                    nav_entries.append(nav_entry)
                    
                    i += 8  # 跳过这个条目的所有行
                except:
                    i += 1
            else:
                i += 1
        
        return nav_entries
    
    def create_mixed_rinex_header(self):
        """创建混合RINEX导航文件头部"""
        current_time = datetime.now()
        header = f"     3.02           N: GNSS NAV DATA    M: MIXED            RINEX VERSION / TYPE\n"
        header += f"UnicoreConvert      Unicore             {current_time.strftime('%Y%m%d %H%M%S')} UTC PGM / RUN BY / DATE\n"
        header += f"                                                            LEAP SECONDS        \n"
        header += f"                                                            END OF HEADER       \n"
        return header

    # ...existing code...

def create_argument_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description='多卫星系统RINEX转换工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用示例:
  python %(prog)s NAV.txt                           # 使用默认设置转换
  python %(prog)s NAV.txt -o ./output               # 指定输出目录
  python %(prog)s NAV.txt -o ./output -p rinex_     # 指定输出目录和前缀
  python %(prog)s NAV.txt -s GPS BDS                # 只转换GPS和BDS系统
  python %(prog)s NAV.txt -m                        # 创建混合导航文件
  python %(prog)s NAV.txt -m -v                     # 创建混合文件并显示详细信息
  python %(prog)s -i                                # 交互式模式
  python %(prog)s NAV.txt -v                        # 显示详细信息
  python %(prog)s NAV.txt --stats                   # 只显示统计信息
        ''')
    
    parser.add_argument('input_file', nargs='?', 
                       help='输入的星历数据文件路径')
    
    parser.add_argument('-o', '--output', 
                       help='输出目录路径 (默认为输入文件所在目录)')
    
    parser.add_argument('-p', '--prefix', 
                       help='输出文件前缀 (默认为当前时间戳)')
    
    parser.add_argument('-s', '--systems', nargs='+', 
                       choices=['GPS', 'GAL', 'BDS'],
                       help='指定要转换的卫星系统 (默认转换所有检测到的系统)')
    
    parser.add_argument('-m', '--mixed', action='store_true',
                       help='创建混合导航文件 (包含所有卫星系统)')
    
    parser.add_argument('-i', '--interactive', action='store_true',
                       help='交互式模式')
    
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='显示详细信息')
    
    parser.add_argument('--stats', action='store_true',
                       help='只显示文件统计信息，不进行转换')
    
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    
    return parser

def interactive_mode():
    """交互式模式"""
    print("=" * 60)
    print("多卫星系统RINEX转换工具 - 交互式模式")
    print("支持: GPS, Galileo(GAL), BDS")
    print("=" * 60)
    
    # 创建转换器实例
    converter = MultiSatelliteConverter()
    
    # 获取输入文件
    default_input = r'D:\desktop\RTK_Trans\NAV.txt'
    input_file = input(f"请输入星历数据文件路径 (默认: {default_input}): ").strip()
    if not input_file:
        input_file = default_input
    
    # 检查文件是否存在
    if not os.path.exists(input_file):
        print(f"错误: 文件不存在 - {input_file}")
        return 1
    
    # 获取输出目录
    output_dir = input(f"请输入输出目录 (默认: {os.path.dirname(input_file)}): ").strip()
    if not output_dir:
        output_dir = os.path.dirname(input_file)
    
    # 获取输出前缀
    default_prefix = f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_prefix = input(f"请输入输出文件前缀 (默认: {default_prefix}): ").strip()
    if not output_prefix:
        output_prefix = default_prefix
    
    # 询问是否创建混合文件
    create_mixed = input("是否创建混合导航文件? (y/n): ").strip().lower()
    create_mixed = create_mixed in ['y', 'yes', '是']
    
    # 显示文件统计信息
    print("\n文件统计信息:")
    stats = converter.show_statistics(input_file)
    for stat in stats:
        print(stat)
    
    # 询问是否创建混合导航文件
    mixed_choice = input("是否创建混合导航文件? (y/n): ").strip().lower()
    create_mixed = mixed_choice in ['y', 'yes', '是']
    
    # 询问是否继续转换
    print("\n" + "=" * 40)
    choice = input("是否开始转换? (y/n): ").strip().lower()
    if choice not in ['y', 'yes', '是']:
        print("转换已取消")
        return 0
    
    # 开始转换
    print("\n开始转换...")
    results = converter.convert_all_systems(input_file, output_dir, output_prefix, create_mixed)
    
    # 显示结果
    print("\n转换结果:")
    for result in results:
        print(result)
    
    print("\n转换完成!")
    return 0

def main():
    """主函数"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # 创建转换器实例
    converter = MultiSatelliteConverter()
    
    # 如果没有提供参数或者指定了交互式模式，则进入交互式模式
    if args.interactive or (not args.input_file and not args.stats):
        return interactive_mode()
    
    # 检查是否提供了输入文件
    if not args.input_file:
        print("错误: 必须提供输入文件路径")
        parser.print_help()
        return 1
    
    # 检查输入文件是否存在
    if not os.path.exists(args.input_file):
        print(f"错误: 文件不存在 - {args.input_file}")
        return 1
    
    # 显示详细信息
    if args.verbose:
        print("=" * 60)
        print("多卫星系统RINEX转换工具")
        print("支持: GPS, Galileo(GAL), BDS")
        print("=" * 60)
        print(f"输入文件: {args.input_file}")
        print(f"输出目录: {args.output or os.path.dirname(args.input_file)}")
        print(f"输出前缀: {args.prefix or 'output_<timestamp>'}")
        if args.systems:
            print(f"指定系统: {', '.join(args.systems)}")
        if args.mixed:
            print("创建混合导航文件: 是")
        print("-" * 60)
    
    # 显示统计信息
    if args.verbose or args.stats:
        print("\n文件统计信息:")
        stats = converter.show_statistics(args.input_file)
        for stat in stats:
            print(stat)
    
    # 如果只要求显示统计信息，则退出
    if args.stats:
        return 0
    
    # 开始转换
    if args.verbose:
        print("\n开始转换...")
    
    results = converter.convert_all_systems(
        args.input_file, 
        args.output, 
        args.prefix,
        args.mixed
    )
    
    # 显示结果
    if args.verbose:
        print("\n转换结果:")
    
    for result in results:
        print(result)
    
    if args.verbose:
        print("\n转换完成!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
