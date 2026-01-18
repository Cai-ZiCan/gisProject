// 工具模块：包含与图层显示、GIS分析相关的工具的图标界面和交互逻辑
// 对应需求：与图层显示相关的工具设置

// 图层图例更新逻辑
function updateLegend() {
    const container = document.getElementById('legend-container');
    const img = document.getElementById('legend-image');
    if (!container || !img) {
        console.warn('Legend elements not found');
        return;
    }
    let activeLayer = null;

    if (typeof wmsLayer2 !== 'undefined' && wmsLayer2.getVisible()) activeLayer = 'deformation:v_mean_cropped_15_25';
    else if (typeof wmsLayer1 !== 'undefined' && wmsLayer1.getVisible()) activeLayer = 'deformation:V_mean_cropped_15_18';

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

// 透明度控制初始化
// map: 可选，若传入则从 map.getLayers() 自动补充图层列表
function initOpacityControls(map = null, extraLayers = {}) {
    console.info('[Opacity] initOpacityControls start');
    const selectEl = document.getElementById('opacity-layer-select');
    const sliderEl = document.getElementById('opacity-slider');
    const valueEl = document.getElementById('opacity-value');

    if (!selectEl || !sliderEl || !valueEl) {
        console.warn('[Opacity] elements not found', { selectEl, sliderEl, valueEl });
        return;
    }

    // 汇总可控制的图层
    const layerEntries = [];
    const pushLayer = (key, label, layer) => {
        if (layer && typeof layer.setOpacity === 'function') {
            layerEntries.push({ key, label, layer });
        }
    };

    pushLayer('base', '街道底图', window.baseLayer);
    pushLayer('satellite', '卫星影像', window.satelliteLayer);
    pushLayer('deformation1', '15-18形变场', window.wmsLayer1 || extraLayers['deformation1']);
    pushLayer('deformation2', '15-25形变场', window.wmsLayer2 || extraLayers['deformation2']);

    // 合并额外传入的图层
    Object.keys(extraLayers || {}).forEach(key => {
        if (!layerEntries.find(item => item.key === key)) {
            pushLayer(key, key, extraLayers[key]);
        }
    });

    // 如果传入 map，则自动扫描地图中的图层
    if (map && typeof map.getLayers === 'function') {
        const arr = typeof map.getLayers().getArray === 'function'
            ? map.getLayers().getArray()
            : map.getLayers();
        (arr || []).forEach((layer, idx) => {
            if (!layer || typeof layer.setOpacity !== 'function') return;
            const key = layer.get('id') || layer.get('name') || `layer-${idx}`;
            const label = layer.get('title') || key;
            if (!layerEntries.find(item => item.key === key)) {
                layerEntries.push({ key, label, layer });
            }
        });
    }

    console.info('[Opacity] layer entries:', layerEntries.map(l => ({ key: l.key, title: l.label })));

    // 填充下拉选项
    selectEl.innerHTML = '<option value="">请选择</option>';
    layerEntries.forEach(item => {
        const opt = document.createElement('option');
        opt.value = item.key;
        opt.textContent = item.label;
        selectEl.appendChild(opt);
    });

    let activeLayer = null;

    const syncSlider = () => {
        if (!activeLayer) {
            sliderEl.disabled = true;
            sliderEl.value = 1;
            valueEl.textContent = '100%';
            return;
        }
        const op = typeof activeLayer.getOpacity === 'function' ? activeLayer.getOpacity() : 1;
        sliderEl.disabled = false;
        sliderEl.value = op;
        valueEl.textContent = Math.round(op * 100) + '%';
    };

    selectEl.onchange = () => {
        const selected = layerEntries.find(item => item.key === selectEl.value);
        activeLayer = selected ? selected.layer : null;
        syncSlider();
    };

    sliderEl.oninput = () => {
        const val = parseFloat(sliderEl.value);
        valueEl.textContent = Math.round(val * 100) + '%';
        if (activeLayer) {
            if (typeof updateLayerOpacity === 'function') {
                updateLayerOpacity(activeLayer, val);
            } else {
                activeLayer.setOpacity(val);
            }
        }
    };

    // 默认选中第一项以便直接调节
    if (layerEntries.length > 0) {
        selectEl.value = layerEntries[0].key;
        activeLayer = layerEntries[0].layer;
    }
    syncSlider();
}

// 构建GIS分析处理工具控制模块

/**
 * 初始化 GIS 工具栏
 * @param {ol.Map} map OpenLayers Map 对象
 */
function initGISTools(map) {
    const mapContainer = document.getElementById('map-container');
    if (!mapContainer) return;

    // 创建工具栏容器
    const toolbar = document.createElement('div');
    toolbar.className = 'gis-toolbar';
    toolbar.id = 'gis-tools-panel';

    // 定义工具列表
    const tools = [
        {
            id: 'btn-mining-risk',
            icon: '⛏️', 
            title: '矿井开采风险预警',
            action: () => toggleMiningRiskTool(map)
        },
        {
            id: 'btn-subsidence-risk',
            icon: '🏙️',
            title: '城市沉降风险预警',
            action: () => toggleSubsidenceRiskTool(map)
        }
    ];

    // 动态生成按钮
    tools.forEach(tool => {
        const btn = document.createElement('div');
        btn.className = 'gis-tool-btn';
        btn.id = tool.id;
        btn.innerHTML = tool.icon;
        btn.setAttribute('data-title', tool.title);
        
        btn.onclick = function() {
            // 如果需要互斥，这里可以先移除所有兄弟元素的 active 类
            // Array.from(toolbar.children).forEach(c => c.classList.remove('active'));

            if (this.classList.contains('active')) {
                this.classList.remove('active');
                console.log(`[GIS Tool] ${tool.title} deactivated`);
                // 这里可以调用关闭工具的逻辑，例如移除图层
            } else {
                this.classList.add('active');
                console.log(`[GIS Tool] ${tool.title} activated`);
                tool.action();
            }
        };

        toolbar.appendChild(btn);
    });

    // 暴露添加新工具的接口到全局，方便后续扩展
    window.addGISTool = function(toolConfig) {
        // toolConfig: { id, icon, title, action }
        const btn = document.createElement('div');
        btn.className = 'gis-tool-btn';
        btn.id = toolConfig.id || ('gis-tool-' + Date.now());
        btn.innerHTML = toolConfig.icon || '🔧';
        btn.setAttribute('data-title', toolConfig.title || '新工具');
        btn.onclick = function() {
             this.classList.toggle('active');
             if (this.classList.contains('active')) {
                 if (typeof toolConfig.action === 'function') toolConfig.action();
             }
        };
        toolbar.appendChild(btn);
    };

    mapContainer.appendChild(toolbar);
}



function toggleMiningRiskTool(map) {
    console.log(">>> [Interface] 调用后端接口：获取矿井开采风险数据...");
    // TODO: 实现后端请求逻辑
    // fetch('/api/analysis/mining-risk', { method: 'POST', body: ... })
    //     .then(res => res.json())
    //     .then(data => {
    //         // 在地图上渲染风险区域
    //     });
    alert("已启动：矿井开采风险预警模块\n(后端接口预留)");
}

function toggleSubsidenceRiskTool(map) {
    console.log(">>> [Interface] 调用后端接口：获取城市沉降风险数据...");
    // TODO: 实现后端请求逻辑
    // fetch('/api/analysis/subsidence-risk')
    //     .then(...)
    alert("已启动：城市沉降风险预警模块\n(后端接口预留)");
}

