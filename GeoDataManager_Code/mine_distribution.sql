-- 用于在postsql地理空间数据库中构建矿井信息表

-- 1.创建矿井信息表
-- 内容：
-- 矿井ID、矿井名称、矿井类型、矿井等级、经度、纬度、
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

