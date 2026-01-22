from flask import Flask, jsonify, request  # 添加 request
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import logging
from bufferAnalysis import BufferAnalysisTool

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
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            sql = """
                SELECT 
                    mine_id, mine_name, mine_type, mine_level, 
                    longitude, latitude, extraction_status,
                    ST_AsGeoJSON(ST_MakePoint(longitude, latitude)) as geom_json
                FROM mine_info
            """
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
                        "status": row['extraction_status']
                    },
                    "geometry": json.loads(row['geom_json']) if row['geom_json'] else None
                })
            
            return jsonify({
                "type": "FeatureCollection",
                "features": features
            })
    except Exception as e:
        logging.error(f"Error fetching mining risk: {e}")
        # 如果表不存在，返回空集合而不是500，以免前端报错太难看
        return jsonify({"type": "FeatureCollection", "features": []})
    
    finally:
        if conn: conn.close()

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
                sql = f"""
                    SELECT 
                        ST_AsGeoJSON({geometry_column}) as geom_json
                    FROM {output_table}
                """
            else:
                sql = f"""
                    SELECT 
                        *,
                        ST_AsGeoJSON(buffer_geom) as buffer_geom_json
                    FROM {output_table}
                    LIMIT 1000
                """
            
            cur.execute(sql)
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



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)