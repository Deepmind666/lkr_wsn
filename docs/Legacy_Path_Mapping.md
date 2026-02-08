## Legacy Path Mapping

为便于审阅旧报告，本页记录历史命名 `Enhanced-EEHFR-WSN-Protocol` 与现有仓库 `AERIS-WSN-Protocol` 之间的映射。所有旧路径或脚本命令只需将字符串 `Enhanced-EEHFR-WSN-Protocol` 替换为 `AERIS-WSN-Protocol` 即可（含大小写）。

### 常见替换示例

| 历史引用 | 现行路径 |
|---|---|
| `C:\Enhanced-EEHFR-WSN-Protocol\docs\templates\...` | `C:\AERIS-WSN-Protocol\docs\templates\...` |
| `src/Enhanced-EEHFR-WSN-Protocol/` | `src/aeris/`（或仓库根目录下对应子模块） |
| `conda activate eehfr-py311` | `conda activate aeris-py311` |

### 适用范围

- `docs/` 文件夹下的历史报告（例如 `AERIS_Project_Deep_Assessment_2025_10_19.md`、`Deep_Understanding_and_Improvement_Plan_2025_10_19.md` 等）目前保留原文引用以便对照，但均受上述映射约束。
- `archive/` 与 `results/_archive_*` 目录同样沿用旧路径，只作存档用途。

> 若在过往文档中遇到未列举的历史路径，可将其视为旧仓库名的直接替换；必要时请参考本文件或提交 issue。
