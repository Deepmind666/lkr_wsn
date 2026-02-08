# AERIS-WSN-Protocol 代码审核清单

## 一、核心算法文件

### 1. 主协议实现
| 文件 | 说明 | 行数 |
|------|------|------|
| `src/aeris_protocol.py` | AERIS核心协议实现 | ~2000 |
| `src/cas_selector.py` | CAS模块(上下文感知选择) | ~300 |
| `src/gateway_selector.py` | Gateway模块(网关选择) | ~200 |
| `src/skeleton_selector.py` | Skeleton模块(骨干网络) | ~150 |

### 2. 基线协议
| 文件 | 说明 |
|------|------|
| `src/baseline_protocols/leach_protocol.py` | LEACH协议 |
| `src/baseline_protocols/pegasis_protocol.py` | PEGASIS协议 |
| `src/baseline_protocols/heed_protocol.py` | HEED协议 |
| `src/teen_protocol.py` | TEEN协议 |

### 3. 能量模型
| 文件 | 说明 |
|------|------|
| `src/improved_energy_model.py` | CC2420/TelosB能量模型 |

---

## 二、实验脚本

### 关键实验脚本
| 文件 | 说明 | 审核重点 |
|------|------|----------|
| `scripts/run_mega_experiments.py` | 大规模实验 | pdr_end2end输出、stable_hash |
| `scripts/run_ultra_scale_10h.py` | 超大规模实验 | enable_channel配置 |
| `scripts/run_large_scale_scalability.py` | 可扩展性实验 | 严格PDR模式 |

---

## 三、实验结果

### 主要结果文件
| 文件 | 大小 | 实验数 |
|------|------|--------|
| `results/mega_8h_20260128_162624.json` | 17.2MB | 41,380 |

### 结果数据结构
```json
{
  "n_results": 41380,
  "metadata": {
    "timestamp": "20260128_162624",
    "git_commit": "44b51f6",
    "workers": 16
  },
  "results": {
    "baseline": [...],      // 1920个
    "scalability": [...],   // 3240个
    "ablation": [...],      // 2560个
    "sensitivity": [...],   // 10080个
    "dynamic": [...],       // 11520个
    "cross_topology": [...],// 3840个
    "longterm": [...],      // 480个
    "montecarlo": [...],    // 7200个
    "extreme_scale": [...]  // 540个
  }
}
```

---

## 四、核心指标汇总

### 基线实验结果 (n=320/协议)
| 协议 | PDR_e2e | Energy(J) |
|------|---------|-----------|
| AERIS-R | 0.991 | 169.7 |
| AERIS-E | 0.993 | 170.8 |
| PEGASIS | 0.589 | 104.8 |
| LEACH | 0.332 | 185.8 |
| HEED | 0.351 | 169.1 |
| TEEN | 0.380 | 178.7 |

### 可扩展性结果
| 节点数 | AERIS | PEGASIS |
|--------|-------|---------|
| 100 | 0.999 | 0.594 |
| 500 | 0.978 | 0.624 |
| 1000 | 0.967 | 0.624 |
| 2000 | 0.958 | 0.637 |

---

## 五、已知问题

### 1. PDR fallback问题
以下脚本使用fallback逻辑（缺失时回退到hop PDR）：
- `run_mega_experiments.py:276`
- `run_ultra_scale_10h.py:264`
- `overnight_master_v2.py:201`

**建议**: 改为返回-1.0标记无效数据

### 2. 消融实验进程池崩溃
消融实验阶段容易导致BrokenProcessPool错误

### 3. 指标提取不完整
协议输出了更多指标但实验脚本未提取：
- hop_count (跳数分布)
- fairness (公平性)
- FND (首节点死亡时间)

---

## 六、审核要点

### 代码正确性
- [ ] aeris_protocol.py 的端到端PDR计算逻辑
- [ ] enable_channel=True 是否正确启用信道模型
- [ ] stable_hash() 是否替代所有hash()调用

### 实验公平性
- [ ] 基线协议是否使用相同信道模型
- [ ] 能量模型参数是否一致
- [ ] 随机种子是否可重复

### 数据完整性
- [ ] pdr_end2end 字段是否正确输出
- [ ] 实验样本数是否足够(n≥30)
- [ ] 统计显著性检验是否完成
