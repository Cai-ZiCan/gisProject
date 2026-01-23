"""
矿井形变风险分析功能测试脚本
用于验证API和数据库查询功能
"""

import requests
import json

# API基础URL
BASE_URL = "http://127.0.0.1:5000"

def test_deformation_analysis_basic():
    """测试基本的形变分析（不使用缓冲区）"""
    print("\n=== 测试1: 基本形变分析 ===")
    
    url = f"{BASE_URL}/api/mining-deformation-analysis"
    payload = {
        "miningLayer": "oil_well_info",
        "deformationLayer": "v_mean_cropped_15_25",
        "threshold": 10.0,
        "activeOnly": True
    }
    
    print(f"请求URL: {url}")
    print(f"请求参数: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(url, json=payload)
        print(f"\n响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"分析状态: {data.get('status')}")
            print(f"消息: {data.get('message')}")
            print(f"特征数量: {data.get('featureCount')}")
            
            if data.get('featureCount', 0) > 0:
                # 显示第一个特征的详细信息
                first_feature = data['geojson']['features'][0]
                print(f"\n第一个高风险油井示例:")
                print(f"  - 名称: {first_feature['properties'].get('name')}")
                print(f"  - 形变值: {first_feature['properties'].get('deformation_value')} mm/year")
                print(f"  - 状态: {first_feature['properties'].get('status')}")
        else:
            print(f"错误: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("错误: 无法连接到后端服务器。请确保Flask服务器正在运行。")
    except Exception as e:
        print(f"错误: {e}")


def test_deformation_analysis_with_buffer():
    """测试带缓冲区的形变分析"""
    print("\n=== 测试2: 带缓冲区的形变分析 ===")
    
    url = f"{BASE_URL}/api/mining-deformation-analysis"
    payload = {
        "miningLayer": "oil_well_info",
        "deformationLayer": "v_mean_cropped_15_25",
        "threshold": 10.0,
        "activeOnly": True,
        "bufferDistance": 500,
        "bufferUnit": "meters"
    }
    
    print(f"请求URL: {url}")
    print(f"请求参数: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(url, json=payload)
        print(f"\n响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"分析状态: {data.get('status')}")
            print(f"消息: {data.get('message')}")
            print(f"特征数量: {data.get('featureCount')}")
            
            if data.get('featureCount', 0) > 0:
                # 显示第一个特征的详细信息
                first_feature = data['geojson']['features'][0]
                props = first_feature['properties']
                print(f"\n第一个高风险油井示例:")
                print(f"  - 名称: {props.get('name')}")
                print(f"  - 点位形变值: {props.get('deformation_value')} mm/year")
                print(f"  - 缓冲区平均值: {props.get('buffer_mean')} mm/year")
                print(f"  - 缓冲区最大值: {props.get('buffer_max')} mm/year")
                print(f"  - 缓冲区最小值: {props.get('buffer_min')} mm/year")
                print(f"  - 最大绝对值: {props.get('max_abs_deformation')} mm/year")
        else:
            print(f"错误: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("错误: 无法连接到后端服务器。请确保Flask服务器正在运行。")
    except Exception as e:
        print(f"错误: {e}")


def test_invalid_parameters():
    """测试无效参数处理"""
    print("\n=== 测试3: 无效参数处理 ===")
    
    url = f"{BASE_URL}/api/mining-deformation-analysis"
    
    # 测试缺少必需参数
    print("\n3.1 测试缺少必需参数:")
    payload = {
        "threshold": 10.0
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"响应状态码: {response.status_code}")
        if response.status_code != 200:
            data = response.json()
            print(f"预期错误消息: {data.get('message')}")
    except Exception as e:
        print(f"错误: {e}")
    
    # 测试无效的图层名称
    print("\n3.2 测试无效的图层名称:")
    payload = {
        "miningLayer": "invalid_layer",
        "deformationLayer": "v_mean_cropped_15_25",
        "threshold": 10.0
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"响应状态码: {response.status_code}")
        if response.status_code != 200:
            data = response.json()
            print(f"预期错误消息: {data.get('message')}")
    except Exception as e:
        print(f"错误: {e}")
    
    # 测试不存在的形变图层
    print("\n3.3 测试不存在的形变图层:")
    payload = {
        "miningLayer": "oil_well_info",
        "deformationLayer": "nonexistent_layer",
        "threshold": 10.0
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"响应状态码: {response.status_code}")
        if response.status_code != 200:
            data = response.json()
            print(f"预期错误消息: {data.get('message')}")
    except Exception as e:
        print(f"错误: {e}")


def test_different_thresholds():
    """测试不同阈值的影响"""
    print("\n=== 测试4: 不同阈值对结果的影响 ===")
    
    url = f"{BASE_URL}/api/mining-deformation-analysis"
    thresholds = [5.0, 10.0, 15.0, 20.0]
    
    for threshold in thresholds:
        payload = {
            "miningLayer": "oil_well_info",
            "deformationLayer": "v_mean_cropped_15_25",
            "threshold": threshold,
            "activeOnly": False
        }
        
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                count = data.get('featureCount', 0)
                print(f"阈值 {threshold} mm/year: 找到 {count} 个高风险油井")
        except Exception as e:
            print(f"阈值 {threshold} 测试失败: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("矿井形变风险分析API测试")
    print("=" * 60)
    
    print("\n请确保:")
    print("1. Flask后端服务器正在运行 (python app.py)")
    print("2. PostgreSQL数据库可访问")
    print("3. 数据库中已导入形变栅格数据和油井数据")
    
    input("\n按回车键开始测试...")
    
    # 运行所有测试
    test_deformation_analysis_basic()
    test_deformation_analysis_with_buffer()
    test_invalid_parameters()
    test_different_thresholds()
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
