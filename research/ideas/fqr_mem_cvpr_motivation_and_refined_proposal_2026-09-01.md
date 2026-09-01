# 记住不可替代的证据：FQR-Mem 的 CVPR 动机重建与方案细化

> 日期：2026-09-01
>
> 文档性质：在 [AI 记忆的最小形式化与 FQR-Mem 实例](./minimal_memory_formalization_with_fqr_2026-09-01.md) 基础上的独立新报告；不修改或替代原报告
>
> 目标：广泛核查近期近邻工作，重新界定可辩护的动机、新颖性、方法与 CVPR 验证路径
>
> 暂定方法名：FQR-Mem v3，Future-Query-Robust Conditional Value Memory
>
> 一句话主张：学习视觉证据在“当前记忆与侧信息已知”条件下，对未知未来 grounded 任务族的稳健边际写入价值

## 0. 执行结论

FQR-Mem 仍然值得做，但原先最直观的动机已经不能直接使用：

> 在具体问题出现前，一个流式视频系统应该记住什么？

截至 2026-09-01，SelectStream、SAVEMem、CausalMem、StreamMind、StreamFlow、D-HSM 等工作已经明确研究了查询不可见或任意时刻查询下的固定预算视频记忆。DeMem 又从决策率失真的角度说明，记忆应保留会改变下游决策的历史区分。Learning What to Remember 已在文本 agent 中学习 future-query-blind 的多因子 retention value；CMI 与 CICL 则把干预式或反事实启发的效用用于当前问题已知后的记忆、文件和上下文选择。因此，下面这些单点都不能再作为 FQR-Mem 的独立新颖性：

- query-after-write；
- 固定预算流式记忆；
- 任务相关而非重建相关的记忆；
- surprise 或 semantic novelty 不等于任务价值；
- 学习一个 query-blind 的长期 retention score；
- 反事实效用；
- 决策中心的率失真；
- 图记忆、分层记忆或 query-aware retrieval；
- 通过删除或替换记忆验证模型是否使用了它。

但现有工作之间仍留下了一个清晰的交叉空白：

> **当视觉流必须在真实问题出现前被不可逆压缩时，如何估计一个候选视觉证据相对于当前持久记忆与 side information 的未来 grounded 边际效用，并让这种写入价值对已声明的未来任务分布变化稳健？**

这个问题比“什么值得记住”更窄，也更可检验。它同时强调五个现有方法很少共同满足的条件：

1. **写入时真实问题不可见。** 训练时可以利用问题产生监督，测试 writer 不能看到问题。
2. **价值是条件的。** 候选证据是否有用，取决于当前记忆中已经有什么，以及 ASR、OCR、时间戳等是否已经解释了它。
3. **价值是任务损失，不是内容代理量。** surprise、相似度、语义显著性和表示残差只是候选特征，不是最终定义。
4. **价值允许组合与负效用。** 单独无用的两个事件可能联合决定答案；一个看似相关的条目也可能干扰模型。
5. **价值面向未来任务族与 shift。** 目标不是训练混合分布上的平均准确率，而是在明确 ambiguity set 下控制 worst-group 或 tail grounded regret。

因此，本报告建议把论文的中心从“提出一种新的记忆结构”改成：

> **发现并量化 query-hidden 视频写入中的 retention-value misalignment，再提出一个把离线反事实任务信号蒸馏为在线 query-free writer 的条件价值学习方法。**

最合适的标题方向是：

> **Remember the Irreplaceable: Learning Conditional Write Value for Query-Hidden Streaming Video**

中文可概括为：

> **记住不可替代的证据：未知未来问题下的条件写入价值**

这比原题更能避开 SelectStream 与 SAVEMem 已占据的动机，同时保留 FQR 的核心。

---

## 1. 调研范围、证据等级与检索结论

### 1.1 范围

本轮以此前的 [2026 年相关文献证据表](../literature/fqr_mem_2026_literature_evidence.md) 为底稿。该表已经逐项记录 40 项工作，包括 24 篇 2026 年正式会议论文和 16 篇高度相关预印本。本轮进一步重点核查了 2026 年 5 月至 8 月出现、且会直接改变 FQR 定位的工作：

- SAVEMem；
- SelectStream；
- CausalMem；
- StreamFlow；
- StreamArena / StreamMind；
- D-HSM；
- DeMem；
- Learning What to Remember；
- Causal Memory Intervention；
- Decision-Aware Memory Cards / CICL；
- StreamForest；
- Vista；
- WeaveTime；
- HERMES；
- StreamingTOM；
- MemDreamer、EGAgent 与 M3-Agent。

合并已有证据后，实际审阅集合超过 50 项。由于部分新增条目此前已作为其他论文的相关工作被间接引用，这里不把它们机械相加并宣称为完全无重叠的“55 篇独立新增文献”。

### 1.2 证据等级

本文严格区分：

- **已正式发表工作**：可把会议接收状态作为影响力代理；
- **2026 年最新预印本**：只代表竞争态势和研究方向，不能用尚未形成的引用数宣称“高影响力”；
- **文献事实**：论文明确写出的协议、模块、公式、数据或作者报告结果；
- **本文推论**：从多篇工作对比后得到的空白与风险判断，仍需实验验证。

所有引用优先链接论文、正式 proceedings 或官方 CVPR 页面。性能数字若出现，均是作者报告结果，不等于本项目已复现。

### 1.3 总体检索结论

近期研究已经从“有没有记忆”迅速推进到三个更具体的问题：

1. **如何在无限流上构造有界状态**：FluxMem、CausalMem、SelectStream、SAVEMem、StreamFlow；
2. **如何组织和读取长期历史**：StreamForest、OASIS、WorldMM、StreamMind、D-HSM；
3. **如何使记忆与当前决策对齐**：DeMem、CMI、CICL。

FQR-Mem 的机会不在重复任何一条，而在三条的交叉处：**未来问题不可见的视觉写入、相对于已有信息的条件决策价值、以及对未来任务族变化的稳健分配。**

---

## 2. 近期近邻工作的系统地图

### 2.1 最直接的 query-hidden 视频 writer

