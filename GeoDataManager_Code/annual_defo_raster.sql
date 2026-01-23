-- 年均形变速率栅格数据表，用于存储GeoTIFF形变数据，支持空间分析
CREATE TABLE IF NOT EXISTS annual_defo_raster (
	rid SERIAL PRIMARY KEY,                -- 栅格ID
	rast RASTER NOT NULL,                  -- PostGIS栅格数据
	layer_name VARCHAR(100) NOT NULL,      -- 图层名，关联deformation_layer_info
	upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	description TEXT
);

-- 图层名外键约束（需保证deformation_layer_info表存在）
ALTER TABLE annual_defo_raster
	ADD CONSTRAINT fk_layer_name FOREIGN KEY (layer_name)
	REFERENCES deformation_layer_info(layer_name)
	ON UPDATE CASCADE ON DELETE CASCADE;

-- 空间索引（提升栅格空间查询效率）
CREATE INDEX IF NOT EXISTS idx_defo_raster_gist
	ON annual_defo_raster USING GIST (ST_ConvexHull(rast));
-- 实现栅格数据的存储