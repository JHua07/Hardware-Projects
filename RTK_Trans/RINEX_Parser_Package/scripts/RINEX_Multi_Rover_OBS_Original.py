#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import re

def parse_obsvma_to_rinex(obsvma_data, output_file):
    """
    整合卫星标识计算的OBSVMA数据解析器
    """
    try:
        # 系统映射表
        SYS_MAP = {
            0: 'G',  # GPS
            1: 'R',  # GLONASS
            2: 'S',  # SBAS
            3: 'E',  # Galileo
            4: 'C',  # BDS
            5: 'J'   # QZSS
        }
        
        # 解析头部信息和观测数据部分
        header_section, obs_section = obsvma_data.split(';', 1)
        obs_section = obs_section.strip()
        obs_section = re.sub(r'\*[0-9a-fA-F]+$', '', obs_section)
        
        # 解析头部信息
        header_fields = [field.strip() for field in header_section.split(',') if field.strip()]
        
        # 提取历元头信息
        # 格式: #OBSVMA,88,GPS,FINE,2368,291726000,0,0,18,37
        time_system = header_fields[2] if len(header_fields) > 2 else "GPS"  # 第3个字段：时间系统
        time_quality = header_fields[3] if len(header_fields) > 3 else "FINE"  # 第4个字段：时间质量
        gps_week = int(header_fields[4]) if len(header_fields) > 4 else 2368  # 第5个字段：GPS周数
        gps_tow_ms = int(header_fields[5]) if len(header_fields) > 5 else 291726000  # 第6个字段：GPS周内秒(ms)
        leap_seconds = int(header_fields[8]) if len(header_fields) > 8 else 18  # 第9个字段：闰秒
        output_delay = int(header_fields[9]) if len(header_fields) > 9 else 0  # 第10个字段：数据输出延迟
        
        # 将GPS周数和周内秒转换为年月日时分秒
        gps_tow_s = gps_tow_ms / 1000.0  # 转换为秒
        
        # GPS起始时间：1980年1月6日00:00:00 UTC
        gps_epoch_days = 6 + 365 * 10 + 2  # 1970到1980年的天数（包含闰年）
        gps_epoch_seconds = gps_epoch_days * 24 * 3600
        
        # 计算UTC时间
        total_seconds = gps_epoch_seconds + gps_week * 7 * 24 * 3600 + gps_tow_s - leap_seconds
        
        import datetime
        utc_time = datetime.datetime.utcfromtimestamp(total_seconds)
        
        # 格式化为RINEX格式的时间
        year = utc_time.year
        month = utc_time.month  
        day = utc_time.day
        hour = utc_time.hour
        minute = utc_time.minute
        second = utc_time.second + utc_time.microsecond / 1000000.0
        
        return {
            'year': year,
            'month': month,
            'day': day,
            'hour': hour,
            'minute': minute,
            'second': second,
            'satellite_data': parse_satellite_data(obs_section, SYS_MAP)
        }
                    
    except Exception as e:
        print(f"Error processing OBSVMA data: {e}")
        return None

