# 油井数据导入系统

本目录包含用于从Shapefile读取油井数据并导入到PostgreSQL数据库的完整解决方案。

## 📁 文件说明

### 1. `oil_well_info.sql`
数据库结构定义文件，包含：
- `oil_well_info` 表结构（11个字段）
- `upsert_oil_well_info()` 存储过程（支持插入/更新）
- `update_oil_well_status()` 存储过程（更新油井状态）
- 约束、索引和统计视图

### 2. `add_oil_well_info.py`
Python数据导入脚本，功能包括：
- 严格坐标系验证（EPSG:3857）
- 自动坐标转换（3857 → 4326）
- 字段映射与数据转换
- 批量导入与错误处理

## 🔧 安装依赖

```bash
pip install psycopg2 geopandas
```

## 📊 字段映射关系

| 数据库字段 | Shapefile字段 | 转换逻辑 |
|-----------|--------------|---------|
| `mine_api` | `APINumber` | 唯一主键，直接映射 |
| `mine_name` | `LeaseName` / `FieldName` | **优先使用LeaseName** |
| `mine_type` | `FieldName` | 油田类型 |
| `mine_level` | `DistrictNu` | 区域编号 |
| `longitude` | `Longitude` | 转换为EPSG:4326，保留6位小数 |
| `latitude` | `Latitude` | 转换为EPSG:4326，保留6位小数 |
| `well_depth_ft` | `WellDepthA` | **转换为浮点数**，NULL则存NULL |
| `extraction_status` | `WellStatus` | A→Active, I/P→Stopped |
| `extraction_start_time` | `SPUDDate` | 日期解析 |
| `extraction_end_time` | `AbandonedD` | 日期解析 |
| `remarks` | `Comments` + `NLA_URL` | 字符串合并 |

## 🚀 使用步骤

### 步骤1：创建数据库表
```bash
# 连接到PostgreSQL数据库
psql -U postgres -d deformation_db

# 执行SQL脚本
\i oil_well_info.sql
```

或者使用命令行：
```bash
psql -U postgres -d deformation_db -f oil_well_info.sql
```

### 步骤2：配置Python脚本
编辑 `add_oil_well_info.py` 文件，修改以下配置：

```python
# 数据库配置
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": "5432",
    "database": "deformation_db",  # 修改为您的数据库名
    "user": "postgres",
    "password": "123456"           # 修改为您的密码
}

# Shapefile路径
SHP_FILE_PATH = r"D:\path\to\your\Oil_Wells.shp"  # 修改为实际路径
```

### 步骤3：运行导入脚本
```bash
python add_oil_well_info.py
```

## ⚠️ 重要说明

### 坐标系要求
- **源数据必须为 EPSG:3857**（Web Mercator投影坐标系）
- 如果坐标系不匹配，程序会**立即终止**并显示错误信息
- 数据会自动转换为 EPSG:4326（WGS84经纬度坐标系）存储

### API冲突处理
- 使用 `ON CONFLICT (mine_api) DO UPDATE` 策略
- 当API编号重复时，**覆盖更新**所有字段

### NULL值处理
- `WellDepthA` 为NULL时，存储为NULL（不做转换）
- `extraction_end_time` 为NULL且状态为Stopped时，自动设置为当前时间

## 📈 数据统计查询

导入完成后，可使用以下SQL查询统计信息：

```sql
-- 查看所有油井信息
SELECT * FROM oil_well_info;

-- 按状态统计
SELECT extraction_status, COUNT(*) 
FROM oil_well_info 
GROUP BY extraction_status;

-- 查看状态统计视图
SELECT * FROM oil_well_status_stats;

-- 查询特定API的油井
SELECT * FROM oil_well_info 
WHERE mine_api = '04120334567';

-- 查询活跃油井
SELECT mine_name, mine_api, longitude, latitude 
FROM oil_well_info 
WHERE extraction_status = 'Active';
```

## 🐛 常见问题

### 1. 坐标系验证失败
**错误信息**：`错误：坐标系不匹配！期望坐标系：EPSG:3857`

**解决方案**：
- 检查Shapefile的坐标系统
- 使用QGIS或ArcGIS将数据重投影为EPSG:3857
- 或修改脚本中的 `SOURCE_EPSG` 配置（不推荐）

### 2. 数据库连接失败
**错误信息**：`psycopg2.OperationalError: could not connect to server`

**解决方案**：
- 检查PostgreSQL服务是否运行
- 确认数据库名、用户名、密码是否正确
- 检查防火墙设置

### 3. 井深转换失败
**警告信息**：`[警告] 井深转换失败: xxx`

**说明**：
- 这是预期行为，不影响其他字段
- 该记录的 `well_depth_ft` 字段会存储为NULL
- 建议检查源数据质量

## 📝 示例输出

```
============================================================
油井数据导入程序 v1.0
============================================================
数据库: 127.0.0.1:5432/deformation_db
用户: postgres
目标坐标系: EPSG:4326
源坐标系要求: EPSG:3857 (严格验证)
============================================================

============================================================
[步骤1] 读取Shapefile
============================================================
文件路径: D:\GIS\Oil_Wells.shp
[成功] 读取到 1234 条记录

============================================================
[步骤2] 坐标系验证
============================================================
[验证通过] 坐标系：EPSG:3857 (Web Mercator)

============================================================
[步骤3] 坐标系转换
============================================================
转换: EPSG:3857 → EPSG:4326
[成功] 坐标系已转换为 EPSG:4326

============================================================
[完成] 导入统计
============================================================
  ✓ 成功: 1230 条
  ✗ 失败: 4 条
  ∑ 总计: 1234 条
  成功率: 99.68%
============================================================
```

## 📄 许可证

本代码遵循项目统一许可证。
