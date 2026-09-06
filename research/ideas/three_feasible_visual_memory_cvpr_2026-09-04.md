# 视觉记忆 × 超长视频：面向 CVPR 2027 的三个资源可行方案

> 日期：2026-09-04
>
> 目标：在最多 `2 × 80GB` GPU、没有大规模预训练资源的条件下，从既有调研和形式化讨论中收敛出三个可以立即做现象验证、且有机会形成 CVPR 论文的方向。
>
> 证据截止：2026-09-04；文献中的数值均为作者报告，尚未在本项目中独立复现。
>
> 当前状态：仓库已有完整调研、形式化报告和方案一的英文论文草稿，但**尚无实验结果**。本文是新的决策文档，不覆盖旧方案。

## 0. 执行结论

### 0.1 三个方案与优先级

| 优先级 | 方案 | 论文核心问题 | 训练主体 | 预计总 GPU 时* | 最大风险 | 当前建议 |
|---:|---|---|---|---:|---|---|
| 1 | **完整证据路径记忆（CPM）** | 未知未来问题下，怎样保住至少一条完整的最小充分证据路径？ | 轻量 set critic / allocator | 100–250 | 真实数据的 bundle 标注不完整 | **主线；立即做** |
| 2 | **记忆完整性诊断（MID）** | 压缩后，系统能否判断自己是没存、没取到，还是取到但不会用？ | 小型诊断器或 7B LoRA | 60–160 | 容易退化为普通置信度/拒答 | **首选备线** |
| 3 | **延迟可知性记忆（DKM）** | 后续观察使早期事件变重要时，因果 writer 能否及时回溯提权？ | 小型关系/影响 critic | 80–200 | 真实 delayed-knowability 效应可能太小 | **先诊断，后立项** |

\* GPU 时是基于冻结 7–8B VLM、缓存视觉特征、只训练轻量模块的工程估计，不是实测结果；应在首个 100 样本 pilot 后重估。若改为端到端训练 VideoLLM、在线 RL 或 27B 以上 teacher，表中预算不再成立。

综合判断：

1. **若只能押一个方向，选择方案一。** 它有最直接的文献 headroom、最清楚的形式对象和最多的仓库复用；已有论文草稿可直接转入实验。
2. **方案二是时间最紧时最稳的替代。** 它不要求训练新 writer，数据可由压缩与受控干预自动生成，单卡即可完成；但必须做“阶段归因 + 缺失 witness + false-safe 风险控制”，普通 abstention 已不新。
3. **方案三的科学上限很高，但不能直接下注。** 先用 7–10 天测量 causal-hindsight premium；若 premium 很小或收益依赖回看已删除原视频，应立即停止。
4. **不要同时开发三个完整系统。** 三个方案共享同一个最小基础设施；前 10 天先测量三个决定量，再只保留一个主论文方向。

### 0.2 对“今年 CVPR”的时间解释

