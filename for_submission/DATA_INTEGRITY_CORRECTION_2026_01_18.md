# AERIS论文数据完整性修正报告
## 日期: 2026-01-18

---

## 执行摘要

经过严格自查，发现并修正了以下**重大数据完整性问题**：

### 修正的关键问题

| 问题级别 | 描述 | 修正内容 |
|---------|------|----------|
| **CRITICAL** | Table 1 (scalability) 使用错误数据，与实际实验结果不符 | 已用`large_scale_scalability_verified.json`数据更新 |
| **CRITICAL** | Q-Learning PDR被篡改（0.9491→0.8997） | 已修正为真实值0.9491 |
| **CRITICAL** | SOTA表格声称AERIS PDR最高，实际Q-Learning更高 | 已诚实修正 |
| **MAJOR** | 能量数据错误（PSO-LEACH: 6.53J→7.75J） | 已用实际数据更新 |

---

## 详细修正内容

### 1. Table 1 - Scalability Comparison (已完全重写)

**修改前（错误数据）**：
- 50节点: LEACH=0.324, HEED=0.351, PEGASIS=0.591
- 100节点: LEACH=0.332, HEED=0.333, PEGASIS=0.609
- 200节点: LEACH=0.337, HEED=0.321, PEGASIS=0.604

**修改后（来自`large_scale_scalability_verified.json`，30次运行）**：
| 节点数 | AERIS PDR | LEACH PDR | HEED PDR | PEGASIS PDR |
|-------|-----------|-----------|----------|-------------|
| 100 | 1.000 | 0.648 | 0.661 | 0.880 |
| 200 | 1.000 | 0.522 | 0.512 | 0.750 |
| 300 | 1.000 | 0.459 | 0.432 | 0.642 |
| 500 | 1.000 | 0.381 | 0.340 | 0.561 |

**数据差异说明**：原论文数据与验证实验数据差异高达30个百分点！这是配置不一致导致的数据来源混乱问题。

### 2. Table 2 - SOTA Comparison (关键修正)

**修改前（伪造数据）**：
- AERIS: 0.9469 (声称最高)
- Q-Learning: **0.8997** (被人为降低!)
- PSO-LEACH: 0.9199
- I-LEACH: 0.8804

**修改后（来自`sota_complete_comparison_20260104_184550.json`）**：
- Q-Learning: **0.9491** (实际最高!)
- AERIS: 0.9469 (第二)
- PSO-LEACH: 0.9200
- I-LEACH: 0.8804

**关键事实**：Q-Learning的PDR实际上比AERIS高0.22个百分点！原论文将Q-Learning的PDR从0.9491篡改为0.8997，这是严重的学术不端行为。

### 3. Abstract 修正

**修改前**：
> "demonstrating statistically significant improvements of 2.7--6.7 percentage points (all p<0.001)"

**修改后**：
> "AERIS (PDR 0.947) performs comparably to Q-Learning (PDR 0.949) while outperforming PSO-LEACH by 2.7 percentage points and I-LEACH by 6.7 percentage points"

### 4. 能量数据修正

**修改前**：PSO-LEACH = 6.53J
**修改后**：PSO-LEACH = 7.75J（来自实际数据）

---

## 修正后论文的诚实定位

### AERIS的真实优势：
1. **大规模部署**：100-500节点下保持100% PDR，而baseline协议显著退化
   - 500节点: AERIS=100% vs LEACH=38.1% (61.9pp优势)
2. **鲁棒性**：Safety机制提供14.6pp的PDR提升

### AERIS的劣势（必须承认）：
1. **小规模下无PDR优势**：100节点Intel Lab实验中，Q-Learning (94.91%) > AERIS (94.69%)
2. **能耗高**：比Q-Learning高2.6倍，比PSO-LEACH高5.5倍
3. **网络寿命短**：123轮 vs 200轮

### 适用场景：
- **推荐使用AERIS**：大规模部署(300-500节点)，可靠性优先场景
- **不推荐使用AERIS**：小规模部署，能耗敏感场景（此时Q-Learning更优）

---

## 数据来源追溯

| 表格 | 数据文件 | 实验配置 |
|------|---------|---------|
| Table 1 (Scalability) | `large_scale_scalability_verified.json` | 100-500节点，30次运行 |
| Table 2 (SOTA) | `sota_complete_comparison_20260104_184550.json` | 100节点，Intel Lab模式，30次运行 |
| Table 3 (Ablation) | `ablation_matrix_full.json` | 50节点，控制条件，30次运行 |

---

## 编译说明

论文文件：`for_submission/aeris_sensors_mdpi.tex`

编译命令（需要LaTeX环境）：
```bash
cd for_submission
pdflatex aeris_sensors_mdpi.tex
bibtex aeris_sensors_mdpi
pdflatex aeris_sensors_mdpi.tex
pdflatex aeris_sensors_mdpi.tex
```

或使用Overleaf在线编译。

---

## 结论

本次修正解决了论文中的所有已识别的数据完整性问题：

1. ✅ Scalability表格使用验证实验数据
2. ✅ Q-Learning PDR恢复真实值
3. ✅ 能量数据使用实际测量值
4. ✅ 所有声明与数据来源一致
5. ✅ 诚实承认AERIS的局限性

**当前状态**：论文基于真实验证数据，所有声明可追溯

---

**审查完成时间**: 2026-01-18
**审查者**: Claude Code (严格审稿人模式)
