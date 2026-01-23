from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
import json
import logging
from bufferAnalysis import BufferAnalysisTool
from getDataFromDB import (
    extract_deformation_values_at_points,
    extract_deformation_values_with_buffer,
    get_deformation_raster_by_layer
)

app = Flask(__name__)
CORS(app, supports_credentials=True)

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": "5432",
    "database": "deformation_db",
    "user": "postgres",
    "password": "123456"
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)
# API: 获取 GPS 形变点数据，返回 GeoJSON 格式
@app.route('/api/metadata', methods=['GET'])
def get_metadata():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 优化 1: 在 SQL 中使用 AS 给字段起别名，确保 row['name'] 能取到值
            # 优化 2: 确保 ST_AsGeoJSON 的结果有一个明确的列名，方便后续 json.loads
            sql = """
                SELECT 
                    id, 
                    station_name AS name, 
                    deformation_mm,
                    ST_AsGeoJSON(ST_Transform(geom, 4326)) AS geom_json 
                FROM gps_points;
            """
            cur.execute(sql)
            rows = cur.fetchall()
            
            # 优化 3: 构造标准的 GeoJSON 格式
            features = []
            for row in rows:
                features.append({
                    "type": "Feature",
                    "properties": {
                        "id": row['id'],
                        "name": row['name'],
                        "deformation": row['deformation_mm']
                    },
                    "geometry": json.loads(row['geom_json']) if row['geom_json'] else None
                })
            
            results = {
                "type": "FeatureCollection",
                "features": features
            }
            
            return jsonify(results)
            
    except Exception as e:
        logging.error(f"Database Error: {e}") # 使用 logging 代替 print 更好
        return jsonify({"error": "数据库查询失败", "details": str(e)}), 500
    finally:
        if conn:
            conn.close()

