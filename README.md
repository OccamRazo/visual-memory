# Visual Memory

研究大模型如何从连续视觉流中选择、压缩、保存、取回和更新信息，当前聚焦超长视频理解。

- [项目状态](docs/STATUS.md)：当前任务、权威方案与下一步。
- [项目约定](docs/project-guide.md)与[工作记录规范](docs/work-records.md)。
- [研究调研](research/README.md)：文献、方法提案与时间索引。
- [执行方案](docs/plan/README.md)：当前验证方案及历史版本。
- [实验索引](experiments/README.md)：独立实验的配置、结果和审计记录。
- `writing/`：论文草稿、图表和周报。
- `notes/sessions/`：跨会话的简要上下文。

原多证据数据收集队列保持暂停，详见[暂停记录](experiments/EXP-20260917-videomme-multievidence50/README.md)。已按事件与语义重新分组，完成[已有 API 选出 caption 的复查](experiments/EXP-20260917-videomme-semantic-reassessment/README.md)，其后[50题API原始证据定位](experiments/EXP-20260917-videomme-api-source50/README.md)均已产生处理结果，后台已停止；失败及未确定题的原因诊断已完成，[32题API定向修复与补证](experiments/EXP-20260918-videomme-api-repair32/README.md)已完成，固定50题累计32题多组源支持；[新增50题源核验](experiments/EXP-20260918-videomme-api-expand50/README.md)亦已完成，累计52题多组源支持，已超过50题目标。

## 代码状态

旧 EG-VQA 验证实现已于 2026-09-16 停用，源码、脚本、测试、依赖及数据说明统一收纳于[实验代码归档](experiments/EXP-20260907-egvqa-15h-pilot/code/README.md)。它只保留作历史追溯，不作为后续开发的基础；实验结果和[失败审计](experiments/EXP-20260907-egvqa-failure-audit/README.md)继续保留。

目前没有正式实现。后续一次性验证代码及其专用依赖随对应实验保存，只有确定用于持续开发的实现才进入根目录的 `src/`、`scripts/`、`tests/`；目录按实际需要创建。
