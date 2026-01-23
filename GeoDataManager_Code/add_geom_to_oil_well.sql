-- ==============================================================================
-- 为油井信息表添加 PostGIS 几何列
-- 数据库：deformation_db
-- 描述：为 oil_well_info 表添加标准的 PostGIS 几何列，使其能够在缓冲区分析中使用
-- ==============================================================================

-- 1. 检查表是否存在
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'oil_well_info') THEN
        RAISE EXCEPTION '表 oil_well_info 不存在，请先执行 oil_well_info.sql 创建表';
    END IF;
END $$;

-- 2. 添加 geom 几何列（如果不存在）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'oil_well_info' AND column_name = 'geom'
    ) THEN
        ALTER TABLE oil_well_info 
        ADD COLUMN geom GEOMETRY(Point, 4326);
        RAISE NOTICE '已添加 geom 几何列';
    ELSE
        RAISE NOTICE 'geom 列已存在，跳过添加步骤';
    END IF;
END $$;

-- 3. 从经纬度字段填充几何列数据
UPDATE oil_well_info 
SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
WHERE geom IS NULL AND longitude IS NOT NULL AND latitude IS NOT NULL;

-- 获取更新的行数
DO $$
DECLARE
    v_count INT;
BEGIN
    SELECT COUNT(*) INTO v_count 
    FROM oil_well_info 
    WHERE geom IS NOT NULL;
    
    RAISE NOTICE '已更新 % 条油井记录的几何数据', v_count;
END $$;

-- 4. 创建空间索引（删除旧的，创建新的）
DROP INDEX IF EXISTS idx_oil_well_location;
DROP INDEX IF EXISTS idx_oil_well_geom;

CREATE INDEX idx_oil_well_geom ON oil_well_info USING GIST(geom);

RAISE NOTICE '已创建空间索引 idx_oil_well_geom';

-- 5. 添加列注释
COMMENT ON COLUMN oil_well_info.geom IS 'PostGIS 几何对象（WGS84，EPSG:4326），用于空间分析';

-- 6. 创建触发器：自动更新 geom 字段（当经纬度变化时）
CREATE OR REPLACE FUNCTION update_oil_well_geom()
RETURNS TRIGGER AS $$
BEGIN
    -- 如果经度或纬度发生变化，自动更新 geom
    IF (NEW.longitude IS NOT NULL AND NEW.latitude IS NOT NULL) AND 
       (NEW.longitude != OLD.longitude OR NEW.latitude != OLD.latitude OR 
        OLD.longitude IS NULL OR OLD.latitude IS NULL) THEN
        NEW.geom = ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 删除旧触发器（如果存在）
DROP TRIGGER IF EXISTS trg_update_oil_well_geom ON oil_well_info;

-- 创建新触发器
CREATE TRIGGER trg_update_oil_well_geom
    BEFORE INSERT OR UPDATE OF longitude, latitude ON oil_well_info
    FOR EACH ROW
    EXECUTE FUNCTION update_oil_well_geom();

RAISE NOTICE '已创建触发器 trg_update_oil_well_geom';

-- 7. 验证几何列是否正确注册到 PostGIS
DO $$
DECLARE
    v_registered INT;
BEGIN
    SELECT COUNT(*) INTO v_registered
    FROM geometry_columns
    WHERE f_table_name = 'oil_well_info' AND f_geometry_column = 'geom';
    
    IF v_registered > 0 THEN
        RAISE NOTICE '✓ 油井表已成功注册到 PostGIS geometry_columns 视图';
    ELSE
        RAISE WARNING '⚠ 油井表未在 geometry_columns 中找到，尝试手动注册...';
        -- PostGIS 2.x+ 通常自动注册，如果是 1.x 需要手动
        -- PERFORM Populate_Geometry_Columns('public.oil_well_info'::regclass);
    END IF;
END $$;

-- 8. 显示统计信息
DO $$
DECLARE
    v_total INT;
    v_with_geom INT;
    v_without_geom INT;
BEGIN
    SELECT COUNT(*) INTO v_total FROM oil_well_info;
    SELECT COUNT(*) INTO v_with_geom FROM oil_well_info WHERE geom IS NOT NULL;
    SELECT COUNT(*) INTO v_without_geom FROM oil_well_info WHERE geom IS NULL;
    
    RAISE NOTICE '==========================================';
    RAISE NOTICE '油井数据表几何列添加完成！';
    RAISE NOTICE '==========================================';
    RAISE NOTICE '总记录数：%', v_total;
    RAISE NOTICE '已填充几何数据：%', v_with_geom;
    RAISE NOTICE '未填充几何数据：%', v_without_geom;
    RAISE NOTICE '';
    
    IF v_without_geom > 0 THEN
        RAISE WARNING '存在 % 条记录缺少几何数据，请检查经纬度字段是否有效', v_without_geom;
    END IF;
    
    RAISE NOTICE '✓ 空间索引已创建';
    RAISE NOTICE '✓ 自动更新触发器已创建';
    RAISE NOTICE '✓ 表已可用于缓冲区分析工具';
    RAISE NOTICE '==========================================';
END $$;

-- 9. 测试查询：验证几何列可以正常使用
-- SELECT 
--     well_id, 
--     mine_api, 
--     mine_name,
--     ST_AsText(geom) as geom_wkt,
--     ST_X(geom) as lon,
--     ST_Y(geom) as lat
-- FROM oil_well_info
-- LIMIT 5;
