#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GAL星历数据转换脚本, 以下是GAL EPH的字段格式说明

偏移 | 字段            | 类型    | 大小 | 描述
----|-----------------|---------|------|-----------------------------------------------------
H+0  | SatId           | Ulong   | 4    | 卫星ID编号 (Galileo:1-38)
H+4  | FNAVReceived    | Bool    | 4    | 接收到FNAV星历数据的标识
H+8  | INAVReceived    | Bool    | 4    | 接收到INAV星历数据的标识
H+12 | E1BHealth       | Uchar   | 1    | E1b健康状态 (INAV有效时)
H+13 | E5aHealth       | Uchar   | 1    | E5a健康状态 (FNAV有效时)
H+14 | E5bHealth       | Uchar   | 1    | E5b健康状态 (INAV有效时)
H+15 | E1BDVS          | Uchar   | 1    | E1b数据有效状态 (INAV有效时)
H+16 | E5aDVS          | Uchar   | 1    | E5a数据有效状态 (FNAV有效时)
H+17 | E5bDVS          | Uchar   | 1    | E5b数据有效状态 (INAV有效时)
H+18 | SISA            | Uchar   | 1    | 空间信号精度 (Signal-In-Space Accuracy)
H+19 | Reserved        | Uchar   | 1    | 保留字段
H+20 | IODNav          | Ulong   | 4    | 星历数据期号
H+24 | Toe             | Ulong   | 4    | 星历参考时间 (秒)
H+28 | RootA           | Double  | 8    | 卫星轨道长半轴 (√m)
H+36 | DeltaN          | Double  | 8    | 平均角速度改正值 (rad/s)
H+44 | M0              | Double  | 8    | TOE时间的平近点角 (rad)
H+52 | Ecc             | Double  | 8    | 轨道偏心率
H+60 | Omega           | Double  | 8    | 近地点幅角 (rad)
H+68 | Cuc             | Double  | 8    | 纬度幅角余弦振幅 (rad)
H+76 | Cus             | Double  | 8    | 纬度幅角正弦振幅 (rad)
H+84 | Crc             | Double  | 8    | 轨道半径余弦振幅 (m)
H+92 | Crs             | Double  | 8    | 轨道半径正弦振幅 (m)
H+100| Cic             | Double  | 8    | 倾角余弦振幅 (rad)
H+108| Cis             | Double  | 8    | 倾角正弦振幅 (rad)
H+116| I0              | Double  | 8    | TOE时间轨道倾角 (rad)
H+124| IDot            | Double  | 8    | 轨道倾角变化率 (rad/s)
H+132| Omega0          | Double  | 8    | 升交点赤经 (rad)
H+140| OmegaDot        | Double  | 8    | 升交点赤经变化率 (rad/s)
H+148| FNAVT0c         | Ulong   | 4    | FNAV钟差参考时间 (s) (FNAV有效时)
H+152| FNAVAf0         | Double  | 8    | FNAV钟差参数 (s)
H+160| FNAVAf1         | Double  | 8    | FNAV钟速参数 (s/s)
H+168| FNAVAf2         | Double  | 8    | FNAV钟漂参数 (s/s²)
H+176| INAVT0c         | Ulong   | 4    | INAV钟差参考时间 (s) (INAV有效时)
H+180| INAVAf0         | Double  | 8    | INAV钟差参数 (s)
H+188| INAVAf1         | Double  | 8    | INAV钟速参数 (s/s)
H+196| INAVAf2         | Double  | 8    | INAV钟漂参数 (s/s²)
H+204| E1E5aBGD        | Double  | 8    | E1-E5a广播群延迟 (s)
H+212| E1E5bBGD        | Double  | 8    | E1-E5b广播群延迟 (s) (INAV有效时)
H+220| CRC             | Hex     | 4    | 32位CRC校验
H+224| [CR][LF]        | -       | -    | 语句结束符 (仅ASCII格式)

