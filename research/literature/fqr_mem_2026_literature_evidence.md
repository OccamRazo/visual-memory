# FQR-Mem：2026 年相关文献证据表

> 截止日期：2026-08-24
>
> 调研问题：在问题未知的连续视频写入阶段，如何在固定视觉记忆预算下，保留对未来问题最有条件增益、且对问题分布变化稳健的视觉证据？
>
> 对应方案：`FQR-Mem`（Future-Query-Robust Conditional Evidence Memory）

## 1. 范围与证据口径

用户所说的“2026 年之后”在当前日期不可能指 2027 年及以后，因此本文按“2026 年以来，截至 2026-08-24”执行。

“高影响力”不能用尚未成熟的引用数判断，本文采用两个可核验代理：

1. **A 类：2026 年 ICLR、CVPR、ECCV 正式接收或正式 proceedings 论文。** 共 24 篇，已经超过“至少 20 篇”的要求。个别论文在 2025 年先发 arXiv，但正式发表年份是 2026，已在表中明确标注。
2. **B 类：2026 年一手预印本。** 共 16 篇。它们与 FQR-Mem 的问题设定高度贴近，但尚不能被称为已经形成高学术影响，本文只把它们作为最新竞争态势与设计证据。

表格中的性能数字均是**作者报告结果**，未做独立复现；由文献直接支持的内容标为“事实”，跨文献得到的判断标为“推论”。

## 2. A 类：2026 年顶会正式论文（24 篇）

