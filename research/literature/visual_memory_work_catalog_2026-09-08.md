# 大模型与 Agent 视觉记忆：79 篇工作分类表

> 调研截止：2026-09-08。配套阅读：[方法脉络综述](visual_memory_survey_2026-09-08.md)。

## 1. 范围、来源与计数

本表收录 **79 篇独立工作：65 篇方法／系统、14 篇以评测或数据为主的工作**。其中 **46 篇的 arXiv 首次提交在 2026 年**；另有 Memento、EgoMemory 两篇确认于 2026 年正式公开的会议论文，更早预印本首发时间未核定，不混入前述首发统计。其余为建立脉络所需的早期工作。条目在各类内优先呈现 2026 年成果，而非按引用量排序。

筛选采用以下可复核规则：

- **任务相关**：明确保留并复用视觉历史，或直接评测这种能力。纳入视频理解、具身规划与操作、GUI、个人多模态记忆，以及有可迁移机制的世界模型和三维基础模型；不以纯文本 agent memory、普通长上下文模型凑数。
- **机构门槛**：依据论文署名、官方项目页或作者主页，选择知名企业研究组及领域头部研究团队；逐行列出具体机构／实验室。这里的“头部”是领域筛选判断，不存在统一排名，也不把名校署名等同于已验证影响力。主要覆盖 Meta、Google、NVIDIA、Microsoft、Adobe、字节、阿里、腾讯、华为、三星、IBM、Physical Intelligence 等及 MIT、Stanford、Berkeley、Oxford、CMU、清北、NUS、NTU 等研究团队。
- **新工作不虚构影响力**：2026 年多数新作尚无充分时间积累引用。它们凭可核验团队与主题契合入选，不声称每篇都有“极高影响力”；会议录用也不是影响力证明。
- **一手来源**：每行题名链接用于核验作品身份、日期和摘要，机构链接指向论文全文、项目页或作者机构信息。逐篇核对身份、机构及摘要，并对关键方法与评测协议定点核读；不是逐篇全文精读或代码复现。机构列为相关署名机构的节选，不代表唯一牵头方。
- **去重**：预印本、正式会议版、同文改题名、同文基准不重复计数。Flash-VStream 的 2024 前身与 2025 扩展合算；PhysMem 的旧题名合算；MemoryVLA 与新增想象机制的 MemoryVLA++ 为两篇独立后续论文。
- **日期与状态**：普通日期指 arXiv 首次提交，而非本次检索或会议年份。仅有 arXiv 链接不表示未录用；未逐篇确认会议状态时不填写。arXiv 编号月份偶与页面提交日期不同，本表使用页面 submission history。
- **事实与判断分列**：“核心机制”归纳作者提出的方法；“边界／综述判断”是本次分析，不一概声称为原文已验证的失败。所有性能提升若无具体复现，仅视为作者报告，本表不进行跨骨干、跨数据集的数值排名。

| 分类 | 独立工作数 | 关注点 |
|---|---:|---|
| A | 20 | 视频流的潜空间、递归状态与 KV 记忆 |
| B | 9 | 结构化检索与长视频记忆 agent |
| C | 14 | 具身探索、空间记忆与 VLA 操作 |
| D | 6 | 参数式记忆与测试时训练 |
| E | 10 | 世界模型、持续三维感知与对象记忆 |
| F | 6 | GUI agent 与个人多模态记忆 |
| G | 14 | 记忆评测、数据与诊断工作 |

记忆形态可以重叠：KV 是潜表示的一种，但因其与注意力、缓存搬运和位置编码紧密耦合而单独讨论；神经网络权重中的快权重状态才归入参数式实例记忆。情景记忆、语义记忆描述的是内容／功能，不唯一决定物理存储形式。

## A. 视频流的潜空间、递归状态与 KV 记忆

