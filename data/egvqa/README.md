# EG-VQA 小规模验证子集

为 15 小时初步验证准备数据：默认 **24 个完整视频、96 道 QA**，额外弱监督训练数据按需启用。下载器只需要 CPU、网络和 Python，不需要 GPU、模型权重或 EG-Reasoner 的训练环境。

脚本入口：[`scripts/download_egvqa.py`](../../scripts/download_egvqa.py)；复用逻辑：[`src/egvqa_subset.py`](../../src/egvqa_subset.py)。

## 直接使用

在本分支的仓库根目录执行，建议 Python 3.10 或以上：

```bash
python -m pip install -r data/egvqa/requirements.txt
python scripts/download_egvqa.py --output data/downloads/egvqa-pilot
```

将 `--output` 改为服务器上的数据目录即可。默认目录已被仓库 `.gitignore` 排除；视频、完整标注缓存、扫描索引和下载日志均不提交 Git。

只准备标注和选样清单，暂不读取视频包：

```bash
python scripts/download_egvqa.py \
  --prepare-only --output data/downloads/egvqa-pilot
```

查看清单后，下载或续传同一子集：

```bash
python scripts/download_egvqa.py \
  --download-only --output data/downloads/egvqa-pilot
```

默认流程先获取所需 split 的小 JSON，随后定位并下载视频。**首次定位可能需要数十分钟**：远端包没有目录索引，需要按 tar 头逐项跳读，最坏约两千次小请求；读取的头总量约 1 MiB，主要成本是网络往返。索引会保存进度，重跑不会从头扫描，也不会重下已完成且校验通过的视频。

## 默认子集

| 项目 | 默认值与用途 |
|---|---|
| 官方来源划分 | `train`，默认仅下载其 7,390,047 字节标注，保留官方 `test` |
| 内部 `dev` | 6 个视频、24 道 QA，用于提示与阈值调试 |
| 内部 `eval` | 18 个视频、72 道 QA，用于冻结配置后的初步验证 |
| 视频时长 | 60–600 秒；默认选中视频合计约 111.34 分钟 |
| 问题筛选 | `temporal`、`descriptive`；每题 2–4 段有效时间证据；每视频 4 题 |
| 来源覆盖 | 对 ActivityNet Captions、HiREST、YouCook2 做轮转抽样；来源候选不足时由其他来源补足 |
| 随机性 | 固定 `seed=17`，按种子与 ID 的 SHA-256 排序，不依赖原始 JSON 顺序 |
| 额外训练集 | 默认 0；可选 40 个视频、200 道 QA，与 dev/eval 按视频隔离 |

默认 pilot 从 65 个合格视频中选取，包含 4 个 YouCook2、11 个 HiREST、9 个 ActivityNet Captions 视频。候选池限制了来源占比。每题含多段标注只说明适合做证据干预检查，**不说明这些段已被证明联合必要**。此子集有显式选择偏差，不用于报告官方整体 benchmark 分数。

默认排除因果和反事实题，是为减少初步机制验证对常识推测的依赖。可通过 `--question-types temporal descriptive causal counterfactual` 扩展。`--min-gap-seconds` 可要求合并证据区间后存在指定长度的无覆盖间隙；筛选过严导致样本不足时会报错，不会悄悄缩小样本。

## 扩展弱监督训练

独立输出目录可保持已冻结的 pilot 版本：

```bash
python scripts/download_egvqa.py \
  --train-videos 40 \
  --annotations-dir data/downloads/egvqa-pilot/cache \
  --index-file data/downloads/egvqa-pilot/cache/videos.index.json \
  --output data/downloads/egvqa-pilot-weak
```

这个配置总计 **64 个视频、296 道 QA**，其中原 pilot 24 个视频的选择保持不变。新输出目录可复用已有索引继续定位；如果还没有索引，去掉 `--index-file`。

额外训练视频只按时长、来源和 QA 数筛选，不使用金标证据数量、时间戳或描述选取训练样本。导出的 `annotations/train.json` 和 manifest 中的训练记录只保留 QA 及基础视频字段，不含 `evidence`、`metadata`。这属于使用既有 QA 的弱监督设置。原始标注缓存依然包含官方金标，训练代码应读取导出的训练文件。

需要更小规模时，例如：

```bash
python scripts/download_egvqa.py \
  --num-videos 8 --dev-videos 2 \
  --output data/downloads/egvqa-small
```

如明确要用官方测试集，设置 `--split test --dev-videos 0` 并使用新输出目录。已有目录若选样配置不同会报错，避免重跑时覆盖样本定义。`--download-only` 始终使用该目录已冻结的 manifest。

## 文件与实验入口

```text
<output>/
  manifest.json                 # 版本、配置、所选视频及问题；包含评估金标
  annotations/
    dev.json                    # 原官方格式的所选 QA、证据与源标注
    eval.json
    train.json                  # 额外训练的 QA-only 记录，未启用时为空
  inputs/
    <role>_ingest.jsonl          # 只有 video_id、video_path、duration
    <role>_questions.jsonl       # 问题及类型，无答案/证据
  videos/<original_filename>    # 所选视频；保留官方包内的文件名与字节
  download_status.json          # 成功/失败、文件大小、SHA-256、缺失视频清单
  ready/
    annotations/<role>.json     # 仅包含当前已经完成校验的视频对应 QA
    inputs/<role>_ingest.jsonl
    inputs/<role>_questions.jsonl
  cache/
    train.json                  # 仅缓存需要的官方 split；按需增加 test.json
    videos.index.json           # tar 成员的偏移/长度与续扫位置，无视频正文
    receipts/                   # 部分文件来源与已完成文件的校验收据
```

