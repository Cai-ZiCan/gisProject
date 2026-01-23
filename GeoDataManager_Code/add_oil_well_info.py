"""
油井数据导入脚本
用于从Shapefile读取油井数据并导入到PostgreSQL数据库中

功能特性：
1. 严格坐标系验证（必须为EPSG:3857，否则终止程序）
2. 自动坐标转换（EPSG:3857 → EPSG:4326）
3. 字段映射与数据转换
4. API冲突时覆盖更新（UPSERT逻辑）

字段映射关系：
- mine_name ← LeaseName 或 FieldName (优先LeaseName)
- mine_api ← APINumber (UNIQUE主键)
- mine_type ← FieldName
- mine_level ← DistrictNu
- longitude/latitude ← Longitude/Latitude (转换为EPSG:4326)
- well_depth_ft ← WellDepthA (转换为浮点数，NULL则存NULL)
- extraction_status ← WellStatus (A→Active, I/P→Stopped)
- extraction_start_time ← SPUDDate
- extraction_end_time ← AbandonedD
- remarks ← Comments + NLA_URL
"""

import psycopg2
import geopandas as gpd
from datetime import datetime
import re

# ========================================
# 数据库配置
# ========================================
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": "5432",
    "database": "deformation_db",  # 根据实际情况修改数据库名
    "user": "postgres",
    "password": "123456"
}

# ========================================
# Shapefile路径配置
# ========================================
# 请修改为您的实际Shapefile路径
SHP_FILE_PATH = r"D:\\GIS\\GISwork_DATA\\CourseDesign\\LosAngle_oil_gas\\cropped_oil_wells.shp"

# 目标坐标系（可配置）
TARGET_EPSG = 4326  # WGS84经纬度坐标系
SOURCE_EPSG = 3857  # Web Mercator投影坐标系（严格要求）


# ========================================
# 坐标系验证函数
# ========================================
def check_crs_strict(gdf):
    """
    严格验证坐标系是否为EPSG:3857
    如果不匹配则抛出异常并终止程序
    
    Args:
        gdf: GeoDataFrame对象
        
    Raises:
        ValueError: 当坐标系不是EPSG:3857时
    """
    if gdf.crs is None:
        raise ValueError(
            "错误：Shapefile没有定义坐标系统！\n"
            "要求：数据必须使用EPSG:3857坐标系。"
        )
    
    crs_epsg = gdf.crs.to_epsg()
    
    if crs_epsg != SOURCE_EPSG:
        raise ValueError(
            f"错误：坐标系不匹配！\n"
            f"期望坐标系：EPSG:{SOURCE_EPSG} (Web Mercator)\n"
            f"实际坐标系：EPSG:{crs_epsg}\n"
            f"程序已终止。请使用正确坐标系的数据或先进行坐标转换。"
        )
    
    print(f"[验证通过] 坐标系：EPSG:{crs_epsg} (Web Mercator)")


# ========================================
# 数据转换函数
# ========================================
def map_well_status(well_status):
    """
    映射WellStatus字段到extraction_status
    
    映射规则：
    - A → Active
    - I, P → Stopped
    - 其他 → 原值或 Unknown
    
    Args:
        well_status: 原始井状态值
        
    Returns:
        str: 映射后的状态值
    """
    if well_status is None or well_status == '':
        return 'Unknown'
    
    status_upper = str(well_status).strip().upper()
    
    if status_upper == 'A':
        return 'Active'
    elif status_upper in ['I', 'P']:
        return 'Stopped'
    else:
        # 保留原值以便后续分析
        return status_upper


def parse_date(date_value):
    """
    解析日期字段，转换为TIMESTAMP格式
    支持多种日期格式
    
    Args:
        date_value: 原始日期值
        
    Returns:
        datetime or None: 解析后的日期对象
    """
    if date_value is None or date_value == '':
        return None
    
    try:
        # 检查是否是pandas的NaT值
        import pandas as pd
        if pd.isna(date_value):
            return None
        
        # 如果已经是datetime对象，直接返回
        if isinstance(date_value, datetime):
            return date_value
        
        # 处理pandas的Timestamp对象
        if hasattr(date_value, 'to_pydatetime'):
            return date_value.to_pydatetime()
        
        # 尝试多种日期格式
        if isinstance(date_value, str):
            date_value = date_value.strip()
            # 尝试常见格式
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y/%m/%d', '%d-%m-%Y', '%Y%m%d']:
                try:
                    return datetime.strptime(date_value, fmt)
                except ValueError:
                    continue
    except Exception as e:
        print(f"[警告] 日期解析失败: {date_value}, 错误: {e}")
    
    return None


