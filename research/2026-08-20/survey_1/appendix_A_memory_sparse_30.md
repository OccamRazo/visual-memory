# 稀疏注意力、KV Cache 压缩与模型级记忆：30 篇核心工作

> 截止日期：2026-08-20。题名、时间按 arXiv 首个公开版本（v1）记录；机构列列出论文首页的主要署名机构，而非穷举全部合作者。每篇均链接到 arXiv 原始记录，避免把二手解读当成论文结论。

## 口径、统计与纳入理由

- **严格 30 篇**：稀疏/高效注意力 10 篇，KV Cache 压缩/复用 10 篇，模型级记忆/长上下文压缩 10 篇。
- **2025 年及以后：18/30（60%）**。Titans 的 v1 提交于 **2024-12-31**，虽通常按 arXiv 编号和引用习惯记作 2025，本文仍按严格首发时间计为 2024；若采用常见引用年，则为 **19/30**。
- 其余 12 篇是无法绕过的直接前驱：它们奠定了动态稀疏模式、按查询选 KV、按 head/layer 分工、KV 量化与潜变量缓存、固定状态记忆/自更新记忆等主线。入选标准是头部实验室、顶会认可或已成为 2025–2026 工作反复比较的强基线；不以“新”替代“关键”。
- “视觉记忆启示”均是本文基于机制做的迁移推论，不冒充原论文已经完成的实验；其中 MMInference、VL-Cache、LaCT 确实包含视觉/视频实验，其他大多仍以文本为主。

## A. 稀疏与高效注意力（10 篇）

### 1. MInference 1.0: Accelerating Pre-filling for Long-Context LLMs via Dynamic Sparse Attention

