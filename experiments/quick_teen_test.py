#!/usr/bin/env python3
"""
快速测试修复后的TEEN协议
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from teen_protocol import TEENProtocol, TEENConfig

def main():
    print("🧪 快速测试修复后的TEEN协议...")
    
    # 创建配置 - 使用更宽松的阈值确保有数据传输
    config = TEENConfig(
        num_nodes=10,
        area_width=100,
        area_height=100,
        base_station_x=50,
        base_station_y=175,
        initial_energy=2.0,
        hard_threshold=30.0,  # 更低的硬阈值
        soft_threshold=0.1,   # 更低的软阈值
        max_time_interval=2   # 更短的强制传输间隔
    )
    
    # 创建协议实例
    teen = TEENProtocol(config)
    
    # 初始化网络
    node_positions = [
        (25, 25), (75, 25), (25, 75), (75, 75), (50, 50),
        (10, 10), (90, 10), (10, 90), (90, 90), (50, 25)
    ]
    teen.initialize_network(node_positions)
    
    # 运行短期仿真
    result = teen.run_simulation(max_rounds=20)
    
    print(f"📊 修复后的TEEN协议性能:")
    print(f"   能效: {result['energy_efficiency']:.2f} packets/J")
    print(f"   投递率: {result['packet_delivery_ratio']:.3f}")
    print(f"   总能耗: {result['total_energy_consumed']:.6f} J")
    print(f"   发送数据包: {result['packets_transmitted']}")
    print(f"   接收数据包: {result['packets_received']}")
    
    # 判断修复效果
    if 30 <= result['energy_efficiency'] <= 100:
        print("✅ TEEN协议能效已修复到合理范围!")
    elif result['energy_efficiency'] > 100:
        print("⚠️  TEEN协议能效仍然过高，需要进一步调整")
    else:
        print("⚠️  TEEN协议能效过低，可能有其他问题")

if __name__ == "__main__":
    main()