| 工作 | 文献事实 | 已经占据的主张 | 仍未回答、与 FQR 相关的边界 |
|---|---|---|---|
| [SURGE](https://proceedings.iclr.cc/paper_files/paper/2026/hash/07b92344686c19cf3ffc335a0f565406-Abstract-Conference.html)，ICLR 2026 | 用历史预测误差定义 surprise，并可叠加 query relevance | surprise-guided token reduction | surprise 是不可预测性代理，不是给定当前记忆和侧信息后的任务边际损失 |
| [FluxMem](https://arxiv.org/abs/2603.02096)，CVPR 2026 | query 不可见时按场景统计做层次选择与空间合并 | 自适应层次流式视觉记忆 | 写入目标主要来自视觉统计与冗余，不直接估计未来 grounded task loss |
| [CausalMem](https://arxiv.org/abs/2606.25658) | 固定预算、严格因果地维护在线 semantic basis，并用残差表征新语义 | query-hidden semantic novelty writer | 主成分或残差覆盖不等于任务族中的条件不可替代性 |
| [SelectStream](https://arxiv.org/abs/2606.16353) | 固定容量 latent graph；surprise 切分；按 similarity、surprise、read count、recency 的固定加权惩罚合并；query-conditioned graph read | 写入、保留与读取的一体化 latent allocation | 作者明确说明 consolidation 不是全局最优压缩；priority 项不测任务失真。最公平的 FQR 验证是保留其骨干，只替换价值目标 |
| [SAVEMem](https://arxiv.org/abs/2605.07897) | 在真实问题隐藏后构建三层固定预算记忆；用对象、计数、动作、场景变化、空间布局等固定伪问题库计算 MaxSim；问题到达后自适应检索 | query-hidden writer 使用未来任务族的语义先验 | 已占据“用伪任务预见未来问题”。但 MaxSim 测的是语义轴显著性，不是相对于已有记忆和侧信息的证据必要性、组合充分性或尾部损失 |
| [StreamFlow](https://arxiv.org/abs/2608.10949) | 用动力学残差过滤中期像素、固定容量 latent 长期记忆，并在生成时根据视觉注意下降触发注入；用 matched 与 shuffled memory 干预验证视觉使用 | dynamics-aware memory flow、注意触发注入、记忆使用干预 | 干预主要用于分析 reader 是否使用记忆，不是 writer 的条件价值监督；写入仍未针对未来任务族的边际损失 |
| [StreamMem](https://arxiv.org/abs/2508.15717) / [InfiniPot-V](https://proceedings.neurips.cc/paper_files/paper/2025/hash/caef5f5e658aa1f7565f063a2cd99726-Abstract-Conference.html) | 以压缩、通用查询 token 或 token 价值管理有界视觉状态 | 通用有界 memory / KV 价值 | 缺少对具体未来任务族、side information 与稀有证据的显式稳健目标 |

这组工作说明：**“严格 query-hidden + fixed budget”已经是成熟协议，不是 FQR 的 novelty。**

### 2.2 事件、结构化与 agentic 长期记忆

| 工作 | 文献事实 | 对 FQR 的约束 |
|---|---|---|
| [Memento](https://proceedings.iclr.cc/paper_files/paper/2026/hash/3b5f4587a0bdb81ecc6ce9d82320a5c2-Abstract-Conference.html)，ICLR 2026 | 动态记忆、query-related selection、step-aware attention，并以最长 7 小时流视频评估 | “超长视频需要动态记忆”已经不是新结论 |
| [StreamForest](https://arxiv.org/abs/2509.24871)，NeurIPS 2025 Spotlight | 把持续事件组织为可合并的 event memory forest | 事件层次和增量合并已经被覆盖 |
| [OASIS](https://arxiv.org/abs/2604.17052)，CVPR 2026 | 分层事件记忆，在推理不确定时按需读取 | uncertainty-triggered hierarchical retrieval 已被覆盖 |
| [WorldMM](https://arxiv.org/abs/2512.02425)，CVPR 2026 | episodic、semantic、visual 多类记忆，按 query 选择来源和时间粒度 | 多模态混合记忆本身不是贡献；但它支持“文本摘要不能替代所有视觉细节”的动机 |
| [HAVEN](https://arxiv.org/abs/2601.13719)，CVPR 2026 | 维持视听实体一致性，构造多粒度结构并 agentic search | 实体身份、音频和视觉证据的互补必须纳入 side information 定义 |
| [StreamArena / StreamMind](https://arxiv.org/abs/2608.05703) | 243 个视频、平均 88.8 分钟、3,646 个开放式问题；writer 在查询出现前持续构建多粒度事件与实体图记忆；作者明确指出未来工作应从检索结果学习 evidence utility | “future-aware retention”已经被公开提出，但尚未给出条件任务价值定义、固定物理预算和可训练 writer 目标。这是问题重要性的强证据，也是最接近的未来工作声明 |
| [D-HSM](https://arxiv.org/abs/2608.30294) | 2026-08-31 发布；把均匀选取的历史 chunk 转为对象、人物、动作、OCR、空间和事件等结构化文本，以实体 hub-and-spoke 组织，问题到达后动态读取 | 结构化文本、实体组织和 query-adaptive retrieval 已很拥挤；FQR 不应再增加另一套图结构。其历史观测近似均匀选择，恰好留下“哪些 chunk 值得在写入期保留”的问题 |
| [MemDreamer](https://arxiv.org/abs/2606.07512)、[EGAgent](https://arxiv.org/abs/2601.18157)、[M3-Agent](https://arxiv.org/abs/2508.09736) | 分别使用多层图记忆、实体场景图、episodic 与 semantic multimodal memory 支持 agentic 检索 | 图、实体、长期 agent memory 是可选载体，不应成为 FQR 的定义或主创新 |

这组视频工作的共同不足不是结构不够复杂，而是：**几乎每个系统都必须用某种人工或代理优先级决定保留什么，但优先级很少被定义为“加入当前记忆后降低多少未来任务损失”。**

### 2.3 决策中心与反事实效用：最危险的相邻领域

| 工作 | 文献事实 | 与 FQR 的关键差异 |
|---|---|---|
| [DeMem](https://arxiv.org/abs/2605.10870) | 从决策率失真定义 agent memory 和 exact forgetting boundary；LoCoMo 上 descriptive similarity 与 evidence compatibility 的 Spearman 相关仅为 $0.103$，AUC 为 $0.548$；其编码器在回答时可见当前查询：$M_t=g_t(H_t,Q_t)$ | 它已经占据“记住决策而非描述”的一般思想。FQR 的边界必须是：历史在 $Q$ 出现前已经不可逆压缩，同一个 snapshot 要服务未来任务族，而不是拿完整历史和当前 $Q$ 做 answer-time encoding |
| [Learning What to Remember](https://arxiv.org/abs/2606.12945) | 明确区分 peeking-at-$Q$ 的 oracle retrieval 与 blind forgetting；用 emotional intensity、goal relevance、self/user relevance、reliability 等因子的学习加权值驱动编码、遗忘和读取。在 479 个 LongMemEval-S 样本的 blind keep-$30\%$ 设置中，作者报告 gold-evidence retention 为 $0.770\pm0.011$ | 已占据“未来问题未知时学习 retention value”。但主实验只评估文本 turn 的 gold retention，不运行 answerer；四个有效因子形成 item-wise scalar，不条件于当前 memory coalition 与多模态 side information，也不研究 grounded task loss、物理字节、组合价值和未来 shift |
| [Causal Intervention-Based Memory Selection](https://arxiv.org/abs/2605.17641) | 对当前用户请求，从已有文本 memory bank 中比较 no-memory、with-memory 和 perturbed-memory 条件，以当前回答效用选记忆 | 已占据“以干预效用代替相似度”的检索主张；但候选 bank 已经存在、当前请求已知，没有解决视觉流的 pre-query irreversible write |
| [Decision-Aware Memory Cards / CICL](https://arxiv.org/abs/2606.08151) | 用 action shift、outcome uplift、necessity 和 negative transfer 等信号给当前任务的文件、测试、轨迹和规则打分，并在 token 预算下打包 memory cards | 已占据“反事实启发效用 + budgeted context packing”；但实证主要是当前任务已知的文件检索与压缩，不是未来问题族下的因果写入 |
| [Choosing How to Remember](https://arxiv.org/abs/2602.14038) | 按下游 response quality 和 utilization 在多种 LLM memory structure 间自适应选择 | 占据自适应结构选择，不直接定义视觉证据的未来条件写入价值 |
| [Remember When It Matters](https://arxiv.org/abs/2607.08716) | 让并行 memory agent 决定何时向当前 action agent 注入提醒 | 占据 proactive injection；它回答“什么时候用”，不是“问题未知时提前保留什么” |

因此，FQR 不能声称：

> 我们首次在未来问题未知时学习记忆价值，或首次用任务效用与反事实干预定义记忆价值。

可辩护的表述只能是：

> **我们研究反事实任务价值如何监督一个 query-hidden、不可逆、固定预算的视觉流 writer；价值条件于当前持久状态和 side information，并对未来 grounded task family 的 shift 显式稳健。**

### 2.4 压缩、读取和取证工作

| 方向 | 代表工作 | 已回答的问题 | 在 FQR 中的角色 |
|---|---|---|---|
| 通用视觉压缩 | [VideoChat-Flash](https://proceedings.iclr.cc/paper_files/paper/2026/hash/b14d7175755b180dc2163e15e3110cb6-Abstract-Conference.html)、[FlashVID](https://arxiv.org/abs/2602.08024)、[CRAFT](https://arxiv.org/abs/2608.01644)、[ForestPrune](https://arxiv.org/abs/2603.22911) | 如何保留通用表示并减少 token | 作为 codec 骨干和 matched-budget 强基线，不作为 FQR 新结构 |
| KV 与 latent memory | [FlexMem](https://arxiv.org/abs/2603.29252)、[MuKV](https://arxiv.org/abs/2605.22269)、[HERMES](https://arxiv.org/abs/2601.14724)、[StreamingTOM](https://arxiv.org/abs/2510.18269) | 多粒度 KV 压缩、复用和量化 | 检验 FQR 价值目标是否可迁移到不同表示 |
| 时间记忆 | [WeaveTime](https://arxiv.org/abs/2602.22142)，CVPR 2026 | 时间重建、顺序感知与不确定性触发的 coarse-to-fine recall | 时间顺序不能只靠语义摘要；但 uncertainty-driven read 已被覆盖 |
| post-hoc 查询 | [Vista](https://arxiv.org/abs/2602.08448)，AAAI 2026 | 场景压缩后回答 post-hoc query，并可从 CPU 召回全分辨率帧 | “问题后来才出现”已被覆盖；其原始帧冷存储不符合 FQR 主协议，可作为允许 replay 的上界 |
| query-known 取证 | [MARC](https://proceedings.iclr.cc/paper_files/paper/2026/hash/16049e0c3f47899091ac46f8b3afb178-Abstract-Conference.html)、[QViC-MF](https://arxiv.org/abs/2603.15167)、[LongVideo-R1](https://arxiv.org/abs/2602.20913)、[LongVT](https://arxiv.org/abs/2511.20785)、[ReMem](https://arxiv.org/abs/2607.24794) | 当前问题已知后导航、选择、压缩和读取 | 只能作为 privileged oracle 或 reader，不是公平 writer 基线 |
| evidence scheduling | [GCR](https://arxiv.org/abs/2608.01660)、[EcoFrame](https://arxiv.org/abs/2608.03918)、[EviSelect](https://arxiv.org/abs/2608.05780)、[REVEAL](https://arxiv.org/abs/2608.08612) | 当前问题下如何覆盖遗漏、扩充预算、检查证据充分性 | 提供 query-time oracle 和 bundle sufficiency 的监督思想 |

### 2.5 评测工作带来的直接约束

| 工作 | 关键事实或发现 | FQR 必须吸收的约束 |
|---|---|---|
| [WorldMemArena](https://arxiv.org/abs/2605.29341) | 将记忆拆成 write、maintain、retrieve、use；更好的写入或保存不保证最终任务更好，视觉证据使用仍困难 | 必须分阶段诊断，不能把“存到了”当成“模型用了” |
| [E-VQA](https://arxiv.org/abs/2607.11862)、[EG-VQA](https://arxiv.org/abs/2606.24797)、[VideoZeroBench](https://arxiv.org/abs/2604.01569) | 要求答案与时间、对象或时空证据共同正确 | 任务损失必须包含 grounding，避免语言先验掩盖记忆失败 |
| [MMR-V](https://proceedings.iclr.cc/paper_files/paper/2026/hash/6f1989abe9562c5cd306e070725fe0a3-Abstract-Conference.html) | 强调远距离、多片段组合与干扰项 | 单事件价值不足，需测 coalition / bundle marginality |
| [RIVER](https://proceedings.iclr.cc/paper_files/paper/2026/hash/1022661f3f43406065641f16ce25eafa-Abstract-Conference.html) | 区分 retrospective memory、live perception 与 proactive response | 长期记忆结果应与最近视觉窗口分栏报告 |
| [StreamArena](https://arxiv.org/abs/2608.05703) | 历史回溯问题存在长 evidence gap，且部分题需要多个证据片段 | 适合验证长间隔和多证据，但需控制 StreamMind 的大模型与系统规模混杂 |

---

## 3. 哪些动机已经被占据，哪些问题仍然成立

### 3.1 已被占据的动机

| 原动机 | 状态 | 原因 |
|---|---|---|
| 具体问题出现前需要记忆 | 已占据 | SelectStream、SAVEMem、CausalMem、StreamMind 等均明确采用 query-hidden 或任意时刻查询协议 |
| 用任务先验比通用压缩更好 | 部分占据 | SAVEMem 已用固定伪问题库近似潜在问题分布 |
| 记忆应面向决策而非描述 | 已占据 | DeMem 已正式化 decision rate-distortion |
| 在未来问题未知时学习 retention value | 已占据 | Learning What to Remember 已用下游 gold-retention 目标学习 blind multi-factor value |
| 相似度不等于有用性 | 已占据 | DeMem、Learning What to Remember、CMI、CICL 都把这一点作为中心现象 |
| 用反事实或干预衡量记忆 | 已占据 | CMI、CICL 和 StreamFlow 的使用分析已经覆盖 |
| 多轮读取、图结构或分层事件 | 已占据 | OASIS、WorldMM、StreamForest、StreamMind、D-HSM 等已经很密集 |

### 3.2 尚未被正面回答的交叉问题

以下不是“未找到任何相关论文”的绝对断言，而是截至当前检索，对上述直接近邻方法目标与协议的综合判断：

1. **条件写入价值。** 现有 query-hidden writer 与 blind value model 很少把候选证据相对于当前 $M$ 和 side information $S$ 的任务损失下降作为显式监督。
2. **从 paired task effect 到写前策略。** Learning What to Remember 学到的是由少量 item factors 组成的全局 retention score，主实验目标是 gold-evidence retention；CMI/CICL 的干预效用又发生在当前任务已知后。仍缺少把 candidate-by-memory-state 的训练期 grounded task delta 蒸馏为测试时 query-free、不可逆 admission policy 的闭环。
3. **视觉 grounded 价值。** 文本 agent memory 的 action utility 不要求保留小物体、颜色、空间布局、身份和视觉冲突，也没有 evidence grounding loss。
4. **组合边际性。** 逐条 relevance 或单条 with/without 对多片段证据不充分；未来 writer 必须提前保存互补 bundle。
5. **未来尾部稳健性。** 固定伪问题或平均训练分布容易牺牲稀有问题、长 evidence gap、side-info 冲突和低显著但关键的细节。
6. **存储与使用闭环。** 条目被 writer 保留、被 retriever 返回、被 consumer 真正用于正确视觉依据，是三个不同事件。

### 3.3 新的中心现象：retention-value misalignment

建议把论文先建立在一个可独立发表的经验现象上：

> **Query-hidden 视频 writer 常用的保存代理分数，与候选证据对未来 grounded 任务的真实条件边际价值系统性错配。**

至少包含五类错配：

| 错配 | 例子 | 预期失败 |
|---|---|---|
| intrinsic salience $\neq$ marginal value | 剧烈镜头切换很新奇，但未来问题只问此前低动态的小标签 | surprise writer 保存干扰，丢失低显著证据 |
| semantic similarity $\neq$ evidence necessity | 画面与伪问题“动作发生”相似，但 ASR 已完整描述动作 | SAVEMem 式 MaxSim 重复保存可由文本恢复的内容 |
| standalone value $\neq$ bundle value | A 片段显示拿起杯子，B 片段显示把杯子交给另一人；单独都不能回答转移链 | 独立 top-$k$ 抛弃组合中的弱单项 |
| average value $\neq$ tail value | 高频题问主要动作，低频题问身份、计数或空间冲突 | ERM writer 以很小平均损失牺牲整个稀有组 |
| stored evidence $\neq$ used evidence | 正确帧被取回，但大量文本或错误摘要使模型仍靠先验作答 | 只看 recall 或答案无法定位 reader/interface 失败 |

如果这个现象在强基线和至少两个数据来源上不成立，FQR-Mem 就不应继续扩展为完整系统。这是方案最重要的早停门槛。

---

## 4. 从最小记忆形式化到 FQR 的问题定义

### 4.1 继承什么，舍弃什么

继承原报告的三个判断：

1. 记忆是受资源约束的因果策略，不是一种固定结构；
2. 应区分历史信息是否保存、是否可取回、是否能被指定模型使用；
3. 任务族和 side information 共同决定哪些历史差异必须保留。

不把下列内容作为 FQR 的前提：

- 潜记忆；
- 世界模型；
- 图、树或固定槽位；
- 必须先完整重建世界再压缩；
- 必须多轮检索；
- writer 必须看不完整的旧记忆。

这使 FQR 成为一种 writer 目标，可以嵌入 SelectStream、FluxMem、视觉 KV、事件表或混合 memory，而不是和每种载体竞争。

### 4.2 严格任务协议

令视频前缀为

$$
H_T=(O_1,\ldots,O_T),
$$

side information 为

$$
S_T=(S_1,\ldots,S_T),
$$

其中可以包括原生 ASR、OCR、时间戳和低成本传感器状态。测试问题 $Q$ 在 $T$ 时刻之后才对系统可见。因果 writer 满足

$$
M_t=W_\phi(M_{t-1},O_t,S_t),\qquad t\leq T,
$$

且

$$
Q\notin \operatorname{inputs}(W_\phi).
$$

主协议要求：

1. $W_\phi$ 只能访问当前及过去输入；
2. $M_T$ 的总持久字节不超过 $B$，与视频长度无关；
3. 同一视频 checkpoint 只构造一个冻结的 $M_T$，供该 checkpoint 的全部问题共享；
4. 主结果禁止回放原视频，也不允许把全分辨率帧藏在未计费 CPU 冷存储；
5. reader 在问题出现后可以 query-aware，但只能读 $M_T$、$S_T$ 和允许的最近窗口；
6. caption、轨迹、对象表或生成文本若持久保存，必须计入存储；其生成成本单独报告；
7. 训练问题可以产生监督，但测试问题及其改写、答案和证据时间戳不得泄漏给 writer。

### 4.3 Grounded task loss

每个未来任务实例写为

$$
T=(Q,Y,E,G),
$$

其中 $Y$ 是答案，$E$ 是时间、对象或时空证据，$G$ 是任务与证据组，例如题型、证据延迟、证据片段数、视觉依赖度和 side-info 可靠度。

定义

$$
\ell_{\mathrm{grd}}
=
\ell_{\mathrm{ans}}
+
\lambda_{\mathrm{gnd}}\ell_{\mathrm{evidence}}.
$$

只在没有 grounding 标注的数据上令 $\lambda_{\mathrm{gnd}}=0$，但这类数据不能单独支撑主结论。

给定 consumer $F_\theta$ 和 reader $R_\psi$，某个任务分布 $P$ 下的风险是

$$
\mathcal R_P(M,S)
=
\mathbb E_{(Q,Y,E,G)\sim P(\cdot\mid H,S)}
\left[
\ell_{\mathrm{grd}}
\left(
F_\theta\!\left(Q,R_\psi(M,Q,S),S\right),
Y,E
\right)
\right].
$$

### 4.4 未来分布与 ambiguity set

“未来问题未知”不等于“对任意问题都保证”。需要在训练前声明一个可审计的分布集合 $\mathcal U$，例如允许：

- 题型先验变化；
- 组内证据稀有度和延迟变化；
- 单证据与多证据比例变化；
- ASR/OCR 缺失、噪声或与视觉冲突；
- 已知任务原语的新组合；
- 有限的视频域迁移。

稳健风险定义为

$$
\mathcal R_{\mathcal U}(M,S)
=
\sup_{P\in\mathcal U}
\mathcal R_P(M,S).
$$

实现上不必直接求解任意分布 supremum。第一版可以用预先定义的层次组、worst-group loss 与 CVaR 近似：

$$
\widehat{\mathcal R}_{\mathrm{rob}}
=
\alpha\max_{g\in\mathcal G}\widehat{\mathcal R}_g
+
(1-\alpha)\operatorname{CVaR}_{\tau}
\left(
\ell_{\mathrm{grd}}
\right).
$$

这里的层次性很重要：只按“计数、动作、空间”等题型分组，会掩盖每个题型内部的长延迟、低频实体和 side corruption。

### 4.5 条件写入价值：FQR 的核心定义

候选事件 $i$ 可以有多个码率或表示选项

$$
c_{i,b}=\operatorname{Codec}_b(O_{a_i:b_i},S),
$$

其中 $b$ 表示码率或保真等级。先对任意 $P\in\mathcal U$ 定义分布条件写入价值：

$$
v^P_{i,b}(M,S)
=
\mathcal R_P(M,S)
-
\mathcal R_P(M\oplus c_{i,b},S).
$$

给定当前记忆 $M$ 和侧信息 $S$，主目标使用候选对 minimax frontier 的改善：

$$
v^{\mathrm{rob}}_{i,b}(M,S)
=
\mathcal R_{\mathcal U}(M,S)
-
\mathcal R_{\mathcal U}(M\oplus c_{i,b},S).
$$

这里两个最坏风险可能由不同的 $P$ 达到；这个量回答“候选是否降低当前 minimax 目标”。另定义更保守的 uniform-safe value：

$$
v^{\mathrm{safe}}_{i,b}(M,S)
=
\inf_{P\in\mathcal U}
v^P_{i,b}(M,S).
$$

它要求候选在 $\mathcal U$ 的每个允许分布上都不劣。主方法优化 $v^{\mathrm{rob}}$，把 $v^{\mathrm{safe}}$ 作为强保守消融，避免混淆“改善最坏风险”和“对所有分布逐点改善”。

$M\oplus c_{i,b}$ 表示把候选以码率 $b$ 加入当前记忆并执行必要的重排、替换或合并。单位字节价值为

$$
u_{i,b}(M,S)
=
\frac{
v^{\mathrm{rob}}_{i,b}(M,S)
}{
\operatorname{Bytes}(c_{i,b})
}.
$$

这个定义有四个关键性质：

1. $v$ 依赖当前 $M$，所以同一个片段在空记忆和已有相似证据的记忆中价值不同；
2. $v$ 依赖 $S$，所以 ASR 已解释的信息与纯视觉不可恢复细节价值不同；
3. $v$ 依赖 consumer 和接口，信息存在但模型不会用时，操作价值仍可能低；
4. $v$ 可以为负，因为加入相关但冲突或冗长的证据可能使回答更差。

“条件不可替代”是这个定义的直观语言：候选不是因为本身罕见而值得保存，而是因为在当前系统可获得的其余信息中没有低成本替代物。

### 4.6 组向量价值，而不是过早压成一个标量

对每个组 $g$，先定义

$$
v^g_{i,b}(M,S)
=
\mathbb E_{(Q,Y,E)\sim P_g}
\left[
\ell_{\mathrm{grd}}(M,S;Q,Y,E)
-
\ell_{\mathrm{grd}}(M\oplus c_{i,b},S;Q,Y,E)
\right].
$$

训练 critic 预测向量

$$
\mathbf v_{i,b}
=
\left(v^1_{i,b},\ldots,v^{|\mathcal G|}_{i,b}\right),
$$

再由部署时声明的风险偏好聚合。这样做比直接拟合一个平均 scalar 有三个优势：

- 可以在不重训表示的情况下改变 group 权重；
- 可以检查收益来自哪个任务与证据组；
- 可以区分平均性能提升和对稀有组的真实保护。

### 4.7 组合价值

若任务需要证据集合 $\{i,j\}$，单条 add-one 标签可能低估二者。对采样 coalition $C$，定义

$$
\Delta_{i,b}(C,S;g)
=
\mathcal R_g(C,S)
-
\mathcal R_g(C\cup\{c_{i,b}\},S).
$$

训练时从真实 online policy 产生的记忆状态中采样多个 $C$，而不是只在空集合上测一次。对少量高疑似互补对，再估计

$$
\operatorname{Syn}_{i,j}(C)
=
\Delta_{\{i,j\}}(C)
-
\Delta_i(C)
-
\Delta_j(C).
$$

这只是 sampled coalition marginality，不应宣称为精确 Shapley value。完整 Shapley 计算昂贵，而且单点 Shapley 排名本身并不保证组合预算选择最优。

### 4.8 Pre-query frontier 的正确地位

保留原报告中的 pre-query rate-distortion frontier，但把它降为测量工具而非标题级新颖性：

$$
D^*_{\mathrm{pre}}(B;\mathcal U,F_\theta)
=
\inf_{
\substack{
W\ \mathrm{causal,\ query\text{-}hidden}\\
\operatorname{Bytes}(M_T)\leq B
}
}
\sup_{P\in\mathcal U}
\mathbb E_P
\left[
\ell_{\mathrm{grd}}(M_T)
-
\ell_{\mathrm{grd}}(H_T)
\right].
$$

其中 $\ell_{\mathrm{grd}}(H_T)$ 表示可访问完整历史或足够强证据 oracle 时的参考损失。这个 frontier 用于回答“固定预算下不可避免地损失多少”，不能被描述成 FQR 首次提出通用 memory rate-distortion，因为 DeMem 已经占据了决策率失真的一般框架。

---

## 5. FQR-Mem v3：Conditional Value Writer

### 5.1 设计原则：固定强骨干，只学习写入价值

FQR-Mem v3 不再把新图、新层次或新注入模块作为中心。系统拆成六个可替换部分：

$$
\text{stream}
\rightarrow
\text{candidate generator}
\rightarrow
\text{codec menu}
\rightarrow
\text{value critic}
\rightarrow
\text{budget allocator}
\rightarrow
\text{standard reader}.
$$

论文主实验固定 candidate generator、codec、reader 和 consumer，只比较 writer 的保存目标。这样才能回答：

> 性能提升究竟来自条件任务价值，还是来自更强的视频编码器、更大的候选池和更复杂的 reader？

首选做法是在至少一个强现有骨干上替换其 admission / consolidation score：

- SelectStream 骨干：保留事件切分、latent node 和 graph reader，把固定 priority merge 换成 FQR value；
- FluxMem 或 SAVEMem 骨干：保留三层 token 表示和 query-time retrieval，把 visual statistics 或 pseudo-question MaxSim 换成 FQR value；
- 第二表示验证：在 event card 或视觉 KV 上复用同一价值目标。

只要一个骨干开源且可稳定复现，就可作为主受控实验；第二个骨干用于证明目标可迁移。最终选择应以代码、数据许可和同机复现结果为准，当前不锁死。

### 5.2 Query-hidden 候选生成

视频流被因果地切成候选事件

$$
e_i=(O_{a_i:b_i},t_i,\eta_i),
$$

其中 $\eta_i$ 包含轻量级变化量、对象、运动和边界统计。候选生成器可以采用固定窗口、scene boundary 或 SelectStream 的 surprise boundary，但在所有 writer 间必须一致。

候选生成器只负责提出可能的写入单位，不决定其长期价值。否则，若任务关键帧在候选阶段已经被 surprise filter 删除，再强的 value critic 也无法恢复它。为此需报告：

- 候选池对 gold evidence 的 recall；
- 候选数量与在线成本；
- writer 前的候选上限造成的 oracle ceiling。

第一版宜采用偏高召回的候选生成器，把真正的预算决策留给 value writer。

### 5.3 条件 codec menu

每个事件不只有“保留或删除”，而有多个码率选项：

$$
\mathcal C(e_i)
=
\left\{
c_{i,0},c_{i,1},\ldots,c_{i,L}
\right\},
$$

其中 $c_{i,0}$ 表示不保留。其余选项可包括：

- 低码率 key：时间、实体、事件类型和 provenance；
- 中码率 payload：少量视觉 token、关键 crop 或压缩帧；
- 高码率 payload：更密时间采样、更高空间分辨率或局部轨迹；
- 可选文本 trace：只在确实比视觉表示更节省且生成成本被计费时使用。

每项至少携带

$$
\left(
\text{key},
\text{payload},
\text{time},
\text{provenance},
\text{reliability},
\text{rate}
\right).
$$

codec 本身不是新颖性。它的作用是让 critic 学会：

> 一个事件是否值得保存，以及值得以多少字节保存。

side information 只作为条件输入，不应被复制进视觉 payload。若 ASR 已准确说出“John 把红杯递给 Mary”，仍可能需要少量视觉 token 保存说话者身份是否对应、杯子颜色是否与 ASR 冲突、动作是否真正发生等不可由文本可靠恢复的内容。

### 5.4 离线 Counterfactual Value Teacher

训练阶段允许访问训练问题、答案和 evidence 标注。Teacher 不直接作为测试 writer，而用于生成监督。

对训练视频的一个真实 online memory coalition $C$、候选 $c_{i,b}$ 和组 $g$，运行完全相同的 consumer 与 reader，比较：

$$
L^{-}
=
\ell_{\mathrm{grd}}
\left(
F_\theta(Q,R_\psi(C,Q,S),S),
Y,E
\right),
$$

$$
L^{+}_{i,b}
=
\ell_{\mathrm{grd}}
\left(
F_\theta(Q,R_\psi(C\cup\{c_{i,b}\},Q,S),S),
Y,E
\right).
$$

干预标签为

$$
\widehat{\Delta}_{i,b}
=
L^{-}-L^{+}_{i,b}.
$$

这里的“反事实”是**对模型输入记忆的受控干预效应**：同一视频、同一问题、同一模型、同一 reader、同一解码和相同预算条件下，只改变候选是否可用。它不是对真实世界因果效应的识别；论文应明确使用 operational intervention 或 controlled memory intervention，避免不必要的因果过度声称。

Teacher 的具体标签过程：

1. 运行当前或历史 writer，收集实际会出现的 memory state，而不是只构造随机集合；
2. 按任务组、证据延迟、片段数、视觉依赖度和 side quality 分层采样训练问题；
3. 对候选的多个 codec rate 做 paired with/without evaluation；
4. 对高疑似互补事件采样二元或小规模 coalition；
5. 记录 answer delta、evidence delta、负效用和不确定性；
6. 把标签按视频划分保存，训练 critic 时不得跨越 train/validation/test 视频边界。

为控制离线成本，采用两阶段 teacher：

1. **宽覆盖廉价标签。** 使用 gold evidence overlap、冻结 reader score 和答案 log-likelihood 产生高召回候选对；
2. **稀疏精确干预。** 只对不确定、相互接近或代表关键组的候选运行完整 consumer with/without；
3. **主动补标。** critic 训练后优先补充高方差、排序冲突和稀有组样本。

主结果必须报告 teacher 总调用量与 GPU 小时。离线监督可以昂贵，但不能把它伪装成免费的系统收益。

### 5.5 Conditional Value Critic

critic 接收：

$$
\left(
h(e_i),
h(M),
h(S),
b,
\xi_i
\right),
$$

其中：

- $h(e_i)$：候选视觉与事件表示；
- $h(M)$：当前记忆的低成本摘要，包括实体覆盖、时间覆盖、已有相似 payload 和剩余预算；
- $h(S)$：ASR/OCR 的覆盖、置信度和冲突特征；
- $b$：候选码率；
- $\xi_i$：surprise、semantic novelty、pseudo-question MaxSim 等代理特征。

把现有启发式作为输入而不是答案，允许模型在适合的组上使用它们，同时学习它们何时失效。

输出为

$$
\left(
\widehat{\mathbf v}_{i,b},
\widehat{\boldsymbol \sigma}_{i,b}
\right),
$$

分别表示逐组价值和估计不确定性。训练损失可写为

$$
\mathcal L_{\mathrm{critic}}
=
\mathcal L_{\mathrm{reg}}
+
\beta_{\mathrm{rank}}\mathcal L_{\mathrm{rank}}
+
\beta_{\mathrm{sign}}\mathcal L_{\mathrm{sign}}
+
\beta_{\mathrm{cal}}\mathcal L_{\mathrm{cal}}.
$$

四项分别负责：

- 回归 paired delta；
- 在同一 memory state 内正确排序候选；
- 区分正、零、负效用；
- 让预测方差与实际误差校准。

只做标量 MSE 容易被大量接近零的候选主导，因此 pairwise ranking、sign classification 和 group-balanced sampling 是必要的。

### 5.6 Robust Budget Allocator

在时刻 $t$，动作集合包括：

- skip；
- 以某个码率插入新候选；
- 用新候选替换一个旧条目；
- 降低一个或多个旧条目的码率；
- 合并具有高可替代性的旧条目。

令当前逐组风险估计为 $\widehat{\mathbf r}_t$，动作 $a$ 对应的预测逐组净价值为 $\widehat{\mathbf v}(a)$。定义风险聚合器

$$
\rho_{\mathcal W}(\mathbf r)
=
\sup_{\mathbf w\in\mathcal W}
\mathbf w^\top\mathbf r.
$$

在线选择可写成

$$
a_t^*
=
\arg\max_{a\in\mathcal A_t}
\left[
\rho_{\mathcal W}(\widehat{\mathbf r}_t)
-
\rho_{\mathcal W}
\left(
\widehat{\mathbf r}_t-\widehat{\mathbf v}(a)
\right)
-
\kappa\,
\widehat\sigma_\rho(a)
-
\lambda\,\operatorname{Cost}(a)
\right],
$$

满足

$$
\operatorname{Bytes}(M_t)\leq B.
$$

$\mathcal W$ 是允许的组权重集合，$\widehat\sigma_\rho(a)$ 是聚合后价值的不确定性。$\widehat{\mathbf r}_t$ 由只读取 $h(M_t)$ 与 $h(S_t)$ 的轻量 risk head 估计，或在第一版中直接采用训练集上冻结的组风险与对偶权重；它不能读取测试问题。这个目标直接近似“动作前后的最坏风险之差”。若要测试 uniform-safe 策略，则把方括号中的风险下降项替换为 $\inf_{\mathbf w\in\mathcal W}\mathbf w^\top\widehat{\mathbf v}(a)$。第一版不需要求解复杂在线组合优化，可采用：

1. value-per-byte 预筛；
2. 在少量受影响条目上枚举 insert / replace / downgrade；
3. 用组对偶权重或 CVaR 权重更新在线优先级；
4. 定期执行局部 consolidation。

关键不是声称全局最优，而是保证每个保留动作都由同一个可审计的稳健条件价值近似驱动。

### 5.7 Reader 与 consumer

主结果使用一个固定、尽量简单的 query-aware reader：

$$
Z=R_\psi(M_T,Q,S),
\qquad
\widehat Y,\widehat E=F_\theta(Q,Z,S).
$$

建议先做单轮读取，原因是：

- 多轮 agentic retrieval 已由 OASIS、LongVideo-R1、LongVT、REVEAL 等大量覆盖；
- 多轮控制会把 writer 价值和 reader 能力混在一起；
- 单轮条件下更容易测出“写入时是否保留了正确证据”。

多轮读取可作为扩展实验：若单轮 reader 已到达明显瓶颈，再测试价值记忆是否也能提升 iterative evidence acquisition。它不应成为第一版的必要条件。

### 5.8 方法中真正新的与仅为工程支撑的部分

| 组件 | 论文地位 |
|---|---|
| 事件切分、latent graph、KV 或 event card | 复用骨干，不主张新颖 |
| 多码率 codec | 必要工程支撑，除非产生独立显著发现，否则不主张核心创新 |
| 训练期 paired intervention | 与 CMI/CICL 有思想近邻，单独不新 |
| 把 intervention label 蒸馏为 query-hidden causal writer | 核心方法差异 |
| 条件于当前 $M$ 与 $S$ 的逐组 grounded value | 核心目标差异 |
| future ambiguity set 下的 per-byte robust allocation | 核心优化差异 |
| memory deletion / swap audit | 必要验证，因 WorldMemArena 与 StreamFlow 已有近邻，不能单独当贡献 |

---

## 6. 用 oracle ladder 解耦失败，而不是依赖“神奇 oracle”

这里的 oracle 只是一个**拥有额外信息或额外能力的不可部署对照组**，用来定位上限与失败层，不是方法的一部分。

建议按以下顺序设置：

| 层级 | 额外特权 | 回答的问题 |
|---|---|---|
| O0：Full-history consumer | 问题到达后可访问完整视频 | backbone 在此任务上是否本来就会做 |
| O1：Gold-evidence consumer | 直接提供人工标注证据片段 | consumer 能否使用正确证据，grounding 接口是否有效 |
| O2：Post-query memory oracle | 看到 $Q$ 后从完整候选池按真实 task loss 选固定预算证据 | 如果 writer 提前知道问题，预算是否足够 |
| O3：Pre-query distribution oracle | 看不到测试 $Q$，但可用训练任务分布和昂贵 coalition search 为整个 query family 构造一个 snapshot | query-hidden 协议本身造成的不可避免差距 |
| O4：FQR learned writer | 只用在线候选、当前 $M$、$S$ 和蒸馏 critic | 学习与在线近似损失多少 |
| O5：heuristic writer | surprise、novelty、MaxSim 或固定 priority | FQR 价值学习相对代理量带来多少 |

典型解释：

- O0 很差：不是 memory paper 能解决的，consumer 或数据本身有问题；
- O0 好、O1 差：证据接口或模型使用失败；
- O1 好、O2 差：字节预算或 codec 不足；
- O2 好、O3 差：问题出现前不可避免的信息需求冲突很大；
- O3 好、O4 差：value critic 或 online allocator 不够好；
- O4 与 O5 接近：新目标没有转化为实际优势。

这套 ladder 的价值是诊断，不是新颖性。WorldMemArena 已经说明 write、store、retrieve、use 必须分开评估。

---

## 7. 新颖性边界：必须同时满足的交叉条件

图例：✓ 表示明确满足；△ 表示部分满足或只在分析中满足；— 表示不属于该工作设置。

| 方法 | 写入时真实 $Q$ 隐藏 | 不可逆流式写入 | 价值条件于当前 $M,S$ | 直接任务损失 / 干预信号 | 未来任务族 | 显式 tail shift | 视觉 grounding | 固定物理预算 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| SURGE / FluxMem | ✓ | ✓ | △ | — | — | — | — | △ |
| CausalMem | ✓ | ✓ | 仅 $M$ 的语义基 | — | 通用未来语义 | — | — | ✓ |
| SelectStream | ✓ | ✓ | △ | 训练有 answer / retrieval loss，但 consolidation 是固定 priority | △ | — | △ | ✓ |
| SAVEMem | ✓ | ✓ | △ | pseudo-question MaxSim | 固定伪问题族 | — | — | token budget |
| StreamMind | ✓ | ✓ | 结构化旧记忆 | — | 隐式开放问题 | — | timestamp evidence | 未做严格同字节主张 |
| StreamFlow | ✓ | ✓ | △ | 干预用于使用分析 | — | — | △ | latent capacity |
| DeMem | 否，encoder 可见 $Q$ | 否，answer-time encoding | 相对于 query-selected state | decision distortion | 每个当前 query fiber | 有理论 worst case | 文本任务 | $K$ states / answer budget |
| Learning What to Remember | ✓，blind forgetting | △，主实验只隔离 keep/drop | 否，item-wise factors | gold-evidence retention proxy | LongMemEval workload | — | 文本 gold turn | keep fraction |
| CMI | 否 | 否，bank 已存在 | 相对于当前请求与候选 | with / without / perturbed | 当前任务 | harmful memory robustness | 文本 | top-$k$ |
| CICL | 否 | 否，候选上下文已存在 | 相对于当前任务 | counterfactual-inspired utility | 当前任务 | negative transfer | 文本/代码 | token budget |
| **FQR-Mem v3** | **✓** | **✓** | **✓** | **训练期 paired grounded loss，测试期蒸馏 writer** | **声明的未来任务族** | **层次组与 CVaR** | **答案 + evidence** | **总持久字节 + 计算** |

FQR 的 novelty 是最后一行的**联合问题与方法**，而不是其中任意单列。

### 7.1 可以写进论文的贡献

若实验支持，贡献应限制为：

1. **现象贡献。** 首次在严格 query-hidden、matched-representation 的流式视频设置中系统量化 retention proxy 与未来 grounded conditional value 的错配。
2. **目标贡献。** 提出条件于当前记忆与 side information、面向未来任务 ambiguity set 的逐组 per-byte write value。
3. **方法贡献。** 用训练期 controlled memory interventions 蒸馏 query-free value critic，并以该 critic 驱动固定预算 online admission、replacement 和 rate allocation。
4. **验证贡献。** 在相同 candidate、codec、reader、consumer 和物理预算下，与 surprise、semantic residual、pseudo-question prior 和 priority consolidation 对比，并用 grounding 与干预审计证明收益来自正确视觉证据。

第 4 点是实验严谨性，不应包装成完全独立的算法创新。

### 7.2 不能写的贡献

- 首个 query-hidden streaming memory；
- 首个 task-aware visual memory；
- 首个在 future query 未知时学习 retention value；
- 首个 counterfactual memory；
- 首个 decision-centric memory formalization；
- 首个 fixed-budget 或 hierarchical video memory；
- 对任意未知未来问题都鲁棒；
- 理论上识别真实世界因果效应；
- 在不声明 consumer 与接口时定义了普适“完美记忆”。

---

## 8. CVPR 级实验设计

### 8.1 五个可证伪假设

#### H1：代理分数错配

在相同候选与 codec 下，surprise、feature change、semantic novelty、pseudo-question MaxSim 和 SelectStream priority 与 oracle coalition marginal value 的排序相关性显著低于条件价值 critic。

#### H2：条件性必要

去掉当前 $M$ 或 $S$ 后，value ranking、evidence recall 和 grounded regret 显著退化，尤其在 side-redundant、side-conflict 和 repeated-event 子集。

#### H3：尾部稳健性必要

平均 ERM value writer 可能有相近平均准确率，但在稀有题型、长 evidence gap、多证据与 side corruption 下 worse；逐组 robust value 降低 worst-group grounded regret。

#### H4：记忆被实际使用

删除 FQR 最高价值条目造成的性能下降显著大于 matched random deletion；把它替换为同码率、同时间位置但错误语义的证据会导致可预测的答案或 grounding 变化。

#### H5：价值目标可迁移

在至少两种 memory representation 或两个 consumer 上，FQR objective 相对各自 proxy writer 都有一致方向的收益；若只在自定义 latent 上有效，主张应降为特定架构优化。

### 8.2 数据与任务组合

建议分成三层，最终采用前需确认数据、代码和许可可用性：

| 层 | 候选数据 | 用途 |
|---|---|---|
| 主长时流评估 | StreamArena；或可严格重放的 OVO-Bench / StreamingBench 子集 | query-after-write、长 evidence gap、多时刻 snapshot |
| grounded 主评估 | EG-VQA、E-VQA、VideoZeroBench | 答案与时间/空间证据联合损失 |
| 组合与诊断 | MMR-V；少量可控 CLEVRER 或合成事件链 | 多证据 synergy、干扰、因果与时间组合 |

OVO-Bench、StreamingBench 中很多题可能被最近窗口或语言先验解决，因此只报告总体分数不够。必须建立预先定义的 diagnostic slices：

- high-surprise but irrelevant；
- low-surprise but task-critical；
- pseudo-query similar but side-redundant；
- visually subtle and text-unrecoverable；
- standalone-low but coalition-critical；
- rare task / long-delay；
- side-consistent 与 side-conflicting。

这些 slice 可以从 gold evidence、视频变化量、ASR/OCR 覆盖和人工小规模审计中构造。切分规则必须只用训练集确定，再冻结应用于测试集。

### 8.3 先做现象实验，不先训练完整系统

第一阶段只回答：

> 强 writer 的代理分数是否真的和条件未来价值错配？

固定：

- 同一视频 candidate pool；
- 同一 codec 和 consumer；
- 同一当前 memory coalition；
- 同一 query family；
- 同一字节预算。

对候选计算 sampled intervention label，再比较：

- uniform / FIFO；
- recency；
- feature change；
- SURGE-style surprise；
- semantic diversity；
- CausalMem-style residual；
- SAVEMem pseudo-question MaxSim；
- SelectStream priority；
- Learning What to Remember-style learned blind multi-factor value；
- 不条件于 $M,S$ 的平均 learned value；
- FQR conditional group value。

指标包括：

$$
\operatorname{Spearman}(\widehat u,u^*),
\qquad
\operatorname{Kendall}\text{-}\tau,
\qquad
\operatorname{nDCG}@K.
$$

定义预算价值恢复率：

$$
\operatorname{VR}@B
=
\frac{
\mathcal U(\widehat A_B)-\mathcal U(\varnothing)
}{
\mathcal U(A_B^*)-\mathcal U(\varnothing)
},
$$

其中 $\widehat A_B$ 是某个 writer 在预算 $B$ 下选出的集合，$A_B^*$ 是在受控候选池上用昂贵 search 得到的近似 oracle 集合，$\mathcal U$ 是负 grounded risk。由于组合优化难，必须写成“近似 oracle”，并报告搜索方法。

还需报告：

- evidence bundle recall；
- 条件值正负号准确率；
- 逐组 value calibration；
- side-only、visual-only、joint 三种输入下的价值变化；
- 候选 oracle ceiling。

**早停规则：** 若条件 oracle value 相对最强 proxy 在至少两个数据来源和多个预算上没有稳定更高的 VR、grounding 或 tail gain，就不应继续构建复杂 FQR 系统。

### 8.4 全系统受控比较

主比较分两层。

#### 层 A：目标函数隔离

同一个 writer backbone 内只替换保存分数：

1. original priority；
2. surprise；
3. semantic residual；
4. pseudo-question prior；
5. learned blind multi-factor value；
6. average ERM value；
7. FQR conditional value；
8. FQR robust group value。

其余 candidate、codec、reader、consumer、训练数据和 online compute 尽量相同。这张表决定论文是否成立。

#### 层 B：系统级外部比较

与完整系统比较：

- recent-window / FIFO；
- StreamingVLM 或简单 recent visual + long text；
- FluxMem；
- CausalMem；
- SelectStream；
- SAVEMem；
- StreamFlow；
- 可复现时的 StreamForest、D-HSM、StreamMind；
- query-known MARC、QViC-MF、LongVideo-R1、LongVT、ReMem 作为 privileged oracle，单独分栏。

系统级比较不能替代层 A，因为不同 backbone、帧率、文本生成器和存储口径会混杂结论。

### 8.5 防止 query leakage

必须执行：

1. 以视频为单位拆分 train / validation / test；
2. 测试视频的全部问题共享一次性构造的 memory snapshot；
3. writer 输入日志中不出现真实问题、答案、证据时间戳或其 embedding；
4. 伪问题、task group 和 ambiguity set 在测试前冻结；
5. 超参数不根据 test worst group 调整；
6. 训练 teacher 产生的 query-conditioned label 只用于训练视频；
7. 把 query-known selector 明确标为 oracle，不能进入公平主排名。

一个很有说服力的自动审计是：对同一视频随机打乱问题顺序或替换问题集合，writer 产生的 $M_T$ 哈希必须完全相同。

### 8.6 Shift 设计

不声称任意 OOD，只验证预声明变化：

| Shift | 构造 | 检验 |
|---|---|---|
| task-prior shift | 改变动作、计数、OCR、空间、身份等组权重 | 固定 pseudo bank 和 ERM writer 是否牺牲低频组 |
| evidence-delay shift | 测试集提高长时间间隔比例 | recency / read-count priority 是否失效 |
| bundle shift | 增加需要 2 个以上分散片段的题 | 单条 top-$k$ 与 coalition labels 的差异 |
| side-quality shift | ASR/OCR dropout、噪声或受控冲突 | 条件 codec 是否自适应保留视觉 payload |
| composition shift | 已知实体、动作、关系的新组合 | task primitive prior 是否能有限组合泛化 |
| limited domain shift | 在不同视频域间训练与测试 | 检查视觉 proxy 与 critic 是否过拟合场景统计 |

至少同时报告 in-distribution、单因素 shift 和两因素组合 shift。层次 ambiguity set 的意义正是在组间与组内都变化时不把失败藏在平均数中。

### 8.7 主指标与资源口径

主指标建议为 matched-byte 下的 worst-group grounded regret：

$$
\operatorname{Regret}_{g}
=
\mathcal R_g(M_{\mathrm{method}},S)
-
\mathcal R_g(M_{\mathrm{postQ\ oracle}},S),
$$

$$
\operatorname{WGRegret}
=
\max_{g\in\mathcal G}
\operatorname{Regret}_{g}.
$$

同时报告：

- 平均 QA accuracy 或 open-ended judge score；
- temporal / spatial evidence F1；
- joint answer-and-evidence accuracy；
- CVaR；
- evidence bundle recall；
- 活动字节与总持久字节；
- 每分钟视频的写入 FLOPs、延迟和能耗代理；
- query-time read FLOPs、TTFT 和峰值显存；
- 原视频 I/O；
- caption / OCR / ASR 的生成与存储成本；
- 至少 3 个随机种子、bootstrap 置信区间和 paired significance。

不同表示的 token 数不可直接比较，主资源轴必须是实际字节。视觉 token、文本 token、KV、latent node 和 CPU 冷存储分别列出。

### 8.8 关键消融

| 消融 | 要回答的问题 |
|---|---|
| 去掉 $h(M)$ | 价值是否真的相对于已有记忆，而非候选自身显著性 |
| 去掉 $h(S)$ | 是否学到了 side redundancy 与视觉互补 |
| scalar ERM 替代 group vector | tail gain 是否来自鲁棒目标 |
| 独立标签替代 coalition labels | 多证据任务是否需要组合监督 |
| 固定单码率 | 自适应 fidelity 是否必要 |
| 去掉 negative labels | 是否会保存有干扰性的相关条目 |
| teacher 只用 evidence overlap | 完整 consumer intervention 是否提供额外信号 |
| oracle critic | 在线 allocator 与 value estimation 各损失多少 |
| oracle allocator | critic 正确时 greedy 预算分配还损失多少 |
| 两种 reader | 改进是否依赖特定 retrieval |
| 两种 consumer / backbone | 价值是否过度模型特定 |

### 8.9 写入—读取—使用干预

至少做四种 matched intervention：

1. **Top-value deletion**：删除最高预测价值条目；
2. **Random deletion**：删除相同字节、相同时间分布的随机条目；
3. **Semantic swap**：替换为同码率、同题面相似但来自其他视频的条目；
4. **Side corruption**：只改变 ASR/OCR 的可靠性，检查 visual retention 是否按预期变化。

若 FQR 真在保存不可替代证据，应观察到：

$$
\Delta_{\mathrm{top\ delete}}
>
\Delta_{\mathrm{matched\ random}},
$$

且 top-value 条目的删除首先破坏其对应组和 evidence grounding，而不是只让输出文字略有变化。

StreamFlow 已使用 matched / shuffled memory 干预验证视觉使用，因此 FQR 的差异不是“也做一次 swap”，而是：

- 同一干预信号用于训练 writer；
- 预测的 value 与实际 deletion effect 校准；
- 作用发生在 query-hidden retention，而非 query-time injection 分析。

---

## 9. 理论只做支撑，不抢论文主线

CVPR 论文不需要建立一个覆盖所有 AI memory 的宏大理论。三个小结论足以支撑方法。

### 9.1 条件冗余意味着语义价值为零

若在理想 decoder 下

$$
(Y,E)
\perp
c_{i,b}
\mid
(M,Q,S),
$$

则加入 $c_{i,b}$ 不改变 Bayes 最优预测，因而其语义条件价值为零。

这说明价值必须条件于 $M$ 和 $S$；仅凭候选自身特征无法判断是否可被替代。对受限 consumer，操作价值可能因提示、校准或模型偏差而非零，因此实验中还需区分 semantic oracle 和 operational consumer。

### 9.2 surprise 与任务价值之间没有普遍单调关系

可以构造两个事件：

- $e_1$ 对视频预测器非常意外，但其内容已被可靠 ASR 完整记录，未来任务也不询问其视觉细节；
- $e_2$ 视觉变化很小，却包含未来任务唯一需要读取的小标签。

则可能有

$$
\operatorname{Surprise}(e_1)
>
\operatorname{Surprise}(e_2),
$$

但

$$
v(e_1\mid M,S)
<
v(e_2\mid M,S).
$$

没有关于任务分布、side information 和 decoder 的额外假设，任何 intrinsic content score 都不能保证与任务条件价值同序。论文应把这作为反例和经验假设，而不是夸大为深奥定理。

### 9.3 单点价值不能完全解决组合预算

若只有 $e_i$ 与 $e_j$ 联合时才能回答一个问题，则

$$
\Delta_i(\varnothing)\approx 0,
\qquad
\Delta_j(\varnothing)\approx 0,
$$

但

$$
\Delta_{\{i,j\}}(\varnothing)>0.
$$

因此独立 top-$k$ value 仍会失败。这正当化 sampled coalitions 和 bundle-aware evaluation，也同时限制主张：第一版 FQR 只是对组合价值的可扩展近似，不是一般子集效用优化的精确解。

---

## 10. CVPR 论文叙事

### 10.1 推荐标题

首选：

> **Remember the Irreplaceable: Learning Conditional Write Value for Query-Hidden Streaming Video**

备选：

> **Future Questions Do Not Reward Surprise: Robust Conditional Value for Streaming Video Memory**

不建议继续使用：

> What Should a Video Remember Before the Question Is Known?

原因是它与 SelectStream 的标题及 SAVEMem 的协议过于接近，容易让审稿人在摘要第一段就判断为动机重复。

### 10.2 摘要逻辑

1. 流式视频必须在问题出现前压缩历史；
2. 近期方法按 surprise、semantic novelty、fixed pseudo-query 或手工 priority 保存内容；
3. 我们发现这些代理分数与未来 grounded conditional value 系统性错配，尤其在 side redundancy、多证据和稀有任务组；
4. 定义相对于当前 memory 与 side information 的逐组 grounded marginal write value；
5. 用训练期 controlled interventions 监督 critic，在测试时以 query-free critic 做 fixed-byte online allocation；
6. 在相同 backbone、candidate、codec 和 reader 下显著降低 worst-group grounded regret，并通过 deletion / swap 证明模型使用了正确证据。

### 10.3 CVPR 适配性

这个问题不是一般 LLM memory 的简单多模态版本。视频带来四个决定性差异：

- 历史输入速率高，写入必须在线且不可逆；
- 视觉细节常不能由文本 side information 重建；
- 证据具有空间、时间、身份与多片段组合结构；
- 资源必须以视觉 token、帧、KV、字节和实时吞吐共同约束。

论文中应让这些视觉特性贯穿数据切片、loss 和 intervention，而不是只把文本 agent memory 的 memory card 换成 frame embedding。

### 10.4 一张图讲清主线

建议 Figure 1 由三个横向面板构成：

1. **错配现象**：high-surprise redundant 与 low-surprise irreplaceable 两个视频事件；
2. **训练期 teacher**：同一 coalition 上 with / without candidate，产生 group-wise grounded delta；
3. **测试期 writer**：没有真实 query，只根据 candidate、当前 $M$、$S$ 和预测 value 做 insert / replace / rate allocation。

图中应显式画出训练 query 只连接 teacher label，不连接测试 writer，避免 query leakage 质疑。

### 10.5 最关键的主表

主表必须是同一强骨干内的 objective replacement，而不是跨系统排行榜：

| Writer objective | Avg QA | Evidence F1 | Joint | Worst-group regret | CVaR | Bytes | Write cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| original priority |  |  |  |  |  | matched |  |
| surprise |  |  |  |  |  | matched |  |
| semantic residual |  |  |  |  |  | matched |  |
| pseudo-question MaxSim |  |  |  |  |  | matched |  |
| learned blind multi-factor value |  |  |  |  |  | matched |  |
| average task value |  |  |  |  |  | matched |  |
| FQR conditional value |  |  |  |  |  | matched |  |
| FQR robust group value |  |  |  |  |  | matched |  |

如果这张表不成立，跨系统 SOTA 不能挽救论文的科学主张。

---

## 11. 预判审稿质疑

### 11.1 “这只是 learned SAVEMem”

有效反驳必须来自实验，而非文字：

- 同一骨干、同一伪问题特征；
- MaxSim 与 FQR objective 单独比较；
- 展示 pseudo-query similar 但 side-redundant、以及 low-MaxSim 但高 task delta 的反例；
- 表明收益来自条件于 $M,S$ 和 group-tail，而不是单纯把规则换成 MLP。

若没有这些结果，这个质疑成立。

### 11.2 “这只是 SelectStream 加 Group DRO”

需要证明：

- 不是只对最终 QA 做 Group DRO；
- supervision 单位是 candidate-by-memory-state 的 paired write delta；
- 当前 $M$、$S$ 和 codec rate 改变同一候选的标签；
- 用相同 SelectStream backbone 替换 consolidation objective 后仍有效；
- coalition 和负效用标签带来额外收益。

如果最终实现只是给 SelectStream loss 加一个 worst-group 权重，创新不足。

### 11.3 “CMI/CICL 已经做了反事实记忆价值”

正面承认，并明确协议差异：

- CMI/CICL 在当前任务已知时，从已存在的文本或文件 bank 中选择上下文；
- FQR 的候选若在流入时被删除，问题到达后已不存在；
- FQR 训练时用 query 估值，测试 writer 必须在所有未来 query 之间共享一个 snapshot；
- FQR 的 loss 包含视觉 grounding、side complementarity 与未来分布 shift。

还应加入 CMI-style current-query oracle，展示 post-query selection 的上界，而不是把它当作不存在。

### 11.4 “Learning What to Remember 已经学习了 blind retention value”

这是成立一半的质疑，必须把该工作列为直接 baseline，而非只放 related work。FQR 需要用受控实验显示四个额外因素缺一不可：

- item value 必须条件于当前 $M$，重复证据的边际值会随 coalition 改变；
- value 必须条件于多模态 $S$，同一视觉事件在 ASR 可靠与冲突时需要不同码率；
- supervision 是 answer-and-evidence task delta，而不只是 gold turn 是否幸存；
- group vector、coalition 与 physical byte allocation 在未来 shift 下产生额外收益。

可实现一个该方法的 video adaptation：用其多因子 scalar 对完全相同的事件候选排序。如果 FQR 只比 recency 或 uniform 强、却不能超过这个 learned blind-value baseline，新颖性不足。

### 11.5 “DeMem 已经形式化了同一个问题”

DeMem 的核心编码器明确为

$$
M_t=g_t(H_t,Q_t),
$$

即在回答时看当前 query 后把历史映射到 bounded state。FQR 的编码器是

$$
M_t=W(M_{t-1},O_t,S_t),
$$

测试写入期没有 $Q_t$，并且完整历史已不可回访。这个信息结构差异必须在 introduction、problem setup 和 oracle table 中重复清楚。

同时承认 DeMem 已占据 decision-centric rate-distortion 与 forgetting boundary，FQR 不宣称重做其一般理论。

### 11.6 “训练 teacher 看未来问题是作弊”

监督学习可以在训练时使用任务标签，关键是测试协议。需用以下证据回应：

- train/test 按视频拆分；
- 测试 writer 的输入追踪；
- 同视频不同测试问题共享 snapshot；
- 打乱或替换测试问题集合不改变 snapshot hash；
- 伪问题库、group 和 ambiguity set 在测试前冻结。

### 11.7 “未来分布根本不可知”

接受这一限制。论文只对预声明的 $\mathcal U$ 稳健，不对任意未来问题保证。报告 ID、每类 shift 和超出支持集的失败案例。对完全新任务，通用压缩或 raw archive 可能更合理。

### 11.8 “反事实标签不是真因果”

使用 controlled memory intervention 或 operational marginal effect。只有在同一实例、相同解码和仅改变 memory context 的条件下，才能把差异归因于该输入干预；不声称识别真实世界事件对答案的因果效应。

### 11.9 “收益来自更多离线计算或更强模型”

同时报告：

- teacher GPU 小时；
- online writer 延迟；
- matched consumer；
- matched candidate、codec 和 reader；
- oracle teacher 与轻量 critic 的 gap；
- 不同标签量的 scaling curve。

主张是把昂贵训练信号蒸馏到低成本部署，不是无成本提高。

### 11.10 “grounding 数据太少”

用有明确 evidence 的数据支撑主结论；没有 evidence 的大规模 QA 只做辅助。可把 temporal overlap、object grounding 和 answer loss 分开训练，不把自动 caption 当成 gold evidence。

---

## 12. 最小可行推进顺序

### 阶段 0：协议与数据审计

- 选择一个可复现强骨干；
- 确认候选 benchmark 的数据、标注与许可；
- 实现一次构建、多 query 共用 snapshot；
- 统一字节和计算记账；
- 复现至少 surprise、pseudo-question 与 original priority 三个 writer。

完成标志：同一骨干下的基线结果稳定，query leakage 审计通过。

### 阶段 1：Value Misalignment Study

- 从 100 至 300 个视频前缀和分层问题开始；
- 生成少量 coalition paired labels；
- 比较五类 proxy 与 oracle value；
- 审计四类核心反例；
- 计算 VR、grounded regret 和逐组相关性。

完成标志：至少两个数据来源、三个预算下出现可重复错配。

### 阶段 2：Conditional Critic

- 先做 scalar average value；
- 加入 $M$ 条件；
- 加入 $S$ 条件；
- 输出 group vector 与 uncertainty；
- 做 on-policy memory-state 补标。

完成标志：critic 在 held-out 视频上的 ranking、sign 和 calibration 明显优于 proxy。

### 阶段 3：Robust Online Allocation

- insert / skip；
- replacement；
- rate downgrade；
- group robust aggregation；
- 在线成本优化。

完成标志：相同 backbone 和物理字节下，FQR 在 ID 不显著退化，并降低多类 shift 的 worst-group grounded regret。

### 阶段 4：论文级闭环

- 第二 representation 或 consumer；
- top-delete、random-delete、swap 与 side corruption；
- oracle ladder；
- teacher cost scaling；
- 失败案例和支持集边界；
- 跨系统外部比较。

完成标志：主要结论不依赖单一数据集、单一表示或未计费资源。

---

## 13. 明确的继续与停止标准

### 13.1 值得继续

同时满足：

1. 最强 proxy 与 oracle conditional value 存在稳定排序错配；
2. $M,S$ 条件确实改变 writer 的选择并提高 grounded performance；
3. robust objective 的优势集中在预声明稀有组与 shift，而非随机波动；
4. 同 backbone objective replacement 有效；
5. top-value deletion 的实际影响与预测 value 校准；
6. 至少第二种表示或 consumer 上方向一致。

### 13.2 应收缩主张

出现以下任一情况：

- 只提高平均 QA，不提高 evidence grounding；
- 只对一个自定义 latent 骨干有效；
- 只在合成 shift 有效；
- 依赖极大的未披露 teacher 或 side-info 生成成本；
- 相对 SAVEMem / SelectStream 的受控替换没有收益；
- critic 只学会 evidence timestamp overlap，未学到条件互补。

此时可退化为“特定骨干的 task-aware retention objective”，但不足以支撑广义视觉记忆形式化。

### 13.3 应停止完整 FQR 系统

- proxy ranking 与 oracle conditional value 高度一致；
- oracle conditional selection 在 matched bytes 下也不能改善 tail grounded regret；
- post-query gold evidence oracle 仍然表现差，说明 consumer 根本不会利用证据；
- 候选生成器漏掉大量关键证据且无法在可接受在线成本内提高 recall；
- 未来任务组无法在训练前合理声明，导致所谓 robustness 只能事后挑 test slice。

这些负结果本身也应记录，而不是继续叠加结构掩盖。

---

## 14. 最终判断

### 14.1 动机强度

经本轮广泛调研后，宽泛动机的强度下降了，但收窄后的科学问题更强：

- “未知问题前需要记忆”已不新；
- “记忆应面向任务”也不新；
- “在 blind forgetting 中学习 retention value”也已有直接工作；
- “反事实价值”在文本 agent 中已有直接工作；
- **但“如何把未来任务的受控效用信号转化为 query-hidden 视觉流的条件写入策略”仍有清晰空白。**

这个空白同时有 SelectStream / SAVEMem 的直接系统基线、Learning What to Remember / DeMem / CMI / CICL 的理论与方法近邻、StreamArena 的现实需求证据，以及 WorldMemArena / grounded VQA 的诊断工具，适合形成一篇问题边界清楚的 CVPR 论文。

### 14.2 创新性强度

当前是**有潜力但必须靠 phenomenon-first 实验建立**，不能只靠形式化语言成立。

创新最强的版本不是：

> 我们设计了一个更复杂的视频记忆。

而是：

> **我们发现流式视频 writer 的保留代理与真实未来条件价值存在系统错配；我们用训练期受控干预学习候选相对于当前记忆与侧信息的逐组 grounded value，并把它蒸馏为测试时不见 query 的稳健写入策略。**

如果相同骨干上的 objective replacement、tail grounding 和 causal-use calibration 三项都成立，这一动机与方法足以支撑 CVPR 主线。若只做新 codec、图结构或普通 Group DRO，创新性不足。

### 14.3 最小论文核心

最终应把论文压缩到三个不可分割的贡献：

1. retention-value misalignment 的强实证；
2. robust conditional write value 的精确定义；
3. teacher-to-query-free-writer 的可复现实现与受控验证。

最小形式化继续作为统一语言与实验分解工具，FQR 则是其中最重要的可检验实例。这样既保留“从根本问题出发”的思想，又避免把一篇 CVPR 论文写成范围过大、难以证伪的 AI memory 总理论。

---

## 15. 主要一手文献索引

### 15.1 直接视频近邻

- [What Should a Streaming Video Model Remember? / SelectStream](https://arxiv.org/abs/2606.16353)
- [Semantic-Aware Adaptive Visual Memory for Streaming Video Understanding / SAVEMem](https://arxiv.org/abs/2605.07897)
- [Towards a Dynamic and Fixed-budget Memory Bank for Efficient Streaming Video Understanding / CausalMem](https://arxiv.org/abs/2606.25658)
- [StreamFlow: Dynamic Memory Flows for Streaming Video Understanding](https://arxiv.org/abs/2608.10949)
- [StreamArena: Toward Continuous, Interactive, and Long-Horizon Agentic Streaming Video Understanding](https://arxiv.org/abs/2608.05703)
- [Dynamic Hub-and-Spoke Memory for Streaming Video Understanding](https://arxiv.org/abs/2608.30294)
- [FluxMem: Adaptive Hierarchical Memory for Streaming Video Understanding](https://arxiv.org/abs/2603.02096)
- [SURGE: Surprise-Guided Token Reduction for Efficient Video Understanding with VLMs](https://proceedings.iclr.cc/paper_files/paper/2026/hash/07b92344686c19cf3ffc335a0f565406-Abstract-Conference.html)
- [Memento: Toward an All-Day Proactive Assistant for Ultra-Long Streaming Video](https://proceedings.iclr.cc/paper_files/paper/2026/hash/3b5f4587a0bdb81ecc6ce9d82320a5c2-Abstract-Conference.html)
- [StreamForest: Efficient Online Video Understanding with Persistent Event Memory](https://arxiv.org/abs/2509.24871)

### 15.2 决策价值与 agent memory

- [Remember the Decision, Not the Description: A Rate-Distortion Framework for Agent Memory](https://arxiv.org/abs/2605.10870)
- [Learning What to Remember: A Cognitively Grounded Multi-Factor Value Model for Agentic Memory](https://arxiv.org/abs/2606.12945)
- [Causal Intervention-Based Memory Selection for Long-Horizon LLM Agents](https://arxiv.org/abs/2605.17641)
- [Decision-Aware Memory Cards: Counterfactual-Inspired Context Selection and Compression for Tool-Using LLM Agents](https://arxiv.org/abs/2606.08151)
- [Choosing How to Remember: Adaptive Memory Structures for LLM Agents](https://arxiv.org/abs/2602.14038)
- [Remember When It Matters: Proactive Memory Agent for Long-Horizon Agents](https://arxiv.org/abs/2607.08716)
- [WorldMemArena: Evaluating Multimodal Agent Memory Through Action-World Interaction](https://arxiv.org/abs/2605.29341)

### 15.3 结构化、压缩与读取

- [OASIS: On-Demand Hierarchical Event Memory for Streaming Video Reasoning](https://arxiv.org/abs/2604.17052)
- [WorldMM: Dynamic Multimodal Memory Agent for Long Video Reasoning](https://arxiv.org/abs/2512.02425)
- [Hierarchical Long Video Understanding with Audiovisual Entity Cohesion and Agentic Search / HAVEN](https://arxiv.org/abs/2601.13719)
- [Scaling the Long Video Understanding of Multimodal Large Language Models via Visual Memory Mechanism / FlexMem](https://arxiv.org/abs/2603.29252)
- [MuKV: Multi-Grained KV Cache Compression for Long Streaming Video Question-Answering](https://arxiv.org/abs/2605.22269)
- [WeaveTime: Stream from Earlier Frames into Emergent Memory in VideoLLMs](https://arxiv.org/abs/2602.22142)
- [Vista: Scene-Aware Optimization for Streaming Video Question Answering under Post-Hoc Queries](https://arxiv.org/abs/2602.08448)
- [Reasoning with Memory: A Temporal Granularity-Adaptive Framework for Training-Free Long Video Understanding / ReMem](https://arxiv.org/abs/2607.24794)

### 15.4 Grounded 与长时评测

- [Evidence-Backed Video Question Answering / E-VQA](https://arxiv.org/abs/2607.11862)
- [EG-VQA: Benchmarking Verifiable Video Question Answering with Grounded Temporal Evidence](https://arxiv.org/abs/2606.24797)
- [VideoZeroBench: Probing the Limits of Video MLLMs with Spatio-Temporal Evidence Verification](https://arxiv.org/abs/2604.01569)
- [MMR-V: What's Left Unsaid? A Benchmark for Multimodal Deep Reasoning in Videos](https://proceedings.iclr.cc/paper_files/paper/2026/hash/6f1989abe9562c5cd306e070725fe0a3-Abstract-Conference.html)
- [RIVER: A Real-Time Interaction Benchmark for Video LLMs](https://proceedings.iclr.cc/paper_files/paper/2026/hash/1022661f3f43406065641f16ce25eafa-Abstract-Conference.html)

更完整的 2026 年逐篇事实、状态与原始 FQR 约束见 [FQR-Mem：2026 年相关文献证据表](../literature/fqr_mem_2026_literature_evidence.md)。
