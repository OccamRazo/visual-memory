# FQR 候选方向：动机强度、最近邻工作与剩余问题

- 日期：2026-09-02
- 状态：基于当前公开论文与既有项目调研形成的方向判断，不是最终选题结论
- 目的：把“问题是否重要”“现有工作是否解决”“剩余空间是否足以成篇”分开评价

## 0. 先给结论

当前最值得继续深挖的不是更复杂的单条 memory value，而是下面这个统一问题：

> **在未来问题未知、原始流不可回看、记忆预算固定的条件下，系统怎样保留至少一条完整的最小充分证据路径；如果没有任何完整路径存活，又怎样识别并定位自己为何已经不可回答？**

它由两个相连但应分阶段完成的子问题组成：

1. **A：证据集合几何（主问题）**——从逐条证据价值转向最小充分证据 bundle、替代路径、共享核心和 task-family coverage；
2. **C：压缩后可回答性诊断（安全层）**——判断完整证据路径是否仍存活，并区分 store、access、use 三类失败。

四个候选方向的综合判断如下。动机评分只衡量问题强度，不等于新颖性评分。

| 方向 | 真实且普遍 | 结构性 | 可测 headroom | 核心影响 | 可证伪性 | 动机总分 | 剩余研究空间 | 当前判断 |
|---|---:|---:|---:|---:|---:|---:|---|---|
| A. Pre-query 证据集合几何 | 5 | 5 | 5 | 5 | 4 | **24/25** | 高，但必须超越“maximum coverage”措辞 | **第一优先级** |
| C. 压缩后可回答性与故障归因 | 5 | 5 | 5 | 5 | 3 | **23/25** | 中高；普通“compression-aware abstention”已被占据 | 只做 certificate / localization 版本 |
| B. 未来观察触发的延迟重估 | 4 | 5 | 4 | 5 | 3 | **21/25** | 高，但真实 effect size 尚未建立 | 高上限诊断支线 |
| D. 压缩等变的时间测度 | 4 | 4 | 2 | 3 | 5 | **18/25** | 条件性；相邻修补方案已经密集 | 两周诊断或备选机制 |

评分判据：

1. **真实且普遍**：不是为 benchmark 人造的边缘错误；
2. **结构性**：增加模型尺寸、上下文或普通工程优化不会自然消失；
3. **可测 headroom**：存在同预算 oracle、反事实干预或强控制表明问题可改善；
4. **核心影响**：直接影响长程视觉记忆的能力、可靠性或可扩展性；
5. **可证伪性**：能否先用可控实验决定继续或止损。

---

## 1. A：从逐条 FQR 到 pre-query 证据集合几何

### 1.1 为什么动机足够强

