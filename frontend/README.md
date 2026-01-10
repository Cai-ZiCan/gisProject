# 前端 WebGIS 模块化框架说明

本文档描述了 `frontend` 目录下 JavaScript 脚本的文件组织架构。为了方便管理和维护，我们将原有的单一脚本拆分为以下功能模块。

## 1. 📂 文件结构说明

所有的 JavaScript 逻辑脚本均位于 `frontend/js/` 目录下：

| 文件名 | 功能模块 | 描述 |
| :--- | :--- | :--- |
| **`config.js`** | **配置模块** | 存放全局常量，例如 GeoServer 的 WMS 服务地址、TileGrid 分辨率配置等。 |
| **`layers.js`** | **图层数据设置** | 负责定义和初始化所有地图图层对象（如底图 `baseLayer`、卫星图 `satelliteLayer`、WMS 业务图层 `wmsLayer`）。 |
| **`layerControls.js`** | **图层工具设置** | 包含与图层显示相关的交互逻辑工具函数，例如图例更新函数 `updateLegend()`。 |
| **`gisAnalysis.js`** | **GIS 分析工具** | 独立的 GIS 空间分析功能模块。目前包含基础的 `GISAnalysis` 对象结构，预留作后续扩展（如测量、缓冲区分析等）。 |
| **`main.js`** | **主程序入口** | 负责最终的地图初始化（`ol.Map`）、DOM 元素事件绑定以及各模块的协调运行。 |

## 2. 📝 模块详情

### config.js
- **职责**: 集中管理配置项，避免硬编码分散。
- **主要变量**: 
  - `MY_GEOSERVER_WMS`: GeoServer WMS 服务地址。
  - `gwcResolutions`: GeoWebCache 切片方案的分辨率数组。

### layers.js
- **职责**: 实例化 OpenLayers 的图层对象。
- **依赖**: 依赖 `config.js` 中的配置。
- **主要对象**: `baseLayer`, `satelliteLayer`, `wmsLayer1`, `wmsLayer2`。

### layerControls.js
- **职责**: 处理 UI 组件与地图图层之间的交互逻辑。
- **主要函数**: `updateLegend()` - 根据当前显示的图层动态请求并更新图例图片。

### gisAnalysis.js
- **职责**: 封装 GIS 空间分析算法和工具。
- **当前状态**: 提供 `init` 和 `performAnalysis` 接口框架，待具体业务逻辑填充。

### main.js
- **职责**: 程序的入口点。
- **执行逻辑**: 
  1. 初始化 `ol.Map` 对象，加载 `layers.js` 中定义的图层。
  2. 监听 `DOMContentLoaded` 事件。
  3. 绑定页面上的复选框与图层可见性控制。
  4. 启动图例更新和分析工具初始化。

## 3. ✅ 运行与维护

- **引入顺序**: 在 `index.html` 中，脚本可以通过以下顺序引入，确保依赖关系正确：
  1. `config.js`
  2. `layers.js`
  3. `layerControls.js`
  4. `gisAnalysis.js`
  5. `main.js`
- **稳健性**: `main.js` 采用了 DOM 加载检测，确保 HTML 元素（如 map 容器、控制按钮）存在后再执行操作。
