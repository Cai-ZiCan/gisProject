# 矿井形变风险分析功能说明

## 功能概述

本功能实现了矿井/油井与形变栅格数据的叠加分析，用于识别缓冲区范围内有高形变值的油井，支持用户在前端对话框中设置形变阈值。

## 技术架构

### 前端 (Frontend)

**文件位置**: `frontend/js/Controls.js`

#### 1. 对话框增强

在矿井开采风险对话框中添加了以下新控件：

- **高形变阈值输入框**
  - ID: `deformation-threshold`
  - 默认值: 10 mm/year
  - 说明: 选择形变绝对值大于此阈值的油井（沉降或隆起风险）

- **缓冲区距离输入框**（可选）
  - ID: `buffer-distance`
  - 单位选择: 米/千米
  - 说明: 若填写，将统计缓冲区内形变值（使用最大绝对值）

#### 2. 分析流程

`executeMiningRiskAnalysis()` 函数：
1. 获取用户输入参数（图层、阈值、缓冲区等）
2. 验证输入参数
3. 调用后端API `/api/mining-deformation-analysis`
4. 接收分析结果并加载到地图

`loadDeformationAnalysisResult()` 函数：
- 将分析结果显示为矢量图层
- 根据形变值绝对值设置不同颜色（红色渐变）
- 在地图上显示油井名称和形变值

### 后端 (Backend)

#### 1. 数据库查询模块

**文件位置**: `backend/getDataFromDB.py`

提供三个核心函数：

##### `get_deformation_raster_by_layer(layer_name)`
- 验证形变图层是否存在
- 返回栅格瓦片RID列表

##### `extract_deformation_values_at_points(layer_name, mining_layer, active_only, threshold)`
- 提取矿井/油井点位置的形变值
- 使用PostGIS函数 `ST_Value(rast, geom)` 从栅格中提取值
- 使用 `ABS(ST_Value(...)) > threshold` 筛选高风险点
- 返回GeoJSON格式的特征列表

##### `extract_deformation_values_with_buffer(layer_name, mining_layer, active_only, threshold, buffer_distance, buffer_unit)`
- 创建缓冲区：`ST_Buffer(geom::geography, distance)`
- 裁剪栅格：`ST_Clip(rast, buffer_geom)`
- 统计形变值：`ST_SummaryStats()` 获取mean、max、min
- 计算最大绝对值：`GREATEST(ABS(buffer_max), ABS(buffer_min))`
- 筛选超过阈值的点

#### 2. API端点

**文件位置**: `backend/app.py`

##### `/api/mining-deformation-analysis` (POST)

**请求参数**:
```json
{
  "miningLayer": "oil_well_info",          // 必需: 矿井图层
  "deformationLayer": "v_mean_cropped_15_25", // 必需: 形变图层
  "threshold": 10.0,                       // 必需: 阈值（绝对值）
  "activeOnly": true,                      // 可选: 仅活跃状态
  "bufferDistance": 500,                   // 可选: 缓冲区距离
  "bufferUnit": "meters"                   // 可选: 单位
}
```

**响应示例**:
```json
{
  "status": "success",
  "message": "分析完成，找到 15 个高风险区域",
  "featureCount": 15,
  "geojson": {
    "type": "FeatureCollection",
    "features": [...]
  },
  "analysisParams": {...}
}
```

**错误处理**:
- 400: 参数验证失败
- 404: 图层不存在
- 500: 服务器内部错误

## 数据库要求

### 必需的表

1. **annual_defo_raster**
   - 存储形变栅格数据
   - 字段: `rid`, `rast`, `layer_name`, `upload_time`, `description`
   - 空间索引: `idx_defo_raster_gist`

2. **deformation_layer_info**
   - 形变图层元数据
   - 字段: `layer_name`, `image_count`, `start_date`, `end_date`

3. **oil_well_info**
   - 油井信息
   - 字段: `well_id`, `mine_name`, `extraction_status`, `geom`
   - 空间索引: `idx_oil_well_geom`

4. **mine_info** (可选)
   - 矿井信息
   - 字段: `mine_id`, `mine_name`, `extraction_status`, `longitude`, `latitude`

### PostGIS函数依赖

