import sys
import re

def parse_obsvbasea_to_rinex(obsvbasea_data, output_file, detected_obs_types=None):
    """
    整合卫星标识计算的OBSVBASEA数据解析器
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
        header_section, obs_section = obsvbasea_data.split(';', 1)
        obs_section = obs_section.strip()
        obs_section = re.sub(r'\*[0-9a-fA-F]+$', '', obs_section)
        
        # 解析头部信息
        header_fields = [field.strip() for field in header_section.split(',') if field.strip()]
        
        # 提取历元头信息
        # 格式: #OBSVBASEA,88,GPS,FINE,2368,291726000,0,0,18,37
        time_system = header_fields[2] if len(header_fields) > 2 else "GPS"      # 第4个字段: 时间系统 (TimeRef)
        time_quality = header_fields[3] if len(header_fields) > 3 else "FINE"     # 第5个字段: 时间质量 (TimeStatus)
        gps_week = int(header_fields[4]) if len(header_fields) > 4 else 0        # 第6个字段: GPS周数 (Wn)
        gps_tow_ms = int(header_fields[5]) if len(header_fields) > 5 else 0      # 第7个字段: GPS周内秒(ms) (Ms)
        # leap_seconds = int(header_fields[8]) if len(header_fields) > 8 else 18   # 第10个字段: 闰秒 (Leap sec)， UPrecise好像不需要闰秒
        leap_seconds = 0
        output_delay = int(header_fields[9]) if len(header_fields) > 9 else 0 # 第11个字段: 数据输出延迟 (Output Delay)

        import datetime

        # 将GPS周数和周内秒转换为UTC时间
        gps_tow_s = gps_tow_ms / 1000.0  # 转换为秒
        
        # GPS时间的原点是 1980年1月6日 00:00:00 UTC
        gps_epoch = datetime.datetime(1980, 1, 6, 0, 0, 0)
        
        # 计算从GPS原点开始的总秒数
        total_seconds_from_epoch = (gps_week * 7 * 24 * 3600) + gps_tow_s
        
        # 计算GPS时间
        gps_time = gps_epoch + datetime.timedelta(seconds=total_seconds_from_epoch)
        
        # 从GPS时间中减去闰秒得到UTC时间
        utc_time = gps_time - datetime.timedelta(seconds=leap_seconds)
        
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
            'satellite_data': parse_satellite_data(obs_section, SYS_MAP, detected_obs_types)
        }
                    
    except Exception as e:
        print(f"Error processing OBSVBASEA data: {e}")
        return None

def parse_satellite_data(obs_section, SYS_MAP, detected_obs_types=None):
    """解析卫星观测数据"""
    # 解析观测数据字段
    fields = [field.strip() for field in obs_section.split(',') if field.strip()]
    
    # 跳过第一个字段（观测信息数量）
    if fields and fields[0].isdigit():
        fields = fields[1:]
    
    # 存储卫星数据
    satellite_data = {}
    
    # 如果提供了观测类型收集器，初始化
    if detected_obs_types is None:
        detected_obs_types = {}
    
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
            # 1. 转换跟踪状态为整数（使用第10个字段）
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
            
            # 确定观测类型并记录到检测列表中
            sys_char = sat_id[0]
            if sys_char not in detected_obs_types:
                detected_obs_types[sys_char] = set()
            
            # 根据卫星系统和跟踪状态确定观测类型
            obs_type_info = determine_obs_types_from_status(ch_tr_int, sys_char)
            detected_obs_types[sys_char].update(obs_type_info)
            
            satellite_data[sat_id].append({
                'psr': psr_val,
                'adr': adr_val,
                # 'dopp': dopp_val,
                'cn0': cn0_val
            })
            successful_parses += 1
            
        except Exception as e:
            continue
    
    print(f"成功解析了 {successful_parses} 个卫星观测数据")
    print(f"过滤了 {filtered_out} 个低质量观测数据")
    
    return satellite_data

def determine_obs_types_from_status(status_word, sys_char):
    """
    根据跟踪状态字和卫星系统确定观测类型（与 REF_CODES/unicore.c 保持一致）
    - 信号类型(sigtype): 位21-25（5位）
    - L2C 标志(l2c): 位26（1位），仅在 GPS/QZSS 的 sigtype==9 时区分 L2C(M) 与 L2P(Y)/semi-codeless
    """
    obs_types = set()

    sigtype = (status_word >> 21) & 0x1F
    l2c = (status_word >> 26) & 0x01

    if sys_char == 'G':  # GPS
        if sigtype == 0:  # L1 C/A
            obs_types.update(['C1C', 'L1C', 'D1C', 'S1C'])
        elif sigtype == 3:  # L1C Pilot
            obs_types.update(['C1L', 'L1L', 'D1L', 'S1L'])
        elif sigtype == 11:  # L1C Data
            obs_types.update(['C1S', 'L1S', 'D1S', 'S1S'])
        elif sigtype == 6:  # L5 Data
            obs_types.update(['C5I', 'L5I', 'D5I', 'S5I'])
        elif sigtype == 14:  # L5 Pilot
            obs_types.update(['C5Q', 'L5Q', 'D5Q', 'S5Q'])
        elif sigtype == 9:  # L2: P(Y)/semi-codeless or L2C(M)
            if l2c == 1:
                obs_types.update(['C2S', 'L2S', 'D2S', 'S2S'])  # L2C(M)
            else:
                obs_types.update(['C2W', 'L2W', 'D2W', 'S2W'])  # L2P(Y) / semi-codeless
                # obs_types.update(['C2P', 'L2P', 'D2P', 'S2P'])  # L2P(Y) / semi-codeless
        elif sigtype == 17:  # L2C(L)
            obs_types.update(['C2L', 'L2L', 'D2L', 'S2L'])

    elif sys_char == 'R':  # GLONASS
        if sigtype == 0:  # L1 C/A
            obs_types.update(['C1C', 'L1C', 'D1C', 'S1C'])
        elif sigtype == 5:  # L2 C/A
            obs_types.update(['C2C', 'L2C', 'D2C', 'S2C'])
        elif sigtype == 6:  # G3I
            obs_types.update(['C3I', 'L3I', 'D3I', 'S3I'])
        elif sigtype == 7:  # G3Q
            obs_types.update(['C3Q', 'L3Q', 'D3Q', 'S3Q'])

    elif sys_char == 'E':  # Galileo
        if sigtype == 1:  # E1B
            obs_types.update(['C1B', 'L1B', 'D1B', 'S1B'])
        elif sigtype == 2:  # E1C
            obs_types.update(['C1C', 'L1C', 'D1C', 'S1C'])
        elif sigtype == 12:  # E5a Pilot
            obs_types.update(['C5Q', 'L5Q', 'D5Q', 'S5Q'])
        elif sigtype == 17:  # E5b Pilot
            obs_types.update(['C7Q', 'L7Q', 'D7Q', 'S7Q'])
        elif sigtype == 18:  # E6B
            obs_types.update(['C6B', 'L6B', 'D6B', 'S6B'])
        elif sigtype == 22:  # E6C
            obs_types.update(['C6C', 'L6C', 'D6C', 'S6C'])

    elif sys_char == 'J':  # QZSS
        if sigtype == 0:  # L1 C/A
            obs_types.update(['C1C', 'L1C', 'D1C', 'S1C'])
        elif sigtype == 1:  # L1E
            obs_types.update(['C1E', 'L1E', 'D1E', 'S1E'])
        elif sigtype == 3:  # L1C pilot
            obs_types.update(['C1L', 'L1L', 'D1L', 'S1L'])
        elif sigtype == 4:  # L1Z (L1S)
            obs_types.update(['C1Z', 'L1Z', 'D1Z', 'S1Z'])
        elif sigtype == 6:  # L5 Data
            obs_types.update(['C5I', 'L5I', 'D5I', 'S5I'])
        elif sigtype == 9:  # L2: P(Y)/semi-codeless or L2C(M)
            if l2c == 1:
                obs_types.update(['C2S', 'L2S', 'D2S', 'S2S'])
            else:
                obs_types.update(['C2W', 'L2W', 'D2W', 'S2W'])
        elif sigtype == 11:  # L1C Data
            obs_types.update(['C1S', 'L1S', 'D1S', 'S1S'])
        elif sigtype == 14:  # L5 Pilot
            obs_types.update(['C5Q', 'L5Q', 'D5Q', 'S5Q'])
        elif sigtype == 17:  # L2C(L)
            obs_types.update(['C2L', 'L2L', 'D2L', 'S2L'])
        elif sigtype == 21:  # L6Z (L6D)
            obs_types.update(['C6Z', 'L6Z', 'D6Z', 'S6Z'])
        elif sigtype == 27:  # L6E
            obs_types.update(['C6E', 'L6E', 'D6E', 'S6E'])

    elif sys_char == 'C':  # BDS (Beidou)
        if sigtype == 0:  # B1I
            obs_types.update(['C1I', 'L1I', 'D1I', 'S1I'])
        elif sigtype == 4:  # B1Q
            obs_types.update(['C1Q', 'L1Q', 'D1Q', 'S1Q'])
        elif sigtype == 8:  # B1C pilot
            obs_types.update(['C1P', 'L1P', 'D1P', 'S1P'])
        elif sigtype == 23:  # B1C data
            obs_types.update(['C1D', 'L1D', 'D1D', 'S1D'])
        elif sigtype == 5:  # B2Q
            obs_types.update(['C7Q', 'L7Q', 'D7Q', 'S7Q'])
        elif sigtype == 17:  # B2I
            obs_types.update(['C2I', 'L2I', 'D2I', 'S2I'])
        elif sigtype == 12:  # B2a Pilot
            obs_types.update(['C7Q', 'L7Q', 'D7Q', 'S7Q'])
        elif sigtype == 28:  # B2a Data
            obs_types.update(['C7D', 'L7D', 'D7D', 'S7D'])
        elif sigtype == 6:  # B3Q
            obs_types.update(['C6Q', 'L6Q', 'D6Q', 'S6Q'])
        elif sigtype == 21:  # B3I
            obs_types.update(['C6I', 'L6I', 'D6I', 'S6I'])
        elif sigtype == 13:  # B2b (I)
            obs_types.update(['C7P', 'L7P', 'D7P', 'S7P'])

    elif sys_char == 'I':  # IRNSS / NavIC
        if sigtype == 6:  # L5 Data
            obs_types.update(['C5A', 'L5A', 'D5A', 'S5A'])
        elif sigtype == 14:  # L5 Pilot
            obs_types.update(['C5C', 'L5C', 'D5C', 'S5C'])

    elif sys_char == 'S':  # SBAS
        if sigtype == 0:  # L1 C/A
            obs_types.update(['C1C', 'L1C', 'D1C', 'S1C'])
        elif sigtype == 6:  # L5I
            obs_types.update(['C5I', 'L5I', 'D5I', 'S5I'])

    return obs_types


def get_baseinfo_position(input_file):
    """
    从 BASEINFOA 提取基站坐标与站号。
    BASEINFOA 数据部分格式（见文档与样例）：
    <status>,<X>,<Y>,<Z>,"<StationId>",<reserved>
    返回: (x, y, z, station_id)
    若不存在，返回 None。
    """
    try:
        import os

        def extract_from_text(text):
            pattern = r'#BASEINFOA[^#]*'
            recs = re.findall(pattern, text, re.DOTALL)
            return recs

        # 先在输入文件中找
        records = []
        try:
            with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
                records = extract_from_text(f.read())
        except Exception:
            records = []

        if not records:
            return None

        # 选择最后一条记录（通常最新），也可优先选择 status==0 的
        chosen = None
        for rec in reversed(records):
            try:
                if ';' not in rec:
                    continue
                _, data_section = rec.split(';', 1)
                data_section = re.sub(r'\*[0-9a-fA-F]+$', '', data_section.strip())
                fields = [field.strip() for field in data_section.split(',')]
                if len(fields) < 5:
                    continue
                status_str = fields[0]
                # 有的为十六进制字符串（如 00000000），容错处理
                status_val = None
                try:
                    status_val = int(status_str, 16)
                except Exception:
                    try:
                        status_val = int(status_str)
                    except Exception:
                        status_val = None
                if status_val is None or status_val != 0:
                    # 状态无效则继续找
                    continue
                x = float(fields[1])
                y = float(fields[2])
                z = float(fields[3])
                station_id = fields[4].strip('"')
                chosen = (x, y, z, station_id)
                break
            except Exception:
                continue

        # 若没有 status==0 的，则退而求其次选择最后一条可解析记录
        if chosen is None:
            rec = records[-1]
            if ';' in rec:
                _, data_section = rec.split(';', 1)
                data_section = re.sub(r'\*[0-9a-fA-F]+$', '', data_section.strip())
                fields = [field.strip() for field in data_section.split(',')]
                if len(fields) >= 5:
                    x = float(fields[1])
                    y = float(fields[2])
                    z = float(fields[3])
                    station_id = fields[4].strip('"')
                    chosen = (x, y, z, station_id)

        return chosen
    except Exception:
        return None

def parse_all_satellites(status_word):
    """
    解析全卫星系统的状态字，返回RINEX 3.02观测类型
    :param status_word: 32位状态字（十六进制）
    :return: dict {卫星系统: [观测类型列表]}
    """
    # 卫星系统映射（bit16-18）
    SAT_SYSTEMS = {
        0: 'G',  # GPS
        1: 'R',  # GLONASS
        2: 'S',  # SBAS
        3: 'E',  # Galileo
        4: 'C',  # BDS
        5: 'J'   # QZSS
    }

    # 解析字段
    sys_bits = (status_word >> 16) & 0x7  # bit16-18: 卫星系统
    # 与 C 代码一致：sigtype 位21-25（5位），L2C 位26
    sigtype = (status_word >> 21) & 0x1F
    l2c = (status_word >> 26) & 0x01
    
    # 获取卫星系统代码
    sys_code = SAT_SYSTEMS.get(sys_bits, None)
    if not sys_code:
        return {}

    # 有效性检查
    carrier_valid = (status_word >> 10) & 0x1  # bit 10: 载波相位有效
    range_valid = (status_word >> 12) & 0x1    # bit 12: 伪距有效
    
    # 基于统一映射生成观测类型
    obs_types = list(determine_obs_types_from_status(status_word, sys_code))

    # 过滤无效数据
    if not carrier_valid:
        obs_types = [t for t in obs_types if not t.startswith(('L', 'D'))]
    if not range_valid:
        obs_types = [t for t in obs_types if not t.startswith('C')]

    return {sys_code: obs_types}

def generate_obs_types_from_detected(detected_obs_types):
    """
    根据实际检测到的观测类型生成RINEX头部的SYS / # / OBS TYPES行
    """
    lines = []
    
    # 按系统顺序排序：G, R, C, E, J, S
    system_order = ['G', 'R', 'C', 'E', 'J', 'S']
    
    for sys_char in system_order:
        if sys_char in detected_obs_types and detected_obs_types[sys_char]:
            # 对观测类型进行排序：按观测类型字母顺序排序 (C, D, L, S)
            obs_types = sorted(list(detected_obs_types[sys_char]), 
                             key=lambda x: (x[0], x[1]))  # 按观测类型+频点排序
            # obs_types = list(detected_obs_types[sys_char])
            
            # 生成RINEX格式的行
            if len(obs_types) <= 8:
                # 所有观测类型都能放在一行
                obs_str = ' '.join(obs_types)
                padding = ' ' * (max(0, 60 - len(f"{sys_char}   {len(obs_types)} {obs_str}")) - 1)
                line = f"{sys_char}   {len(obs_types):>2} {obs_str}{padding}SYS / # / OBS TYPES "
                lines.append(line)
            elif len(obs_types) <= 13:
                # 所有观测类型都能放在一行
                obs_str = ' '.join(obs_types)
                padding = ' ' * max(0, 60 - len(f"{sys_char}   {len(obs_types)} {obs_str}"))
                line = f"{sys_char}   {len(obs_types):>2} {obs_str}{padding}SYS / # / OBS TYPES "
                lines.append(line)
            else:
                # 需要分多行（每行最多13个观测类型）
                for i in range(0, len(obs_types), 13):
                    chunk = obs_types[i:i+13]
                    obs_str = ' '.join(chunk)
                    
                    if i == 0:
                        # 第一行包含系统标识和总数
                        padding = ' ' * max(0, 60 - len(f"{sys_char}   {len(obs_types)} {obs_str}"))
                        line = f"{sys_char}   {len(obs_types)} {obs_str}{padding}SYS / # / OBS TYPES "
                    else:
                        # 后续行只包含观测类型
                        padding = ' ' * max(0, 60 - len(f"       {obs_str}"))
                        line = f"       {obs_str}{padding}SYS / # / OBS TYPES "
                    lines.append(line)
    
    # 如果没有检测到任何观测类型，返回空列表
    if not lines:
        print("警告：未检测到任何观测类型")
        return []
    
    return lines



def parse_multi_obsvbasea_to_rinex(input_file, output_file):
    """
    批处理多个OBSVBASEA数据的解析器
    """
    try:
        # 仅从 BASEINFOA 提取基站坐标与站号（严格要求）
        baseinfo = get_baseinfo_position(input_file)
        if baseinfo is None:
            print("错误：未找到 BASEINFOA 记录，无法获取基站坐标与站号。")
            sys.exit(1)
        base_x, base_y, base_z, station_id = baseinfo
        print(f"从 BASEINFOA 读取基站坐标: X={base_x:.4f}, Y={base_y:.4f}, Z={base_z:.4f}, StationID={station_id}")
        
        # 读取输入文件
        with open(input_file, 'r') as f:
            content = f.read()
        
        # 查找所有的OBSVBASEA记录
        obsvbasea_pattern = r'#OBSVBASEA[^#]*'
        obsvbasea_records = re.findall(obsvbasea_pattern, content, re.DOTALL)
        
        if not obsvbasea_records:
            print("未找到任何#OBSVBASEA记录")
            return
        
        print(f"找到 {len(obsvbasea_records)} 个OBSVBASEA记录")
        
        # 初始化检测到的观测类型收集器
        detected_obs_types = {}
        
        # 解析所有记录
        all_epochs = []
        for i, record in enumerate(obsvbasea_records):
            print(f"正在处理第 {i+1}/{len(obsvbasea_records)} 个OBSVBASEA记录...")
            epoch_data = parse_obsvbasea_to_rinex(record.strip(), None, detected_obs_types)
            if epoch_data:
                all_epochs.append(epoch_data)
        
        if not all_epochs:
            print("没有成功解析任何OBSVBASEA记录")
            return
        
        print(f"成功解析了 {len(all_epochs)} 个历元的数据")
        
        # 根据实际检测到的观测类型生成头部
        print("检测到的观测类型:")
        for sys_char, obs_types in detected_obs_types.items():
            print(f"  {sys_char}: {sorted(list(obs_types))}")
        
        # 根据实际检测到的观测类型生成头部
        print("根据实际检测到的观测类型生成头部:")
        obs_type_lines = generate_obs_types_from_detected(detected_obs_types)
        if not obs_type_lines:
            print("错误：未能从数据中检测到任何有效的观测类型，无法生成头部。")
            return
        
        # 获取时间范围
        first_epoch = all_epochs[0]
        last_epoch = all_epochs[-1]
        
        # 固定文件头（流动站版本 - 使用计算得到的坐标和实际检测到的观测类型）
        header = [
            "     3.02           OBSERVATION DATA    M                   RINEX VERSION / TYPE",
            "G = GPS,  R = GLONASS,  E = GALILEO,  C = BDS,  M = MIXED   COMMENT             ",
            "UnicoreConvert      Unicore             20250729 100837 UTC PGM / RUN BY / DATE",
            f"{station_id:<60}MARKER NAME         ",
            "GEODETIC                                                    MARKER TYPE         ",
            "Unicore-001         Unicore HPL EVT                         OBSERVER / AGENCY   ",
            "Unicore#001         GEODETIC            Unicore UB4B0       REC # / TYPE / VERS ",
            "Ant001              BASE                                    ANT # / TYPE        ",
            f" {base_x:13.4f} {base_y:13.4f} {base_z:13.4f}                  APPROX POSITION XYZ ",
            "        0.0000        0.0000        0.0000                  ANTENNA: DELTA H/E/N"
        ]
        
        # 添加实际检测到的观测类型
        header.extend(obs_type_lines)
        
        # 添加剩余的头部信息
        header.extend([
            f"  {first_epoch['year']:4d}  {first_epoch['month']:4d}  {first_epoch['day']:4d}  {first_epoch['hour']:4d}  {first_epoch['minute']:4d}  {first_epoch['second']:6.1f}000000     GPS        TIME OF FIRST OBS    ",
            f"  {last_epoch['year']:4d}  {last_epoch['month']:4d}  {last_epoch['day']:4d}  {last_epoch['hour']:4d}  {last_epoch['minute']:4d}  {last_epoch['second']:6.1f}000000     GPS        TIME OF LAST OBS     ",
            "     0                                                      RCV CLOCK OFFS APPL  ",
            "                                                            END OF HEADER        "
        ])
        
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
                f.write(f"> {epoch['year']:4d} {epoch['month']:02d} {epoch['day']:02d} {epoch['hour']:02d} {epoch['minute']:02d}{epoch['second']:11.7f}  0 {len(sat_order)}\n")
                
                # 按排序后的顺序写入卫星数据
                for sat_id in sat_order:
                    observations = satellite_data[sat_id]
                    line = f"{sat_id}"
                    
                    for i, obs in enumerate(observations):
                        # 格式化观测值，精确匹配参考文件格式
                        if i == 0:
                            # 第一组观测值的格式
                            psr_str = f"{obs['psr']:14.3f}"
                            adr_str = f"{obs['adr']:14.3f}"
                            cn0_str = f"{obs['cn0']:14.3f}"
                            line += f"{psr_str}  {adr_str}  {cn0_str}"
                        else:
                            # 后续观测值的格式
                            psr_str = f"{obs['psr']:14.3f}"
                            adr_str = f"{obs['adr']:14.3f}"
                            cn0_str = f"{obs['cn0']:14.3f}"
                            line += f"  {psr_str}  {adr_str}  {cn0_str}"
                    
                    f.write(line + "  \n")
        
        print(f"成功创建RINEX文件: {output_file}")
        print(f"包含 {len(all_epochs)} 个历元的观测数据")
                    
    except Exception as e:
        print(f"Error processing multi OBSVBASEA data: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) != 3:
        print("Usage: python RINEX_Multi_Rover_OBS_Original.py <input_file> <output_file>")
        sys.exit(1)
        
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    try:
        print(f"Converting {input_file} to RINEX 3.02 format...")
        parse_multi_obsvbasea_to_rinex(input_file, output_file)
        
    except FileNotFoundError:
        print(f"Error: Input file {input_file} not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
