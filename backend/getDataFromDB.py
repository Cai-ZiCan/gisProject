"""
数据库查询工具模块
提供与PostGIS数据库交互的各种查询函数
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

# 数据库配置
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": "5432",
    "database": "deformation_db",
    "user": "postgres",
    "password": "123456"
}

def get_db_connection():
    """获取数据库连接"""
    return psycopg2.connect(**DB_CONFIG)


def get_deformation_raster_by_layer(layer_name):
    """
    根据图层名称获取形变栅格数据的RID列表
    
    参数:
        layer_name: 图层名称，如 'v_mean_cropped_15_25'
        
    返回:
        包含栅格RID的列表，如果图层不存在则返回空列表
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 首先验证图层是否存在于元数据表中
            cur.execute("""
                SELECT layer_name FROM deformation_layer_info 
                WHERE layer_name = %s
            """, (layer_name,))
            
            if not cur.fetchone():
                logging.warning(f"Layer {layer_name} not found in deformation_layer_info")
                return []
            
            # 获取该图层的所有栅格瓦片RID
            cur.execute("""
                SELECT rid FROM annual_defo_raster 
                WHERE layer_name = %s
                ORDER BY rid
            """, (layer_name,))
            
            rows = cur.fetchall()
            return [row['rid'] for row in rows]
            
    except Exception as e:
        logging.error(f"Error fetching deformation raster: {e}")
        return []
    finally:
        if conn:
            conn.close()


