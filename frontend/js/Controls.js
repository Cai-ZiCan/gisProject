// 工具模块：包含与图层显示、GIS分析相关的工具的图标界面和交互逻辑
// 对应需求：与图层显示相关的工具设置

// 图层图例更新逻辑
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

// ----------------------
// 预留的工具逻辑接口 (后端调用占位符)
// ----------------------

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

