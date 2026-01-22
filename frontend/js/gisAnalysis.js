// GIS 分析处理工具模块
// 缓冲区建立工具

const GISAnalysis = {
    map: null,
    bufferLayer: null,  // 用于显示缓冲区结果的图层

    // 初始化分析工具
    init: function(mapInstance) {
        this.map = mapInstance;
        console.log("GIS Analysis tools initialized");
        
        // 初始化缓冲区结果图层
        this.bufferLayer = new ol.layer.Vector({
            source: new ol.source.Vector(),
            style: new ol.style.Style({
                fill: new ol.style.Fill({
                    color: 'rgba(255, 165, 0, 0.3)'  // 橙色半透明
                }),
                stroke: new ol.style.Stroke({
                    color: '#ff8c00',
                    width: 2
                })
            })
        });
        this.bufferLayer.set('id', 'buffer-result');
        this.bufferLayer.set('title', '缓冲区结果');
        this.map.addLayer(this.bufferLayer);
    },

    // 显示缓冲区建立对话框
    showBufferDialog: function() {
        // 创建对话框HTML
        const dialogHTML = `
            <div id="buffer-dialog" style="display:none; position:fixed; top:50%; left:50%; transform:translate(-50%, -50%); 
                 background:white; padding:25px; border-radius:12px; box-shadow:0 8px 32px rgba(0,0,0,0.3); 
                 z-index:3000; min-width:400px; max-width:500px;">
                <h3 style="margin:0 0 20px 0; color:#333; border-bottom:2px solid #1890ff; padding-bottom:10px;">
                    🛠️ 缓冲区建立工具
                </h3>
                
                <div style="margin-bottom:15px;">
                    <label style="display:block; margin-bottom:5px; font-weight:bold; color:#555;">
                        选择输入图层：
                    </label>
                    <select id="buffer-input-layer" style="width:100%; padding:8px; border:1px solid #ddd; border-radius:6px;">
                        <option value="">正在加载图层列表...</option>
                    </select>
                </div>
                
                <div style="margin-bottom:15px;">
                    <label style="display:block; margin-bottom:5px; font-weight:bold; color:#555;">
                        缓冲距离：
                    </label>
                    <div style="display:flex; gap:10px;">
                        <input type="number" id="buffer-distance" value="1000" min="0" step="10"
                               style="flex:1; padding:8px; border:1px solid #ddd; border-radius:6px;">
                        <select id="buffer-unit" style="width:100px; padding:8px; border:1px solid #ddd; border-radius:6px;">
                            <option value="meters">米</option>
                            <option value="kilometers">千米</option>
                            <option value="degrees">度</option>
                        </select>
                    </div>
                </div>
                
                <div style="margin-bottom:15px;">
                    <label style="display:block; margin-bottom:5px; font-weight:bold; color:#555;">
                        融合类型：
                    </label>
                    <select id="buffer-dissolve" style="width:100%; padding:8px; border:1px solid #ddd; border-radius:6px;">
                        <option value="NONE">不融合 (保留各要素独立缓冲区)</option>
                        <option value="ALL">全部融合 (合并所有重叠区域)</option>
                    </select>
                </div>
                
                <div style="margin-bottom:20px;">
                    <label style="display:block; margin-bottom:5px; font-weight:bold; color:#555;">
                        末端类型 (仅线要素)：
                    </label>
                    <select id="buffer-endtype" style="width:100%; padding:8px; border:1px solid #ddd; border-radius:6px;">
                        <option value="ROUND">圆形末端</option>
                        <option value="FLAT">平面末端</option>
                    </select>
                </div>
                
                <div id="buffer-status" style="margin-bottom:15px; padding:10px; border-radius:6px; display:none;"></div>
                
                <div style="display:flex; gap:10px; justify-content:flex-end;">
                    <button onclick="GISAnalysis.closeBufferDialog()" 
                            style="padding:10px 20px; background:#f0f0f0; border:1px solid #ccc; 
                                   border-radius:6px; cursor:pointer; font-size:14px;">
                        取消
                    </button>
                    <button onclick="GISAnalysis.executeBufferAnalysis()" 
                            style="padding:10px 20px; background:#1890ff; color:white; border:none; 
                                   border-radius:6px; cursor:pointer; font-size:14px; font-weight:bold;">
                        执行分析
                    </button>
                </div>
            </div>
            <div id="buffer-overlay" style="display:none; position:fixed; top:0; left:0; right:0; bottom:0; 
                 background:rgba(0,0,0,0.5); z-index:2999;" onclick="GISAnalysis.closeBufferDialog()"></div>
        `;
        
        // 添加到页面
        if (!document.getElementById('buffer-dialog')) {
            document.body.insertAdjacentHTML('beforeend', dialogHTML);
        }
        
        // 显示对话框
        document.getElementById('buffer-dialog').style.display = 'block';
        document.getElementById('buffer-overlay').style.display = 'block';
        
        // 加载图层列表
        this.loadAvailableLayers();
    },

    // 加载可用图层列表
    loadAvailableLayers: function() {
        const baseUrl = (typeof API_BASE_URL !== 'undefined') ? API_BASE_URL : 'http://localhost:5000';
        const select = document.getElementById('buffer-input-layer');
        
        fetch(`${baseUrl}/api/layers/list`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success' && data.layers) {
                    select.innerHTML = '<option value="">-- 请选择图层 --</option>';
                    data.layers.forEach(layer => {
                        const option = document.createElement('option');
                        option.value = layer.name;
                        option.textContent = `${layer.name} (${layer.geometryType})`;
                        option.dataset.geomColumn = layer.geomColumn;
                        option.dataset.geometryType = layer.geometryType;
                        select.appendChild(option);
                    });
                } else {
                    select.innerHTML = '<option value="">加载失败</option>';
                }
            })
            .catch(error => {
                console.error('Error loading layers:', error);
                select.innerHTML = '<option value="">加载失败</option>';
            });
    },

    // 执行缓冲区分析
    executeBufferAnalysis: function() {
        const layerSelect = document.getElementById('buffer-input-layer');
        const inputLayer = layerSelect.value;
        const distance = parseFloat(document.getElementById('buffer-distance').value);
        const unit = document.getElementById('buffer-unit').value;
        const dissolveType = document.getElementById('buffer-dissolve').value;
        const endType = document.getElementById('buffer-endtype').value;
        const statusDiv = document.getElementById('buffer-status');
        
        // 验证输入
        if (!inputLayer) {
            this.showStatus('请选择输入图层', 'error');
            return;
        }
        if (isNaN(distance) || distance <= 0) {
            this.showStatus('请输入有效的缓冲距离', 'error');
            return;
        }
        
        // 获取几何列名
        const selectedOption = layerSelect.options[layerSelect.selectedIndex];
        const geomColumn = selectedOption.dataset.geomColumn || 'geom';
        
        // 显示处理状态
        this.showStatus('正在执行缓冲区分析，请稍候...', 'loading');
        
        // 调用后端API
        const baseUrl = (typeof API_BASE_URL !== 'undefined') ? API_BASE_URL : 'http://localhost:5000';
        
        fetch(`${baseUrl}/api/analysis/create-buffer`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                inputLayer: inputLayer,
                distance: distance,
                unit: unit,
                dissolveType: dissolveType,
                endType: endType,
                geometryColumn: geomColumn
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                this.showStatus(
                    `✅ ${data.message}<br>共生成 ${data.featureCount} 个缓冲区要素`, 
                    'success'
                );
                
                // 在地图上显示结果
                if (data.geojson && data.geojson.features) {
                    this.displayBufferResult(data.geojson);
                }
                
                // 3秒后自动关闭对话框
                setTimeout(() => {
                    this.closeBufferDialog();
                }, 3000);
            } else {
                this.showStatus(`❌ 分析失败: ${data.message}`, 'error');
            }
        })
        .catch(error => {
            console.error('Buffer analysis error:', error);
            this.showStatus(`❌ 网络错误: ${error.message}`, 'error');
        });
    },

    // 在地图上显示缓冲区结果
    displayBufferResult: function(geojson) {
        if (!this.bufferLayer) return;
        
        // 清空之前的结果
        this.bufferLayer.getSource().clear();
        
        // 解析GeoJSON并添加到图层
        const features = new ol.format.GeoJSON().readFeatures(geojson, {
            dataProjection: 'EPSG:4326',
            featureProjection: this.map.getView().getProjection()
        });
        
        this.bufferLayer.getSource().addFeatures(features);
        
        // 缩放到结果范围
        if (features.length > 0) {
            const extent = this.bufferLayer.getSource().getExtent();
            this.map.getView().fit(extent, {
                padding: [50, 50, 50, 50],
                duration: 1000
            });
        }
    },

    // 显示状态消息
    showStatus: function(message, type) {
        const statusDiv = document.getElementById('buffer-status');
        if (!statusDiv) return;
        
        statusDiv.style.display = 'block';
        statusDiv.innerHTML = message;
        
        if (type === 'error') {
            statusDiv.style.background = '#fff2f0';
            statusDiv.style.border = '1px solid #ffccc7';
            statusDiv.style.color = '#cf1322';
        } else if (type === 'success') {
            statusDiv.style.background = '#f6ffed';
            statusDiv.style.border = '1px solid #b7eb8f';
            statusDiv.style.color = '#52c41a';
        } else if (type === 'loading') {
            statusDiv.style.background = '#e6f7ff';
            statusDiv.style.border = '1px solid #91d5ff';
            statusDiv.style.color = '#1890ff';
        }
    },

    // 关闭对话框
    closeBufferDialog: function() {
        const dialog = document.getElementById('buffer-dialog');
        const overlay = document.getElementById('buffer-overlay');
        if (dialog) dialog.style.display = 'none';
        if (overlay) overlay.style.display = 'none';
    }
};