def extract_deformation_values_at_points(layer_name, mining_layer, active_only=False, threshold=10.0):
    """
    提取矿井/油井点位置的形变值，并筛选出绝对值超过阈值的点
    
    参数:
        layer_name: 形变图层名称
        mining_layer: 矿井图层名称 ('oil_well_info' 或 'mine_info')
        active_only: 是否仅包含活跃状态
        threshold: 形变绝对值阈值
        
    返回:
        包含GeoJSON格式的特征列表
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 验证图层名称
            if mining_layer not in ['oil_well_info', 'mine_info']:
                raise ValueError(f"Invalid mining layer: {mining_layer}")
            
            # 构建SQL查询
            if mining_layer == 'oil_well_info':
                sql = """
                    SELECT 
                        o.well_id as id,
                        o.mine_api,
                        o.mine_name,
                        o.mine_type,
                        o.extraction_status,
                        o.well_depth_ft,
                        ST_X(o.geom) as longitude,
                        ST_Y(o.geom) as latitude,
                        ST_AsGeoJSON(o.geom) as geom_json,
                        ST_Value(r.rast, o.geom) as deformation_value
                    FROM oil_well_info o
                    CROSS JOIN annual_defo_raster r
                    WHERE o.geom IS NOT NULL
                        AND r.layer_name = %s
                        AND ST_Intersects(r.rast, o.geom)
                """
                params = [layer_name]
                
                if active_only:
                    sql += " AND o.extraction_status = 'Active'"
                
                # 添加阈值筛选（使用绝对值）
                sql += " AND ABS(ST_Value(r.rast, o.geom)) > %s"
                params.append(threshold)
                
            else:  # mine_info
                sql = """
                    SELECT 
                        m.mine_id as id,
                        m.mine_name,
                        m.mine_type,
                        m.mine_level,
                        m.extraction_status,
                        m.longitude,
                        m.latitude,
                        ST_AsGeoJSON(ST_MakePoint(m.longitude, m.latitude)) as geom_json,
                        ST_Value(r.rast, ST_SetSRID(ST_MakePoint(m.longitude, m.latitude), 4326)) as deformation_value
                    FROM mine_info m
                    CROSS JOIN annual_defo_raster r
                    WHERE r.layer_name = %s
                        AND ST_Intersects(r.rast, ST_SetSRID(ST_MakePoint(m.longitude, m.latitude), 4326))
                """
                params = [layer_name]
                
                if active_only:
                    sql += " AND m.extraction_status = 'Active'"
                
                # 添加阈值筛选（使用绝对值）
                sql += " AND ABS(ST_Value(r.rast, ST_SetSRID(ST_MakePoint(m.longitude, m.latitude), 4326))) > %s"
                params.append(threshold)
            
            cur.execute(sql, params)
            rows = cur.fetchall()
            
            features = []
            for row in rows:
                # 跳过形变值为NULL的记录
                if row['deformation_value'] is None:
                    continue
                    
                feature = {
                    "type": "Feature",
                    "properties": {
                        "id": row['id'],
                        "name": row['mine_name'],
                        "status": row['extraction_status'],
                        "deformation_value": float(row['deformation_value'])
                    },
                    "geometry": eval(row['geom_json']) if row['geom_json'] else None
                }
                
                # 添加额外的属性
                if mining_layer == 'oil_well_info':
                    feature['properties']['api'] = row['mine_api']
                    feature['properties']['type'] = row['mine_type']
                    feature['properties']['depth_ft'] = row['well_depth_ft']
                else:
                    feature['properties']['type'] = row['mine_type']
                    feature['properties']['level'] = row['mine_level']
                
                features.append(feature)
            
            return features
            
    except Exception as e:
        logging.error(f"Error extracting deformation values: {e}")
        raise
    finally:
        if conn:
            conn.close()


def extract_deformation_values_with_buffer(layer_name, mining_layer, active_only=False, 
                                          threshold=10.0, buffer_distance=1000, buffer_unit='meters'):
    """
    在缓冲区内提取形变统计值，筛选出最大绝对值超过阈值的点
    
    参数:
        layer_name: 形变图层名称
        mining_layer: 矿井图层名称
        active_only: 是否仅包含活跃状态
        threshold: 形变绝对值阈值
        buffer_distance: 缓冲区距离
        buffer_unit: 缓冲区单位 ('meters', 'kilometers')
        
    返回:
        包含GeoJSON格式的特征列表（带缓冲区形变统计）
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 验证图层名称
            if mining_layer not in ['oil_well_info', 'mine_info']:
                raise ValueError(f"Invalid mining layer: {mining_layer}")
            
            # 转换距离单位
            if buffer_unit == 'kilometers':
                buffer_distance_m = buffer_distance * 1000
            else:
                buffer_distance_m = buffer_distance
            
            # 构建SQL查询（使用缓冲区统计）
            if mining_layer == 'oil_well_info':
                sql = """
                    WITH buffered AS (
                        SELECT 
                            o.well_id,
                            o.mine_api,
                            o.mine_name,
                            o.mine_type,
                            o.extraction_status,
                            o.well_depth_ft,
                            o.geom,
                            ST_Buffer(o.geom::geography, %s)::geometry as buffer_geom
                        FROM oil_well_info o
                        WHERE o.geom IS NOT NULL
                """
                
                if active_only:
                    sql += " AND o.extraction_status = 'Active'"
                
                sql += """
                    ),
                    deform_stats AS (
                        SELECT 
                            b.well_id,
                            b.mine_api,
                            b.mine_name,
                            b.mine_type,
                            b.extraction_status,
                            b.well_depth_ft,
                            b.geom,
                            ST_Value(r.rast, b.geom) as point_deformation,
                            (ST_SummaryStats(ST_Clip(r.rast, b.buffer_geom, true))).mean as buffer_mean,
                            (ST_SummaryStats(ST_Clip(r.rast, b.buffer_geom, true))).max as buffer_max,
                            (ST_SummaryStats(ST_Clip(r.rast, b.buffer_geom, true))).min as buffer_min
                        FROM buffered b
                        CROSS JOIN annual_defo_raster r
                        WHERE r.layer_name = %s
                            AND ST_Intersects(r.rast, b.buffer_geom)
                        GROUP BY b.well_id, b.mine_api, b.mine_name, b.mine_type, 
                                 b.extraction_status, b.well_depth_ft, b.geom, r.rast
                    )
                    SELECT 
                        well_id as id,
                        mine_api,
                        mine_name,
                        mine_type,
                        extraction_status,
                        well_depth_ft,
                        ST_AsGeoJSON(geom) as geom_json,
                        point_deformation,
                        buffer_mean,
                        buffer_max,
                        buffer_min,
                        GREATEST(ABS(buffer_max), ABS(buffer_min)) as max_abs_deformation
                    FROM deform_stats
                    WHERE GREATEST(ABS(buffer_max), ABS(buffer_min)) > %s
                """
                
                params = [buffer_distance_m, layer_name, threshold]
                
            else:  # mine_info
                sql = """
                    WITH buffered AS (
                        SELECT 
                            m.mine_id,
                            m.mine_name,
                            m.mine_type,
                            m.mine_level,
                            m.extraction_status,
                            m.longitude,
                            m.latitude,
                            ST_SetSRID(ST_MakePoint(m.longitude, m.latitude), 4326) as geom,
                            ST_Buffer(ST_SetSRID(ST_MakePoint(m.longitude, m.latitude), 4326)::geography, %s)::geometry as buffer_geom
                        FROM mine_info m
                """
                
                if active_only:
                    sql += " WHERE m.extraction_status = 'Active'"
                
                sql += """
                    ),
                    deform_stats AS (
                        SELECT 
                            b.mine_id,
                            b.mine_name,
                            b.mine_type,
                            b.mine_level,
                            b.extraction_status,
                            b.geom,
                            ST_Value(r.rast, b.geom) as point_deformation,
                            (ST_SummaryStats(ST_Clip(r.rast, b.buffer_geom, true))).mean as buffer_mean,
                            (ST_SummaryStats(ST_Clip(r.rast, b.buffer_geom, true))).max as buffer_max,
                            (ST_SummaryStats(ST_Clip(r.rast, b.buffer_geom, true))).min as buffer_min
                        FROM buffered b
                        CROSS JOIN annual_defo_raster r
                        WHERE r.layer_name = %s
                            AND ST_Intersects(r.rast, b.buffer_geom)
                        GROUP BY b.mine_id, b.mine_name, b.mine_type, b.mine_level,
                                 b.extraction_status, b.geom, r.rast
                    )
                    SELECT 
                        mine_id as id,
                        mine_name,
                        mine_type,
                        mine_level,
                        extraction_status,
                        ST_AsGeoJSON(geom) as geom_json,
                        point_deformation,
                        buffer_mean,
                        buffer_max,
                        buffer_min,
                        GREATEST(ABS(buffer_max), ABS(buffer_min)) as max_abs_deformation
                    FROM deform_stats
                    WHERE GREATEST(ABS(buffer_max), ABS(buffer_min)) > %s
                """
                
                params = [buffer_distance_m, layer_name, threshold]
            
            cur.execute(sql, params)
            rows = cur.fetchall()
            
            features = []
            for row in rows:
                feature = {
                    "type": "Feature",
                    "properties": {
                        "id": row['id'],
                        "name": row['mine_name'],
                        "status": row['extraction_status'],
                        "deformation_value": float(row['point_deformation']) if row['point_deformation'] else None,
                        "buffer_mean": float(row['buffer_mean']) if row['buffer_mean'] else None,
                        "buffer_max": float(row['buffer_max']) if row['buffer_max'] else None,
                        "buffer_min": float(row['buffer_min']) if row['buffer_min'] else None,
                        "max_abs_deformation": float(row['max_abs_deformation']) if row['max_abs_deformation'] else None
                    },
                    "geometry": eval(row['geom_json']) if row['geom_json'] else None
                }
                
                # 添加额外的属性
                if mining_layer == 'oil_well_info':
                    feature['properties']['api'] = row['mine_api']
                    feature['properties']['type'] = row['mine_type']
                    feature['properties']['depth_ft'] = row['well_depth_ft']
                else:
                    feature['properties']['type'] = row['mine_type']
                    feature['properties']['level'] = row['mine_level']
                
                features.append(feature)
            
            return features
            
    except Exception as e:
        logging.error(f"Error extracting deformation with buffer: {e}")
        raise
    finally:
        if conn:
            conn.close()