- **时间 / 机构 / 类别**：2024-07；Microsoft Research；训练后、动态稀疏 prefill。
- **核心机制**：先离线为每个 attention head 识别 A-shape、vertical-slash 或 block-sparse 三类模式，再在输入到来时在线构造稀疏索引并调用对应 GPU kernel。它不改模型参数，目标是只加速长 prompt 的 prefill，而不是把所有阶段统一成一种稀疏结构。
- **视觉记忆启示**：视频 token 的“邻域、轨迹/竖线、事件块”可分别映射到三种模式；head-specific pattern 比全层统一抽帧更有机会同时保住局部动作和远程回指。
- **关键局限**：模式族由人工预设且主要服务 prefill；不减少随后解码必须长期保存的 KV，也不直接定义跨事件写入/遗忘策略。
- **一手来源**：[arXiv:2407.02490](https://arxiv.org/abs/2407.02490)

### 2. SeerAttention: Learning Intrinsic Sparse Attention in Your LLMs

- **时间 / 机构 / 类别**：2024-10；Microsoft Research；可学习的 block-sparse attention。
- **核心机制**：为 attention 增加轻量 block-level gate，预测哪些 Q–K 块值得计算；用 dense attention 产生的信号做自蒸馏，再由定制 block-sparse kernel 执行。相较手工模式，稀疏图可随输入和 head 改变。
- **视觉记忆启示**：可把 gate 扩展为“帧块 × 空间块 × 模态块”路由器，让模型学习何时读取远处镜头，而非只依赖固定时间窗口。
- **关键局限**：节省是否可靠取决于 gate 对 dense attention 的召回；蒸馏、额外训练和 kernel 适配提高迁移成本，漏掉小而关键的视觉块会不可逆。
- **一手来源**：[arXiv:2410.13276](https://arxiv.org/abs/2410.13276)

### 3. Native Sparse Attention: Hardware-Aligned and Natively Trainable Sparse Attention

- **时间 / 机构 / 类别**：2025-02；DeepSeek-AI；原生训练、硬件对齐的稀疏注意力。
- **核心机制**：NSA 把三条读取路径合在同一层：压缩后的粗粒度全局 token、对原始 token 的细粒度选择、以及局部滑窗精确注意力。模型从预训练阶段就适应这种层次化稀疏结构，并按 GPU 友好的块粒度组织计算。
- **视觉记忆启示**：天然对应“全局故事摘要—少量原始关键帧—当前局部连续帧”三级记忆；它提示视觉记忆不应只做单一路径 Top-k，而应保留不同保真度的互补通道。
- **关键局限**：不是对现成 VLM 的无训练插件；压缩与选择路径若共享错误显著性，会同时遗失短暂但决定答案的细节，且视频侧仍需重新设计时空块。
- **一手来源**：[arXiv:2502.11089](https://arxiv.org/abs/2502.11089)

### 4. MoBA: Mixture of Block Attention for Long-Context LLMs

- **时间 / 机构 / 类别**：2025-02；Moonshot AI；Mixture-of-Experts 式块稀疏注意力。
- **核心机制**：把上下文切成块，用块内 key 的均值作为路由表示；每个 query 以参数无关的 Top-k 选择少数远程块，同时总是访问当前块。它保留完整块内 softmax，并通过继续训练让模型适应块级路由。
- **视觉记忆启示**：可令一个块对应一个镜头或事件，把“找相关历史事件”改写为可扩展的 block routing；连续块保留局部动作完整性，比散点式 token pruning 更符合视频语义。
- **关键局限**：均值路由会稀释块内短促细节，固定分块可能切断事件边界；需要继续训练，且 Top-k 路由仍可能使分散证据无法共同被读出。
- **一手来源**：[arXiv:2502.13189](https://arxiv.org/abs/2502.13189)

### 5. FlexPrefill: A Context-Aware Sparse Attention Mechanism for Efficient Long-Sequence Inference

- **时间 / 机构 / 类别**：2025-02；北京大学、香港大学、字节跳动 Seed；自适应 sparse prefill（ICLR 2025 Oral）。
- **核心机制**：先用 Jensen–Shannon divergence 判断当前 head 更像 query-specific block 模式还是 vertical-slash 模式，再通过累计 attention 阈值按输入动态决定稀疏预算与索引。核心不是固定稀疏率，而是让不同 head、样本获得不同计算量。
- **视觉记忆启示**：同一视频中静态镜头、快速动作和跨镜头回忆所需预算不同；“模式选择 + 自适应预算”可直接迁移到按事件难度分配视觉 memory read。
- **关键局限**：代理 attention 和阈值校准决定召回率；依然偏 prefill 计算加速，不能自动解决长期 KV 存储或多轮问题改变后的重新检索。
- **一手来源**：[arXiv:2502.20766](https://arxiv.org/abs/2502.20766)

### 6. XAttention: Block Sparse Attention with Antidiagonal Scoring

- **时间 / 机构 / 类别**：2025-03；MIT Han Lab；免训练 block-sparse attention。
- **核心机制**：利用 attention map 内重要区域沿反对角线聚集的经验规律，以反对角线聚合分数估计块重要性，再只计算高分 Q–K 块。该设计作为插件接入既有模型，并在文本长上下文及 VideoMME/VBench 上验证。
- **视觉记忆启示**：反对角结构与“相对时间差”天然相关，可用于优先保留跨帧轨迹和周期性事件；它也是少数直接显示文本稀疏规律可迁移到视频任务的证据。
- **关键局限**：显著性若是弥散的、非对角的或跨模态错位，反对角代理会漏块；它选择计算区域但不提供持久记忆写入、合并或冲突消解。
- **一手来源**：[arXiv:2503.16428](https://arxiv.org/abs/2503.16428)

### 7. MMInference: Accelerating Pre-filling for Long-Context Visual Language Models via Modality-Aware Permutation Sparse Attention

- **时间 / 机构 / 类别**：2025-04；Microsoft Research；视觉语言模型 sparse prefill（ICML 2025）。
- **核心机制**：论文发现长视频注意力具有专门的时空 Grid 模式，并以 modality-aware permutation 重排视觉/文本 token，使网格与模态边界更适合稀疏 kernel。它延续 MInference 的“离线逐 head 模式搜索 + 在线动态索引”，且无需微调。
- **视觉记忆启示**：这是最直接的桥梁：视觉稀疏性不是文本 vertical/slash 的简单复制，必须显式建模帧序与空间位置；重排后可把相似轨迹或同一空间格的历史 token 连续存取。
- **关键局限**：主要解决一次长视频 prompt 的 prefill；未给出跨问题可复用的压缩记忆、在线事件更新或解码阶段固定成本状态。
- **一手来源**：[arXiv:2504.16083](https://arxiv.org/abs/2504.16083)

### 8. DuoAttention: Efficient Long-Context LLM Inference with Retrieval and Streaming Heads

- **时间 / 机构 / 类别**：2024-10；MIT Han Lab 等；head-level 混合注意力与 KV 保留。
- **核心机制**：通过合成检索任务优化一个 gate，找出少量需要完整历史的 retrieval heads；其余 streaming heads 只保留 attention sink 和最近窗口。由此同时减少解码 attention 与 KV cache，而关键检索能力由少数 full-cache heads 承担。
- **视觉记忆启示**：可显式分化“身份/物体追踪 head”和“局部动作 head”，只给前者保留长时间视觉缓存；比所有 head 使用同一帧集合更符合功能分工。
- **关键局限**：head 角色在新任务、问题或模态上可能改变，静态划分会错误删除信息；GQA/MQA 的共享 KV 也会限制实际可压缩比例。
- **一手来源**：[arXiv:2410.10819](https://arxiv.org/abs/2410.10819)

### 9. Quest: Query-Aware Sparsity for Efficient Long-Context LLM Inference

- **时间 / 机构 / 类别**：2024-06；MIT Han Lab、University of Michigan；解码期 query-aware KV 选择。
- **核心机制**：把 KV cache 分页，并为每页 key 保存逐通道最小/最大值；当前 query 可用这些界估计页面可能达到的 attention score，只加载 Top-k 页面做精确 attention。它把稀疏读取从“历史累计重要性”改为随当前 query 改变。
- **视觉记忆启示**：视觉记忆可为每个事件块维护廉价 key envelope，问题到来后先做粗检索再读取高保真帧；这能支持同一视频面对不同问题时选择不同记忆。
- **关键局限**：若完整 KV 仍在 CPU/低层存储，主要省带宽和计算而非总存储；界估计松或证据分散时，固定 Top-k 会漏掉组合证据。
- **一手来源**：[arXiv:2406.10774](https://arxiv.org/abs/2406.10774)

### 10. Kimi Linear: An Expressive, Efficient Attention Architecture

- **时间 / 机构 / 类别**：2025-10；Moonshot AI / Kimi Team；线性注意力与 MLA 混合架构。
- **核心机制**：Kimi Delta Attention（KDA）以通道级 forget gate 配合 delta-rule 更新固定大小矩阵状态，并用硬件友好的 chunkwise/WY 形式训练；整体按 3:1 交织 KDA 与精确的 MLA 层。它不是“全线性替换”，而是让固定状态承担大部分历史，再周期性保留 softmax 检索通道。
- **视觉记忆启示**：可把 KDA 状态视为持续更新的场景/角色记忆，把稀疏 MLA 层作为高保真回看通道；通道级遗忘也适合分别控制外观、动作、位置等视觉属性寿命。
- **关键局限**：必须按新架构训练；有限状态会发生干扰和覆盖，精确 needle retrieval 仍依赖 MLA，效率优势也随 batch、上下文长度和 kernel 条件变化。
- **一手来源**：[arXiv:2510.26692](https://arxiv.org/abs/2510.26692)

## B. KV Cache 压缩、量化与复用（10 篇）

### 11. KVzip: Query-Agnostic KV Cache Compression with Context Reconstruction

- **时间 / 机构 / 类别**：2025-05；Seoul National University；query-agnostic KV pruning（NeurIPS 2025 Oral）。
- **核心机制**：KVzip 不用某个未来问题给 token 打分，而让缓存重建其原上下文，以重建时的贡献估计可跨查询复用的 KV 重要性。一次压缩后的 cache 因而可服务多个未知问题，避免每次 query 重新压缩。
- **视觉记忆启示**：适合“视频先看完、问题后到达”的设定；可把重建目标改成多尺度视觉/事件重建，使共享 memory bank 在未知 QA 前先完成写入。
- **关键局限**：重建原输入并不等价于保留未来问题所需的罕见细节；压缩 pass 有额外成本，且文本自回归重建尚不能保证时空一致性。
- **一手来源**：[arXiv:2505.23416](https://arxiv.org/abs/2505.23416)

### 12. ChunkKV: Semantic-Preserving KV Cache Compression for Efficient Long-Context LLM Inference

- **时间 / 机构 / 类别**：2025-02；香港科技大学（广州）等；chunk-level KV eviction（NeurIPS 2025）。
- **核心机制**：用 prompt 末端 observation window 的 attention 给连续 token chunk 计分，以 chunk 为整体保留/丢弃，并保留最近窗口；相邻层还可复用选中索引。它针对逐 token Top-k 会破坏主谓宾等语义结构的问题。
- **视觉记忆启示**：视频中最自然的压缩单位应是镜头、动作段或 tracklet，而不是孤立 patch；完整保留一个事件块可减少“看见物体却丢失动作/关系”的碎片化。
- **关键局限**：固定 chunk 边界未必等于真实事件边界，长块会稀释瞬时线索；末端 observation window 对尚未出现的问题仍带有偏置。
- **一手来源**：[arXiv:2502.00299](https://arxiv.org/abs/2502.00299)

### 13. Cache-Craft: Managing Chunk-Caches for Efficient Retrieval-Augmented Generation

- **时间 / 机构 / 类别**：2025-02；Adobe Research、IIT Bombay、IIT Kanpur；KV chunk 复用系统（SIGMOD 2025）。
- **核心机制**：为任意 RAG 文档块预计算 chunk-cache，处理 RoPE/位置变化，判断哪些 cache 可复用，并只重算少量受上下文影响的 token；再以分层存储、预取和淘汰隐藏 I/O。其核心是避免重复 prefill，而非有损删除同一请求内的 KV。
- **视觉记忆启示**：重复出现的人物、地点或镜头可维护可复用的视觉 chunk-cache，仅在新上下文改变关系时局部修补；适合多轮询问同一长视频或跨视频共享实体记忆。
- **关键局限**：收益依赖 chunk 重复率和可复用性；上下文依赖修补是系统启发式，且它不降低每个唯一视频第一次编码的总信息量。
- **一手来源**：[arXiv:2502.15734](https://arxiv.org/abs/2502.15734)

### 14. TurboQuant: Online Vector Quantization with Near-optimal Distortion Rate

- **时间 / 机构 / 类别**：2025-04；Google Research；在线向量/KV 量化。
- **核心机制**：先用随机旋转使坐标分布集中，再逐坐标使用接近最优的标量量化；为避免 MSE 量化带来的内积偏差，又对残差加一层 1-bit Quantized JL，从而得到无偏的内积估计。算法 data-oblivious，适合在线写入 cache。
- **视觉记忆启示**：它提供“保留全部视觉 token、降低每 token 字节数”的正交轴，可与事件选择叠加；内积无偏性尤其适合随后用 query 对压缩视觉 keys 做检索。
- **关键局限**：只压缩数值精度，不决定哪些帧/事件值得保留；旋转、残差和专用 kernel 的端到端收益需在具体 VLM 硬件栈复核。
- **一手来源**：[arXiv:2504.19874](https://arxiv.org/abs/2504.19874)

### 15. SnapKV: LLM Knows What You are Looking for Before Generation

- **时间 / 机构 / 类别**：2024-04；UIUC、Cohere、Princeton；免训练 prompt-KV 压缩。
- **核心机制**：用 prompt 尾部 observation window 观察每个 head 对历史位置的 attention，投票并池化相邻位置，再保留 head-specific 的关键 prefix KV 与完整近期窗口。压缩在生成前一次完成，随后解码 cache 大小近似固定。
- **视觉记忆启示**：池化邻近位置比孤立选帧更能保留动作连续性；逐 head 选择可让外观、OCR、运动等线索拥有不同关键帧集合。
- **关键局限**：假设 prompt 末端已经表达未来生成需求；若问题稍后才出现、或多轮问题改变关注点，先前删除的视觉证据无法恢复。
- **一手来源**：[arXiv:2404.14469](https://arxiv.org/abs/2404.14469)

### 16. PyramidKV: Dynamic KV Cache Compression based on Pyramidal Information Funneling

- **时间 / 机构 / 类别**：2024-06；UW–Madison、北京大学、南京大学、Qwen/Alibaba、UC Riverside、Microsoft 等；layer-adaptive KV 压缩。
- **核心机制**：论文观察到低层 attention 分散、高层逐步聚焦的“金字塔信息漏斗”，据此给低层更大 KV budget、高层更小 budget，并在每层选保关键位置。它打破所有层统一 cache 长度的惯例。
- **视觉记忆启示**：低层视觉特征需要较密的空间/纹理记忆，高层可只保留语义事件；按层分配保真度比全模型统一抽帧更合理。
- **关键局限**：单调金字塔规律并非对所有 VLM、任务或跨模态层都成立；静态预算曲线也未显式响应当前视频运动强度和问题类型。
- **一手来源**：[arXiv:2406.02069](https://arxiv.org/abs/2406.02069)

### 17. KIVI: A Tuning-Free Asymmetric 2bit Quantization for KV Cache

- **时间 / 机构 / 类别**：2024-02；Rice University、Texas A&M、Stevens Institute、CMU；2-bit KV 量化。
- **核心机制**：根据离群值分布差异，对 key 采用 per-channel 非对称 2-bit 量化，对 value 采用 per-token 量化；最新的一段 residual cache 保持高精度，旧 token 分组后量化。它不删 token，专注减少每个 KV 元素的存储与带宽。
- **视觉记忆启示**：视觉细节不能轻易删时，可先以低比特保留全时间轴，再给近期或高价值事件高精度 residual；这为“容量压缩”和“语义遗忘”解耦提供基线。
- **关键局限**：量化误差会在细粒度视觉比对/OCR 上放大，且真实加速依赖算子支持；长度与 attention 计算仍随 token 数线性增长。
- **一手来源**：[arXiv:2402.02750](https://arxiv.org/abs/2402.02750)

### 18. DeepSeek-V2: A Strong, Economical, and Efficient Mixture-of-Experts Language Model

- **时间 / 机构 / 类别**：2024-05；DeepSeek-AI；Multi-head Latent Attention（MLA）架构级 cache 压缩。
- **核心机制**：MLA 将各 head 的 key/value 联合下投影为低维 latent cache；内容部分可在读取时重构或把投影吸收到权重中，位置部分通过 decoupled RoPE key 单独保留。它从架构源头减少每 token cache 宽度，而非推理时删历史位置。
- **视觉记忆启示**：可把每帧多头视觉 KV 合成共享 latent，再单独保存时间/空间位置通道；适合作为事件级 memory 的高保真底层表示。
- **关键局限**：要求预训练/继续训练新架构，不能无损套到现有 VLM；共享低维 latent 可能压掉只由少数 head 承载的细节，且 token 数仍随视频长度增长。
- **一手来源**：[arXiv:2405.04434](https://arxiv.org/abs/2405.04434)

### 19. VL-Cache: Sparsity and Modality-Aware KV Cache Compression for Vision-Language Model Inference Acceleration

- **时间 / 机构 / 类别**：2024-10；UCLA、Amazon AWS AI；VLM 专用 KV 压缩（ICLR 2025）。
- **核心机制**：先分别测量视觉 token 与文本 token 在 prefill/decode 的稀疏性和 cache hit，再按层自适应分配有限 cache budget，并以 modality-aware 分数选择 token。它说明把文本 KV 策略原样迁移到 VLM 会产生错误预算。
- **视觉记忆启示**：这是视觉 KV 压缩的直接起点：视觉、文本、以及未来可加入的音频/字幕应拥有不同的保留先验；层预算与模态预算应联合学习。
- **关键局限**：模态标签不等于事件价值，仍可能删除短暂但问答关键的画面；现有验证不足以证明在小时级视频、多轮未知问题下仍稳健。
- **一手来源**：[arXiv:2410.23317](https://arxiv.org/abs/2410.23317)

### 20. xKV: Cross-Layer KV-Cache Compression via Aligned Singular Vector Extraction

- **时间 / 机构 / 类别**：2025-03；Cornell、University of Washington、NYCU、Microsoft Research Asia 等；跨层低秩 KV 压缩。
- **核心机制**：以 CKA 观察到不同层 KV 的主导左奇异向量对齐，于是对一组层联合分解，让它们共享低秩子空间；解码时再做 dense 或 landmark-guided selective reconstruction。它把冗余轴从“token 内/层内”扩展到“跨层”。
- **视觉记忆启示**：长视频在层间重复保存同一实体/场景，可共享 temporal basis，只为不同层保留小型系数；还可与帧选择和低比特量化正交组合。
- **关键局限**：SVD/校准和重构增加实现复杂度，跨层对齐随模型与数据变化；长生成时新增 KV、以及精细视觉层的非共享成分仍可能成为瓶颈。
- **一手来源**：[arXiv:2503.18893](https://arxiv.org/abs/2503.18893)

## C. 模型级记忆、固定状态与长上下文压缩（10 篇）

### 21. Titans: Learning to Memorize at Test Time

- **时间 / 机构 / 类别**：2024-12-31（常见引用年 2025）；Google Research；test-time neural long-term memory。
- **核心机制**：用一个深层神经网络作为长期记忆，以当前样本对记忆的“surprise”（损失梯度）驱动在线写入，并引入 momentum 与 forgetting 控制更新；短期精确依赖仍由 attention 承担。论文给出 memory as context、memory as gate、memory as layer 等组合方式。
- **视觉记忆启示**：可把预测误差大的新角色、场景变化或反常事件优先写入视觉长期记忆，而冗余帧自然获得较小更新；attention + neural memory 对应回放细节与累积经验的双系统。
- **关键局限**：顺序梯度更新会发生干扰、灾难性覆盖和数值稳定问题；“surprise”不一定与未来 QA 价值一致，且原工作不是小时级视频问答验证。
- **一手来源**：[arXiv:2501.00663](https://arxiv.org/abs/2501.00663)

### 22. Nested Learning: The Illusion of Deep Learning Architectures

- **时间 / 机构 / 类别**：2025-12；Google Research；多时间尺度优化/continuum memory。
- **核心机制**：把模型、优化器与记忆统一为多个嵌套或并行的优化问题，每层拥有自己的 context flow 和更新频率；优化器状态本身被解释为压缩梯度历史的 associative memory。Hope 原型进一步结合 self-modifying sequence model 与 continuum memory，展示多层次持续学习的可能性。
- **视觉记忆启示**：视觉记忆可按时间尺度分层：帧级快速状态、事件级中速状态、角色/场景级慢速状态，并让写入规则也可学习，而非只学习 memory content。
- **关键局限**：更接近统一理论与 proof-of-concept，尚缺少成熟的多模态服务系统；多层在线优化的稳定性、并发隔离和可控遗忘仍未解决。
- **一手来源**：[arXiv:2512.24695](https://arxiv.org/abs/2512.24695)

### 23. End-to-End Test-Time Training for Long Context

- **时间 / 机构 / 类别**：2025-12；Astera Institute、NVIDIA、Stanford、UC Berkeley、UC San Diego 等；端到端 TTT / 权重记忆。
- **核心机制**：只用标准 sliding-window Transformer，在测试时继续做 next-token learning，把读过的长上下文压进模型权重；训练时又通过 meta-learning 学到适合这种在线学习的初始化。记忆容量因此从显式 KV 转为每个序列独立演化的参数状态。
- **视觉记忆启示**：可令视频自监督目标（下一帧 latent、遮挡重建、时序一致性）驱动 test-time write，使模型在看视频时形成会被后续问题读取的临时参数记忆。
- **关键局限**：每条视频拥有可变权重，给并发 batching、缓存复用、回滚与隐私隔离带来困难；meta-training 和跨更新反传昂贵，错误自监督信号也会污染记忆。
- **一手来源**：[arXiv:2512.23675](https://arxiv.org/abs/2512.23675)

### 24. Test-Time Training Done Right

- **时间 / 机构 / 类别**：2025-05；MIT、Adobe Research；Large-Chunk Test-Time Training（LaCT）。
- **核心机制**：LaCT 将 fast-weight 更新块从很小的在线 batch 扩到 2K–1M token，以提高硬件利用率并允许更大的非线性记忆状态；块内局部顺序/空间结构交给 window attention。论文覆盖语言、novel-view synthesis 与 14B 自回归视频扩散，是视觉记忆最直接的 TTT 证据之一。
- **视觉记忆启示**：一个更新块可对齐一帧、一组视角或一个镜头；window attention 保局部结构，非线性 fast weight 汇总跨镜头信息，形成“局部精确 + 全局固定状态”。
- **关键局限**：超大块更新弱化细粒度因果写入，并在块内近似集合；论文视频任务是生成而非超长视频 QA，问题条件下的选择性记忆仍需新增机制。
- **一手来源**：[arXiv:2505.23884](https://arxiv.org/abs/2505.23884)

### 25. Conditional Memory via Scalable Lookup: A New Axis of Sparsity for Large Language Models

- **时间 / 机构 / 类别**：2026-01；DeepSeek-AI；Engram / O(1) conditional memory。
- **核心机制**：Engram 将经典 N-gram embedding 现代化：确定性哈希定位静态 memory entry，再用上下文门控融合；访问地址可预知，因此可从 host memory 预取。它把“条件计算（MoE）”之外增加“条件记忆”这一独立扩容轴。
- **视觉记忆启示**：可为离散化的实体—动作—场景组合建立 O(1) 原型表，把常见视觉知识移出主干计算，并把 attention 容量留给当前视频的全局关系。
- **关键局限**：N-gram lookup 擅长静态局部模式，不是可写的 episodic video memory；哈希碰撞、词表/码本陈旧与连续视觉特征离散化会限制迁移。
- **一手来源**：[arXiv:2601.07372](https://arxiv.org/abs/2601.07372)

### 26. MemoryLLM: Towards Self-Updatable Large Language Models

- **时间 / 机构 / 类别**：2024-02；UC San Diego、Amazon、UCLA；latent memory pool / 自更新模型。
- **核心机制**：在 Transformer 每层放置固定大小的 latent memory tokens；新文本到来时只更新每层 memory pool 的一部分，让新知识进入、旧知识逐步退出，生成时再将记忆作为层内状态参与计算。其目标是无需无限增长外部文本库的持续知识注入。
- **视觉记忆启示**：可把视频片段逐段注入分层视觉 latent pool，并为不同层分别保存纹理、实体和事件关系；固定池提供严格的长视频内存上界。
- **关键局限**：固定池容量导致干扰与慢性遗忘，更新本身不是 query-aware；需要专门的持续训练，且文本注入结果不能直接证明对密集视觉细节有效。
- **一手来源**：[arXiv:2402.04624](https://arxiv.org/abs/2402.04624)

### 27. M+: Extending MemoryLLM with Scalable Long-Term Memory

- **时间 / 机构 / 类别**：2025-02；UC San Diego、MIT-IBM Watson AI Lab/IBM Research、Amazon、OPPO；分层 latent memory + co-trained retriever。
- **核心机制**：在 MemoryLLM 的短期固定池之外加入可扩展、可放在 CPU 的长期 hidden-state memory，并共同训练 retriever；生成时每层做一次相关记忆检索，再供所有 query heads 使用。它把“压缩写入”和“按需读取”合成两级系统。
- **视觉记忆启示**：近期镜头留在 GPU 短期池，旧事件/实体转入 CPU 长期库，问题到来后按层检索；这是超长视频可部署分级存储的直接模板。
- **关键局限**：效果受检索训练、索引陈旧和 CPU–GPU 传输影响；长期库仍会增长，且文本 hidden-state 相似度未必能区分细粒度视觉事件。
- **一手来源**：[arXiv:2502.00592](https://arxiv.org/abs/2502.00592)

### 28. Fix the Structural Bottleneck: Context Compression via Explicit Information Transmission

- **时间 / 机构 / 类别**：2026-02；King’s College London、Tsinghua、Imperial College London、Alan Turing Institute；ComprExIT / soft context compression。
- **核心机制**：不把 LLM 本身继续训练成 compressor，而把冻结 LLM 各层 hidden states 当特征：depthwise 路径用跨层加权捷径形成 token anchors，widthwise 路径用全局协调的 optimal-transport plan 将 anchors 分配到少量连续 slots。它分别针对逐层信息稀释和多个 gist token 重复覆盖同一区域。
- **视觉记忆启示**：可从视觉编码器多层同时抽取低层细节与高层语义，再用最优传输让有限 event slots 分工覆盖不同时间段/实体，减少多个 memory token“都记住同一显著镜头”。
- **关键局限**：压缩前仍要完整编码原上下文；原方法 query-agnostic，且现有证据以文本为主，长视频需要时空约束的 transport 与流式/窗口化实现。
- **一手来源**：[arXiv:2602.03784](https://arxiv.org/abs/2602.03784)

### 29. SeDeM: Selective Decompression of Hidden-State Memories for Long-Context Question Answering

- **时间 / 机构 / 类别**：2026-07（arXiv 归档号为 2608）；UCLA；选择性压缩—检索—解压记忆。
- **核心机制**：把中间层 hidden states 池化成紧凑 memory blocks；问题到来后由 selector 选少量块，再用轻量 decompressor 展开并注入 decoder 的中间层。它显式分离低成本存储表示与适合生成器消费的高带宽表示，而不是让压缩 slot 直接承担所有读出。
- **视觉记忆启示**：长视频可常驻保存事件级 latent，仅对问题相关事件恢复帧/对象级 tokens；这为“存得粗、读时细化”提供清晰的数据流，也容许不同问题采用不同解压粒度。
- **关键局限**：selector 是单点瓶颈，漏选后 decompressor 无法恢复证据；训练依赖压缩/检索监督，当前为早期文本 QA 预印本，尚无视频实证。
- **一手来源**：[arXiv:2608.00311](https://arxiv.org/abs/2608.00311)

### 30. Gated Delta Networks: Improving Mamba2 with Delta Rule

- **时间 / 机构 / 类别**：2024-12；NVIDIA Research；固定大小 recurrent associative memory。
- **核心机制**：在矩阵值状态的 delta-rule 写入上加入 data-dependent gate：gate 可快速擦除旧状态，delta update 则按 key 精确修正其关联 value；同时保留可并行训练的 chunkwise 形式。论文也探索与 sliding-window attention / Mamba2 组合的 hybrid 模型。
- **视觉记忆启示**：矩阵状态可作为在线“视觉 key→value 关联表”，门控负责场景切换时遗忘，delta-rule 负责更新同一实体的外观/位置；再用局部 attention 保留近期细节。
- **关键局限**：固定矩阵会因键不正交而干扰，精确回取任意历史细节通常不及 full attention；强覆盖 gate 可能把暂时消失但稍后重现的实体过早忘掉。
- **一手来源**：[arXiv:2412.06464](https://arxiv.org/abs/2412.06464)

## 技术演化脉络

1. **从固定模式到输入自适应、再到原生训练。** MInference 用少数可解释 pattern 覆盖 head；Quest/SnapKV 把选择条件放到 query 或 observation window；SeerAttention 学 gate，FlexPrefill 学会按输入选模式/预算；NSA、MoBA 则从训练阶段让模型形成可执行的稀疏性。MMInference 进一步说明视觉 token 需要自己的 Grid 与 modality-aware 排布。
2. **压缩轴从“删 token”扩展到 head、layer、channel、rank 与系统复用。** DuoAttention 在 head 维分工，PyramidKV/VL-Cache 在 layer/modality 维分预算，KIVI/TurboQuant 降低数值位宽，MLA/xKV 压缩特征宽度或跨层冗余，Cache-Craft 复用重复块。它们彼此大多正交，未来系统不会只选一种。
3. **记忆从随长度增长的 KV，转向固定状态与分级存储。** Gated DeltaNet/KDA 用 recurrent matrix state，Titans/TTT/LaCT 把上下文写入 fast weights，MemoryLLM 用可自更新 latent pool，M+ 将 GPU 短期池与 CPU 长期库连接，Engram 则把静态知识变成 O(1) lookup。
4. **读取从“直接消费压缩 token”走向选择—恢复。** ComprExIT 改善写入时的跨层取材和 slot 全局分工，SeDeM 则在读取时按问题选择并解压；二者拼出适合视频的完整链条：多尺度写入 → 稀疏索引 → 问题条件选择 → 局部高保真恢复。

## 关键矛盾与对视觉记忆的约束

- **有界成本 vs. 精确回忆**：固定 cache/state 必然产生干扰或删除；需要保留一个稀疏但可精确回看的原始证据通道，而不是只靠单个连续摘要。
- **query-aware vs. query-agnostic**：前者选择准但问题必须先到，后者可复用但会错过罕见未来需求。长视频更合理的是“问题前用重建/新奇度写入，问题后再 query-aware 读出”。
- **token 重要性 vs. 事件完整性**：逐 token Top-k 容易保住显著物体却丢动作、关系和因果。memory unit 应从 patch/token 升级为可变长 shot、event、tracklet，并允许一个事件包含多种保真层级。
- **写入压缩 vs. 读取带宽**：极小 slot 容量便宜，却会让 decoder 无法恢复细节。SeDeM 式选择性解压提示：存储格式与消费格式应分离，并明确计算 write、index、read、decompress 四段成本。
- **免训练插件 vs. 原生架构**：SnapKV/Quest/MInference 易部署但受既有 attention 表征限制；NSA/MLA/KDA/TTT 可从训练中塑造记忆，却需要大规模预训练和新 kernel。研究方案应先用插件验证因果，再决定是否原生训练。
- **算法稀疏 vs. 硬件可兑现**：非结构化 Top-k 可能理论 FLOPs 很低、真实延迟却不降；block、page、chunk、确定性地址与预取必须成为方法的一部分，而非事后系统优化。
- **文本代理目标 vs. 视觉 QA 价值**：重建损失、attention mass、surprise 都不等同于“未来问题会问什么”。视觉记忆评估需单独测：短暂细节、跨镜头实体绑定、顺序/计数、因果链、多轮问题变化，以及删除后是否可恢复。

## 最值得用于后续方案设计的组合接口

1. **NSA/MMInference 的三级读取** × **ChunkKV 的事件单元**：全局事件摘要、少量原始关键帧、近期连续窗口。
2. **KVzip/ComprExIT 的问题前写入** × **Quest/M+/SeDeM 的问题后检索与解压**：同时解决未知问题与高保真读出。
3. **PyramidKV/VL-Cache 的层/模态预算** × **KIVI/TurboQuant/xKV 的位宽/秩压缩**：在不额外丢时间位置的前提下先压缩冗余。
4. **Titans/KDA/Gated DeltaNet 的在线状态** × **稀疏原始证据库**：固定成本语义状态负责快速理解，证据库负责可验证的精确回看。
5. **Nested Learning/LaCT 的多时间尺度更新** × **事件边界感知路由**：帧、镜头、事件、角色分别以不同频率写入和遗忘，避免“一把尺子”的统一 cache policy。
