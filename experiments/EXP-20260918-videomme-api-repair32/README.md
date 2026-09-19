# Video-MME：32题 API 定向修复与补证

2026-09-18，Asia/Shanghai。用户授权尝试让 API 解决上一轮的 `technical_failed`、`source_unresolved`。只重处理原固定50题中的23题技术失败和9题未确定；不补抽题，不恢复旧采样队列。上一轮18题已有源支持的结果保留为历史。

## 状态与依据

**已于2026-09-18 00:59:52完成32/32题处理，后台退出。** 本轮19题多组源支持、7题单组足够/冗余、4题输出无效、1题准备失败、1题参考冲突；26题获源支持，6题仍未解决。连同原18题历史结果，固定50题中共32题多组、12题单组/冗余、6题未解决。详见[终态摘要](terminal_summary.json)。以下先导与启动信息为过程记录。

- 先导3题全部完成：723-3、765-2为源支持但单组足够或组间冗余；763-1为需要联合多组且源支持。723-3实际划分2个语义组，不能把“单组/冗余”标签误读成只找到1组。
- 先导共10次API尝试，3次格式失败均在一次重试后恢复；返回用量341,880 tokens。详见不可变的[先导摘要](pilot_summary.json)。这不是32题的最终统计。
- 00:44已启动 `tmux videomme-repair32`，自动跳过先导结果、继续其余29题；3路并发，无需保持当前对话。实时进展以本机产物 `status.json` 为准，启动记录见[launch.json](launch.json)。
- 部署后的[检查快照](validation.json)记录实时进度及本机验证：编译、11项回归、32题新输入/原结果哈希和入口链接均通过。610-2在两次定位响应中仍引用不存在的caption/字幕ID，保留为 `output_invalid`，未伪造ID映射；当时队列继续处理其他题。
- 前因见[原50题实验](../EXP-20260917-videomme-api-source50/README.md)及[32题原因诊断](../EXP-20260917-videomme-api-source50/terminal-failure-analysis.md)。所属方案见[动机验证](../../docs/plan/content_linked_memory_completeness_validation_2026-09-16.md)。四步方法实验未运行。

## 输入、处理与输出

| 步骤 | 输入 | 处理与输出 |
|---|---|---|
| 固定范围 | 原50题清单和原结果 | 冻结32题、原状态、问题/选项、视频位置、旧结果哈希；见[manifest.json](manifest.json) |
| 定向检索 | 完整问题/选项、该视频全部caption和原始字幕、已知缺口；无参考答案 | `qwen3.8-flash`选择候选窗口。原9题未确定立即检索；23题技术失败先重核已有窗口，发现缺口再全量检索 |
| 观察原源 | 候选窗口中实际解码帧、同步原始字幕、完整问题/选项；无参考答案 | API提取事实、当前来源ID、语义组、跨片段关系、必要缺口；caption不交给视觉观察器作为事实依据 |
| 密集核验 | 保留全部粗帧/字幕，加密事实附近帧；问题/选项、观察结果、参考答案 | API重新核验实际来源，可改事实、引用及分组；脚本检查引用存在性与声明一致性，并绑定原始时间戳 |
| 有界补证 | 最终必要缺口或参考冲突 | 再由API检索全部caption/字幕并重复源核验，最多2轮源处理。仍不足或冲突分别保留，不强行通过 |

语义组按事件、动作、状态、阶段划分；连续活动可有不同组。检索窗口只控制取帧，既不限定语义组归属，也不直接充当证据组。

模型只引用当前帧/字幕ID，脚本从原始来源取时间：`frame_point`保存实际帧PTS（起止相同），`subtitle_span`保存完整字幕cue起止。每个事实保存 `video_id` 和可不连续的 `source_spans`，不把间隙填成长区间；跨段关系独立保存。审计新选的邻帧或字幕重新绑定时间，避免套用旧事实边界误拒。此轮不让模型手填精确事件边界。

## 协议与可复现范围

[protocol.json](protocol.json)版本2.0；请求和返回模型均为 `qwen3.8-flash`，temperature=0、thinking=false。数据仍为本地Video-MME-long原视频、官方字幕归档和WorldMM时间caption；使用逐输入/视频/字幕/帧哈希追踪，本地数据上游提交版本未知。caption库包含300视频/74,136条，每题检索使用对应视频的全部条目，无40条截断。

