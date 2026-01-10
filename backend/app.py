from flask import Flask, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import logging

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

@app.route('/api/layer-info', methods=['GET'])
def get_layer_info():
    """
    返回形变图层的元数据信息
    """
    metadata = {
        "layer_name": "地表形变监测图层",
        "satellite_source": "Sentinel-1A/B (哨兵一号)",
        "processing_method": "InSAR (干涉合成孔径雷达)",
        "time_series": "2015-01 至 2018-12",
        "data_volume": "1.2 GB",
        "resolution": "15m x 15m",
        "update_frequency": "每12天",
        "description": "该图层展示了基于长时间序列InSAR技术处理的地表形变速率，红色代表沉降，蓝色代表抬升。"
    }
    return jsonify(metadata)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)