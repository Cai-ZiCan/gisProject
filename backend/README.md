# GIS Project Backend (后端分析服务)

本目录包含基于 Python Flask 的后端应用，负责核心业务逻辑处理与高级空间分析功能的实现。

## 技术栈与依赖

*   **Framework**: Python Flask
*   **Database Driver**: psycopg2 (连接 PostGIS)
*   **Libraries**: 可能包含 `Shapely`, `GeoPandas`, `NumPy` 等用于具体的空间计算。

## 功能职责

1.  **RESTful API 接口**:
    *   `app.py` 提供了前端所需的 HTTP 接口（如 GET/POST 请求）。
    *   处理跨域资源共享 (CORS) 支持。
2.  **空间分析实现 (核心)**:
    *   接收前端传输的参数（如坐标点、范围、时间段）。
    *   执行具体的空间运算逻辑（如形变趋势计算、空间聚合、缓冲区分析等）。
    *   将分析结果封装为 JSON 或 GeoJSON 格式返回给前端。
3.  **数据交互**:
    *   直接连接 `deformation_db` 数据库，执行复杂的 SQL 查询。

## 运行说明

```bash
# 安装依赖
pip install flask flask-cors psycopg2-binary

# 启动服务
python app.py
```
