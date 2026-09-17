# Video-MME：60题时间证据组划分

2026-09-17 完成。冻结原有 **60 题 / 47 视频 / 79 评分事实**，全部给出时间分组并逐题进行 Codex 源复查，原题和原始证据未覆盖。结果是 **AI 审计标注，不是人工金标**。

|结果|数量|
|---|---:|
|全部候选证据组|153 组，平均 2.55 组/题|
|通过源支持及删组复核|52 题|
|其中单组足够|44 题|
|其中需要多组|8 题：5 题两组、2 题三组、1 题四组|
|通过复核后的保留组|64 组，平均 1.23 组/题（分母为52）|
|保留分组但标记存疑|8 题，不计可靠必要组数|

候选组不是全部必要，也不是全片所有相关片段的穷举；“不可再删”仅针对当前提供的源证据和核验器，不等于全视频最少组数。153 组不能作为必须跨组的统计。原60题经过更严格的时间/删组检查后有8题存疑，**不能再无条件把原60题全部视为充分证据样本**。

本机正式结果位于 `/mnt/raid5-01/baorui/visual-memory/EXP-20260917-videomme-evidence-groups/run-002-continuity/final/`：

- [逐题浏览原视频区间、原帧和原字幕](/mnt/raid5-01/baorui/visual-memory/EXP-20260917-videomme-evidence-groups/run-002-continuity/final/index.html)
- [60题分组总表](/mnt/raid5-01/baorui/visual-memory/EXP-20260917-videomme-evidence-groups/run-002-continuity/final/groups60.md)
- [完整标注JSONL](/mnt/raid5-01/baorui/visual-memory/EXP-20260917-videomme-evidence-groups/run-002-continuity/final/evidence_groups60.jsonl)、[逐组CSV](/mnt/raid5-01/baorui/visual-memory/EXP-20260917-videomme-evidence-groups/run-002-continuity/final/groups.csv)
- `group_packages/<qid>/<Gxx>.json`：153份逐组原始证据包，保存视频路径、起止时间、实际帧和原字幕，不包含参考答案或生成caption。浏览页直接播放原视频对应区间，未批量另存MP4。

处理方法见 [METHOD.md](METHOD.md)，固定规则见 [protocol.json](protocol.json)、[复裁规则](adjudication_rules.json)，实现见 [code/group.py](code/group.py)。流程为：冻结源数据 → API提议连续活动组 → 投射原片段并补抽边界帧 → 独立API调用审计 → 源证据删组测试 → Codex逐题复查/有记录修订 → 完整性校验和导出。评分事实对核验器可见；这不是回答器的盲测。

本轮纠正了连续制作被按动作拆组、同一事件介绍与收尾被拆组、滚动字幕把独立章节误合并、边界混入下一动物/表演者、模型混淆主题概念以及局部贪心漏测替代组等问题。15题使用冻结的源复查修订输入，3题附加语义解释约束；全部保存在 `group_overrides/`、`evaluation_notes/`。旧输入在 `adjudication_history/`，旧结果在本机 `superseded_results/`，技术失败在 `failed_results/`，不静默覆盖。

|存疑题|保留原因|
|---|---|
|674-2|相邻麻将教学主题的组粒度不稳定，不认定为可靠跨组样本|
|885-2|球衣/字幕可证曾获冠军，但“previous competition”具体时间指向不明确|
|808-3、863-2|原因/动作可见，人物姓名绑定等完整事实仍有缺口|
|702-3|砸窗男子与后段前男友是否同一人，跨场景身份对应未充分确认|
|793-3|11个正例片段不等于证明全片恰好11个已揭秘魔术，缺穷尽范围依据|
|689-1|“赢得太空竞赛”的强概括及删组充分性尺度不稳定|
|889-3|自豪/感动的主体、时间及因果方向不稳，自动所得5组不予确认|

源文件 SHA256：`0292dc45de55b0a2b7b500880174a84ce2b52651c15921cdf86c432278eda12b`。结果 SHA256、模型用量及统计见 [summary.json](summary.json)；逐题清单见 [manifest.json](manifest.json)。

正式运行433次API调用，0次传输/API失败，**12,782,698 token**；另保留早期v1.0先导31次调用、1,220,085 token。合计464次、14,002,783 token，不含本Codex会话；费用未计算。请求及返回模型为 `gpt-5.6-luna` / `gpt-5.6-luna-2026-07-09`。8份技术格式失败记录均归档并解决，不等同于API失败。先导产物保留在本实验大目录根部，正式数据仅以 `run-002-continuity/final/` 为准。

[完整性校验](validation.json)通过：60题及原评分事实保持不变，2041个源锚点可解析，3928份唯一帧文件哈希正确，47个原字幕成员与原压缩包一致；132个实际删组请求均检查了原始载荷，被移除组内容未混入。所有组区间互不重叠且包含所引原始锚点。`py_compile`、隔离逻辑检查及交付链接/文件检查见 [delivery_checks.json](delivery_checks.json)。

环境见 [environment.json](environment.json)，输入、提示、代码和复裁文件哈希见 [reproducibility.json](reproducibility.json)。离线运行 `code/export.py` 可重建已有标注，不调用API；全新模型调用不保证相同输出，边界仍受稀疏帧限制。逐帧连续观看、人工校准及四步存取实验均未运行。当前仍在 `work/motivation-data-prep`，本次随暂停归档纳入本地提交，未推送，88个已接触视频的未来未见测试排除规则不变。
