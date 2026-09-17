# Video-MME：60 题完整证据复核

2026-09-17 00:45–01:49（Asia/Shanghai）。状态：完成。最终 **60 题、47 个视频、79 条评分事实**，其中 13 题包含多个评分事实。原剩余 48 题及本轮补抽的 76 题均已有明确结论，没有待复核候选或未解决的技术失败。

| 来源 | 检查题数 | 入选 | 排除 |
| --- | ---: | ---: | ---: |
| 先前固定 12 题，沿用原审计 | 12 | 8 | 4 |
| 原开发集剩余 48 题 | 48 | 21 | 27 |
| 未处理题补抽，两批 48 + 28 | 76 | 31 | 45 |
| 合计 | 136 | 60 | 76 |

用户要求跳过歧义、不适配和证据不足题，补抽至 60 题。此次筛选形成的是 **AI 复核的开发/诊断集，非人工金标、自然分布评测集或未见测试集**。原始样本和排除记录保留。来源为[整体规划](../../docs/plan/content_linked_memory_completeness_validation_2026-09-16.md)、[数据准备实验](../EXP-20260916-memory-data-prep/README.md)及[先前审计](../EXP-20260916-videomme-annotation-audit/README.md)。本轮只处理 Video-MME，未运行四步存取方法实验。

## 数据与证据

[最终数据](</mnt/raid5-01/baorui/visual-memory/EXP-20260917-videomme-evidence60/final/evidence60.jsonl>) · [逐题证据查看页](</mnt/raid5-01/baorui/visual-memory/EXP-20260917-videomme-evidence60/final/index.html>)。

本机产物根：`/mnt/raid5-01/baorui/visual-memory/EXP-20260917-videomme-evidence60/`。

| 产物相对路径 | 内容 |
| --- | --- |
| `final/evidence60.jsonl` | 60 题完整记录：原题、改写、参考、最小评分事实、逐事实证据、审计与来源哈希 |
| `final/questions.jsonl` | 仅题号、视频历史 ID、题目；不含参考答案和标签 |
| `final/scoring_facts.jsonl` | 独立保存参考答案与评分事实 |
| `final/task_labels.jsonl` | 任务标签，只作元数据，不参与事实评分 |
| `final/evidence_index.jsonl` | 每条事实的帧/字幕 ID、证据包及审计指针 |
| `final/index.html` | 按题展开查看问题、事实、原帧、原字幕和复核说明 |
| `packages/`、`frames/`、`supplements/` | 原视频帧实际 PTS/哈希、原字幕时间/文本及明确标注的补充源证据 |
| `results/`、`calls/`、`codex_reviews/` | 原模型结果、API 请求/响应账本和当前会话的逐题判定 |
| `failed_results/v1.0/`、`codex_reviews_history/` | 12 次技术失败和显式修订前的判定，原记录不删除 |
| `sampling_manifest.json`、`batches/` | 固定补抽顺序、每批题号、执行版本和时间 |

仓库保留[汇总](summary.json)、[入选清单](accepted_manifest.json)、[全部去留及理由](dispositions.json)、[48 题阶段检查点](remaining48_summary.json)、[评分/证据修订](rubric_overrides.json)和[后续测试排除清单](future_test_exclusions.json)。所有接触过的 **88 个视频**均排除出未来未见测试候选，剩余 212 个 long 视频；同视频的其他题也一并排除。没有修改原开发/先导清单。

## 实际处理与判定

使用 `/mnt/raid5-01/baorui/Video-MME` 原视频和 `subtitle.zip`；已对齐的 WorldMM 约 10 秒 caption **仅作定位提示**。先完成原 48 题，再从其余 840 题按 `SHA256("20260917:replacement:<qid>")` 固定顺序补抽。题目顺序在回答前固定，但证据定位可见参考，不声称全流程盲选。

定位模型可见题目、参考、原字幕和检索到的 caption。观察器仅见改写题与实际源帧/字幕，不见答案、选项或评分事实。核验器另看同一源证据及参考事实，不看观察器回答；随后由当前 Codex 会话逐题检查源证据。模型提出的 72 个通过候选中，Codex 保留 52 个、排除 20 个，加先前 8 个得到 60 个。是否答对不作为入选标准。

“完整”指**每条必要答案事实及其关系都有可追溯源支持**，不等于逐帧穷尽全视频。主旨题可用明确目的与代表性内容；顺序、计数、否定和范围判断须有对应范围的证据。例如 859-1 的原话限定为没对 vlog 说话，不能推出工作期间很少说话；848-1 只有事件顺序，缺少指定章节标题的对应；这些题均排除。

