面试Slides大纲（10页｜AERIS-AERIS）

1. 标题页
- AERIS-AERIS：面向WSN的环境自适应双阶段能效路由
- 作者/单位/关键词：PatchTST引导、熵权/模糊软决策、动态网关

2. 场景与问题
- 密集WSN在温湿度干扰、拓扑变化、网关拥塞下的PDR与能耗难以同时优化
- 目标：在保持高PDR的同时延长寿命、降低热点风险

3. 技术主线（一图总览）
- 预测（PatchTST/DLinear）→ 熵权评分 → 模糊软决策 → 动态网关
- 轻重分离：预测离线/边缘，在线仅保留轻量规则

4. 模型与决策融合
- 熵权指标：残余能量、链路质量、预测负载/干扰
- 模糊系统：三规则簇（稳定性/公平性/拥塞回避），抑制抖动

5. 关键机制：动态网关
- 负载/时延/稳定性三者平衡
- 拥塞退避、周期性重评估、灾备回退

6. 实验设计与统计检验
- 数据与拓扑：Intel Lab + 多拓扑生成器
- 指标：PDR/能耗/首节点死亡、显著性检验（bootstrap、多重校正）

7. 结果Ⅰ：PDR-能耗与寿命提升
- 展示 publication_figures/*pdr_energy*.svg
- 展示 plots_curated/*lifetime*.svg
- 讲述：高PDR、低能耗、延迟FND（first node dead）

8. 结果Ⅱ：稳健性与显著性
- 展示 plots_curated/*significance*.svg
- 展示 plots_curated/*uncertainty_grid*.svg
- 讲述：跨拓扑/参数仍保持优势，统计显著

9. 消融/灵敏度与可落地性
- 展示 plots_curated/*ablation* 与 *sensitivity*.svg
- 开销评估：在线决策<ms级；预测可离线/边缘

10. 总结与下一步
- 工程侧：规则库可解释、可控；GPU路径与快速DLinear通道
- 研究侧：泛化到DTN/边缘协同；与AERIS论文深度对齐
- 预备问题：为何选PatchTST、熵权与模糊的互补性、网关稳定性控制

附：打开方式
- 图表目录：results/plots_curated、results/publication_figures
- 清单：results/plots_curated/manifest.json
- 一页纸：docs/Interview_OnePager_CN.md / docs/Interview_OnePager_EN.md