- `ST_Value(rast, geom)`: 提取栅格值
- `ST_Buffer()`: 创建缓冲区
- `ST_Clip()`: 裁剪栅格
- `ST_SummaryStats()`: 统计分析
- `ST_Intersects()`: 空间相交判断

## 使用方法

### 前端操作流程

1. 打开矿井开采风险分析对话框
2. 选择矿井/油井数据图层（如"油井分布"）
3. 选择形变分析图层（如"15-25年形变场"）
4. 设置高形变阈值（如10 mm/year）
5. （可选）设置缓冲区距离（如500米）
6. 勾选"仅显示活跃开采状态"（可选）
7. 点击"加载分析图层"按钮
8. 查看地图上高风险油井的分布和详细信息

### 后端测试

运行测试脚本：
```bash
cd backend
python test_deformation_analysis.py
```

测试内容包括：
- 基本形变分析
- 带缓冲区的形变分析
- 无效参数处理
- 不同阈值的影响

## 关键特性

### 1. 阈值采用绝对值
- 前端输入的阈值会被转换为正数：`Math.abs(threshold)`
- 后端查询使用绝对值比较：`ABS(ST_Value(...)) > threshold`
- 同时识别沉降（负值）和隆起（正值）风险

### 2. 缓冲区分析
- 支持米和千米两种单位
- 使用PostGIS的geography类型确保精确的测地距离
- 统计缓冲区内的平均值、最大值、最小值
- 使用最大绝对值作为风险判断标准

### 3. 性能优化
- 利用PostGIS空间索引加速查询
- 栅格数据已切片（100x100）
- 仅返回超过阈值的点，减少数据传输

### 4. 可视化
- 根据形变值设置不同颜色深度
- 显示油井名称和形变值标签
- 区分点位形变值和缓冲区统计值

## 配置说明

### 数据库连接配置

**文件位置**: `backend/app.py` 和 `backend/getDataFromDB.py`

```python
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": "5432",
    "database": "deformation_db",
    "user": "postgres",
    "password": "123456"
}
```

### 前端API地址配置

**文件位置**: `frontend/js/Controls.js`

```javascript
const baseUrl = (typeof API_BASE_URL !== 'undefined') 
    ? API_BASE_URL 
    : 'http://127.0.0.1:5000';
```

可在 `frontend/js/config.js` 中定义全局 `API_BASE_URL`。

## 故障排查

### 前端问题

**问题**: 点击"加载分析图层"无响应
- 检查浏览器控制台是否有错误
- 确认后端服务器正在运行
- 检查网络请求是否成功（Network标签）

**问题**: 显示"分析失败"
- 查看错误消息了解具体原因
- 检查选择的图层是否存在
- 确认数据库中有对应的数据

### 后端问题

**问题**: API返回404错误
- 检查形变图层名称是否正确
- 确认 `annual_defo_raster` 表中有对应数据
- 验证 `deformation_layer_info` 表中有图层元数据

**问题**: API返回500错误
- 查看Flask控制台的错误堆栈
- 检查数据库连接是否正常
- 确认PostGIS扩展已安装

**问题**: 查询速度慢
- 检查空间索引是否已创建
- 考虑减小查询范围或增加阈值
- 检查数据库服务器性能

### 数据库问题

**检查栅格数据**:
```sql
SELECT layer_name, COUNT(*) as tile_count 
FROM annual_defo_raster 
GROUP BY layer_name;
```

**检查油井几何列**:
```sql
SELECT COUNT(*) as wells_with_geom 
FROM oil_well_info 
WHERE geom IS NOT NULL;
```

**检查空间索引**:
```sql
SELECT indexname, tablename 
FROM pg_indexes 
WHERE tablename IN ('annual_defo_raster', 'oil_well_info');
```

## 扩展建议

### 1. 多时段对比
- 支持选择多个形变图层进行对比
- 显示形变趋势变化

### 2. 导出功能
- 导出分析结果为CSV或GeoJSON
- 生成分析报告PDF

### 3. 统计图表
- 显示形变值分布直方图
- 按状态分组的统计信息

### 4. 实时监测
- 定期自动分析
- 阈值超标预警通知

## 版本历史

**v1.0.0** (2026-01-23)
- 初始版本
- 支持点位形变值提取
- 支持缓冲区形变统计
- 基于绝对值的阈值筛选
- 前端可视化展示

## 联系支持

如有问题或建议，请查看项目文档或联系开发团队。