去除选项依赖，保留必要时间/范围限定；评分事实和任务标签分开。删除未经核验的自动同义答案，最小事实仍须保留原意与必要限定。图像描述、额外评分要求等修订在 `rubric_overrides.json` 中明确列出，原始模型结果和官方答案独立保留。889-3 的“八个月”限定为赛事准备时间，不能扩展成终身参与该运动的时长。

协议见 [v1.0](protocol-history/v1.0.json) 与 [v1.1](protocol.json)。12 次失败来自定位窗超过格式上限，均保留失败结果后重试；v1.1 将长窗连续切分，保留原范围，仍最多 64 帧，不降低证据完整标准。888-1 额外补充完整原 SRT 以核对四个训练日边界，按[补充政策](source_supplement_policy.json)保存独立包；这部分由 Codex 检查，原观察器/核验器没有看到补充包，记录中明确区分。

## 环境、开销与复现

设备及依赖见 [environment.json](environment.json)。使用既有 WorldMM Python 环境，分支 `work/motivation-data-prep`，基底提交 `3916850f86b1150dd8c4ea7be110d4c2c4f92e8f`；代码运行时尚未提交；本次随暂停归档纳入本地提交，未推送。原始数据只读。源码、提示、源清单、协议哈希及逐版本快照位置见 [reproducibility.json](reproducibility.json)。API 凭据仅从忽略的本地 `tmp/api.json` 读取，不写入记录。

本轮 288 次 API 请求，0 次 API 请求失败；8,258,844 输入 token、261,436 输出 token，共 **8,520,280 token**。技术格式失败与 API 失败分别计数。请求模型 `gpt-5.6-luna`，服务实际返回 `gpt-5.6-luna-2026-07-09` / `gpt-5.6-luna`；逐次用量和响应保留。费用未计算，当前 Codex 会话精确底层部署版本不可获取，以上 token 不含本会话。

复核和重新导出命令（仓库根目录；不新增 API 调用）：

```bash
/home/baorui/projects/WorldMM/.venv/bin/python experiments/EXP-20260917-videomme-evidence60/code/review.py status
/home/baorui/projects/WorldMM/.venv/bin/python experiments/EXP-20260917-videomme-evidence60/code/export.py
```

收集阶段实际顺序为 `collect.py --phase remaining`，对归档的 12 题以 `--phase ids --ids ...` 重试，然后 `--phase replacement --count 48` 和 `--phase replacement --count 28`。精确题号及版本在本机 `batches/` 和 `code_snapshots/`。重放既有批次应使用其题号和 `--phase ids`；再次执行 `--phase replacement` 会抽取新题，不能作为原批次复现。相同请求使用缓存。

`review.py show <题号>` 查看来源；`accept/reject <题号> --inspection frames/subtitles/mixed --note '具体证据说明'` 保存判定。更改已有判定必须显式 `--revise` 并保留原记录。重新导出复现已有判定，不构成新的独立审阅。

## 已执行验证与限制

本机 [validation.json](validation.json) 通过：60 个唯一题号、所有候选已有判定、剩余 48 题有结论、逐事实引用可解析；检查 **2,716 条帧哈希、8,550 条字幕记录**及 **87 份观察器请求头**，字幕文本/时间与原 SRT 归档一致，原抽样清单未变，最终证据包不使用生成 caption 充当证据。帧数是包内记录数，不代表逐张独立人工审核；字幕数也包含不同题间重复使用的源记录。

[交付检查](delivery_checks.json) 通过：五个 JSONL 各 60 行、题号一致，补抽严格对应固定顺序前 76 题，136 题均有最终去留记录；检查证据页 289 个本地链接、相关文档链接和 15 个来源/代码哈希。四个脚本的 `py_compile` 与本机 `git diff --check` 均通过。

独立人工校准、逐帧连续观看、独立音频听写及四步方法实验均 **not run**；本轮交付范围是源证据整理与 AI 复核。完整性校验能检出文件与引用问题，不能替代语义判断。观察器虽不见参考，但证据定位可见参考；先前 8 题沿用既有可见参考审计，不声称新增独立盲审。经过筛选后的题型与难度分布不能用来估计原始 Video-MME 整体成绩。

## 后续时间分组复核（2026-09-17）

已完成[全部60题时间证据组划分](../EXP-20260917-videomme-evidence-groups/README.md)：153个候选组，52题通过进一步AI源支持/删组复核，8题因身份对应、语义、分组粒度或全局范围保留存疑。使用本数据时应同时读取该后续判定，不能无条件将本轮初版60题全部视为充分证据。原数据及当时判定保持不变，修订原因、逐组原证据包与复现方法独立保存。
