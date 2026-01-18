// 图层设置模块：负责定义和配置地图图层
// 对应需求：图层显示数据设置

// 1. 图层初始化

// 街道底图
const baseLayer = new ol.layer.Tile({
    source: new ol.source.XYZ({ url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}' })
});

// 标注名称供通用透明度控件展示
baseLayer.set('id', 'base');
baseLayer.set('title', '街道底图');

// 让其他脚本稳定访问图层对象（用于透明度控制等）
window.baseLayer = baseLayer;

// 卫星光学影像
const satelliteLayer = new ol.layer.Tile({
    source: new ol.source.XYZ({ url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}' })
});

satelliteLayer.set('id', 'satellite');
satelliteLayer.set('title', '卫星影像');

// 让其他脚本稳定访问图层对象（用于透明度控制等）
window.satelliteLayer = satelliteLayer;

// WMS 图层 1: 15-18形变场
const wmsLayer1 = new ol.layer.Tile({
    visible: true,
    opacity: 0.8,
    source: new ol.source.TileWMS({
        url: MY_GEOSERVER_WMS, //地理数据库WMS服务地址
        params: { 
            'LAYERS': 'deformation:v_mean_cropped_15_18', 
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

wmsLayer1.set('id', 'deformation1');
wmsLayer1.set('title', '15-18形变场');

// 让其他脚本稳定访问图层对象（用于透明度控制等）
window.wmsLayer1 = wmsLayer1;

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

wmsLayer2.set('id', 'deformation2');
wmsLayer2.set('title', '15-25形变场');

// 让其他脚本稳定访问图层对象（用于透明度控制等）
window.wmsLayer2 = wmsLayer2;

// 2.图层元数据信息显示
document.addEventListener('DOMContentLoaded', function() {
    // 监听带有 data-layer-name 属性的标签点击事件
    document.querySelectorAll('.layer-label').forEach(function(label) {
        label.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation(); // 防止触发 checkbox 选择
            
            const layerName = this.getAttribute('data-layer-name');
            if (layerName) {
                fetchLayerMetadata(layerName);
            }
        });
    });
});

function fetchLayerMetadata(layerName) {
    const modal = document.getElementById('metadata-modal');
    const content = document.getElementById('metadata-content');
    const title = document.getElementById('metadata-title');
    
    if (!modal || !content) return;

    // 显示模态框并设置为加载状态
    modal.style.display = 'block';
    title.innerText = '图层信息';
    content.innerHTML = '<div style="text-align:center; padding:20px;">正在从数据库加载元数据...</div>';

    // 调用后端 API
    // 假设后端地址已经在 config.js 中定义为 API_BASE_URL，如果没有则使用默认 localhost:5000
    const baseUrl = (typeof API_BASE_URL !== 'undefined') ? API_BASE_URL : 'http://localhost:5000';
    
    fetch(`${baseUrl}/api/layer-metadata/${layerName}`)
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            if (data.error) {
                content.innerHTML = `<p style="color:red">错误: ${data.error}</p>`;
            } else {
                // 格式化显示元数据
                content.innerHTML = `
                    <style>
                        .meta-table { width: 100%; border-collapse: collapse; }
                        .meta-table td { padding: 6px; border-bottom: 1px solid #eee; }
                        .meta-label { font-weight: bold; width: 100px; color: #555; }
                    </style>
                    <table class="meta-table">
                        <tr><td class="meta-label">图层名称:</td><td>${data.layer_name}</td></tr>
                        <tr><td class="meta-label">数据量:</td><td>${data.data_volume || '-'}</td></tr>
                        <tr><td class="meta-label">最早时间:</td><td>${data.earliest_data_time ? new Date(data.earliest_data_time).toLocaleDateString() : '-'}</td></tr>
                        <tr><td class="meta-label">最新时间:</td><td>${data.latest_data_time ? new Date(data.latest_data_time).toLocaleDateString() : '-'}</td></tr>
                        <tr><td class="meta-label">数据来源:</td><td>${data.data_source || '-'}</td></tr>
                        <tr><td class="meta-label">制作方法:</td><td>${data.production_method || '-'}</td></tr>
                        <tr><td class="meta-label">制作工具:</td><td>${data.production_tool || '-'}</td></tr>
                        <tr><td class="meta-label">备注:</td><td>${data.remarks || '无'}</td></tr>
                    </table>
                `;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            content.innerHTML = `<p style="color:red">获取元数据失败。<br>请检查后端服务是否启动。</p>`;
        });
}

/**
 * 调整图层透明度
 * @param {ol.layer.Base} layer OpenLayers 图层对象
 * @param {number} opacity 透明度值 (0-1)
 */
function updateLayerOpacity(layer, opacity) {
    if (layer && typeof layer.setOpacity === 'function') {
        layer.setOpacity(opacity);
        console.log(`[Layer] Opacity updated to ${opacity}`);
    }
}
