# EG-VQA 单卡 15 小时验证

本轮按[原方案 v1.1](../../docs/plan/egvqa_15h_single_gpu_validation_plan.md)完成数据、环境、前端、冻结快照、模型调用与科学协议实现。由于 D0 人工校准未完成，在查看任何 eval 预测前登记为 **12 视频 / 48 QA 的工程 smoke**；原始 18 视频 / 72 QA 清单完整保留。这是因人工门槛缺口采用的保守降级，不是 GPU 吞吐不足，不能记作标准规模科学验收通过。E1/E2 已完成全部注册条件：320/320 与 192/192，核心进程退出码为 0。主表见 [results.md](results.md) 和 [summary.json](summary.json)；逐题分数见 [paired_scores.json](paired_scores.json)，可独立重算主差值与置信区间。

## 本轮结果与判断

E1 有效机械配对 44/48，Full 为 11/44（25%），D=+0.38 pp，95% CI [−10.23,+10.61] pp；自动联合候选为 0。E2 的 R0/R1/R2/R* 为 11/16/10/11 题正确（共同分母 48）；R2−R1=−12.5 pp，95% CI [−22.92,−2.08] pp，2 题改善、8 题退步。R1/R2 在 42 题可行子集上的时间组完整覆盖均为 16/42，R* 虽覆盖 42/42，仍仅答对 9/42。当前未观察到预定联合信号或组合补取优势，也未打开足够的注入参考改善空间；研究判断均为 `INCONCLUSIVE`，先核验视觉可答性与评价质量。

共 816 次物理请求、823 次逻辑调用，1,178,269 个物理 token，预算违规为 0。D0 50、预留 81、E1 356、E2 329 次物理请求全部计入；缓存节约 7 次，逻辑费用仍保留。核心推理约于 03:16+08:00 结束，从 T0 至首次结果汇总为 1.17 小时，GPU 已释放。核心没有模型错误、截断或非法引用；准备阶段 4 次历史截断仍保留。最终 [完整性核验](integrity_checks.json) 通过，10 个源码和 24 个真实快照的 hash 未变化。

人工 D0 校准、E1 语义干预与 E2 grounding 审核仍为待办；E3 为 `NOT_RUN`。单独 AI 文本盲审与本地 judge 一致 26/32，6 处分歧，见 [AI 复核摘要](ai_review_summary.json)。两道固定选择的 Full 错误题另有 [AI 视觉诊断](ai_visual_diagnostics.md)，只定位动作抽帧、细分食材及后续片段干扰的可能问题，不作为人工通过记录。

## 目标与假设

E1 检查完整证据包、逐段关键替换、无关替换及无历史条件的成对差值，区分自然视频的联合证据依赖与一般扰动。E2 在同一个 query-hidden reservoir 快照上比较 R0 top-6、R1 普通二轮、R2 组合补取与 R* 存活证据注入参考。主要比较为 E1 的 D 和 E2 的 R2−R1；负结果也保留。E3 仅在核心科学有效性和审核门槛均通过时考虑，本轮人工门槛未通过，记 `NOT_RUN`。

## 数据、模型与设备

- 数据固定为 `lphuang33/EG-VQA@24379571655174cc80e9c1a1603160e6783c6252`，官方 train 内 seed=17 选 24 视频 / 96 QA；dev 6/24，原定 eval 18/72。全部下载在 `data/downloads/egvqa-pilot`，共 350,188,158 字节，24/24 视频通过本地逐文件 SHA 重验和完整实际 PTS 解码。详见 [数据摘要](data_summary.json) 和[数据说明](../../data/egvqa/README.md)。
- 模型复用 `/root/autodl-tmp/models/Qwen3-VL-8B-Instruct`；本地 checkpoint 无可确认 revision，保存全部权重、tokenizer 和 processor 文件 SHA 清单。检索编码器为 `openai/clip-vit-base-patch32@3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268`，位于 `/root/autodl-tmp/models/clip-vit-base-patch32`。
- GPU 为 RTX PRO 6000 Blackwell Server Edition，97,887 MiB，驱动 595.71.05；PyTorch 2.12.1+cu130、Transformers 4.57.6，BF16 / SDPA / batch=1、greedy、冻结权重。环境位于仓库 `.venv`，复用系统 CUDA PyTorch，附加依赖在仓库环境安装；版本见 [requirements-egvqa-pilot.txt](../../requirements-egvqa-pilot.txt) 和独立 run 的模型 identity。
- 实际 T0：2026-09-07T02:06+08:00，即 2026-09-06T18:06Z。模型任务截止 14:36+08:00，整轮截止 17:06+08:00。实际冻结时间为 02:50:07+08:00，后续未根据 eval 答案选参数。

