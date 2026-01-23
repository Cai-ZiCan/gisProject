// 主程序模块：负责地图初始化和界面事件绑定
// 对应需求：窗口界面显示的主函数

// 地图初始化 (Main Function)
const map = new ol.Map({
    target: 'map',
    layers: [satelliteLayer, baseLayer, wmsLayer1, wmsLayer2],
    view: new ol.View({ projection: 'EPSG:4326', center: [-118.15, 33.95], zoom: 9 })
});

// 创建油井图层
let oilWellLayer = null;

// 预缓存油井样式 - 固定符号，避免每次渲染都创建新对象
const oilWellStyles = {
    'Active': new ol.style.Style({
        image: new ol.style.Circle({
            radius: 5,
            fill: new ol.style.Fill({ color: 'rgba(255, 140, 0, 0.8)' }),  // 橙色 - 活跃
            stroke: new ol.style.Stroke({ color: 'rgba(255, 100, 0, 1)', width: 1.5 })
        })
    }),
    'Stopped': new ol.style.Style({
        image: new ol.style.Circle({
            radius: 5,
            fill: new ol.style.Fill({ color: 'rgba(128, 128, 128, 0.6)' }),  // 灰色 - 停止
            stroke: new ol.style.Stroke({ color: 'rgba(100, 100, 100, 1)', width: 1.5 })
        })
    }),
    'default': new ol.style.Style({
        image: new ol.style.Circle({
            radius: 5,
            fill: new ol.style.Fill({ color: 'rgba(100, 149, 237, 0.7)' }),  // 蓝色 - 未知
            stroke: new ol.style.Stroke({ color: 'rgba(70, 130, 180, 1)', width: 1.5 })
        })
    })
};

/**
 * 加载油井点位数据并显示在地图上
 */
