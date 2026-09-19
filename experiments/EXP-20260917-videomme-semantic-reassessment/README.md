# Video-MME：按事件与语义重新划分证据组

2026-09-17。已完成 `run-002-caption-semantic`：按用户最新指示，**仅复查历史 API 已选 caption 的语义，不再逐题查看原始图像，不运行删组或反搜**。原始采样队列保持暂停。

## 判断口径

- 按事件、动作、对象状态、比较对象及语义阶段分组。同一堂课、同一制作过程中的不同动作可分别成组。
- 时间相隔较远的观察可分别成组，即使活动连续或内容相似；相邻片段也可因语义变化分组。不设统一秒数门槛，不按 caption 条数机械分组。
- 分别输出“相关证据是否多组”“回答是否需联合多组”“caption 是否覆盖答案”。多组但内容缺失仍保留多组标签；重复展示同一答案可为多组但无需联合。
- 本轮结果是 **caption 语义判断**。不声称重新核验过视频真实性或得到全视频最少证据组；时间边界为 caption 粒度。

## 输入与处理

1. 冻结四轮历史的 **825 个去重题号、1,060 条记录**，保留原判定及文件哈希。
2. 收集各历史版本 API 提议的 caption ID、定位区间与分组区间。取显式 ID 及所有与区间重叠的 caption，按 ID 去重；不再设 40 条上限，也不重新搜索整段视频。
3. **242 题**可恢复非空 caption 集，共 **13,429 条题目—caption 记录**（跨题可重复）。583 题无可恢复选择，其中 534 题只有技术失败，49 题有其他记录但没有选出的 caption；它们不判作单组或不合格。
4. 将原题、选项、参考答案及所选 caption 一次传给 `qwen3.8-flash`，每题一次，8 并发、关闭深度思考。不给旧判定，避免延续“连续活动只能一组”的错误。
5. 保存分组、引用 ID、贡献、联合需求、覆盖程度及缺失项。从实际引用的 caption 计算时间范围并校验 ID；原始响应和失败请求全部保留。没有额外视觉 API、删组测试或反搜调用。

当前协议：[caption_protocol.json](caption_protocol.json)。代码：[caption_review.py](code/caption_review.py)、[离线检查与导出](code/export_caption_review.py)。原题和官方答案未改。

## 结果与产物

242题caption语义复查全部完成，未留待处理题：

| 判定 | 题数 |
|---|---:|
| 相关caption可分为多个语义组 | 214 |
| 单组 | 22 |
| caption不足以判断分组 | 6 |
| 无可恢复caption选择，未作语义判断 | 583 |

214道多组题中，188道同时被判定需联合多组、caption覆盖充分且参考答案一致，共581组，平均3.09组/题。这是caption语义候选数量，非重新完成源视频验证的数量。其余26道保留多组标签和具体问题。

[汇总](caption_summary.json) 及 [逐题表](caption_review_table.csv) 为权威摘要；[caption_decisions.json](caption_decisions.json) 保存每题分组及理由，[caption_multi_candidates.json](caption_multi_candidates.json) 单列“多组＋需联合＋caption覆盖充分＋参考一致”的语义候选。它们不与历史源确认数量混加。

例如886-2同一次周二腿部训练按哈克深蹲、负重行走弓步、超级组、递减组、站姿提踵分为5组（引用caption范围1410–1490、1490–1560、1560–1620、1620–1690、1690–1730秒）。这些片段相邻连续仍可因动作不同而分组。672-2瑜伽顺序为4组，caption未明确命名中间体式，覆盖标partial，不因此合并为一组。

243次API请求：240次直接通过结构检查，1次缺字段仅重试该题成功，另外2次通过明确的格式规范化恢复；所有242题有最终文字判定。总返回用量2,363,189 tokens（输入2,218,764，输出144,425），包含失败请求，无缺失usage；价格未查询，费用未知。实际调用窗口为 2026-09-17T19:42:16.049818+08:00 至 2026-09-17T19:50:09.217634+08:00。

