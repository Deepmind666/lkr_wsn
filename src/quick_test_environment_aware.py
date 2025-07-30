#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境感知EEHFR协议快速测试
"""

import numpy as np
from environment_aware_eehfr import (
    EnvironmentAwareEEHFR, 
    EnvironmentClassifier
)
from enhanced_eehfr_protocol import EnhancedNode
from realistic_channel_model import EnvironmentType

def create_test_network(num_nodes: int = 20) -> list:
    """创建测试网络"""
    nodes = []
    np.random.seed(42)
    
    for i in range(num_nodes):
        x = np.random.uniform(0, 50.0)
        y = np.random.uniform(0, 50.0)
        node = EnhancedNode(i, x, y, 2.0)
        nodes.append(node)
    
    return nodes

def main():
    print("🧪 环境感知Enhanced EEHFR协议快速测试")
    print("=" * 50)
    
    # 测试1: 环境分类器
    print("1. 测试环境分类器...")
    classifier = EnvironmentClassifier()
    
    test_metrics = {'avg_rssi': -70, 'avg_pdr': 0.85, 'reliability_score': 92.0}
    predicted_env = classifier.classify_environment(test_metrics)
    print(f"   预测环境: {predicted_env.value}")
    
    # 测试2: 协议初始化
    print("\n2. 测试协议初始化...")
    nodes = create_test_network(15)
    base_station = (25.0, 25.0)
    
    protocol = EnvironmentAwareEEHFR(
        nodes=nodes,
        base_station=base_station,
        initial_environment=EnvironmentType.INDOOR_OFFICE
    )
    
    print(f"   节点数量: {len(protocol.nodes)}")
    print(f"   初始环境: {protocol.current_environment.value}")
    print(f"   发射功率: {protocol.adaptive_tx_power} dBm")
    
    # 测试3: 环境自适应
    print("\n3. 测试环境自适应...")
    old_power = protocol.adaptive_tx_power
    protocol._adapt_to_environment_change(EnvironmentType.INDOOR_FACTORY)
    new_power = protocol.adaptive_tx_power
    
    print(f"   环境变化: OFFICE → FACTORY")
    print(f"   功率调整: {old_power} → {new_power} dBm")
    
    # 测试4: 长期协议运行 (100轮)
    print("\n4. 测试协议运行 (100轮)...")
    results = protocol.run_environment_aware_protocol(max_rounds=100)
    
    print(f"   运行轮数: {results['rounds_completed']}")
    print(f"   总能耗: {results['total_energy_consumed']:.4f}J")
    print(f"   存活节点: {results['final_alive_nodes']}/{len(nodes)}")
    print(f"   传输成功率: {results['transmission_success_rate']*100:.2f}%")
    
    print("\n✅ 快速测试完成！")

if __name__ == "__main__":
    main()
