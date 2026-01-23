-- ==============================================================================
-- GPS测站元数据信息表创建脚本
-- 数据库：deformation_db
-- 描述：创建GPS监测测站的元数据信息表，包含测站基本信息、位置信息、设备信息等
-- ==============================================================================

-- 1. 删除旧表（如果存在）
DROP TABLE IF EXISTS gps_deformation_data CASCADE;
DROP TABLE IF EXISTS gps_station_info CASCADE;

-- 2. 创建GPS测站元数据信息表
CREATE TABLE gps_station_info (
    -- 基本标识信息
    station_id SERIAL PRIMARY KEY,                  -- 测站ID（主键，自增）
    station_code VARCHAR(50) UNIQUE NOT NULL,       -- 测站编码（唯一，用于业务识别）
    code_type VARCHAR(20) DEFAULT '4CHARID',        -- 编码类型（4CHARID/IGS/CUSTOM等）
    station_name VARCHAR(100) UNIQUE NOT NULL,      -- 测站名称（唯一）
    station_name_en VARCHAR(100),                   -- 测站英文名称
    
    -- 分类信息
    station_type VARCHAR(50) DEFAULT 'GPS',         -- 测站类型（GPS/GNSS/北斗等）
    network_name VARCHAR(100),                      -- 所属监测网络名称
    project_name VARCHAR(100),                      -- 所属项目名称
    
    -- 地理位置信息
    longitude DECIMAL(10,7) NOT NULL,               -- 经度（十进制度，7位小数）
    latitude DECIMAL(10,7) NOT NULL,                -- 纬度（十进制度，7位小数）
    elevation DECIMAL(8,3),                         -- 高程（米，3位小数）
    geom GEOMETRY(Point, 4326),                     -- 空间几何对象（WGS84坐标系）
    
    -- 行政区划信息
    province VARCHAR(50),                           -- 省份
    city VARCHAR(50),                               -- 城市
    district VARCHAR(50),                           -- 区县
    address TEXT,                                   -- 详细地址
    
    -- 设备信息
    receiver_type VARCHAR(100),                     -- 接收机类型
    receiver_serial VARCHAR(100),                   -- 接收机序列号
    antenna_type VARCHAR(100),                      -- 天线类型
    antenna_serial VARCHAR(100),                    -- 天线序列号
    antenna_height DECIMAL(5,3),                    -- 天线高度（米）
    
    -- 运行状态信息
    status VARCHAR(50) DEFAULT '在用',              -- 运行状态（在用/停用/维修/报废）
    data_quality VARCHAR(50) DEFAULT '良好',        -- 数据质量（优秀/良好/一般/较差）
    operational_start_date DATE,                    -- 开始运行日期
    operational_end_date DATE,                      -- 停止运行日期
    last_maintenance_date DATE,                     -- 最后维护日期
    next_maintenance_date DATE,                     -- 下次维护日期
    
    -- 数据采集设置
    sampling_interval INT DEFAULT 30,               -- 采样间隔（秒）
    data_storage_days INT DEFAULT 365,              -- 数据保存天数
    alert_threshold DECIMAL(10,3),                  -- 预警阈值（毫米）
    
    -- 审计信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 创建时间
    created_by VARCHAR(50),                         -- 创建人
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 更新时间
    updated_by VARCHAR(50),                         -- 更新人
    is_deleted BOOLEAN DEFAULT FALSE,               -- 是否删除（软删除标记）
    
    -- 备注信息
    remarks TEXT,                                   -- 备注信息
    metadata_json JSONB                             -- 扩展元数据（JSON格式，用于存储其他自定义信息）
);

-- 3. 添加表注释
COMMENT ON TABLE gps_station_info IS 'GPS监测测站元数据信息表';
COMMENT ON COLUMN gps_station_info.station_id IS '测站ID（主键）';
COMMENT ON COLUMN gps_station_info.station_code IS '测站编码（唯一业务标识）';
COMMENT ON COLUMN gps_station_info.code_type IS '编码类型：4CHARID/IGS/CUSTOM等';
COMMENT ON COLUMN gps_station_info.station_name IS '测站名称';
COMMENT ON COLUMN gps_station_info.geom IS '空间几何对象（WGS84，EPSG:4326）';
COMMENT ON COLUMN gps_station_info.status IS '运行状态：在用/停用/维修/报废';

