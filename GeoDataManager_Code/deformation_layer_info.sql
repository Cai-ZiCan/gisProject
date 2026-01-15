 -- 用于在postgresql数据库 中创建存储 平均形变速率图层信息表 的SQL脚本

 -- 1.创建平均形变速率图层信息（元数据）表
 -- 内容：
 -- 图层ID、图层名称、生产使用数据量（影像幅数）、最早数据时间、最晚数据时间、
 -- 数据来源（所用卫星）、生产方式（使用的InSAR算法）、生产工具（使用软件）、备注 等字段
    CREATE TABLE deformation_layer_info (
        layer_id SERIAL PRIMARY KEY,                 -- 图层ID
        layer_name VARCHAR(100) NOT NULL,           -- 图层名称
        data_volume INT,                            -- 生产使用数据量（影像幅数）
        earliest_data_time TIMESTAMP,                -- 最早数据时间
        latest_data_time TIMESTAMP,                  -- 最晚数据时间
        data_source VARCHAR(100),                    -- 数据来源（所用卫星）
        production_method VARCHAR(100),              -- 生产方式（使用的InSAR算法）
        production_tool VARCHAR(100),                -- 生产工具（使用软件）
        remarks TEXT                                -- 备注
    );
    -- 添加检查约束，确保最早数据时间不晚于最晚数据时间
    ALTER TABLE deformation_layer_info
    ADD CONSTRAINT chk_data_time
    CHECK (earliest_data_time <= latest_data_time);

-- 2.创建用于数据插入的存储过程
-- 用于向deformation_layer_info表中插入新图层信息
""" 
-- 使用示例：
insert_deformation_layer(
     'Deformation Layer 1', 50, '2022-01-01 00:00:00', '2022-12-31 23:59:59',
     'Sentinel-1', 'SBAS', 'SNAP', 'Initial data layer'
);
"""
CREATE OR REPLACE FUNCTION insert_deformation_layer(
    p_layer_name VARCHAR,               -- 图层名称
    p_data_volume INT,                 -- 生产使用数据量（影像幅数）
    p_earliest_data_time TIMESTAMP,     -- 最早数据时间
    p_latest_data_time TIMESTAMP,       -- 最晚数据时间
    p_data_source VARCHAR,              -- 数据来源（所用卫星）
    p_production_method VARCHAR,        -- 生产方式（使用的InSAR算法）
    p_production_tool VARCHAR,          -- 生产工具（使用软件）
    p_remarks TEXT                     -- 备注
) RETURNS VOID AS $$
BEGIN -- 存储过程开始
    INSERT INTO deformation_layer_info (
        layer_name, data_volume, earliest_data_time, latest_data_time,
        data_source, production_method, production_tool, remarks
    ) VALUES (
        p_layer_name, p_data_volume, p_earliest_data_time, p_latest_data_time,
        p_data_source, p_production_method, p_production_tool, p_remarks
    );
END;
$$ LANGUAGE plpgsql; -- 存储过程结束