# Video-MME-long：动机验证数据准备

开始日期：2026-09-16。当前状态：首批处理完成；60 题草稿及 12 题两轮自动核验已保存，等待人工校准。结论及限制见 [analysis.md](analysis.md)。

后续更正：已完成独立记录的 [AI 标注复核](../EXP-20260916-videomme-annotation-audit/README.md)，发现检索漏段、画面文字漏读及空泛评分事实；修订草稿与逐题裁定另存。下文原始运行结果保持历史记录性质，不再直接用作可冻结标签。

本轮仅处理 Video-MME-long，按用户最新要求不处理 EgoLife。依据[整体规划](../../docs/plan/content_linked_memory_completeness_validation_2026-09-16.md)，执行“分段索引 → 按题定位 → 原帧核验 → 独立复核”，准备简答题、评分事实、任务标签和证据记录；不运行存取方法比较或训练。

## 数据与运行范围

- 原始数据：`/mnt/raid5-01/baorui/Video-MME`，只读。官方 long 子集 300 视频、900 QA。
- Caption：[WorldMM 的 10 秒文件](https://github.com/wgcyeo/WorldMM/blob/3a55b65235e4f9618626a91c28e7e45baa6d8bdf/data/Video-MME/caption.zip)。本地克隆原文件为 Git LFS 指针，实际载荷单独下载到产物目录，未改基线仓库。SHA256：`ada66bdab7af40c0975f5bfdd40040380384ee17d82dd1afc284c26f1947b348`。
- 300 个 caption 视频 ID 与官方 long 清单完全一致，共 74,136 条。所有源视频存在，300 个视频元数据探测通过；caption 从 0 开始、无区间断点，末端与视频时长差在向上取整容差内。此检查不等于逐帧完整解码或描述语义准确。
- 开发集：seed `20260916`，按视频 ID 的固定 SHA256 顺序选择 20 个视频，保留每视频全部 3 题，共 60 题。余下 280 视频 / 840 题为未冻结候选池。
- 视觉核验先导：在任何模型输出前，从开发题固定 hash 顺序选择 12 题，每视频最多一题。选择与答题是否成功无关；所有不适配、未确定和失败记录保留。
- 自然抽样与富集测试集尚未冻结：应先完成开发校准。开发视频涉及 4 个领域，未覆盖全部领域，不能将先导统计当作基准总体分布。

## 标注协议与边界

初始配置见 [protocol.json](protocol.json)，经开发诊断修订的配置见 [protocol_refined.json](protocol_refined.json)，提示见 [code/prompts](code/prompts)。以下第 2–4 点描述首轮；第二轮调整另列。

1. 简答改写、必要答案事实及任务标签由配置中的模型生成草稿。多步问题保留任务本身的步骤列表；无法脱离选项明确作答的否定题标记待审/不适配，不臆造替代题。
2. 用题目及检索词在对应视频 caption 中做 BM25 检索，取 12 条候选。提名模型可见未核验参考，最多提名 4 条，再按固定规则加入邻段，总计不超过 6 条。这是评测标注的特权定位，不是正式方法的读取器。
3. 每个 10 秒候选约每秒取一帧，最多 10 帧，长边最多 768 像素；保留实际解码 PTS、JPEG 校验和与原视频路径。原字幕/音频没有传入此阶段，故静态帧不能确认听觉事实或保证瞬时动作可见。
4. 新上下文中的独立视觉核验只接收简答问题、片段时间和实际图片，不接收选项、参考、caption、评分事实或提名理由。随后另一次调用比较参考草稿与观察事实。
5. 同一模型在独立上下文中担任提名、核验和比对，可能存在共同偏差。所有结果明确标为自动代理；人工审核未完成前，不称为金标或科学验证通过。
6. 需要全历史覆盖、音频或缺失动作的题保持未确定/明确缺口。少量检索片段无法证明首次、最后一次、否定、准确总数或全视频概括。因改写问题而暂停的题不从原分母删除。

第二轮保持原 12 题不变：按步骤、评分事实及参考草稿分别检索，最多 24 条 caption 候选；加入对应片段的原始字幕；模型逐项区分视觉和字幕支持。未核验参考只用于评测侧定位，不传入独立核验。两轮均不等同于正式基线，且检索额度/模态不同，不能作方法增益比较。首轮 60 题草稿以带哈希的来源记录继承，不重新生成或覆盖。

## 代码、环境和重现

- 当前代码位于分支 `work/motivation-data-prep`，运行时尚未提交；本次随暂停归档纳入本地提交，未推送。每次标注运行保存实际代码快照、配置和提示 SHA256；源仓库基线及本机环境见 `provenance.json`。
- Python：`/home/baorui/projects/WorldMM/.venv/bin/python`（3.13.12），使用已安装的 PyArrow、PyAV、Pillow、OpenAI SDK 和 HTTPX；未改动基线依赖。
- API 凭据从用户提供的 `tmp/api.json` 读取，不复制到产物、日志或版本库。仓库根 `tmp/` 已忽略。模型请求使用配置别名，响应中的实际模型版本逐次记录。
- API URL 若没有路径则补 `/v1`；显式使用环境中的 HTTPS HTTP 代理，避免 HTTPX 自动读取 SOCKS 代理导致缺依赖。未修改系统代理和现有模型环境。

在仓库根执行；输出目录必须与相应配置/代码版本匹配，新实现使用新运行目录：

```bash
/home/baorui/projects/WorldMM/.venv/bin/python experiments/EXP-20260916-memory-data-prep/code/prepare.py --config experiments/EXP-20260916-memory-data-prep/protocol.json --output /mnt/raid5-01/baorui/visual-memory/EXP-20260916-memory-data-prep/run-001-inventory

/home/baorui/projects/WorldMM/.venv/bin/python /mnt/raid5-01/baorui/visual-memory/EXP-20260916-memory-data-prep/run-003-dev-annotation/code_snapshot/annotate.py --config experiments/EXP-20260916-memory-data-prep/protocol.json --inventory /mnt/raid5-01/baorui/visual-memory/EXP-20260916-memory-data-prep/run-001-inventory --output /mnt/raid5-01/baorui/visual-memory/EXP-20260916-memory-data-prep/run-003-dev-annotation --stage draft

/home/baorui/projects/WorldMM/.venv/bin/python /mnt/raid5-01/baorui/visual-memory/EXP-20260916-memory-data-prep/run-003-dev-annotation/code_snapshot/annotate.py --config experiments/EXP-20260916-memory-data-prep/protocol.json --inventory /mnt/raid5-01/baorui/visual-memory/EXP-20260916-memory-data-prep/run-001-inventory --output /mnt/raid5-01/baorui/visual-memory/EXP-20260916-memory-data-prep/run-003-dev-annotation --stage visual

/home/baorui/projects/WorldMM/.venv/bin/python experiments/EXP-20260916-memory-data-prep/code/annotate.py --config experiments/EXP-20260916-memory-data-prep/protocol_refined.json --inventory /mnt/raid5-01/baorui/visual-memory/EXP-20260916-memory-data-prep/run-001-inventory --output /mnt/raid5-01/baorui/visual-memory/EXP-20260916-memory-data-prep/run-004-source-refinement --stage visual
```

清单脚本拒绝覆盖已有运行目录。标注脚本对同配置、同提示、同代码、同请求复用缓存；失败调用及重试各自保留，不重写旧响应。重现已完成清单应使用新输出目录。

## 产物与记录

本机根目录：`/mnt/raid5-01/baorui/visual-memory/EXP-20260916-memory-data-prep/`。

| 位置 | 内容 |
|---|---|
| `resources/` | 固定版本的 WorldMM caption 压缩包 |
| `run-001-inventory/` | 900 QA、74,136 caption、300 视频清单，开发/先导抽样，源校验和及视频元数据 |
| `run-002-annotation/` | 两题 API/标注流程 smoke；其原提示、代码及结果保留 |
| `run-003-dev-annotation/` | 60 题开发标注及首轮 12 题先导；两题不适配，10 题有实际源帧核验 |
| `run-004-source-refinement/` | 同一批 12 题的分步骤检索及字幕复核；作为当前自动代理结果，继承首轮草稿 |
| `review-001/` | 当前 60 题审核队列（JSONL、CSV）和带源帧/原始字幕/原视频链接的 `index.html` |

标注目录中的 `calls/` 保存匿名阶段请求、原始响应、实际模型版本、token 用量及失败记录；图片请求用图像 SHA256 代替 base64 日志，实际帧另存。`human_review.html` 和 `human_review_queue.json` 供人工审核；`summary.json` 汇总自动代理标签，不是实验准确率。

已执行的检查见 [首轮检查](run-003-dev-annotation_integrity_checks.json) 和 [第二轮检查](run-004-source-refinement_integrity_checks.json)。数据/实际输入完整性通过，模型引用时间仍有警告。API 账本见 [execution_summary.json](execution_summary.json)；逐题状态见 [pilot_case_summary.json](pilot_case_summary.json)。

下一步：人工审核简答适配、评分事实和源证据，校准独立核验与后续比对的分歧；解决缺失字幕和必要动作采样问题后，再冻结正式测试样本及评分规则。尚未运行四步存取实验。

2026-09-17 后续更新：[60 题完整证据复核](../EXP-20260917-videomme-evidence60/README.md)已完成，包含原剩余 48 题及 76 道补抽题的明确去留记录。最终保留 60 题；本页历史结果不变，仍未进行独立人工校准或四步方法实验。