def parse_satellite_data(obs_section, SYS_MAP):
    """解析卫星观测数据"""
    # 解析观测数据字段
    fields = [field.strip() for field in obs_section.split(',') if field.strip()]
    
    # 跳过第一个字段（观测信息数量）
    if fields and fields[0].isdigit():
        fields = fields[1:]
    
    # 存储卫星数据
    satellite_data = {}
    
    # 每11个字段为一组处理卫星数据（ASCII格式简化版）
    successful_parses = 0
    filtered_out = 0
    for i in range(0, len(fields), 11):
        if i + 10 >= len(fields):
            break
            
        group = fields[i:i+11]
        
        try:
            # 解析字段 - ASCII格式映射
            system_freq = group[0]   # GLONASS频点或其他系统标识
            prn = group[1]           # PRN号
            psr = group[2]           # 伪距
            adr = group[3]           # 载波相位
            psr_std = group[4]       # 伪距标准差
            adr_std = group[5]       # 载波相位标准差
            dopp = group[6]          # 多普勒
            cn0 = group[7]           # 载噪比
            reserved = group[8]      # 保留字段
            locktime = group[9]      # 连续跟踪时间
            ch_tr_status = group[10] # 跟踪状态
            
            # ==== 卫星标识计算核心逻辑 ====
            # 1. 转换跟踪状态为整数
            try:
                ch_tr_int = int(ch_tr_status, 16)
            except ValueError:
                continue
            
            # 2. 提取系统标识位 (bit16-18)
            sys_bits = (ch_tr_int >> 16) & 0x7
            
            # 3. 映射系统前缀
            sys_char = SYS_MAP.get(sys_bits, ' ')
            
            # 4. 处理PRN编号
            try:
                prn_int = int(prn)
            except ValueError:
                continue
            
            # 5. 生成卫星标识
            if sys_char == 'R':
                # 对GLONASS卫星，根据文档PRN范围38~61，减去37得到标准ID 1~24
                # 但实际RINEX中GLONASS使用1~24的编号
                mapped_prn = prn_int - 37
                sat_id = f"{sys_char}{mapped_prn:02d}"
            else:
                sat_id = f"{sys_char}{prn_int:02d}"
            # ============================
            
            # ==== 数据质量过滤逻辑 ====
            # 提取跟踪状态标志位
            psr_valid = (ch_tr_int >> 12) & 0x1     # bit 12: 伪距有效标志
            adr_valid = (ch_tr_int >> 10) & 0x1     # bit 10: 载波相位有效标志
            
            # 载噪比检查
            try:
                cn0_val = float(cn0) / 100.0
            except ValueError:
                continue
            
            # 基本数据质量过滤（第一版简化过滤）
            quality_check_passed = True
            
            # 1. 伪距有效性检查
            if psr_valid == 0:
                quality_check_passed = False
            
            # 2. 载波相位有效性检查
            if adr_valid == 0:
                quality_check_passed = False
            
            # 3. 载噪比基本阈值检查
            if cn0_val < 25.0:
                quality_check_passed = False
            
            # 如果质量检查不通过，跳过此观测记录
            if not quality_check_passed:
                filtered_out += 1
                continue
            # ==========================
            
            # 转换数值
            try:
                psr_val = float(psr)
                adr_val = abs(float(adr))  # 载波相位取绝对值
                dopp_val = float(dopp)
                cn0_val = float(cn0) / 100.0  # 转换为dB-Hz
            except ValueError:
                continue
            
            # 存储观测值
            if sat_id not in satellite_data:
                satellite_data[sat_id] = []
            
            satellite_data[sat_id].append({
                'psr': psr_val,
                'adr': adr_val,
                'dopp': dopp_val,
                'cn0': cn0_val
            })
            successful_parses += 1
            
        except Exception as e:
            continue
    
    print(f"成功解析了 {successful_parses} 个卫星观测数据")
    print(f"过滤了 {filtered_out} 个低质量观测数据")
    
    return satellite_data

