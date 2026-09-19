# 项目状态

- 当前任务：内容关联记忆与证据完整性的动机验证；[四步方案](plan/content_linked_memory_completeness_validation_2026-09-16.md)中的方法实验尚未运行。
- 上轮结果：按用户要求，已完成[已有caption语义复查](../experiments/EXP-20260917-videomme-semantic-reassessment/README.md)。清点825题/1060条历史记录；242题有可恢复caption并全部复查：214题多组、22题单组、6题未确定。其中188题为“需联合多组＋caption覆盖充分＋参考一致”的语义候选，共581组。583题没有可恢复caption，未判单组或不合格。
- 口径：事件/动作/状态/语义优先；同一活动不强制合并，时间相隔较远可分别成组。该caption复查阶段只做文字判断，无新的逐题看图、删组或反搜验证；分组、联合需求和覆盖程度分别记录。旧结果保留，语义候选不与源确认数量混加。
- 原流程：[全量caption多证据收集](../experiments/EXP-20260917-videomme-multievidence50/README.md)保持暂停，暂停时11题/36组源确认，原50题源确认目标未达成。复审前阶段复用源检查的15题/47组另存，不代表本轮视觉验证。未启动新采样或方法实验。
- 已有数据：Video-MME-long的300视频/900 QA/74,136 caption已对齐；历史60题等修订关系见[实验索引](../experiments/README.md)。AI判断非人工金标，已接触视频排除规则继续有效。
- 当前执行结果：[固定50题及修复](../experiments/EXP-20260918-videomme-api-repair32/README.md)后32题多组源支持；[新增50题源核验](../experiments/EXP-20260918-videomme-api-expand50/README.md)于2026-09-18 01:47:39全部完成，新增20题多组。两批100题合计52题多组、26题单组/冗余、22题未解决（17输出无效、3参考冲突、2准备/请求失败）。52题来自52视频、172语义组，超过50题目标已达成；48题备用未启用，后台及终态审计已结束。审计核对新批34个源支持结果和3,446张帧哈希，非人工金标。权威统计和5个例子见新实验入口；未追加重试或方法实验。
- 项目入口：[项目约定](project-guide.md)、[工作记录规范](work-records.md)、[方案索引](plan/README.md)、[研究索引](../research/README.md)。旧EG-VQA实现已[归档停用](../experiments/EXP-20260907-egvqa-15h-pilot/code/README.md)。
- 分支与交付：`work/motivation-data-prep`；基底为暂停归档提交`cef8161`；caption复查、两批源核验、定向修复与累计52题结果纳入本次本地提交；提交号见当前分支Git日志。未推送，无跨设备交接。
