-- 油井信息表数据库结构
-- 用于在PostgreSQL地理空间数据库中构建油井信息表

-- ========================================
-- 1. 创建油井信息表
-- ========================================
-- 表结构包含：油井ID、API编号、油井名称、油井类型、区域编号、经度、纬度、
-- 井深、开采状态、开采起始时间、开采结束时间、备注等字段
CREATE TABLE IF NOT EXISTS oil_well_info (
    well_id SERIAL PRIMARY KEY,                  -- 油井ID（自增主键）
    mine_api VARCHAR(50) UNIQUE NOT NULL,        -- API编号（唯一标识，对应APINumber）
    mine_name VARCHAR(100) NOT NULL,             -- 油井名称（对应LeaseName或FieldName）
    mine_type VARCHAR(100),                      -- 油井类型（对应FieldName）
    mine_level VARCHAR(20),                      -- 区域编号（对应DistrictNu）
    longitude DECIMAL(9,6) NOT NULL,             -- 经度（EPSG:4326）
    latitude DECIMAL(9,6) NOT NULL,              -- 纬度（EPSG:4326）
    well_depth_ft DECIMAL(10,2),                 -- 井深（英尺，对应WellDepthA转换后的值）
    extraction_status VARCHAR(50),               -- 开采状态（Active/Stopped）
    extraction_start_time TIMESTAMP,             -- 开采起始时间（对应SPUDDate）
    extraction_end_time TIMESTAMP,               -- 开采结束时间（对应AbandonedD）
    remarks TEXT                                 -- 备注（Comments + NLA_URL合并）
);

-- ========================================
-- 2. 添加表约束
-- ========================================
-- 添加检查约束：确保若状态为停止开采，则结束时间不能为空
ALTER TABLE oil_well_info
DROP CONSTRAINT IF EXISTS chk_extraction_end_time;

ALTER TABLE oil_well_info
ADD CONSTRAINT chk_extraction_end_time
CHECK (
    (extraction_status != 'Stopped') OR 
    (extraction_status = 'Stopped' AND extraction_end_time IS NOT NULL)
);

-- ========================================
-- 3. 创建索引
-- ========================================
-- 创建空间索引以提高地理空间查询性能
DROP INDEX IF EXISTS idx_oil_well_location;
CREATE INDEX idx_oil_well_location ON oil_well_info 
USING GIST (ST_MakePoint(longitude, latitude));

-- 为API编号创建索引（提高查询性能）
DROP INDEX IF EXISTS idx_oil_well_api;
CREATE INDEX idx_oil_well_api ON oil_well_info(mine_api);

-- 为开采状态创建索引
DROP INDEX IF EXISTS idx_oil_well_status;
CREATE INDEX idx_oil_well_status ON oil_well_info(extraction_status);

-- ========================================
-- 4. 创建插入或更新油井信息的存储过程（UPSERT逻辑）
-- ========================================
-- 用于向oil_well_info表中插入新油井信息或更新已有信息
-- 使用ON CONFLICT实现UPSERT（如果API已存在则覆盖更新）
CREATE OR REPLACE FUNCTION upsert_oil_well_info(
    p_mine_api VARCHAR,                  -- API编号（唯一标识）
    p_mine_name VARCHAR,                 -- 油井名称
    p_mine_type VARCHAR,                 -- 油井类型
    p_mine_level VARCHAR,                -- 区域编号
    p_longitude DECIMAL,                 -- 经度
    p_latitude DECIMAL,                  -- 纬度
    p_well_depth_ft DECIMAL,             -- 井深（英尺）
    p_extraction_status VARCHAR,         -- 开采状态
    p_extraction_start_time TIMESTAMP,   -- 开采起始时间
    p_extraction_end_time TIMESTAMP,     -- 开采结束时间
    p_remarks TEXT                       -- 备注
) RETURNS VOID AS $$
BEGIN
    -- 检查API编号是否为空
    IF p_mine_api IS NULL OR p_mine_api = '' THEN
        RAISE EXCEPTION 'API编号不能为空';
    END IF;

    -- 检查状态与结束时间的逻辑一致性
    IF p_extraction_status = 'Stopped' AND p_extraction_end_time IS NULL THEN
        p_extraction_end_time := CURRENT_TIMESTAMP;
        p_remarks := COALESCE(p_remarks, '') || ' | 自动设置结束时间为当前时间（原始数据中结束时间为空）';
        RAISE NOTICE '油井 API % 状态为Stopped但无结束时间，已自动设置为当前时间', p_mine_api;
    END IF;

    -- 使用ON CONFLICT实现UPSERT（API冲突时覆盖所有字段）
    INSERT INTO oil_well_info (
        mine_api, mine_name, mine_type, mine_level, 
        longitude, latitude, well_depth_ft, extraction_status, 
        extraction_start_time, extraction_end_time, remarks
    ) VALUES (
        p_mine_api, p_mine_name, p_mine_type, p_mine_level,
        p_longitude, p_latitude, p_well_depth_ft, p_extraction_status,
        p_extraction_start_time, p_extraction_end_time, p_remarks
    )
    ON CONFLICT (mine_api) DO UPDATE SET
        mine_name = EXCLUDED.mine_name,
        mine_type = EXCLUDED.mine_type,
        mine_level = EXCLUDED.mine_level,
        longitude = EXCLUDED.longitude,
        latitude = EXCLUDED.latitude,
        well_depth_ft = EXCLUDED.well_depth_ft,
        extraction_status = EXCLUDED.extraction_status,
        extraction_start_time = EXCLUDED.extraction_start_time,
        extraction_end_time = EXCLUDED.extraction_end_time,
        remarks = EXCLUDED.remarks;
        
    RAISE NOTICE '油井 API % 数据已插入或更新', p_mine_api;