[离线检查](caption_checks.json)通过：825题覆盖、1,060条历史记录哈希不变、825份caption包哈希一致、5,547处引用ID有效，242个请求均为纯文字且使用指定模型。Python编译与Git空白检查通过；本轮原图验证not run（按用户要求）。

本机完整请求、响应、选中 caption、选择溯源和可浏览页面：

`/mnt/raid5-01/baorui/visual-memory/EXP-20260917-videomme-semantic-reassessment/run-002-caption-semantic/`

其中 `caption_review.html` 可按题号搜索，逐组展开原 caption 和时间；`packets/` 是实际模型输入，`selection_provenance/` 保存历史选择来源，`calls/` 逐次保留请求、响应与用量，`code_snapshots/` 冻结实际运行代码。完整内容在本机可用，不纳入 Git。

## 执行与复现

基础提交 `cef8161`，分支 `work/motivation-data-prep`，本轮代码尚未提交。使用 WorldMM 现有虚拟环境；caption 来源为原数据准备冻结的 WorldMM caption 银行，哈希见 [caption_manifest.json](caption_manifest.json)。API 请求名称为 `qwen3.8-flash`，后端实际返回名称逐调用保存。凭据只从忽略的 `tmp/api.json` 读取；使用现有本机代理 :7897，不修改系统设置。

```bash
# 离线：恢复冻结的选中caption清单，不调用API
/home/baorui/projects/WorldMM/.venv/bin/python experiments/EXP-20260917-videomme-semantic-reassessment/code/caption_review.py prepare
# 会调用API：仅处理尚无成功结果的题，每次调用均保留独立attempt记录
/home/baorui/projects/WorldMM/.venv/bin/python experiments/EXP-20260917-videomme-semantic-reassessment/code/caption_review.py review
# 离线：检查825题覆盖、1060条历史哈希和引用，导出表格及浏览页
/home/baorui/projects/WorldMM/.venv/bin/python experiments/EXP-20260917-videomme-semantic-reassessment/code/export_caption_review.py
```

每个请求关闭 SDK 自动重试；连续失败3次停止调度。输出缺字段等失败可仅重跑缺失题，原失败不覆盖。唯一可确定的 ID 补零、未支持枚举值等格式修正见 [修正记录](caption_output_normalizations.json)，用 [离线脚本](code/normalize_caption_outputs.py)恢复，不调用 API。两题“多组但单组已够”的文字更正见 [caption_overrides.json](caption_overrides.json)，与原模型输出分别保存。API 用量包含返回了 usage 的失败请求，缺失用量单列。模型新调用不保证复现相同判断，冻结输入、响应和代码支持离线重放。运行期间仅维护了离线汇总逻辑，实际已加载代码与请求时磁盘代码的对应关系见本机 `runtime_manifest.json`。

## 保留的早期复审

`run-001` 原计划先复审旧判定、再做源确认。用户中途要求改为直接复查 caption，因此停在820/825条记录处，余5条不补跑；它不是当前 caption 结果。旧模型判定仍存在不当合并连续活动的理由，未逐条纠正，不能据此继续准入。其 [协议](protocol.json)、[清单](inventory.json)、[原始判定](decisions.json)、[摘要](summary.json) 原样溯源；摘要补记中止原因及含失败请求用量。

此前沿用/复查源包的15题47组保存在 [confirmed_manifest.json](confirmed_manifest.json)，包括旧11题和撤销错误分组否决的瑜伽、戈雅经历、外星生命采访、公司介绍顺序4题。它们使用旧源检查，非新的完整视觉API验证；与本轮caption语义标签可能不同。`code/source_prompts/` 是中途准备但**未用于本轮caption复查**的源核验提示草案。

该阶段产物位于本机同实验的 `run-001/`；旧实验结果不改写。本轮不抽新题，不启动[四步方法实验](../../docs/plan/content_linked_memory_completeness_validation_2026-09-16.md)。
