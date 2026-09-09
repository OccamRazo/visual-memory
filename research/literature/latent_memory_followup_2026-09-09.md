# 潜记忆补充调研：20 篇新作与 20 篇视频流工作的联合报告

资料截止：**2026-09-09**。配套：[12 页周报内容稿](../../writing/weekly-reports/2026-09-09/latent_memory_12slides_2026-09-09.md) · [周报阅读版](../../writing/weekly-reports/2026-09-09/latent_memory_12slides_2026-09-09.html) · [逐篇来源与结构化记录](latent_memory_sources_2026-09-09.json)。

## 1. 范围与阅读口径

本次新增 **20 篇**，均按 arXiv submission history 核实为 **2026 年首次提交**，且不在[上一轮 79 篇目录](visual_memory_work_catalog_2026-09-08.md)中。复用其中“视频流的潜空间、递归状态与 KV 记忆”**A01–A20 共 20 篇**，形成 **40 篇主表**。另补充 MemGen、VisMem 两篇团队脉络前作；两者首发于 2025 年，不计入新增 20 篇。这里将“26 年之后”按本轮语境解释为“2026 年以来”，不收录截止日以后的材料。

入选依据是**可核验的知名企业研究组或领域研究团队**，具体署名在逐篇表中列出；2026 年新作尚不足以统一用引用量判断影响力，不宣称每篇均已成为高影响经典。团队名称不表示所有署名单位共同牵头，也不将同属 NUS 的作者视为同一实验室。

逐篇核对题名、首发时间、作者机构与摘要，并对记忆构件定点核读；代表工作进一步核读方法、训练、实验和限制。表中“机制／证据”归纳文献，“边界”是本报告的分析。成绩仅作作者报告的证据范围，不跨骨干、数据集和资源预算排名；本轮未复现实验。新作链接固定到本次核读版本，旧 A 类沿用上一轮已核验条目和首发口径。

**潜记忆的操作定义：**将历史、事实或训练知识保存在可被后续计算利用的连续向量、KV、动态矩阵或参数模块中。仅用向量检索原始文本、却没有潜状态写入／演化机制的通用 RAG，不自动算潜记忆；“潜空间推理”也不自动意味着持久历史记忆。

为避免混淆，需要同时描述四个轴：

| 轴 | 需要回答的问题 | 例子 |
|---|---|---|
| 存在哪里 | 向量序列、KV、动态矩阵还是训练参数？ | LCLM、IndexMem、Metis、上下文 LoRA |
| 何时写入 | 预训练、离线构库、在线观察，还是问题出现后？ | Engram 与 Mem-W 写入时机不同 |
| 怎样读取 | 直接消费、先重建、检索后压缩，还是残差补偿？ | One Token、NextMem、LatentMem、IndexMem |
| 保留什么 | 实例事实、可复用经验、当前工作状态还是通用知识？ | NextMem、Mem-W、δ-mem、Memory Grafting |

## 2. 五条技术分支

五类按**主要技术贡献**分组，并非互斥物理形态。例如 LycheeMemory 的长期库属于 KV，但本报告将它放在压缩后读取路线；EvoEmbedding 内部递归，但主要贡献是动态检索表征。

| 分支 | 总体思路 | 新作 | 旧视频流工作 | 周报代表 |
|---|---|---|---|---|
| I. 潜表示压缩与事实读取 | 把历史变成较短潜记录，再研究如何读回事实 | L01, L02, L03, L04, L05（5） | A08, A14, A16, A20（4） | LCLM |
| II. 按任务生成与编排潜记忆 | 根据角色、任务与当前推理状态组织和调用记忆 | L06, L07, L08, L09, L10, L11（6） | A01, A02, A06, A11（4） | Mem-W |
| III. 递归状态与在线关联记忆 | 以固定维状态持续吸收历史，使其参与后续计算 | L12, L13（2） | A09, A17, A18, A19（4） | Metis |
| IV. KV 的选择、凝固与淘汰补偿 | 在保留部分精确缓存的同时处理被压缩或淘汰信息 | L14, L15, L16, L17（4） | A03, A04, A05, A07, A10, A12, A13, A15（8） | IndexMem |
| V. 参数与条件查表中的潜知识 | 把知识写入可选参数模块或条件向量表 | L18, L19, L20（3） | 无；用于补足知识记忆维度（0） | Context Distillation |

## 3. 新增 20 篇：逐篇介绍

### I. 潜表示压缩与事实读取