| ID | 工作、完整题名与时间 | 入选机构／证据 | 任务与记忆 | 核心机制（文献事实归纳） | 边界／综述判断 |
|---|---|---|---|---|---|
| A01 | **LatentStream**<br>[Beyond Retrieval: Progressive Latent Memory Evolution for Streaming Video Understanding](https://arxiv.org/abs/2609.04131)<br>2026-09-03 | [蚂蚁集团、NUS、CUHK、南京理工](https://arxiv.org/html/2609.04131) | 视频流；潜变量＋检索 | 短中长期记忆在固定预算内整合；问题到达后逐步扩展潜变量感受范围，并用熵相关奖励学习证据内化。 | 写入和问题后的潜变量演化分属两阶段；潜变量更新不能直接归为模型权重更新。 |
| A02 | **StreamFlow**<br>[StreamFlow: Dynamic Memory Flows for Streaming Video Understanding](https://arxiv.org/abs/2608.10949)<br>2026-08-11 | [NTU（Bo An）、NUS（Shuicheng Yan）、同济、Michigan、HKUST](https://arxiv.org/pdf/2608.10949) | 视频流；潜变量＋按需读取 | 编码前用中期动态信息过滤冗余，长期库保存视觉潜变量；生成中视觉关注减弱时触发历史信息注入。 | 读取策略也会决定记忆价值；注意力指标改善不等于已证明事实忠实性。 |
| A03 | **CausalMem**<br>[Towards a Dynamic and Fixed-budget Memory Bank for Efficient Streaming Video Understanding](https://arxiv.org/abs/2606.25658)<br>2026-06-24 | [厦门大学多媒体可信感知与高效计算教育部重点实验室（纪荣嵘、周易毅）](https://arxiv.org/html/2606.25658) | 视频流；固定预算视觉 bank | 在线构造语义基底、识别冗余并维护有容量上限的记忆；写入不依赖尚未到达的问题，可免训练接入。 | 固定容量仍有不可逆遗忘；应进一步检查罕见细节和远期问题覆盖。 |
| A04 | **OmniMem**<br>[OmniMem: Perturbation-aware Memory Compression for Streaming Audio-Visual LLMs](https://arxiv.org/abs/2606.07577)<br>2026-05-26 | [字节跳动、剑桥大学、清华大学](https://arxiv.org/html/2606.07577) | 音视频流；分模态 KV | 用扰动敏感性估计保留价值，分别分配音频和视觉预算；另提供预算感知微调。 | 音频与画面可能互补，不能把双模态压缩简化为视觉 token 排序。 |
| A05 | **MuKV**<br>[MuKV: Multi-Grained KV Cache Compression for Long Streaming Video Question-Answering](https://arxiv.org/abs/2605.22269)<br>2026-05-21 | [NUS（Angela Yao）、中国科大](https://arxiv.org/html/2605.22269) | 长视频问答；多粒度 KV | 同时在 patch、帧、片段尺度压缩，结合注意力和频率线索，以半层级结构读取历史缓存。 | 压缩率和最终读取量应与整个历史库占用分别报告。 |
| A06 | **R3-Streaming**<br>[An Efficient Streaming Video Understanding Framework with Agentic Control](https://arxiv.org/abs/2605.17921)<br>2026-05-18 | [微软亚洲研究院、上海交大、宁波东方理工](https://arxiv.org/html/2605.17921) | 视频流；记忆＋agent 控制 | 把历史压缩、回答时机判断、强模型路由结合，采用时间感知奖励学习何时回答与升级推理。 | 收益同时来自控制与路由，不能全部归因于记忆表示。 |
| A07 | **FlexMem**<br>[Scaling the Long Video Understanding of Multimodal Large Language Models via Visual Memory Mechanism](https://arxiv.org/abs/2603.29252)<br>2026-03-31 | [厦门大学上述教育部重点实验室、国防科大](https://arxiv.org/html/2603.29252) | 长视频；压缩 KV＋局部检索 | 以视觉记忆机制组合压缩的全局上下文与局部细节检索，扩展现有 MLLM 的长视频处理能力。 | 全局概述和细节通道应分别消融；不能只按最终输入长度比较资源。 |
| A08 | **FluxMem**<br>[FluxMem: Adaptive Hierarchical Memory for Streaming Video Understanding](https://arxiv.org/abs/2603.02096)<br>2026-03-02 | [复旦可信具身智能研究院（吴祖玄）、上海创智、马里兰大学](https://arxiv.org/html/2603.02096) | 视频流；自适应分层 token | 时间上抑制相邻冗余，空间上合并相似内容，动态调节压缩强度以保留流中的变化。 | 低变化不一定低任务价值；细小但决定答案的差异可能被合并。 |
| A09 | **WeaveTime**<br>[WeaveTime: Stream from Earlier Frames into Emergent Memory in VideoLLMs](https://arxiv.org/abs/2602.22142)<br>2026-02-25 | [香港大学、上海科技大学、中山大学（杨思蓓）](https://arxiv.org/html/2602.22142) | 视频流；时间表征＋历史 cache | 以时间重建目标学习先后顺序；推理时通过不确定性触发由粗到细的历史读取，区分过去与当前。 | 不仅是选帧方法；应区分训练获得的时间能力与缓存机制贡献。 |
| A10 | **HERMES**<br>[HERMES: KV Cache as Hierarchical Memory for Efficient Streaming Video Understanding](https://arxiv.org/abs/2601.14724)<br>2026-01-21 | [复旦 OpenMOSS、上海创智、NUS](https://hermes-streaming.github.io/) | 视频流；分层 KV | 直接把 KV cache 组织成具有不同时间尺度的层级记忆，在持续编码中处理历史，降低提问时的额外开销。 | 层级缓存不自动保证每种细节都能长期恢复；需核算各层实际字节数。 |
| A11 | **Memento**<br>[Memento: Toward an All-Day Proactive Assistant for Ultra-Long Streaming Video](https://proceedings.iclr.cc/paper_files/paper/2026/hash/3b5f4587a0bdb81ecc6ce9d82320a5c2-Abstract-Conference.html)<br>2026 ICLR；更早首发未核定 | [Deepeleph、清华大学、小红书、北航等](https://openreview.net/pdf/e8fee5c834738ed247230ea336b2d1f5bf0a18cf.pdf) | 全天主动助手；动态视觉记忆 | 按问题相关性与步骤组织记忆和注意力，并构建长时间视频上的主动响应训练与评测资源。 | 主动响应与被动问答协议不同；Memento54K、MementoBench 不另算论文。 |
| A12 | **StreamingVLM**<br>[StreamingVLM: Real-Time Understanding for Infinite Video Streams](https://arxiv.org/abs/2510.09608)<br>2025-10-10 | [MIT Han Lab、NVIDIA、First Intelligence](https://arxiv.org/html/2510.09608) | 实时视频流；有限 KV 窗口 | 保留 attention sink、较短视觉历史和较长文本历史，并用与流式推理匹配的重叠短片段训练。 | 持续运行能力不等于可恢复任意久远的原始视觉证据。 |
| A13 | **StreamMem**<br>[StreamMem: Query-Agnostic KV Cache Memory for Streaming Video Understanding](https://arxiv.org/abs/2508.15717)<br>2025-08-21 | [Meta AI、NYU Agentic Learning Lab](https://arxiv.org/html/2508.15717) | 视频流；问题无关 KV 压缩 | 在未来问题未知时，用通用上下文中的 token 重要性维护受限视觉 KV 记忆，供后续问题读取。 | 通用显著性只是未来效用的代理；应检验分布外问题与小目标。 |
| A14 | **Flash-VStream**<br>[Flash-VStream: Efficient Real-Time Understanding for Long Video Streams](https://arxiv.org/abs/2506.23825)<br>2024 前身 / 2025-06-30 扩展 | [清华大学、字节跳动、北京交通大学](https://arxiv.org/html/2506.23825) | 实时视频；概述＋细节记忆 | 低容量上下文概述与高容量细节补充共同保留历史，异步视频编码与问答支持实时交互。 | 2024 年前身与 2025 年扩展版合并为一个工作家族，避免重复计数。 |
| A15 | **ReKV**<br>[Streaming Video Question-Answering with In-context Video KV-Cache Retrieval](https://arxiv.org/abs/2503.00540)<br>2025-03-01 | [阿里巴巴、上海交大](https://arxiv.org/html/2503.00540) | 视频流；外部 KV 检索 | 滑窗编码后把历史 KV 存入 RAM/磁盘，问题到来时检索并搬回相关缓存，复用已编码的视频。 | GPU 占用受控，但完整外部历史随时长增长；不是固定总存储方案。 |
| A16 | **Video-XL**<br>[Video-XL: Extra-Long Vision Language Model for Hour-Scale Video Understanding](https://arxiv.org/abs/2409.14485)<br>2024-09-22 | [北京智源、北京大学、人大、上海交大等](https://arxiv.org/html/2409.14485) | 小时级视频；可学习 KV 摘要 | 训练视觉总结 token 汇总区间 KV，结合渐进式训练和动态压缩，在保留细节与长度之间取舍。 | 摘要 token 的训练参数和实例记忆中的 KV 是不同概念。 |
| A17 | **VideoLLaMB**<br>[VideoLLaMB: Long Streaming Video Understanding with Recurrent Memory Bridges](https://arxiv.org/abs/2409.01071)<br>2024-09-02 | [BIGAI 通用人工智能全国重点实验室、北大、北理工、UCSC](https://arxiv.org/html/2409.01071) | 视频流；递归 memory bridge | 结合场景切分与跨片段递归记忆桥，将历史语义传递给后续视觉语言推理。 | 递归状态小并不意味着所有可检索历史均为常数容量。 |
| A18 | **VideoStreaming**<br>[Streaming Long Video Understanding with Large Language Models](https://arxiv.org/abs/2405.16009)<br>2024-05-25 | [上海人工智能实验室、香港中文大学](https://arxiv.org/html/2405.16009) | 长视频；传播状态＋选择 | 片段间传播压缩记忆，再依据问题选择固定数量的相关记忆供语言模型推理。 | 问题条件选择与问题无关写入需分开；固定输入 token 不等于固定历史库存。 |
| A19 | **MA-LMM**<br>[MA-LMM: Memory-Augmented Large Multimodal Model for Long-Term Video Understanding](https://arxiv.org/abs/2404.05726)<br>2024-04-08 | [Meta、马里兰大学（Abhinav Shrivastava）](https://arxiv.org/html/2404.05726) | 视频理解；视觉／查询双 bank | 在线编码并保存视觉特征与查询表征，通过记忆融合引用较早内容，避免一次性输入全部视频。 | 较早的模块化基线；其短视频任务成绩不能直接代表多小时记忆效果。 |
| A20 | **MovieChat**<br>[MovieChat: From Dense Token to Sparse Memory for Long Video Understanding](https://arxiv.org/abs/2307.16449)<br>2023-07-31 | [微软亚洲研究院、浙江大学、华盛顿大学](https://arxiv.org/html/2307.16449) | 长视频；稀疏潜空间记忆 | 借鉴短期与长期记忆分工，把密集视频 token 合并成稀疏长期表示，支持长视频问答。 | 构建了早期潜空间压缩范式；压缩后丢失的信息不能靠更强读取恢复。 |

## B. 结构化检索与长视频记忆 agent

| ID | 工作、完整题名与时间 | 入选机构／证据 | 任务与记忆 | 核心机制（文献事实归纳） | 边界／综述判断 |
|---|---|---|---|---|---|
| B01 | **ReMem**<br>[Reasoning with Memory: A Temporal Granularity-Adaptive Framework for Training-Free Long Video Understanding](https://arxiv.org/abs/2607.24794)<br>2026-06-30 | [NUS、NTU、A*STAR、中国科大等](https://arxiv.org/html/2607.24794) | 长视频推理；事件／帧检索 | 根据问题的时间粒度，在关键帧级与事件级记忆之间选择推理路径，免训练进行多粒度读取。 | 问题已知时的粒度适配，不能直接视为未知问题下的最优写入。 |
| B02 | **MemoryCard**<br>[MemoryCard: Topic-Aware Multi-Modal Clue Compression for Long-Video Question Answering](https://arxiv.org/abs/2606.05917)<br>2026-06-04 | [清华大学人工智能研究院、东北大学、神州数码](https://arxiv.org/html/2606.05917) | 长视频问答；多模态事件卡 | 把视频和话语压成主题相关的事件概述与少量关键视觉时刻，检索卡片进行后续推理。 | 卡片包含视觉线索而非纯字幕；预处理成本、细粒度运动损失应另计。 |
| B03 | **OASIS**<br>[OASIS: On-Demand Hierarchical Event Memory for Streaming Video Reasoning](https://arxiv.org/abs/2604.17052)<br>2026-04-18 | [OPPO AI Center、中山大学（李冠彬）](https://arxiv.org/html/2604.17052) | 视频流；层级事件记忆 | 组织层级历史事件，先尝试短上下文回答，再根据不确定性和高层意图逐步检索细化。 | 按需读取能控制单次推理量；历史索引规模仍需单独报告。 |
| B04 | **EGAgent**<br>[Agentic Very Long Video Understanding](https://arxiv.org/abs/2601.18157)<br>2026-01-26 | [Meta Reality Labs、威斯康星大学麦迪逊分校](https://arxiv.org/html/2601.18157) | 超长视频；实体图＋工具 | 围绕人物、地点、物体及其关系维护实体场景图，结合音频、视觉工具执行多跳检索。 | 图中身份与时间绑定错误会传播到后续推理；命中实体不等于命中证据。 |
| B05 | **HAVEN**<br>[Hierarchical Long Video Understanding with Audiovisual Entity Cohesion and Agentic Search](https://arxiv.org/abs/2601.13719)<br>2026-01-20 | [微软亚洲研究院、中国科大](https://arxiv.org/html/2601.13719) | 长视频；音视频实体层级 | 维护跨片段一致的音视频实体，在全局、场景、片段、实体等层级进行 agent 搜索。 | 实体一致性是检索前提；应检查同名、换装、重现和跨模态错配。 |
| B06 | **WorldMM**<br>[WorldMM: Dynamic Multimodal Memory Agent for Long Video Reasoning](https://arxiv.org/abs/2512.02425)<br>2025-12-02 | [KAIST、NTU、DeepAuto.ai](https://arxiv.org/html/2512.02425) | 长视频；情景／语义／视觉混合库 | 分别保存多尺度事件、持续更新的概念知识和详细视觉证据，让 agent 动态决定读取来源与次数。 | 不同模态并非重复副本；需分别核算构库、更新和多轮工具调用成本。 |
| B07 | **M3-Agent**<br>[Seeing, Listening, Remembering, and Reasoning: A Multimodal Agent with Long-Term Memory](https://arxiv.org/abs/2508.09736)<br>2025-08-13 | [字节跳动 Seed、浙江大学、上海交大](https://arxiv.org/html/2508.09736) | 音视频 agent；情景＋语义记忆 | 持续观察音视频并构建实体中心的长时记忆，通过强化学习训练迭代检索与回答。 | 记住可检索证据与正确使用证据是两步；M3Bench 与方法合并计数。 |
| B08 | **VideoTree**<br>[VideoTree: Adaptive Tree-based Video Representation for LLM Reasoning on Long Videos](https://arxiv.org/abs/2405.19209)<br>2024-05-29 | [UNC Chapel Hill（Mohit Bansal、Gedas Bertasius）](https://arxiv.org/html/2405.19209) | 长视频问答；自适应树 | 按问题相关性迭代聚类和细化关键帧，构造多粒度树，让语言模型从粗到细获取证据。 | 建树可受当前问题影响，不能与严格单遍、未来问题未知的写入直接比较。 |
| B09 | **VideoAgent（Fan 等）**<br>[VideoAgent: A Memory-augmented Multimodal Agent for Video Understanding](https://arxiv.org/abs/2403.11481)<br>2024-03-18 | [BIGAI 通用人工智能全国重点实验室、北京大学](https://arxiv.org/html/2403.11481) | 视频 agent；事件＋物体状态库 | 统一时间事件描述和物体跟踪状态，提供片段定位、物体查询及视觉工具完成问答。 | 此处是 Fan 等的 memory-augmented VideoAgent；与其他同名论文区别计数。 |

## C. 具身探索、空间记忆与 VLA 操作

| ID | 工作、完整题名与时间 | 入选机构／证据 | 任务与记忆 | 核心机制（文献事实归纳） | 边界／综述判断 |
|---|---|---|---|---|---|
| C01 | **Analytic Concept-Centric Memory**<br>[Analytic Concept-Centric Memory for Agentic Embodied Manipulation](https://arxiv.org/abs/2606.29774)<br>2026-06-29 | [上海交大（卢策吾）、上海创智、复旦、西湖、浙大](https://arxiv.org/html/2606.29774) | 机器人操作；概念／部件结构库 | 以概念为中心关联部件几何、可供性、状态转移和技能，供 agent 进行可组合的操作推理。 | “参数化几何模板”不等于把历史写入神经网络快权重。 |
| C02 | **EventVLA**<br>[EventVLA: Event-Driven Visual Evidence Memory for Long-Horizon Vision-Language-Action Policies](https://arxiv.org/abs/2606.20092)<br>2026-06-18 | [上海人工智能实验室、清华、华为、港大、中科大等](https://arxiv.org/html/2606.20092) | VLA 操作；关键视觉事件 | 预测值得保留的关键事件，保存未来行动需要的短暂视觉线索，并结合起始与近期锚点。 | 已经涉及面向未来动作的记忆选择；不能把“未来价值写入”笼统当作空白。 |
| C03 | **MemoryVLA++**<br>[MemoryVLA++: Temporal Modeling via Memory and Imagination in Vision-Language-Action Models](https://arxiv.org/abs/2606.09827)<br>2026-06-08 | [清华 BNRist、HKU MMLab、Dexmal、阶跃星辰](https://arxiv.org/html/2606.09827) | VLA 操作；记忆＋未来想象 | 把历史记忆与未来状态想象结合，为当前动作提供过去和预测未来的时间上下文。 | 真实经历与模型想象应标记来源；不能把预测内容当作观察证据。 |
| C04 | **MEM**<br>[MEM: Multi-Scale Embodied Memory for Vision Language Action Models](https://arxiv.org/abs/2603.03596)<br>2026-03-03 官方发布 / 03-04 arXiv | [Physical Intelligence（Finn、Levine、Driess 等）](https://www.pi.website/research/memory) | VLA 长任务；短视频＋长文本 | 以短期视频保留动作相关细节，以长期文本记录任务进度，在行动过程中主动整理跨尺度记忆。 | 文本和视觉承担不同时间尺度；并非测试时修改基础模型权重。 |
| C05 | **BrainMem**<br>[BrainMem: Brain-Inspired Evolving Memory for Embodied Agent Task Planning](https://arxiv.org/abs/2604.16331)<br>2026-03-12 | [NTU（Yang Liu 团队）、天津大学](https://arxiv.org/html/2604.16331) | 具身规划；工作／情景／语义库 | 围绕工作、情景、语义记忆维护演化知识图谱，以符号结构约束规划与历史经验调用。 | 语义规则可能陈旧；仿真规划收益不自动迁移到真实机器人低层控制。 |
| C06 | **PhysMem**<br>[PhysMem: Scaling Test-Time Memory for Embodied Physical Reasoning](https://arxiv.org/abs/2602.20323)<br>2026-02-23 | [斯坦福大学、UC San Diego](https://arxiv.org/html/2602.20323) | 具身物理推理；经验→原则 | 从交互轨迹产生物理假设，经过后续交互检验后形成可调用原则，持续改进规划。 | test-time memory 指外部记忆演化，并不更新模型参数；同文旧题名合并。 |
| C07 | **MemoryVLA**<br>[MemoryVLA: Perceptual-Cognitive Memory in Vision-Language-Action Models for Robotic Manipulation](https://arxiv.org/abs/2508.19236)<br>2025-08-26 | [清华 BNRist、Dexmal、旷视、阶跃星辰等](https://arxiv.org/html/2508.19236) | VLA 操作；感知／认知双 bank | 把低层感知细节和高层语义分开保存，由当前工作记忆检索融合后供扩散动作专家使用。 | 与 ++ 为独立后续方法论文；需保持骨干与训练数据一致再比较其贡献。 |
| C08 | **3DLLM-Mem**<br>[3DLLM-Mem: Long-Term Spatial-Temporal Memory for Embodied 3D Large Language Model](https://arxiv.org/abs/2505.22657)<br>2025-05-28 | [UCLA、Google Research](https://arxiv.org/html/2505.22657) | 具身三维推理；工作 token＋情景库 | 当前观察作为工作记忆查询历史空间和时间特征，并融合到 3D LLM 的回答与动作决策。 | 跨房间与时间绑定是关键；3DMem-Bench 和方法为一篇论文。 |
| C09 | **Embodied VideoAgent**<br>[Embodied VideoAgent: Persistent Memory from Egocentric Videos and Embodied Sensors Enables Dynamic Scene Understanding](https://arxiv.org/abs/2501.00358)<br>2024-12-31 | [BIGAI、中国科大、清华大学、北京大学](https://arxiv.org/html/2501.00358) | 具身视频；持久物体状态 | 融合视频、深度和相机位姿，依据观察到的动作和状态变化更新物体记忆，支持时空查询。 | 明确使用额外传感信息；不能与纯 RGB 方法忽略传感器差异比较。 |
| C10 | **3D-Mem**<br>[3D-Mem: 3D Scene Memory for Embodied Exploration and Reasoning](https://arxiv.org/abs/2411.17735)<br>2024-11-23 | [MIT、MIT-IBM Watson AI Lab、UMass、CUHK、哥伦比亚](https://arxiv.org/html/2411.17735) | 探索／问答；多视角快照 | 以记忆快照保留丰富场景外观，以 frontier 快照表示未探索区域，结合增量构建与检索。 | 不只存过去，还让未知区域参与行动选择；图像快照与纯文本图各有信息损失。 |
| C11 | **Embodied-RAG**<br>[Embodied-RAG: General Non-parametric Embodied Memory for Retrieval and Generation](https://arxiv.org/abs/2409.18313)<br>2024-09-26 | [CMU（Bisk、Salakhutdinov、Johnson-Roberson 等）](https://arxiv.org/html/2409.18313) | 导航／语言生成；语义森林 | 自动构建多尺度空间语义层级，把非参数检索从文档扩展到具身环境与导航目标。 | 此条对应 Xie 等的 2409.18313；层级检索不等于动态物体状态持续正确。 |
| C12 | **ReMEmbR**<br>[ReMEmbR: Building and Reasoning Over Long-Horizon Spatio-Temporal Memory for Robot Navigation](https://arxiv.org/abs/2409.13682)<br>2024-09-20 | [NVIDIA、UT Austin](https://arxiv.org/html/2409.13682) | 机器人导航；时空语义检索 | 从机器人观察生成可检索语义描述，结合位置和时间，由语言模型推理过去经历并导航。 | 描述是压缩后的观察；缺失的外观细节不能从语言摘要中重新证明。 |
| C13 | **ConceptGraphs**<br>[ConceptGraphs: Open-Vocabulary 3D Scene Graphs for Perception and Planning](https://arxiv.org/abs/2309.16650)<br>2023-09-28 | [MIT、Toronto、Montréal、JHU、UMass](https://arxiv.org/html/2309.16650) | 空间感知／规划；开放词表 3D 图 | 把二维基础模型识别结果多视角关联成三维对象和语义关系，支持语言指定的空间规划。 | 对象图易于寻址，但细粒度关系、动态变化与原始视觉证据需要额外机制。 |
| C14 | **ConceptFusion**<br>[ConceptFusion: Open-set Multimodal 3D Mapping](https://arxiv.org/abs/2302.07241)<br>2023-02-14 | [MIT CSAIL、Toronto、Montréal、CMU 等](https://arxiv.org/html/2302.07241) | 三维建图；多模态稠密特征 | 把开放集像素特征融合进三维地图，可用语言、图像、音频与几何查询场景。 | 属于基础模型驱动的空间记忆；逐点特征的容量代价与对象图不同。 |

## D. 参数式记忆与测试时训练

| ID | 工作、完整题名与时间 | 入选机构／证据 | 任务与记忆 | 核心机制（文献事实归纳） | 边界／综述判断 |
|---|---|---|---|---|---|
| D01 | **RoboTTT**<br>[RoboTTT: Context Scaling for Robot Policies](https://arxiv.org/abs/2607.15275)<br>2026-07-16 | [NVIDIA GEAR、斯坦福大学、UT Austin](https://arxiv.org/html/2607.15275) | 机器人策略；测试时快权重 | 把历史上下文写入随序列更新的快权重，通过动作序列训练与截断反传扩展机器人策略上下文。 | 参数式实例记忆已有直接 VLA 实证；容量、更新代价和跨任务干扰仍需测量。 |
| D02 | **Online Neural Space Time Memory**<br>[Online Neural Space Time Memory for Dynamic Novel View Synthesis](https://arxiv.org/abs/2607.15271)<br>2026-07-16 | [Google、华盛顿大学](https://arxiv.org/html/2607.15271) | 动态新视角合成；快权重场 | 用测试时训练维护在线神经时空记忆，周期更新与逐帧读取分离，并用记忆约束缓解漂移。 | 主要证据来自动态重建；不能据此推断语言问答或实体事实回忆已解决。 |
| D03 | **WAM-TTT**<br>[WAM-TTT: Steering World-Action Models by Watching Human Play at Test Time](https://arxiv.org/abs/2607.06988)<br>2026-07-08 | [北京大学、Galbot、中科院自动化所、清华大学](https://arxiv.org/html/2607.06988) | 世界动作模型；测试时自适应记忆 | 观看无动作标注的人类视频，通过自监督预测把经验写入自适应记忆，再用于机器人行动。 | 基础世界动作模型冻结与记忆模块更新并存；不是全模型在线微调。 |
| D04 | **Spatial-TTT**<br>[Spatial-TTT: Streaming Visual-based Spatial Intelligence with Test-Time Training](https://arxiv.org/abs/2603.12255)<br>2026-03-12 | [清华大学、腾讯混元、NTU](https://arxiv.org/html/2603.12255) | 流式空间理解；快权重＋滑窗 | 大块测试时更新与局部滑窗结合，辅以空间预测结构和稠密三维描述训练来压缩历史。 | 输入的空间监督和更新成本必须计入；空间能力提升不等于一般事件记忆提升。 |
| D05 | **ZipMap**<br>[ZipMap: Linear-Time Stateful 3D Reconstruction via Test-Time Training](https://arxiv.org/abs/2603.04385)<br>2026-03-04 | [Google DeepMind、Cornell、MIT](https://arxiv.org/html/2603.04385) | 三维重建；可查询快权重状态 | 采用大块 TTT，把多视角图像压入可查询场景状态，实现近线性处理与状态式重建。 | 主体设置包含双向重建；流式扩展应单列，不能统称严格因果方法。 |
| D06 | **LaCT / Test-Time Training Done Right**<br>[Test-Time Training Done Right](https://arxiv.org/abs/2505.23884)<br>2025-05-29 | [Adobe Research、MIT](https://arxiv.org/html/2505.23884) | 视觉／多模态；大块快权重更新 | 通过大块而非细碎在线更新提高硬件利用率，扩大非线性记忆容量，验证新视角合成等任务。 | 它解释了实现与容量如何影响 TTT，而不是任何任务都适用的免费压缩器。 |

## E. 世界模型、持续三维感知与对象记忆

| ID | 工作、完整题名与时间 | 入选机构／证据 | 任务与记忆 | 核心机制（文献事实归纳） | 边界／综述判断 |
|---|---|---|---|---|---|
| E01 | **WorldTrace / Addressable Memory**<br>[Addressable Memory for Video World Models](https://arxiv.org/abs/2608.07408)<br>2026-08-07 | [NVIDIA、Princeton](https://arxiv.org/html/2608.07408) | 视频世界模型；可寻址压缩 KV | 给压缩记忆分配合适虚拟位置，在未旋转空间处理位置编码，并区分连续场景与地标式情景记忆。 | 位置编码兼容性会决定能否读到历史；ICML 2026 F2S 是 workshop，非主会。 |
| E02 | **Mem-World**<br>[Mem-World: Memory-Augmented Action-Conditioned World Models for Persistent Robot Manipulation](https://arxiv.org/abs/2606.18960)<br>2026-06-17 | [三星北京研究院、大连理工（卢湖川、贾旭）](https://arxiv.org/html/2606.18960) | 机器人世界模型；4D surfel 索引 | 用随时间变化的腕部视角表面元记录历史可见性，按未来动作所需视角检索证据，预测操作视频。 | 服务于预测和策略评估；几何、相机信息与生成误差需单独控制。 |
| E03 | **Lyra 2.0**<br>[Lyra 2.0: Explorable Generative 3D Worlds](https://arxiv.org/abs/2604.13036)<br>2026-04-14 | [NVIDIA](https://arxiv.org/html/2604.13036) | 可探索世界；几何路由记忆 | 用三维几何检索历史帧并建立对应，把外观合成交给生成模型；以退化历史训练抑制累积漂移。 | 几何用于寻址，不等于把世界完全存成显式三维模型。 |
| E04 | **HyDRA**<br>[Out of Sight but Not Out of Mind: Hybrid Memory for Dynamic Video World Models](https://arxiv.org/abs/2603.25716)<br>2026-03-26 | [快手 Kling、华中科大（白翔）](https://arxiv.org/html/2603.25716) | 动态世界；静态／动态混合记忆 | 分开组织背景空间记忆与运动实体的时空信息，读取不同记忆以恢复离开视野后的内容。 | 静态场景回环与运动物体持续性是不同问题；需分别测量。 |
| E05 | **MosaicMem**<br>[MosaicMem: Hybrid Spatial Memory for Controllable Video World Models](https://arxiv.org/abs/2603.17117)<br>2026-03-17 | [Toronto、Vector、Georgia Tech、Osaka、UT Austin、Mujin](https://arxiv.org/html/2603.17117) | 可控视频世界；空间 patch＋生成 | 按三维空间索引历史 patch，拼出目标视角的可见记忆，再用生成模型补全未知与动态部分。 | 可追溯的已见证据和生成补全应区别；拼接质量不能替代事实一致性验证。 |
| E06 | **RELIC**<br>[RELIC: Interactive Video World Model with Long-Horizon Memory](https://arxiv.org/abs/2512.04040)<br>2025-12-03 | [Adobe Research](https://relic-worldmodel.github.io/) | 交互视频世界；相机感知潜变量 KV | 压缩历史潜变量并加入相机与动作信息，通过长教师到因果学生的蒸馏训练实时长时生成。 | 实时性依赖骨干和硬件；长时间视觉一致性与真实世界记忆是不同评测目标。 |
| E07 | **VMem**<br>[VMem: Consistent Interactive Video Scene Generation with Surfel-Indexed View Memory](https://arxiv.org/abs/2506.18903)<br>2025-06-23 | [Oxford VGG（Torr、Vedaldi、Jakab）](https://arxiv.org/html/2506.18903) | 交互场景生成；surfel 视图索引 | 把历史视图关联到三维表面元，通过几何覆盖选择重访位置所需的视觉记忆。 | 显式几何提供稳定键；动态对象与几何估计错误仍会影响检索。 |
| E08 | **WorldMem**<br>[WorldMem: Long-term Consistent World Simulation with Memory](https://arxiv.org/abs/2504.12369)<br>2025-04-16 | [NTU S-Lab、北京大学王选所、上海人工智能实验室](https://arxiv.org/html/2504.12369) | 世界模拟；帧／位姿／时间 bank | 储存历史帧和状态信息，用状态感知注意力在返回旧位置时读取历史，维持长期一致性。 | 历史生成帧也可能含错误，持续记忆可能传播而非消除错误。 |
| E09 | **CUT3R**<br>[Continuous 3D Perception Model with Persistent State](https://arxiv.org/abs/2501.12387)<br>2025-01-21 | [UC Berkeley、Google DeepMind](https://arxiv.org/html/2501.12387) | 连续三维感知；递归隐状态 | 每次观察更新持久状态，输出同一坐标系下的度量点图，并可用虚拟视角查询未见区域。 | 是基础视觉状态模型；对未见区域的输出属于先验推断，不是已观察记忆。 |
| E10 | **SAM 2**<br>[SAM 2: Segment Anything in Images and Videos](https://arxiv.org/abs/2408.00714)<br>2024-08-01 | [Meta FAIR](https://arxiv.org/html/2408.00714) | 视频对象分割；流式 mask 记忆 | 维护历史帧的对象特征与掩码信息，通过记忆注意力持续跟踪分割对象。 | 是对象级视觉记忆锚点，不是语言语义记忆或通用 agent 的完整解决方案。 |

## F. GUI agent 与个人多模态记忆

| ID | 工作、完整题名与时间 | 入选机构／证据 | 任务与记忆 | 核心机制（文献事实归纳） | 边界／综述判断 |
|---|---|---|---|---|---|
| F01 | **FocusMem**<br>[FocusMem: Factorizing Content, Readout, and Trust in Latent GUI Memory](https://arxiv.org/abs/2608.04530)<br>2026-08-05 | [北京大学高可信软件技术重点实验室、中科院信工所、清华](https://arxiv.org/html/2608.04530) | GUI agent；潜变量＋可信门控 | 将记忆内容、当前状态相关读取、使用信任度分解，分别组织情景和工作信息，控制无关历史干扰。 | 固定骨干也能训练记忆组件；可信读取是独立于压缩率的研究维度。 |
| F02 | **ATMem**<br>[What Memory Do GUI Agents Really Need? From Passive Records to Active Task-Driving States](https://arxiv.org/abs/2606.31612)<br>2026-06-30 | [阿里巴巴通义实验室、UTS、Adelaide University](https://arxiv.org/pdf/2606.31612) | GUI agent；主动任务状态 | 记录值、任务角色和当前状态；STR-GRPO 比较开关记忆的执行轨迹，用成功贡献和成本训练选择性使用。 | 已研究反事实记忆效用；新的写入价值工作需比它更明确地区分保留与使用。 |
| F03 | **MemGUI-Agent**<br>[MemGUI-Agent: An End-to-End Long-Horizon Mobile GUI Agent with Proactive Context Management](https://arxiv.org/abs/2606.19926)<br>2026-06-18 | [快手、浙江大学](https://arxiv.org/html/2606.19926) | 移动 GUI；上下文管理动作 | 把任务历史、界面状态与近期步骤组织为可主动管理的上下文，由同一策略输出操作和管理决策。 | 记忆管理进入动作空间；长期跨任务迁移不能仅凭单任务成功率推断。 |
| F04 | **VisualMem**<br>[Personal Visual Memory from Explicit and Implicit Evidence](https://arxiv.org/abs/2605.28806)<br>2026-05-27 | [Adobe Research、JHU（Vishal Patel）、UW–Madison](https://arxiv.org/html/2605.28806) | 个人助手；显式／隐式视觉事实 | 从用户直接说明与图像隐含线索中提炼个人视觉记忆，联合视觉证据和文本事实支持后续检索。 | 个体身份、所有权和外观不能总由通用图注替代；推断事实应保留不确定性。 |
| F05 | **MementoGUI**<br>[MementoGUI: Learning Agentic Multimodal Memory Control for Long-Horizon GUI Agents](https://arxiv.org/abs/2605.18652)<br>2026-05-18 | [MIT-IBM Watson AI Lab、Rochester、UW–Madison](https://arxiv.org/html/2605.18652) | GUI agent；多模态记忆控制 | 学习选择、压缩、写入和读取，组合关键视觉区域、文本工作记忆及长期情景记录。 | 要区分视觉裁剪、文字记录与控制学习分别带来的收益。 |
| F06 | **EAM / Executable Agentic Memory**<br>[Executable Agentic Memory for GUI Agent](https://arxiv.org/abs/2605.12294)<br>2026-05-12 | [清华大学、中山大学](https://arxiv.org/html/2605.12294) | GUI agent；可执行程序性记忆 | 用知识图谱、状态感知搜索与动作组挖掘组织操作经验，结合价值引导搜索调用可执行知识。 | 记住“怎么做”不同于记住“看到了什么”；程序迁移需控制 UI 版本变化。 |

## G. 记忆评测、数据与诊断工作

| ID | 工作、完整题名与时间 | 入选机构／证据 | 任务与记忆 | 核心机制（文献事实归纳） | 边界／综述判断 |
|---|---|---|---|---|---|
| G01 | **EgoMonth**<br>[EgoMonth: A Month-Level Egocentric Video Benchmark for Long-Term Spatiotemporal Memory](https://arxiv.org/abs/2608.13113)<br>2026-08-13 | [华为、南京大学、天津大学](https://arxiv.org/html/2608.13113) | 月级第一视角；基准＋基线 | 构建跨天、跨周到月级的时空记忆问题，结合结构化情景记忆与级联推理基线分析长期依赖。 | 月级是跨日时间跨度；须与累计视频小时数、单人连续时长分开报告。 |
| G02 | **S-EMBER**<br>[S-EMBER: A Large-Scale Benchmark for Streaming Egocentric Memory Retrieval](https://arxiv.org/abs/2607.02689)<br>2026-07-02 | [Meta FAIR、Reality Labs](https://arxiv.org/html/2607.02689) | 第一视角流；证据检索基准 | 以流式历史上的问题和时间证据衡量情景记忆，要求不只回答，还找回相关的过去片段。 | 必须遵守问题时刻的可见历史；离线看全片会改变被评估问题。 |
| G03 | **EgoMemory**<br>[EgoMemory: Memory-Augmented Personalized Retrieval for Long-Context Egocentric Video](https://aclanthology.org/2026.findings-acl.362/)<br>2026 Findings of ACL；更早首发未核定 | [Microsoft Research（官方出版目录）](https://www.microsoft.com/en-us/research/publication/egomemory-memory-augmented-personalized-retrieval-for-long-context-egocentric-video/) | 个人第一视角；检索基准＋EgoRetriever | 把用户历史与个人对象检索结合，利用上下文和反思式推理理解个体化目标。 | 个体专属对象和一般开放词表对象识别不同；长上下文并不保证个性化匹配。 |
| G04 | **EG-VQA**<br>[EG-VQA: Benchmarking Verifiable Video Question Answering with Grounded Temporal Evidence](https://arxiv.org/abs/2606.24797)<br>2026-06-23 | [中山大学 HCP（林倞）、鹏城实验室、深圳大学](https://arxiv.org/html/2606.24797) | 视频问答；答案＋时间证据 | 提供与答案对应的时间证据并联合评价，诊断语义回答正确但证据不对的情况。 | 属于可验证问答评测，不是记忆机制论文；作者指标需按其协议复现。 |
| G05 | **M3Exam**<br>[M^3Exam: Benchmarking Multimodal Memory for Realistic User-Agent Interactions](https://arxiv.org/abs/2606.07402)<br>2026-06-05 | [HKUST／HKUST(GZ)、腾讯混元、鹏城实验室等](https://arxiv.org/html/2606.07402) | 个人多模态；跨会话记忆基准 | 覆盖真实用户交互中的文档、图像与隐含信息，研究跨模态记忆使用，并以 M3Proctor 缓解读取偏置。 | 不能把检索到相关文本等同于用到了图片；与 M3-Agent、M3Bench 不同。 |
| G06 | **WorldMemArena**<br>[WorldMemArena: Evaluating Multimodal Agent Memory Through Action-World Interaction](https://arxiv.org/abs/2605.29341)<br>2026-05-28 | [UCSB、Stanford、ETH Zürich、J.P. Morgan、CMU 等](https://arxiv.org/pdf/2605.29341) | 多模态 agent；全生命周期基准 | 将记忆拆成写入、维护、检索、使用，结合世界状态演化、行动反馈和阶段证据进行诊断。 | 保存得更好未必执行得更好；最新版 PDF 为 461 个多会话任务，版本需固定。 |
| G07 | **EgoMemReason**<br>[EgoMemReason: A Memory-Driven Reasoning Benchmark for Long-Horizon Egocentric Video Understanding](https://arxiv.org/abs/2605.09874)<br>2026-05-11 | [UNC Chapel Hill（Bansal、Bertasius）、NTU](https://arxiv.org/html/2605.09874) | 第一视角；跨时证据组合基准 | 从实体、事件和行为层面构造依赖多处历史证据的问题，突出长时间回溯与组合推理。 | 证据覆盖率和链条完整性比单个片段召回率更有解释力。 |
| G08 | **SceneBench / Scene-RAG**<br>[Seeing the Scene Matters: Revealing Forgetting in Video Understanding Models with a Scene-Aware Long-Video Benchmark](https://arxiv.org/abs/2603.27259)<br>2026-03-28 | [University of Cambridge、CUHK、上海交大等](https://arxiv.org/html/2603.27259) | 长视频；场景遗忘基准 | 构造场景感知问题以检测先前场景被遗忘的现象，并提供按场景组织检索的基线。 | 场景切分既是方法先验也可能影响评测；需控制切分来源和边界误差。 |
| G09 | **RoboMME**<br>[RoboMME: Benchmarking and Understanding Memory for Robotic Generalist Policies](https://arxiv.org/abs/2603.04639)<br>2026-03-04 | [Stanford、Figure AI、University of Michigan](https://arxiv.org/html/2603.04639) | 机器人；记忆类型诊断 | 用统一任务族区分时间、空间、对象、程序记忆，并在同一 VLA 骨干下比较多种记忆设计。 | 不同表示的效果高度依赖任务；总成功率会掩盖类型间的取舍。 |
| G10 | **MemGUI-Bench**<br>[MemGUI-Bench: Benchmarking Memory of Mobile GUI Agents in Dynamic Environments](https://arxiv.org/abs/2602.06075)<br>2026-02-03 | [vivo AI Lab、浙江大学、CUHK、上海交大等](https://arxiv.org/html/2602.06075) | 移动 GUI；跨应用／会话基准 | 以成对任务、分阶段评审与跨会话学习协议评估信息保留、经验复用和执行效率。 | 与快手的 MemGUI-Agent 不是同一篇；短期保留与长期经验应分别计分。 |
| G11 | **EgoLife**<br>[EgoLife: Towards Egocentric Life Assistant](https://arxiv.org/abs/2503.03803)<br>2025-03-05 | [NTU S-Lab（Ziwei Liu）、LMMs-Lab 等](https://arxiv.org/html/2503.03803) | 生活助手；数据＋EgoButler | 采集多人一周的第一视角生活数据，构建长期生活问答，结合 EgoGPT 与 EgoRAG 支持回忆和个性化。 | 300 小时是多人总量，不能写成单人连续 300 小时；数据、模型、基准合算一篇。 |
| G12 | **GOAT-Bench**<br>[GOAT-Bench: A Benchmark for Multi-Modal Lifelong Navigation](https://arxiv.org/abs/2404.06609)<br>2024-04-09 | [Georgia Tech、CMU、UIUC、Mistral AI、UW](https://arxiv.org/html/2404.06609) | 终身导航；多模态目标基准 | 同一环境中连续完成语言、图像、类别目标，比较显式与隐式场景记忆及经验复用。 | 跨目标复用场景历史不同于每个目标重置环境和记忆的单回合导航。 |
| G13 | **OpenEQA**<br>[OpenEQA: Embodied Question Answering in the Era of Foundation Models](https://open-eqa.github.io/)<br>2024；CVPR 2024 | [Meta FAIR 及合作高校](https://open-eqa.github.io/) | 具身问答；情景回忆＋主动探索 | 区分已有经历上的问答与需要继续探索的问答，用自然语言问题衡量场景理解。 | 被动记忆和主动获取新证据必须分开；该基准本身不指定存储表示。 |
| G14 | **Ego4D**<br>[Ego4D: Around the World in 3,000 Hours of Egocentric Video](https://arxiv.org/abs/2110.07058)<br>2021-10-13 | [Meta／Facebook AI 与国际高校联盟](https://arxiv.org/html/2110.07058) | 第一视角；基础数据与情景记忆任务 | 以大规模日常第一视角视频定义自然语言、视觉查询等回忆任务，为后续视觉记忆评测提供基础。 | 基础数据论文首发 2021、CVPR 2022；后续扩容版本和子任务不重复计数。 |

## 2. 引用与版本注意事项

1. **2026 会议不等于 2026 首发**：StreamingVLM、WorldMM、M3-Agent、MemoryVLA、LaCT 等有较早预印本；表内按首发日期处理。
2. **会议与 workshop 区别**：WorldTrace 的 ICML 2026 F2S workshop 信息不能写成 ICML 主会录用。只在已有一手证据时描述正式发表状态。
3. **同名作品区别**：VideoAgent 指 Fan 等的 2403.11481；Embodied-RAG 指 Xie 等的 2409.18313。Memento、MementoGUI、M3-Agent、M3Exam、MemGUI-Agent、MemGUI-Bench 是不同工作。
4. **版本变化**：WorldMemArena 当前 PDF 为 461 个多会话任务；部分摘要／索引保留旧版规模。需要使用数值时，应固定具体版本并重新核对方法、附录与数据版本。
5. **支持机器检索**：[来源清单 JSON](visual_memory_sources_2026-09-08.json)保存 ID、题名、来源链接、机构依据、日期和中文归纳。它是引用导航元数据，不是已验证的 BibTeX，也不包含论文全文或数据。
6. **检索边界**：这是围绕机构与机制的定向文献调查，不是声称检索穷尽的系统综述；未收录不代表工作质量低。机构或视觉关联不足以核实的候选不纳入计数。
