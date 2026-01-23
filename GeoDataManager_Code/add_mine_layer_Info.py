# 用于将矿井的shp文件加载存储到数据库中，以用于后续的查询和分析
mine_shp_path = r'"D:\\GIS\\GISwork_DATA\\CourseDesign\\LosAngle_oil_gas\\Oil_Wells_(Inside_LA_County)\\Oil_Wells_(Inside_LA_County).shp"'
mine_layer_name = 'oil_gas_layer'
# 矿井表格信息
#  1.创建矿井信息表
# -- 内容：
# -- 矿井ID、矿井API、矿井名称(默认矿井名称不重复，若遇到问题需要检查)、矿井类型、矿井深度、经度、纬度、
# -- 开采状态、开采起始时间、开采结束时间（若已结束开采）、备注 等字段
# CREATE TABLE mine_info (
#     mine_id SERIAL PRIMARY KEY,              -- 矿井ID
#     mine_name VARCHAR(100) NOT NULL,         -- 矿井名称
#     mine_api VARCHAR(50) UNIQUE NOT NULL,    -- 矿井API
#     mine_type VARCHAR(50),                    -- 矿井类型
#     mine_depth DECIMAL(10,2),                 -- 矿井深度
#     longitude DECIMAL(9,6) NOT NULL,         -- 经度
#     latitude DECIMAL(9,6) NOT NULL,          -- 纬度
#     extraction_status VARCHAR(50),            -- 开采状态 （Active/Stopped）
#     extraction_start_time TIMESTAMP,          -- 开采起始时间
#     extraction_end_time TIMESTAMP,            -- 开采结束时间
#     remarks TEXT                             -- 备注
# );

