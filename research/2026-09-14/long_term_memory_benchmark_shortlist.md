# 长期记忆 benchmark：公开资源复核与五项推荐

调研截止：2026-09-14。承接本会话对长期任务、记忆压缩、遗忘和更新的讨论。本轮提高公开资源完整度与社区采用证据的权重。

## 结论与边界

推荐进一步考察 **LongMemEval-V2、GOAT-Bench、EgoLife / EgoLifeQA、LongMemEval、MemoryAgentBench**。前三项保留视觉输入，后两项用于成熟的记忆机制对照。这不是五个都原生满足“持续长期行动 + 动态世界 + 固定总存储”的任务：目前这份候选集仍需补充协议或组合评测。

核查范围包括官方论文、代码目录、README、数据文件列表、baseline 入口及 GitHub 公开元数据。**没有安装环境、下载完整大数据或运行 benchmark，因此不宣称复现成功。** Star 是 2026-09-14 的关注度快照，不是论文引用量、独立复现数量或质量评分；同一家族和依赖平台的关注度分别计算。

## 五项推荐

| 优先级 | Benchmark | 官方仓库 star / fork | 已核实的公开资源 | 用途与原版缺口 |
| --- | --- | --- | --- | --- |
| 1 | LongMemEval-V2 | 158 / 24 | 轨迹、截图、问题、评测框架、六种 memory backend 及运行脚本 | 大规模多模态经验记忆；下游仍是 QA，总存储尚未统一受限 |
| 2 | GOAT-Bench | 157 / 23 | 环境代码、episode 下载链接、目标特征、SenseAct-NN 权重与评测脚本 | 检验记忆是否改善导航；原版只有 5–10 个子目标，场景静态 |
| 3 | EgoLife / EgoLifeQA | 461 / 21 | 多日视频、QA、caption、EgoRAG 与 EgoGPT 代码 | 真实跨日视觉经历；原版是回顾性 QA，需要另加流式写入和预算协议 |
| 4 | LongMemEval | 1,083 / 83 | 清理版 S / M / oracle 数据、检索和生成评测代码 | 更新、跨会话推理与拒答对照；文本任务，不验证视觉或行动 |
| 5 | MemoryAgentBench | 451 / 62 | 处理后数据、增量输入流程、长上下文 / RAG / 记忆系统评测脚本 | 检验增量积累和冲突消解；主要是文本诊断任务，非连续世界 |

### 1. LongMemEval-V2：优先考察的多模态记忆接口

包含 451 个问题，Small / Medium 分别使用 100 / 500 条操作轨迹，来自 WebArena / WorkArena 的网页与企业应用环境。能力包含静态状态、动态变化、工作流程、环境特有失败和前提辨析。接口为 `insert(trajectory)` 与 `query(question, image)`；提供无检索、两类 RAG、AgentRunbook-R、编码代理及 AgentRunbook-C。

论文评测记忆返回的证据能否支持 QA，以及查询延迟；不能把长历史等同于待测 agent 连续完成了这些任务。返回上下文的 token 上限也不等于总存储上限。V2 的关注度需与 V1 分开报告。

