#!/usr/bin/env python3
"""
测试修复后的TEEN协议能耗计算
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from teen_protocol import TEENProtocol, TEENConfig

def main():
    config = TEENConfig()
    teen = TEENProtocol(config)

    print('🧪 测试修复后的TEEN能耗计算:')
    distances = [10, 50, 100, 150]
    for distance in distances:
        tx_energy = teen._calculate_transmission_energy(distance, 4000)
        rx_energy = teen._calculate_reception_energy(4000)
        total_energy = tx_energy + rx_energy
        print(f'   距离{distance}m: 传输={tx_energy:.9f}J, 接收={rx_energy:.9f}J, 总计={total_energy:.9f}J')
        
        if total_energy > 0.1:
            print(f'   ⚠️  距离{distance}m能耗过高: {total_energy:.9f}J')
        elif total_energy < 1e-6:
            print(f'   ⚠️  距离{distance}m能耗过低: {total_energy:.9f}J')

if __name__ == "__main__":
    main()