def calculate_rover_position(input_file):
    """
    从BESTNAVXYZA数据计算流动站平均坐标
    """
    try:
        with open(input_file, 'r') as f:
            content = f.read()
        
        # 查找所有BESTNAVXYZA记录
        bestnavxyza_pattern = r'#BESTNAVXYZA[^#]*'
        bestnavxyza_records = re.findall(bestnavxyza_pattern, content, re.DOTALL)
        
        if not bestnavxyza_records:
            print("未找到BESTNAVXYZA记录，使用默认坐标")
            return -1326002.0000, 5323044.0000, 3243889.0000
        
        print(f"找到 {len(bestnavxyza_records)} 个BESTNAVXYZA记录")
        
        # 解析坐标数据
        coordinates = []
        for record in bestnavxyza_records:
            try:
                # 分割头部和数据部分
                if ';' not in record:
                    continue
                    
                header_section, data_section = record.split(';', 1)
                data_section = data_section.strip()
                data_section = re.sub(r'\*[0-9a-fA-F]+$', '', data_section)
                
                # 解析数据字段
                fields = [field.strip() for field in data_section.split(',') if field.strip()]
                
                # BESTNAVXYZA格式: SOL_COMPUTED,NARROW_INT,X,Y,Z,...
                if len(fields) >= 5 and 'NARROW_INT' in fields[1]:
                    x = float(fields[2])  # X坐标
                    y = float(fields[3])  # Y坐标  
                    z = float(fields[4])  # Z坐标
                    coordinates.append((x, y, z))
                    
            except Exception as e:
                continue
        
        if not coordinates:
            print("无法解析BESTNAVXYZA坐标数据，使用默认坐标")
            return -1326002.0000, 5323044.0000, 3243889.0000
        
        # 计算平均坐标
        avg_x = sum(coord[0] for coord in coordinates) / len(coordinates)
        avg_y = sum(coord[1] for coord in coordinates) / len(coordinates)
        avg_z = sum(coord[2] for coord in coordinates) / len(coordinates)
        
        print(f"计算得到流动站平均坐标:")
        print(f"  X: {avg_x:.4f}m")
        print(f"  Y: {avg_y:.4f}m") 
        print(f"  Z: {avg_z:.4f}m")
        print(f"  (基于 {len(coordinates)} 个BESTNAVXYZA记录)")
        
        return avg_x, avg_y, avg_z
        
    except Exception as e:
        print(f"计算坐标时出错: {e}")
        return -1326002.0000, 5323044.0000, 3243889.0000