## 最终冻结配置与 dev 校准

2s/capsule、4 个实际帧、224×224 RGB letterbox；不足 4 个不同 PTS 的尾段显式 mask 填充。seed=17 的在线 reservoir K=64，不读取问题/答案/金标。CLIP 原始帧 projection 在有效帧上取均值后 L2 归一化，全部编码在 CPU 上与单卡 VLM 并行。每个正式快照实际 38,699,319–38,701,883 字节，低于 42,008,576。dev 标注完整组存活 24/24，R0 取齐 7/24；按预定双条件规则保持 K=64。

最终单次上限 8,192 token / 24 图；回答生成上限由 dev 初始 96 校准到 **128**，control=96、judge=256。每张图实际为 grid `[1,14,14]`、49 个视觉 token，24 图共 1,176。E2 每方法每题累计上限 12,288 token，R0/R* 最多 1 次、R1/R2 最多 2 次，缓存命中仍计逻辑费用；核心 1,400、全轮 1,800、核心预留 100 次物理请求硬上限同时执行。

原始 D0 50 次完整保存：32 答案、8 控制、8 judge、2 个最大输入边界。发现并在 eval 前处理了 R1 合法单字符串与数组解析不一致、Blind 幻造引用和较长 group ID 导致输出截断的问题。先用预留 40 次复核共同短答案格式，再用 40 次验证 128 上限与精确 Allowed citation IDs 清单，补 1 次 `8064+128=8192`、24 图边界。准备阶段共 **131 次物理请求**，其中预留用掉 81/100；原始各轮输出与配置均未覆盖。

最终 24 条有图 dev 答案结构与引用合法，8 条 Blind 引用均为空，无截断、OOM 或模型错误。6 条 Blind 的合法 JSON 空答案按明确未回答计 0，保留配对题；这是 eval 前固定的解析/计分规则，不能将其当作缺失结果删除。完整解析复核见 run 的 `dev_final_parser_validation.json`。人工 judge 一致率仍为 `未运行`，不得以格式通过或 AI 文本复核替代。

## 已运行检查与边界

当前设备通过检查脚本执行 `.venv/bin/python -m unittest discover -s tests -v`（为本地 HTTP 测试临时移除代理）：**61 项通过**，覆盖下载、真实 PyAV 前端、reservoir 前缀、干预像素差异、独立组合/覆盖穷举、预算、缓存/失败计费、缺失与重复聚合、弃答、匿名评分和失败路径。`scripts/check_egvqa_pilot.py` 对全部 24 个真实快照验证文件访问拒绝、淘汰 ID 拒绝、像素 hash、查询顺序不变性与实际字节预算；六类机械协议检查通过。GPU 边界及混合推理为真实执行；额外跨题 VLM 重放测试未运行。

本设备没有 mount/unshare 权限，正常 reader 使用单线程 `spawn` 子进程和 Landlock ABI 1 文件白名单，仅能读取当前快照与运行库；原视频、金标和完整候选文件的实际读取均被拒绝。R* 使用独立特权诊断进程。该实现没有网络沙箱，不称完整容器隔离。详细审阅与证据边界见 [protocol_review.md](protocol_review.md)。

