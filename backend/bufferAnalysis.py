import psycopg2
from psycopg2 import sql

class BufferAnalysisTool:
    def __init__(self, db_config):
        """
        初始化缓冲区分析工具
        :param db_config: 数据库连接配置字典 (host, port, database, user, password)
        """
        self.db_config = db_config

    def _get_connection(self):
        return psycopg2.connect(**self.db_config)

    def create_buffer(self, input_table, output_table, distance, unit='meters', 
                      dissolve_type='NONE', end_type='ROUND', geometry_column='geom'):
        """
        模仿 ArcGIS 'Create Buffers' 工具逻辑，
        在 PostGIS 数据库中生成缓冲区并保存到新表。
        
        参考: https://pro.arcgis.com/zh-cn/pro-app/latest/tool-reference/feature-analysis/create-buffers.htm

        参数:
        :param input_table: 输入表名
        :param output_table: 输出表名 (将创建新表，如果存在则覆盖)
        :param distance: 缓冲距离 (float)
        :param unit: 距离单位，支持 'meters', 'kilometers', 'degrees'。
                     如果数据是经纬度且单位是 meters/kilometers，将使用 geography 类型进行测地线缓冲(Geodesic)。
        :param dissolve_type: 融合类型。
                              'NONE': 不融合 (默认)，保留每个要素的缓冲区。
                              'ALL': 融合所有缓冲区为一个多边形。
        :param end_type: 末端类型 (仅适用于线要素且非测地线缓冲时有效)。
                         'ROUND': 圆头 (默认)
                         'FLAT': 平头
        :param geometry_column: 几何列名，默认为 'geom'
        """
        
        # 单位转换 (转换为米，或保持度)
        dist_val = float(distance)
        if unit == 'kilometers':
            dist_val *= 1000.0
        
        use_geography = False
        if unit in ['meters', 'kilometers']:
            # 假设如果单位是米但在 4326 坐标系下，我们需要 cast 到 geography 以获得正确结果
            use_geography = True
        elif unit == 'degrees':
            use_geography = False

        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # 1. 检查并删除已存在的输出表
                cur.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier(output_table)))
                
                # 2. 构建缓冲区 SQL 表达式
                # ST_Buffer 签名:
                # geometry: ST_Buffer(geom, dist, 'endcap=round|flat ...')
                # geography: ST_Buffer(geog, dist) -> 总是 geodesic (round)

                geom_expr = sql.Identifier(geometry_column)
                
                if use_geography:
                    # 使用 geography 类型进行计算 (单位: 米)
                    # geography 缓冲总是 round endcap
                    buffer_expr = sql.SQL("ST_Buffer({}::geography, %s)::geometry").format(geom_expr)
                    buffer_params = [dist_val]
                else:
                    # 使用 geometry 类型进行计算 (单位: 坐标系单位，通常是度或投影单位)
                    style_params = ''
                    if end_type.upper() == 'FLAT':
                        style_params = 'endcap=flat join=round'
                    else:
                        style_params = 'endcap=round join=round'
                        
                    buffer_expr = sql.SQL("ST_Buffer({}, %s, %s)").format(geom_expr)
                    buffer_params = [dist_val, style_params]

                # 3. 构建完整的 SELECT ... INTO ... (或 CREATE TABLE AS)
                if dissolve_type.upper() == 'ALL':
                    # 融合所有结果: ST_Union
                    # 注意: 融合后的属性可能丢失，这里简单地只保留几何
                    query = sql.SQL("""
                        CREATE TABLE {} AS
                        SELECT 
                            ST_Union({}) AS {} 
                        FROM {}
                    """).format(
                        sql.Identifier(output_table),
                        buffer_expr,
                        sql.Identifier(geometry_column),
                        sql.Identifier(input_table)
                    )
                else: # NONE
                    # 保持原表属性，只替换几何列
                    # 为了简化，我们选取所有列，但替换 geometry 列
                    # 需要获取列名列表比较安全，但这里使用 SELECT *, buffer AS geom 的变体
                    # 更好的方式: CREATE TABLE AS SELECT table.* EXCEPT geom, buffer(geom) ...
                    # 但 PostgreSQL 标准 SQL 不直接支持 EXCEPT columns。
                    # 我们简单地做: SELECT *, ST_Buffer(...) as buffer_geom
                    
                    query = sql.SQL("""
                        CREATE TABLE {} AS
                        SELECT 
                            *,
                            {} AS buffer_geom
                        FROM {}
                    """).format(
                        sql.Identifier(output_table),
                        buffer_expr,
                        sql.Identifier(input_table)
                    )
                    # 注意：这将导致新表有原 geom 列和新的 buffer_geom 列。
                    # 用户可能需要丢弃原 geom 列，这里为了逻辑完整性我们保留原数据。

                # 执行查询
                cur.execute(query, buffer_params)
                
                # 为新表注册 geometry 列信息 (可选, 视 PostGIS 版本而定)
                # cur.execute(sql.SQL("SELECT Populate_Geometry_Columns('{}'::regclass);").format(sql.Identifier(output_table)))
                
                conn.commit()
                print(f"缓冲区建立成功: 表 '{output_table}' 已创建。")
                
        except Exception as e:
            conn.rollback()
            print(f"缓冲区建立失败: {e}")
            raise
        finally:
            conn.close()

# 示例调用代码 (调试用)
if __name__ == "__main__":
    # 配置需根据实际环境修改
    DB_CONFIG = {
        "host": "127.0.0.1",
        "port": "5432",
        "database": "deformation_db",
        "user": "postgres",
        "password": "123456"
    }
    
    tool = BufferAnalysisTool(DB_CONFIG)
    
    # 示例: 为 gps_points 表创建 500米 缓冲区，不融合
    # tool.create_buffer(
    #     input_table="gps_points", 
    #     output_table="gps_points_buffer_500m", 
    #     distance=500, 
    #     unit='meters', 
    #     dissolve_type='NONE'
    # )
