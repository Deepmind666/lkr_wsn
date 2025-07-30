#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境感知Enhanced EEHFR协议测试脚本

测试内容:
1. 环境分类器功能验证
2. 环境自适应参数调整
3. 协议完整运行测试
4. 多环境性能对比

作者: Enhanced EEHFR Research Team
日期: 2025-01-30
版本: 1.0
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
import matplotlib.pyplot as plt
import json
from datetime import datetime

from environment_aware_eehfr import (
    EnvironmentAwareEEHFR, 
    EnvironmentClassifier,
    EnvironmentMetrics
)
from enhanced_eehfr_protocol import EnhancedNode
from realistic_channel_model import EnvironmentType

def create_test_network(num_nodes: int = 50, area_size: float = 100.0) -> list:
    """创建测试网络"""
    nodes = []
    np.random.seed(42)  # 确保可重现性
    
    for i in range(num_nodes):
        x = np.random.uniform(0, area_size)
        y = np.random.uniform(0, area_size)
        initial_energy = 2.0  # 2J初始能量
        
        node = EnhancedNode(i, x, y, initial_energy)
        nodes.append(node)
    
    return nodes

def test_environment_classifier():
    """测试环境分类器"""
    print("🧪 测试环境分类器...")
    
    classifier = EnvironmentClassifier()
    
    # 测试用例：不同环境的典型指标
    test_cases = [
        {
            'name': '理想住宅环境',
            'metrics': {'avg_rssi': -60, 'avg_pdr': 0.95, 'reliability_score': 98.0},
            'expected': EnvironmentType.INDOOR_RESIDENTIAL
        },
        {
            'name': '办公室环境',
            'metrics': {'avg_rssi': -70, 'avg_pdr': 0.85, 'reliability_score': 92.0},
            'expected': EnvironmentType.INDOOR_OFFICE
        },
        {
            'name': '恶劣工厂环境',
            'metrics': {'avg_rssi': -85, 'avg_pdr': 0.30, 'reliability_score': 25.0},
            'expected': EnvironmentType.INDOOR_FACTORY
        },
        {
            'name': '城市环境',
            'metrics': {'avg_rssi': -95, 'avg_pdr': 0.20, 'reliability_score': 10.0},
            'expected': EnvironmentType.OUTDOOR_URBAN
        }
    ]
    
    correct_classifications = 0
    for test_case in test_cases:
        predicted = classifier.classify_environment(test_case['metrics'])
        is_correct = predicted == test_case['expected']
        correct_classifications += is_correct
        
        print(f"   {test_case['name']}: "
              f"预测={predicted.value}, "
              f"期望={test_case['expected'].value}, "
              f"{'✅' if is_correct else '❌'}")
    
    accuracy = correct_classifications / len(test_cases)
    print(f"   分类准确率: {accuracy*100:.1f}%")
    
    return accuracy > 0.75  # 75%以上准确率为通过

def test_environment_adaptation():
    """测试环境自适应功能"""
    print("🧪 测试环境自适应功能...")
    
    nodes = create_test_network(20, 50.0)
    base_station = (25.0, 25.0)
    
    # 创建协议实例
    protocol = EnvironmentAwareEEHFR(
        nodes=nodes,
        base_station=base_station,
        initial_environment=EnvironmentType.INDOOR_OFFICE
    )
    
    # 记录初始参数
    initial_params = {
        'tx_power': protocol.adaptive_tx_power,
        'retrans_limit': protocol.adaptive_retransmission_limit,
        'update_freq': protocol.adaptive_update_frequency
    }
    
    print(f"   初始环境: {protocol.current_environment.value}")
    print(f"   初始参数: 功率={initial_params['tx_power']}dBm, "
          f"重传={initial_params['retrans_limit']}, "
          f"更新频率={initial_params['update_freq']}")
    
    # 模拟环境变化到工厂环境
    protocol._adapt_to_environment_change(EnvironmentType.INDOOR_FACTORY)
    
    # 检查参数是否正确调整
    adapted_params = {
        'tx_power': protocol.adaptive_tx_power,
        'retrans_limit': protocol.adaptive_retransmission_limit,
        'update_freq': protocol.adaptive_update_frequency
    }
    
    print(f"   适应后环境: {protocol.current_environment.value}")
    print(f"   适应后参数: 功率={adapted_params['tx_power']}dBm, "
          f"重传={adapted_params['retrans_limit']}, "
          f"更新频率={adapted_params['update_freq']}")
    
    # 验证参数调整是否合理
    power_increased = adapted_params['tx_power'] > initial_params['tx_power']
    retrans_increased = adapted_params['retrans_limit'] > initial_params['retrans_limit']
    freq_decreased = adapted_params['update_freq'] < initial_params['update_freq']
    
    adaptation_success = power_increased and retrans_increased and freq_decreased
    print(f"   自适应结果: {'✅ 成功' if adaptation_success else '❌ 失败'}")
    
    return adaptation_success

