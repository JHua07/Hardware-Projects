#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPS星历数据转换脚本, 以下是GPS EPH的字段格式说明

偏移 | 字段         | 类型    | 大小 | 描述
----|--------------|---------|------|-----------------------------------------------------
H+0  | PRN          | Ulong   | 4    | 卫星PRN编号 (GPS:1-32, QZSS:33-42)
H+4  | Tow          | Double  | 8    | 子帧0的时间戳 (秒)
H+12 | health       | Ulong   | 4    | 健康状态 (ICD-GPS-200a定义的6位健康代码)
H+16 | IODE1        | Ulong   | 4    | 星历数据1龄期
H+20 | IODE2        | Ulong   | 4    | 星历数据2龄期 (GPS的IODE1)
H+24 | Week         | Ulong   | 4    | GPS周数 (GPS Week)
H+28 | Z Week       | Ulong   | 4    | Z计数的周数 (星历表子帧1的周数)
H+32 | Toe          | Double  | 8    | 星历的参考时间 (秒)
H+40 | A            | Double  | 8    | 卫星轨道长半轴 (米)
H+48 | ΔN           | Double  | 8    | 卫星平均角速度的改正值 (弧度/秒)
H+56 | M0           | Double  | 8    | TOE时间的平近点角 (弧度)
H+64 | Ecc          | Double  | 8    | 卫星轨道偏心率
H+72 | ω            | Double  | 8    | 近地点幅角 (弧度)
H+80 | cuc          | Double  | 8    | 纬度幅角余弦振幅 (弧度)
H+88 | cus          | Double  | 8    | 纬度幅角正弦振幅 (弧度)
H+96 | crc          | Double  | 8    | 轨道半径余弦振幅 (米)
H+104| crs          | Double  | 8    | 轨道半径正弦振幅 (米)
H+112| cic          | Double  | 8    | 倾角余弦振幅 (弧度)
H+120| cis          | Double  | 8    | 倾角正弦振幅 (弧度)
H+128| I0           | Double  | 8    | TOE时间轨道倾角 (弧度)
H+136| IDOT         | Double  | 8    | 轨道倾角变化率 (弧度/秒)
H+144| Ω0           | Double  | 8    | 升交点赤经 (弧度)
H+152| Ω dot        | Double  | 8    | 升交点赤经变化率 (弧度/秒)
H+160| iodc         | Ulong   | 4    | 时钟数据龄期
H+164| toc          | Double  | 8    | 卫星钟差参考时间 (秒)
H+172| tgd          | Double  | 8    | 群延迟 (秒)
H+180| af0          | Double  | 8    | 卫星钟差参数 (秒)
H+188| af1          | Double  | 8    | 卫星钟速参数 (秒/秒)
H+196| af2          | Double  | 8    | 卫星钟漂参数 (秒/秒²)
H+204| AS           | Ulong   | 4    | 反欺骗: 0=FALSE, 1=TRUE
H+208| N            | Double  | 8    | 改正平均角速度 (弧度/秒)
H+216| URA          | Double  | 8    | 用户距离精度 (米²)
H+224| CRC          | Hex     | 4    | 32位CRC校验
H+236| [CR][LF]     | -       | -    | 语句结束符 (仅ASCII格式)
"""

import struct
from math import sqrt
from datetime import datetime, timedelta

# GPS时间原点 (1980-01-06 00:00:00 UTC)
GPS_EPOCH = datetime(1980, 1, 6)

def parse_eph_seg_ascii(eph_data_text):
    """
    解析ASCII格式的GPS EPF_SEG星历数据（NMEA格式）
    :param eph_data_text: ASCII格式的星历数据字符串
    :return: 解析后的星历字典
    """
    lines = eph_data_text.strip().split('\n')
    eph_list = []
    
    for line in lines:
        if line.startswith('#GPSEPHA'):
            try:
                # 找到分号位置，分号后面才是实际的字段数据
                semicolon_pos = line.find(';')
                if semicolon_pos == -1:
                    print(f"未找到分号分隔符: {line[:50]}...")
                    continue
                
                # 分割头部信息和数据部分
                header_part = line[:semicolon_pos]
                data_part = line[semicolon_pos + 1:]
                
                # 移除末尾的校验和部分 (*xxxx)
                if '*' in data_part:
                    data_part = data_part[:data_part.find('*')]
                
                # 解析头部信息 (逗号分隔)
                header_parts = header_part.split(',')
                # 解析数据部分 (逗号分隔)
                data_parts = data_part.split(',')
                
                if len(data_parts) < 30:
                    print(f"数据字段不足: {len(data_parts)} < 30")
                    continue
                
                eph = {}
                
                # 从数据部分解析GPS字段 (分号后的数据)
                idx = 0
                eph['prn']      = int(data_parts[idx]); idx += 1      # PRN编号 (GPS:1-32, QZSS:33-42)
                eph['tow']      = float(data_parts[idx]); idx += 1    # 子帧0的时间戳 (秒)
                eph['health']   = int(data_parts[idx]); idx += 1      # 健康状态 (6位健康代码)
                eph['iode1']    = int(data_parts[idx]); idx += 1      # 星历数据1龄期
                eph['iode2']    = int(data_parts[idx]); idx += 1      # 星历数据2龄期 (GPS的IODE1)
                eph['week']     = int(data_parts[idx]); idx += 1      # GPS周数
                eph['z_week']   = int(data_parts[idx]); idx += 1      # Z计数的周数
                eph['toe']      = float(data_parts[idx]); idx += 1    # 星历的参考时间 (秒)
                
                # 轨道参数
                eph['A']        = float(data_parts[idx]); idx += 1    # 卫星轨道长半轴 (米)
                eph['ΔN']       = float(data_parts[idx]); idx += 1    # 卫星平均角速度的改正值 (弧度/秒)
                eph['M0']       = float(data_parts[idx]); idx += 1    # TOE时间的平近点角 (弧度)
                eph['Ecc']      = float(data_parts[idx]); idx += 1    # 卫星轨道偏心率
                eph['ω']        = float(data_parts[idx]); idx += 1    # 近地点幅角 (弧度)
                eph['cuc']      = float(data_parts[idx]); idx += 1    # 纬度幅角余弦振幅 (弧度)
                eph['cus']      = float(data_parts[idx]); idx += 1    # 纬度幅角正弦振幅 (弧度)
                eph['crc']      = float(data_parts[idx]); idx += 1    # 轨道半径余弦振幅 (米)
                eph['crs']      = float(data_parts[idx]); idx += 1    # 轨道半径正弦振幅 (米)
                eph['cic']      = float(data_parts[idx]); idx += 1    # 倾角余弦振幅 (弧度)
                eph['cis']      = float(data_parts[idx]); idx += 1    # 倾角正弦振幅 (弧度)
                eph['I0']       = float(data_parts[idx]); idx += 1    # TOE时间轨道倾角 (弧度)
                eph['IDOT']     = float(data_parts[idx]); idx += 1    # 轨道倾角变化率 (弧度/秒)
                eph['Ω0']       = float(data_parts[idx]); idx += 1    # 升交点赤经 (弧度)
                eph['Ω_dot']    = float(data_parts[idx]); idx += 1    # 升交点赤经变化率 (弧度/秒)
                
                # 时钟参数
                if idx < len(data_parts):
                    eph['iodc'] = int(data_parts[idx]); idx += 1      # 时钟数据龄期
                else:
                    eph['iodc'] = eph['iode1']
                
                if idx < len(data_parts):
                    eph['toc']  = float(data_parts[idx]); idx += 1    # 卫星钟差参考时间 (秒)
                else:
                    eph['toc'] = eph['toe']
                
                # 解析剩余的时钟参数
                eph['tgd']  = float(data_parts[idx]) if idx < len(data_parts) else 0.0; idx += 1    # 群延迟 (秒)
                eph['af0']  = float(data_parts[idx]) if idx < len(data_parts) else 0.0; idx += 1    # 卫星钟差参数 (秒)
                eph['af1']  = float(data_parts[idx]) if idx < len(data_parts) else 0.0; idx += 1    # 卫星钟速参数 (秒/秒)
                eph['af2']  = float(data_parts[idx]) if idx < len(data_parts) else 0.0; idx += 1    # 卫星钟漂参数 (秒/秒²)
                
                # GPS特有参数
                if idx < len(data_parts):
                    # 处理AS字段：TRUE=1, FALSE=0
                    as_value = data_parts[idx].strip().upper()
                    if as_value == 'TRUE':
                        eph['AS'] = 1
                    elif as_value == 'FALSE':
                        eph['AS'] = 0
                    else:
                        eph['AS'] = int(as_value)  # 如果是数字形式
                    idx += 1
                else:
                    eph['AS'] = 0
                
                if idx < len(data_parts):
                    eph['N']    = float(data_parts[idx]); idx += 1    # 改正平均角速度 (弧度/秒)
                else:
                    eph['N'] = 0.0
                
                eph['URA']  = float(data_parts[idx]) if idx < len(data_parts) else 4.0              # 用户距离精度 (米²)
                
                eph_list.append(eph)
                print(f"成功解析GPS卫星 PRN {eph['prn']} 的星历数据")
                
            except (ValueError, IndexError) as e:
                print(f"解析行数据时出错: {line[:50]}... 错误: {e}")
                continue
    
    return eph_list

def gps_time_to_datetime(gps_week, gps_seconds):
    """
    GPS周和时间转换为UTC时间
    :param gps_week: GPS周数
    :param gps_seconds: GPS周内秒数
    :return: datetime对象
    """
    try:
        # 限制GPS周数范围，避免溢出
        if gps_week > 10000:  # 过大的GPS周数
            gps_week = gps_week % 1024  # 使用GPS周数的10位表示
        
        total_seconds = int(gps_week * 604800 + gps_seconds)
        return GPS_EPOCH + timedelta(seconds=total_seconds)
    except (OverflowError, ValueError):
        # 如果仍然溢出，返回当前时间
        return datetime.utcnow()

def format_rinex_float(value):
    """
    将浮点数格式化为RINEX格式 (使用D代替E)
    RINEX格式：正数和零前面加空格，负数负号占据空格位置
    :param value: 浮点数值
    :return: RINEX格式字符串 + 一个空格
    """
    if value == 0.0:
        return " .000000000000D+00 "
    
    # 处理正负号
    if value < 0:
        sign = '-'
        value = abs(value)
    else:
        sign = ' '  # 非负数前面加空格
    
    # 计算科学计数法的指数和尾数
    import math
    if value == 0:
        exp = 0
        mantissa = 0.0
    else:
        exp = math.floor(math.log10(value))
        mantissa = value / (10 ** exp)
    
    # 确保尾数在 [0.1, 1.0) 范围内
    if mantissa >= 1.0:
        mantissa /= 10
        exp += 1
    
    # 格式化尾数为12位小数
    mantissa_str = f"{mantissa:.12f}"
    
    # 转换为RINEX格式：0.143285 -> .143285
    if mantissa_str.startswith('0.'):
        mantissa_str = mantissa_str[1:]
    
    # 格式化指数部分
    if exp >= 0:
        exp_str = f"D+{exp:02d}"
    else:
        exp_str = f"D-{abs(exp):02d}"
    
    # 组合最终结果：符号 + 尾数 + 指数 + 一个空格
    result = sign + mantissa_str + exp_str + " "
    
    return result

def convert_to_nav_seg(eph_data_text):
    """
    将GPS EPF_SEG ASCII数据转换为RINEX NAV格式
    :param eph_data_text: ASCII格式的星历数据
    :return: RINEX NAV格式字符串
    """
    # 解析星历数据
    eph_list = parse_eph_seg_ascii(eph_data_text)
    
    if not eph_list:
        return "# 没有找到有效的GPS星历数据"
    
    # 创建RINEX NAV格式内容
    nav_seg = []
    
    # 1. 文件头
    now = datetime.utcnow().strftime('%Y%m%d %H%M%S UTC')
    nav_seg.append("     3.02           N: GNSS NAV DATA    G: GPS              RINEX VERSION / TYPE")
    nav_seg.append(f"UnicoreConvert      Unicore             {now} PGM / RUN BY / DATE")
    nav_seg.append("                                                            LEAP SECONDS")
    nav_seg.append("                                                            END OF HEADER")
    
    # 2. 处理每个GPS卫星的数据
    for eph in eph_list:
        # GPS卫星系统标识
        sat_system = 'G'  # GPS
        prn = eph['prn']
        sat_id = f"{sat_system}{prn:02d}"
        
        # 转换参考时间
        toc_dt = gps_time_to_datetime(eph['week'], eph['toc'])
        
        # GPS卫星数据块 (每个卫星8行)
        # 第一行: PRN和时钟参数
        nav_seg.append(
            f"{sat_id} {toc_dt.year:4d} {toc_dt.month:02d} {toc_dt.day:02d} "
            f"{toc_dt.hour:02d} {toc_dt.minute:02d} {toc_dt.second:02d} "
            f"{format_rinex_float(eph['af0'])}{format_rinex_float(eph['af1'])}{format_rinex_float(eph['af2'])}"
        )
        
        # 第二行: IODE, Crs, Delta_n, M0
        nav_seg.append(
            f"     {format_rinex_float(float(eph.get('iode1', 1)))}{format_rinex_float(eph['crs'])}"
            f"{format_rinex_float(eph['ΔN'])}{format_rinex_float(eph['M0'])}"
        )
        
        # 第三行: Cuc, e, Cus, sqrt(A)
        sqrt_a = eph['A'] ** 0.5
        nav_seg.append(
            f"     {format_rinex_float(eph['cuc'])}{format_rinex_float(eph['Ecc'])}"
            f"{format_rinex_float(eph['cus'])}{format_rinex_float(sqrt_a)}"
        )
        
        # 第四行: Toe, Cic, OMEGA, Cis
        nav_seg.append(
            f"     {format_rinex_float(eph['toe'])}{format_rinex_float(eph['cic'])}"
            f"{format_rinex_float(eph['Ω0'])}{format_rinex_float(eph['cis'])}"
        )
        
        # 第五行: i0, Crc, omega, OMEGA_DOT
        nav_seg.append(
            f"     {format_rinex_float(eph['I0'])}{format_rinex_float(eph['crc'])}"
            f"{format_rinex_float(eph['ω'])}{format_rinex_float(eph['Ω_dot'])}"
        )
        
        # 第六行: IDOT, Codes_on_L2, GPS_Week, L2_P_data_flag
        # GPS特有字段 - Codes_on_L2应该反映AS标志
        nav_seg.append(
            f"     {format_rinex_float(eph['IDOT'])}{format_rinex_float(float(eph['AS']))}"
            f"{format_rinex_float(float(eph['week']))}{format_rinex_float(0.0)}"
        )
        
        # 第七行: SV_accuracy, SV_health, TGD, IODC
        # SV_accuracy应该是URA值开根号，而不是URA指数
        ura_sqrt = sqrt(eph['URA'])
        nav_seg.append(
            f"     {format_rinex_float(ura_sqrt)}{format_rinex_float(float(eph['health']))}"
            f"{format_rinex_float(eph['tgd'])}{format_rinex_float(float(eph['iodc']))}"
        )
        
        # 第八行: 传输时间 和 fit interval (GPS用tow表示)
        nav_seg.append(
            f"     {format_rinex_float(eph['tow'])}{format_rinex_float(0.0)}"
        )
    
    return "\n".join(nav_seg)

def convert_ura(ura_value):
    """
    将URA值转换为URA指数 (根据ICD-GPS-200标准)
    :param ura_value: URA值 (米²)
    :return: URA指数 (0-15)
    """
    ura_std = sqrt(ura_value)  # 计算标准差
    ura_table = [
        0.0, 2.4, 3.4, 4.85, 6.85, 9.65, 
        13.65, 24.0, 48.0, 96.0, 192.0, 384.0, 
        768.0, 1536.0, 3072.0, 6144.0
    ]
    
    # 查找匹配的URA指数
    for i in range(len(ura_table)):
        if ura_std <= ura_table[i]:
            return i
    return 15  # 超过6144米的异常值

def save_nav_seg_file(nav_content, file_path):
    """
    保存RINEX NAV文件
    :param nav_content: RINEX NAV格式内容
    :param file_path: 文件保存路径
    """
    with open(file_path, 'w') as f:
        f.write(nav_content)

# ================================================
# 示例使用代码
# ================================================
if __name__ == "__main__":
    # 1. 读取GPS EPF_SEG ASCII文件
    input_file = r'D:\desktop\RTK_Trans\Test\EPH_SEG_GPS.txt'
    output_file = r'D:\desktop\RTK_Trans\output_gps.nav'
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            eph_data_text = f.read()
        
        # 2. 转换为RINEX NAV格式
        nav_seg_content = convert_to_nav_seg(eph_data_text)
        
        # 3. 保存为文件
        save_nav_seg_file(nav_seg_content, output_file)
        
        print(f"GPS星历转换完成! RINEX NAV文件已保存到: {output_file}")
        print(f"输入文件: {input_file}")
        print(f"输出文件: {output_file}")
        
    except FileNotFoundError:
        print(f"错误: 找不到输入文件 {input_file}")
    except Exception as e:
        print(f"转换过程中出错: {e}")
        import traceback
        traceback.print_exc()