**[事实]** [EMBER](https://arxiv.org/abs/2606.05894) 已经把几乎相同的资源协议定义为 Budgeted Pre-Query Retention：写入时问题未知、读取时不能访问完整原始流、保留的源证据受固定 token 预算约束。在 LongMemEval-RR 的 8192-token 点，EMBER-14B 的 F1 为 0.3017，而同预算 oracle retention 为 0.4499；Retain-Recall 为 0.3215，而 oracle 为 0.9998。这不是“略有提升空间”，而是写入决策仍远未达到证据可保留上界。

**[事实]** EMBER 的 MultiQ 设置更直接暴露 task-family coverage 问题：一份冻结记忆同时服务五个未来问题。在 10% 预算下，EMBER-14B 的 mean-query Retain-Recall 为 0.3081，oracle 为 0.6275；coverage balance 为 0.0356，oracle 为 0.0517。通用 heuristic 的 coverage balance 全为 0。说明平均保住若干证据不等于为每个问题保住一条可用证据路径。

**[事实]** [OSL-MR](https://arxiv.org/abs/2606.10616) 明确承认 retention reward 是 non-decomposable、combinatorial 的，因为质量取决于一组 memories，而非单条 memory；它还证明单步子问题推广了 budgeted maximum coverage。其可控实验中，即使每一步都精确最大化当前收益，面对 demand shift 仍距最优 31.5%，加入昂贵 reacquisition 后仍差 19.3%。这说明逐时、逐条优化的不足是结构性的。

**[事实]** [CVMA](https://arxiv.org/abs/2607.25467) 对视觉 KV 做成对因果干预：当前 attention 与未来区域效用在 4×4 粒度上的 Spearman 为 -0.103，按当前 attention 联合保留甚至差于随机；但同一对话的 marginal-utility control 显著优于随机。这同时证明了“常用 proxy 错位”与“仍有可选信号”。

**[事实]** [REVEAL](https://arxiv.org/abs/2608.08612) 的最大单项增益来自 evidence sufficiency verifier：在 Video-MME-long/LVBench 上分别增加 7.8/10.9 点；无 verifier 时约 128 个片段达到 76.2%，有 verifier 时平均约 31 个片段达到 79.1%。这说明 relevance/volume 不是主要矛盾，决定性条件是证据是否已经完整满足问题。

**[判断]** 这些证据共同支持一个很强的动机：当前方法主要优化“保留了多少看起来有用的证据”，而真正决定答案的是“是否至少有一条完整、可访问、可用的充分证据路径存活”。两者在多跳、顺序、计数、身份绑定和状态变化问题上不等价。

### 1.2 最近邻工作到底做到哪里

#### EMBER：最接近协议与系统目标

它已经解决：

- 明确定义 query-hidden writer 与 no-raw-log read；
- 保留 source-backed evidence capsule，而不是只留摘要；
- 将 survive、read、answer 三段结果用于 writer 的延迟训练；
- 提供 single-query 与 MultiQ 的预算曲线。

它没有解决透：

1. **没有显式刻画最小充分证据族。** 其 reward 会联合评价整条 trajectory，因此不能简单说它“只做 item-wise”；但存储对象和监督仍以 source span / gold evidence unit 为基本单位，没有建模“哪些证据必须 AND 在一起、哪些 bundle 彼此可替代”。
2. **没有解释 MultiQ 困难来自哪里。** query 数量、query entropy、证据 bundle 大小、bundle 间重叠、共享核心和替代路径被混在一个总结果里。
3. **没有 task-family 的可计算 frontier。** 它给 budget curve，但没有给同一实例上的 post-query、offline-pre-query、causal-pre-query 三类 oracle，因此无法量化“未知问题本身的价格”。
4. **证据标签仍是 benchmark 定义的文本单元。** 对视觉事件、对象轨迹、OCR、动作顺序等异构证据，粒度和联合充分性尚未验证。

#### OSL-MR：最接近组合优化形式

它已经解决：

- 把长期 retention 写成硬预算、部分可观测、多步随机优化；
- 显式纳入 miss、reacquisition、staleness 与延迟反馈；
- 证明 maximum-coverage 核心与 NP-hardness；
- 用 exact small instances 测量 myopic 与 multi-step 的差距。

它没有解决透：

1. **其已知 coverage 目标是“覆盖 evidence element 的并集”。** 这是典型的 OR/additive coverage；复杂 QA 更常见的是 bundle 内 AND、bundle 间 OR。例如 `{看到钥匙, 看到交付, 看到后来开门}` 三项缺一不可，但也可能存在另一条完整的口头证据路径。
2. **为可部署性退回到 per-memory evidence-membership scorer。** 论文自己说明直接 set reward 难以归因，所以用逐条 evidence membership 学习。它绕过了集合交互，而没有恢复这些交互。
3. **没有区分“覆盖元素”与“使答案可判定”。** 覆盖 80% 的若干 bundle，可能没有任何一个 bundle 完整，最终 answerability 仍为 0。
4. **未来需求是文本 query demand。** 没有视觉证据粒度、编码损失与 consumer 可用性的联合分析。

#### DeMem：最接近理论边界

[DeMem](https://arxiv.org/abs/2605.10870) 已给出 decision rate–distortion、exact forgetting boundary、decision covering/packing numbers，并证明描述相似性不是正确的压缩准则。

它没有覆盖我们的关键协议：

- 其回答时 encoder 是 query-aware 的：`M_t = g_t(H_t, Q_t)`；
- forgetting boundary 在固定 query fiber 内定义；
- 它研究哪些 histories 对当前已知 query 可共享一个 decision state，而不是一个 query-agnostic encoding 怎样同时服务未知 future task family；
- 它不刻画源证据 bundle 的可恢复性、检索可达性与视觉编码损失。

因此，不能声称“首次对记忆做 rate–distortion / covering”；剩余问题必须明确是 **common pre-query encoding under a family of unknown tasks**。

#### REVEAL：最接近 evidence sufficiency，但协议相反

REVEAL 已经很好地证明 relevance 不等于 sufficiency，也能根据缺失 rubric 继续有针对性地检索。但它在 query 已知后工作，且离线 memory / 原视频片段仍可被再次访问。它解决的是“怎样从仍存在的全库中补齐证据”，不是“不可逆 pre-query 压缩后，怎样事先保留完整证据路径”。

### 1.3 真正还没做透的问题

对每个未来问题 `q`，定义其最小充分证据族：

\[
\mathcal E_q=\{E_{q,1},E_{q,2},\ldots\},
\]

其中每个 `E_{q,k}` 是一条可独立支持答案的最小 bundle。保留集合为 `M` 时，最简单的精确 answerability 是：

\[
A(q,M)=\mathbf 1\!\left[\exists k,\ E_{q,k}\subseteq M\right].
\]

这形成“bundle 内 AND、bundle 间 OR”的超图覆盖，而不是普通 evidence recall 或 additive maximum coverage。可进一步研究：

- **未知问题价格**：
  \[
  \Pi_Q(B)=D_{\mathrm{preQ}}(B)-D_{\mathrm{postQ}}(B);
  \]
- `Π_Q` 怎样随 query entropy、bundle order、bundle overlap、替代路径数变化；
- task family 是否存在小的 shared evidence core；
- side information（字幕、历史答案、实体图）怎样改变残余 bundle complexity；
- item-wise marginal / Shapley / learned scalar 在何种结构下必然失效；
- 存储、访问和 consumer 使用三个预算分别怎样改变 answerability frontier。

**[新意边界]** 超图覆盖、随机 set cover、函数源编码等数学对象本身不是新的。可辩护贡献应是：pre-query 视频记忆协议中的精确映射、可控结构诊断、oracle frontier、证明现有逐条 policy 在特定 evidence geometry 下的系统性 regret，以及 bundle-aware writer 的实际收益。

### 1.4 最小决定性实验与止损

先做一个可精确枚举的小型 Video Memory Gym：

- bundle size：1/2/3/4；
- bundle 内互补强度：从近似可加到严格 AND；
- bundle 间 overlap：0 到 1；
- 每个问题的替代路径数：1/2/4；
- task-family entropy、预算、延迟、视觉/字幕侧信息分别变化；
- 小实例用枚举或整数规划算 postQ / offline-preQ / causal-preQ oracle。

比较：recency、attention、salience、individual future utility、EMBER-style writer、OSL-style scorer、普通 maximum coverage、bundle-aware policy。

关键指标不是只有 evidence recall，而是：完整 bundle survival、worst-query answerability、answerability–budget frontier、interaction residual、`Π_Q(B)`。

**止损条件：** 若控制所有单条证据 recall 后，bundle interaction 对答案没有稳定额外解释力；或逐条 marginal policy 在不同 overlap/order 下都接近 exact oracle，则无需把集合几何升为主方向。

---

## 2. C：压缩后的可回答性、证书与故障归因

### 2.1 为什么动机足够强

**[事实]** 2026-08-30 出现的 [Compression-Aware Abstention](https://arxiv.org/abs/2608.29934) 已正面证明：KV 压缩不只是降低准确率，还会改变“当前上下文是否仍包含答案证据”。其小型 LoRA 在 prompt-style truncation 下减少 97% hallucination；但在真实 compressed-cache decoding、80% retention 下，最强模型 honest accuracy 只有 0.315，即使标签认为 answer-bearing span 存活，正确回答也只有 22/69。

**[事实]** 该论文的 span-survival 标签与 LLM judge 的语义充分性只有中等一致性（Cohen's κ=0.61，raw agreement 80%）；主要分歧恰好是答案字符串还在，但多跳 bridging evidence 已丢失。这是 A 中 bundle 完整性与 C 中 answerability 检测的直接连接点。

**[事实]** CVMA 说明低当前 attention 不能构成 safe-forgetting certificate；REVEAL 说明 sufficiency verification 是检索系统最大增益来源；[MemTrace](https://arxiv.org/abs/2606.17328) 又发现失败时“证据可检索但未被使用”约比“证据根本不可达”多 10 倍。因此，一个只输出“拒答”的模型会混淆至少三种不同故障：没存、没取到、取到但不会用。

**[判断]** 动机非常强，但普通版本已被占位。现在值得做的不是另一套 compression-aware refusal tuning，而是 **memory-loss diagnosis with controlled false-safe risk**。

### 2.2 最近邻工作与不足

#### Compression-Aware Abstention：直接占据普通版本

它已经解决：

- 用 compressor survival mask 自动构造 answer / abstain 监督；
- 同时验证 prompt truncation 与真实 compressed-cache inference；
- 测试多种 mask family，并做同长度对照；
- 证明小 adapter 能学到部分“证据被压缩掉时拒答”的行为。

仍未解决：

1. **标签不是 semantic sufficiency。** answer string 或短 span 存活不代表完整推理链存活，κ=0.61 已量化这一噪声。
2. **最难的高 retention 局部缺失仍失败。** 在 80% retention 的稀有 Abstain-gold 样本上，三次训练稳定 hallucinate 同样的 4/7；作者判断模型大量利用 retention ratio 和 deletion pattern，而非识别当前问题的特定证据是否存活。
3. **真实 compressed-cache answerability 仍很低。** 80% retention 的 honest accuracy 0.315，表明“检测”和“使用残存 KV”都未解决。
4. **只有二元行为。** 不说明是 storage、access 还是 consumer failure，也不给缺失证据 witness。
5. **没有风险保证。** 未控制最危险的 false-safe：模型说能答、但完整证据其实已经丢失。
6. **范围窄。** 主要是 MuSiQue 2-hop 文本、一个真实 compressed-cache 路径；尚未覆盖视频、长程 writer、跨 codec 与 streaming lifecycle。

#### CVMA：强因果审计，但不是部署证书

CVMA 的价值是把 proxy validity、未来视觉依赖和 image-to-text substitution 分开，并证明 attention 可能比随机更差。其边界也很清楚：

- 主要对象是一次图像 prefill 后的多轮对话，不是超长视频 streaming memory；
- 主指标是固定 teacher-forced trajectory 上的 NLL；
- marginal-utility control 需要未来对话及干预，不能在线部署；
- 作者明确将贡献定位为 audit，而不是新的 compression policy 或 certificate。

#### REVEAL：知道“还缺什么”，但可重新搜索

REVEAL 的 verifier 能列出 unmet evidence requirements，并回到完整离线视频 memory 中继续检索。它不需要区分“证据暂时没取到”与“证据已被不可逆删除”；因此不解决 bounded persistent memory 的 absent-evidence detection。

#### MemTrace：对故障归因的关键警告

MemTrace 发现 evidence-use failure 远多于 retrieval miss。若我们只用最终答错反推“记忆丢了”，会把 reader/consumer 的失败错误归因给 writer。任何证书方案都必须有分层干预：

1. 原证据是否进入 retained state；
2. query 后能否从 retained state 访问；
3. 访问后 consumer 是否能使用；
4. 完整证据 bundle 是否语义充分。

### 2.3 可辩护的新问题

将 query-time 状态拆成四类：

\[
Y\in\{\text{answerable},\ \text{storage-miss},\ \text{access-miss},\ \text{use-failure}\}.
\]

学习的不只是拒答概率，而是一个带 provenance / dependency witness 的诊断器 `C(q,M)`，并在选择性回答中约束：

\[
\Pr(\text{answer}\mid \text{insufficient})\leq \alpha.
\]

可实现形式不应声称 open-world 的形式证明；更现实的是：

- 在可控 evidence hypergraph 上给 exact certificate；
- 在真实视频上用 conformal / risk-control 校准 false-safe；
- writer 在 eviction 时保存极低码率 dependency/provenance sketch；
- query 时检测是否至少一条充分 bundle 的必要组件仍可定位；
- 若不可答，返回缺失类型和最小 repair request，而不是泛化拒答。

### 2.4 决定性实验与止损

- 对同一视频和 query 做 paired interventions，分别移除存储、破坏索引、保留证据但扰乱 consumer；
- gold label 来自 bundle survival 与强 reader/full-context 对照，而非 answer substring；
- 比较 verbalized confidence、entropy、REVEAL-style rubric、Compression-Aware Abstention、provenance detector；
- 报 risk–coverage、false-safe rate、failure localization、calibration、跨 compressor / backbone / evidence type 泛化。

**止损条件：** 若在固定 retention ratio、固定删除数量和 matched content hard negatives 下，诊断器优势消失；或它无法区分 storage 与 use failure，则不能包装为 certificate，只能称普通 abstention calibration。

---

## 3. B：未来观察触发的延迟重估与 causal hindsight

### 3.1 为什么动机强，但尚需先证实 effect size

未知未来问题只是第一类不确定性。第二类更深：一个事件在发生时即使未来 task family 已知，其重要性也可能要等后续视觉事实出现后才变得可知。例如：

- 早先无名的人物，后来才被叫出姓名；
- 早先普通的物体，后来成为事故原因或任务关键工具；
- setup 片段只有在 payoff 出现后才知道应与之绑定；
- 某个状态变化只有在后来异常或回退出现后才获得因果意义。

**[事实]** [ViSAGE](https://arxiv.org/abs/2607.28678) 已经给出直接视觉证据：延迟身份线索触发 Global Backward Update；去掉 Bidirectional Memory Refinement，M3-Bench-robot 下降 4.7 点。

**[事实]** OSL-MR 的 exact control 从另一侧说明未来耦合很强：当前最优的 myopic retention 在需求切换时仍可距全局最优 31.5%。

**[事实]** [Hindsight Memory-PRM](https://arxiv.org/abs/2608.29605) 证明通过后续 retrieval、citation 与删除-重答审计，可以给早期 memory operation 分配可审计 hindsight credit，并显著改善长期记忆组织。

**[判断]** 现象真实，但还没有论文直接测量“后来视觉观察使早期证据的重要性变得可知”在严格 bounded streaming writer 中占多大比例。ViSAGE 的 4.7 点集中在身份绑定；OSL-MR 的未来是 query demand；Hindsight Memory-PRM 的未来反馈来自 query/answer audit。故其动机得分高，但 headroom 证据不如 A/C 直接。

### 3.2 最近邻工作与不足

#### ViSAGE：最直接的 delayed visual evidence

它已经解决：

- entity-centric Incident Logs + Object Cards；
- later naming evidence 反向修正历史 `who` 字段；
- 通过身份约束交叉验证减少错配和无证据回答。

它未覆盖 RTC 的核心条件：

1. Incident Logs 是 append-only，事件内容 immutable，仅 `who` 可修正；
2. 没有固定 persistent-memory budget，也没有不可逆 eviction；
3. Global Backward Update 会遍历历史日志，默认旧记录仍在；
4. 修正的是身份语义，不是决定早期视觉证据是否应被 retention / promotion；
5. 当前实现限于 human-centric face/voice identity，非人物对象和动物被当作背景；
6. 没有 causal writer 与 whole-stream offline writer 的 oracle 差值。

#### Hindsight Memory-PRM：最接近 hindsight credit 机制

它已经解决：

- 用 retrieval/citation/deletion-reanswer 给 Write/Merge/Noop 分配 operation-conditioned credit；
- 保留 source-turn mapping，使反事实审计可定位；
- 证明 outcome-only credit 对长 memory trajectory 不够。

但它明确使用 lossless substrate：自动 verbatim layer 保存每一轮，Merge 的旧版本也保留，并排除 destructive deletion。作者在 limitations 中承认 LoCoMo 没有 budget pressure、forgetting 被低估，需要 streaming benchmark。因此它优化的是索引和压缩组织，不是固定总存储下“当初没保留就永远丢失”的 retention。

此外，其 credit 来自后续问题、引用与重答审计，不是后来视频观察对早期事件的重新解释；chain-shared credit 还会高估可由其他操作补偿的 entry。

#### OSL-MR：未来需求，不是未来观察

OSL-MR 的 multi-step value 对未来 demand shift 有效，但没有修改旧 memory 的语义，也没有估计某个未来视觉事件对旧事件的反事实边际贡献。它说明 myopia 是结构问题，却没有回答“何时重要性首次变得可知”。

#### RetroAttention / Event-Causal RAG 等邻近机制

- [RetroAttention](https://proceedings.iclr.cc/paper_files/paper/2026/hash/f4daa773a5bb2d562a9204a7e2225a67-Abstract-Conference.html) 用后来加载的文本 KV 修订过去 attention output，目标是生成中的 context integration，不是 retention/promotion；
- [Event-Causal RAG](https://arxiv.org/abs/2605.06185) 记录 State–Event–State 图并在 query time 双向检索因果链，旧原始证据仍可访问；
- foresight / surprise 类方法预测当前观测的未来价值，但没有在未来事实真正到达后给旧事件分配 causal hindsight credit。

### 3.3 更清楚的形式化问题

必须把两种 uncertainty 分开：

- `Q`：未来会问什么未知；
- `H_{t+1:T}`：未来还会观察到什么未知。

定义三种同预算 oracle：

1. `postQ`：见到 query 后再从完整历史压缩；
2. `offline-preQ`：不知道 query，但写入者见完整视频后统一压缩；
3. `causal-preQ`：不知道 query，也只能逐时看到视频并在固定预算内更新。

未来观察的不确定性价格为：

\[
\Pi_H(B)=D_{\mathrm{causal-preQ}}(B)-D_{\mathrm{offline-preQ}}(B).
\]

若 `Π_H` 明显大于 0，才证明 RTC 不是普通 pre-query selection 的改写。还应估计每个事件的 **knowability time**：其未来效用在何时、依赖哪一条后来证据才可被可靠判断。

严格流式下，一个关键限制不能回避：未来上下文只能提升仍存 sketch 的优先级，不能恢复已删除的像素细节。因此方法必须选择其一：

- 保留所有事件的超低码率 forensic tier，未来触发 promotion；
- 允许原视频外存并把重新编码 I/O 纳入预算；
- 或只研究在 eviction deadline 前到达的 delayed evidence。

### 3.4 决定性实验与止损

构造/筛选四类 delayed-knowability 流：identity reveal、setup–payoff、later-used object、anomaly recontextualization。对每类严格控制 delay、干扰、forensic bitrate 和 raw-video availability。

比较 causal myopic、causal learned、bounded forensic + backward credit、offline-preQ oracle、postQ oracle。报告 `Π_H(B)`、promotion precision、早期证据 survival、不可恢复细节比例、额外 I/O。

**止损条件：** 若真实或高质量合成流中 `Π_H` 很小；若大部分收益可由最近窗口/简单对象跟踪获得；或所有提升都依赖无限原视频回看，则 RTC 不足以成为独立主方向。

---

## 4. D：压缩等变的时间测度（TM-KV）

### 4.1 动机存在，但当前证据不足以直接立项

核心直觉仍正确：合并后的 token 可能代表多个不连续时刻或一段长区间，而普通位置编码只给它一个点；不同 FPS、block size、merge tree 和召回拼接顺序会改变 cache index，却不应改变同一物理事件的时间关系。

但这个问题的相邻解法在 2026 年已经非常密集：

- [PAS](https://arxiv.org/abs/2511.10979) 已把 M-RoPE 的 frame-scale ripple 形式化，并用 phase aggregation 稳定小时间偏移；在 matched-token 结果中，MVBench 从 67.2 提到 69.5、TempCompass 从 71.5 提到 73.3；
- [TIE](https://arxiv.org/abs/2605.10543) 已把 interval 提升为 RoPE-compatible 一等对象，给出一般概率 kernel 的积分形式与 uniform kernel 的 sinc closed form；在视频生成中，TCSR 从 77.34% 提到 96.03%；
- [ST-Merge](https://arxiv.org/abs/2606.29350) 已对 merge 后 token 重新计算三维加权质心和 RoPE；
- [TTF](https://arxiv.org/abs/2605.07355) 已让 surviving token 保留原 `(t,y,x)` 坐标，并使 decode position 与实际 cache 对齐；作者报告移除约 67% token 时保留约 99.5% aggregate accuracy；
- [CRAFT](https://arxiv.org/abs/2608.01644) 已做 position-aware recursive fusion，在约 8× 压缩时保留约 97% 平均准确率；
- [Kamera](https://arxiv.org/abs/2606.23581) 已解决 chunk relocate/reorder 时的 RoPE 重旋转与 position-invariant KV reuse。

**[判断]** 因而“点时间不够”“应该用 interval”“merge 后要修坐标”“采样偏移要稳定”都不能再作为独立新意。当前缺少的是决定性证据：在 PAS、TIE、centroid 和 true-coordinate controls 都加入后，compression path 本身是否仍造成足够大的 temporal error。

### 4.2 各最近邻尚未覆盖的精确缝隙

#### PAS

PAS 平滑的是同一批 merged-frame tokens 上 M-RoPE 的 phase ripple；它不记录一个 compressed token 的完整 temporal support，也不要求两种 merge tree 得到相同表示。它解决 sampling-offset sensitivity，而非 compression-operator equivariance。

#### TIE

TIE 已经非常接近“时间测度”：其一般形式是对概率 kernel `μ_I` 上的 RoPE 做期望。因此不能声称 content-weighted temporal distribution 本身首次出现。

剩余差异只能是：

- TIE 的主要对象是 video-generation cross-attention 中“点状视觉 token 对 interval textual event”；
- uniform interval 是其闭式主实例；
- 它不研究由递归 token merge provenance 诱导的 measure；
- 不要求 merge associativity / path invariance；
- 不评估 video understanding 中同一内容在不同压缩树、FPS 和 retrieval reorder 下的不变性。

#### ST-Merge

加权质心只保留一阶矩。两个时间支持只要均值相同——例如 `{1,9}` 与 `{4,6}`——就获得相同时间点，但其跨度、多峰性和与 query interval 的关系不同。论文重点也主要是浅层 vision-encoder merging 和机器人 latency，没有系统 stress test merge-tree invariance。

#### TTF

TTF 对 surviving token 保留原坐标，但被判定冗余的 source token 直接由 anchor token identity replacement，不形成表示其所有来源时刻的 temporal support。论文自己的 MVBench 结果也显示 motion-intensive probes 比 aggregate benchmark 更敏感，但没有把误差归因到 support collapse、内容损失还是 anchor selection。

#### CRAFT

CRAFT 的内部 weighting scorer 使用 3D 坐标，融合 token 对 LLM 仍以某个 survivor 的原始绝对位置进入序列；它没有暴露 provenance-induced temporal distribution，也未要求递归融合对 merge order/path 等变。其常规评测通常固定 FPS 与 compression procedure，不能回答 counterfactual path consistency。

#### Kamera

Kamera 解决同一个缓存 chunk 搬到新序列位置后如何恢复 RoPE 与 cross-chunk conditioning；它没有解决一个 token 本身代表多个物理时间的问题。

### 4.3 只有这个版本仍可能成立

令压缩 token `z` 的时间支持为测度：

\[
\mu_z=\sum_i w_i\,\delta_{t_i},\qquad \sum_i w_i=1.
\]

merge 应在测度空间满足：

\[
\mu_{\operatorname{merge}(z_1,z_2)}
=\alpha\mu_{z_1}+(1-\alpha)\mu_{z_2},
\]

并使不同合法 merge tree 在相同最终 provenance weights 下得到相同 temporal representation。可用有限 characteristic features：

\[
\phi_\omega(\mu)=\mathbb E_{t\sim\mu}[e^{i\omega t}],
\]

但必须承认这与 TIE 的一般 kernel integral 数学上高度相邻。真正贡献要来自 **compression algebra、path-invariance theorem、measure-to-measure video attention、以及现有点/区间 controls 失败的实证**，而不是 Fourier 表达本身。

### 4.4 决定性实验与止损

对同一视频内容只改变：FPS、sampling offset、block size、merge tree、compression ratio、retrieval reorder。比较 M-RoPE、PAS、center、start/end、TIE-uniform、ST-Merge centroid、TTF/CRAFT-style coordinates 与 measure encoding。

主要指标：答案一致率、temporal QA、interval grounding、duration/order error、attention-kernel distortion、path invariance error。

**止损条件：** 若强 controls 后同一内容的 temporal answer consistency 已高；或 measure encoding 只改善 attention error、不改善 temporal task；或收益只发生在极端人造多峰 merge，则不应把 TM-KV 升为主方向。

---

## 5. 横向判断：哪些问题是真正没解决透

| 已有工作基本解决 | 仍明显未解决 |
|---|---|
| query-hidden、固定证据预算的协议定义（EMBER） | 未知 task family 下的最小充分 bundle 几何与完整路径 survival |
| 多步 retention、maximum coverage 与 delayed demand（OSL-MR） | AND-complementarity、替代证据路径、shared core 与 query-uncertainty price |
| query-aware decision rate–distortion（DeMem） | 一个 common pre-query encoding 同时服务未知 query family 的 frontier |
| query-time sufficiency verification 与再检索（REVEAL） | 不可逆压缩后的 absent-evidence detection 与 repair impossibility |
| compression-aware 二元拒答 | store/access/use 分层归因、缺失 witness、false-safe risk control |
| 延迟身份回写（ViSAGE） | 固定总预算下由未来视觉事实驱动的早期 retention/promotion |
| hindsight operation credit（Memory-PRM） | destructive forgetting、严格 streaming 与未来观察 credit |
| interval / phase / centroid / coordinate 修正 | compression path invariance 是否仍是显著真实瓶颈 |

最关键的判断是：**A 的最近邻论文已经把问题暴露出来，却通过可计算 surrogate 绕开了最难的集合交互；C 的最近邻论文则把普通版本做出来，同时用其失败案例证明 bundle-aware diagnosis 仍未解决。** 这两者不是牵强拼接，而是同一个 answerability bottleneck 的 writer 侧与 verifier 侧。

---

## 6. 推荐研究路线

### 第一阶段：只做问题测量，不急于造大模型

建立 exact small world，回答三个问题：

1. evidence bundle interaction 在控制 individual recall 后是否仍显著；
2. `Π_Q(B)` 和 `Π_H(B)` 哪一个更大；
3. storage、access、use 三类失败各占多少。

若 A 通过止损线，论文中心应是：

> **Beyond Evidence Recall: Bundle-Aware Pre-Query Memory under Unknown Future Tasks**

FQR 不再以“给每条 event 一个 future-query score”为新意，而作为 task-family 风险协议或 bundle-aware robust objective。

### 第二阶段：A 为主方法，C 为审计而非堆模块

- writer 优化完整 bundle survival / worst-query answerability；
- evaluator 同时报告 item recall 与 bundle survival，证明二者不可替代；
- 使用轻量 certificate 检查无完整路径时的 false-safe，但先不把完整 diagnosis 系统塞进同一首篇。

### 第三阶段：按诊断结果分叉

- 若 `Π_H` 大：推进 B，研究 bounded forensic tier + causal hindsight promotion；
- 若 silent failure 比 retention regret 更突出：把 C 独立做成 lifecycle diagnosis / calibrated certificate；
- 若 FPS/merge-tree counterfactual 在强 controls 下仍有显著差：再把 D 升为压缩等变机制论文。

## 7. 最终 go / no-go

- **A：Go。** 动机、直接 headroom、结构缺口和可控形式化同时成立；但必须用 bundle interaction 与 oracle frontier 超越 EMBER/OSL-MR。
- **C：Conditional Go。** “compression-aware abstention”本身 No-Go；“bundle survival + store/access/use localization + risk-controlled false-safe”才 Go。
- **B：Diagnostic Go。** 先测 `Π_H`，不先承诺大系统；若 effect size 足够，科学上限可能高于 A。
- **D：No-Go as flagship for now。** 只值得用低成本 counterfactual test 决定是否复活。
