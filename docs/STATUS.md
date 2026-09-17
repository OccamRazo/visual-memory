# 项目状态

- 当前任务：内容关联记忆与证据完整性的动机验证；[四步方案](plan/content_linked_memory_completeness_validation_2026-09-16.md)中的存取方法实验尚未运行。
- 状态：2026-09-17 按用户要求**暂停全量 caption 多证据收集方案**。当前确认 11 道多证据题、36 个必要证据组，目标 50 道未达成；暂停时 816 道有处理结果，其中 646 道技术失败，不能计作完成验证。详见[暂停记录及实验入口](../experiments/EXP-20260917-videomme-multievidence50/README.md)。已无本地实验进程，保留暂停标记，不自动恢复。
- 已有数据：Video-MME-long 的 300 视频/900 QA/74,136 caption 已对齐。原 60 题经后续分组复核，52 题通过（44 题单组、8 题多组）、8 题存疑；历次结果及修订关系见[实验索引](../experiments/README.md)。AI 复核非人工金标，已接触视频排除规则继续有效。
- 下一步：等待用户决定是否调整方案；本次仅离线保存结果、补齐项目文档并提交，不追加 API 调用，不启动方法实验。
- 项目入口：[项目约定](project-guide.md)、[工作记录规范](work-records.md)、[方案索引](plan/README.md)、[研究索引](../research/README.md)。旧 EG-VQA 实现已[归档停用](../experiments/EXP-20260907-egvqa-15h-pilot/code/README.md)，当前无正式实现。
- 分支与交付：`work/motivation-data-prep`；本轮数据准备、暂停归档和文档维护纳入本地提交，具体提交见分支 Git 日志；未推送，无跨设备交接。
