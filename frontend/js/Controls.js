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
    pushLayer('oil-wells', '🛢️ 油井分布', window.oilWellLayer || extraLayers['oil-wells']);

    // 合并额外传入的图层
    Object.keys(extraLayers || {}).forEach(key => {
        if (!layerEntries.find(item => item.key === key)) {
            const layer = extraLayers[key];
            const label = layer && layer.get ? (layer.get('title') || key) : key;
            pushLayer(key, label, layer);
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
    console.log('[GIS] initGISTools called');
    const mapContainer = document.getElementById('map-container');
    if (!mapContainer) {
        console.error("Map container not found for GIS tools");
        return;
    }

    // 复用页面已有的工具栏占位容器，若不存在则创建
    let toolbar = document.getElementById('gis-toolbar');
    if (!toolbar) {
        console.log('[GIS] Creating new toolbar element');
        toolbar = document.createElement('div');
        toolbar.className = 'gis-toolbar';
        toolbar.id = 'gis-toolbar';
        // 确保添加到 DOM
        mapContainer.appendChild(toolbar);
    } else {
        console.log('[GIS] Found existing toolbar element');
        // 如果元素存在但不在 mapContainer 内（防御性编程）
        if (toolbar.parentNode !== mapContainer) {
            mapContainer.appendChild(toolbar);
        }
    }

    // 清空后再挂载按钮，避免重复渲染
    toolbar.innerHTML = '';
    // 强制可见性
    toolbar.style.display = 'flex';
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
    console.log('[GIS] Generating tools:', tools.length);
    tools.forEach(tool => {
        const btn = document.createElement('div');
        btn.className = 'gis-tool-btn';
        btn.id = tool.id;
        // 增加背景色和边框样式确保可见
        btn.style.width = '40px';
        btn.style.height = '40px';
        btn.style.backgroundColor = 'white';
        btn.style.border = '1px solid #999';
        btn.style.cursor = 'pointer';
        btn.innerHTML = `<span style="pointer-events:none; font-style:normal; font-size:24px; line-height:40px;">${tool.icon}</span>`;
        btn.setAttribute('data-title', tool.title);
        
        btn.onclick = function(e) {
            e.stopPropagation(); // 防止点击传透到地图
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
        btn.onclick = function(e) {
             e.stopPropagation();
             this.classList.toggle('active');
             if (this.classList.contains('active')) {
                 if (typeof toolConfig.action === 'function') toolConfig.action();
             }
        };
        toolbar.appendChild(btn);
    };

}



function toggleMiningRiskTool(map) {
    if (!map) return;
    showMiningRiskDialog(map);
}

// 显示矿井风险分析图层选择对话框
function showMiningRiskDialog(map) {
    const dialogHTML = `
        <div id="mining-risk-dialog" style="display:none; position:fixed; 
             top:50%; left:50%; transform:translate(-50%, -50%); 
             background:white; padding:25px; border-radius:12px; 
             box-shadow:0 8px 32px rgba(0,0,0,0.3); z-index:3000; 
             min-width:450px; max-width:600px;">
            
            <h3 style="margin:0 0 20px 0; color:#333; border-bottom:2px solid #ff4d4f; 
                       padding-bottom:10px;">
                ⛏️ 矿井开采风险分析 - 图层选择
            </h3>
            
            <!-- 矿井/油井数据图层选择 -->
            <div style="margin-bottom:20px;">
                <label style="display:block; margin-bottom:8px; font-weight:bold; color:#555;">
                    🛢️ 选择矿井/油井数据图层：
                </label>
                <select id="mining-data-layer" style="width:100%; padding:10px; 
                        border:1px solid #ddd; border-radius:6px; font-size:14px;">
                    <option value="">-- 请选择矿井/油井数据 --</option>
                </select>
                <div style="font-size:12px; color:#999; margin-top:5px;" id="mining-layer-desc"></div>
            </div>
            
            <!-- 形变分析图层选择 -->
            <div style="margin-bottom:20px;">
                <label style="display:block; margin-bottom:8px; font-weight:bold; color:#555;">
                    📊 选择形变分析图层（可选）：
                </label>
                <select id="deformation-layer" style="width:100%; padding:10px; 
                        border:1px solid #ddd; border-radius:6px; font-size:14px;">
                    <option value="">-- 不启用形变图层 --</option>
                </select>
                <div style="font-size:12px; color:#999; margin-top:5px;" id="deform-layer-desc"></div>
            </div>
            
            <!-- 分析参数 -->
            <div style="margin-bottom:20px; padding:15px; background:#f9f9f9; 
                        border-radius:6px;">
                <label style="font-size:13px; color:#666; display:flex; align-items:center; cursor:pointer;">
                    <input type="checkbox" id="show-active-only" checked style="margin-right:8px;">
                    <span>仅显示活跃开采状态的矿井/油井</span>
                </label>
            </div>
            
            <!-- 高形变阈值 -->
            <div style="margin-bottom:20px;">
                <label for="deformation-threshold" style="display:block; margin-bottom:8px; 
                       font-weight:bold; color:#555;">
                    📏 高形变阈值 (mm/year):
                </label>
                <input type="number" id="deformation-threshold" value="10" step="0.1" min="0" 
                       style="width:100%; padding:10px; border:1px solid #ddd; 
                              border-radius:6px; font-size:14px;">
                <div style="font-size:12px; color:#999; margin-top:5px;">
                    选择形变绝对值大于此阈值的油井（沉降或隆起风险）
                </div>
            </div>
            
            <!-- 缓冲区距离 -->
            <div style="margin-bottom:20px;">
                <label for="buffer-distance" style="display:block; margin-bottom:8px; 
                       font-weight:bold; color:#555;">
                    🔍 缓冲区距离 (可选):
                </label>
                <div style="display:flex; gap:10px;">
                    <input type="number" id="buffer-distance" value="" 
                           placeholder="留空则不进行缓冲区分析" step="10" min="0" 
                           style="flex:1; padding:10px; border:1px solid #ddd; 
                                  border-radius:6px; font-size:14px;">
                    <select id="buffer-unit" style="width:100px; padding:10px; border:1px solid #ddd; 
                                                    border-radius:6px; font-size:14px;">
                        <option value="meters">米</option>
                        <option value="kilometers">千米</option>
                    </select>
                </div>
                <div style="font-size:12px; color:#999; margin-top:5px;">
                    若填写，将统计缓冲区内形变值（使用最大绝对值）
                </div>
            </div>
            
            <!-- 状态提示 -->
            <div id="mining-risk-status" style="display:none; margin-bottom:15px; 
                 padding:10px; border-radius:6px;"></div>
            
            <!-- 操作按钮 -->
            <div style="display:flex; gap:10px; justify-content:flex-end;">
                <button onclick="closeMiningRiskDialog()" 
                        style="padding:10px 20px; background:#f0f0f0; 
                               border:1px solid #ccc; border-radius:6px; 
                               cursor:pointer; font-size:14px;">
                    取消
                </button>
                <button onclick="executeMiningRiskAnalysis()" 
                        style="padding:10px 20px; background:#ff4d4f; color:white; 
                               border:none; border-radius:6px; cursor:pointer; 
                               font-size:14px; font-weight:bold;">
                    加载分析图层
                </button>
            </div>
        </div>
        
        <div id="mining-risk-overlay" style="display:none; position:fixed; 
             top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.5); 
             z-index:2999;" onclick="closeMiningRiskDialog()"></div>
    `;
    
    // 添加到页面
    if (!document.getElementById('mining-risk-dialog')) {
        document.body.insertAdjacentHTML('beforeend', dialogHTML);
    }
    
    // 填充矿井图层选项
    const miningSelect = document.getElementById('mining-data-layer');
    const miningDesc = document.getElementById('mining-layer-desc');
    if (typeof MINING_LAYERS !== 'undefined' && miningSelect) {
        // 清除除了第一个选项外的所有选项，防止重复
        while (miningSelect.options.length > 1) {
            miningSelect.remove(1);
        }
        
        MINING_LAYERS.forEach(layer => {
            const option = document.createElement('option');
            option.value = layer.id;
            option.textContent = layer.name;
            option.dataset.description = layer.description;
            option.dataset.endpoint = layer.apiEndpoint;
            miningSelect.appendChild(option);
        });
        
        // 监听选择变化，显示描述
        miningSelect.addEventListener('change', function() {
            const selected = this.options[this.selectedIndex];
            if (selected && selected.dataset.description) {
                miningDesc.textContent = selected.dataset.description;
            } else {
                miningDesc.textContent = '';
            }
        });
    }
    
    // 填充形变图层选项
    const deformSelect = document.getElementById('deformation-layer');
    const deformDesc = document.getElementById('deform-layer-desc');
    if (typeof DEFORMATION_LAYERS !== 'undefined' && deformSelect) {
        // 清除除了第一个选项外的所有选项，防止重复
        while (deformSelect.options.length > 1) {
            deformSelect.remove(1);
        }
        
        DEFORMATION_LAYERS.forEach(layer => {
            const option = document.createElement('option');
            option.value = layer.name;
            option.textContent = `${layer.displayName} (${layer.dataVolume}幅影像)`;
            option.dataset.description = `${layer.description} | ${layer.timeRange}`;
            deformSelect.appendChild(option);
        });
        
        // 监听选择变化，显示描述
        deformSelect.addEventListener('change', function() {
            const selected = this.options[this.selectedIndex];
            if (selected && selected.dataset.description) {
                deformDesc.textContent = selected.dataset.description;
            } else {
                deformDesc.textContent = '';
            }
        });
    }
    
    // 显示对话框
    document.getElementById('mining-risk-dialog').style.display = 'block';
    document.getElementById('mining-risk-overlay').style.display = 'block';
    
    // 保存map引用供后续使用
    window._miningRiskMap = map;
}

// 关闭矿井风险分析对话框
function closeMiningRiskDialog() {
    const dialog = document.getElementById('mining-risk-dialog');
    const overlay = document.getElementById('mining-risk-overlay');
    if (dialog) dialog.style.display = 'none';
    if (overlay) overlay.style.display = 'none';
}

// 显示对话框状态信息
function showMiningRiskStatus(message, type = 'info') {
    const statusDiv = document.getElementById('mining-risk-status');
    if (!statusDiv) return;
    
    const colors = {
        'info': { bg: '#e6f7ff', border: '#91d5ff', text: '#0050b3' },
        'success': { bg: '#f6ffed', border: '#b7eb8f', text: '#389e0d' },
        'error': { bg: '#fff2e8', border: '#ffbb96', text: '#d4380d' },
        'warning': { bg: '#fffbe6', border: '#ffe58f', text: '#d48806' }
    };
    
    const color = colors[type] || colors['info'];
    statusDiv.style.display = 'block';
    statusDiv.style.background = color.bg;
    statusDiv.style.border = `1px solid ${color.border}`;
    statusDiv.style.color = color.text;
    statusDiv.textContent = message;
}

// 执行矿井风险分析
function executeMiningRiskAnalysis() {
    const map = window._miningRiskMap;
    if (!map) {
        alert('地图对象未初始化');
        return;
    }
    
    const miningLayerId = document.getElementById('mining-data-layer').value;
    const deformationLayerName = document.getElementById('deformation-layer').value;
    const activeOnly = document.getElementById('show-active-only').checked;
    const threshold = parseFloat(document.getElementById('deformation-threshold').value) || 10;
    const bufferDistance = document.getElementById('buffer-distance').value;
    const bufferUnit = document.getElementById('buffer-unit').value;
    
    // 验证
    if (!miningLayerId) {
        showMiningRiskStatus('请选择矿井/油井数据图层', 'error');
        return;
    }
    
    if (!deformationLayerName) {
        showMiningRiskStatus('请选择形变分析图层', 'error');
        return;
    }
    
    showMiningRiskStatus('正在执行形变叠加分析...', 'info');
    
    // 查找矿井图层配置
    let miningLayerConfig = null;
    if (typeof MINING_LAYERS !== 'undefined') {
        miningLayerConfig = MINING_LAYERS.find(l => l.id === miningLayerId);
    }
    
    if (!miningLayerConfig) {
        showMiningRiskStatus('图层配置错误', 'error');
        return;
    }
    
    // 构建请求参数
    const requestData = {
        miningLayer: miningLayerId,
        deformationLayer: deformationLayerName,
        threshold: Math.abs(threshold), // 确保阈值为正数
        activeOnly: activeOnly
    };
    
    // 如果提供了缓冲区距离，添加到请求中
    if (bufferDistance && parseFloat(bufferDistance) > 0) {
        requestData.bufferDistance = parseFloat(bufferDistance);
        requestData.bufferUnit = bufferUnit;
    }
    
    // 调用新的形变分析API
    const baseUrl = (typeof API_BASE_URL !== 'undefined') ? API_BASE_URL : 'http://127.0.0.1:5000';
    fetch(`${baseUrl}/api/mining-deformation-analysis`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showMiningRiskStatus(`分析完成！找到 ${data.featureCount} 个高风险油井`, 'success');
            
            // 加载分析结果到地图
            loadDeformationAnalysisResult(map, data.geojson, miningLayerConfig);
            
            // 切换形变图层可见性
            toggleDeformationLayerVisibility(map, deformationLayerName, true);
            
            // 延迟关闭对话框
            setTimeout(() => {
                closeMiningRiskDialog();
            }, 1500);
        } else {
            showMiningRiskStatus(`分析失败: ${data.message}`, 'error');
        }
    })
    .catch(error => {
        console.error('形变分析请求失败:', error);
        showMiningRiskStatus('分析请求失败，请检查网络连接', 'error');
    });
}

// 加载形变分析结果到地图
function loadDeformationAnalysisResult(map, geojson, layerConfig) {
    const layerId = `deformation-analysis-result-${layerConfig.id}`;
    
    // 移除已存在的分析结果图层
    if (typeof map.getLayers === 'function') {
        const existingLayer = map.getLayers().getArray().find(l => l.get('id') === layerId);
        if (existingLayer) {
            map.removeLayer(existingLayer);
        }
    }
    
    // 创建矢量源
    const vectorSource = new ol.source.Vector({
        features: new ol.format.GeoJSON().readFeatures(geojson, {
            featureProjection: 'EPSG:4326' // Map View is EPSG:4326, so we must project features to match it
        })
    });

    // 创建样式函数 - 统一突出显示高风险目标
    const styleFunction = function(feature) {
        const deformValue = feature.get('deformation_value') || 0;
        const name = feature.get('mine_name') || feature.get('name') || '';
        
        // 统一使用醒目的红色加粗边框样式
        return new ol.style.Style({
            image: new ol.style.Circle({
                radius: 12,
                fill: new ol.style.Fill({ color: '#ff0000' }), // 鲜艳的红色
                stroke: new ol.style.Stroke({ 
                    color: '#ffffff', 
                    width: 3
                })
            }),
            text: new ol.style.Text({
                text: `${name}\n${deformValue.toFixed(2)}mm/yr`, // 显示两位小数
                font: 'bold 14px "Microsoft YaHei", sans-serif',
                fill: new ol.style.Fill({ color: '#d90000' }),
                stroke: new ol.style.Stroke({ color: '#ffffff', width: 4 }),
                offsetY: -22,
                backgroundFill: new ol.style.Fill({ color: 'rgba(255, 255, 255, 0.8)', padding: [2,5,2,5] })
            }),
            zIndex: 999
        });
    };
    
    // 创建矢量图层
    const vectorLayer = new ol.layer.Vector({
        source: vectorSource,
        style: styleFunction,
        visible: true,
        zIndex: 1000 // High z-index
    });
    
    vectorLayer.set('id', layerId);
    vectorLayer.set('title', `形变分析结果 - ${layerConfig.name}`);
    
    map.addLayer(vectorLayer);
    console.log(`[Deformation Analysis] Result layer loaded with ${vectorSource.getFeatures().length} features`);
}

// 加载矿井/油井矢量图层
function loadMiningVectorLayer(map, layerConfig, activeOnly) {
    const layerId = `mining-risk-layer-${layerConfig.id}`;
    
    // 检查是否已存在该图层
    let existingLayer = null;
    if (typeof map.getLayers === 'function') {
        existingLayer = map.getLayers().getArray().find(l => l.get('id') === layerId);
    }
    
    if (existingLayer) {
        // 如果存在，切换可见性
        existingLayer.setVisible(true);
        console.log(`[Mining Risk] Layer ${layerId} already exists, showing it`);
        return;
    }
    
    // 构建API URL
    const baseUrl = (typeof API_BASE_URL !== 'undefined') ? API_BASE_URL : 'http://127.0.0.1:5000';
    let apiUrl = `${baseUrl}${layerConfig.apiEndpoint}`;
    
    // 添加参数
    const params = new URLSearchParams();
    if (activeOnly && layerConfig.id === 'oil_well_info') {
        // oil_well_info 使用 bbox 策略，过滤在样式函数中处理
        // 或者如果API支持status参数，可以添加
        params.append('active_only', 'true');
    }
    if (layerConfig.id === 'mine_info' && activeOnly) {
        params.append('active_only', 'true');
    }
    
    const queryString = params.toString();
    if (queryString) {
        apiUrl += (apiUrl.includes('?') ? '&' : '?') + queryString;
    }
    
    console.log(`[Mining Risk] Loading layer from: ${apiUrl}`);
    
    // 创建矢量源
    const vectorSource = new ol.source.Vector({
        url: apiUrl,
        format: new ol.format.GeoJSON(),
        strategy: layerConfig.id === 'oil_well_info' ? ol.loadingstrategy.bbox : ol.loadingstrategy.all
    });
    
    // 创建样式函数
    const styleFunction = function(feature) {
        const status = feature.get('extraction_status') || feature.get('status');
        const name = feature.get('mine_name') || feature.get('name') || '';
        
        // 如果仅显示活跃且当前要素非活跃，则不显示
        if (activeOnly && status !== 'Active') {
            return null; // 返回null表示不渲染该要素
        }
        
        // 根据状态设置颜色
        let fillColor = '#ff4d4f'; // 默认红色
        if (status === 'Active') {
            fillColor = '#ff8c00'; // 活跃：橙色
        } else if (status === 'Stopped') {
            fillColor = '#999'; // 停止：灰色
        }
        
        return new ol.style.Style({
            image: new ol.style.Circle({
                radius: 6,
                fill: new ol.style.Fill({ color: fillColor }),
                stroke: new ol.style.Stroke({ color: 'white', width: 2 })
            }),
            text: new ol.style.Text({
                text: name,
                font: '12px sans-serif',
                fill: new ol.style.Fill({ color: '#000' }),
                stroke: new ol.style.Stroke({ color: '#fff', width: 3 }),
                offsetY: -12
            })
        });
    };
    
    // 创建矢量图层
    const vectorLayer = new ol.layer.Vector({
        source: vectorSource,
        style: styleFunction,
        visible: true,
        zIndex: 1000 // 确保在最上层
    });
    
    vectorLayer.set('id', layerId);
    vectorLayer.set('title', layerConfig.name);
    
    map.addLayer(vectorLayer);
    console.log(`[Mining Risk] Layer ${layerConfig.name} loaded successfully`);
}

// 切换形变图层可见性
function toggleDeformationLayerVisibility(map, layerName, visible) {
    if (!map || !layerName) return;
    
    // 查找对应的形变图层
    let targetLayer = null;
    
    // 尝试从全局变量获取
    if (layerName === 'v_mean_cropped_15_18' && typeof wmsLayer1 !== 'undefined') {
        targetLayer = wmsLayer1;
    } else if (layerName === 'v_mean_cropped_15_25' && typeof wmsLayer2 !== 'undefined') {
        targetLayer = wmsLayer2;
    }
    
    // 如果没有找到，从地图图层中查找
    if (!targetLayer && typeof map.getLayers === 'function') {
        const layers = map.getLayers().getArray();
        targetLayer = layers.find(l => {
            const params = l.getSource && l.getSource().getParams ? l.getSource().getParams() : {};
            return params.LAYERS && params.LAYERS.includes(layerName);
        });
    }
    
    if (targetLayer && typeof targetLayer.setVisible === 'function') {
        targetLayer.setVisible(visible);
        console.log(`[Mining Risk] Deformation layer ${layerName} visibility set to ${visible}`);
        
        // 更新图例
        if (typeof updateLegend === 'function') {
            updateLegend();
        }
    } else {
        console.warn(`[Mining Risk] Deformation layer ${layerName} not found`);
    }
}

function toggleMiningRiskTool_OLD(map) {
    if (!map) return;
    const layerId = 'mining-risk-layer';
    
    // 检查是否已存在图层
    let layer = null;
    if (typeof map.getLayers === 'function') {
        layer = map.getLayers().getArray().find(l => l.get('id') === layerId);
    }

    if (layer) {
        // 如果存在，切换可见性
        const visible = !layer.getVisible();
        layer.setVisible(visible);
        console.log(`[GIS Tool] Mining risk layer visibility: ${visible}`);
        // 可选：提示用户
        // alert(visible ? "显示矿井图层" : "隐藏矿井图层");
        return;
    }

    console.log(">>> [Interface] 调用后端接口：获取矿井开采风险数据...");
    
    // 创建矢量源和图层
    // 注意：假设后端运行在 5000 端口
    const vectorSource = new ol.source.Vector({
        url: 'http://127.0.0.1:5000/api/analysis/mining-risk',
        format: new ol.format.GeoJSON()
    });
    
    // 创建矢量图层
    const vectorLayer = new ol.layer.Vector({
        source: vectorSource,
        style: new ol.style.Style({
            image: new ol.style.Circle({
                radius: 6,
                fill: new ol.style.Fill({color: '#ff4d4f'}),
                stroke: new ol.style.Stroke({color: 'white', width: 2})
            }),
            text: new ol.style.Text({
                font: '12px Calibri,sans-serif',
                fill: new ol.style.Fill({ color: '#000' }),
                stroke: new ol.style.Stroke({ color: '#fff', width: 2 }),
                offsetY: -10
            })
        })
    });
    
    // 简单的样式函数，用于显示名称
    vectorLayer.setStyle(function(feature) {
        const style = vectorLayer.getStyle();
        // 如果 vectorLayer.getStyle() 返回 style 对象
        // 克隆并设置 text
        // 这里简化处理，直接返回一个新的style或修改共有style(不推荐修改共有)
        const name = feature.get('name');
        return new ol.style.Style({
            image: new ol.style.Circle({
                radius: 6,
                fill: new ol.style.Fill({color: '#ff4d4f'}),
                stroke: new ol.style.Stroke({color: 'white', width: 2})
            }),
            text: new ol.style.Text({
                text: name ? name : '',
                font: '12px sans-serif',
                fill: new ol.style.Fill({ color: '#000' }),
                stroke: new ol.style.Stroke({ color: '#fff', width: 3 }),
                offsetY: -12
            })
        });
    });
    
    vectorLayer.set('id', layerId);
    vectorLayer.set('title', '矿井分布');
    
    map.addLayer(vectorLayer);
    alert("已加载矿井开采风险数据图层");
}

function toggleSubsidenceRiskTool(map) {
    console.log(">>> [Interface] 调用后端接口：获取城市沉降风险数据...");
    // TODO: 实现后端请求逻辑
    // fetch('/api/analysis/subsidence-risk')
    //     .then(...)
    alert("已启动：城市沉降风险预警模块\n(后端接口预留)");
}

