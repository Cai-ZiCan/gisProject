-- 1. 用于在postgresql地理空间数据库中构建GPS站点信息表
-- 创建GPS站点信息表
-- 内容：
-- 站点ID、站点名称、站点等级、经度、纬度、高程、状态 ，设备开始运行时间、备注 等信息
CREATE TABLE gps_station_info (
    station_id SERIAL PRIMARY KEY,          -- 站点ID
    station_name VARCHAR(100) NOT NULL,     -- 站点名称
    station_level VARCHAR(20),               -- 站点等级
    longitude DECIMAL(9,6) NOT NULL,        -- 经度
    latitude DECIMAL(9,6) NOT NULL,         -- 纬度
    elevation DECIMAL(7,2),                  -- 高程
    status VARCHAR(50),                      -- 状态
    operational_start_time TIMESTAMP,         -- 设备开始运行时间
    remarks TEXT                           -- 备注
);

-- 创建空间索引以提高地理空间查询性能
CREATE INDEX idx_gps_station_location ON gps_station_info USING GIST (ST_MakePoint(longitude, latitude));


-- 2. 创建形变数据信息表，以存储GPS站点的形变数据
--内容：
-- 站点ID、观测时间点 、形变值（毫米）、备注 等信息
CREATE TABLE gps_deformation_data (
    record_id SERIAL PRIMARY KEY,           -- 记录ID
    station_id INT NOT NULL REFERENCES gps_station_info(station_id), -- 站点ID
    timestamp TIMESTAMP NOT NULL,           -- 时间戳
    deformation_value DECIMAL(10,3),         -- 形变值（毫米）
    remarks TEXT                           -- 备注
);

-- 创建索引以提高查询性能
-- 作用：快速根据站点ID查询形变数据
-- 使用方式：
CREATE INDEX idx_gps_deformation_station ON gps_deformation_data(station_id);


-- 3. 创建用于插入数据的存储过程
-- 用于向gps_station_info表中插入新站点信息
-- 使用示例：
-- SELECT insert_gps_station('Station A', 'Level 1', 120.123456, 30.123456, 50.5, 'Active', '2023-01-01 00:00:00', 'Initial setup');
CREATE OR REPLACE FUNCTION insert_gps_station(
    p_station_name VARCHAR, -- 站点名称
    p_station_level VARCHAR, -- 站点等级
    p_longitude DECIMAL,
    p_latitude DECIMAL,
    p_elevation DECIMAL,
    p_status VARCHAR,
    p_operational_start_time TIMESTAMP,
    p_remarks TEXT
) RETURNS VOID AS $$
BEGIN -- 存储过程开始
    INSERT INTO gps_station_info (
        station_name, station_level, longitude, latitude, elevation, status, operational_start_time, remarks
    ) VALUES (
        p_station_name, p_station_level, p_longitude, p_latitude, p_elevation, p_status, p_operational_start_time, p_remarks
    );
END;
$$ LANGUAGE plpgsql; -- 存储过程结束

-- 4. 用于向gps_deformation_data表中插入新形变数据
-- 使用示例：
-- SELECT insert_gps_deformation(1, '2023-01-15 12:00:00', 5.123, 'No significant events');
CREATE OR REPLACE FUNCTION insert_gps_deformation(
    p_station_id INT, -- 站点ID
    p_timestamp TIMESTAMP,
    p_deformation_value DECIMAL,
    p_remarks TEXT
) RETURNS VOID AS $$
BEGIN
    INSERT INTO gps_deformation_data (
        station_id, timestamp, deformation_value, remarks
    ) VALUES (
        p_station_id, p_timestamp, p_deformation_value, p_remarks
    );
END;
$$ LANGUAGE plpgsql; -- 存储过程结束