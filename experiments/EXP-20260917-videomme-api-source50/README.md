# Video-MME：50题 API 原始证据定位与核验

后续：2026-09-18用户授权的[32题API定向修复与补证](../EXP-20260918-videomme-api-repair32/README.md)已单独启动；本实验原结果、失败记录和熔断标记保留。

2026-09-17。状态：本轮50题均有处理结果，后台已停止；连续失败触发的熔断标记保留。13题多组源支持、5题单组/冗余、23题技术失败、9题未确定。这里的源支持仍是API判断，非人工金标。

已完成[全部23道technical_failed与9道source_unresolved的原因检查](terminal-failure-analysis.md)。至少5题存在已证实的重叠窗口帧归属误报，另有盲观察漏传选项、审核分组矛盾和人物错误关联。当前仅完成诊断，冻结代码和结果未修改、未重跑。终态计数见[terminal_summary.json](terminal_summary.json)。

## 固定输入

从[caption语义复查](../EXP-20260917-videomme-semantic-reassessment/README.md)的188道候选中选择50题、50视频、157个候选组。固定随机种子20260917，按2组、3组、4组及以上三档轮流取样，各档内固定打乱，每视频最多1题。为控制这轮处理量，要求每题最多6组，所选caption去重后总时长不超过300秒。它是有时长限制的先导样本，非总体随机样本；不按新API输出换题，也不保证50题全部通过。

[manifest.json](manifest.json)冻结题号、输入哈希、caption时长及原视频路径，选择发生在本轮视觉API输出之前。[protocol.json](protocol.json)冻结模型、抽帧、重试和停止规则。原视频及旧实验只读，原暂停采样队列不恢复。

## 自动流程

| 阶段 | 输入 | 处理与输出 |
|---|---|---|
| 原始来源准备 | caption引用的各个时间段、原视频、SRT | 合并相交区间，保留不相交区间，前后扩展3秒；按约4秒间隔抽帧，记录实际解码PTS和图像哈希；匹配原字幕 |
| 盲定位API | 原题、实际帧、同步字幕；隐藏caption、选项和答案 | 输出原子事实、源引用、候选事实时段、关系与缺失项 |
| 细化API | 候选事实时段及前后3秒、约1秒间隔原帧、字幕 | 检查前轮观察，修正事实与时段；记录边界不确定性。前轮模型文字只作假设 |
| 独立源核验API | 细化后的实际帧、字幕、事实、原题及参考答案 | 逐事实检查来源支持、参考一致性、跨片段关系及多组互补性；不运行删组测试或全视频反搜 |
| 自动归档 | API输出及实际源包 | 校验来源ID、时段、关联，输出多组支持、单组/冗余、未确定或技术失败；保存每次调用与费用用量信息 |

全程使用 **qwen3.8-flash**，关闭深度思考，3题并发，每阶段最多2次尝试。1.1版依据被引用的原字幕/实际帧时间自动扩展时段边界（每端最多10秒，不改来源引用），再执行完整校验；原始响应和校正记录均保留。原始内容以**原视频抽帧＋原始字幕**输入，不上传整段视频或音频。需要声音但字幕不足的问题保持未确定；不声称听过音频。Video-MME此次没有可用的事实级官方时间金标，caption时间仅用于定位。

时间输出是**原始来源支持的见证片段**，依据实际帧PTS及字幕时码，约1秒目标抽样精度；不是逐帧标注的完整事件起止边界。稀疏帧不能证明未采样处没有事件，计数/首次出现/全视频否定问题可因范围不足保留未确定。不同动作/状态/语义阶段可分别成组，即使活动连续。

## 后台运行与恢复

使用 `/home/baorui/projects/WorldMM/.venv/bin/python`，基底提交`cef8161`、任务分支`work/motivation-data-prep`；本轮代码未提交。API凭据仅从被忽略的`tmp/api.json`读取，本机已有代理`:7897`。依赖来自已配置环境：PyAV、Pillow、pysrt、httpx、openai。实际模型名称逐调用保存。