| ID／工作／首发 | 团队依据 | 记忆与方法简介 | 文献中的验证范围 | 边界／本报告判断 |
|---|---|---|---|---|
| **L01 LCLM**<br>[End-to-End Context Compression at Scale](https://arxiv.org/abs/2606.09659)<br>2026-06-08；核读 v1 | [NYU、Princeton、UMD、Columbia、Harvard、Meta FAIR、LLNL；Izmailov / Goldblum / Goldstein / Zhuang Liu 等团队](https://arxiv.org/html/2606.09659v1) | **分块 soft tokens；可回取原文。**编码器把局部文本聚合为连续 token，经投影交给解码器直接消费；分阶段对齐后联合训练读写接口。agent 可先浏览压缩全文，再用 EXPAND 取回细节。 | 0.6B 编码器、4B 解码器，每个比例继续预训练超过 350B token；比较 4、8、16 倍压缩的质量、时延与显存。 | 训练规模大；EXPAND 依赖原文仍在外部存储，不能作为固定总容量或不可回看视频的直接解法。 |
| **L02 NextMem**<br>[NextMem: Towards Latent Factual Memory for LLM-based Agents](https://arxiv.org/abs/2603.15634)<br>2026-02-26；核读 v1 | [NUS（Tat-Seng Chua、Yang Zhang）、人大（Xu Chen）、CUHK、中国科大](https://arxiv.org/html/2603.15634v1) | **可重建的潜事实记录；可量化。**自回归自编码器把事实压成潜序列，经重建对齐与逐步潜变量替换训练，再量化存储；强调历史事实的可恢复性。 | 原文评测记忆检索、重建、压缩比例与量化鲁棒性，并比较直接潜空间读取和先重建再回答。 | 主要读取路径需要重建事实文本，不能将存储压缩率直接当成生成输入节省；精确细节与压缩率仍有取舍。 |
| **L03 One Token per Multimodal Evidence**<br>[One Token per Multimodal Evidence: Latent Memory for Resource-Constrained QA](https://arxiv.org/abs/2606.10572)<br>2026-06-09；核读 v1 | [NUS School of Computing（Wee Sun Lee 团队）](https://arxiv.org/html/2606.10572v1) | **每条文本／图像证据一个高维潜 token。**小型压缩器联合学习重建、检索对齐和答案蒸馏；问题检索潜 token 后，将其直接送入生成模型，避免每次重读原始证据。 | 文本与多模态 QA；作者报告生成器 token 使用量为所比 RAG 的约 1/3–1/10。 | 一个高维浮点向量不等于一个文本 token 的存储字节；证据库大小和检索索引仍随条目数增长。 |
| **L04 LycheeMemory**<br>[Dynamic Long Context Reasoning over Compressed Memory via End-to-End Reinforcement Learning](https://arxiv.org/abs/2602.08382)<br>2026-02-09；核读 v1 | [哈工大深圳计算与智能研究院（Min Zhang、Meishan Zhang、Baotian Hu）](https://arxiv.org/html/2602.08382v1) | **压缩 KV 长期库＋离散文本工作记忆。**分块压缩成 memory-token KV；门控依问题和当前工作记忆决定读取，推理器迭代更新工作状态。压缩器和推理器联合 RL，门控单独监督训练。 | ACL 2026；RULER-HQA 等多跳任务，考察长上下文外推与推理成本。 | 潜空间部分是长期 KV 库；工作记忆是固定长度文本窗口。读取上下文有界不意味着长期库总大小有界。 |
| **L05 EvoEmbedding**<br>[EvoEmbedding: Evolvable Representations for Long-Context Retrieval and Agentic Memory](https://arxiv.org/abs/2606.21649)<br>2026-06-19；核读 v2 | [南京大学（Chaoyou Fu、Caifeng Shan、Junlan Feng）](https://arxiv.org/html/2606.21649v2) | **递归潜状态辅助检索表示。**顺序编码时不断更新潜记忆，结合当前内容生成随历史变化的 embedding；用记忆队列和联合检索训练缓解递归表征退化。 | EvoTrain-180K；长上下文检索、个性化和 agent RAG，测试超出训练窗口的上下文。 | 主要改进检索器的状态表示，并非把检索命中的全部证据直接变成生成器的潜输入；需和直接读取潜记忆区分。 |

### II. 按任务生成与编排潜记忆

| ID／工作／首发 | 团队依据 | 记忆与方法简介 | 文献中的验证范围 | 边界／本报告判断 |
|---|---|---|---|---|
| **L06 L²-VMAS**<br>[Dual Latent Memory for Visual Multi-agent System](https://arxiv.org/abs/2602.00471)<br>2026-01-31；核读 v2 | [NUS（Shuicheng Yan、Xiaobin Hu）、复旦、清华、浙大、上海 AI Lab 等](https://arxiv.org/html/2602.00471v2) | **视觉与思考双潜记忆。**将多 agent 的感知信息与思考信息分开表示，以潜记忆承接协作历史；根据熵相关信号按需触发访问，减少反复文本转述。 | 比较不同骨干、规模和多 agent 组织方式下的准确率及 token 成本。 | 双记忆按感知／思考划分，并非天然等同短期／长期；多轮协作收益尚不能证明跨天实例事实保持。 |
| **L07 Mem-W**<br>[Mem-W: Latent Memory-Native GUI Agents](https://arxiv.org/abs/2605.09317)<br>2026-05-10；核读 v1 | [LV-NUS Lab；NUS / NTU（Guibin Zhang、Shuicheng Yan）](https://arxiv.org/html/2605.09317v1) | **同一接口承载跨任务经验和当前任务历史。**共享 Q-Former 压缩器将观察—动作片段变为潜 token；历史成功／失败轨迹与本轮较早步骤共同前置给 GUI policy，保留近期原始上下文。 | 冻结 agent，先自蒸馏再按任务结果训练压缩器；Web／移动端四组评测，并消融两类记忆。 | 跨任务库仍存轨迹；Top-M 检索冻结且不反传。固定每段潜 token 数不等于系统总存储固定。 |
| **L08 LaMem-VLA**<br>[Dual Latent Memory in Vision-Language-Action Models for Robotic Manipulation](https://arxiv.org/abs/2607.07608)<br>2026-07-08；核读 v1 | [NUS（Shuicheng Yan、Xiaobin Hu）、南京理工（Xiangbo Shu）、浙大（Wenguan Wang）](https://arxiv.org/html/2607.07608v1) | **短／长期视觉潜记忆。**curator 管理双库，seeker 依当前多模态状态检索，condenser 压成潜 token，weaver 与当前观察、指令交织后指导动作。 | SimplerEnv 与 LIBERO 机器人操作；原文比较记忆构件对动作成功的贡献。 | 动作成功检验任务充分性；并不等同于任意历史细节可重建。与未知未来问题的视频写入协议有差别。 |
| **L09 LatentMem**<br>[LatentMem: Customizing Latent Memory for Multi-Agent Systems](https://arxiv.org/abs/2602.03036)<br>2026-02-03；核读 v2 | [同济、上海 AI Lab、CUHK、南京大学、上海交大等（Muxin Fu、Yu Cheng、Yang Yang 等）](https://arxiv.org/html/2602.03036v2) | **按 agent 角色定制的潜经验。**外部 bank 保留原始交互轨迹；composer 结合检索经验、角色和当前上下文生成短潜记忆，以 LMPO 将任务信号传给 composer。 | 在多个 MAS 框架、任务上比较角色定制和记忆效率。 | 同一历史可生成不同角色的记忆；这并不保证共享事实一致。按 v2 署名描述，不将其直接归入颜水成团队。 |
| **L10 ElasticMem**<br>[ElasticMem: Latent Memory as a Learnable Resource for LLM Agents](https://arxiv.org/abs/2605.30690)<br>2026-05-29；核读 v1 | [UIUC（Jiaxuan You、Ge Liu）、NTU](https://arxiv.org/html/2605.30690v1) | **可变预算的检索潜记忆。**离线 bank 保存检索键与内容缓存，模型由推理隐藏状态检索，为每条命中记忆分配可变潜 token 数；GRPO 学习整套使用策略。 | MemorySuite 的 QA 与 ALFWorld，比较检索、自适应预算及 token 成本。 | ALFWorld 是文本交互式具身环境，不能写成视觉机器人实验；bank、查询时预算和策略训练成本需分别计算。 |
| **L11 HyMEM**<br>[Hybrid Self-evolving Structured Memory for GUI Agents](https://arxiv.org/abs/2603.10291)<br>2026-03-11；核读 v1 | [UC San Diego（Biwei Huang）、Abel.ai](https://arxiv.org/html/2603.10291v1) | **离散概念图＋连续轨迹记忆。**图的高层符号节点组织低层连续轨迹 embedding，支持多跳检索、节点演化和执行时工作记忆刷新，连接经验结构与多模态细节。 | GUI agent；比较图结构、全局演化和局部更新，在开源骨干上测试任务完成。 | 属于结构与潜表示混合方法；不能仅因含 embedding 就描述为整个系统端到端潜空间记忆。 |

### III. 递归状态与在线关联记忆

| ID／工作／首发 | 团队依据 | 记忆与方法简介 | 文献中的验证范围 | 边界／本报告判断 |
|---|---|---|---|---|
| **L12 Metis**<br>[Metis: Memory Foundation Model](https://arxiv.org/abs/2607.26760)<br>2026-07-29；核读 v2 | [MemTensor、人大（Xu Chen）、NUS（Tat-Seng Chua、Yang Zhang）、上海交大、同济等](https://arxiv.org/html/2607.26760v2) | **Transformer 内部持久矩阵状态。**Metis block 以 local memory 保存动态矩阵及归一化状态，hyper memory 选择并变换输入隐藏表示，学习跨交互的写入和读取程序。 | 记忆重建、操作与正则目标联合训练；原文评测长程记忆使用，并发布模型与实现。 | 测试交互更新动态状态，静态模型权重冻结；不是每步对完整基础模型反向传播。固定矩阵并不保证无限无损记忆。 |
| **L13 δ-mem**<br>[$\delta$-mem: Efficient Online Memory for Large Language Models](https://arxiv.org/abs/2605.12357)<br>2026-05-12；核读 v1 | [NTU / DeCLaRe Lab（Soujanya Poria）、Mind Lab、复旦、上海交大等](https://arxiv.org/html/2605.12357v1) | **delta-rule 在线关联矩阵。**在冻结全注意力骨干旁维护小型状态，以 delta rule 写入历史，读出结果生成注意力计算的低秩修正，避免替换整个骨干。 | MemoryAgentBench、LoCoMo 与通用能力；原文展示小状态配置下的记忆任务增益。 | 8×8 是作者配置中的状态尺寸描述，不是整个系统的字节数；必须额外计入各层／头复制与普通 KV。 |

### IV. KV 的选择、凝固与淘汰补偿

| ID／工作／首发 | 团队依据 | 记忆与方法简介 | 文献中的验证范围 | 边界／本报告判断 |
|---|---|---|---|---|
| **L14 IndexMem**<br>[IndexMem: Learned KV-Cache Eviction with Latent Memory for Long-Context LLM Inference](https://arxiv.org/abs/2605.25475)<br>2026-05-25；核读 v2 | [HKUST（Yike Guo、Sirui Han）、浙大；微软研究院有官方论文条目](https://arxiv.org/html/2605.25475v2) | **保留 KV＋淘汰内容的潜状态。**learnable indexer 预测保留价值；淘汰 KV 被写入固定大小潜状态，读出以残差补偿注意力，避免把潜摘要直接塞进 softmax 造成竞争。 | Qwen、Mistral、Llama 上的 RULER、NIAH、LongBench；原文分析 indexer 和潜记忆贡献。 | 补偿是近似，不能恢复被删 token 的全部精确贡献；论文也指出极端压缩及分布外场景的限制。 |
| **L15 RetentiveKV**<br>[RetentiveKV: State-Space Memory for Uncertainty-Aware Multimodal KV Cache Eviction](https://arxiv.org/abs/2605.04075)<br>2026-04-14；核读 v1 | [浙江大学、阿里巴巴](https://arxiv.org/html/2605.04075v1) | **SSM 汇聚待淘汰的多模态 KV。**针对视觉信息的延迟重要性，用熵相关状态转移将低注意力 token 写入连续状态，并在后续语义相关时重新调用。 | 多模态评测中的 KV 压缩、解码速度与任务质量。 | 视觉 KV 改进不自动成立于严格单遍长视频；应区分提问后解码压缩与问题未知时的流式写入。 |
| **L16 FlashMem**<br>[FlashMem: Distilling Intrinsic Latent Memory via Computation Reuse](https://arxiv.org/abs/2601.05505)<br>2026-01-09；核读 v2 | [北航（Zengchang Qin）、中科院计算所、UCAS、VinUniversity](https://arxiv.org/html/2601.05505v2) | **复用已有 KV 的潜记忆凝固。**Shared-KV Consolidator 直接读取推理骨干缓存生成潜记忆，配合基于注意力熵的触发器，减少另设编码器再次处理历史的计算。 | Findings of ACL 2026；问答、推理、摘要等任务，比较质量和记忆生成成本。 | 复用计算有工程价值；“末隐藏状态是充分统计量”的论证不能当成有限精度下无损保留所有历史的普遍保证。 |
| **L17 MemRoPE**<br>[MemRoPE: Training-Free Infinite Video Generation via Evolving Memory Tokens](https://arxiv.org/abs/2603.12513)<br>2026-03-12；核读 v1 | [USC（C.-C. Jay Kuo、Peter A. Beerel）](https://arxiv.org/html/2603.12513v1) | **双速 EMA 潜 KV 与动态位置编码。**把历史键聚合成长／短期 memory tokens；存储未施加 RoPE 的键，读取时重新附加位置，避免混合不同旋转相位。 | 免训练长视频生成，评测时间一致性、身份保持和画质。 | 生成一致性与历史事实可回答性不同；EMA 可能抹平短暂事件。其位置处理对视频 KV 合并有迁移价值。 |

### V. 参数与条件查表中的潜知识

| ID／工作／首发 | 团队依据 | 记忆与方法简介 | 文献中的验证范围 | 边界／本报告判断 |
|---|---|---|---|---|
| **L18 Context Distillation as Latent Memory Management**<br>[Context Distillation as Latent Memory Management](https://arxiv.org/abs/2605.28889)<br>2026-05-27；核读 v1 | [CUHK（Qiang Xu）、华为诺亚方舟实验室](https://arxiv.org/html/2605.28889v1) | **每个上下文一个 LoRA 潜记忆模块。**将不同上下文分别蒸馏进 adapter；先外部检索候选，再内部路由，借首 token 熵决定是否启用，以共享前缀 KV 降低切换成本。 | SQuAD、NarrativeQA 等；分开评测存储方式、选哪个模块和是否调用。 | 写入需要上下文蒸馏训练；检索索引和全部 adapter 也占空间。不是免训练的在线 state update。 |
| **L19 Memory Grafting**<br>[Memory Grafting: Scaling Language Model Pre-training via Offline Conditional Memory](https://arxiv.org/abs/2605.20948)<br>2026-05-20；核读 v1 | [清华大学（Chun Yuan）、微软亚洲研究院（Yeyun Gong、Yan Lu）](https://arxiv.org/html/2605.20948v1) | **外部 n-gram 条件潜向量库。**离线运行冻结模型，取高频 n-gram 末 token 隐藏表示建库；接收模型按最长后缀精确查表，经投影与门控注入，未命中用 Engram 回退。 | 同架构、同预训练预算下，对比 MoE 和 Engram 的语言建模与下游任务。 | 属于预训练知识容量扩展，库在推理时通常静态；不能直接宣称 agent 会在线记住新经历。 |
| **L20 Engram**<br>[Conditional Memory via Scalable Lookup: A New Axis of Sparsity for Large Language Models](https://arxiv.org/abs/2601.07372)<br>2026-01-12；核读 v2 | [DeepSeek-AI、北京大学（Huishuai Zhang、Dongyan Zhao）](https://arxiv.org/html/2601.07372v2) | **可学习 n-gram embedding 条件记忆。**局部 token 模式经压缩与哈希查表，读取训练获得的向量，由上下文门控注入骨干；将静态知识查找与神经计算分开扩容。 | 严格等参数／等 FLOPs 的 MoE 对比，以及知识、推理与长上下文任务。 | “潜”指读出的连续向量；地址是离散 token 模式，主要是训练期知识记忆，区别于交互实例记忆。 |

## 4. 旧调研 A01–A20：与新路线连接

以下 20 篇不计入本轮新增。保留旧 ID 方便对照，简介来自上一轮目录；最后一列给出本轮归类和迁移判断。旧论文作为技术源流保留，不受本轮“新增必须 2026 首发”的时间限制。

| ID／工作／时间 | 团队 | 记忆机制简介 | 本轮主分类与边界 |
|---|---|---|---|
| **A01** **LatentStream**<br>[Beyond Retrieval: Progressive Latent Memory Evolution for Streaming Video Understanding](https://arxiv.org/abs/2609.04131)<br>2026-09-03 | [蚂蚁集团、NUS、CUHK、南京理工](https://arxiv.org/html/2609.04131) | 视频流；潜变量＋检索。短中长期记忆在固定预算内整合；问题到达后逐步扩展潜变量感受范围，并用熵相关奖励学习证据内化。 | **II**。写入和问题后的潜变量演化分属两阶段；潜变量更新不能直接归为模型权重更新。 |
| **A02** **StreamFlow**<br>[StreamFlow: Dynamic Memory Flows for Streaming Video Understanding](https://arxiv.org/abs/2608.10949)<br>2026-08-11 | [NTU（Bo An）、NUS（Shuicheng Yan）、同济、Michigan、HKUST](https://arxiv.org/pdf/2608.10949) | 视频流；潜变量＋按需读取。编码前用中期动态信息过滤冗余，长期库保存视觉潜变量；生成中视觉关注减弱时触发历史信息注入。 | **II**。读取策略也会决定记忆价值；注意力指标改善不等于已证明事实忠实性。 |
| **A03** **CausalMem**<br>[Towards a Dynamic and Fixed-budget Memory Bank for Efficient Streaming Video Understanding](https://arxiv.org/abs/2606.25658)<br>2026-06-24 | [厦门大学多媒体可信感知与高效计算教育部重点实验室（纪荣嵘、周易毅）](https://arxiv.org/html/2606.25658) | 视频流；固定预算视觉 bank。在线构造语义基底、识别冗余并维护有容量上限的记忆；写入不依赖尚未到达的问题，可免训练接入。 | **IV**。固定容量仍有不可逆遗忘；应进一步检查罕见细节和远期问题覆盖。 |
| **A04** **OmniMem**<br>[OmniMem: Perturbation-aware Memory Compression for Streaming Audio-Visual LLMs](https://arxiv.org/abs/2606.07577)<br>2026-05-26 | [字节跳动、剑桥大学、清华大学](https://arxiv.org/html/2606.07577) | 音视频流；分模态 KV。用扰动敏感性估计保留价值，分别分配音频和视觉预算；另提供预算感知微调。 | **IV**。音频与画面可能互补，不能把双模态压缩简化为视觉 token 排序。 |
| **A05** **MuKV**<br>[MuKV: Multi-Grained KV Cache Compression for Long Streaming Video Question-Answering](https://arxiv.org/abs/2605.22269)<br>2026-05-21 | [NUS（Angela Yao）、中国科大](https://arxiv.org/html/2605.22269) | 长视频问答；多粒度 KV。同时在 patch、帧、片段尺度压缩，结合注意力和频率线索，以半层级结构读取历史缓存。 | **IV**。压缩率和最终读取量应与整个历史库占用分别报告。 |
| **A06** **R3-Streaming**<br>[An Efficient Streaming Video Understanding Framework with Agentic Control](https://arxiv.org/abs/2605.17921)<br>2026-05-18 | [微软亚洲研究院、上海交大、宁波东方理工](https://arxiv.org/html/2605.17921) | 视频流；记忆＋agent 控制。把历史压缩、回答时机判断、强模型路由结合，采用时间感知奖励学习何时回答与升级推理。 | **II**。收益同时来自控制与路由，不能全部归因于记忆表示。 |
| **A07** **FlexMem**<br>[Scaling the Long Video Understanding of Multimodal Large Language Models via Visual Memory Mechanism](https://arxiv.org/abs/2603.29252)<br>2026-03-31 | [厦门大学上述教育部重点实验室、国防科大](https://arxiv.org/html/2603.29252) | 长视频；压缩 KV＋局部检索。以视觉记忆机制组合压缩的全局上下文与局部细节检索，扩展现有 MLLM 的长视频处理能力。 | **IV**。全局概述和细节通道应分别消融；不能只按最终输入长度比较资源。 |
| **A08** **FluxMem**<br>[FluxMem: Adaptive Hierarchical Memory for Streaming Video Understanding](https://arxiv.org/abs/2603.02096)<br>2026-03-02 | [复旦可信具身智能研究院（吴祖玄）、上海创智、马里兰大学](https://arxiv.org/html/2603.02096) | 视频流；自适应分层 token。时间上抑制相邻冗余，空间上合并相似内容，动态调节压缩强度以保留流中的变化。 | **I**。低变化不一定低任务价值；细小但决定答案的差异可能被合并。 |
| **A09** **WeaveTime**<br>[WeaveTime: Stream from Earlier Frames into Emergent Memory in VideoLLMs](https://arxiv.org/abs/2602.22142)<br>2026-02-25 | [香港大学、上海科技大学、中山大学（杨思蓓）](https://arxiv.org/html/2602.22142) | 视频流；时间表征＋历史 cache。以时间重建目标学习先后顺序；推理时通过不确定性触发由粗到细的历史读取，区分过去与当前。 | **III**。不仅是选帧方法；应区分训练获得的时间能力与缓存机制贡献。 |
| **A10** **HERMES**<br>[HERMES: KV Cache as Hierarchical Memory for Efficient Streaming Video Understanding](https://arxiv.org/abs/2601.14724)<br>2026-01-21 | [复旦 OpenMOSS、上海创智、NUS](https://hermes-streaming.github.io/) | 视频流；分层 KV。直接把 KV cache 组织成具有不同时间尺度的层级记忆，在持续编码中处理历史，降低提问时的额外开销。 | **IV**。层级缓存不自动保证每种细节都能长期恢复；需核算各层实际字节数。 |
| **A11** **Memento**<br>[Memento: Toward an All-Day Proactive Assistant for Ultra-Long Streaming Video](https://proceedings.iclr.cc/paper_files/paper/2026/hash/3b5f4587a0bdb81ecc6ce9d82320a5c2-Abstract-Conference.html)<br>2026 ICLR；更早首发未核定 | [Deepeleph、清华大学、小红书、北航等](https://openreview.net/pdf/e8fee5c834738ed247230ea336b2d1f5bf0a18cf.pdf) | 全天主动助手；动态视觉记忆。按问题相关性与步骤组织记忆和注意力，并构建长时间视频上的主动响应训练与评测资源。 | **II**。主动响应与被动问答协议不同；Memento54K、MementoBench 不另算论文。 |
| **A12** **StreamingVLM**<br>[StreamingVLM: Real-Time Understanding for Infinite Video Streams](https://arxiv.org/abs/2510.09608)<br>2025-10-10 | [MIT Han Lab、NVIDIA、First Intelligence](https://arxiv.org/html/2510.09608) | 实时视频流；有限 KV 窗口。保留 attention sink、较短视觉历史和较长文本历史，并用与流式推理匹配的重叠短片段训练。 | **IV**。持续运行能力不等于可恢复任意久远的原始视觉证据。 |
| **A13** **StreamMem**<br>[StreamMem: Query-Agnostic KV Cache Memory for Streaming Video Understanding](https://arxiv.org/abs/2508.15717)<br>2025-08-21 | [Meta AI、NYU Agentic Learning Lab](https://arxiv.org/html/2508.15717) | 视频流；问题无关 KV 压缩。在未来问题未知时，用通用上下文中的 token 重要性维护受限视觉 KV 记忆，供后续问题读取。 | **IV**。通用显著性只是未来效用的代理；应检验分布外问题与小目标。 |
| **A14** **Flash-VStream**<br>[Flash-VStream: Efficient Real-Time Understanding for Long Video Streams](https://arxiv.org/abs/2506.23825)<br>2024 前身 / 2025-06-30 扩展 | [清华大学、字节跳动、北京交通大学](https://arxiv.org/html/2506.23825) | 实时视频；概述＋细节记忆。低容量上下文概述与高容量细节补充共同保留历史，异步视频编码与问答支持实时交互。 | **I**。2024 年前身与 2025 年扩展版合并为一个工作家族，避免重复计数。 |
| **A15** **ReKV**<br>[Streaming Video Question-Answering with In-context Video KV-Cache Retrieval](https://arxiv.org/abs/2503.00540)<br>2025-03-01 | [阿里巴巴、上海交大](https://arxiv.org/html/2503.00540) | 视频流；外部 KV 检索。滑窗编码后把历史 KV 存入 RAM/磁盘，问题到来时检索并搬回相关缓存，复用已编码的视频。 | **IV**。GPU 占用受控，但完整外部历史随时长增长；不是固定总存储方案。 |
| **A16** **Video-XL**<br>[Video-XL: Extra-Long Vision Language Model for Hour-Scale Video Understanding](https://arxiv.org/abs/2409.14485)<br>2024-09-22 | [北京智源、北京大学、人大、上海交大等](https://arxiv.org/html/2409.14485) | 小时级视频；可学习 KV 摘要。训练视觉总结 token 汇总区间 KV，结合渐进式训练和动态压缩，在保留细节与长度之间取舍。 | **I**。摘要 token 的训练参数和实例记忆中的 KV 是不同概念。 |
| **A17** **VideoLLaMB**<br>[VideoLLaMB: Long Streaming Video Understanding with Recurrent Memory Bridges](https://arxiv.org/abs/2409.01071)<br>2024-09-02 | [BIGAI 通用人工智能全国重点实验室、北大、北理工、UCSC](https://arxiv.org/html/2409.01071) | 视频流；递归 memory bridge。结合场景切分与跨片段递归记忆桥，将历史语义传递给后续视觉语言推理。 | **III**。递归状态小并不意味着所有可检索历史均为常数容量。 |
| **A18** **VideoStreaming**<br>[Streaming Long Video Understanding with Large Language Models](https://arxiv.org/abs/2405.16009)<br>2024-05-25 | [上海人工智能实验室、香港中文大学](https://arxiv.org/html/2405.16009) | 长视频；传播状态＋选择。片段间传播压缩记忆，再依据问题选择固定数量的相关记忆供语言模型推理。 | **III**。问题条件选择与问题无关写入需分开；固定输入 token 不等于固定历史库存。 |
| **A19** **MA-LMM**<br>[MA-LMM: Memory-Augmented Large Multimodal Model for Long-Term Video Understanding](https://arxiv.org/abs/2404.05726)<br>2024-04-08 | [Meta、马里兰大学（Abhinav Shrivastava）](https://arxiv.org/html/2404.05726) | 视频理解；视觉／查询双 bank。在线编码并保存视觉特征与查询表征，通过记忆融合引用较早内容，避免一次性输入全部视频。 | **III**。较早的模块化基线；其短视频任务成绩不能直接代表多小时记忆效果。 |
| **A20** **MovieChat**<br>[MovieChat: From Dense Token to Sparse Memory for Long Video Understanding](https://arxiv.org/abs/2307.16449)<br>2023-07-31 | [微软亚洲研究院、浙江大学、华盛顿大学](https://arxiv.org/html/2307.16449) | 长视频；稀疏潜空间记忆。借鉴短期与长期记忆分工，把密集视频 token 合并成稀疏长期表示，支持长视频问答。 | **I**。构建了早期潜空间压缩范式；压缩后丢失的信息不能靠更强读取恢复。 |

## 5. 方法脉络：从“保留表示”到“学习记忆接口”

### 5.1 潜表示压缩：关键从长度转向事实能否被读出

早期 MovieChat、MA-LMM 和 Video-XL 将视频历史转成稀疏 token、特征 bank 或总结 KV，使语言模型可以访问更长时间跨度。新一轮文本工作进一步把**写入器与读取器的配合**作为训练对象：LCLM 联合训练编码、投影与解码；One Token 同时优化检索键和可消费内容；NextMem 先保证压缩事实可被重建。它们分别代表“直接阅读”“检索后直接阅读”“先恢复后阅读”三种接口。EvoEmbedding 则表明，历史状态也可以进入检索器本身，而不只进入答案生成器。[LCLM](https://arxiv.org/html/2606.09659v1)、[One Token](https://arxiv.org/html/2606.10572v1)、[NextMem](https://arxiv.org/html/2603.15634v1)、[EvoEmbedding](https://arxiv.org/html/2606.21649v2)。

用统一记号概括这些接口，以下为**本报告的抽象表达，不是某篇论文的原公式**：

$$
\begin{aligned}
z_i &= E_\phi(x_i), \\
\hat y_{\mathrm{direct}} &= D_\theta(q,z_{\mathcal I(q)}), \\
\hat x_i &= R_\psi(z_i), \qquad
\hat y_{\mathrm{reconstruct}} = D_\theta(q,\hat x_{\mathcal I(q)}).
\end{aligned}
$$

这里 $\mathcal I(q)$ 是所选择的记忆集合，$E$ 是写入器，$R$ 是重建器，$D$ 是答案模型。对视频而言，关键问题是颜色、身份、顺序等证据是否仍可读取。LCLM 的按需展开说明，压缩浏览与精确回查可以互补；若任务禁止回看原视频，这条回查路径就必须计入预算，或明确关闭。LycheeMemory 也提醒我们，系统可以同时含潜 KV 长期库和**文本**工作记忆，不能只用一个“latent”标签概括。[LCLM §7](https://arxiv.org/html/2606.09659v1)、[LycheeMemory](https://aclanthology.org/2026.acl-long.365/)。

### 5.2 生成与编排：同一份历史，按当前需求形成不同记忆

Mem-W、LatentMem、ElasticMem 的共同变化是：记忆并非检索到后原样拼接，而是根据使用者、任务或推理状态重新生成潜表示。三个主要控制变量分别是**来源与时间尺度、角色、读取预算**。L²-VMAS 把视觉证据与思考轨迹分开，LaMem-VLA 将短长期潜记忆放进动作生成过程；旧表 StreamFlow 和 LatentStream 则将这种思路带入持续视频观察与问题后的记忆使用。[Mem-W](https://arxiv.org/html/2605.09317v1)、[LatentMem](https://arxiv.org/html/2602.03036v2)、[ElasticMem](https://arxiv.org/html/2605.30690v1)、[L²-VMAS](https://arxiv.org/html/2602.00471v2)、[LaMem-VLA](https://arxiv.org/html/2607.07608v1)。

这条线需要分开评估“检索到了什么”和“压成了什么”。一个能按角色生成高效提示的 composer，可能偏向当前目标而忽略反证；更高成功率也可能来自更多检索或更好控制策略。HyMEM 的启发在于保留离散结构来组织连续经验，使来源和关联仍可管理。**本报告推断：**结构化索引与潜内容不必互相取代，前者可提供身份、时间、版本与证据位置，后者承担密集内容表达；是否有收益仍需同预算实验。[HyMEM](https://arxiv.org/html/2603.10291v1)。

### 5.3 递归与在线关联：状态是历史的持续变换，而非条目的集合

VideoLLaMB、VideoStreaming 通过跨片段状态传播处理长视频。Metis 和 δ-mem 把持续状态更紧密地嵌入模型计算：前者学习原生记忆操作，后者以小型关联矩阵提供注意力修正。这一脉络可以抽象成：

$$
M_t = U_\phi(M_{t-1},h_t), \qquad r_t = R_\psi(M_{t-1},q_t).
$$

$M_t$ 是实例动态状态，$\phi,\psi$ 是训练得到的更新与读取参数。**动态状态变化不等于基础模型权重更新**。Metis 论文把部分状态称为 dynamic parameters，但其交互阶段通过前向记忆程序更新，静态权重保持冻结；不能因此写成每轮对整个模型做测试时梯度训练。[Metis §3](https://arxiv.org/html/2607.26760v2)、[官方实现](https://github.com/MemTensor/Metis)、[δ-mem](https://arxiv.org/html/2605.12357v1)。

矩阵状态有利于约束运行内存，也使“哪一条事实写入了哪一部分”更难定位。对于视频事实问答，需要单独检查干扰写入、顺序交换、实体覆盖和罕见短事件。测试一个模型能否连续运行很久，与测试它能否回答很久以前的细节，是不同实验。

### 5.4 KV 路线：从筛选缓存，到给遗忘的信息保留补偿通道

ReKV 将完整历史 KV 放到外部介质，问题到来后检索；StreamMem、MuKV、OmniMem、HERMES 等研究在预算约束下选择或分层组织缓存。IndexMem 与 RetentiveKV 更进一步：被淘汰的内容仍可进入一个紧凑状态，供后续计算近似调用。FlashMem 则从计算复用切入，利用已有 KV 凝固潜记忆；MemRoPE 提醒我们，跨时间聚合键值时必须同时处理位置编码。[IndexMem](https://arxiv.org/html/2605.25475v2)、[RetentiveKV](https://arxiv.org/html/2605.04075v1)、[FlashMem](https://aclanthology.org/2026.findings-acl.230/)、[MemRoPE](https://arxiv.org/html/2603.12513v1)。

可将“保留＋补偿”的思想概括为：

$$
\begin{aligned}
K_t,V_t &= \operatorname{Keep}(\mathcal C_t;B), \\
M_t &= U(M_{t-1},\operatorname{Evict}(\mathcal C_t;B)), \\
o_t &= \operatorname{Attention}(q_t,K_t,V_t)+R(M_t,q_t).
\end{aligned}
$$

该式是路线示意，省略原论文的归一化、门控和层间处理。它表明“精确缓存”和“有损潜状态”可承担不同职责。潜状态提供的是近似补偿，不能据此认定被删除证据仍然完整。视频生成中的身份一致性也不能替代问答中的事实保持评测。

### 5.5 参数与条件查表：知识容量和经历记忆需要分别讨论

Context Distillation 把某个上下文蒸馏进独立 LoRA，因此“存什么、选哪个、是否启用”成为显式管理问题。Engram 按局部 token 模式读取训练得到的向量表；Memory Grafting 则从另一个冻结模型离线抽取隐藏表示来构建条件记忆。三者都在潜表示中保存知识，但写入来源与更新时机不同。[Context Distillation](https://arxiv.org/html/2605.28889v1)、[Engram](https://arxiv.org/html/2601.07372v2)、[Memory Grafting](https://arxiv.org/html/2605.20948v1)。

这条线补充了上一轮以视觉历史为中心的分类：**参数式记忆并不限于在线快权重**，也包含离线蒸馏的模块与预训练条件表。对当前视频问题，它们更适合作为“通用知识／可复用技能”的参照；只有证明能写入新观察并区分具体事件后，才能称为该视频的实例记忆。不能把知识表容量直接换算成可记住的视频时长。

## 6. 颜水成／NUS 相关脉络

以下连线表示本报告观察到的共同设计主题和任务扩展，**不表示原论文证明了严格继承关系，也不代表团队完整发表列表**。

| 工作 | 首发／是否计入新 20 篇 | 简介与脉络位置 |
|---|---|---|
| [MemGen](https://arxiv.org/abs/2509.24704) | 2025-09-29；补充前作 | NUS Guibin Zhang、Muxin Fu、Shuicheng Yan。trigger 决定何时调用，weaver 生成可穿插到推理中的潜记忆。强调经验如何影响推理；ICLR 2026 正式发表不改变首发年份。[会议版](https://openreview.net/pdf/5502f3ee13172b87f448fa27ffdf174d66216628.pdf)。 |
| [VisMem](https://arxiv.org/abs/2511.11007) | 2025-11-14；补充前作 | NUS Shuicheng Yan、Xiaobin Hu 等与复旦、清华、vivo 等合作。短期视觉细节与长期语义潜记忆互补，通过触发读取缓解长推理中的视觉依据减弱；是视觉任务内的记忆，不能直接等同跨天观察日志。[CVPR 2026 正式版](https://openaccess.thecvf.com/content/CVPR2026/papers/Yu_VisMem_Latent_Vision_Memory_Unlocks_Potential_of_Vision-Language_Models_CVPR_2026_paper.pdf)。 |
| L06 L²-VMAS | 2026-01-31；新增 | 将视觉与思考潜记忆用于多 agent 协作，强调避免文本交流造成感知内容损失。 |
| L07 Mem-W | 2026-05-10；新增 | 把跨任务经验与本轮工作记忆统一成 GUI policy 可消费的潜 token。 |
| L08 LaMem-VLA | 2026-07-08；新增 | 进一步面向机器人操作，将双库检索与潜记忆融合放入动作生成。 |
| [A02 StreamFlow](https://arxiv.org/abs/2608.10949) | 2026-08-11；旧表 | NTU Bo An、NUS Shuicheng Yan 等合作；将动态信息过滤和推理期间按需读取用于视频流。 |
| [A01 LatentStream](https://arxiv.org/abs/2609.04131) | 2026-09-03；旧表 | 蚂蚁、NUS 等合作，署名含 Shuicheng Yan；在固定预算观察后，按问题逐步演化潜变量以整合相关视觉记忆。 |

共同主题可概括为：**按需触发 → 潜表示生成／交织 → 多来源或多时间尺度 → 视觉协作、GUI、动作与流式视频**。其中“生成时补入记忆”不等于“原始证据以同样形式被永久保存”，阅读这些论文时仍应追问底层 bank 存了什么。

NUS 内另有两条相关但不同的合作线：**Tat-Seng Chua / Yang Zhang** 参与 NextMem 与 Metis，分别偏事实压缩和模型原生状态；**Wee Sun Lee** 团队的 One Token 偏资源受限多模态证据读取。LatentMem 按本次核读 v2 的署名列为同济、上海 AI Lab、CUHK 等合作，不仅凭作者曾与 NUS 合作就归入颜水成团队。

## 7. 对视频记忆研究的可检验启发

以下是**待验证方向**，不作为已经成立的方法结论，也不改变现有项目方案。

| 可检验问题 | 文献出发点 | 最小对照与指标 |
|---|---|---|
| 潜内容是否真的保住关键事实？ | NextMem、LCLM、One Token | 同字节预算比较直接答、重建后答；分别测实体、属性、时间、证据组完整率。 |
| 精确片段与潜补偿是否互补？ | IndexMem、RetentiveKV、ReKV | 固定总预算，比较只留 KV、只用潜状态、二者混合；控制编码器与读取计算。 |
| 未知未来问题时，学到的预算策略能否泛化？ | ElasticMem、LatentStream、StreamFlow | 写入阶段禁止接触测试问题；按不同问题类型和时间跨度评估，避免查询泄漏。 |
| 多来源记忆能否保留证据身份与顺序？ | Mem-W、L²-VMAS、HyMEM | 打乱写入顺序、交换实体名、插入相似反例；测答案正确率和来源定位一致性。 |
| 递归状态会在何时被干扰覆盖？ | Metis、δ-mem、VideoLLaMB | 注入逐量干扰与矛盾更新；画历史跨度—保留率曲线，固定状态大小与数值精度。 |

资源比较至少分开报告：

$$
B_{\mathrm{total}}=B_{\mathrm{latent}}+B_{\mathrm{KV}}+B_{\mathrm{raw}}+B_{\mathrm{index}}+B_{\mathrm{adapter}}.
$$

这里统计实例记忆和可调用记忆库占用；基础骨干及共享压缩器权重另报，避免相同权重被重复计入。还应记录构库成本、每步写入成本、首答时延、后续查询成本及是否允许原文／原视频回查。**固定输入长度、固定 GPU cache、固定总记忆**是三种不同约束。

## 8. 筛除记录与材料说明

本轮没有用以下材料补足数量：2025 首发的 MemGen、VisMem 和 Apple Hierarchical Memories；仅讨论文字工作状态的 [GRU-Mem](https://arxiv.org/abs/2602.10560)；以任务内自回归潜推理为主、未充分建立持久历史记忆的 [Latent Memory Palace](https://arxiv.org/abs/2607.08724)；以及机构／影响力依据尚不足的部分新预印本。它们可作邻近参考，但与新增主表采用的口径不同。

配套 JSON 保存首发日期、核读版本、团队依据、方法归纳、边界与来源定位，不保存论文全文。周报采用五条路线各“总体介绍＋代表工作”两页；正文正好 10 页，封面和结束页另计。代表论文图均来自原文，来源记录见周报 assets/README.md；没有改写图中的实验数字。