-- 4. 创建索引以提高查询性能
CREATE INDEX idx_gps_station_code ON gps_station_info(station_code);          -- 测站编码索引
CREATE INDEX idx_gps_station_code_type ON gps_station_info(code_type);        -- 编码类型索引
CREATE INDEX idx_gps_station_name ON gps_station_info(station_name);          -- 测站名称索引
CREATE INDEX idx_gps_station_status ON gps_station_info(status);              -- 状态索引
CREATE INDEX idx_gps_station_network ON gps_station_info(network_name);       -- 监测网络索引
CREATE INDEX idx_gps_station_location ON gps_station_info(province, city);    -- 地理位置索引
CREATE INDEX idx_gps_station_geom ON gps_station_info USING GIST (geom);      -- 空间索引（GiST）
CREATE INDEX idx_gps_station_created_at ON gps_station_info(created_at);      -- 创建时间索引
CREATE INDEX idx_gps_station_is_deleted ON gps_station_info(is_deleted);      -- 删除标记索引

-- 5. 创建触发器：自动更新geom字段
CREATE OR REPLACE FUNCTION update_gps_station_geom()
RETURNS TRIGGER AS $$
BEGIN
    NEW.geom = ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_gps_station_geom
    BEFORE INSERT OR UPDATE OF longitude, latitude ON gps_station_info
    FOR EACH ROW
    EXECUTE FUNCTION update_gps_station_geom();

-- 6. 创建触发器：自动更新updated_at字段
CREATE OR REPLACE FUNCTION update_gps_station_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_gps_station_timestamp
    BEFORE UPDATE ON gps_station_info
    FOR EACH ROW
    EXECUTE FUNCTION update_gps_station_timestamp();


-- ==============================================================================
-- GPS形变数据表
-- ==============================================================================

-- 7. 创建GPS形变数据表
CREATE TABLE gps_deformation_data (
    record_id SERIAL PRIMARY KEY,                           -- 记录ID（主键）
    station_id INT NOT NULL,                                -- 测站ID（外键）
    observation_time TIMESTAMP NOT NULL,                    -- 观测时间
    
    -- 三维形变数据
    deformation_x DECIMAL(10,3),                            -- X方向形变值（毫米，东西向）
    deformation_y DECIMAL(10,3),                            -- Y方向形变值（毫米，南北向）
    deformation_z DECIMAL(10,3),                            -- Z方向形变值（毫米，垂直向）
    deformation_total DECIMAL(10,3),                        -- 总形变量（毫米）
    
    -- 速率信息
    velocity_x DECIMAL(10,3),                               -- X方向速率（毫米/年）
    velocity_y DECIMAL(10,3),                               -- Y方向速率（毫米/年）
    velocity_z DECIMAL(10,3),                               -- Z方向速率（毫米/年）
    
    -- 精度信息
    accuracy_x DECIMAL(10,3),                               -- X方向精度（毫米）
    accuracy_y DECIMAL(10,3),                               -- Y方向精度（毫米）
    accuracy_z DECIMAL(10,3),                               -- Z方向精度（毫米）
    
    -- 数据质量
    data_quality VARCHAR(20) DEFAULT '良好',                -- 数据质量（优秀/良好/一般/较差）
    is_abnormal BOOLEAN DEFAULT FALSE,                      -- 是否异常数据
    abnormal_reason TEXT,                                   -- 异常原因
    
    -- 处理信息
    processing_method VARCHAR(100),                         -- 数据处理方法
    baseline_length DECIMAL(10,3),                          -- 基线长度（公里）
    satellites_used INT,                                    -- 使用卫星数量
    
    -- 审计信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,         -- 创建时间
    remarks TEXT,                                           -- 备注
    
    -- 外键约束
    CONSTRAINT fk_station_id FOREIGN KEY (station_id) 
        REFERENCES gps_station_info(station_id) 
        ON DELETE CASCADE ON UPDATE CASCADE
);

-- 8. 添加表注释
COMMENT ON TABLE gps_deformation_data IS 'GPS形变监测数据表';
COMMENT ON COLUMN gps_deformation_data.deformation_x IS 'X方向（东西向）形变值，单位：毫米';
COMMENT ON COLUMN gps_deformation_data.deformation_y IS 'Y方向（南北向）形变值，单位：毫米';
COMMENT ON COLUMN gps_deformation_data.deformation_z IS 'Z方向（垂直向）形变值，单位：毫米';

