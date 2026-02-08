# Python环境修复完整指南

**日期**: 2025-10-19
**目的**: 修复AERIS项目的Python环境依赖问题
**适用**: Windows系统 + Anaconda

---

## 问题诊断

### 当前状态
```
✅ Conda已安装: C:\Users\admin\anaconda3
✅ 可用环境: eehfr-py311, aether-wsn, isj-gpu
❌ 当前环境缺少依赖: numpy, torch, scipy等
❌ Python版本过新: 3.13.7 (某些库不兼容)
```

### 推荐Python版本
- **Python 3.11.x** (最稳定，所有库兼容)
- Python 3.10.x (备选)
- ❌ Python 3.13.x (过新，某些库不支持)

---

## 解决方案（三选一）

### 方案A: 使用Anaconda Prompt（最简单，推荐）

#### 步骤1: 打开Anaconda Prompt
1. 按 `Win` 键，搜索 "Anaconda Prompt"
2. 右键 → 以管理员身份运行

#### 步骤2: 激活环境
```bash
conda activate eehfr-py311
```

#### 步骤3: 安装依赖
```bash
cd C:\Enhanced-EEHFR-WSN-Protocol
pip install -r requirements.txt
```

#### 步骤4: 验证安装
```bash
python scripts/verify_dependencies.py
```

#### 步骤5: 运行测试
```bash
python scripts/smoke_test.py
```

---

### 方案B: 创建全新Conda环境（最稳妥）

#### 步骤1: 创建新环境
```bash
# 打开Anaconda Prompt
conda create -n aeris-final python=3.11 -y
```

#### 步骤2: 激活并安装依赖
```bash
conda activate aeris-final
cd C:\Enhanced-EEHFR-WSN-Protocol
pip install -r requirements.txt
```

#### 步骤3: 安装PyTorch (CPU版本)
```bash
# 如果pip install失败，使用conda
conda install pytorch torchvision torchaudio cpuonly -c pytorch
```

#### 步骤4: 验证
```bash
python -c "import numpy, torch, scipy, sklearn; print('All dependencies installed!')"
```

---

### 方案C: 在PowerShell中激活Conda（高级用户）

#### 步骤1: 初始化Conda for PowerShell（一次性）
```powershell
# 打开PowerShell（管理员）
conda init powershell
```

#### 步骤2: 关闭并重新打开PowerShell

#### 步骤3: 激活环境
```powershell
conda activate eehfr-py311
cd C:\Enhanced-EEHFR-WSN-Protocol
python scripts/smoke_test.py
```

---

## 常见错误及解决

### 错误1: "conda不是内部或外部命令"

**原因**: PATH环境变量未配置

**解决**:
```powershell
# 方法1: 使用完整路径
C:\Users\admin\anaconda3\Scripts\activate.bat

# 方法2: 添加到PATH
# 1. Win+R → sysdm.cpl → 高级 → 环境变量
# 2. 系统变量 → Path → 新建
# 3. 添加: C:\Users\admin\anaconda3\Scripts
# 4. 添加: C:\Users\admin\anaconda3
```

### 错误2: "ModuleNotFoundError: No module named 'numpy'"

**原因**: 环境中未安装依赖

**解决**:
```bash
# 在正确的conda环境中
pip install -r requirements.txt

# 如果仍然失败，逐个安装
pip install numpy scipy pandas scikit-learn matplotlib seaborn networkx tqdm
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

### 错误3: "Could not find platform independent libraries"

**原因**: Python安装配置问题

**解决**:
```bash
# 重新创建干净的conda环境
conda deactivate
conda env remove -n eehfr-py311
conda create -n eehfr-py311 python=3.11 -y
conda activate eehfr-py311
pip install -r requirements.txt
```

### 错误4: PyTorch安装失败

**原因**: Windows系统需要特殊配置

**解决**:
```bash
# CPU版本（推荐，兼容性最好）
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# 或使用conda（更稳定）
conda install pytorch torchvision torchaudio cpuonly -c pytorch
```

---

## GPU支持（可选）

如果您有NVIDIA GPU并希望使用：

### 检查CUDA版本
```bash
nvidia-smi
# 查看CUDA Version行
```

### 安装对应版本PyTorch
```bash
# CUDA 11.8
conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia

# CUDA 12.1
conda install pytorch torchvision torchaudio pytorch-cuda=12.1 -c pytorch -c nvidia
```

### 验证GPU
```python
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"
```

---

## 快速验证清单

运行以下命令，全部通过即表示环境正确：

```bash
# 1. 检查Python版本（应为3.11.x或3.10.x）
python --version

# 2. 检查依赖
python -c "import numpy, torch, scipy, sklearn, matplotlib, seaborn, networkx; print('Core deps OK')"

# 3. 检查项目导入
cd C:\Enhanced-EEHFR-WSN-Protocol
python -c "import sys; sys.path.append('src'); from benchmark_protocols import NetworkConfig; print('Project imports OK')"

# 4. 运行快速测试
python scripts/smoke_test.py
```

全部通过后，环境配置完成！✅

---

## 运行实验的标准流程

### 1. 激活环境（每次新打开终端都需要）
```bash
# Anaconda Prompt
conda activate eehfr-py311
cd C:\Enhanced-EEHFR-WSN-Protocol
```

### 2. 运行核心实验
```bash
# 基线对比
python scripts/run_intel_baselines_all.py

# 消融实验
python scripts/run_intel_ablation.py

# 敏感性分析
python scripts/run_intel_sensitivity.py

# 统计显著性
python scripts/run_significance_intel.py
```

### 3. 生成图表
```bash
python scripts/plot_paper_figures.py
python scripts/curate_figures.py
```

### 4. 查看结果
```bash
# 结果在 results/ 目录
ls results/*.json
ls results/plots/paper_*.pdf
```

---

## 故障排除终极方案

如果所有方法都失败，使用以下步骤从零开始：

```bash
# 1. 卸载所有conda环境
conda env list  # 查看所有环境
conda env remove -n eehfr-py311
conda env remove -n aether-wsn
# ... 删除所有项目相关环境

# 2. 创建全新环境
conda create -n aeris-clean python=3.11 numpy scipy pandas scikit-learn matplotlib seaborn networkx tqdm -y

# 3. 激活并安装PyTorch
conda activate aeris-clean
conda install pytorch torchvision torchaudio cpuonly -c pytorch -y

# 4. 安装项目特定依赖
cd C:\Enhanced-EEHFR-WSN-Protocol
pip install scikit-fuzzy  # 模糊逻辑（可选）

# 5. 验证
python scripts/verify_dependencies.py
python scripts/smoke_test.py
```

---

## 联系康锐大师

如果遇到无法解决的问题，请提供以下信息：

```bash
# 1. 环境信息
conda info
conda list

# 2. Python信息
python --version
python -c "import sys; print(sys.executable)"

# 3. 错误日志
# 复制完整的错误信息
```

---

## 成功标志

当您看到以下输出时，环境配置成功：

```
============================================================
AERIS项目环境验证
============================================================

Python版本: 3.11.x
执行路径: C:\Users\admin\anaconda3\envs\eehfr-py311\python.exe

依赖检查:
------------------------------------------------------------
✅ NumPy 1.24.3
✅ SciPy 1.11.1
✅ Pandas 2.0.3
✅ Scikit-learn 1.3.0
✅ PyTorch 2.2.0 (CPU only)
✅ Matplotlib 3.7.2
✅ Seaborn 0.12.2
✅ NetworkX 3.1
✅ tqdm 4.65.0
------------------------------------------------------------

总结: 9/9 依赖已安装 (100.0%)

🎉 所有依赖已正确安装！环境配置完成。
```

**现在可以运行所有实验了！** 🚀

---

**下一步**: 阅读 `Deep_Understanding_and_Improvement_Plan_2025_10_19.md` 了解改进计划。