def test_protocol_execution():
    """测试协议完整执行"""
    print("🧪 测试协议完整执行...")
    
    nodes = create_test_network(30, 80.0)
    base_station = (40.0, 40.0)
    
    # 创建协议实例
    protocol = EnvironmentAwareEEHFR(
        nodes=nodes,
        base_station=base_station,
        initial_environment=EnvironmentType.INDOOR_OFFICE
    )
    
    # 运行协议 (短时间测试)
    results = protocol.run_environment_aware_protocol(max_rounds=50)
    
    # 验证结果
    execution_success = (
        results['rounds_completed'] > 0 and
        results['total_energy_consumed'] > 0 and
        results['final_alive_nodes'] > 0 and
        0 <= results['transmission_success_rate'] <= 1
    )
    
    print(f"   执行轮数: {results['rounds_completed']}")
    print(f"   总能耗: {results['total_energy_consumed']:.4f}J")
    print(f"   存活节点: {results['final_alive_nodes']}/{len(nodes)}")
    print(f"   传输成功率: {results['transmission_success_rate']*100:.2f}%")
    print(f"   执行结果: {'✅ 成功' if execution_success else '❌ 失败'}")
    
    return execution_success, results

def test_multi_environment_comparison():
    """测试多环境性能对比"""
    print("🧪 测试多环境性能对比...")
    
    environments = [
        EnvironmentType.INDOOR_RESIDENTIAL,
        EnvironmentType.INDOOR_OFFICE,
        EnvironmentType.INDOOR_FACTORY
    ]
    
    comparison_results = {}
    
    for env in environments:
        print(f"   测试环境: {env.value}")
        
        nodes = create_test_network(25, 60.0)
        base_station = (30.0, 30.0)
        
        protocol = EnvironmentAwareEEHFR(
            nodes=nodes,
            base_station=base_station,
            initial_environment=env
        )
        
        results = protocol.run_environment_aware_protocol(max_rounds=30)
        
        comparison_results[env.value] = {
            'network_lifetime': results['network_lifetime'],
            'total_energy_consumed': results['total_energy_consumed'],
            'transmission_success_rate': results['transmission_success_rate'],
            'final_alive_nodes': results['final_alive_nodes']
        }
        
        print(f"      生存时间: {results['network_lifetime']} 轮")
        print(f"      能耗: {results['total_energy_consumed']:.4f}J")
        print(f"      成功率: {results['transmission_success_rate']*100:.2f}%")
    
    return comparison_results

def run_comprehensive_test():
    """运行综合测试"""
    print("🚀 开始环境感知Enhanced EEHFR协议综合测试")
    print("=" * 60)
    
    test_results = {
        'timestamp': datetime.now().isoformat(),
        'test_summary': {},
        'detailed_results': {}
    }
    
    # 测试1: 环境分类器
    classifier_passed = test_environment_classifier()
    test_results['test_summary']['environment_classifier'] = classifier_passed
    print()
    
    # 测试2: 环境自适应
    adaptation_passed = test_environment_adaptation()
    test_results['test_summary']['environment_adaptation'] = adaptation_passed
    print()
    
    # 测试3: 协议执行
    execution_passed, execution_results = test_protocol_execution()
    test_results['test_summary']['protocol_execution'] = execution_passed
    test_results['detailed_results']['execution_results'] = execution_results
    print()
    
    # 测试4: 多环境对比
    comparison_results = test_multi_environment_comparison()
    test_results['detailed_results']['multi_environment_comparison'] = comparison_results
    print()
    
    # 总结测试结果
    total_tests = len(test_results['test_summary'])
    passed_tests = sum(test_results['test_summary'].values())
    
    print("=" * 60)
    print("🏁 测试完成总结")
    print(f"   总测试数: {total_tests}")
    print(f"   通过测试: {passed_tests}")
    print(f"   测试通过率: {passed_tests/total_tests*100:.1f}%")
    
    if passed_tests == total_tests:
        print("   🎉 所有测试通过！环境感知EEHFR协议功能正常")
    else:
        print("   ⚠️  部分测试失败，需要进一步调试")
    
    # 保存测试结果
    results_file = f"../results/environment_aware_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs(os.path.dirname(results_file), exist_ok=True)
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(test_results, f, indent=2, ensure_ascii=False)
    
    print(f"   📊 测试结果已保存: {results_file}")
    
    return test_results

if __name__ == "__main__":
    test_results = run_comprehensive_test()
