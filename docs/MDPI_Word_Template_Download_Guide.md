# MDPI Sensors Word模板下载指南

**日期**: 2025-10-07  
**目的**: 下载MDPI Sensors期刊的官方Word模板供本地编辑

---

## 方法1：官方网站下载（推荐）

### 步骤：

1. **访问MDPI Sensors主页**  
   https://www.mdpi.com/journal/sensors

2. **点击 "Instructions for Authors"**（作者指南）  
   通常在页面顶部导航栏

3. **下载Word模板**  
   在"Manuscript Preparation"部分找到"Word Template"下载链接  
   或直接访问：https://www.mdpi.com/journal/sensors/instructions

4. **常见模板文件名**：
   - `sensors-template.doc` 或 `sensors-template.docx`
   - `mdpi-template.doc` (通用MDPI模板)

---

## 方法2：直接下载链接（可能需要验证）

尝试以下URL（在浏览器中打开）：

### MDPI通用模板：
```
https://www.mdpi.com/files/word-templates/mdpi_template.docx
```

### Sensors专用模板：
```
https://www.mdpi.com/files/word-templates/sensors-template.docx
```

---

## 方法3：使用LaTeX转Word（备选）

如果无法获取Word模板，可以使用Pandoc将我们的LaTeX文件转换为Word：

### 安装Pandoc：
```bash
# Windows (使用Chocolatey)
choco install pandoc

# 或下载安装包
https://pandoc.org/installing.html
```

### 转换命令：
```bash
cd C:\Enhanced-EEHFR-WSN-Protocol\docs\templates\mdpi_latex\mdpi_template
pandoc aeris_paper.tex -o aeris_paper.docx --bibliography=bibliography.bib
```

---

## 当前可用文件

### PDF版本（已生成）：
- **文件**: `C:\Enhanced-EEHFR-WSN-Protocol\docs\templates\mdpi_latex\mdpi_template\aeris_paper.pdf`
- **页数**: 19页
- **大小**: 282 KB
- **状态**: ✅ 可查看

### LaTeX源文件：
- **文件**: `C:\Enhanced-EEHFR-WSN-Protocol\docs\templates\mdpi_latex\mdpi_template\aeris_paper.tex`
- **状态**: ✅ 可编译

### Markdown预览版：
- **文件**: `C:\Enhanced-EEHFR-WSN-Protocol\docs\AERIS_Paper_Preview.md`
- **状态**: ✅ 可在VS Code中查看

---

## 推荐工作流程

1. **阅读PDF版本**：快速查看论文整体效果
2. **下载MDPI Word模板**：用于最终提交
3. **复制内容到Word**：从Markdown或PDF复制文本到Word模板
4. **调整格式**：确保符合MDPI格式要求

---

## 备注

- MDPI Sensors接受LaTeX或Word格式投稿
- LaTeX通常更适合包含大量数学公式的论文
- Word模板更适合与编辑沟通和修改

如需帮助，请随时联系！

