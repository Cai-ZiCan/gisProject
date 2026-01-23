// 配置文件：包含全局常量和基础设置
// 对应需求：图层显示 data settings (partially) or general config

// --- 请务必修改这里 ---
const MY_GEOSERVER_WMS = 'https://geoserver.test/geoserver/wms'; // 替换为你真实的 GeoServer WMS 地址
// ----------------------

const gwcResolutions = [
    0.703125, 0.3515625, 0.17578125, 0.087890625, 0.0439453125, 
    0.02197265625, 0.010986328125, 0.0054931640625, 0.00274658203125, 
    0.001373291015625, 0.0006866455078125, 0.00034332275390625, 
    0.000171661376953125, 0.0000858306884765625, 0.00004291534423828125, 
    0.000021457672119140625, 0.0000107288360595703125, 0.000005364418029785156, 
    0.000002682209014892578, 0.000001341104507446289, 0.0000006705522537231445, 
    0.00000033527612686157227
];

// 形变图层配置 - 用于矿井风险分析图层选择
const DEFORMATION_LAYERS = [
    {
        id: 'deformation:v_mean_cropped_15_18',
        name: 'v_mean_cropped_15_18',
        displayName: '15-18年形变场',
        description: '2015年5月-2018年5月平均形变速率',
        timeRange: '2015-05-14 至 2018-05-22',
        dataVolume: 67,
        unit: 'mm/year'
    },
    {
        id: 'deformation:v_mean_cropped_15_25',
        name: 'v_mean_cropped_15_25',
        displayName: '15-25年形变场',
        description: '2015年5月-2025年5月平均形变速率',
        timeRange: '2015-05-14 至 2025-05-22',
        dataVolume: 362,
        unit: 'mm/year'
    }
];

// 矿井/油井数据图层配置 - 用于矿井风险分析图层选择
const MINING_LAYERS = [
    {
        id: 'oil_well_info',
        name: '油井分布',
        type: 'vector',
        geometryType: 'Point',
        apiEndpoint: '/api/oil-wells',
        description: '洛杉矶地区油井点位数据',
        statusField: 'extraction_status',
        activeValue: 'Active'
    },
    {
        id: 'mine_info',
        name: '矿区分布',
        type: 'vector',
        geometryType: 'Point',
        apiEndpoint: '/api/analysis/mining-risk',
        description: '矿区点位数据',
        statusField: 'extraction_status',
        activeValue: 'Active'
    }
];