| # | 文献与状态 | 可核验事实 | 对 FQR-Mem 的直接约束 |
|---:|---|---|---|
| 1 | [Memento: Toward an All-Day Proactive Assistant for Ultra-Long Streaming Video](https://proceedings.iclr.cc/paper_files/paper/2026/hash/3b5f4587a0bdb81ecc6ce9d82320a5c2-Abstract-Conference.html)，ICLR 2026 | 动态记忆、query-related memory selection、step-aware memory attention；MementoBench 覆盖最长 7 小时流视频。 | 仅证明“动态记忆有效”不再新颖；FQR-Mem 必须突出**问题不可见写入**与**未来尾部风险**。 |
| 2 | [StreamingVLM: Real-Time Understanding for Infinite Video Streams](https://proceedings.iclr.cc/paper_files/paper/2026/hash/6445dd88ebb9a6a3afa0b126ad87fe41-Abstract-Conference.html)，ICLR 2026 | 以 attention sink、短视觉窗口和较长文本窗口维持紧凑 KV cache；Inf-Streams-Eval 的视频平均超过两小时。 | “近期视觉 + 长期文本”是必须击败的强简洁基线；同时为“文本无法替代的视觉证据”提供对照。 |
| 3 | [Progressive Online Video Understanding with Evidence-Aligned Timing and Transparent Decisions](https://proceedings.iclr.cc/paper_files/paper/2026/hash/093b793f0af498e8fa218eb5445daeb0-Abstract-Conference.html)，ICLR 2026 | HPSI 用多层聚合 token 维持全局状态，并显式评估首次证据充分时刻。 | 记忆评价不应只有最终 QA；应检查证据何时出现、是否被及时写入与保存。 |
| 4 | [MARC: Memory-Augmented RL Token Compression for Efficient Video Understanding](https://proceedings.iclr.cc/paper_files/paper/2026/hash/16049e0c3f47899091ac46f8b3afb178-Abstract-Conference.html)，ICLR 2026 | 先检索 query-relevant 事件，再以 RL 蒸馏压缩；作者报告视觉 token 减少 95%。 | query 已知条件下的“检索后压缩”很强；只能作为 FQR-Mem 的**上界/特权信息基线**，不能混为同一设定。 |
| 5 | [SURGE: Surprise-Guided Token Reduction for Efficient Video Understanding with VLMs](https://proceedings.iclr.cc/paper_files/paper/2026/hash/07b92344686c19cf3ffc335a0f565406-Abstract-Conference.html)，ICLR 2026 | 以历史预测误差定义 surprise，并可用 query relevance 再细化；作者报告最高约 7 倍 token 缩减。 | surprise 是最重要的无问题写入启发式；FQR-Mem 必须证明“惊奇”不等于“未来条件价值”。 |
| 6 | [VideoChat-Flash: Hierarchical Compression for Long-Context Video Modeling](https://proceedings.iclr.cc/paper_files/paper/2026/hash/b14d7175755b180dc2163e15e3110cb6-Abstract-Conference.html)，ICLR 2026 | HiCo 从 clip 到 video 分层压缩，作者报告约 1/50 压缩且性能损失很小。 | 通用分层压缩已经很强；FQR-Mem 的优势应集中在视觉依赖、跨模态冲突和长尾问题，而非所有平均题型。 |
| 7 | [FlashVID: Efficient Video Large Language Models via Training-free Tree-based Spatiotemporal Token Merging](https://arxiv.org/abs/2602.08024)，ICLR 2026 Oral | 以 attention/diversity 选 token，再做树状时空合并；作者报告保留 10% token 时保留 99.1% 的基座平均性能。 | 必须与强 query-agnostic token merging 在相同**总字节或 token**预算下公平比较。 |
| 8 | [MMR-V: What's Left Unsaid? A Benchmark for Multimodal Deep Reasoning in Videos](https://proceedings.iclr.cc/paper_files/paper/2026/hash/6f1989abe9562c5cd306e070725fe0a3-Abstract-Conference.html)，ICLR 2026 | 强调远距离多帧证据、隐含信息与干扰项；含 317 个视频、1,257 个任务。 | FQR-Mem 不能只优化单帧“needle”；需监督和评估多事件组合价值。 |
| 9 | [RIVER: A Real-Time Interaction Benchmark for Video LLMs](https://proceedings.iclr.cc/paper_files/paper/2026/hash/1022661f3f43406065641f16ce25eafa-Abstract-Conference.html)，ICLR 2026 | 将在线能力拆为 retrospective memory、live perception、proactive response。 | 支持把“历史记忆”与“最近窗口感知”分开报告，避免最近帧掩盖长期记忆能力。 |
| 10 | [Mitigating Spurious Correlation via Distributionally Robust Learning with Hierarchical Ambiguity Sets](https://proceedings.iclr.cc/paper_files/paper/2026/hash/c4f85da01632a2211c785f482cb3e043-Abstract-Conference.html)，ICLR 2026 | 论证普通 Group DRO 仍会受组内分布变化影响，并提出同时覆盖组间、组内不确定性的层次歧义集。 | FQR-Mem 不应只按问题类型做 flat worst-group；需覆盖类型内部的证据稀有度、延迟与 side-info 可靠度变化。 |
| 11 | [Temporal Generalization: A Reality Check](https://proceedings.iclr.cc/paper_files/paper/2026/hash/d24b7366d714b09a977946ef0d9bf3ad-Abstract-Conference.html)，ICLR 2026 | 多类时间任务上，所评估外推方法没有稳定优于简单基线；论文强调没有生成机制假设时，未来泛化非常困难。 | 不能声称对任意未来问题稳健；必须给出明确的 shift family 或 ambiguity set。 |
| 12 | [When Shift Happens - Confounding Is to Blame](https://proceedings.iclr.cc/paper_files/paper/2026/hash/d285ab51e167a923f07e6137d802305a-Abstract-Conference.html)，ICLR 2026 | 隐藏混杂变化会破坏常见 OOD 假设；仅学不变因果特征未必充分。 | 问题分布、视频域与 side-info 质量可能共同变化；实验必须有组合 shift，而非只交换题型先验。 |
| 13 | [Scaling the Long Video Understanding of Multimodal Large Language Models via Visual Memory Mechanism](https://arxiv.org/abs/2603.29252)（FlexMem），CVPR 2026 | 以视觉 KV cache 为记忆源，双通路压缩并探索多种读取策略；训练免费。 | KV 记忆是直接架构基线；FQR-Mem 需说明为什么保存“条件证据 payload”优于只保留通用 KV。 |
| 14 | [FluxMem: Adaptive Hierarchical Memory for Streaming Video Understanding](https://arxiv.org/abs/2603.02096)，CVPR 2026 | 在 query 不可见的流式阶段，依据场景统计自适应做时间相邻选择与空间合并。 | 与 FQR-Mem 的协议非常接近；“自适应层次记忆”本身不是贡献，区别必须落在**目标函数和监督信号**。 |
| 15 | [OASIS: On-Demand Hierarchical Event Memory for Streaming Video Reasoning](https://arxiv.org/abs/2604.17052)，CVPR 2026 | 组织层次事件，并在推理不确定时按意图触发检索。 | 读阶段可借鉴“证据不足再检索”；写阶段仍没有解决未知未来问题下的条件价值分配。 |
| 16 | [WorldMM: Dynamic Multimodal Memory Agent for Long Video Reasoning](https://arxiv.org/abs/2512.02425)，CVPR 2026（arXiv 首发于 2025） | 同时维护 episodic、semantic、visual memory，并按 query 动态选择来源和时间粒度；论文明确指出文本抽象会丢视觉细节。 | 支持多模态互补动机，但也要求 FQR-Mem 超越“多放一个视觉库”，给出可检验的写入原则。 |
| 17 | [Question-guided Visual Compression with Memory Feedback for Long-Term Video Understanding](https://arxiv.org/abs/2603.15167)（QViC-MF），CVPR 2026 | 给定问题后，用当前片段和历史相关帧共同指导视觉压缩。 | 是强 query-known oracle；FQR-Mem 应报告距该 oracle 的差距，而不是把它当普通公平基线。 |
| 18 | [LongVideo-R1: Smart Navigation for Low-cost Long Video Understanding](https://arxiv.org/abs/2602.20913)，CVPR 2026 | 以 SFT+RL 学习从全局摘要到局部片段的 query-aware 主动导航，并在证据足够时停止。 | 若测试时可回放原视频，agentic navigation 会削弱固定记忆问题；FQR-Mem 主实验应禁止原视频回放。 |
| 19 | [LongVT: Incentivizing “Thinking with Long Videos” via Native Tool Calling](https://arxiv.org/abs/2511.20785)，CVPR 2026（arXiv 首发于 2025） | 通过原生视频裁剪工具进行 query-aware、全局到局部的证据检索。 | 进一步说明必须区分“只读已写记忆”和“可重新访问完整视频”两种系统能力。 |
| 20 | [Seeing the Scene Matters: Revealing Forgetting in Video Understanding Models with a Scene-Aware Long-Video Benchmark](https://arxiv.org/abs/2603.27259)，CVPR 2026 Highlight | SceneBench 揭示场景级长上下文遗忘；Scene-RAG 用动态场景记忆改善结果。 | 事件/场景是比独立帧更合理的写入单位，但仍需保留小物体、计数和状态变化等细粒度 payload。 |
| 21 | [MuKV: Multi-Grained KV Cache Compression for Long Streaming Video Question-Answering](https://arxiv.org/abs/2605.22269)，CVPR 2026 | 在 patch、frame、segment 三个粒度压缩 KV，并做半层次检索。 | FQR-Mem 要与多粒度 KV 在记忆、在线时延和证据召回三方面同时比较。 |
| 22 | [Hierarchical Long Video Understanding with Audiovisual Entity Cohesion and Agentic Search](https://arxiv.org/abs/2601.13719)（HAVEN），CVPR 2026 | 跨视觉和音频维持实体一致性，建立 global/scene/segment/entity 层次并 agentic search。 | side information 不是单一 caption；实体身份和视听对齐是条件编码的重要输入。 |
| 23 | [Evidence-Backed Video Question Answering](https://arxiv.org/abs/2607.11862)，ECCV 2026 | E-VQA 同时要求答案、时间段与对象 masklet；ST-Evidence-Instruct 提供大规模细粒度 grounding 监督。 | 只看答案正确会奖励语言猜测；FQR-Mem 的 regret 必须包含 grounded-evidence loss。 |
| 24 | [Reasoning with Memory: A Temporal Granularity-Adaptive Framework for Training-Free Long Video Understanding](https://arxiv.org/abs/2607.24794)（ReMem），ECCV 2026 | 根据 query 时间粒度解析和事件结构动态路由关键帧。 | 读取阶段应自适应时间粒度；写入阶段仍必须在 query 未知时覆盖多粒度证据。 |

## 3. B 类：2026 年高度相关最新预印本（16 篇）

| # | 文献 | 可核验事实 | 对 FQR-Mem 的用途 |
|---:|---|---|---|
| 25 | [What Should a Streaming Video Model Remember?](https://arxiv.org/abs/2606.16353)（SelectStream） | 固定容量 latent memory；surprise-driven window、priority consolidation、query-conditioned graph read。 | 最接近的系统级竞争者之一；迫使 FQR-Mem 证明反事实监督和鲁棒风险优于 surprise/priority。 |
| 26 | [Towards a Dynamic and Fixed-budget Memory Bank for Efficient Streaming Video Understanding](https://arxiv.org/abs/2606.25658)（CausalMem） | 用在线 semantic basis 估计冗余，并在不可预测的未来内容和指令下更新固定预算视觉记忆。 | 最接近的 query-hidden writer；直接对照“信息量最大化”与“未来条件 regret 最小化”。 |
| 27 | [MemoryCard: Topic-Aware Multi-Modal Clue Compression for Long-Video Question Answering](https://arxiv.org/abs/2606.05917) | 先 self-reading 分出事件/主题，再生成 event gist 并选代表视觉时刻。 | 支持事件级单元和多模态线索；也是“文本 gist + 少量视觉帧”的强基线。 |
| 28 | [Query-Conditioned Evidential Keyframe Sampling for MLLM-Based Long-Form Video Understanding](https://arxiv.org/abs/2604.01002) | 将给定 query 的选帧表述为条件互信息最大化，并训练证据评分器。 | 为“条件价值”提供近邻理论语言，但其 query 在选择前已知；可作为 FQR-Mem 的 privileged oracle。 |
| 29 | [Ground, Cover, and Refine: Evidence-Centric Frame Selection for Long-Video Question Answering](https://arxiv.org/abs/2608.01660)（GCR） | 将时间戳文本、真实视觉锚点、全局覆盖和遗漏区 refinement 结合在固定帧预算内。 | 说明单次相关性选择会漏掉分散证据；FQR-Mem 应学习覆盖和证据 bundle，而非只保存最高分事件。 |
| 30 | [When and Where to Look: Adaptive Visual Evidence Scheduling for Efficient Long Video Understanding](https://arxiv.org/abs/2608.03918)（EcoFrame） | 用输出熵决定是否扩预算，并用 attention 决定在哪里局部搜索。 | 读阶段应有证据充分性与自适应停止；但这不能替代写阶段固定预算选择。 |
| 31 | [Evidence-Driven Dynamic Visual Selector for Efficient Long Video Understanding](https://arxiv.org/abs/2608.05780)（EviSelect） | 用目标 MLLM 内部 attention 引导时间、采样率和空间分辨率，并以 GRPO 优化准确率—成本。 | FQR-Mem 的 utility critic 最好与目标模型对齐，且必须同时预测**价值与所需码率**。 |
| 32 | [REVEAL: A Rubric-Guided Agent for Explicit Evidence Sufficiency Verification in Long-Video Question Answering](https://arxiv.org/abs/2608.08612) | 显式检验已取证据是否充分，并针对缺失线索重新检索。 | 支持把“相关性”和“充分性”区分；未来问题鲁棒记忆需覆盖证据组合的完整性。 |
| 33 | [VideoZeroBench: Probing the Limits of Video MLLMs with Spatio-Temporal Evidence Verification](https://arxiv.org/abs/2604.01569) | 500 个问题带时间区间和空间框；作者报告在答案与时空 grounding 同时正确的最高层级，没有模型超过 1%。 | 证明 grounded regret 不是装饰指标；它能避免正确答案掩盖错误视觉依据。 |
| 34 | [EG-VQA: Benchmarking Verifiable Video Question Answering with Grounded Temporal Evidence](https://arxiv.org/abs/2606.24797) | 2,067 个视频、11,838 个 QA，带时间证据；提出 EG-F1。 | 可作为时间证据监督和验证来源，并支持按证据跨度、稀有度建立 groups。 |
| 35 | [EgoMonth: A Month-Level Egocentric Video Benchmark for Long-Term Spatiotemporal Memory](https://arxiv.org/abs/2608.13113) | 300 多小时第一视角视频，跨度 20–120 天；包含 schema、episodic indexing、cascading reasoning。 | 用于检验小时级方法是否能扩展到跨日长期记忆；更适合作为后期外部验证，不宜作为首轮 MVP。 |
| 36 | [CRAFT: Compression via Recursive Adaptive Fusion of Video Tokens for Vision-Language Models](https://arxiv.org/abs/2608.01644) | query-agnostic 递归融合，并保留真实时空坐标；作者报告约 8 倍压缩时保留约 97% 平均性能。 | 可作为 FQR-Mem 条件 codec 的强通用压缩骨干或 matched-budget baseline。 |
| 37 | [ForestPrune: High-ratio Visual Token Compression for Video Multimodal Large Language Models via Spatial-Temporal Forest Modeling](https://arxiv.org/abs/2603.22911) | 以全局时空 forest 决定树和节点重要性；训练免费。 | 说明局部相邻冗余不足以代表全局可替代性；writer 的 redundancy 项需跨事件计算。 |
| 38 | [Beyond Frame Selection: Generative Latent Evidence Aggregation for Long-Video Understanding](https://arxiv.org/abs/2607.28516)（GenEvA） | 在已选帧之后，以 query-conditioned 分布聚合跨帧 latent evidence。 | 说明多证据的联合表示有独立价值；支持在 FQR-Mem 中加入 bundle synergy 标签。 |
| 39 | [WorldMemArena: Evaluating Multimodal Agent Memory Through Action-World Interaction](https://arxiv.org/abs/2605.29341) | 将记忆拆为写入、维护、检索与使用阶段；作者发现写得/存得更好不保证任务更好，视觉证据使用仍困难。 | FQR-Mem 必须做阶段诊断和 memory deletion/swap 测试，不能只看端到端 QA。 |
| 40 | [StreamSoccer: Event-Driven Memory for Streaming Soccer Commentary](https://arxiv.org/abs/2608.19723) | 固定 active memory 保存演化中的事件状态，完成事件被整合为可检索历史记录。 | 表明“事件生命周期”比固定 clip 更适合流式更新；可启发状态变更与完成事件的写入策略。 |

## 4. 跨文献结论

### 4.1 已经拥挤、不能再作为主贡献的部分

以下判断是对上述事实的综合推论：

1. **“做一个固定预算流式视觉记忆”已经不够新。** Memento、FlexMem、FluxMem、MuKV、SelectStream、CausalMem 已从 dynamic memory、KV cache、层次压缩和在线更新等角度覆盖该命题。
2. **“按 query 选关键帧”更加拥挤。** QViC-MF、MARC、LongVideo-R1、LongVT、ReMem、GCR、EcoFrame、EviSelect 已形成很强的 query-known 阵线。
3. **“surprise/novelty 就是记忆价值”不能未经验证地采用。** SURGE、SelectStream 让它成为强基线，但 surprise 衡量不可预测性，不直接衡量相对于 ASR/OCR/caption 的未来回答增益。
4. **“分层记忆”也不能单独构成创新。** VideoChat-Flash、OASIS、WorldMM、HAVEN、MuKV 已从不同粒度给出实现。

### 4.2 仍未被正面解决的空白

1. **条件互补写入。** 现有 query-hidden writer 多优化通用信息量、场景统计、surprise 或冗余；尚未看到它们把“给定低成本 side information 后仍不可恢复的未来证据价值”作为核心监督目标。
2. **未来问题的尾部风险。** 现有方法主要优化训练/测试混合分布的平均准确率；层次 group shift 与 upper-tail regret 尚未成为视觉记忆写入目标。
3. **问题未知时的证据 bundle。** query-known 方法可以在读取时拼接多段证据；query-hidden writer 如何提前保存互补事件组合，仍缺少明确反事实监督。
4. **写入—使用因果闭环。** grounding benchmark 和 WorldMemArena 都表明“答案正确”“记忆写得像摘要”不等于模型真正使用了正确视觉证据。

### 4.3 对 FQR-Mem 的收敛性结论

FQR-Mem 最有机会成立的论文命题不是“更强的视频记忆”，而是：

> 在严格的 **query-after-write**、固定总视觉预算、显式 side information 和禁止原视频回放的协议下，用反事实未来回答损失学习**条件视觉证据的单位字节边际价值**，并在事先声明的问题分布与证据分布变化族上最小化层次化尾部 regret。

该命题与直接近邻的区别如下：

| 方法族 | 写入时 query | 写入信号 | 主要目标 | FQR-Mem 的差异 |
|---|---:|---|---|---|
| SURGE / FluxMem / CausalMem | 否 | surprise、场景统计、语义冗余 | 通用信息保留 | 条件于 side information 的未来 grounded regret |
| Memento / SelectStream | 流式任务中可在读阶段使用 | priority、query-related retrieval | 在线平均任务性能 | 写入时问题隐藏；层次 shift 下的尾部风险 |
| QViC-MF / MARC / LongVideo-R1 / LongVT | 是 | query relevance 或任务奖励 | 当前问题的取证效率 | 仅作为特权 oracle；FQR-Mem 解决问题到达前的写入 |
| WorldMM / HAVEN / MemoryCard | 读时是 | 多模态层次记忆与事件摘要 | 跨粒度检索 | 显式估计文本/音频已经解释后，视觉 payload 还增加多少价值 |
| E-VQA / VideoZeroBench / EG-VQA | 不适用 | 证据标注 | 可验证评估 | 将 grounding 变成写入监督与 regret 的组成部分 |

## 5. 需要谨慎陈述的边界

1. **不能声称对“任意未来问题”泛化。** 可辩护的说法是对预先定义的 ambiguity set 稳健，例如问题类型先验变化、已知类型的新组合、side-information 退化、证据跨度/延迟变化和有限域迁移。
2. **不能把 query-known selector 当作同协议对手。** 它们应标为 privileged oracle；公平主基线在写入时都不得看到测试问题。
3. **不能让文本生成成本隐身。** 原生 ASR/OCR、离线生成 caption、对象轨迹与摘要的计算/存储成本必须分栏报告。
4. **不能只报告 token 数。** 不同表示的 token 不可直接比较；主资源轴应包括活动字节、总持久字节、写入 FLOPs/时延、读取 TTFT 与原视频 I/O。
5. **不能由调研直接断言方案有效。** 当前证据只说明问题空白可辨识；最先要做的是低成本 phenomenon study，验证“条件未来价值”是否真实优于 surprise/通用压缩。

## 6. 调研结论

截至 2026-08-24，FQR-Mem 仍有论文空间，但空间已经被压缩到一个更窄、更科学的问题：**未知问题写入阶段的条件证据价值与尾部风险**。如果只实现事件分层、固定 memory bank、query-aware retrieval 或一般 token compression，会与 2026 年工作高度重叠；只有反事实条件效用、严格防 query 泄漏、层次 shift、grounded regret 和因果使用验证同时成立，才足以支撑 ICLR/CVPR 级主张。