def get_mine_name(row):
    """
    获取油井名称，优先使用LeaseName，若为空则使用FieldName
    
    Args:
        row: GeoDataFrame的一行数据
        
    Returns:
        str: 油井名称
    """
    import pandas as pd
    
    lease_name = row.get('LeaseName', '')
    field_name = row.get('FieldName', '')
    
    # 处理pandas NaN值和float类型
    if pd.notna(lease_name) and lease_name != '':
        lease_name = str(lease_name).strip()
        if lease_name:
            return lease_name
    
    if pd.notna(field_name) and field_name != '':
        field_name = str(field_name).strip()
        if field_name:
            return field_name
    
    return 'Unknown'


def get_remarks(row):
    """
    合并Comments和NLA_URL字段作为备注
    
    Args:
        row: GeoDataFrame的一行数据
        
    Returns:
        str or None: 合并后的备注信息
    """
    import pandas as pd
    
    comments = row.get('Comments', '')
    nla_url = row.get('NLA_URL', '')
    
    # 处理pandas NaN值和float类型
    if pd.notna(comments) and comments != '':
        comments = str(comments).strip()
    else:
        comments = ''
    
    if pd.notna(nla_url) and nla_url != '':
        nla_url = str(nla_url).strip()
    else:
        nla_url = ''
    
    remarks_parts = []
    if comments:
        remarks_parts.append(f"Comments: {comments}")
    if nla_url:
        remarks_parts.append(f"URL: {nla_url}")
    
    return ' | '.join(remarks_parts) if remarks_parts else None


def parse_well_depth(depth_value):
    """
    解析WellDepthA字段，转换为浮点数
    
    处理逻辑：
    - NULL或空字符串 → 返回None
    - 包含单位（如"1234 ft"）→ 提取数字部分
    - 纯数字字符串 → 转换为浮点数
    - 转换失败 → 返回None（不抛异常）
    
    Args:
        depth_value: 原始井深值
        
    Returns:
        float or None: 转换后的井深（英尺）
    """
    if depth_value is None or depth_value == '':
        return None
    
    try:
        # 如果已经是数字类型，直接返回
        if isinstance(depth_value, (int, float)):
            return float(depth_value)
        
        # 字符串处理
        if isinstance(depth_value, str):
            depth_str = depth_value.strip()
            
            # 提取所有数字和小数点
            # 使用正则表达式提取数字部分（包括小数）
            match = re.search(r'[\d.]+', depth_str)
            if match:
                number_str = match.group(0)
                return float(number_str)
    
    except Exception as e:
        print(f"[警告] 井深转换失败: {depth_value}, 错误: {e}")
    
    return None


# ========================================
# 数据库操作函数
# ========================================
def insert_oil_well_info(row):
    """
    向oil_well_info表中插入单条油井数据
    调用存储过程 upsert_oil_well_info
    
    Args:
        row: GeoDataFrame的一行数据
        
    Returns:
        bool: 插入成功返回True，失败返回False
    """
    conn = None
    mine_api = None
    
    try:
        # ========================================
        # 1. 字段映射和转换
        # ========================================
        mine_api = str(row.get('APINumber', '')).strip()
        if not mine_api:
            print(f"[警告] 跳过无效记录：APINumber为空")
            return False
        
        import pandas as pd
        
        mine_name = get_mine_name(row)
        
        # 处理mine_type字段
        mine_type_val = row.get('FieldName', '')
        if pd.notna(mine_type_val) and mine_type_val != '':
            mine_type = str(mine_type_val).strip()
        else:
            mine_type = None
        
        # 处理mine_level字段
        mine_level_val = row.get('DistrictNu', '')
        if pd.notna(mine_level_val) and mine_level_val != '':
            mine_level = str(mine_level_val).strip()
        else:
            mine_level = None
        
        # 获取经纬度（已转换为EPSG:4326）
        if hasattr(row, 'geometry') and row.geometry is not None:
            longitude = round(row.geometry.x, 6)
            latitude = round(row.geometry.y, 6)
        else:
            # 备用方案：从字段中读取（如果存在）
            longitude = float(row.get('Longitude', 0))
            latitude = float(row.get('Latitude', 0))
        
        # 井深转换
        well_depth_ft = parse_well_depth(row.get('WellDepthA'))
        
        # 状态映射
        extraction_status = map_well_status(row.get('WellStatus'))
        
        # 日期解析
        extraction_start_time = parse_date(row.get('SPUDDate'))
        extraction_end_time = parse_date(row.get('AbandonedD'))
        
        # 备注合并
        remarks = get_remarks(row)
        
        # ========================================
        # 2. 连接数据库并执行存储过程
        # ========================================
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # 执行存储过程
        sql = """
            SELECT upsert_oil_well_info(
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            );
        """
        cur.execute(sql, (
            mine_api, mine_name, mine_type, mine_level,
            longitude, latitude, well_depth_ft, extraction_status,
            extraction_start_time, extraction_end_time, remarks
        ))
        
        conn.commit()
        
        # 获取NOTICE信息（来自存储过程）
        notices = conn.notices
        for notice in notices:
            print(f"  [数据库通知] {notice.strip()}")
        
        return True
        
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"[错误] 插入失败 (API: {mine_api}): {error}")
        return False
    finally:
        if conn is not None:
            conn.close()