END;
$$ LANGUAGE plpgsql;

-- ========================================
-- 5. 创建更新油井开采状态的存储过程
-- ========================================
-- 用于更新油井的开采状态及相关时间信息
CREATE OR REPLACE FUNCTION update_oil_well_status(
    p_mine_api VARCHAR,                  -- API编号
    p_extraction_status VARCHAR,         -- 新开采状态
    p_extraction_end_time TIMESTAMP,     -- 新开采结束时间
    p_remarks TEXT                       -- 备注信息
) RETURNS VOID AS $$
BEGIN
    -- 检查API编号是否存在
    IF NOT EXISTS (SELECT 1 FROM oil_well_info WHERE mine_api = p_mine_api) THEN
        RAISE EXCEPTION '油井 API % 不存在', p_mine_api;
    END IF;

    -- 检查状态与结束时间的逻辑一致性
    IF p_extraction_status = 'Stopped' AND p_extraction_end_time IS NULL THEN
        RAISE EXCEPTION '当状态为Stopped时，结束时间不能为空';
    END IF;

    -- 更新状态和时间
    UPDATE oil_well_info
    SET extraction_status = p_extraction_status,
        extraction_end_time = p_extraction_end_time,
        remarks = COALESCE(remarks, '') || ' | ' || COALESCE(p_remarks, '')
    WHERE mine_api = p_mine_api;
    
    RAISE NOTICE '油井 API % 状态已更新', p_mine_api;
END;
$$ LANGUAGE plpgsql;

-- ========================================
-- 6. 创建查询统计视图
-- ========================================
-- 创建油井状态统计视图
CREATE OR REPLACE VIEW oil_well_status_stats AS
SELECT 
    extraction_status,
    COUNT(*) as well_count,
    AVG(well_depth_ft) as avg_depth_ft,
    MIN(well_depth_ft) as min_depth_ft,
    MAX(well_depth_ft) as max_depth_ft
FROM oil_well_info
WHERE well_depth_ft IS NOT NULL
GROUP BY extraction_status;

-- ========================================
-- 说明与使用示例
-- ========================================
-- 
-- 使用方法：
-- 1. 在PostgreSQL数据库中执行本SQL文件创建表和存储过程
--    psql -U postgres -d deformation_db -f oil_well_info.sql
--
-- 2. 插入或更新油井数据：
--    SELECT upsert_oil_well_info(
--        '04120334567',                    -- API编号
--        'Sample Well',                     -- 油井名称
--        'Oil Field',                       -- 油井类型
--        '01',                              -- 区域编号
--        -118.243683,                       -- 经度
--        34.052235,                         -- 纬度
--        5000.50,                           -- 井深（英尺）
--        'Active',                          -- 开采状态
--        '2020-01-15'::TIMESTAMP,          -- 开采起始时间
--        NULL,                              -- 开采结束时间
--        'This is a sample well'           -- 备注
--    );
--
-- 3. 更新油井状态：
--    SELECT update_oil_well_status(
--        '04120334567',                    -- API编号
--        'Stopped',                         -- 新状态
--        CURRENT_TIMESTAMP,                 -- 结束时间
--        'Well stopped due to maintenance' -- 备注
--    );
--
-- 4. 查询油井信息：
--    SELECT * FROM oil_well_info WHERE extraction_status = 'Active';
--
-- 5. 查看状态统计：
--    SELECT * FROM oil_well_status_stats;
--
