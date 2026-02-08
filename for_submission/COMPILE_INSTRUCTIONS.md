# 论文编译说明

## 方法1: Overleaf在线编译（推荐）

1. **打包上传文件**：
   ```
   for_submission/
   ├── aeris_paper_final.tex      # 主文档
   ├── bibliography.bib           # 参考文献
   ├── Definitions/               # MDPI模板文件
   │   ├── mdpi.cls
   │   ├── mdpi.bst
   │   └── ...
   └── figures/                   # 所有图片
       ├── sota_comparison_6panel.pdf
       ├── fig_advanced_analysis.pdf
       ├── fig_ns3_scalability.pdf
       ├── fig_ns3_ablation.pdf
       ├── fig_ns3_combined_panel.pdf
       └── ...
   ```

2. **上传到Overleaf**：
   - 访问 https://www.overleaf.com
   - 创建新项目 → 上传项目
   - 将整个 `for_submission` 文件夹打成zip上传

3. **编译设置**：
   - 编译器：pdfLaTeX
   - 主文档：aeris_paper_final.tex

## 方法2: 本地安装TeX Live

### Windows:
```powershell
# 下载并安装MiKTeX: https://miktex.org/download
# 或 TeX Live: https://www.tug.org/texlive/

# 编译命令
cd for_submission
pdflatex aeris_paper_final.tex
bibtex aeris_paper_final
pdflatex aeris_paper_final.tex
pdflatex aeris_paper_final.tex
```

### WSL/Linux:
```bash
sudo apt-get install texlive-full
cd /mnt/c/AERIS-WSN-Protocol/for_submission
pdflatex aeris_paper_final.tex
bibtex aeris_paper_final
pdflatex aeris_paper_final.tex
pdflatex aeris_paper_final.tex
```

## 更新内容 (2026-01-19)

本次更新新增了 **NS-3交叉验证** 章节（Section 4.5），包含：

1. **真实信道模型配置** (Table 3)
   - Log-distance path loss (n=2.5)
   - Shadow fading (σ=3 dB)
   - Rician multi-path fading

2. **可扩展性验证** (Table 4)
   - AERIS: 96.51% PDR
   - LEACH: 82.65% PDR
   - 提升: +16.78%

3. **消融实验** (Table 5)
   - Gateway模块贡献: +19.8% PDR
   - Fairness模块贡献: +7% 节点存活率

## 新增图表

| 图表 | 文件 | 说明 |
|------|------|------|
| Table 3 | N/A | NS-3信道模型参数 |
| Table 4 | N/A | NS-3可扩展性结果 |
| Table 5 | N/A | NS-3消融实验结果 |

## 文件清单

- `aeris_paper_final.tex` - 主LaTeX文件（已更新NS-3验证章节）
- `figures/fig_ns3_*.pdf` - NS-3验证图表
- `ns3_validation/` - NS-3实验代码和原始数据

---
生成时间: 2026-01-19
