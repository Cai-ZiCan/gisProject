# 南加州洛杉矶盆地垂直形变场展示、分析系统

本项目是一个基于windows系统实现的 Web GIS 系统，旨在可视化展示和分析南加州洛杉矶盆地的地表垂直形变数据。系统整合了 GPS 监测点数据与形变场栅格数据，提供交互式的地图浏览与空间分析功能。

## 📂 项目结构

本项目采用前后端分离架构，主要包含以下核心模块：

*   **`frontend/` (前端可视化)**
    *   基于 **OpenLayers** 框架开发的 Web 界面。
    *   负责地图渲染、图层控制、图例交互以及用户操作捕获。
    *   通过 AJAX/HTTP 请求与后端 API 进行通信。

*   **`backend/` (后端服务)**
    *   基于 **Python Flask** 的应用程序。
    *   提供 RESTful API 接口，响应前端请求。
    *   负责核心的空间分析计算逻辑，连接数据库进行复杂查询。

*   **`GeoDataManager_Code/` (数据与数据库)**
    *   包含数据库构建与维护的 **SQL 脚本**。
    *   负责 PostGIS 空间数据库 (`deformation_db`) 的初始化。
    *   实现数据的清洗、导入以及底层空间查询功能的封装（如 `ST_Intersects`）。

*   **`geoserve/` (地图服务器)**
    *   包含 **GeoServer** 的相关配置与运行文件。
    *   负责发布 WMS (Web Map Service) 地图服务，为前端提供底图和专题图层切片。

## 🛠️ 技术栈

*   **前端**: HTML5, CSS3, JavaScript, OpenLayers v8.2.0
*   **后端**: Python, Flask, Psycopg2
*   **数据库**: PostgreSQL, PostGIS
*   **地图服务**: GeoServer

## 🚀 快速开始

### 1. 数据库准备
进入 `GeoDataManager_Code` 目录，按照说明初始化 PostGIS 数据库并导入数据。
```bash
# 示例流程 (需根据具体脚本说明操作)
psql -U postgres -d postgres -f init_db.sql
```

### 2. 启动后端服务
进入 `backend` 目录，安装依赖并启动 API 服务。
```bash
cd backend
pip install -r requirements.txt
python app.py
```

### 3. 启动 GeoServer
运行 `geoserve/bin` 目录下的启动脚本，确保 WMS 服务可用。
```bash
# Windows
.\geoserve\bin\startup.bat
```

### 4. 访问前端
直接通过 Web 服务器（如 ServBay, Nginx 或 Live Server）托管 `frontend` 目录，或者在浏览器中打开 `frontend/index.html` (需解决跨域问题)。

## 📝 开发说明

*   **数据流向**:  
    `原始数据` -> `GeoDataManager (PostGIS)` -> `GeoServer (WMS)` -> `Frontend (Layer)`  
    `用户交互` -> `Frontend` -> `Backend (API)` -> `Database (Query)` -> `Frontend (Result)`

详细的模块说明请参考各子目录下的 `README.md` 文件。
