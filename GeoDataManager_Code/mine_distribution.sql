-- 用于在postsql地理空间数据库中构建矿井信息表

-- 1.创建矿井信息表
-- 内容：
-- 矿井ID、矿井名称(默认矿井名称不重复，若遇到问题需要检查)、矿井类型、矿井等级、经度、纬度、
-- 开采状态、开采起始时间、开采结束时间（若已结束开采）、备注 等字段
CREATE TABLE mine_info (
    mine_id SERIAL PRIMARY KEY,              -- 矿井ID
    mine_name VARCHAR(100) NOT NULL,         -- 矿井名称
    mine_type VARCHAR(50),                    -- 矿井类型
    mine_level VARCHAR(20),                   -- 矿井等级
    longitude DECIMAL(9,6) NOT NULL,         -- 经度
    latitude DECIMAL(9,6) NOT NULL,          -- 纬度
    extraction_status VARCHAR(50),            -- 开采状态 （Active/Stopped）
    extraction_start_time TIMESTAMP,          -- 开采起始时间
    extraction_end_time TIMESTAMP,            -- 开采结束时间
    remarks TEXT                             -- 备注
);
-- 添加检查约束，确保若状态为停止开采，则结束时间不能为空
ALTER TABLE mine_info
ADD CONSTRAINT chk_extraction_end_time
CHECK (
    (extraction_status != 'Stopped') OR 
    (extraction_status = 'Stopped' AND extraction_end_time IS NOT NULL)
);

--2.创建插入矿井信息的存储过程
-- 用于向mine_info表中插入新矿井信息
"""
-- 使用示例：
SELECT insert_mine_info(
    'Mine A', 'Coal', 'Level 1', 120.123456, 30.123456,
    'Active', '2023-01-01 00:00:00', NULL, 'Initial setup'
);
"""
CREATE OR REPLACE FUNCTION insert_mine_info(
    p_mine_name VARCHAR,               -- 矿井名称
    p_mine_type VARCHAR,               -- 矿井类型
    p_mine_level VARCHAR,              -- 矿井等级
    p_longitude DECIMAL,               -- 经度
    p_latitude DECIMAL,                -- 纬度
    p_extraction_status VARCHAR,       -- 开采状态
    p_extraction_start_time TIMESTAMP, -- 开采起始时间
    p_extraction_end_time TIMESTAMP,   -- 开采结束时间
    p_remarks TEXT                     -- 备注
) RETURNS VOID AS $$
-- 检查约束确保存储过程插入的数据符合业务逻辑
-- 2.1 检查名称是否与当前已有矿井重复,若重复则抛出异常
-- 2.2 检查开采状态与结束时间的逻辑一致性，若状态为停止开采，则结束时间不能为空，
--     若为空在以当前时间作为结束时间，并在备注中注明结束时间未知
BEGIN -- 存储过程开始
    IF p_extraction_status = 'Stopped' AND p_extraction_end_time IS NULL THEN
        p_extraction_end_time := CURRENT_TIMESTAMP;
        p_remarks := COALESCE(p_remarks, '') || ' | Extraction end time set to current time due to unknown end time.';
    END IF;

    IF EXISTS (SELECT 1 FROM mine_info WHERE mine_name = p_mine_name) THEN
        RAISE EXCEPTION 'Mine name % already exists.', p_mine_name;
    END IF;

    INSERT INTO mine_info (
        mine_name, mine_type, mine_level, longitude, latitude,
        extraction_status, extraction_start_time, extraction_end_time, remarks
    ) VALUES (
        p_mine_name, p_mine_type, p_mine_level, p_longitude, p_latitude,
        p_extraction_status, p_extraction_start_time, p_extraction_end_time, p_remarks
    );
END;

--3.更新矿井开采状态的存储过程
-- 用于更新矿井的开采状态及相关时间信息
-- 使用示例：
-- SELECT update_mine_extraction_status('Mine A', 'Stopped', '2023-06-01 00:00:00', 'Temporary halt in extraction');
CREATE OR REPLACE FUNCTION update_mine_extraction_status(
    p_mine_name VARCHAR,               -- 矿井名称
    p_extraction_status VARCHAR,       -- 新开采状态
    p_extraction_end_time TIMESTAMP,   -- 新开采结束时间
    p_remarks TEXT                     -- 备注信息
) RETURNS VOID AS $$
BEGIN
    -- 3.1 检查矿井名称是否存在，若不存在则抛出异常
    IF NOT EXISTS (SELECT 1 FROM mine_info WHERE mine_name = p_mine_name) THEN
        RAISE EXCEPTION 'Mine name % does not exist.', p_mine_name;
    END IF;

    -- 3.2 检查状态与结束时间的逻辑一致性
    IF p_extraction_status = 'Stopped' AND p_extraction_end_time IS NULL THEN
        RAISE EXCEPTION 'Extraction end time must be provided when status is Stopped.';
    END IF;

    UPDATE mine_info
    SET extraction_status = p_extraction_status,
        extraction_end_time = p_extraction_end_time,
        remarks = COALESCE(remarks, '') || ' | ' || COALESCE(p_remarks, '')
    WHERE mine_name = p_mine_name;
END;