证据：[论文](https://arxiv.org/html/2605.12493)、[官方代码](https://github.com/xiaowu0162/LongMemEval-V2)、[实际数据文件](https://huggingface.co/datasets/xiaowu0162/longmemeval-v2/tree/main)。

### 2. GOAT-Bench：较成熟的视觉行动验证平台

在同一室内场景中连续寻找 5–10 个目标，输入为 RGB-D、位姿与文字或图像目标，每子任务最多 500 个动作。CVPR 2024 原始工作之外，CVPR 2025 的 3D-Mem 已在其上评测记忆，并提供每子任务清空记忆的对照；这是比 star 更直接的研究采用证据。

官方依赖较旧，场景资产需按 HM3D 的访问流程获取。原版并非跨日动态部署；若扩展目标数或引入物体迁移，应作为新协议单列。公开仓库未检出独立 LICENSE，不能据此宣称具有宽松开源许可。

证据：[官方代码和资源入口](https://github.com/Ram81/goat-bench)、[权重与特征文件](https://huggingface.co/datasets/axel81/goat-bench/tree/main)、[3D-Mem 的 GOAT 评测](https://openaccess.thecvf.com/content/CVPR2025/papers/Yang_3D-Mem_3D_Scene_Memory_for_Embodied_Exploration_and_Reasoning_CVPR_2025_paper.pdf)。

### 3. EgoLife / EgoLifeQA：自然视觉的长期经历来源

六位参与者共同生活一周，合计约 300 小时的第一人称生活记录；不是每位参与者各有 300 小时。官方发布视频、QA、caption 及 EgoRAG。Ego-R1 等后续方法采用了 EgoLifeQA，说明已有后续比较基础。

它仍然是 QA。只有按时间写入、限制保留量并禁止无成本回读已丢弃视频，才适合论证压缩取舍。Ego-R1 因使用部分问题训练而采用清理后的评测子集，复用其 baseline 时必须对齐 split。代码使用 S-Lab 许可，数据卡另有许可标记，应分别核实。

证据：[CVPR 2025 论文](https://openaccess.thecvf.com/content/CVPR2025/html/Yang_EgoLife_Towards_Egocentric_Life_Assistant_CVPR_2025_paper.html)、[代码](https://github.com/EvolvingLMMs-Lab/EgoLife)、[视频与标注](https://huggingface.co/datasets/lmms-lab/EgoLife/tree/main)、[Ego-R1 的评测说明](https://egolife-ai.github.io/Ego-R1/)。

### 4. LongMemEval：成熟的更新与跨会话对照

ICLR 2025；500 个问题，覆盖跨会话推理、知识更新、时间推理和拒答等。M 版本每个样例约 500 个历史会话。官方提供长上下文与检索 baseline，并于 2025 年 9 月发布清理后的历史。

优先采用 cleaned 数据，配合固定预算；oracle 只用于区分读取与检索瓶颈。它的价值是机制对照和比较基础，不能据其成绩直接声称改善了长期视觉任务。

证据：[代码与版本说明](https://github.com/xiaowu0162/LongMemEval)、[清理版数据](https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/tree/main)。

### 5. MemoryAgentBench：增量写入和冲突消解诊断

ICLR 2026；将信息分块增量写入，覆盖检索、测试时学习、长距离理解和选择性遗忘，提供 EventQA、FactConsolidation 等数据。代码 README 将相关维度称为 Conflict Resolution。已有多类 RAG、长上下文和外部记忆系统接口。

FactConsolidation 适合检验新证据是否覆盖过期事实，但答对冲突问题不证明系统真正删除了旧存储，也不直接证明预算下遗忘策略有效。它与 LongMemEval 存在任务覆盖重叠，组合使用时重点取其独有子任务。

证据：[论文](https://arxiv.org/html/2507.05257)、[代码与指标对应表](https://github.com/HUST-AI-HYZ/MemoryAgentBench)、[数据文件](https://huggingface.co/datasets/ai-hyz/MemoryAgentBench/tree/main)。

## 上轮候选与其他平台为何降级

| 候选 | 核查结果 | 本轮决定 |
| --- | --- | --- |
| ScenDroid | 官方仓库 0 star；基础框架已公开，模拟器镜像、用户模拟器及更多 agent 仍待发布 | 保留任务设计参考，不作为优先复现对象 |
| STARBench / STAR | 分别 5 / 6 star；benchmark 有代码和下载脚本，方法 README 仍有未完善部分；未检出独立许可文件 | 不再放在成熟基准之前；不能误写成完全未公开 |
| WorldLines、EvoNav-Bench | 上轮核查到论文，但未定位到可核实的官方代码与完整数据入口 | 待资源核实，不进入本轮前五；“未找到”不等于证明不存在 |
| MemoryArena | 60 star / 12 fork；已有任务代码及数据，但 README 明确标为 preview；平均约 57 个动作 | 从前五降为观察项，继续关注正式发布与后续采用 |
| FindingDory | 环境仓库 10 star / 1 fork；已有公开资源，采用证据仍少 | 次级视觉诊断候选 |
| LifelongAgentBench | 98 star / 6 fork；代码数据公开，但 DB / OS 任务之间恢复或重建环境 | 主要测技能经验迁移，暂不作为动态世界状态记忆的主评测 |
| RoboMME | 官方 benchmark 仓库 164 star / 23 fork；已公开，且 LeRobot 提供集成文档 | 有采用基础，但主要是 episode 内记忆，保留为短程诊断 |
| BEHAVIOR-1K | 1,691 star / 246 fork；成熟的具身任务平台 | 热度较高，但不能据任务动作长直接推断需要长期记忆 |

证据：[ScenDroid](https://github.com/GoooKuuu/scendroid)、[STARBench](https://github.com/ut-amrl/STARBench)、[STAR](https://github.com/ut-amrl/STAR)、[MemoryArena](https://github.com/ZexueHe/MemoryArena)、[FindingDory](https://github.com/findingdory-benchmark/findingdory-habitat)、[LifelongAgentBench 环境重置说明](https://arxiv.org/html/2505.11942)、[RoboMME 官方仓库](https://github.com/RoboMME/robomme_benchmark)、[LeRobot 集成](https://github.com/huggingface/lerobot/blob/main/docs/source/robomme.mdx)、[BEHAVIOR-1K](https://github.com/StanfordVL/BEHAVIOR-1K)。

## 建议的后续验证（尚未执行）

先审计 LongMemEval-V2 Small 和 GOAT-Bench 的最小运行链，分别检验多模态记忆接口与行动收益；EgoLife 用于确认自然视觉的跨日适用性。机制对照从 LongMemEval-M 与 MemoryAgentBench 的 FactConsolidation 选取即可，不必一次跑五个完整基准。

统一固定基座、可访问历史和总存储口径；原始视频、截图、摘要、索引及代理私自保留的副本均需计入相应预算。区分记忆容量与查询上下文，报告成功率或 QA 质量随历史增长的变化，并单列检索、查询及重新探索成本。新增预算、时间延展和世界动态规则均需清楚标为我们提出的协议。