# ========================================
# 批量导入函数
# ========================================
def batch_import_from_shapefile(shp_path):
    """
    批量从Shapefile导入油井数据
    
    流程：
    1. 读取Shapefile
    2. 严格验证坐标系（必须为EPSG:3857）
    3. 转换坐标系到EPSG:4326
    4. 逐条插入数据
    5. 统计成功/失败数量
    
    Args:
        shp_path: Shapefile文件路径
    """
    try:
        # ========================================
        # 1. 读取Shapefile
        # ========================================
        print(f"\n{'='*60}")
        print(f"[步骤1] 读取Shapefile")
        print(f"{'='*60}")
        print(f"文件路径: {shp_path}")
        
        gdf = gpd.read_file(shp_path)
        print(f"[成功] 读取到 {len(gdf)} 条记录")
        
        # ========================================
        # 2. 严格验证坐标系
        # ========================================
        print(f"\n{'='*60}")
        print(f"[步骤2] 坐标系验证")
        print(f"{'='*60}")
        
        check_crs_strict(gdf)
        
        # ========================================
        # 3. 转换坐标系
        # ========================================
        print(f"\n{'='*60}")
        print(f"[步骤3] 坐标系转换")
        print(f"{'='*60}")
        print(f"转换: EPSG:{SOURCE_EPSG} → EPSG:{TARGET_EPSG}")
        
        gdf = gdf.to_crs(epsg=TARGET_EPSG)
        print(f"[成功] 坐标系已转换为 EPSG:{TARGET_EPSG}")
        
        # ========================================
        # 4. 显示字段信息
        # ========================================
        print(f"\n{'='*60}")
        print(f"[步骤4] 数据字段信息")
        print(f"{'='*60}")
        print(f"字段列表: {list(gdf.columns)}")
        print(f"数据类型:\n{gdf.dtypes}")
        
        # ========================================
        # 5. 批量插入数据
        # ========================================
        print(f"\n{'='*60}")
        print(f"[步骤5] 批量导入数据")
        print(f"{'='*60}")
        
        success_count = 0
        fail_count = 0
        
        # 逐条插入
        for idx, row in gdf.iterrows():
            print(f"\n[进度] 处理第 {idx + 1}/{len(gdf)} 条记录...")
            if insert_oil_well_info(row):
                success_count += 1
                print(f"  [✓] 成功")
            else:
                fail_count += 1
                print(f"  [✗] 失败")
        
        # ========================================
        # 6. 显示统计结果
        # ========================================
        print(f"\n{'='*60}")
        print(f"[完成] 导入统计")
        print(f"{'='*60}")
        print(f"  ✓ 成功: {success_count} 条")
        print(f"  ✗ 失败: {fail_count} 条")
        print(f"  ∑ 总计: {len(gdf)} 条")
        print(f"  成功率: {success_count/len(gdf)*100:.2f}%")
        print(f"{'='*60}\n")
        
    except ValueError as ve:
        # 坐标系验证失败（严格模式）
        print(f"\n{'='*60}")
        print(f"[严重错误] 坐标系验证失败")
        print(f"{'='*60}")
        print(f"{ve}")
        print(f"{'='*60}\n")
        raise  # 重新抛出异常，终止程序
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"[错误] Shapefile读取或处理失败")
        print(f"{'='*60}")
        print(f"错误信息: {e}")
        print(f"{'='*60}\n")
        raise


# ========================================
# 主程序入口
# ========================================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("油井数据导入程序 v1.0")
    print("="*60)
    print(f"数据库: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    print(f"用户: {DB_CONFIG['user']}")
    print(f"目标坐标系: EPSG:{TARGET_EPSG}")
    print(f"源坐标系要求: EPSG:{SOURCE_EPSG} (严格验证)")
    print("="*60)
    
    try:
        # 批量导入
        batch_import_from_shapefile(SHP_FILE_PATH)
        
        print("\n[程序结束] 所有操作已完成！\n")
        
    except KeyboardInterrupt:
        print("\n\n[中断] 用户取消操作\n")
    except Exception as e:
        print(f"\n[失败] 程序异常终止: {e}\n")