-- 9. 创建索引
CREATE INDEX idx_deformation_station ON gps_deformation_data(station_id);                    -- 测站索引
CREATE INDEX idx_deformation_time ON gps_deformation_data(observation_time);                 -- 时间索引
CREATE INDEX idx_deformation_station_time ON gps_deformation_data(station_id, observation_time); -- 复合索引
CREATE INDEX idx_deformation_abnormal ON gps_deformation_data(is_abnormal);                  -- 异常标记索引
CREATE INDEX idx_deformation_quality ON gps_deformation_data(data_quality);                  -- 质量索引

-- ==============================================================================
-- 存储过程和函数
-- ==============================================================================

-- 10. 插入GPS测站信息的存储过程
CREATE OR REPLACE FUNCTION insert_gps_station(
    p_station_code VARCHAR,
    p_station_name VARCHAR,
    p_code_type VARCHAR DEFAULT '4CHARID',
    p_station_type VARCHAR DEFAULT 'GPS',
    p_longitude DECIMAL DEFAULT NULL,
    p_latitude DECIMAL DEFAULT NULL,
    p_elevation DECIMAL DEFAULT NULL,
    p_province VARCHAR DEFAULT NULL,
    p_city VARCHAR DEFAULT NULL,
    p_district VARCHAR DEFAULT NULL,
    p_address TEXT DEFAULT NULL,
    p_status VARCHAR DEFAULT '在用',
    p_operational_start_date DATE DEFAULT NULL,
    p_remarks TEXT DEFAULT NULL,
    p_created_by VARCHAR DEFAULT NULL
) RETURNS INT AS $$
DECLARE
    v_station_id INT;
BEGIN
    -- 检查测站编码是否已存在
    IF EXISTS (SELECT 1 FROM gps_station_info WHERE station_code = p_station_code AND is_deleted = FALSE) THEN
        RAISE EXCEPTION '测站编码 % 已存在', p_station_code;
    END IF;
    
    -- 检查测站名称是否已存在
    IF EXISTS (SELECT 1 FROM gps_station_info WHERE station_name = p_station_name AND is_deleted = FALSE) THEN
        RAISE EXCEPTION '测站名称 % 已存在', p_station_name;
    END IF;
    
    -- 检查经纬度是否有效
    IF p_longitude IS NOT NULL AND (p_longitude < -180 OR p_longitude > 180) THEN
        RAISE EXCEPTION '经度值无效：%，必须在-180到180之间', p_longitude;
    END IF;
    
    IF p_latitude IS NOT NULL AND (p_latitude < -90 OR p_latitude > 90) THEN
        RAISE EXCEPTION '纬度值无效：%，必须在-90到90之间', p_latitude;
    END IF;
    
    -- 插入数据
    INSERT INTO gps_station_info (
        station_code, station_name, code_type, station_type,
        longitude, latitude, elevation,
        province, city, district, address,
        status, operational_start_date,
        remarks, created_by
    ) VALUES (
        p_station_code, p_station_name, p_code_type, p_station_type,
        p_longitude, p_latitude, p_elevation,
        p_province, p_city, p_district, p_address,
        p_status, p_operational_start_date,
        p_remarks, p_created_by
    ) RETURNING station_id INTO v_station_id;
    
    RAISE NOTICE '成功插入测站信息，测站ID: %', v_station_id;
    RETURN v_station_id;
END;
$$ LANGUAGE plpgsql;