def parse_multi_obsvma_to_rinex(input_file, output_file):
    """
    批处理多个OBSVMA数据的解析器
    """
    try:
        # 计算流动站坐标
        rover_x, rover_y, rover_z = calculate_rover_position(input_file)
        
        # 读取输入文件
        with open(input_file, 'r') as f:
            content = f.read()
        
        # 查找所有的OBSVMA记录
        obsvma_pattern = r'#OBSVMA[^#]*'
        obsvma_records = re.findall(obsvma_pattern, content, re.DOTALL)
        
        if not obsvma_records:
            print("未找到任何#OBSVMA记录")
            return
        
        print(f"找到 {len(obsvma_records)} 个OBSVMA记录")
        
        # 解析所有记录
        all_epochs = []
        for i, record in enumerate(obsvma_records):
            print(f"正在处理第 {i+1}/{len(obsvma_records)} 个OBSVMA记录...")
            epoch_data = parse_obsvma_to_rinex(record.strip(), None)
            if epoch_data:
                all_epochs.append(epoch_data)
        
        if not all_epochs:
            print("没有成功解析任何OBSVMA记录")
            return
        
        print(f"成功解析了 {len(all_epochs)} 个历元的数据")
        
        # 获取时间范围
        first_epoch = all_epochs[0]
        last_epoch = all_epochs[-1]
        
        # 固定文件头（流动站版本 - 使用计算得到的坐标）
        header = [
            "     3.02           OBSERVATION DATA    M                   RINEX VERSION / TYPE",
            "G = GPS,  R = GLONASS,  E = GALILEO,  C = BDS,  M = MIXED   COMMENT             ",
            "UnicoreConvert      Unicore             20250729 100837 UTC PGM / RUN BY / DATE",
            "UnicoreRoof 001                                             MARKER NAME         ",
            "GEODETIC                                                    MARKER TYPE         ",
            "Unicore-001         Unicore HPL EVT                         OBSERVER / AGENCY   ",
            "Unicore#001         GEODETIC            Unicore UB4B0       REC # / TYPE / VERS ",
            "Ant001              ROVER                                   ANT # / TYPE        ",
            f" {rover_x:13.4f} {rover_y:13.4f} {rover_z:13.4f}                  APPROX POSITION XYZ ",
            "        0.0000        0.0000        0.0000                  ANTENNA: DELTA H/E/N",
            "G    8 C1C L1C D1C S1C C2W L2W D2W S2W                      SYS / # / OBS TYPES ",
            "R    8 C1C L1C D1C S1C C2C L2C D2C S2C                      SYS / # / OBS TYPES ",
            "C   16 C1I L1I D1I S1I C7I L7I D7I S7I C6I L6I D6I S6I C1Q  SYS / # / OBS TYPES ",
            "       L1Q D1Q S1Q                                          SYS / # / OBS TYPES ",
            "E    8 C1C L1C D1C S1C C7Q L7Q D7Q S7Q                      SYS / # / OBS TYPES ",
            "J    8 C1C L1C D1C S1C C2L L2L D2L S2L                      SYS / # / OBS TYPES ",
            f"  {first_epoch['year']:4d}  {first_epoch['month']:4d}  {first_epoch['day']:4d}  {first_epoch['hour']:4d}  {first_epoch['minute']:4d}  {first_epoch['second']:6.1f}000000     GPS         TIME OF FIRST OBS    ",
            f"  {last_epoch['year']:4d}  {last_epoch['month']:4d}  {last_epoch['day']:4d}  {last_epoch['hour']:4d}  {last_epoch['minute']:4d}  {last_epoch['second']:6.1f}000000     GPS         TIME OF LAST OBS     ",
            "     0                                                      RCV CLOCK OFFS APPL  ",
            "                                                            END OF HEADER        "
        ]
        
        # 写入输出文件
        with open(output_file, 'w') as f:
            # 写入文件头
            for line in header:
                f.write(line + "\n")
            
            # 写入每个历元的数据
            for epoch in all_epochs:
                satellite_data = epoch['satellite_data']
                
                # 动态排序：先按系统类型（G、R、C、E、J、S），然后按PRN号排序
                def satellite_sort_key(sat_id):
                    """卫星排序键函数"""
                    sys_char = sat_id[0]
                    prn_num = int(sat_id[1:])
                    
                    # 系统优先级：GPS > GLONASS > BDS > Galileo > QZSS > SBAS
                    sys_priority = {'G': 1, 'R': 2, 'C': 3, 'E': 4, 'J': 5, 'S': 6}
                    return (sys_priority.get(sys_char, 9), prn_num)
                
                # 对卫星ID进行排序
                sat_order = sorted(satellite_data.keys(), key=satellite_sort_key)
                
                # 写入历元头（包含实际的卫星数量和解析出的时间）
                f.write(f"> {epoch['year']:4d} {epoch['month']:02d} {epoch['day']:02d} {epoch['hour']:02d} {epoch['minute']:02d} {epoch['second']:11.7f}  0 {len(sat_order)}\n")
                
                # 按排序后的顺序写入卫星数据
                for sat_id in sat_order:
                    observations = satellite_data[sat_id]
                    line = f"{sat_id}  "
                    
                    for i, obs in enumerate(observations):
                        # 格式化观测值，精确匹配参考文件格式
                        if i == 0:
                            # 第一组观测值的格式
                            psr_str = f"{obs['psr']:12.3f}"
                            adr_str = f"{obs['adr']:14.5f}"
                            dopp_str = f"{obs['dopp']:10.3f}"
                            cn0_str = f"{obs['cn0']:12.3f}"
                            line += f"{psr_str}   {adr_str}     {dopp_str}          {cn0_str}"
                        else:
                            # 后续观测值的格式
                            psr_str = f"{obs['psr']:12.3f}"
                            adr_str = f"{obs['adr']:13.5f}"
                            dopp_str = f"{obs['dopp']:10.3f}"
                            cn0_str = f"{obs['cn0']:12.3f}"
                            line += f"    {psr_str}   {adr_str}     {dopp_str}          {cn0_str}"
                    
                    f.write(line + "  \n")
        
        print(f"成功创建RINEX文件: {output_file}")
        print(f"包含 {len(all_epochs)} 个历元的观测数据")
                    
    except Exception as e:
        print(f"Error processing multi OBSVMA data: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) != 3:
        print("Usage: python RINEX_Multi_Rover_OBS_Original.py <input_file> <output_file>")
        sys.exit(1)
        
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    try:
        print(f"Converting {input_file} to RINEX 3.02 format...")
        parse_multi_obsvma_to_rinex(input_file, output_file)
        
    except FileNotFoundError:
        print(f"Error: Input file {input_file} not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
