# 新增50题原始证据核验，累计多证据题超过50

2026-09-18，Asia/Shanghai。用户要求沿用上一轮处理方式新增50题，并使完全处理完的多证据问题累计超过50题。基线是[原固定50题及其修复](../EXP-20260918-videomme-api-repair32/README.md)中已获源支持的32题；本轮至少新增19题通过，并处理完全部首批50题。未达目标时按冻结顺序每批补5题。

## 当前状态

**已于2026-09-18 01:47:39完成50/50题，累计52题多组源支持，目标达成。** 新批20题多组、14题单组/冗余、16题未解决（13输出无效、2参考冲突、1请求失败，原标签preparation_failed）。48题备用未启用。自动终态审计于01:47:40通过，核对新批34个支持结果的源包和3,446张来源帧哈希。两批共100题：52多组、26单组/冗余、22未解决；52题共172个语义组。见[终态摘要](terminal_summary.json)、[总体统计](overall_summary.json)、[累计题目索引](cumulative_supported_multi.json)及[5题原始例子](five_examples.json)。四步方法实验尚未运行。

用户明确无需持续等待，队列已独立执行完毕。另有 `tmux videomme-expand50-audit` 等待运行锁释放后自动核查50题处理完整性、至少51题累计通过、源包及原帧哈希，再将终态摘要和累计题目索引写入本实验目录；见[audit_launch.json](audit_launch.json)。该步骤只读源结果，不产生API调用；源核验未完成或目标未达时拒绝生成成功摘要，错误保存在本机 `final_audit.log`。离线14项回归、输入去重/哈希与入口链接检查见[validation.json](validation.json)。

## 选择与计数

- 从188题caption语义候选出发，排除上一批50题所在视频，余119题/98视频；每视频只取一题，冻结98题顺序及输入哈希。
- 使用种子20260918，按原caption组数2、3、4及以上分层打乱并轮流选择；前50为必处理批，后48为备用。抽样不看本轮API结果；每个新问题均先做全caption/字幕定位。
- [manifest.json](manifest.json)记录完整候选顺序和分层，[baseline32.json](baseline32.json)记录32题历史结果及来源哈希。98个视频与上一批50个不重叠；它们仍是开发候选，不能宣称从未被历史实验接触过。
- 只有终态 `source_supported_multi` 计数：原源核验通过、必要事实和关系有来源、无最终必要缺口、参考一致、需联合至少两个语义组。单组/冗余、caption候选和任何失败均不计入。按qid去重，不叠加其他历史实验的重叠结果。
- 原32题中13题来自初次源核验、19题来自修复，沿用历史判定，不伪称本轮重核；不同哈希算法明确记录（初版来源包为规范JSON摘要，修复版为文件字节摘要）。

## 处理流程

沿用[修复协议](../EXP-20260918-videomme-api-repair32/README.md)，使用 `qwen3.8-flash`：

1. API接收完整问题/选项及该视频全部caption、原始字幕，选择取证窗口；不提供参考答案。无40条caption限制。
2. 实际解码候选窗口帧、读取同步字幕；API在不见参考答案的情况下提取事实、来源ID、语义组及跨段关系。
3. 在事实来源附近加密取帧，保留所有粗帧与字幕；API结合原始来源、题目选项及参考答案做最终核验，可修正前一步引用和分组。
4. 若有必要缺口或参考冲突，再检索全部caption/字幕并补证一次。每题最多2轮，每阶段最多2次API尝试；全部原始响应和失败记录保留。

证据按事件、动作、状态和阶段分组，连续活动也可分组；语义组不受取帧窗口约束。API只引用当前来源ID，脚本保存视频ID、帧实际PTS点或完整字幕cue区间；离散来源保留间隙，不合成长时段。静态帧可支持静态事实，不能自动证明连续动作。

[protocol.json](protocol.json)版本2.1-expand。科学通过标准、观察和核验提示与修复版一致；改动仅为新题全量定位、确定性新样本选择、达到累计目标后的调度及导出，以及将 `RemoteProtocolError` 正确归为API故障。并发3，temperature=0，thinking=false。

每次检索最多16个窗口、合并600秒；粗帧名义间隔4秒/最多200帧，加密名义1秒/最多240帧，过预算时记录增大的间隔。保留全部粗帧，不能用少量正例冒充全视频最大值/不存在/首次出现的穷尽证明。没有音频；原视频抽样帧和字幕的AI核验不等于人工金标或精确事件边界。

终态区分多组通过、单组/冗余、证据不足、参考冲突、输出无效、API故障、准备失败、中断。连续5题API故障或鉴权拒绝停止；不无限重试失败题。初始50题即使提前达到51题目标也全部处理；只有首批结束仍不足51时才启用备用批。备用池耗尽则如实报告未达标。

## 版本、产物与复现

分支 `work/motivation-data-prep`，基础提交 `cef8161`；运行的是未提交代码，实际版本用部署和代码快照哈希追踪。原源为本机Video-MME-long视频/字幕、WorldMM 10秒caption；上游文件提交版本未知，逐输入、视频、字幕和帧用哈希追踪。环境见[environment.json](environment.json)。

本机产物根目录：

`/mnt/raid5-01/baorui/visual-memory/EXP-20260918-videomme-api-expand50/run-001`

- `manifest.json`、`inputs/`、`baseline32.json`：冻结98题、原32题基线及哈希。
- `queue.json`：真正入队的题目及批次；备用不自动算已处理。
- `status.json`：实时处理数量、累计多组数量、目标是否达到、心跳和用量；`background.log`逐题终态。
- `results/`：逐题事实—源点/时段—语义组—关系；`source/`、`combined/`：抽帧和完整源包。
- `calls/`：API请求、原始响应、重试、错误、实际模型及用量；`deployment/`、`code_snapshots/`：冻结代码和协议。
- `all_results.json`、`supported_multi.json`、`cumulative_supported_multi.json`、`summary.json`：批次边界和退出时导出。累计索引提供每题原结果/源包路径与哈希，原证据不覆盖。

仓库根目录执行：

```bash
# 只首次准备；冻结清单已存在时拒绝覆盖
/home/baorui/projects/WorldMM/.venv/bin/python experiments/EXP-20260918-videomme-api-expand50/code/expand.py prepare
# 自动完成首批50，必要时按批补选；会产生API调用
/home/baorui/projects/WorldMM/.venv/bin/python experiments/EXP-20260918-videomme-api-expand50/code/control.py start
# 只读查询
/home/baorui/projects/WorldMM/.venv/bin/python experiments/EXP-20260918-videomme-api-expand50/code/control.py status
# 离线检查，无API调用
/home/baorui/projects/WorldMM/.venv/bin/python -m unittest discover -s experiments/EXP-20260918-videomme-api-expand50/code -p 'test_*.py' -v
```

同设备恢复可运行冻结部署的 `expand.py run`，跳过已有终态并从当前批次继续。`control.py stop`请求停止；STOP或熔断存在时须先检查原因。唯一任务入口为 `expand.py`，`repair.py`和`engine.py`为复用实现。未将凭据、大帧包或调用日志加入Git。