完整本地产物：

`/mnt/raid5-01/baorui/visual-memory/EXP-20260917-videomme-api-source50/run-001/`

- `status.json`：每20秒更新；当前阶段、已处理数、分类、API用量。
- `results/`：每题完成即落盘，含`fact_evidence`与`cross_segment_relations`；每条事实绑定视频ID、时段、帧/字幕ID。
- `source/`：实际抽帧、PTS、哈希、原字幕及请求窗口。
- `calls/`：请求（图片使用哈希及本地路径代替base64）、全部响应、失败与重试提示。
- `code_snapshots/`、`deployment/`：实际实现及后台部署快照。
- `all_results.json`、`supported_multi.json`、`summary.json`：任务结束时自动导出，`completed`表示50题均产生处理结果，不等于50题全部通过。

后台管理脚本为[control.py](code/control.py)：`start`冻结代码并创建tmux会话，`status`只读查询，`stop`请求温和停止。先导或旧部署尚占用队列锁时自动等待，随后接续。

同一队列用文件锁防止重复启动；成功阶段按输入与实现哈希缓存，已有终态题默认跳过。每题失败最多尝试完当前阶段即记录并继续；连续5题技术失败，或认证被拒绝，自动触发熔断并暂停后续调度。进程中断后可从固定快照恢复。长时间无数据由网络超时处理，流式响应另有阶段时限。

```bash
# 只读查看状态
/home/baorui/projects/WorldMM/.venv/bin/python experiments/EXP-20260917-videomme-api-source50/code/run.py status
# 独立后台启动；冻结实现，断开对话仍运行，重复启动会拒绝
/home/baorui/projects/WorldMM/.venv/bin/python experiments/EXP-20260917-videomme-api-source50/code/control.py start
# 仅重试技术失败（原失败移入result_history，成功阶段缓存保留）
/home/baorui/projects/WorldMM/.venv/bin/python experiments/EXP-20260917-videomme-api-source50/code/run.py run --retry-failed
# 请求停止；已进行的API调用结束后停，不强杀或删除结果
 touch /mnt/raid5-01/baorui/visual-memory/EXP-20260917-videomme-api-source50/run-001/STOP
```

重启前检查并清理自己创建的STOP或熔断标记；不要无条件自动清除。进程完成、失败或熔断都会将状态写入文件；本轮不设通知或重复唤醒任务。

## 检查与限制

离线9项契约测试已通过：正确源引用、无效帧ID、空引用、时段未包含字幕、错组、保留非连续窗口、关系指向无效事实、无来源的正向审计。新增检查保证审计者引用不能移出该事实时段。先导851-3已完整通过三阶段流程；678-2两次细化输出曾因字幕句跨界被机器拒绝，已保留失败并在1.1规则下离线回放通过，不冒充已完成最终源审计。第一版后台工作进程已温和退出，已确认1.1队列在独立tmux会话中接续、3题并发；不丢弃调用或已完成结果。启动信息见[launch.json](launch.json)，当前会话为`videomme-source50-v2`。模型的源判断仍属AI核验，非人工金标；时段精度受抽样和字幕质量限制。API价格未查询，费用未知，账本记录实际返回token用量。

复现代码：[run.py](code/run.py)、[提示词](code/prompts/locate.txt)、[契约测试](code/test_contract.py)。所有结果支持追溯原始文件、请求和实现哈希；不覆盖旧版caption标签。

## technical_failed诊断

已对8道终态失败做[只读原因检查](technical-failures.md)：均因源ID、组归属或时段校验未通过；其中723-3已证明存在脚本对重叠窗口帧归属的误报。原8题检查保留；全部终态问题以[后续32题诊断](terminal-failure-analysis.md)为准。冻结实现尚未修复，诊断不改写原结果。