当前日期是 2026-09-04，CVPR 2026 已结束，因此本文将目标解释为 **CVPR 2027 投稿季**。截至本文日期，[CVPR 2027 官网](https://cvpr.thecvf.com/Conferences/2027)只公布了 2027-06-20 至 2027-06-25 的会议日期，尚未公布投稿截止日；上一届 [CVPR 2026 的论文截止日](https://cvpr.thecvf.com/Conferences/2026/Dates)是 2025-11-13。本文因此采用保守假设：**在 2026 年 11 月上旬前完成主结果**。这是排期假设，不是官方日期。

---

## 1. 从既有形式化继承什么

### 1.1 统一任务协议

令：

- $H_t=O_{1:t}$：截至时刻 $t$ 的视频历史；
- $S_t$：允许独立使用的 side information，如原生 ASR、OCR、时间戳；
- $M_t$：持久记忆；
- $W$：看不到未来问题、也看不到未来视频的因果 writer；
- $Q$：在记忆冻结后出现的问题；
- $R$：问题可见的 reader；
- $F_\theta$：冻结的消费模型；
- $\mathbf B=(B_{\mathrm{store}},B_{\mathrm{write}},B_{\mathrm{read}},B_{\mathrm{interface}},B_{\mathrm{compute}})$：多资源预算。

主协议为：

$$
M_t=W(M_{t-1},O_t,S_t),
\qquad
\widehat Y=F_\theta(Q,S_T,R(M_T,Q)).
$$

在主实验中必须满足：

1. writer 在写入时不可见测试问题、答案、证据时间戳或它们的 embedding；
2. 同一视频的所有事后问题共享同一个 frozen memory snapshot；
3. query time 不可回看已删除的原始视频；
4. 主比较固定 candidate、codec、reader、consumer 和实际持久字节，只替换待研究的机制；
5. 视觉 token、文本 token、KV、索引和元数据全部换算为实际字节，读取字节与送入模型的 interface token 另行报告。

### 1.2 三个方案对应三类缺口

此前形式化把记忆问题拆成三层，三个新方案正好各攻一层：

| 形式化层 | 要回答的问题 | 本文方案 |
|---|---|---|
| 语义充分性 | 哪些历史差异必须保留，才不会改变任务答案？ | CPM：完整证据路径 |
| 操作可用性 | 信息已经在记忆中时，指定 reader/consumer 能否访问并使用？ | MID：完整性与故障归因 |
| 因果可维护性 | 重要性在未来才显现时，在线 writer 能否及时修正过去的保留决策？ | DKM：延迟可知性 |

这里不预设记忆必须是 latent、KV、文本、图或帧。三种表示都可作为共同 backbone；首篇论文只研究一个可归因的目标，不再同时发明新 codec、新 reader 和新 consumer。

### 1.3 共同实验原则

- **现象先于模型。** 先证明目标缺口真实且有同预算 oracle headroom，再训练方法。
- **一个受控诊断集 + 两个自然数据源。** 诊断集用于因果归因，自然数据用于外部有效性。
- **冻结大模型。** 默认选择一个可复现的 7–8B 开源 VLM，经小规模 smoke test 后再确定；不在本文中锁定具体模型。
- **只训练小模块。** set critic、诊断器或影响 critic 控制在约 10M–100M 参数；如需 LoRA，只适配少量 attention projection。
- **至少三种随机种子只用于轻量训练。** 大模型特征与确定性 teacher 输出缓存复用。
- **所有结论带干预。** 删除、阻断读取、语义替换和时间打乱用于区分记忆真正被使用，还是模型仅靠题面先验猜对。

---

## 2. 方案一：完整证据路径记忆（Complete-Path Memory, CPM）

### 2.1 一句话方案

> 在未来问题未知、存储预算固定时，不再给每条事件独立打“重要性分数”，而是学习当前 memory set 是否为各类未来问题保住了至少一条**完整的最小充分证据路径**，并据此执行插入与替换。

这是当前最推荐的方向，也是对既有 FQR 思想最自然的收缩：FQR 不再表示单条事件的抽象“未来价值”，而成为**未来任务族下的条件集合价值**。

### 2.2 文献依据与真实 gap

#### 已有结果显示 headroom 很大

1. **严格 pre-query 协议已经成立，但离 oracle 很远。** [EMBER](https://arxiv.org/abs/2606.05894) 明确定义 Budgeted Pre-Query Retention。在 LongMemEval-RR 的 8192-token 点，作者报告 EMBER-14B 的 F1 为 `0.3017`，同预算 oracle 为 `0.4499`；Retain-Recall 为 `0.3215`，oracle 为 `0.9998`。这说明瓶颈不是“协议是否合理”，而是 writer 仍没有保住足够的未来证据。
2. **一份 memory 服务多个问题时，普通保留策略尤其差。** EMBER 的 MultiQ 设置要求一个冻结 memory 同时服务五个未来问题；在 10% 预算下，作者报告 oracle 的 mean-query Retain-Recall 为 `0.6275`，而强 learned writer 仍有明显差距。更关键的是，启发式方法的 weakest-query coverage balance 为 0，说明平均保留若干相关证据不等于每个问题都有完整可用路径。
3. **集合效用确实非可分解。** [OSL-MR](https://arxiv.org/abs/2606.10616) 明确写道 retention reward 是 non-decomposable 和 combinatorial，因为质量由 memory set 而不是单条 item 决定；但为可部署性，它又退回到逐条 evidence-membership supervision。其已知 coverage 目标仍是普通并集覆盖，不能表达“bundle 内 AND、替代 bundle 间 OR”。
4. **相关不等于充分。** [REVEAL](https://arxiv.org/abs/2608.08612) 的 sufficiency verifier 在 Video-MME-long/LVBench 上分别带来 `+7.8/+10.9` 点，是最大单项增益；无 verifier 时约 128 段达到 76.2%，有 verifier 时平均约 31 段达到 79.1%。这支持“证据是否齐全”比“多取一些相关片段”更关键。
5. **常用单条 proxy 可能方向错误。** [CVMA](https://arxiv.org/abs/2607.25467) 在冻结 Qwen-7B 对话上报告当前 attention 与未来区域效用的 Spearman 为 `-0.103`；按 attention 联合保留在多个预算下比 seeded random 更差，而同一对话的 marginal-utility control 又显著优于随机。这同时给出 proxy misalignment 和可选择 headroom。

#### 最近邻还没有解决的精确问题

- EMBER 联合评价完整 trajectory，但存储和监督的基本单元仍是 source evidence unit；它没有显式建模哪些证据必须一起存在、哪些路径可互相替代。
- OSL-MR 形式上承认 set reward，却用 per-memory evidence membership 绕开集合交互；其 maximum-coverage 核心是 OR/additive coverage，不是 answerability 的 AND–OR 结构。
- [DeMem](https://arxiv.org/abs/2605.10870) 已经占据 decision-centric rate–distortion 和 forgetting boundary，但它的 encoder 是 $M_t=g_t(H_t,Q_t)$，在压缩时可见当前 query；它不解决所有未知 future queries 共用一个 pre-query persistent state 的问题。
- [HyperMem](https://arxiv.org/abs/2604.08256) 已使用 hypergraph 表示长期对话中的高阶关联，因此本文不能把“用了超图”当新意；剩余贡献必须是**不可逆 pre-query 视频压缩下的充分路径存活、oracle frontier 和 writer regret**。

因此可辩护的 gap 是：

> 现有方法已经研究 query-hidden retention、集合 reward、hypergraph retrieval 和 query-time sufficiency，但尚未把“未来问题的最小充分证据族”作为 pre-query writer 的直接优化对象，也未测量逐条 scorer 在 AND–OR evidence geometry 下的系统性 regret。

### 2.3 形式化

对每个未来问题 $q$，定义观察到的最小充分证据族：

$$
\mathcal E_q=\{E_{q,1},E_{q,2},\ldots,E_{q,K_q}\},
$$

其中 $E_{q,k}$ 是一条能够独立支持答案与 grounding 的最小路径。保留集合为 $M$ 时：

$$
A(q,M)
=
\mathbf 1\!\left[\exists k,\ E_{q,k}\subseteq M\right].
$$

这对应：

- 同一路径内的证据是 AND；
- 不同替代路径之间是 OR；
- 不同问题可能共享 evidence core；
- 同一 item 的边际价值依赖当前 $M$、side information $S$ 和其他候选。

定义同预算的未来问题价格：

$$
\Pi_Q(B)
=
D_{\mathrm{preQ}}(B)-D_{\mathrm{postQ}}(B),
$$

其中 postQ oracle 看到问题后从完整历史选择，preQ writer 必须为整个任务族共享一次压缩。方案一的目标不是消灭 $\Pi_Q$，而是在严格 causal/pre-query 条件下逼近 offline-preQ oracle。

### 2.4 最小可行方法

#### 固定输入，不做新 codec

先用共同 candidate generator 把视频切成事件 capsule。每个 capsule 固定包含：

- 一小段统一码率视觉 payload；
- 时间区间和来源 ID；
- 冻结视觉 embedding；
- 允许的 ASR/OCR/实体特征；
- 实际存储字节。

第一版所有 capsule 同码率，避免把收益混入 codec。多码率只在主假设成立后作为补充消融。

#### 训练 query-free set critic

对当前 memory $M$ 和候选 $c_t$，轻量 Set Transformer 或 DeepSets 输出预声明结构组的完整路径存活概率：

$$
V_\phi(M)
=
\bigl[V_{\phi,1}(M),\ldots,V_{\phi,G}(M)\bigr].
$$

组只使用训练数据定义，例如：单证据/多证据、短/长间隔、顺序、计数、身份、OCR、状态变化；测试前冻结。训练样本包括：

1. 完整 bundle 正例；
2. 只缺一个必要 item 的 hard negative；
3. 用相似但错误事件替换一个 item 的 semantic-swap negative；
4. 从 writer 实际访问到的 memory state 采样的 on-policy coalition；
5. 同问题的替代路径和跨问题共享核心。

不做大规模在线 RL。teacher 只在训练视频上通过 gold evidence、leave-one-out 和固定 consumer 干预构造 set-level 标签，再蒸馏到小 critic。

#### 在线插入与替换

对 `skip / insert / replace-one` 的小动作集，计算：

$$
J_\phi(M)
=
\frac{1}{G}\sum_g V_{\phi,g}(M)
-
\lambda\operatorname{CVaR}_\alpha(1-V_{\phi,g}(M)).
$$

小容量 $K$ 可枚举所有单替换；较大 $K$ 先用共享的 item-level prefilter 选 8–16 个可能淘汰项，再由 set critic 重排。prefilter ceiling 必须报告，防止方法因预筛漏项被误判。

### 2.5 数据与实验设计

#### 数据候选

最终数据选择应在许可证、下载和 baseline smoke test 后冻结，不提前锁定。当前最合适的候选是：

- **可控 Video Memory Gym**：程序生成 evidence hypergraph，可精确控制 bundle size、overlap、替代路径数、时间间隔和 side-information 质量，并可枚举 oracle。
- [EG-VQA](https://arxiv.org/abs/2606.24797)：2,067 个视频、11,838 个开放式 QA，带细粒度时间证据，适合按视频聚合多问题并形成 observed bundle。
- [E-VQA / ST-Evidence](https://arxiv.org/abs/2607.11862)：同时提供时间段和对象 masklet，适合验证收益是否来自真实视觉 grounding，而不是字幕或题面。
- [StreamArena](https://arxiv.org/abs/2608.05703)：243 个平均 88.8 分钟的视频和 3,646 个开放式 QA，适合作为真正长时、最近窗口无法解决的外部验证；不建议作为第一周的开发集。

真实数据中的 bundle 只能称为 **observed sufficient path**，不能声称标注枚举了所有有效路径。对主要结果需人工复核一个分层子集，并记录可能的替代路径。

#### 核心基线

1. uniform、FIFO、recency、reservoir；
2. scene change、feature novelty、surprise；
3. [FluxMem](https://arxiv.org/abs/2603.02096)、[CausalMem](https://arxiv.org/abs/2606.25658)、[SAVEMem](https://arxiv.org/abs/2605.07897) 或 [StreamMem](https://arxiv.org/abs/2508.15717) 中至少两个可复现的 query-hidden writer；
4. learned scalar future value；
5. additive maximum coverage；
6. CPM set critic；
7. query-known selector、offline-preQ selector 和 full-history reader，均单列为 oracle，不能混入公平排名。offline-preQ 只在可控 gym 或小候选集上用穷举/整数规划求 exact optimum；真实长视频使用带上界的整数规划、beam search 或 best-found 解，并明确标成近似 oracle。

#### 决定性实验

1. **Matched item recall。** 构造 item recall 相同但 complete-path survival 不同的 memory，检查后者能否额外解释 grounded answerability。
2. **Geometry sweep。** 单独改变 bundle size、overlap、替代路径数和 query entropy，画 scalar writer 与 exact oracle 的 regret heat map。
3. **Same-backbone objective replacement。** 固定 capsule、reader、consumer 和字节，只替换原 writer objective、scalar critic、additive coverage 与 CPM。
4. **Lifecycle audit。** 分别报告 bundle 是否 Stored、Accessed、Used，避免 reader 失败被归到 writer。
5. **因果使用测试。** 删除最高集合边际值 item、删除匹配随机 item、阻断一条完整路径、以及跨视频 semantic swap。

#### 主指标

- complete-path survival；
- item evidence recall；
- answerability–budget AUC；
- joint answer-and-evidence score；
- mean / worst-group grounded regret；
- $\Pi_Q(B)$；
- write latency、read bytes、interface tokens、峰值显存与 teacher GPU 时。

### 2.6 可做性分析

#### 为什么在 2 × 80GB 内可做

- 大 VLM 全程冻结；视觉特征和 teacher 输出一次计算、多次复用。
- set critic 只读缓存后的事件 embedding，参数量和序列长度远小于 VideoLLM。
- 不复现 EMBER 的 4×H200/8×H100 rollout 训练；EMBER 自身的 compute disclosure 说明完整 RL 路径较重，而本方案明确用离线 coalition 标签 + supervised critic 替代。
- 7–8B VLM 的 BF16/4-bit 推理和小 LoRA 均可放入单张 80GB；第二张卡可独立做编码、teacher 标注或另一 consumer 的验证。
- 当前仓库已有 bundle-aware 英文草稿、形式化、图计划和最近邻文献表，省去约一到两周的论文框架工作。

#### 建议资源分配

| 环节 | 建议配置 | 粗略 GPU 时 |
|---|---|---:|
| 事件切分与 frozen feature cache | 1 卡批处理 | 30–70 |
| 训练集 bundle/coalition teacher | 1–2 卡并行推理 | 40–120 |
| set critic 训练与三种子 | 1 卡 | 5–20 |
| 全预算曲线、干预与第二 consumer | 1–2 卡 | 25–60 |
| 合计 | 不含失败重跑 | **100–250** |

#### 8 周排期

| 周 | 交付物 | Gate |
|---:|---|---|
| 1 | 数据许可与下载审计；统一 snapshot、字节记账、基础 writer | 同视频换问题后 snapshot hash 不变 |
| 2 | exact gym、三类 oracle、scalar regret | bundle interaction 在至少两个设置中明显非零 |
| 3 | 真实数据 observed bundle 构造与小规模人工审计 | candidate recall 足够，标签不是纯时间泄漏 |
| 4 | set critic、partial-bundle hard negatives | held-out set utility 排序优于 scalar |
| 5 | causal insert/replace writer | 在线成本不随历史线性扫描 |
| 6 | 第一自然数据集全实验 | matched-byte 下 complete-path 与 grounding 同时提升 |
| 7 | 第二数据集、第二 consumer、消融 | 提升方向一致，不依赖单一模型 |
| 8 | 统计、图表、论文收口 | 所有主张都能指向对应实验 |

### 2.7 Go / no-go 标准

建议在开发集预注册以下门槛：

**Go：**

1. 控制 item recall 后，complete-path survival 对 answerability 仍有稳定额外解释力；
2. exact gym 中 scalar writer 在至少两个非平凡 geometry 区域明显落后于 set oracle；
3. CPM 相对最强 scalar writer，在至少两个预算上提高 complete-path survival，并在两个自然数据源上带来同方向 grounded gain；
4. top-path deletion 的损害显著大于匹配随机删除；
5. 第二 consumer 上方向一致。

可作为内部工程门槛而非论文承诺：`complete-path survival ≥ +5pp`，且 `joint answer+evidence ≥ +2pp`；最终应同时报告置信区间，而不是只看点估计。

**No-Go / 收缩：**

- 最强 scalar writer 在 geometry sweep 中始终接近 exact oracle；
- set critic 只提高 item recall，不提高完整路径与 grounding；
- 收益仅存在于人工严格 AND 任务，在自然数据消失；
- observed bundle 的人工一致性太低，或 alternative path 漏标主导结论；
- online allocator 的主要损失来自 candidate prefilter，而不是集合估值。

### 2.8 审稿风险与边界

| 质疑 | 必须给出的回答 |
|---|---|
| “只是 hypergraph memory” | HyperMem 等已占据表示结构；本文贡献是 pre-query answerability objective、oracle frontier 和 writer regret，不是图结构名称。 |
| “EMBER/OSL 已做 set reward” | 用 AND–OR geometry、partial-bundle hard negatives和 same-backbone item-vs-set 对比证明它不是普通 evidence coverage。 |
| “bundle 标签不完备” | 真实数据只称 observed-path coverage；exact claim 仅来自可控 gym；人工审计替代路径。 |
| “teacher 看未来问题是泄漏” | teacher 只生成训练标签；测试 writer 输入审计、按视频切分、多问题共享 snapshot。 |
| “收益来自更多 token” | 持久字节、读取字节、interface token、reader 和 consumer 全部匹配。 |

### 2.9 最小论文贡献

1. 证明 evidence recall 与 answerability 在最小充分路径几何下系统分离；
2. 定义并测量未知未来问题下的 complete-path frontier 与 $\Pi_Q$；
3. 提出一个不看测试 query 的轻量 set-value writer，在同 backbone、同字节下提高完整路径存活和 grounded QA。

---

## 3. 方案二：记忆完整性诊断（Memory Integrity Diagnosis, MID）

### 3.1 一句话方案

> 不再只让模型“没把握就拒答”，而是在压缩后的视觉记忆上预测 `answerable / storage-miss / access-miss / use-failure`，输出缺失证据的时间/类型 witness，并在声明的压缩分布上控制最危险的 false-safe 风险。

该方向不是新 writer，而是视觉记忆的**运行时完整性层**。它最适合在方案一的 bundle 现象不够强、但压缩后 silent failure 很突出时转为主线。

### 3.2 文献依据与真实 gap

1. [Compression-Aware Abstention](https://arxiv.org/abs/2608.29934) 的结果显示，压缩改变的不只是准确率，还改变“上下文是否仍有答案证据”。其 10.1M 参数 LoRA 仅用约 2.6K 个 MuSiQue 样本，并在单张 H100 80GB 上完成训练和评测，说明小规模完整性学习本身非常可做。
2. 但该工作的 label 是短 answer-bearing span 是否存活，而不是完整语义充分性。作者对 400 个样本的审计只得到 `κ=0.61`；主要分歧正是答案字符串还在、桥接证据已丢。真实 compressed-cache、80% retention 时，其 mix-cc honest accuracy 仍只有 `0.315`。
3. [SIEVES](https://arxiv.org/abs/2604.25855) 已将视觉证据定位质量用于 selective prediction，并在多个 OOD VQA 数据上提高 coverage。因此“视觉 grounding 帮助拒答”也不能再作为主创新。
4. [REVEAL](https://arxiv.org/abs/2608.08612) 能判断证据是否充分并指出缺失 rubric，但它可以回到仍然存在的完整离线视频 memory 继续检索；它没有面对不可逆删除后“证据已经不存在”的情况。
5. [MemTrace](https://arxiv.org/abs/2606.17328) 在 13 个长期记忆配置上发现，失败时“证据可检索但未被使用”约比“证据不可达”多 10 倍；[WorldMemArena](https://arxiv.org/abs/2605.29341) 也把多模态记忆拆成 writing、maintenance、retrieval、use 四阶段，并发现写得更好不保证最终表现。这说明用最终答错反推“记忆丢了”会严重误归因。

因此普通版本已经被占据，剩余 gap 必须收窄为：

> 在 query-hidden、不可逆视觉压缩后，用受控干预构造阶段标签，预测并定位 storage/access/use 故障；通过显式 provenance/dependency witness 减少对 retention ratio 和压缩 mask 形状的投机，并对 false-safe 进行风险校准。

### 3.3 形式化

对问题 $q$ 和冻结记忆 $M$，定义生命周期状态：

$$
Y_{\mathrm{life}}
\in
\{\text{answerable},\text{storage-miss},
\text{access-miss},\text{use-failure}\}.
$$

可操作定义为：

1. **Stored**：至少一条 observed sufficient path 的必要视觉证据仍在 $M$；
2. **Accessed**：reader 返回了至少一条已存完整路径；
3. **Used**：给定返回的完整路径，consumer 产生正确、grounded、且对必要证据干预敏感的输出；
4. 第一个失败的阶段决定标签。

诊断器输出：

$$
C_\psi(q,R(M,q),R_L(L_M,q))
=
(\widehat Y_{\mathrm{life}},\widehat w, s),
$$

其中 $L_M$ 是计费的 memory ledger，$R_L$ 是有固定读取预算的 ledger reader，$\widehat w$ 是缺失或失配证据的时间区间/类型 witness，$s$ 是“可以安全回答”的分数。诊断器不能免费扫描全部 payload 或 ledger；$R$ 与 $R_L$ 的读取字节都必须报告。

在校准分布上选择阈值 $\tau$，目标为：

$$
\Pr(\text{answer}\mid Y_{\mathrm{life}}\neq\text{answerable})
\leq \alpha.
$$

可以采用 [Conformal Risk Control](https://arxiv.org/abs/2208.02814) 或其 selective 扩展做校准，但只能在满足交换性或明确 shift 假设的范围内表述保证；不得宣称 open-world certificate。

### 3.4 最小可行方法

#### 计费的 memory ledger

每个候选事件生成一个 64–128 byte 的低码率 ledger entry，记录：

- source interval 与 capsule ID；
- 粗粒度 entity/OCR/action hash；
- 可提供的 evidence capability bit，如颜色、文字、身份、顺序、动作、空间；
- payload 是否仍存、采用何种 codec/rate；
- payload 的存活状态与 codec/rate。

ledger 必须计入 $B_{\mathrm{store}}$。reader 返回与 consumer 引用属于 query-time trace，不伪装成免费的持久元数据，其读取和 interface 成本另计。首篇只主张小时级、预声明最大候选数下的有界开销；不声称无限流中每个历史事件都可永久保留 tombstone。若要扩展到无限流，可在后续工作中研究分层合并或 Bloom/Count-Min sketch。

#### 自动构造阶段监督

从同一 `(video, query)` 生成长度、预算和内容匹配的四类样本：

1. **answerable**：完整证据路径被保留并返回，且 consumer 正确、grounded 地使用它；
2. **storage-miss**：在 writer 后删除一个必要 capsule，同时保留相同数量的匹配 distractor；
3. **access-miss**：存储不变，只阻断 reader 返回一个必要 capsule；
4. **use-failure**：完整路径确实被保留并返回，但固定 consumer 仍答错、grounding 失败，或没有通过必要证据删除/阻断测试；该类只能从真实 consumer rollout 中采集，不能用破坏充分性的 semantic swap 直接伪造。

每个 retention ratio 和 compressor 内做类别平衡，并加入“同长度、同删除数、不同关键证据”的 pair，避免模型只学压缩比例或 mask pattern。跨视频或反事实 semantic swap 仅作为 sufficiency/witness hard negative；若替换破坏了完整路径，应归入 storage/access 侧的证据失配，而不是 use-failure。

#### 小型诊断器

两种都可在资源内实现：

- 首选：冻结 VLM embedding + 50M–100M cross-attention diagnostic head；
- 备选：对 7–8B consumer 做 rank-8/16 LoRA，只适配 attention projections，同时输出状态、witness 和 answer/abstain token。

第一版不要联合训练 compressor。这样可以明确回答：在给定 memory 机制下，完整性诊断是否成立。

### 3.5 数据与实验设计

#### 数据候选

- EG-VQA：时间证据能自动判断 payload 是否覆盖 gold interval；
- E-VQA / ST-Evidence：对象 masklet 能制造“时间正确但对象错误”的 hard negative；
- [VideoZeroBench](https://arxiv.org/abs/2604.01569) 或 StreamArena 的可下载子集：验证更长时间和复杂证据条件；
- 一个可控 evidence-path set：生成 exact storage/access/use 标签，检验诊断器是否真的定位阶段。

#### 压缩族

最低要求是两个训练压缩族和一个 held-out 压缩族：

1. frame/event hard dropping；
2. visual-token/KV compression；
3. text consolidation 或另一未见过的 selector，作为跨 compressor 测试。

不要求完整复现所有最新系统；选择一个共同 streaming backbone，把 uniform、recency、语义压缩和一个 learned writer 映射到统一 capsule/mask 接口即可。

#### 核心基线

1. answer log-prob、entropy、self-consistency；
2. verbalized confidence / “证据是否足够”提示；
3. Compression-Aware Abstention 的视频适配；
4. SIEVES-style visual evidence score；
5. REVEAL-style rubric verifier，但禁止回看已删除原视频；
6. 无 ledger 的相同诊断器；
7. 只看 retention ratio/mask statistics 的 shortcut baseline；
8. gold lifecycle oracle。

#### 主指标

- risk–coverage curve 与 AURC；
- `false-safe = P(answer | insufficient)`；
- answerable 样本上的 over-abstention；
- 四类 lifecycle macro-F1；
- 缺失时间区间 IoU / evidence-type F1；
- cross-compressor、cross-backbone 和 cross-evidence-type transfer；
- ledger bytes、诊断延迟和额外 interface tokens。

### 3.6 可做性分析

#### 为什么在 2 × 80GB 内可做

- 样本由已有 evidence annotation 和受控压缩自动产生，不需要昂贵 RL rollout。
- Compression-Aware Abstention 在单张 H100 80GB、约 2.6K 训练样本和 10.1M LoRA 上完成同类行为学习，其资源用量支持本方案的低算力可行性；本方案虽然增加视频编码和四分类，但仍不需要全量更新 VLM。
- 主要成本是预计算多种压缩后的 VLM 输出；这些分支可以离线缓存并分摊给多个诊断器。
- GPU0 可批量生成视频特征与 compressed outputs，GPU1 可持续训练小 head/LoRA；不存在跨卡大模型训练的必要性。

#### 建议资源分配

| 环节 | 建议配置 | 粗略 GPU 时 |
|---|---|---:|
| 两个训练 compressor + 一个 held-out compressor 的特征/输出 | 1–2 卡 | 30–80 |
| 生命周期干预与标签构造 | 1–2 卡 | 15–40 |
| diagnostic head / LoRA 三种子 | 1 卡 | 5–20 |
| 风险校准、跨模型和人工审计 | 1–2 卡 | 10–30 |
| 合计 | 不含大规模新标注 | **60–160** |

#### 6–8 周排期

| 周 | 交付物 | Gate |
|---:|---|---|
| 1 | 统一 compressor mask/capsule API，复现 answerable vs missing | 受控删除显著改变 grounding/答案 |
| 2 | 四类 paired intervention 数据 | ratio-only baseline 无法解决任务 |
| 3 | 无 ledger 诊断器与通用 confidence 基线 | storage/access/use 确有可分信号 |
| 4 | ledger + witness 模型 | matched hard negatives 上仍有优势 |
| 5 | conformal/selective calibration | 指定风险下 coverage 明显高于基线 |
| 6 | held-out compressor 与第二数据集 | 不只记住一种 mask 形状 |
| 7–8 | 第二 consumer、人工审计、写作 | failure localization 可解释且稳定 |

### 3.7 Go / no-go 标准

**Go：**

1. 在固定 retention ratio、删除数量和上下文长度后，诊断器仍显著优于 ratio-only、entropy 和 verbal self-check；
2. 在目标 false-safe（例如开发集预注册的 5%）下，coverage 比最强基线高至少 10pp，或在匹配 coverage 下 false-safe 相对下降至少 30%；
3. lifecycle macro-F1 比二元 answerability 明显增加实际诊断价值，并能定位缺失时间/类型；
4. held-out compressor 和第二 consumer 上方向一致；
5. ledger 消融表明收益来自 provenance/capability witness，而不是附带更多语义文本。

**No-Go / 收缩：**

- 加入 matched hard negatives 后优势消失；
- 模型只会二元拒答，无法区分 storage 与 access/use；
- gold evidence 存活与真实语义充分性一致性过低；
- 风险控制只在随机切分成立，按视频域或 compressor shift 立即失效；
- ledger 的字节或生成成本抵消了压缩收益。

### 3.8 审稿风险与边界

| 质疑 | 必须给出的回答 |
|---|---|
| “只是 SIEVES/可靠 VQA” | SIEVES 估计答案/定位质量；MID 由压缩干预定义 store/access/use 原因，并显式处理不可逆 memory loss。 |
| “只是 Compression-Aware Abstention 的视频版” | 必须展示四阶段归因、bundle/bridging evidence、witness localization、跨 compressor 和 false-safe 风险控制。 |
| “certificate 过度宣称” | 正文使用 calibrated integrity diagnosis；只对声明的数据/压缩族给统计风险保证，不给 open-world 语义证明。 |
| “storage-miss 不可从缺失信息推断” | 明确依赖计费 ledger；无 ledger 是不可识别下界，而非被隐去的免费信息。 |
| “use-failure 只是模型能力不足” | 正是操作充分性缺口；用第二 consumer、gold-evidence injection 和 matched swap 将其与存储失败分开。 |

### 3.9 最小论文贡献

1. 一个面向不可逆视觉记忆压缩的阶段化完整性协议，并系统检验其相对普通 abstention 的增量价值；
2. 由受控干预自动生成的 answerable/storage/access/use 监督与评测；
3. 一个小型、带 provenance witness 的风险校准诊断器，在未知压缩模式上减少 silent false-safe。

---

## 4. 方案三：延迟可知性记忆（Delayed-Knowability Memory, DKM）

### 4.1 一句话方案

> 一个事件发生时可能看起来普通，只有后来的身份揭示、物体使用、结果或异常才说明它重要；DKM 用受限 forensic tier 保留低码率线索，并让后来观察给仍可维护的早期事件分配 hindsight credit，从而触发保护、关联或升级。

该方案把此前较宽的 RTC/FQR 思想收缩为一个可证伪问题：**未来观察，而不是未来 query，究竟给 causal writer 带来多大不可避免的代价？**

### 4.2 文献依据与真实 gap

1. [ViSAGE](https://arxiv.org/abs/2607.28678) 已给出直接视觉证据：later identity trigger 会触发 Global Backward Update；移除 Bidirectional Memory Refinement 后，作者报告 M3-Bench-robot 下降 4.7 点。说明“后续观察修正过去记忆”不是纯假想。
2. 但 ViSAGE 的 Incident Logs 是 append-only，事件内容 immutable，只允许 `who` 字段被修正；论文没有固定总 memory budget，Global Backward Update 默认历史日志仍在。它不解决“旧证据可能已被淘汰”的问题。
3. [Hindsight Memory-PRM](https://arxiv.org/abs/2608.29605) 用后续 retrieval、citation 与 deletion–reanswer 给早期 memory operation 分配 hindsight credit，其作者结果支持事后可审计监督的有效性；但它明确保留 automatic verbatim layer 和所有旧版本，排除 destructive deletion，并在 limitations 中承认 LoCoMo 没有 budget pressure。
4. OSL-MR 的可解小实例中，即使每步精确最大化当前收益，面对 shifting demand 仍离动态规划最优 31.5%；但这是未来 query demand，不是未来视频观察使过去事件获得新语义。
5. [StreamFlow](https://arxiv.org/abs/2608.10949) 已有动态中期/长期 memory，[D-HSM](https://arxiv.org/abs/2608.30294) 已有实体中心的 hub-and-spoke 结构，因此“两层记忆”或“实体图”本身均不足以构成创新。

剩余 gap 是：

> 在 future query 未知、future observation 也未知、且旧视觉证据可被不可逆淘汰的条件下，量化 causal writer 相对 full-stream offline writer 的损失，并用后来视觉事实的条件边际贡献更新仍存早期证据的 retention priority。

### 4.3 先测量，再设计方法

定义三个同预算 oracle：

1. **postQ**：看到问题后从完整历史选择；
2. **offline-preQ**：不知道问题，但看完整段视频后统一压缩；
3. **causal-preQ**：不知道问题，只能随流到达在线更新。

未来观察的不确定性价格为：

$$
\Pi_H(B)
=
D_{\mathrm{causal-preQ}}(B)
-
D_{\mathrm{offline-preQ}}(B).
$$

若 $\Pi_H(B)$ 在真实或高质量半合成数据上不显著，方案三应停止；不能先做复杂网络再用普通 QA 小增益为其找理由。

同时定义事件 $i$ 的 **knowability time**：在什么最早时刻 $\tau_i$，仅根据 $O_{1:\tau_i}$ 就能可靠判断它属于未来充分证据。方法真正要缩小的是 $t_i$ 到 $\tau_i$ 之间的保护风险。

### 4.4 最小可行方法

#### 有界三层状态

1. **Active ring**：最近若干分钟的高码率 capsule，等待潜在后续揭示；容量固定。
2. **Forensic tier**：更长时间的低码率视觉 sketch、时间与实体/OCR key；容量固定，必要时继续合并或淘汰。
3. **Protected tier**：已被 local value 或 hindsight credit 证实重要的高/中码率证据；容量固定。

三层总字节恒定。future context 只能：

- 把仍在 active ring 的事件晋升到 protected；
- 保护或重新索引仍存在的 forensic sketch；
- 建立早期事件与 later reveal 的显式链接。

它**不能恢复已经删除的像素细节**。主协议不允许静默回看原视频；如果补充实验允许冷存储重编码，必须单列原视频存储和 I/O 成本。

#### Hindsight relation critic

新事件 $c_t$ 到达后，只在 ANN/entity/time prefilter 返回的少量旧 sketch 上计算：

$$
\widehat h_{i,t}
=
H_\phi(c_i^{\mathrm{forensic}},c_t,S_t,M_{t-1}),
$$

预测 later event 是否让早期事件成为某类任务的必要证据。累计 credit：

$$
u_i^t
=
\gamma u_i^{t-1}
+
\eta[\widehat h_{i,t}-b_{\mathrm{freq}}(i,t)]_+.
$$

$b_{\mathrm{freq}}$ 用于抑制“频繁共现但无任务作用”的背景。高 credit 触发 promotion/protection/link update。

#### 离线监督

只在训练视频上，用未来 observation 和问题证据生成 pair/coalition label：

$$
h_{i,t}^{\star}
=
\mathcal L_{\mathrm{task}}(M\setminus c_i;O_{1:t})
-
\mathcal L_{\mathrm{task}}(M;O_{1:t}).
$$

精确 leave-one-out 只对短名单计算；大量样本使用 gold evidence pair、时间顺序与同类 hard negative。在线部署只运行小 critic，不做大模型 counterfactual replay。

### 4.5 数据与实验设计

#### 可控 delayed-knowability 数据

至少覆盖四类：

1. anonymous person/object later named；
2. object appears early and is used much later；
3. setup–payoff；
4. ordinary event later reinterpreted by an anomaly/outcome。

对每类独立控制 reveal delay、distractor density、对象重复频率、active-ring 长度和 forensic bitrate。生成器保存精确的依赖边和 knowability time，可计算 oracle。

#### 自然数据候选

- ViSAGE 使用的 M3-Bench-robot 可作为身份延迟的候选，但需先确认数据和标注是否实际可获得；
- StreamArena 的小时级开放问题可用于挖掘远距离 setup–payoff 与 later-used object；
- EG-VQA、MMR-V 或 E-VQA 中带多个远距 evidence span 的子集可用于构造早期—后期 pair；
- 建议只人工复核 500–1,000 个候选 pair，不创建一个全新的大规模视频数据集。

如果两个自然数据来源都无法稳定得到 delayed-knowability 子集，方案三不应以纯合成结果投 CVPR 主会。

#### 核心基线

1. recency、reservoir、scene-change、surprise；
2. CausalMem/FluxMem/SAVEMem 中可复现的 query-hidden writer；
3. 只做 entity tracking/identity correction 的 ViSAGE-style baseline；
4. 相同三层结构但不做 backward credit；
5. future prediction score，但不做 counterfactual/matched negative；
6. offline-preQ 和 postQ oracle。

#### 决定性实验

1. **Premium test。** 在 matched bytes 下测 $\Pi_H(B)$ 随 reveal delay、active-ring 长度和 forensic bitrate 的变化。
2. **Importance flip。** 测量同一早期事件在 reveal 前后的 oracle value 排名变化，并检验 DKM 是否跟踪这种变化。
3. **Hard negative。** 高频重复背景与真正 setup 共现，但删除背景不影响答案；检查 frequency baseline 与 counterfactual supervision 是否防止误提权。
4. **Irrecoverability audit。** 单独报告因过晚揭示而已丢失的像素细节比例；不能把“索引到低码率 sketch”记为完整恢复。
5. **在线成本。** 每个新事件只访问固定短名单，报告每分钟写入 FLOPs、p50/p95 延迟和历史长度扩展曲线。

#### 主指标

- $\Pi_H(B)$ 与缩小比例；
- early-evidence survival / setup recall；
- retention–delay AUC；
- promotion precision/recall；
- knowability-time estimation error；
- grounded QA 与 evidence recall；
- irreversible-detail-loss rate；
- 总字节、写入延迟和额外 I/O。

### 4.6 可做性分析

#### 为什么仍可在 2 × 80GB 内实现

- backbone、视频 encoder 与 consumer 均冻结；训练对象只是 pairwise relation critic 和小 allocator。
- future credit 标签只对 ANN 短名单做局部 counterfactual，不做整段视频所有事件的 $O(T^2)$ 大模型 replay。
- 可控数据的 exact oracle 在 CPU 或单卡小模型上完成；真实数据只标注小型 delayed subset。
- Active/forensic/protected 三层都可建立在现有 capsule 表示上，不需要设计新 KV kernel 或训练视频 codec。

真正的风险不是显存，而是**数据效应与标注可得性**。因此资源可行不等于论文可行，必须先通过 premium gate。

#### 建议资源分配

| 环节 | 建议配置 | 粗略 GPU 时 |
|---|---|---:|
| 可控流生成、特征与 exact/pseudo oracle | CPU + 1 卡 | 15–40 |
| 自然数据 pair mining 与局部 counterfactual label | 1–2 卡 | 30–80 |
| relation critic / allocator 三种子 | 1 卡 | 10–30 |
| 全延迟曲线、第二数据集和干预 | 1–2 卡 | 25–50 |
| 合计 | 通过 Gate 0 后 | **80–200** |

#### 8–9 周排期

| 周 | 交付物 | Gate |
|---:|---|---|
| 1 | 四类可控流、三 oracle、$\Pi_H$ 曲线 | premium 明显且随 delay/budget 有规律 |
| 2 | 两个自然数据来源的 100–200 样本审计 | effect 不只存在于合成 identity task |
| 3 | Active/forensic/protected 固定预算基线 | 简单 recent window 不能吃掉全部增益 |
| 4 | hindsight critic 与 hard negatives | credit 排序优于 surprise/frequency |
| 5 | causal promotion 与固定短名单访问 | 在线延迟不随历史线性增长 |
| 6–7 | 自然数据全评测、oracle ladder | 缩小 $\Pi_H$ 并提高 grounded QA |
| 8–9 | 消融、第二 consumer、论文 | 明确报告不可恢复边界 |

### 4.7 Go / no-go 标准

**Go：**

1. 在至少两类 delayed event 和一个自然数据来源上，offline-preQ 明显优于 causal-preQ；
2. 建议内部门槛：多个预算上的 $\Pi_H \ge 3$ 个绝对 grounded points，或 offline–causal frontier gap 至少 10%；
3. DKM 相对相同三层结构但无 backward credit，能稳定提高 early-evidence survival；
4. 高频重复 hard negative 下仍能正确提权真正 setup；
5. 增益不依赖回看已删除原视频，且 p95 写入延迟满足目标流速。

**No-Go：**

- $\Pi_H$ 很小，offline 和 causal writer 几乎等价；
- 简单 recent window、对象跟踪或更大的 forensic bitrate 已解释全部收益；
- learned critic 在自然数据上不优于 surprise/recency；
- reveal 到来时关键视觉细节通常已经不可恢复，方法只能改文本标签；
- 所有提升都依赖未计费的 raw archive 或全历史扫描。

### 4.8 审稿风险与边界

| 质疑 | 必须给出的回答 |
|---|---|
| “就是 ViSAGE backward update” | ViSAGE 是 append-only identity repair；DKM 必须展示固定总字节、一般 delayed relation、promotion 和 causal/offline premium。 |
| “就是 Hindsight Memory-PRM” | Memory-PRM 使用 query/answer audit 和 lossless substrate；DKM 的 credit 来自后续视觉观察，并面对 destructive forgetting。 |
| “两层 memory 没有新意” | 两层结构只是实现；核心结果是 $\Pi_H$、knowability time 和 backward credit 对 retention 的因果作用。 |
| “删除后怎么恢复？” | 不恢复；只晋升仍在 active ring 的 payload或保护 forensic sketch，并报告不可恢复率。 |
| “合成任务过强” | 主张必须在至少一个自然 delayed subset 上成立；否则停止而非包装。 |

### 4.9 最小论文贡献

1. 区分 future-query uncertainty 与 future-observation uncertainty，并定义/测量 $\Pi_H$；
2. 提出带不可恢复边界的 fixed-budget forensic/protected memory；
3. 用 later visual evidence 的 counterfactual credit 改善早期证据保留，而非只修订文本身份。

---

## 5. 三个方案的横向选择

### 5.1 研究与工程比较

| 维度 | CPM：完整路径 | MID：完整性诊断 | DKM：延迟可知性 |
|---|---|---|---|
| CVPR 主叙事 | 强：新的 writer objective + 可控几何 | 中强：可靠性协议 + 轻量方法 | 通过 premium 后很强 |
| 与既有形式化结合 | 最直接：任务充分性、$\Pi_Q$ | 最直接：操作缺口、生命周期 | 最直接：因果写入、$\Pi_H$ |
| 算力压力 | 低—中 | **最低** | 低—中 |
| 数据压力 | 中：bundle/alternative path | 低—中：干预可自动生成 | **最高**：delayed pair 稀缺 |
| 工程复杂度 | 中：set critic + allocator | 低—中：统一 mask + diagnostic | 中：三层状态 + backward update |
| 最近邻拥挤度 | 中；精确 AND–OR gap 尚清楚 | 高；必须超越 abstention/SIEVES | 中；直接 fixed-budget 邻居较少 |
| 最快负结果 | 1–2 周 | 1–2 周 | 7–10 天 |
| 失败后可复用 | gym、oracle、capsule、草稿 | 干预集、lifecycle evaluator | delayed subset、$\Pi_H$ 诊断 |
| 综合建议 | **主线** | **备线** | 有条件高风险线 |

### 5.2 不能作为主贡献的内容

不论选择哪个方案，下列宽泛主张都已经过度拥挤：

- “我们做了固定预算流式视觉记忆”：FluxMem、CausalMem、SelectStream、SAVEMem、StreamMem 等已覆盖；
- “我们使用层次/两层/图记忆”：[OASIS](https://arxiv.org/abs/2604.17052)、[WorldMM](https://arxiv.org/abs/2512.02425)、D-HSM、HyperMem、StreamFlow 等已覆盖；
- “我们按 query 选关键帧”：query-known long-video retrieval 已非常密集；
- “attention/surprise 是重要性”：已有大量直接方法，也已有 CVMA 的反例；
- “压缩后让模型拒答”：Compression-Aware Abstention 与 SIEVES 已占据普通版本；
- “事后信用/回溯更新”：Hindsight Memory-PRM 与 ViSAGE 已占据无预算或特定版本。

论文必须把贡献写在**信息结构、可测 gap、干预监督和同预算因果归因**上，而不是模块命名。

---

## 6. 建议的统一 10 天决策实验

三个方案共享同一套 capsule、snapshot 和 oracle，因此先做一个小而完整的选择实验最划算。

### 第 1–3 天：协议和数据

- 选一个可下载的 evidence-grounded 数据源和 100–300 个视频；
- 构造同视频多问题、query-after-write snapshot；
- 实现 uniform、recency、surprise/novelty、caption-only、full-history oracle；
- 统一记录 store/read/interface bytes 与 raw-video I/O；
- 做 query leakage hash test。

### 第 4–6 天：三个核心量

1. **CPM 信号**：控制 item recall 后，完整路径存活是否仍解释答案与 grounding？
2. **MID 信号**：storage/access/use 三类受控干预能否被普通 confidence 区分？false-safe 有多严重？
3. **DKM 信号**：offline-preQ 与 causal-preQ 的 $\Pi_H$ 是否显著？

### 第 7–10 天：只实现最小学习器

- CPM：一个 DeepSets set critic；
- MID：一个 frozen-embedding 四分类 head；
- DKM：一个 pairwise hindsight scorer；
- 每个只跑一个 seed 和 2–3 个预算，不追求最终数字。

### 选择规则

| 观测 | 选择 |
|---|---|
| bundle interaction 强，scalar–oracle regret 大 | 进入 CPM |
| writer headroom 小，但 silent false-safe 高且阶段可分 | 转 MID |
| $\Pi_H$ 明显大于 $\Pi_Q$ 的可改善部分，且自然 delayed 样本足够 | 转 DKM |
| 三个信号都弱 | 停止堆模型，重新审视 benchmark、candidate ceiling 或研究问题 |

这 10 天的产物本身应进入 `EXP-YYYYMMDD-memory-gates/README.md`，记录数据版本、seed、命令、预算、结果与止损决策；不能只留在 notebook 或聊天中。

---

## 7. 最终建议

### 7.1 推荐主线

选择 **CPM：完整证据路径记忆**，原因不是它概念最复杂，而是它当前同时满足：

1. 有 EMBER MultiQ、OSL-MR、REVEAL、CVMA 提供直接而互补的 gap 证据；
2. 有清楚的 AND–OR 形式对象和三个可计算 oracle；
3. 可以在不训练 VideoLLM、不发明新 codec 的情况下做同 backbone objective replacement；
4. 当前仓库已经有论文草稿和形式化，时间复用最大；
5. 两周内即可被严格否证，不会吞掉全部投稿周期。

最小论文不要再扩展到完整 FQR 系统、multi-rate codec、迭代 reader、compiler 和 certificate。只保留：

> **现象：item recall 不等于完整路径。方法：query-free set critic。验证：同字节 writer replacement + oracle frontier + storage/access/use audit。**

### 7.2 备线触发条件

若方案一在第 2 周未通过 bundle interaction gate，但受控压缩产生大量“自信回答却证据已丢”的案例，则立即转 **MID**。它的训练和评测都更轻，不需要等新 backbone；但标题和主张必须围绕 memory-loss diagnosis，而不是普通可靠 VQA。

### 7.3 方案三的正确位置

DKM 目前只值得做 premium diagnostic。只有在自然数据上确认“重要性首次变得可知”的延迟效应，而且它不能被 recent window/identity tracking 吸收时，才升级为主论文。否则把 $\Pi_H$ 作为 CPM 的 oracle 分析即可，不再开发第三套系统。

---

## 8. 关键一手来源

### Pre-query retention、组合价值与形式化

- [EMBER: Efficient Memory via Budgeted Evidence Retention for Long-Horizon Agents](https://arxiv.org/abs/2606.05894)
- [Learning What to Remember / OSL-MR](https://arxiv.org/abs/2606.10616)
- [Remember the Decision, Not the Description / DeMem](https://arxiv.org/abs/2605.10870)
- [Predicting Future Utility: Global Combinatorial Optimization for Task-Agnostic KV Cache Eviction](https://arxiv.org/abs/2602.08585)
- [HyperMem: Hypergraph Memory for Long-Term Conversations](https://arxiv.org/abs/2604.08256)

### 流式视觉记忆与直接系统基线

- [What Should a Streaming Video Model Remember? / SelectStream](https://arxiv.org/abs/2606.16353)
- [CausalMem: Dynamic and Fixed-budget Memory Bank](https://arxiv.org/abs/2606.25658)
- [SAVEMem: Semantic-Aware Adaptive Visual Memory](https://arxiv.org/abs/2605.07897)
- [FluxMem: Adaptive Hierarchical Memory](https://arxiv.org/abs/2603.02096)
- [StreamMem: Query-Agnostic KV Cache Memory](https://arxiv.org/abs/2508.15717)
- [OASIS: On-Demand Hierarchical Event Memory for Streaming Video Reasoning](https://arxiv.org/abs/2604.17052)
- [WorldMM: Dynamic Multimodal Memory Agent for Long Video Reasoning](https://arxiv.org/abs/2512.02425)
- [StreamFlow: Dynamic Memory Flows](https://arxiv.org/abs/2608.10949)
- [Dynamic Hub-and-Spoke Memory](https://arxiv.org/abs/2608.30294)

### Evidence sufficiency、可靠性与生命周期

- [REVEAL: Explicit Evidence Sufficiency Verification](https://arxiv.org/abs/2608.08612)
- [Seen, Said, or Forgotten? / CVMA](https://arxiv.org/abs/2607.25467)
- [Compression-Aware Abstention](https://arxiv.org/abs/2608.29934)
- [SIEVES: Selective Prediction through Visual Evidence Scoring](https://arxiv.org/abs/2604.25855)
- [MemTrace: Probing What Final Accuracy Misses](https://arxiv.org/abs/2606.17328)
- [WorldMemArena](https://arxiv.org/abs/2605.29341)
- [Conformal Risk Control](https://arxiv.org/abs/2208.02814)

### 延迟更新与 hindsight credit

- [ViSAGE: Constructing Self-Correcting Memories](https://arxiv.org/abs/2607.28678)
- [Hindsight Memory-PRM](https://arxiv.org/abs/2608.29605)

### Grounded 与长时数据候选

- [EG-VQA](https://arxiv.org/abs/2606.24797)
- [Evidence-Backed Video Question Answering / E-VQA](https://arxiv.org/abs/2607.11862)
- [StreamArena](https://arxiv.org/abs/2608.05703)
- [VideoZeroBench](https://arxiv.org/abs/2604.01569)
- [Search over the Visual World](https://arxiv.org/abs/2608.08075)

---

## 9. 与仓库既有材料的关系

- 最小记忆形式化：[`minimal_memory_formalization_with_fqr_2026-09-01.md`](./minimal_memory_formalization_with_fqr_2026-09-01.md)
- 更宽的潜记忆方案：[`fqr_mem_formal_latent_memory_2026-09-01.md`](./fqr_mem_formal_latent_memory_2026-09-01.md)
- FQR 最近邻与动机重建：[`fqr_mem_cvpr_motivation_and_refined_proposal_2026-09-01.md`](./fqr_mem_cvpr_motivation_and_refined_proposal_2026-09-01.md)
- 候选方向的最新比较：[`fqr_candidate_motivation_and_nearest_work_2026-09-02.md`](./fqr_candidate_motivation_and_nearest_work_2026-09-02.md)
- CPM 对应的英文论文草稿：[`../../writing/drafts/fqr_bundle_memory_cvpr/main.tex`](../../writing/drafts/fqr_bundle_memory_cvpr/main.tex)

本文相对旧材料的新增决策是：在当前投稿窗口和 2×80GB 约束下，把宽泛形式化压缩为三个互斥的最小可发表单元，并为每个方案给出真实最近邻边界、计算预算、排期和可执行止损门槛。