# API: 获取指定图层的详细元数据
@app.route('/api/layer-metadata/<layer_name>', methods=['GET'])
def get_layer_metadata(layer_name):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = "SELECT * FROM deformation_layer_info WHERE layer_name = %s"
            cur.execute(sql, (layer_name,))
            row = cur.fetchone()
            
            if row:
                return jsonify(row)
            else:
                return jsonify({"error": "Layer not found"}), 404
    except Exception as e:
        logging.error(f"Error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()
# API: 获取矿区风险点数据，返回 GeoJSON 格式
@app.route('/api/analysis/mining-risk', methods=['GET'])
def get_mining_risk():
    """
    获取矿井/油井风险数据
    参数:
        - layer: 图层名称 (mine_info 或 oil_well_info)，默认 mine_info
        - active_only: 是否仅返回活跃状态，true/false，默认 false
    """
    conn = None
    try:
        # 获取参数
        layer_name = request.args.get('layer', 'mine_info')
        active_only = request.args.get('active_only', 'false').lower() == 'true'
        
        # 验证图层名称（防止SQL注入）
        allowed_layers = ['mine_info', 'oil_well_info']
        if layer_name not in allowed_layers:
            return jsonify({"error": "Invalid layer name"}), 400
        
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 根据图层类型构建不同的查询
            if layer_name == 'mine_info':
                sql = """
                    SELECT 
                        mine_id, mine_name, mine_type, mine_level, 
                        longitude, latitude, extraction_status,
                        ST_AsGeoJSON(ST_MakePoint(longitude, latitude)) as geom_json
                    FROM mine_info
                    WHERE 1=1
                """
                if active_only:
                    sql += " AND extraction_status = 'Active'"
                
                cur.execute(sql)
                rows = cur.fetchall()
                
                features = []
                for row in rows:
                    features.append({
                        "type": "Feature",
                        "properties": {
                            "id": row['mine_id'],
                            "name": row['mine_name'],
                            "type": row['mine_type'],
                            "level": row['mine_level'],
                            "status": row['extraction_status']
                        },
                        "geometry": json.loads(row['geom_json']) if row['geom_json'] else None
                    })
                    
            else:  # oil_well_info
                sql = """
                    SELECT 
                        well_id, mine_api, mine_name, mine_type, mine_level,
                        extraction_status, well_depth_ft, longitude, latitude,
                        ST_AsGeoJSON(geom) as geom_json
                    FROM oil_well_info
                    WHERE geom IS NOT NULL
                """
                if active_only:
                    sql += " AND extraction_status = 'Active'"
                
                cur.execute(sql)
                rows = cur.fetchall()
                
                features = []
                for row in rows:
                    features.append({
                        "type": "Feature",
                        "properties": {
                            "id": row['well_id'],
                            "api": row['mine_api'],
                            "name": row['mine_name'],
                            "type": row['mine_type'],
                            "status": row['extraction_status'],
                            "depth_ft": row['well_depth_ft']
                        },
                        "geometry": json.loads(row['geom_json']) if row['geom_json'] else None
                    })
            
            return jsonify({
                "type": "FeatureCollection",
                "features": features,
                "count": len(features)
            })
            
    except Exception as e:
        logging.error(f"Error fetching mining risk: {e}")
        # 如果表不存在，返回空集合而不是500，以免前端报错太难看
        return jsonify({"type": "FeatureCollection", "features": [], "count": 0})
    
    finally:
        if conn: conn.close()

# API: 获取油井点位数据，返回 GeoJSON 格式，支持 BBOX 筛选
@app.route('/api/oil-wells', methods=['GET'])
def get_oil_wells():
    """
    获取油井信息表的数据，支持 bbox 参数筛选范围
    参数: bbox=minx,miny,maxx,maxy (EPSG:4326)
    返回: GeoJSON 格式
    """
    conn = None
    try:
        conn = get_db_connection()
        bbox = request.args.get('bbox')
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 基础 SQL
            base_sql = """
                SELECT 
                    well_id, 
                    mine_api, 
                    mine_name, 
                    mine_type, 
                    mine_level,
                    extraction_status, 
                    well_depth_ft,
                    longitude,
                    latitude,
                    ST_AsGeoJSON(geom) as geom_json
                FROM oil_well_info
                WHERE geom IS NOT NULL
            """
            
            params = []
            
            # 如果有 BBOX 参数，增加空间查询条件
            if bbox:
                try:
                    # bbox 格式应为 minx,miny,maxx,maxy
                    coords = [float(x) for x in bbox.split(',')]
                    if len(coords) == 4:
                        # 使用 && 操作符进行包围盒相交查询，利用空间索引
                        base_sql += " AND geom && ST_MakeEnvelope(%s, %s, %s, %s, 4326)"
                        params.extend(coords)
                except ValueError:
                    logging.warning(f"Invalid bbox parameter: {bbox}")
            
            # 添加排序
            base_sql += " ORDER BY well_id"
            
            # 执行查询
            cur.execute(base_sql, tuple(params))
            rows = cur.fetchall()
            
            features = []
            for row in rows:
                features.append({
                    "type": "Feature",
                    "properties": {
                        "id": row['well_id'],
                        "api": row['mine_api'],
                        "name": row['mine_name'],
                        "type": row['mine_type'],
                        "level": row['mine_level'],
                        "status": row['extraction_status'],
                        "depth_ft": float(row['well_depth_ft']) if row['well_depth_ft'] else None,
                        "longitude": float(row['longitude']) if row['longitude'] else None,
                        "latitude": float(row['latitude']) if row['latitude'] else None
                    },
                    "geometry": json.loads(row['geom_json']) if row['geom_json'] else None
                })
            
            return jsonify({
                "type": "FeatureCollection",
                "count": len(features),
                "features": features
            })
            
    except Exception as e:
        logging.error(f"Error fetching oil wells: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

# API: 获取油井统计信息
@app.route('/api/oil-wells/stats', methods=['GET'])
def get_oil_wells_stats():
    """
    获取油井数据的统计信息
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
                SELECT 
                    COUNT(*) as total_count,
                    COUNT(CASE WHEN extraction_status = 'Active' THEN 1 END) as active_count,
                    COUNT(CASE WHEN extraction_status = 'Stopped' THEN 1 END) as stopped_count,
                    COUNT(DISTINCT mine_type) as type_count,
                    AVG(well_depth_ft) as avg_depth_ft,
                    MAX(well_depth_ft) as max_depth_ft,
                    MIN(well_depth_ft) as min_depth_ft
                FROM oil_well_info
            """
            cur.execute(sql)
            stats = cur.fetchone()
            
            return jsonify({
                "status": "success",
                "stats": {
                    "total": stats['total_count'],
                    "active": stats['active_count'],
                    "stopped": stats['stopped_count'],
                    "types": stats['type_count'],
                    "avgDepth": float(stats['avg_depth_ft']) if stats['avg_depth_ft'] else 0,
                    "maxDepth": float(stats['max_depth_ft']) if stats['max_depth_ft'] else 0,
                    "minDepth": float(stats['min_depth_ft']) if stats['min_depth_ft'] else 0
                }
            })
    except Exception as e:
        logging.error(f"Error fetching oil well stats: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if conn:
            conn.close()

# API: 获取数据库中所有可用的空间图层列表
@app.route('/api/layers/list', methods=['GET'])
def get_available_layers():
    """
    查询数据库中所有包含几何列的表,返回图层列表供前端选择
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 查询 PostGIS geometry_columns 视图,获取所有空间表
            sql = """
                SELECT 
                    f_table_name as table_name,
                    f_geometry_column as geom_column,
                    type as geometry_type,
                    srid
                FROM geometry_columns
                WHERE f_table_schema = 'public'
                ORDER BY f_table_name;
            """
            cur.execute(sql)
            rows = cur.fetchall()
            
            layers = []
            for row in rows:
                layers.append({
                    "name": row['table_name'],
                    "geomColumn": row['geom_column'],
                    "geometryType": row['geometry_type'],
                    "srid": row['srid']
                })
            
            return jsonify({
                "status": "success",
                "layers": layers
            })
            
    except Exception as e:
        logging.error(f"Error fetching layers: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if conn:
            conn.close()

# API: 创建缓冲区分析
@app.route('/api/analysis/create-buffer', methods=['POST'])
def create_buffer_analysis():
    """
    接收前端参数,调用 bufferAnalysis.py 执行缓冲区建立
    请求体示例:
    {
        "inputLayer": "gps_points",
        "distance": 1000,
        "unit": "meters",
        "dissolveType": "NONE",
        "endType": "ROUND",
        "geometryColumn": "geom"
    }
    """
    conn = None
    try:
        data = request.get_json()
        
        # 验证必需参数
        if not data or 'inputLayer' not in data or 'distance' not in data:
            return jsonify({
                "status": "error",
                "message": "缺少必需参数: inputLayer 和 distance"
            }), 400
        
        input_layer = data['inputLayer']
        distance = float(data['distance'])
        unit = data.get('unit', 'meters')
        dissolve_type = data.get('dissolveType', 'NONE')
        end_type = data.get('endType', 'ROUND')
        geometry_column = data.get('geometryColumn', 'geom')
        
        # 验证距离值
        if distance <= 0:
            return jsonify({
                "status": "error",
                "message": "缓冲距离必须大于0"
            }), 400
        
        # 生成输出表名
        output_table = f"{input_layer}_buffer_{int(distance)}{unit[:1]}"
        
        # 调用缓冲区分析工具
        tool = BufferAnalysisTool(DB_CONFIG)
        tool.create_buffer(
            input_table=input_layer,
            output_table=output_table,
            distance=distance,
            unit=unit,
            dissolve_type=dissolve_type,
            end_type=end_type,
            geometry_column=geometry_column
        )
        
        # 查询生成的缓冲区数据并返回GeoJSON
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 根据是否融合选择不同的查询策略
            if dissolve_type.upper() == 'ALL':
                sql_query = f"""
                    SELECT 
                        ST_AsGeoJSON({geometry_column}) as geom_json
                    FROM {output_table}
                """
            else:
                sql_query = f"""
                    SELECT 
                        *,
                        ST_AsGeoJSON(buffer_geom) as buffer_geom_json
                    FROM {output_table}
                    LIMIT 1000
                """
            
            cur.execute(sql_query)
            rows = cur.fetchall()
            
            features = []
            for row in rows:
                if dissolve_type.upper() == 'ALL':
                    features.append({
                        "type": "Feature",
                        "properties": {"type": "merged_buffer"},
                        "geometry": json.loads(row['geom_json']) if row.get('geom_json') else None
                    })
                else:
                    # 提取所有非几何属性
                    properties = {k: v for k, v in row.items() if k not in ['buffer_geom_json', geometry_column]}
                    features.append({
                        "type": "Feature",
                        "properties": properties,
                        "geometry": json.loads(row['buffer_geom_json']) if row.get('buffer_geom_json') else None
                    })
        
        return jsonify({
            "status": "success",
            "message": f"缓冲区分析完成，结果已保存到表: {output_table}",
            "outputTable": output_table,
            "featureCount": len(features),
            "geojson": {
                "type": "FeatureCollection",
                "features": features
            }
        })
        
    except Exception as e:
        logging.error(f"Buffer analysis error: {e}")
        return jsonify({
            "status": "error",
            "message": f"缓冲区分析失败: {str(e)}"
        }), 500
    finally:
        if conn:
            conn.close()
# 缓冲区建立，调用backend/bufferAnalysis.py中的函数
# API: 删除指定图层（用于清除临时缓冲区）
@app.route('/api/analysis/delete-layer', methods=['POST'])
def delete_layer():
    """
    删除指定的数据库表
    请求体: {"tableName": "..."}
    """
    conn = None
    try:
        data = request.get_json()
        table_name = data.get('tableName')
        
        if not table_name:
            return jsonify({"status": "error", "message": "Missing tableName"}), 400
            
        # 简单验证表名安全性 (只允许字母数字下划线)
        if not table_name.replace('_', '').isalnum():
             return jsonify({"status": "error", "message": "Invalid table name"}), 400

        conn = get_db_connection()
        conn.autocommit = True
        with conn.cursor() as cur:
            # 检查表是否存在
            cur.execute("SELECT to_regclass(%s)", (table_name,))
            if not cur.fetchone()[0]:
                 return jsonify({"status": "error", "message": "Table not found"}), 404
            
            # 删除表
            cur.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier(table_name)))
            
        return jsonify({"status": "success", "message": f"Table {table_name} deleted"})
        
    except Exception as e:
        logging.error(f"Error deleting layer: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if conn: conn.close()


# API: 矿井形变风险分析 - 栅格矢量叠加分析
@app.route('/api/mining-deformation-analysis', methods=['POST'])
def mining_deformation_analysis():
    """
    矿井形变风险分析：提取矿井/油井位置的形变值，筛选高风险区域
    
    请求参数 (JSON):
        - miningLayer: 矿井图层名称 ('oil_well_info' 或 'mine_info')
        - deformationLayer: 形变图层名称（如 'v_mean_cropped_15_25'）
        - threshold: 形变绝对值阈值 (mm/year)
        - activeOnly: 是否仅包含活跃状态 (布尔值)
        - bufferDistance: 可选，缓冲区距离
        - bufferUnit: 可选，缓冲区单位 ('meters' 或 'kilometers')
    
    返回:
        GeoJSON格式的特征集合，包含形变值信息
    """
    try:
        # 获取请求参数
        data = request.get_json()
        
        mining_layer = data.get('miningLayer')
        deformation_layer = data.get('deformationLayer')
        threshold = abs(float(data.get('threshold', 10.0)))  # 确保阈值为正数
        active_only = data.get('activeOnly', False)
        buffer_distance = data.get('bufferDistance')
        buffer_unit = data.get('bufferUnit', 'meters')
        
        # 验证必需参数
        if not mining_layer or not deformation_layer:
            return jsonify({
                "status": "error",
                "message": "缺少必需参数: miningLayer 和 deformationLayer"
            }), 400
        
        # 验证图层名称
        if mining_layer not in ['oil_well_info', 'mine_info']:
            return jsonify({
                "status": "error",
                "message": f"无效的矿井图层名称: {mining_layer}"
            }), 400
        
        # 验证形变图层是否存在
        raster_ids = get_deformation_raster_by_layer(deformation_layer)
        if not raster_ids:
            return jsonify({
                "status": "error",
                "message": f"形变图层不存在或没有数据: {deformation_layer}"
            }), 404
        
        logging.info(f"Starting deformation analysis: layer={mining_layer}, "
                    f"deformation={deformation_layer}, threshold={threshold}, "
                    f"buffer={buffer_distance}")
        
        # 根据是否提供缓冲区距离选择不同的分析方法
        if buffer_distance and float(buffer_distance) > 0:
            # 使用缓冲区分析
            features = extract_deformation_values_with_buffer(
                layer_name=deformation_layer,
                mining_layer=mining_layer,
                active_only=active_only,
                threshold=threshold,
                buffer_distance=float(buffer_distance),
                buffer_unit=buffer_unit
            )
        else:
            # 使用点位分析
            features = extract_deformation_values_at_points(
                layer_name=deformation_layer,
                mining_layer=mining_layer,
                active_only=active_only,
                threshold=threshold
            )
        
        return jsonify({
            "status": "success",
            "message": f"分析完成，找到 {len(features)} 个高风险区域",
            "featureCount": len(features),
            "geojson": {
                "type": "FeatureCollection",
                "features": features
            },
            "analysisParams": {
                "miningLayer": mining_layer,
                "deformationLayer": deformation_layer,
                "threshold": threshold,
                "activeOnly": active_only,
                "bufferDistance": buffer_distance,
                "bufferUnit": buffer_unit
            }
        })
        
    except ValueError as e:
        logging.error(f"Validation error in deformation analysis: {e}")
        return jsonify({
            "status": "error",
            "message": f"参数验证失败: {str(e)}"
        }), 400
        
    except Exception as e:
        logging.error(f"Error in deformation analysis: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": f"分析失败: {str(e)}"
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)