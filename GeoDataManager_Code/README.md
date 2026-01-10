# Geo Data Manager (数据库层与空间计算)

本目录专注于数据库的构建、数据管理以及核心空间查询功能的 **SQL 实现**。

## 核心职责

1.  **数据库构建 (Schema Design)**:
    *   构建 `deformation_db` 数据库。
    *   启用 PostGIS 扩展以支持几何类型 (`GEOMETRY`, `RASTER`).
    *   设计空间索引 (GIST) 优化查询性能。
2.  **数据处理 (ETL)**:
    *   编写 SQL 脚本将原始 GPS 监测点 csv、Shapefile 和栅格数据清洗并插入数据库。
3.  **功能实现 (SQL Logic)**:
    *   **查找调用**: 封装复杂的空间过滤逻辑（如 `ST_Intersects`, `ST_DWithin`）。
    *   此处实现的 SQL 查询将被 `backend` 服务调用，作为业务逻辑的数据底座。

## 核心文件

*   `init_db.sql`: 数据库初始化。
*   `create_tables.sql`: 表结构定义。
*   `spatial_queries.sql`: 预定义的空间分析 SQL 语句，实现具体的查找与调用逻辑。

## 技术栈

*   **Database**: PostgreSQL 14+
*   **Extension**: PostGIS 3.x
*   **Language**: SQL / PL/pgSQL