"""

import struct
from math import sqrt
from datetime import datetime, timedelta

# GPS时间原点 (1980-01-06 00:00:00 UTC)
GPS_EPOCH = datetime(1980, 1, 6)

def parse_eph_seg_ascii(eph_data_text):
    """
    解析ASCII格式的Galileo EPF_SEG星历数据（NMEA格式）
    :param eph_data_text: ASCII格式的星历数据字符串
    :return: 解析后的星历字典
    """
    lines = eph_data_text.strip().split('\n')
    eph_list = []
    
    for line in lines:
        if line.startswith('#GALEPHA'):
            try:
                # 找到分号位置，分号后面才是实际的字段数据
                semicolon_pos = line.find(';')
                if semicolon_pos == -1:
                    print(f"未找到分号分隔符: {line[:50]}...")
                    continue
                
                # 分割头部信息和数据部分
                header_part = line[:semicolon_pos]
                data_part = line[semicolon_pos + 1:]
                
                # 解析头部信息 (逗号分隔)
                # #GALEPHA,88,GPS,FINE,2368,291958000,0,0,18,40
                header_parts = header_part.split(',')
                if len(header_parts) < 5:
                    print(f"头部字段不足: {len(header_parts)} < 5")
                    continue
                
                # 从头部获取GPS周数 (第5个字段，索引4)
                gps_week = int(header_parts[4])  # 2368
                
                # 移除末尾的校验和部分 (*xxxx)
                if '*' in data_part:
                    data_part = data_part[:data_part.find('*')]
                
                # 解析数据部分 (逗号分隔)
                data_parts = data_part.split(',')
                
                if len(data_parts) < 30:
                    print(f"数据字段不足: {len(data_parts)} < 30")
                    continue
                
                eph = {}
                
                # 保存从头部解析的GPS周数
                eph['gps_week'] = gps_week
                
                # 从数据部分解析Galileo字段 (分号后的数据)
                idx = 0
                eph['sat_id']       = int(data_parts[idx]); idx += 1      # 卫星ID编号 (Galileo:1-38)
                
                # 处理布尔字段：TRUE=1, FALSE=0
                fnav_str = data_parts[idx].strip().upper()
                eph['fnav_received'] = fnav_str == 'TRUE'; idx += 1  # 接收到FNAV星历数据的标识
                
                inav_str = data_parts[idx].strip().upper()
                eph['inav_received'] = inav_str == 'TRUE'; idx += 1  # 接收到INAV星历数据的标识
                
                eph['e1b_health']   = int(data_parts[idx]); idx += 1      # E1b健康状态
                eph['e5a_health']   = int(data_parts[idx]); idx += 1      # E5a健康状态
                eph['e5b_health']   = int(data_parts[idx]); idx += 1      # E5b健康状态
                eph['e1b_dvs']      = int(data_parts[idx]); idx += 1      # E1b数据有效状态
                eph['e5a_dvs']      = int(data_parts[idx]); idx += 1      # E5a数据有效状态
                eph['e5b_dvs']      = int(data_parts[idx]); idx += 1      # E5b数据有效状态
                eph['sisa']         = int(data_parts[idx]); idx += 1      # 空间信号精度
                idx += 1  # 跳过保留字段
                eph['iod_nav']      = int(data_parts[idx]); idx += 1      # 星历数据期号
                eph['toe']          = float(data_parts[idx]); idx += 1    # 星历参考时间 (秒)
                
                # 轨道参数
                eph['root_a']       = float(data_parts[idx]); idx += 1    # 卫星轨道长半轴的平方根 (√m)
                eph['delta_n']      = float(data_parts[idx]); idx += 1    # 平均角速度改正值 (rad/s)
                eph['m0']           = float(data_parts[idx]); idx += 1    # TOE时间的平近点角 (rad)
                eph['ecc']          = float(data_parts[idx]); idx += 1    # 轨道偏心率
                eph['omega']        = float(data_parts[idx]); idx += 1    # 近地点幅角 (rad)
                eph['cuc']          = float(data_parts[idx]); idx += 1    # 纬度幅角余弦振幅 (rad)
                eph['cus']          = float(data_parts[idx]); idx += 1    # 纬度幅角正弦振幅 (rad)
                eph['crc']          = float(data_parts[idx]); idx += 1    # 轨道半径余弦振幅 (m)
                eph['crs']          = float(data_parts[idx]); idx += 1    # 轨道半径正弦振幅 (m)
                eph['cic']          = float(data_parts[idx]); idx += 1    # 倾角余弦振幅 (rad)
                eph['cis']          = float(data_parts[idx]); idx += 1    # 倾角正弦振幅 (rad)
                eph['i0']           = float(data_parts[idx]); idx += 1    # TOE时间轨道倾角 (rad)
                eph['idot']         = float(data_parts[idx]); idx += 1    # 轨道倾角变化率 (rad/s)
                eph['omega0']       = float(data_parts[idx]); idx += 1    # 升交点赤经 (rad)
                eph['omega_dot']    = float(data_parts[idx]); idx += 1    # 升交点赤经变化率 (rad/s)
                
                # FNAV时钟参数
                if idx < len(data_parts):
                    eph['fnav_t0c'] = float(data_parts[idx]); idx += 1    # FNAV钟差参考时间 (s)
                else:
                    eph['fnav_t0c'] = eph['toe']
                
                eph['fnav_af0']     = float(data_parts[idx]) if idx < len(data_parts) else 0.0; idx += 1    # FNAV钟差参数 (s)
                eph['fnav_af1']     = float(data_parts[idx]) if idx < len(data_parts) else 0.0; idx += 1    # FNAV钟速参数 (s/s)
                eph['fnav_af2']     = float(data_parts[idx]) if idx < len(data_parts) else 0.0; idx += 1    # FNAV钟漂参数 (s/s²)
                
                # INAV时钟参数
                if idx < len(data_parts):
                    eph['inav_t0c'] = float(data_parts[idx]); idx += 1    # INAV钟差参考时间 (s)
                else:
                    eph['inav_t0c'] = eph['toe']
                
                eph['inav_af0']     = float(data_parts[idx]) if idx < len(data_parts) else 0.0; idx += 1    # INAV钟差参数 (s)
                eph['inav_af1']     = float(data_parts[idx]) if idx < len(data_parts) else 0.0; idx += 1    # INAV钟速参数 (s/s)
                eph['inav_af2']     = float(data_parts[idx]) if idx < len(data_parts) else 0.0; idx += 1    # INAV钟漂参数 (s/s²)
                
                # 广播群延迟参数
                eph['e1e5a_bgd']    = float(data_parts[idx]) if idx < len(data_parts) else 0.0; idx += 1    # E1-E5a广播群延迟 (s)
                eph['e1e5b_bgd']    = float(data_parts[idx]) if idx < len(data_parts) else 0.0; idx += 1    # E1-E5b广播群延迟 (s)
                
                # 选择使用INAV或FNAV数据（优先使用INAV）
                if eph['inav_received']:
                    eph['toc'] = eph['inav_t0c']
                    eph['af0'] = eph['inav_af0']
                    eph['af1'] = eph['inav_af1']
                    eph['af2'] = eph['inav_af2']
                    eph['health'] = eph['e1b_health']  # 使用E1b健康状态
                    eph['data_source'] = 'INAV'
                else:
                    eph['toc'] = eph['fnav_t0c']
                    eph['af0'] = eph['fnav_af0']
                    eph['af1'] = eph['fnav_af1']
                    eph['af2'] = eph['fnav_af2']
                    eph['health'] = eph['e5a_health']  # 使用E5a健康状态
                    eph['data_source'] = 'FNAV'
                
                eph_list.append(eph)
                print(f"成功解析Galileo卫星 ID {eph['sat_id']} 的星历数据 (数据源: {eph['data_source']})")
                
            except (ValueError, IndexError) as e:
                print(f"解析行数据时出错: {line[:50]}... 错误: {e}")
                continue
    
    return eph_list

def gal_time_to_datetime(gal_week, gal_seconds):
    """
    Galileo周和时间转换为UTC时间
    Galileo时间起始于1999-08-22 00:00:00 UTC (GPS周数1024)
    :param gal_week: Galileo周数
    :param gal_seconds: Galileo周内秒数
    :return: datetime对象
    """
    try:
        # Galileo时间起始点 (1999年8月22日)
        GAL_EPOCH = datetime(1999, 8, 22)
        
        # 限制Galileo周数范围，避免溢出
        if gal_week > 10000:  # 过大的Galileo周数
            gal_week = gal_week % 4096  # 使用Galileo周数的12位表示
        
        total_seconds = int(gal_week * 604800 + gal_seconds)
        return GAL_EPOCH + timedelta(seconds=total_seconds)
    except (OverflowError, ValueError):
        # 如果仍然溢出，返回当前时间
        return datetime.utcnow()

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
    将Galileo EPF_SEG ASCII数据转换为RINEX NAV格式
    :param eph_data_text: ASCII格式的星历数据
    :return: RINEX NAV格式字符串
    """
    # 解析星历数据
    eph_list = parse_eph_seg_ascii(eph_data_text)
    
    if not eph_list:
        return "# 没有找到有效的Galileo星历数据"
    
    # 创建RINEX NAV格式内容
    nav_seg = []
    
    # 1. 文件头
    now = datetime.utcnow().strftime('%Y%m%d %H%M%S UTC')
    nav_seg.append("     3.02           N: GNSS NAV DATA    E: Galileo          RINEX VERSION / TYPE")
    nav_seg.append(f"UnicoreConvert      Unicore             {now} PGM / RUN BY / DATE")
    nav_seg.append("                                                            LEAP SECONDS")
    nav_seg.append("                                                            END OF HEADER")
    
    # 2. 处理每个Galileo卫星的数据
    for eph in eph_list:
        # Galileo卫星系统标识
        sat_system = 'E'  # Galileo
        sat_id = f"{sat_system}{eph['sat_id']:02d}"
        
        # 转换参考时间 (假设输入数据使用GPS周，需要转换为Galileo时间)
        # 使用从头部解析的GPS周数
        toc_dt = gps_time_to_datetime(eph['gps_week'], eph['toc'])
        
        # Galileo卫星数据块 (每个卫星8行)
        # 第一行: PRN和时钟参数
        nav_seg.append(
            f"{sat_id} {toc_dt.year:4d} {toc_dt.month:02d} {toc_dt.day:02d} "
            f"{toc_dt.hour:02d} {toc_dt.minute:02d} {toc_dt.second:02d} "
            f"{format_rinex_float(eph['af0'])}{format_rinex_float(eph['af1'])}{format_rinex_float(eph['af2'])}"
        )
        
        # 第二行: IODnav, Crs, Delta_n, M0
        nav_seg.append(
            f"     {format_rinex_float(float(eph['iod_nav']))}{format_rinex_float(eph['crs'])}"
            f"{format_rinex_float(eph['delta_n'])}{format_rinex_float(eph['m0'])}"
        )
        
        # 第三行: Cuc, e, Cus, sqrt(A)
        # Galileo直接提供sqrt(A)
        nav_seg.append(
            f"     {format_rinex_float(eph['cuc'])}{format_rinex_float(eph['ecc'])}"
            f"{format_rinex_float(eph['cus'])}{format_rinex_float(eph['root_a'])}"
        )
        
        # 第四行: Toe, Cic, OMEGA0, Cis
        nav_seg.append(
            f"     {format_rinex_float(eph['toe'])}{format_rinex_float(eph['cic'])}"
            f"{format_rinex_float(eph['omega0'])}{format_rinex_float(eph['cis'])}"
        )
        
        # 第五行: i0, Crc, omega, OMEGA_DOT
        nav_seg.append(
            f"     {format_rinex_float(eph['i0'])}{format_rinex_float(eph['crc'])}"
            f"{format_rinex_float(eph['omega'])}{format_rinex_float(eph['omega_dot'])}"
        )
        
        # 第六行: IDOT, L2_CA_Code_Flag, Satellite_Week, spare
        # L2_CA_Code_Flag: L2频道C/A码标识，在Galileo中表示信号类型标识 = 517
        # Satellite_Week: 卫星周数，从头部解析获取
        nav_seg.append(
            f"     {format_rinex_float(eph['idot'])}{format_rinex_float(517.0)}"
            f"{format_rinex_float(float(eph['gps_week']))}                                      "
        )
        
        # 第七行: SVA(m), SV_health, BGD_E1E5a, BGD_E1E5b
        # SVA: 卫星精度（米），需要将SISA转换为实际精度值
        sva_meters = convert_sisa_to_meters(eph['sisa'])
        nav_seg.append(
            f"     {format_rinex_float(sva_meters)}{format_rinex_float(float(eph['health']))}"
            f"{format_rinex_float(eph['e1e5a_bgd'])}{format_rinex_float(eph['e1e5b_bgd'])}"
        )
        
        # 第八行: 传输时间 (参考文件中只有一个字段)
        nav_seg.append(
            f"     {format_rinex_float(eph['toe'])}"
        )
    
    return "\n".join(nav_seg)

