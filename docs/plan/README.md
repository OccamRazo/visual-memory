# 研究与工程方案

> 2026-09-17：当前[多证据数据收集方案已暂停](../../experiments/EXP-20260917-videomme-multievidence50/README.md)，50 题目标未达成；以下四步方法实验尚未运行，等待用户确定后续方向。

当前优先任务是 [内容关联记忆与证据完整性：动机验证](./content_linked_memory_completeness_validation_2026-09-16.md)（2026-09-16）：先以小规模补全验证完整性的答题作用，再定位完整性缺失，随后分别做内容关联存取四格、固定写入器交换任务先验。第 3 步保留原设计，第 4 步采用通用/匹配/错配三组，不合并为多因素网格；独立任务需求诊断不恢复。简答由独立大模型按必要事实评分并人工抽审，证据充分性另行核验，原题型结果单列；固定前端、回答模型和投射，暂不训练完整学习系统。[Video-MME-long 数据准备已启动](../../experiments/EXP-20260916-memory-data-prep/README.md)，四步实验尚未执行。[9 月 15 日方案](./task_structured_memory_motivation_validation_2026-09-15.md)保留为前版。

历史完整工程主稿是 [BundleMem 完整研究与工程方案](./cvpr2027_bundlemem_engineering_plan.md)（v2.0，2026-09-07）。它包含原论文的动机、形式化与方法，以及闭环扩展、数据、工程接口、配置、验收、实验、资源和论文交付；以下导航供需要对应历史设计时使用：

- 理解方法：主稿第 1–6 节。
- 选择数据与开展实验：第 7–8 节。
- 开始实现：第 9 节的 D0/D1、数据契约、配置和 C01–C12 验收。
- 资源、排期与论文：第 10–12 节。

以下参考文件通过原分支合并保留，属于历史版本；与主稿不一致时，实施设计以主稿为准：

| 文件 | 来源与用途 |
|---|---|
| [BundleMem 闭环设计](./cvpr2027_bundlemem_closed_loop_design.md) | `work/bundlemem-closed-loop-plan@1f6d6df`，主稿的主要方法基础 |
| [CVPR27 工作规划](./cvpr2027_closed_loop_visual_memory_plan.md) | `work/cvpr27-plan@e0a241d`，工程组织和近期近邻参考 |
| [原论文初稿](../../writing/drafts/fqr_bundle_memory_cvpr/main.tex) | 原始 storage-only BundleMem；实验前初稿，历史结果占位保留 |

规划中的模块、命令和指标均有明确状态；方案完整不等于模型、模拟器或实验已经运行。实际工作开始后，各独立实验在对应 `experiments/EXP-YYYYMMDD-short-name/README.md` 记录版本、执行、结果和下一步。