-- 11. 插入GPS形变数据的存储过程
CREATE OR REPLACE FUNCTION insert_gps_deformation(
    p_station_id INT,
    p_observation_time TIMESTAMP,
    p_deformation_x DECIMAL DEFAULT NULL,
    p_deformation_y DECIMAL DEFAULT NULL,
    p_deformation_z DECIMAL DEFAULT NULL,
    p_data_quality VARCHAR DEFAULT '良好',
    p_remarks TEXT DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    -- 检查测站是否存在
    IF NOT EXISTS (SELECT 1 FROM gps_station_info WHERE station_id = p_station_id AND is_deleted = FALSE) THEN
        RAISE EXCEPTION '测站ID % 不存在或已删除', p_station_id;
    END IF;
    
    -- 计算总形变量
    DECLARE
        v_deformation_total DECIMAL(10,3);
    BEGIN
        IF p_deformation_x IS NOT NULL AND p_deformation_y IS NOT NULL AND p_deformation_z IS NOT NULL THEN
            v_deformation_total := SQRT(
                POWER(p_deformation_x, 2) + 
                POWER(p_deformation_y, 2) + 
                POWER(p_deformation_z, 2)
            );
        END IF;
        
        -- 插入形变数据
        INSERT INTO gps_deformation_data (
            station_id, observation_time,
            deformation_x, deformation_y, deformation_z, deformation_total,
            data_quality, remarks
        ) VALUES (
            p_station_id, p_observation_time,
            p_deformation_x, p_deformation_y, p_deformation_z, v_deformation_total,
            p_data_quality, p_remarks
        );
    END;
END;
$$ LANGUAGE plpgsql;

-- 12. 更新测站状态的存储过程
CREATE OR REPLACE FUNCTION update_gps_station_status(
    p_station_code VARCHAR,
    p_status VARCHAR,
    p_remarks TEXT DEFAULT NULL,
    p_updated_by VARCHAR DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    -- 检查测站是否存在
    IF NOT EXISTS (SELECT 1 FROM gps_station_info WHERE station_code = p_station_code AND is_deleted = FALSE) THEN
        RAISE EXCEPTION '测站编码 % 不存在或已删除', p_station_code;
    END IF;
    
    -- 检查状态值是否有效
    IF p_status NOT IN ('在用', '停用', '维修', '报废') THEN
        RAISE EXCEPTION '无效的状态值：%，必须是：在用、停用、维修、报废之一', p_status;
    END IF;
    
    -- 更新状态
    UPDATE gps_station_info
    SET status = p_status,
        remarks = CASE 
            WHEN p_remarks IS NOT NULL THEN 
                COALESCE(remarks, '') || E'\n' || 
                '[' || TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS') || '] ' || 
                p_remarks
            ELSE remarks
        END,
        updated_by = p_updated_by,
        updated_at = CURRENT_TIMESTAMP
    WHERE station_code = p_station_code AND is_deleted = FALSE;
    
    RAISE NOTICE '成功更新测站 % 的状态为：%', p_station_code, p_status;
END;
$$ LANGUAGE plpgsql;

-- 13. 软删除测站的存储过程
CREATE OR REPLACE FUNCTION delete_gps_station(
    p_station_code VARCHAR,
    p_updated_by VARCHAR DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    -- 检查测站是否存在
    IF NOT EXISTS (SELECT 1 FROM gps_station_info WHERE station_code = p_station_code AND is_deleted = FALSE) THEN
        RAISE EXCEPTION '测站编码 % 不存在或已删除', p_station_code;
    END IF;
    
    -- 软删除
    UPDATE gps_station_info
    SET is_deleted = TRUE,
        updated_by = p_updated_by,
        updated_at = CURRENT_TIMESTAMP
    WHERE station_code = p_station_code;
    
    RAISE NOTICE '成功删除测站：%', p_station_code;
END;
$$ LANGUAGE plpgsql;

-- 14. 查询测站最新形变数据的函数
CREATE OR REPLACE FUNCTION get_latest_deformation(p_station_id INT)
RETURNS TABLE (
    observation_time TIMESTAMP,
    deformation_x DECIMAL,
    deformation_y DECIMAL,
    deformation_z DECIMAL,
    deformation_total DECIMAL,
    data_quality VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.observation_time,
        d.deformation_x,
        d.deformation_y,
        d.deformation_z,
        d.deformation_total,
        d.data_quality
    FROM gps_deformation_data d
    WHERE d.station_id = p_station_id
    ORDER BY d.observation_time DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- ==============================================================================
-- 示例数据插入
-- ==============================================================================

-- 15. 插入示例测站数据
-- 示例1：北京测站（使用4CHARID编码）
SELECT insert_gps_station(
    'BJ01',                     -- 测站编码（4字符）
    '北京监测站01',              -- 测站名称
    '4CHARID',                  -- 编码类型
    'GNSS',                     -- 测站类型
    116.397128,                 -- 经度
    39.916527,                  -- 纬度
    50.5,                       -- 高程
    '北京市',                    -- 省份
    '北京市',                    -- 城市
    '海淀区',                    -- 区县
    '中关村大街1号',             -- 地址
    '在用',                      -- 状态
    '2023-01-01',               -- 开始运行日期
    '重点监测区域',              -- 备注
    'admin'                     -- 创建人
);

-- 示例2：上海测站（使用4CHARID编码）
SELECT insert_gps_station(
    'SH01', '上海监测站01', '4CHARID', 'GPS',
    121.473701, 31.230416, 10.2,
    '上海市', '上海市', '浦东新区', '世纪大道1号',
    '在用', '2023-02-01',
    '沿海地区监测', 'admin'
);

-- 示例3：广州测站（使用4CHARID编码）
SELECT insert_gps_station(
    'GZ01', '广州监测站01', '4CHARID', 'GNSS',
    113.264385, 23.129110, 25.8,
    '广东省', '广州市', '天河区', '天河路123号',
    '在用', '2023-03-01',
    '城市沉降监测', 'admin'
);

-- 示例4：使用IGS编码的国际测站
SELECT insert_gps_station(
    'BJFS', '北京房山IGS站', 'IGS', 'GNSS',
    116.207000, 39.609000, 124.5,
    '北京市', '北京市', '房山区', 'IGS全球站点',
    '在用', '2020-01-01',
    'IGS国际合作站点，提供全球参考框架', 'admin'
);

-- 16. 插入示例形变数据
-- 为北京测站插入数据
DO $$
DECLARE
    v_station_id INT;
    v_time TIMESTAMP;
    i INT;
BEGIN
    -- 获取测站ID
    SELECT station_id INTO v_station_id 
    FROM gps_station_info 
    WHERE station_code = 'BJ01';
    
    -- 插入30天的模拟数据
    FOR i IN 0..29 LOOP
        v_time := CURRENT_TIMESTAMP - (i || ' days')::INTERVAL;
        
        PERFORM insert_gps_deformation(
            v_station_id,
            v_time,
            ROUND((RANDOM() * 10 - 5)::NUMERIC, 3),  -- X方向：-5到5毫米
            ROUND((RANDOM() * 10 - 5)::NUMERIC, 3),  -- Y方向：-5到5毫米
            ROUND((RANDOM() * 8 - 4)::NUMERIC, 3),   -- Z方向：-4到4毫米
            CASE WHEN RANDOM() > 0.9 THEN '一般' ELSE '良好' END,
            '模拟数据'
        );
    END LOOP;
    
    RAISE NOTICE '成功插入%天的形变数据', 30;
END $$;

-- ==============================================================================
-- 查询视图
-- ==============================================================================

-- 17. 创建测站信息统计视图
CREATE OR REPLACE VIEW v_gps_station_statistics AS
SELECT 
    s.station_id,
    s.station_code,
    s.code_type,
    s.station_name,
    s.station_type,
    s.status,
    s.province,
    s.city,
    s.longitude,
    s.latitude,
    s.elevation,
    COUNT(d.record_id) as data_count,
    MAX(d.observation_time) as latest_observation_time,
    MIN(d.observation_time) as earliest_observation_time
FROM gps_station_info s
LEFT JOIN gps_deformation_data d ON s.station_id = d.station_id
WHERE s.is_deleted = FALSE
GROUP BY s.station_id, s.station_code, s.code_type, s.station_name, 
         s.station_type, s.status, s.province, s.city, 
         s.longitude, s.latitude, s.elevation;

COMMENT ON VIEW v_gps_station_statistics IS 'GPS测站信息统计视图';

-- ==============================================================================
-- 完成提示
-- ==============================================================================
DO $$
BEGIN
    RAISE NOTICE '==========================================';
    RAISE NOTICE 'GPS测站元数据表创建完成！';
    RAISE NOTICE '==========================================';
    RAISE NOTICE '已创建的表：';
    RAISE NOTICE '  1. gps_station_info - GPS测站元数据信息表';
    RAISE NOTICE '  2. gps_deformation_data - GPS形变数据表';
    RAISE NOTICE '';
    RAISE NOTICE '已创建的函数：';
    RAISE NOTICE '  - insert_gps_station() - 插入测站';
    RAISE NOTICE '  - insert_gps_deformation() - 插入形变数据';
    RAISE NOTICE '  - update_gps_station_status() - 更新状态';
    RAISE NOTICE '  - delete_gps_station() - 删除测站';
    RAISE NOTICE '  - get_latest_deformation() - 获取最新数据';
    RAISE NOTICE '';
    RAISE NOTICE '已创建的视图：';
    RAISE NOTICE '  - v_gps_station_statistics - 测站统计视图';
    RAISE NOTICE '';
    RAISE NOTICE '已插入示例数据：4个测站（包含4CHARID和IGS编码），30天形变数据';
    RAISE NOTICE '==========================================';
END $$;

