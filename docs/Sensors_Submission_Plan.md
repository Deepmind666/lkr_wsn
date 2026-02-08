# Sensors Submission Plan

## 1. Target Journal Alignment
- **Journal**: Sensors (MDPI) – Section *Sensor Networks* / *Wireless Sensor Networks*
- **Article Type**: Research Article (Engineering-focused, experimental validation)
- **Key Requirements**:
  - Structured manuscript: Abstract, Introduction, Related Work, Materials and Methods, Results, Discussion, Conclusions
  - Statistical rigor and reproducibility (data/code availability statements)
  - 6–10 high-quality figures/tables with full captions and multi-run statistics
  - 2022–2025 citation coverage, total references ≥ 45 (preferably 50–60)
  - Data sharing statement + Conflict of Interest + Funding disclosures

## 2. Manuscript Assembly Roadmap
1. **Abstract**: 200–250 words, structured (Background, Methods, Results, Conclusions)
2. **Introduction**: Rewrite to reference Sensors publications; clarify motivation vs. deployments
3. **Related Work**: Integrate latest (2023–2025) Sensors / IEEE access / Ad Hoc Networks papers; highlight gaps leading to AERIS
4. **Materials and Methods**:
   - System Model (Section 3)
   - Protocol Description (Section 4)
   - Experimental Setup (Section 5)
   - Statistical Methodology (new subsection) 
5. **Results**: Rebuild based on regenerated datasets; include statistical plots
6. **Discussion**: Practical implications, limitations, comparison to Sensors papers, future work
7. **Conclusions**: Concise summary, deployment outlook
8. **Additional Sections**: Data availability, Code availability, Conflicts, Funding, Acknowledgments, Author Contributions

## 3. Data & Experiment Checklist
- Re-run simulations with final configurations (Intel replay + synthetic topologies)
- Store outputs in `results/final/` with versioned timestamped JSON/CSV
- Provide run scripts & config files (`scripts/run_*`) with README usage
- Capture random seeds, sample counts, runtime environment
- Prepare statistical summaries (mean, CI, p-values, effect sizes) via reproducible scripts

## 4. Figure & Table Plan
- Energy vs. PDR Pareto (Intel replay)
- Boxplot/violin of energy consumption (multi-run)
- ECDF or Gardner-Altman for significance
- Scalability curve (25/50/75/100 nodes)
- Robustness heatmap / sensitivity analysis
- Protocol architecture diagram (vector)
- Tables: baseline comparison, statistical significance, ablation results, parameter settings

## 5. Citation Strategy
- Expand bibliography to 55+ entries
- Ensure ≥ 15 citations from 2023–2025 (Sensors, IEEE IoT J, Ad Hoc Networks, Computer Networks)
- Tag each section with missing citations; use Zotero/Better BibTex export for BibTeX accuracy

## 6. Immediate Next Actions
1. Finalize experiment rerun scope & configs (Priority #2)
2. Build canonical dataset + regenerate figures (Priority #3)
3. Integrate refreshed content into unified manuscript template (Priority #5)
4. Schedule writing sprints: Related Work update → Methods → Results → Discussion

---
Document owner: Codex (automation). Last updated: $(Get-Date -Format 'yyyy-MM-dd HH:mm')