E1 全数据可机械构造 dev 20/24、原定 eval 62/72；14 题的无效原因完整保留。不同 PTS、像素 hash、时间组覆盖不证明独立必要事实或实际 grounding。`Stored_ann == Feasible_ann` 是 m≤4、读取≤6 的定义推论，不能把空的“已存但装不下”类别解释成实验发现。所有人工证据审核仍待完成。

## 复现与设备本地产物

独立 run：`experiments/EXP-20260907-egvqa-15h-pilot/run-20260907T0206+0800/`，已被 Git 排除。数据、原始像素、快照、权重、完整日志和缓存留在本设备；Git 仅提交实现、配置、摘要和审核导航。

创建环境与下载（两个下载命令可在独立终端并行运行）：

```bash
bash scripts/setup_egvqa_pilot.sh
export HF_ENDPOINT=https://hf-mirror.com

env -u http_proxy -u https_proxy -u all_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
  .venv/bin/python scripts/download_egvqa.py --output data/downloads/egvqa-pilot

env -u http_proxy -u https_proxy -u all_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
  HF_HUB_DISABLE_XET=1 HF_HOME=/root/autodl-tmp/models/.hf-cache \
  .venv/bin/python scripts/download_egvqa_retrieval_model.py
```

前端和 CLIP 编码可各在独立终端运行；watch 模式对已完成文件断点续作。使用新 run 时替换以下路径，保留原 run 不动：

```bash
.venv/bin/python scripts/prepare_egvqa_pilot.py \
  --output experiments/EXP-20260907-egvqa-15h-pilot/run-20260907T0206+0800/prepared --watch --workers 4

OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 .venv/bin/python scripts/encode_egvqa_snapshots.py \
  --prepared experiments/EXP-20260907-egvqa-15h-pilot/run-20260907T0206+0800/prepared --watch
```

本机冻结 run 的断点恢复与重算命令如下；恢复时源码与模型 identity 必须等于冻结值，已完成请求不会重复执行：

```bash
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 .venv/bin/python scripts/run_egvqa_pilot.py \
  --run experiments/EXP-20260907-egvqa-15h-pilot/run-20260907T0206+0800 --stage core

OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 .venv/bin/python scripts/summarize_egvqa_pilot.py \
  --run experiments/EXP-20260907-egvqa-15h-pilot/run-20260907T0206+0800 \
  --publish-dir experiments/EXP-20260907-egvqa-15h-pilot

.venv/bin/python scripts/build_egvqa_audit.py \
  --run experiments/EXP-20260907-egvqa-15h-pilot/run-20260907T0206+0800
```

人工审核入口为 [32 条匿名 dev 答案](manual_judge_audit.md)、[E1 四题诊断材料](run-20260907T0206+0800/audit_pages/e1.html)及 [E2 两题增益盲审材料](run-20260907T0206+0800/audit_pages/e2_blind.html)。E1 没有自动联合候选，页面四题只是固定诊断样本。审计页保留实际 ID、PTS、引用、解析状态和填充 mask；重复导出须用 `--output` 指定新目录，避免覆盖意见。实际人工意见须另存带显式 `kind`、`reviewer_type`、审核者和时间的记录，不能把 AI 观察计作人工审核。

`profile_egvqa_model.py`、`run_egvqa_dev.py` 和 `recheck_egvqa_dev.py` 保存了 profiling/复核的流程，但旧配置的精确重放应使用 run 中按 hash 保存的历史模型 identity 与 prompt；当前代码以最终冻结配置为准，不能把重新执行当前脚本称作重放旧 96-token 配置。重新开始正式独立实验必须创建新 run、重新登记时间/数据/配置并完成 D0，不覆盖本轮。

准备阶段的下载索引空成员问题、E1 v1 干扰枚举缺陷、初始代理导致的本地 HTTP 测试失败和一次 reader 升级引发的 D0 CPU 中断均已有记录。E1 v1 包保存在 `prepared/*/e1-frontend-v1`；D0 在已落盘请求边界恢复，未额外重复物理请求。
