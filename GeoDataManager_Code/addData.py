# 用于向数据库中插入已有的/定义的地理数据
import os
import sys
import psycopg2

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": "5432",
    "database": "deformation_db",
    "user": "postgres",
    "password": "123456"
}

# 1.用于向形变图层的元数据表中插入数据
def insert_deformation_layer_info(layer_name, data_volume, earliest_data_time, latest_data_time, data_source, production_method, production_tool, remarks):
    """
    向deformation_layer_info表中插入数据
    调用存储过程 insert_deformation_layer
    """
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # 执行存储过程
        # 注意：postgresql中执行返回void的function通常使用SELECT
        sql = """
            SELECT insert_deformation_layer(
                %s, %s, %s, %s, %s, %s, %s, %s
            );
        """
        cur.execute(sql, (layer_name, data_volume, earliest_data_time, latest_data_time, data_source, production_method, production_tool, remarks))
        
        conn.commit()
        #  添加对于若已有相同图层名时的提示
        notices = conn.notices
        for notice in notices:
            if "Updating existing layer" in notice:
                print(f"[Notice] {notice.strip()}")

        print(f"[Success] 已成功插入图层信息: {layer_name}")
        
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"[Error] 数据库操作失败: {error}")
    finally:
        if conn is not None:
            conn.close()

if __name__ == "__main__":
    # 测试代码
    print("开始插入测试数据...")
    # insert_deformation_layer_info(
    #     'Test Layer', 
    #     100, 
    #     '2023-01-01', 
    #     '2023-12-31', 
    #     'Sentinel-1', 
    #     'SBAS-InSAR', 
    #     'SNAP', 
    #     '这是一个测试插入的图层'
    # )

    # 1.对于15-18年的形变图层数据信息输入
    insert_deformation_layer_info(
        'v_mean_cropped_15_18',
        67,
        '2015-05-14',
        '2018-05-22',
        'Sentinel-1',
        'SBAS-InSAR',
        'Gamma Remote Sensing Software',
        '这是15-18年期间数据处理的年均形变速率图层'
    )

    # 2.对于15-25年的形变图层数据信息输入
    insert_deformation_layer_info(
        'v_mean_cropped_15_25',
        362,
        '2015-05-14',
        '2025-05-22',
        'Sentinel-1',
        'SBAS-InSAR',
        'Gamma Remote Sensing Software',
        '这是15-25年期间数据处理的年均形变速率图层'
    )