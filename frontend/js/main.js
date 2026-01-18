// 主程序模块：负责地图初始化和界面事件绑定
// 对应需求：窗口界面显示的主函数

// 地图初始化 (Main Function)
const map = new ol.Map({
    target: 'map',
    layers: [satelliteLayer, baseLayer, wmsLayer1, wmsLayer2],
    view: new ol.View({ projection: 'EPSG:4326', center: [-118.15, 33.95], zoom: 9 })
});

// 事件绑定
document.addEventListener('DOMContentLoaded', function() {
    // 绑定图层控制开关
    document.getElementById('chk-base').onchange = e => baseLayer.setVisible(e.target.checked);
    document.getElementById('chk-satellite').onchange = e => satelliteLayer.setVisible(e.target.checked);
    
    document.getElementById('chk-deformation1').onchange = e => { 
        wmsLayer1.setVisible(e.target.checked); 
        updateLegend(); 
    };
    
    document.getElementById('chk-deformation2').onchange = e => { 
        wmsLayer2.setVisible(e.target.checked); 
        updateLegend(); 
    };

    // 初始化图层透明度控制 (来自 Controls.js)
    // 传入 map 便于自动扫描所有可调节图层
    if (typeof initOpacityControls === 'function') {
        console.info('[Opacity] calling initOpacityControls');
        const layersDict = {};
        if (typeof wmsLayer1 !== 'undefined') layersDict['deformation1'] = wmsLayer1;
        if (typeof wmsLayer2 !== 'undefined') layersDict['deformation2'] = wmsLayer2;
        initOpacityControls(map, layersDict);
    }

    // 页面加载后立即初始化图例
    try {
        updateLegend();
    } catch (err) {
        console.error("Error updating legend:", err);
    }
    
    // 初始状态确认 (虽然 layers.js 中已经设置了 initial visible, 但这里再次确认逻辑一致性)
    wmsLayer1.setVisible(true);
    wmsLayer2.setVisible(true);

    // 初始化 GIS 分析模块 (如果有)
    if (typeof GISAnalysis !== 'undefined' && GISAnalysis.init) {
        GISAnalysis.init(map);
    }

});
