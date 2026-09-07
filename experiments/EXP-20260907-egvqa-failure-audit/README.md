# EG-VQA 失败原因与独立 AI 重答诊断

本轮完成原 48 题全部记录的评分/表示诊断，以及四题全部 E1/E2 设置的独立 AI 重答：44 个条件、42 个不同输入。**E1 未检出联合信号；E2 原负差值混入了已证实的评分不一致，显著性结论不稳健。** 原实验计数和冻结文件保留。原因分析见 [analysis.md](analysis.md)，逐设置回答见 [reanswers.md](reanswers.md)。

## 目标、数据与模型

解释 [原工程 smoke](../EXP-20260907-egvqa-15h-pilot/README.md) 中 E1 零联合候选、E2 R2−R1 为负的可能原因。事后检验评分一致性、抽帧表示、标注覆盖代理和 R2 集合目标；不以正结果为目标，不启动 E3。

- 数据：`lphuang33/EG-VQA@24379571655174cc80e9c1a1603160e6783c6252`，官方 train 内固定子集；当前分母 12 视频 / 48 QA。文件在 `data/downloads/egvqa-pilot/`，本轮不新增下载。
- 原 VLM：`/root/autodl-tmp/models/Qwen3-VL-8B-Instruct`，本地权重沿用原 SHA 清单；BF16/SDPA/greedy。原 run：`experiments/EXP-20260907-egvqa-15h-pilot/run-20260907T0206+0800`；基线 Git：`8aa327ccdde8828fd1f90bb67796f8841b0e9a28`。
- 检索诊断：CPU 使用原 `openai/clip-vit-base-patch32@3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268`。环境沿用仓库 `.venv`，PyTorch 2.12.1+cu130、Transformers 4.57.6，没有修改依赖或加载 Qwen。
- 新作答：Codex 工具创建的新 AI 上下文，每包 `fork_turns="none"`，不请求模型/推理档位 override。平台未提供可核验的 checkpoint revision、解码 seed、实际推理 token 或可重放请求 ID。任务名、文件落盘时间和 SHA 见 [provenance.json](provenance.json)，不能代替实际请求身份/时间。

## 配置与范围

本地 run 为 `run-20260907T0909+0800/`，2026-09-07 09:09（UTC+08）开始。开始保存五个原记录/配置和十个源码 SHA，结束重验。原 816 次物理 VLM 请求不变；本轮新增本地 Qwen 请求为 0。另有 42 次视觉/无图 AI 作答、2 次 AI 文本审核，以及分析/代码核查代理；与原模型计费分开，不声称等成本。

全量诊断覆盖 512 个终态条件，483 完成、29 构造失败。评分敏感性沿用 video-cluster paired bootstrap，2,000 次、seed=43；穷举六个冲突组的 64 种统一赋值。检索对照固定原查询/候选/快照，仅比较 α=0.2 与 α=0，不生成新集合答案。

新视觉答案出现前，按原结果分四层，各层在 E1 机械有效且未重复的题中按 seed=43 SHA 顺序取首题；见 [selection_manifest.json](selection_manifest.json)。

| 层 | 题目 | 全部最终设置数 |
|---|---|---:|
| 同文不同分的 R2 退步 | `v_0zjA3KPnLK8_q02`，相扑主要活动 | 10 |
| 其余 R2 退步 | `l2OTMq4aluc_q06`，布料动作 | 12 |
| R2 原判增益 | `v_NGk3v4sKqdg_q04`，自行车活动 | 11 |
| E1 Full 错误 | `PtbGXfb6B1I_q01`，点火前准备 | 11 |

每包一个新上下文，最多三个并发；只见问题/帧/ID/PTS，不见条件名、参考、旧答案或其他设置。相同输入共用答案。逐帧核对原 RGB SHA、顺序、ID、PTS，以原尺寸 224×224 拼图展示。回答至多 30 英文词、六个合法 ID，见 [reanswer_protocol.md](reanswer_protocol.md)。这是执行声明与文件校验，不声称操作系统强制盲法。

新旧答案去重为 61 个非空文本项，以 seed=43/44 的不同顺序给两个新 AI 上下文，隐藏来源，沿用原 rubric；见 [text_review_protocol.md](text_review_protocol.md)。空答案按原规则记零，复核者独立判定、不协商。