function loadOilWellsLayer() {
    console.log('🚀 开始加载油井数据 (BBOX策略)...');
    const baseUrl = (typeof API_BASE_URL !== 'undefined') ? API_BASE_URL : 'http://localhost:5000';
    
    // 创建矢量数据源 - 使用 Loader 和 BBOX 策略
    const vectorSource = new ol.source.Vector({
        format: new ol.format.GeoJSON(),
        loader: function(extent, resolution, projection) {
            // 投影转换 (因为 OpenLayers 内部视图通常是 EPSG:3857, 但我们通常交换 4326)
            // 这里我们请求 EPSG:4326 的 bbox, 因为我们的 API 期望该格式
            const proj = projection.getCode();
            const bbox = ol.proj.transformExtent(extent, proj, 'EPSG:4326');
            console.log(`📡 请求范围: ${bbox.join(',')}`);
            
            const url = `${baseUrl}/api/oil-wells?bbox=${bbox.join(',')}`;
            
            fetch(url)
                .then(response => {
                    if (!response.ok) throw new Error(`HTTP ${response.status}`);
                    return response.json();
                })
                .then(data => {
                    console.log(`📦 收到数据: ${data.count} 个点`);
                    if (data.features) {
                        const features = vectorSource.getFormat().readFeatures(data, {
                            dataProjection: 'EPSG:4326',
                            featureProjection: projection
                        });
                        vectorSource.addFeatures(features);
                    }
                })
                .catch(error => {
                    console.error('❌ 加载油井数据失败:', error);
                    vectorSource.removeLoadedExtent(extent); // 失败时允许重试
                });
        },
        strategy: ol.loadingstrategy.bbox
    });

    // 优化后的样式函数：直接返回预缓存的样式对象
    const styleFunction = function(feature) {
        const status = feature.get('status');
        // 直接返回预定义的样式对象，无需每次创建
        return oilWellStyles[status] || oilWellStyles['default'];
    };

    // 如果图层已存在，先移除
    if (oilWellLayer) {
        map.removeLayer(oilWellLayer);
    }
    
    // 创建矢量图层
    oilWellLayer = new ol.layer.Vector({
        source: vectorSource,
        style: styleFunction,
        visible: true,
        opacity: 0.8
    });
    
    // 设置图层属性
    oilWellLayer.set('id', 'oil-wells');
    oilWellLayer.set('title', '油井分布');
    
    // 将图层添加到地图
    map.addLayer(oilWellLayer);
    
    // 暴露到全局以便控制
    window.oilWellLayer = oilWellLayer;
    
    console.log(`✅ 油井图层对象已初始化 (数据将随后台加载)`);
    
    // ----------- 控件初始化逻辑 -----------
    
    // 重新初始化透明度控制以包含油井图层
    if (typeof initOpacityControls === 'function') {
        // 延迟一点点执行，确保图层已被处理
        setTimeout(() => {
            console.info('[Opacity] re-initializing for oil well layer');
            const layersDict = {};
            if (typeof wmsLayer1 !== 'undefined') layersDict['deformation1'] = wmsLayer1;
            if (typeof wmsLayer2 !== 'undefined') layersDict['deformation2'] = wmsLayer2;
            if (oilWellLayer) layersDict['oil-wells'] = oilWellLayer;
            initOpacityControls(map, layersDict);
        }, 100);
    }
    
    // 绑定油井图层的checkbox控制事件
    const checkbox = document.getElementById('chk-oil-wells');
    if (checkbox) {
        checkbox.onchange = null;
        checkbox.checked = oilWellLayer.getVisible();
        
        checkbox.onchange = function(e) {
            if (window.oilWellLayer) {
                window.oilWellLayer.setVisible(e.target.checked);
            }
        };
        console.log('✅ 油井图层控件已绑定');
    }
    
    // 添加点击事件显示详细信息
    // 注意：由于现在是BBOX加载，点击事件不需要改变，因为点击时该位置的要素必然已经加载
    map.on('click', function(evt) {
        const feature = map.forEachFeatureAtPixel(evt.pixel, function(feature, layer) {
            if (layer === oilWellLayer) return feature;
        });
        
        if (feature) {
            const props = feature.getProperties();
            const popupContent = `
                <div style="padding: 10px; max-width: 250px;">
                    <h4 style="margin: 0 0 8px 0; color: #333;">🛢️ ${props.name || '未命名油井'}</h4>
                    <table style="font-size: 13px; width: 100%;">
                        <tr><td><strong>API编号:</strong></td><td>${props.api || '-'}</td></tr>
                        <tr><td><strong>类型:</strong></td><td>${props.type || '-'}</td></tr>
                        <tr><td><strong>状态:</strong></td><td>${props.status || '-'}</td></tr>
                        <tr><td><strong>井深:</strong></td><td>${props.depth_ft ? props.depth_ft.toFixed(1) + ' ft' : '-'}</td></tr>
                        <tr><td><strong>位置:</strong></td><td>${props.longitude?.toFixed(5)}, ${props.latitude?.toFixed(5)}</td></tr>
                    </table>
                </div>
            `;
            showInfoPopup(evt.coordinate, popupContent);
        }
    });
}

/**
 * 显示信息弹窗
 */
function showInfoPopup(coordinate, content) {
    // 检查是否已有弹窗元素
    let popup = document.getElementById('ol-popup');
    let popupOverlay = null;
    
    if (!popup) {
        // 创建弹窗元素
        popup = document.createElement('div');
        popup.id = 'ol-popup';
        popup.className = 'ol-popup';
        popup.innerHTML = `
            <a href="#" id="popup-closer" class="ol-popup-closer"></a>
            <div id="popup-content"></div>
        `;
        document.body.appendChild(popup);
        
        // 添加样式
        const style = document.createElement('style');
        style.textContent = `
            .ol-popup {
                position: absolute;
                background-color: white;
                box-shadow: 0 1px 4px rgba(0,0,0,0.2);
                padding: 15px;
                border-radius: 10px;
                border: 1px solid #cccccc;
                bottom: 12px;
                left: -50px;
                min-width: 200px;
            }
            .ol-popup:after, .ol-popup:before {
                top: 100%;
                border: solid transparent;
                content: " ";
                height: 0;
                width: 0;
                position: absolute;
                pointer-events: none;
            }
            .ol-popup:after {
                border-top-color: white;
                border-width: 10px;
                left: 48px;
                margin-left: -10px;
            }
            .ol-popup:before {
                border-top-color: #cccccc;
                border-width: 11px;
                left: 48px;
                margin-left: -11px;
            }
            .ol-popup-closer {
                text-decoration: none;
                position: absolute;
                top: 2px;
                right: 8px;
                font-size: 20px;
                color: #999;
            }
            .ol-popup-closer:after {
                content: "✖";
            }
        `;
        document.head.appendChild(style);
        
        // 创建 Overlay
        popupOverlay = new ol.Overlay({
            element: popup,
            autoPan: true,
            autoPanAnimation: { duration: 250 }
        });
        map.addOverlay(popupOverlay);
        window.popupOverlay = popupOverlay;
        
        // 关闭按钮事件
        document.getElementById('popup-closer').onclick = function() {
            popupOverlay.setPosition(undefined);
            return false;
        };
    } else {
        popupOverlay = window.popupOverlay;
    }
    
    // 更新内容并显示
    document.getElementById('popup-content').innerHTML = content;
    popupOverlay.setPosition(coordinate);
}

