# 实验索引

当前全量 caption 多证据收集已于 2026-09-17 按用户要求暂停，确认 11 题，50 题目标未达成。四步存取方法实验尚未运行。规范见 [工作记录](../docs/work-records.md)，当前任务见 [项目状态](../docs/STATUS.md)。

| 实验 | 状态与主要结果 |
|---|---|
| [Video-MME 多证据富集](EXP-20260917-videomme-multievidence50/README.md) | 已暂停；全视频 caption + qwen3.8-flash；11 题确认、36 个必要组 |
| [60 题时间证据组](EXP-20260917-videomme-evidence-groups/README.md) | 已完成；52 题通过，其中 44 题单组、8 题多组；8 题存疑 |
| [初版 60 题源复核](EXP-20260917-videomme-evidence60/README.md) | 当轮完成；60 题/47 视频/79 事实，使用时须结合后续时间分组判定 |
| [首批标注审计](EXP-20260916-videomme-annotation-audit/README.md) | AI 审计完成；60 题文本、12 题源先导，非人工校准 |
| [Video-MME 数据准备](EXP-20260916-memory-data-prep/README.md) | 首批完成；300 视频/900 QA/74,136 caption，60 题草稿与固定 12 题先导 |
| [EG-VQA 失败审计](EXP-20260907-egvqa-failure-audit/README.md) | 历史审计保留；相关实现已停用 |
| [EG-VQA 单卡 pilot](EXP-20260907-egvqa-15h-pilot/README.md) | 历史工程 smoke，科学结论不充分；实现已归档停用 |

各轮结果不能相加视作互不重叠样本。原始数据和完整日志不在 Git 中；复现依赖各实验 README 所列设备、路径与冻结输入。
