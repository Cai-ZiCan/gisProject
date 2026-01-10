// 图层工具模块：包含与图层显示相关的工具和交互逻辑
// 对应需求：与图层显示相关的工具设置

// 图例更新逻辑
function updateLegend() {
    const container = document.getElementById('legend-container');
    const img = document.getElementById('legend-image');
    let activeLayer = null;

    if (wmsLayer2.getVisible()) activeLayer = 'deformation:v_mean_cropped_15_25';
    else if (wmsLayer1.getVisible()) activeLayer = 'deformation:V_mean_cropped_15_18';

    if (activeLayer) {
        // 构建 URL：HEIGHT=1 配合 CSS object-fit:fill 强制压缩平滑
        img.src = `${MY_GEOSERVER_WMS}?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png` +
                  `&LAYER=${activeLayer}&WIDTH=20&HEIGHT=1` + 
                  `&LEGEND_OPTIONS=forceRule:true;dx:0;dy:0;mx:0;my:0;forceLabels:off`;
        container.style.display = 'block';
    } else {
        container.style.display = 'none';
    }
}