def convert_sisa_to_meters(sisa_index):
    """
    将Galileo SISA索引转换为SVA精度值（米）
    :param sisa_index: SISA索引 (0-255)
    :return: SVA精度值（米）
    """
    # Galileo SISA到SVA的转换表 (根据Galileo ICD)
    if sisa_index <= 49:
        return sisa_index * 0.01  # 0-0.49米，步长0.01米
    elif sisa_index <= 74:
        return 0.5 + (sisa_index - 50) * 0.02  # 0.5-0.98米，步长0.02米
    elif sisa_index <= 99:
        return 1.0 + (sisa_index - 75) * 0.04  # 1.0-1.96米，步长0.04米
    elif sisa_index <= 125:
        return 2.0 + (sisa_index - 100) * 0.16  # 2.0-6.0米，步长0.16米
    else:
        return 6.0  # 大于125的值对应>6米

def convert_sisa(sisa_value):
    """
    转换Galileo SISA（Signal-In-Space Accuracy）值
    :param sisa_value: SISA值
    :return: SISA索引或值
    """
    # SISA值通常已经是索引形式，直接返回
    return float(sisa_value)

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
    # 1. 读取Galileo EPF_SEG ASCII文件
    input_file = r'D:\desktop\RTK_Trans\Test\EPH_SEG_GAL.txt'
    output_file = r'D:\desktop\RTK_Trans\output_gal.nav'
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            eph_data_text = f.read()
        
        # 2. 转换为RINEX NAV格式
        nav_seg_content = convert_to_nav_seg(eph_data_text)
        
        # 3. 保存为文件
        save_nav_seg_file(nav_seg_content, output_file)
        
        print(f"Galileo星历转换完成! RINEX NAV文件已保存到: {output_file}")
        print(f"输入文件: {input_file}")
        print(f"输出文件: {output_file}")
        
    except FileNotFoundError:
        print(f"错误: 找不到输入文件 {input_file}")
    except Exception as e:
        print(f"转换过程中出错: {e}")
        import traceback
        traceback.print_exc()