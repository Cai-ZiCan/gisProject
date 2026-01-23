# -*- coding: utf-8 -*-
"""
脚本功能：
1. 读取GeoTIFF形变速率栅格文件
2. 自动写入PostgreSQL/PostGIS数据库annual_defo_raster表
3. 支持命令行参数指定tif路径、图层名、描述
4. 依赖：rasterio, psycopg2, tqdm
"""
import os
import sys
import argparse
import rasterio
import psycopg2
from psycopg2 import sql
from tqdm import tqdm
import subprocess
import tempfile
import shutil

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 5432,
    "database": "deformation_db",
    "user": "postgres",
    "password": "123456"
}

# PostGIS工具路径配置
RASTER2PGSQL = r"D:\\ServBay\\packages\\postgresql\\16\\bin\\raster2pgsql.exe"
PSQL = r"D:\\ServBay\\packages\\postgresql\\16\\bin\\psql.exe"

def insert_raster_to_db(tif_path, layer_name, description=None):
    if not os.path.exists(tif_path):
        print(f"[错误] 文件不存在: {tif_path}")
        return
    
    with rasterio.open(tif_path) as src:
        wkb_raster = src.read(1)
        
        # 使用临时文件存储raster2pgsql的输出
        print(f"[信息] 正在导入: {tif_path} -> annual_defo_raster (图层: {layer_name})")
        
        # 设置环境变量
        env = os.environ.copy()
        env['PGPASSWORD'] = DB_CONFIG['password']
        
        # 创建临时副本以避免中文路径问题 - 使用C:\temp避免用户名中的中文
        temp_dir = r"C:\temp"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        
        temp_tif_path = os.path.join(temp_dir, 'temp_raster.tif')
        temp_sql_path = os.path.join(temp_dir, 'temp_import.sql')
        
        try:
            # 复制文件到临时路径
            print(f"[信息] 复制文件到临时路径: {temp_tif_path}")
            shutil.copy2(tif_path, temp_tif_path)
            
            # 第一步：使用raster2pgsql生成SQL导入到临时表
            # 使用临时表名，避免冲突
            staging_table = f"staging_{os.path.basename(tif_path).split('.')[0]}_{os.getpid()}"
            # 确保临时表名合法（只保留字母数字下划线），并转换为小写以避免引用问题
            staging_table = "".join([c if c.isalnum() else "_" for c in staging_table]).lower()
            
            print(f"[信息] 生成SQL (中转表: {staging_table})...")
            # 使用 -d (Drop/Create) 确保中转表是新的, -s 4326 指定坐标系
            with open(temp_sql_path, 'w', encoding='utf-8') as f:
                result = subprocess.run(
                    [RASTER2PGSQL, '-s', '4326', '-I', '-C', '-M', '-F', '-t', '100x100', '-d', temp_tif_path, staging_table],
                    stdout=f,
                    stderr=subprocess.PIPE,
                    env=env,
                    text=True
                )
                if result.returncode != 0:
                    print(f"[错误] raster2pgsql失败: {result.stderr}")
                    return
            
            # 第二步：执行SQL创建临时表并导入数据
            print(f"[信息] 导入数据到临时表...")
            conn = psycopg2.connect(**DB_CONFIG)
            
            # 先执行raster2pgsql生成的SQL脚本
            result = subprocess.run(
                [PSQL, '-h', DB_CONFIG['host'], '-p', str(DB_CONFIG['port']), 
                 '-U', DB_CONFIG['user'], '-d', DB_CONFIG['database'], '-f', temp_sql_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env, # 传递密码
                text=True # 确保输出是文本
                # encoding='utf-8' # psql通常根据环境自动检测，如果乱码可能需要指定
            )
            
            if result.returncode != 0:
                 print(f"[错误] psql执行失败: {result.stderr}")
                 conn.close()
                 return

            # 第三步：从临时表转移到主表 (处理自定义字段和约束)
            print(f"[信息] 从临时表转移数据到主表 annual_defo_raster...")
            try:
                with conn.cursor() as cur:
                    # 检查临时表是否有数据
                    cur.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(staging_table)))
                    count = cur.fetchone()[0]
                    print(f"[信息] 临时表数据行数: {count}")
                    
                    # 插入主表
                    insert_query = sql.SQL("""
                        INSERT INTO annual_defo_raster (rast, layer_name, description, upload_time)
                        SELECT rast, %s, %s, CURRENT_TIMESTAMP
                        FROM {}
                    """).format(sql.Identifier(staging_table))
                    
                    cur.execute(insert_query, (layer_name, description))
                    
                    # 删除临时表
                    cur.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier(staging_table)))
                
                conn.commit()
                print("[成功] 数据入库完成！")
                
            except Exception as e:
                conn.rollback()
                print(f"[错误] 数据转移失败: {e}")
            finally:
                conn.close()
                
        finally:
            # 暂时保留临时文件用于调试
            # if os.path.exists(temp_tif_path):
            #     os.unlink(temp_tif_path)
            # if os.path.exists(temp_sql_path):
            #     os.unlink(temp_sql_path)
            print(f"[调试] 临时文件保留在: {temp_sql_path}")
            pass


def main():
    parser = argparse.ArgumentParser(description="GeoTIFF形变栅格数据入库脚本")
    parser.add_argument('--tif', default=None, help='GeoTIFF文件路径')
    parser.add_argument('--layer', default=None, help='图层名（如v_mean_cropped_15_18）')
    parser.add_argument('--desc', default='', help='描述信息')
    args = parser.parse_args()
    
    # 如果未提供命令行参数，使用默认值
    tif_path = args.tif or "D:\\InSAR\\复现LAB_SBAS\\InSAR_product\\V_mean_cropped_15_18.tif"
    layer_name = args.layer or "v_mean_cropped_15_18"
    description = args.desc or "形变速率栅格数据，时间范围2015-2018"
    
    insert_raster_to_db(tif_path, layer_name, description)

if __name__ == '__main__':
    main()