## 结果

- 57 个同题同文重复组中，6 组/21 行原判冲突。仅要求相扑 R1/R2 同答同分，原 −12.5 pp 变为敏感性 −10.42 pp，95% CI [−22.92,+2.08] pp。统一全部冲突的各情景仍为负点估计，评分缺陷不是全部原因。
- E1 Full 11/44 正确，22/44 题所有有图条件均错；115 个金标组每组四帧、中位跨度 33 秒。时间段不等于不同必要事实，语义干预未完成人工核验。
- R* 时间覆盖未保证动作可见；所覆盖组首帧相对位置中位数 1.55%。R2 双查询 CLIP 相似度中位数 0.944，22/48 题一个条目贡献所有查询最大匹配。仅检索 α=0 对照把完整时间覆盖 16/48 改为 19/48，**没有对应 QA 改善结论**。
- 42 个独立回答全部完成，两名 AI 对 61 项文本的判定一致 61/61。新答相扑 9/10、布料 1/12、自行车 0/11、火坑 0/11 条件正确（均含 Blind）；四题事后选例不能估计总体性能。具体动作变化见 [analysis.md](analysis.md)，已知参考后的画面核查见 [case_observations.md](case_observations.md)。

结论：先修评分一致性和人工语义校准，核验 Full 可答性与动作表示，再在独立 dev 注册 R2 消融。当前既不能否定组合记忆原理，也没有证据称本实现有效。

机器摘要见 [scoring_summary.json](scoring_summary.json)、[representation_summary.json](representation_summary.json)、[reanswer_summary.json](reanswer_summary.json)。全部短答案、参考、原判与新复核理由见 [reanswers.json](reanswers.json)；全部评分冲突和 8 loss / 2 gain 文本见 [scoring_diagnostics.md](scoring_diagnostics.md)。

## 复现

在仓库根目录运行。下方 AUDIT_RUN 是本次路径；复现导出时须改为**新建**的输出 run，并先创建该目录，避免覆盖记录。prepare 导出与 prepare-judge 拒绝覆盖已有输入。

```bash
SOURCE_RUN=experiments/EXP-20260907-egvqa-15h-pilot/run-20260907T0206+0800
AUDIT_RUN=experiments/EXP-20260907-egvqa-failure-audit/run-20260907T0909+0800
.venv/bin/python scripts/analyze_egvqa_scoring.py --run "$SOURCE_RUN" --output "$AUDIT_RUN"
OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 .venv/bin/python scripts/analyze_egvqa_representation.py --source-run "$SOURCE_RUN" --output "$AUDIT_RUN"
.venv/bin/python scripts/prepare_egvqa_reanswer.py --source-run "$SOURCE_RUN" --output "$AUDIT_RUN"
```

按 packet_manifest 排序，为每包单独启动遵守 reanswer_protocol 的新 AI 上下文。全部 responses 保存后运行：

```bash
.venv/bin/python scripts/summarize_egvqa_reanswers.py --run "$AUDIT_RUN" --stage prepare-judge
```

按 text_review_protocol 以两个新上下文生成 text_review_A.json / text_review_B.json，再运行：

```bash
.venv/bin/python scripts/summarize_egvqa_reanswers.py --run "$AUDIT_RUN" --stage report
```

可重现选样、像素、检索、计分聚合与校验；AI 回答依赖平台模型，不保证逐字重放。完整图片、输入输出、敏感性方案和日志留本设备的 ignored run，Git 只保存脚本、短答案、摘要和协议。

## 验证与限制

当前设备实际执行四个新脚本的相关阶段、四脚本 py_compile、输入/输出与 SHA 核验、原冻结文件 SHA 重验及 git diff --check。独立代码复核验证了 42 包共 824 张帧的像素/标签与原请求一致；评分脚本复用冻结 `_score` / `aggregate_e1`，并断言与原逐题结果相符。见 [integrity_checks.json](integrity_checks.json)。

未重跑原 61 项测试或原 Qwen 推理；本轮未修改科学源码或环境。人工校准、人工 grounding、同模型换表示/换 α 的回答对照、E3 均为 `未运行`。AI 审核者可能共享偏差，一致不等于人工真值。新作答模型、呈现和预算不同于原实验，四题依旧结果事后选择，不能声称总体提升、因果贡献比例或人工上限。