`<role>` 是 `dev`、`eval` 或 `train`。所有 `video_path` 均相对于 `<output>`，包括 `ready/` 下文件里的路径。

用于 query-hidden 实验时，writer 只读取 `ready/inputs/<role>_ingest.jsonl` 和视频；封存记忆后，reader 再读取对应的 questions 文件。答案、`evidence.description`、`metadata.segments` 和金标时间戳仅供监督或评估。下载完整时间轴，不根据金标只截取证据片段；帧提取与固定记忆预算留给实验代码。

遇到下载失败会继续处理其余所选视频，退出码为 `1`，并明确列出缺失项。实验必须同时报告计划样本数与实际可用样本数；不能把 `ready/` 的成功子集视为完整目标样本。全部完成返回 `0`，用户中断返回 `130`。失败不会自动换样；更换选样配置应另建输出目录。

## 数据来源与部分下载机制

核查日期：2026-09-07。GitHub 的 [EG-VQA 获取说明](https://github.com/HCPLab-SYSU/EG-VQA#data-acquisition) 仍要求自行取得源视频；作者的 [Hugging Face 数据仓库](https://huggingface.co/datasets/lphuang33/EG-VQA/tree/main) 已提供 `videos.tar`。本脚本直接使用后者，并固定到以下版本：

- Dataset：`lphuang33/EG-VQA`。
- Revision：`24379571655174cc80e9c1a1603160e6783c6252`。
- 未压缩 `videos.tar`：13,090,641,920 字节，约 12.19 GiB。
- Hub 公布的 tar SHA-256：`1e45a98396ef0b5f9e94b0db2b46205528c620be1b073d19cf064f4d7fecd9dc`。
- train JSON SHA-256：`f4992b0d3e239dd3e809b2feecb7bef41f1507153a358c40e9e271ae010622e6`。
- test JSON SHA-256：`673560f4a3076321f9da8a2b57422fd04cf3645e0bd5aa0a6d8b92427a740f8b`。

获取标注需要读取整个小 JSON 以完成可复现选样；不会下载未选择的视频正文，也不下载全量帧、特征、模型权重或训练代码。HTTP Range 用于读取 512 字节 tar 头；根据文件大小跳到下一个头。定位所选文件后，每次最多请求 4 MiB 的该文件字节，写入 `.part`，完成后再发布正式文件。

服务器必须返回 `206` 和准确的 `Content-Range`，包括总包大小。返回 `200`、错误区间或不符长度时会停止读取该响应，**没有整包下载回退**。元数据按固定 SHA-256 校验；提取前复核所选成员的 tar 头、路径和长度，提取后记录视频 SHA-256，重跑时据此校验本地文件。整个 tar 的 SHA-256 仅用于固定来源身份，未通过全量读取重新计算；没有声称拥有上游逐视频校验和。

索引器支持当前已观察到的普通文件和目录头，遇到链接、扩展头、压缩 tar 或非法路径会报错，不猜测位置。公共下载无需账号；网络代理沿用 `requests` 的标准环境变量。若代理忽略 Range，会明确失败。

作者数据卡将标注许可标为 CC BY 4.0；视频来自三个源数据集，使用和再分发仍应核对相应源视频条件。该下载器不会重编码视频，也不保证官方打包视频具有原始上传画质。真实抽查的一个文件为 **398×224、约 3 fps**；后续细粒度证据实验需要检查可见细节与采样时间精度。

## 本次验证

在 macOS、本地临时环境 Python 3.12.14 / requests 2.32.5 上运行：

```bash
python -m unittest discover -s tests -v
python -m py_compile src/egvqa_subset.py scripts/download_egvqa.py
git diff --check
```

14 项自动化测试全部通过，覆盖部分 HTTP 响应、拒绝整包响应、视频与索引续传、损坏文件、选样复现、划分隔离和失败样本导出。另已实际下载并校验官方 train JSON，生成默认 24 视频/96 QA 与扩展 64 视频/296 QA 清单。真实视频抽查：`v_tGHLUWWm_zU.mp4`，2,498,604 字节，SHA-256 `f6867c4c408ef42adfe21ae3e99e2dfa00a0026573a95a44a95448db06f7392b`；重复调用复用文件，不重传视频正文。用独立临时安装的 PyAV 18.1.0 解码首尾帧成功，包内媒体时长 188.0 秒，标注时长 187.55 秒。PyAV 仅用于本次解码检查，不是下载依赖。

CLI 端到端下载检查使用以下单视频配置（单独选择种子以复用该视频做下载检查，不改变正式 pilot 的 seed=17）：

```bash
python scripts/download_egvqa.py \
  --num-videos 1 --dev-videos 0 --sources 'ActivityNet Captions' --seed 50 \
  --output data/downloads/egvqa-smoke
python scripts/download_egvqa.py --download-only --output data/downloads/egvqa-smoke
```

两次均返回 `0`，第二次状态记录的新增范围正文传输量为 `0` 字节。本次实际运行还通过 `--annotations-dir` 和 `--index-file` 复用了本机已校验缓存；没有这些缓存时，上述命令会先获取标注并扫描索引。

本次只抽查下载一个视频，未下载全部 24/64 个视频，未运行 VLM、GPU 实验或全量视频可用率评估。部分索引扫描用于核实真实 tar 格式，不代表所有成员均已验证。完整缓存和视频位于当前设备的 `/tmp/egvqa-subset-audit/`，仅供本次验证，后续实验应在目标设备按以上命令重新建立持久数据目录。