- 候选检索最多16个窗口、合并后600秒；该预算限制实际查看视频的量，不截断caption检索。不能覆盖时保留缺口。
- 粗帧名义间隔4秒、最多200帧；每个事实最多6个均匀分布引用锚点附近加密，名义间隔1秒、最多240帧。超过预算时增加间隔并记录实际值，不静默丢帧。全部粗帧仍交给最终审计。
- 每阶段最多2次尝试、最多2轮源处理；连续5题API故障或鉴权拒绝自动停止。输出格式错误与源不足分开记录，不沿用“technical_failed”混称。
- 最终状态：`source_supported_multi`、`source_supported_single_or_redundant`、`source_incomplete`、`reference_conflict`、`output_invalid`、`api_failed`、`preparation_failed`、`interrupted`。最终必要事实/关系未支持、必要缺口未清除或参考冲突均不通过。早期不确定项已解决或可选备注不阻塞通过。
- 无人工逐题看图；API源核验不是人工金标。输入没有音频；仅有抽样帧和字幕，不能宣称逐帧事件边界或全视频穷尽证明。充分性和需联合多组是模型判断，仍可能误判。

代码复用上一轮的抽帧、调用账本和生命周期，但替换取证契约；唯一运行入口是 `code/repair.py`，`engine.py`中旧阶段和 `max_evidence_interval_s=120` 遗留字段不在新流程启用。11项离线回归检查已通过，覆盖选项保留、点证据、离散来源、错误ID、邻帧重绑定、必要/可选缺口和分组一致性。

分支 `work/motivation-data-prep`，基底 `cef8161`；运行代码尚未提交，不能用基底冒充本轮运行版本。[环境记录](environment.json)、[提示词](code/prompts)、代码快照及部署哈希用于追踪；先导和后台快照不同，后台只增加启动工具、明确plan根对象的格式报错及相应测试，不改变通过标准。温度0不保证全新API调用完全一致。

## 本机产物与命令

设备和依赖见[environment.json](environment.json)。产物根目录：

`/mnt/raid5-01/baorui/visual-memory/EXP-20260918-videomme-api-repair32/run-001`

- `status.json`：实时状态/心跳、各状态题数、实际API用量；`background.log`：逐题终态。
- `inputs/`、`manifest.json`：冻结输入。`results/`：逐题结果，包含事实来源及语义关系。
- `calls/`：请求、全部原始响应、错误、重试、返回模型和用量。`source/`、`combined/`：实际抽帧及来源包。
- `code_snapshots/`、`deployment/`：冻结代码和协议。`all_results.json`、`supported_multi.json`、`summary.json`：每次运行退出时导出，运行中看实时状态或逐题结果。
- `combined50_status.json`：退出时合并状态；注明原18题为历史沿用，尚未重跑的题保留旧状态，不能混称本轮全部核验。

在仓库根目录执行（第一条仅首次准备，已有冻结清单时拒绝覆盖）：

```bash
/home/baorui/projects/WorldMM/.venv/bin/python experiments/EXP-20260918-videomme-api-repair32/code/repair.py prepare
/home/baorui/projects/WorldMM/.venv/bin/python experiments/EXP-20260918-videomme-api-repair32/code/repair.py run --limit 3
/home/baorui/projects/WorldMM/.venv/bin/python experiments/EXP-20260918-videomme-api-repair32/code/control.py start
/home/baorui/projects/WorldMM/.venv/bin/python experiments/EXP-20260918-videomme-api-repair32/code/control.py status
/home/baorui/projects/WorldMM/.venv/bin/python -m unittest discover -s experiments/EXP-20260918-videomme-api-repair32/code -p 'test_*.py' -v
```

`run`/`start`会产生API调用；`status`和测试不会。`control.py stop`请求当前阶段结束后停调度；存在STOP或熔断标记时拒绝启动，须先检查原因。普通恢复跳过终态，仅中断题使用已完成阶段缓存；不无限重试失败题。旧实验结果、失败调用和旧熔断文件原位保留。
