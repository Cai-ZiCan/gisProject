// 图层设置模块：负责定义和配置地图图层
// 对应需求：图层显示数据设置

// 1. 图层初始化

// 街道底图
const baseLayer = new ol.layer.Tile({
    source: new ol.source.XYZ({ url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}' })
});

// 卫星光学影像
const satelliteLayer = new ol.layer.Tile({
    source: new ol.source.XYZ({ url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}' })
});

// WMS 图层 1: 15-18形变场
const wmsLayer1 = new ol.layer.Tile({
    visible: true,
    opacity: 0.8,
    source: new ol.source.TileWMS({
        url: MY_GEOSERVER_WMS, //地理数据库WMS服务地址
        params: { 
            'LAYERS': 'deformation:V_mean_cropped_15_18', 
            'TILED': true, 
            'SRS': 'EPSG:4326', // 显式声明坐标系
            'FORMAT': 'image/png', 
            'version': '1.3.0',
            'TRANSPARENT': true 
        },
        // 关键：定义 TileGrid 强制 OpenLayers 发送符合 GWC 标准的 BBOX
        tileGrid: new ol.tilegrid.TileGrid({
            origin: [-180, 90], // EPSG:4326 标准原点
            resolutions: gwcResolutions,
            tileSize: [256, 256]
        }),
        hidpi: false,
        serverType: 'geoserver',
        crossOrigin: 'anonymous'
    })
});

// WMS 图层 2: 15-25形变场
const wmsLayer2 = new ol.layer.Tile({
    visible: true,
    opacity: 0.8,
    source: new ol.source.TileWMS({
        url: MY_GEOSERVER_WMS,
        params: { 'LAYERS': 'deformation:v_mean_cropped_15_25', 'TILED': true, 'TRANSPARENT': true, 'version': '1.3.0' },
        // 关键：定义 TileGrid 强制 OpenLayers 发送符合 GWC 标准的 BBOX
        tileGrid: new ol.tilegrid.TileGrid({
            origin: [-180, 90], // EPSG:4326 标准原点
            resolutions: gwcResolutions,
            tileSize: [256, 256]
        }),
        hidpi: false,
        serverType: 'geoserver',
        crossOrigin: 'anonymous'
    })
});