// 确保 GIS 工具栏渲染（可多次调用，内部会清空容器）
function renderGISToolbar() {
    if (typeof initGISTools === 'function') {
        initGISTools(map);
    }
}

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

    // 绑定油井图层控制 - 临时绑定，实际绑定在图层加载后
    const oilWellCheckbox = document.getElementById('chk-oil-wells');
    if (oilWellCheckbox) {
        console.log('📌 找到油井checkbox元素，等待图层加载...');
        oilWellCheckbox.onchange = function(e) {
            console.log(`⚠️ 油井checkbox被点击，但图层可能尚未加载`);
            // 通过 window.oilWellLayer 访问，确保获取最新的图层对象
            if (window.oilWellLayer) {
                window.oilWellLayer.setVisible(e.target.checked);
                console.log(`🛢️ 油井图层可见性设置为: ${e.target.checked}`);
            } else {
                console.warn('⚠️ 油井图层尚未加载，请等待数据加载完成');
                // 恢复checkbox状态
                e.target.checked = !e.target.checked;
            }
        };
    } else {
        console.error('❌ 未找到 chk-oil-wells 元素');
    }

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

    // 初始化 GIS 工具栏（再调用一次，保证 DOM 就绪时渲染）
    renderGISToolbar();
    
    // 初始状态确认 (虽然 layers.js 中已经设置了 initial visible, 但这里再次确认逻辑一致性)
    wmsLayer1.setVisible(true);
    wmsLayer2.setVisible(true);

    // 初始化 GIS 分析模块 (如果有)
    if (typeof GISAnalysis !== 'undefined' && typeof GISAnalysis.init === 'function') {
        GISAnalysis.init(map);
    } else if (typeof initGISAnalysis === 'function') {
        initGISAnalysis(map);
    }

    // 加载油井图层
    loadOilWellsLayer();

    // 添加 GIS 工具栏按钮
    const toolbar = document.getElementById('gis-toolbar');
    if (toolbar) {
        const bufferBtn = document.createElement('button');
        bufferBtn.className = 'gis-tool-btn';
        bufferBtn.setAttribute('data-title', '缓冲区分析');
        bufferBtn.innerHTML = '📐';
        bufferBtn.onclick = function() {
            GISAnalysis.showBufferDialog();
        };
        toolbar.appendChild(bufferBtn);

        // 新增：清除缓冲区按钮
        const clearBufferBtn = document.createElement('button');
        clearBufferBtn.className = 'gis-tool-btn';
        clearBufferBtn.setAttribute('data-title', '清除缓冲区');
        clearBufferBtn.innerHTML = '🗑️';
        clearBufferBtn.onclick = function() {
            if (typeof GISAnalysis !== 'undefined' && GISAnalysis.clearBufferResult) {
                GISAnalysis.clearBufferResult();
            }
        };
        toolbar.appendChild(clearBufferBtn);
        console.log('✅ 缓冲区工具按钮已添加');
    } else {
        console.error('❌ 未找到 gis-toolbar 容器');
    }

});

// 首次脚本加载时即尝试渲染，避免某些环境未触发 DOMContentLoaded 时工具栏缺失
renderGISToolbar();
console.log('Main.js loaded - Version 2026.01.20-Updated');
