# 研究与工程方案

当前实施主稿是 [BundleMem 完整研究与工程方案](./cvpr2027_bundlemem_engineering_plan.md)（v2.0，2026-09-07）。它已包含原论文的动机、形式化与方法，以及闭环扩展、数据、工程接口、配置、验收、实验、资源和论文交付；接手者无需先阅读旧方案或聊天记录。

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
