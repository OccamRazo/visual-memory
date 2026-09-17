# Video-MME 标注复核

开始日期：2026-09-16。状态：本轮 AI 复核完成；未完成人工校准，未冻结测试集。

按用户“帮我验证”的要求，检查[数据准备实验](../EXP-20260916-memory-data-prep/README.md)的 60 题改写与评分事实，并对原先固定的 12 题进行源证据或适配复核。遵循[整体规划](../../docs/plan/content_linked_memory_completeness_validation_2026-09-16.md)中答案评分与证据充分性分开的要求。只处理 Video-MME，不运行方法实验。

## 结果

- 60 份草稿全部完成文本检查，32 份有实质字段修订，其中 13 份原评分事实过于空泛或缺少具体答案。修订后的事实仍区分“从官方答案整理”和“经源内容支持”，不能全部当成金标。
- 12 题中：8 题找到支持参考答案的源证据；2 题保留题意或参考表述问题；2 题不适合当前无选项简答。它们不是同预算下的模型成绩，也不是对旧核验器的错误率估计。
- 修订后适配状态：46 题未发现明确文本适配障碍，9 题待核，5 题不适配。46 题不表示源事实全部通过；仅 12 题进入本轮源证据/适配先导。
- 检视旧包抽出的 240 张图片及新增 87 张图片，辅以定位后的原始字幕。600 张旧帧、87 张新增帧及 72 份来源标注文件的完整性检查通过。没有连续观看完整视频，没有独立听写字幕。
- 本轮未新增 API 调用、未读取凭据。复核由当前 Codex 会话完成，可见官方参考及旧判断，**不属于盲审或人工审核**。

逐题结论与局限见 [analysis.md](analysis.md)，机器可读记录见 [summary.json](summary.json)、[pilot_audit.json](pilot_audit.json)、[draft_review.jsonl](draft_review.jsonl) 和 [rubric_changes.json](rubric_changes.json)。检查结果见 [integrity_checks.json](integrity_checks.json)。

## 本机产物

根目录：`/mnt/raid5-01/baorui/visual-memory/EXP-20260916-videomme-annotation-audit/`。

| 路径 | 内容 |
| --- | --- |
| `index.html` | 60 题复核页面，附旧版、修订版、关键帧及字幕链接 |
| `revised_drafts/` | 60 份 `audit-v2-draft`；保存原题、官方参考、AI 审核状态；全部未冻结 |
| `draft_input.json` | 60 题原始输入快照 |
| `inspection_manifest.json` | 旧标注哈希与 10 张拼图的原帧映射 |
| `subtitles/` | 开发视频的原 SRT 转换结果、字幕 ID、时间及成员哈希；缺失明确记录 |
| `evidence_subtitles/` | 逐先导题的证据字幕摘录 |
| `sheets/` | 旧包每片段取第 0、3、6、9 帧的检查拼图 |
| `expanded/`、`expanded_manifest.json` | 定向补充与三个主题/形式题均匀概览；原视频路径、实际 PTS、图片哈希 |

原始视频、前两轮模型响应、旧草稿和旧审核包均保留。本目录是独立复核，不覆盖旧实验标签。

## 协议与复现

这是事后诊断。12 题沿用原先预定清单，补充时间段根据分歧和源内容定位；不声称补充片段选择是盲选。三个主题/形式题另按时长均匀抽 12 帧。Caption 仅帮助定位，结论依据实际帧和原始字幕。题干中的顺序事件按身份匹配，必要答案事实按先后关系拆分；主题覆盖与全量计数、否定证明分开记录。

代码与完整环境哈希见 [provenance.json](provenance.json)。当前分支 `work/motivation-data-prep`，基底提交 `3916850f86b1150dd8c4ea7be110d4c2c4f92e8f`，审计代码运行时尚未提交，本次随暂停归档纳入本地提交。使用既有 WorldMM 虚拟环境的 PyAV、Pillow、pysrt，无新增依赖。底层模型精确部署版本不可获取，复核身份记为当前 Codex 会话。

在仓库根按顺序运行：

```bash
/home/baorui/projects/WorldMM/.venv/bin/python experiments/EXP-20260916-videomme-annotation-audit/code/prepare_audit.py
/home/baorui/projects/WorldMM/.venv/bin/python experiments/EXP-20260916-videomme-annotation-audit/code/expand_evidence.py
/home/baorui/projects/WorldMM/.venv/bin/python experiments/EXP-20260916-videomme-annotation-audit/code/adjudicate.py
/home/baorui/projects/WorldMM/.venv/bin/python experiments/EXP-20260916-videomme-annotation-audit/code/validate_and_package.py
```

`adjudicate.py` 将本会话的明确审核决定物化为记录；重跑只复现这些决定，**不会产生第二名独立审核者**。默认路径对应本机，修改协议或决定应新建运行记录。

后续：解决 9 题的评分/题意歧义，并核验其余开发题的源事实；对修订标准做独立校准后再冻结。缺字幕本身不自动排除视觉可回答题，戒指题已给出实例。四步存取实验仍未运行。

2026-09-17 后续更新：[60 题完整证据复核](../EXP-20260917-videomme-evidence60/README.md)已完成，包含原剩余 48 题及 76 道补抽题的明确去留记录。最终保留 60 题；本页历史结果不变，仍未进行独立人工校准或四步方法实验。
