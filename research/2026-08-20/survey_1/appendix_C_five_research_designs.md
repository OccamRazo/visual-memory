# 视觉记忆 × 超长视频：2025–2026 交叉前沿、技术空白与五个研究方案

> 调研截点：2026-08-20。本文专门补充“视觉记忆/压缩”与“超长、流式视频理解”的交叉地带，不替代两侧各 30 篇工作的完整文献表。2026 年多数工作仍是新近预印本，本文将“技术最近邻”与“已形成影响力/正式接收”分开，不把新预印本误写成高影响力定论。

## 0. 先核验容易写错的论文名与版本

| 常见称呼 | 核验后的原始工作 | 版本边界与结论 |
|---|---|---|
| SelectStream | [What Should a Streaming Video Model Remember?](https://arxiv.org/abs/2606.16353v1), arXiv:2606.16353v1, 2026-06-15 | **真实**。SelectStream 是方法名，不是论文标题。核心是 surprise-driven adaptive windowing、priority-preserving consolidation、query-conditioned graph retrieval、latent evidence injection。 |
| Latent Visual Cache / Latent-VC | [Latent Visual Cache for Video Reasoning](https://arxiv.org/abs/2607.02607v1), arXiv:2607.02607v1, 2026-07-01 | **真实**。论文标题用 *Visual Cache*；正文把方法写作 **Latent Video Cache (Latent-VC)**。它主要解决生成过程中的 Visual Anchoring Decay，不是无限流式输入压缩。 |
| One Token per Multimodal Evidence | [One Token per Multimodal Evidence: Latent Memory for Resource-Constrained QA](https://arxiv.org/abs/2606.10572v1), arXiv:2606.10572v1, 2026-06-09 | **真实**。当前实验是 text/image evidence QA；论文明确承认独立 token 会丢长视频的时间顺序与结构，并把复杂视频列为 future work。不能把它写成已完成的长视频方法。 |
| Frames2LoRA / Video2LoRA | 当前版：[Frames2LoRA: Parametric Video Internalization for Vision-Language Models](https://arxiv.org/abs/2606.04351v2)，早期版：[Video2LoRA](https://arxiv.org/abs/2606.04351v1) | **二者是同一 arXiv 编号的改名**。v1（2026-06-03）叫 Video2LoRA，v2（2026-06-10）改为 Frames2LoRA。引用当前工作应写 Frames2LoRA, arXiv:2606.04351v2；另有同名的视频生成论文，不能混淆。 |
| ObjectStream | [ObjectStream: Latent Objects as Memory Anchors for Streaming Video Understanding](https://arxiv.org/abs/2607.28312v2), arXiv:2607.28312v2, 2026-08-01 | **真实**。training-free；在冻结 Video-LLM 特征中发现 latent objects，以对象历史、对象变化残差、近期窗口组成记忆。 |
| StreamFlow | [StreamFlow: Dynamic Memory Flows for Streaming Video Understanding](https://arxiv.org/abs/2608.10949v1), arXiv:2608.10949v1, 2026-08-11 | **真实且是本调研截点非常近的工作**。在视觉编码前按像素残差过滤，构建 latent long-term memory，并以 visual attention score 触发生成期动态注入。 |

额外的标题版本提醒：`video-SALMONN S` 的 v1 标题是 *Streaming Audio-Visual LLMs Beyond Length Limits via Memory*，当前 v2 标题已改为 [Memory-Enhanced Streaming Audio-Visual LLM](https://arxiv.org/abs/2510.11129v2)。

## 1. 2025–2026 交叉脉络：从“少放 token”走向“决定记什么、何时想起”

### 1.1 第一阶段：把视频变成受控大小的 token/KV（2025）

这一阶段的主要目标是让离线 Video-LLM 进入 streaming 场景，记忆载体仍主要是 visual tokens 或 LM KV cache。

| 工作 | 记忆载体与关键决策 | 仍未解决的问题 |
|---|---|---|
| [ReKV](https://arxiv.org/abs/2503.00540) | 将历史 video KV 存 RAM/disk，问题到来后检索并加载；分离视频编码与 QA | 外存可增长；检索到的是层级 KV 块，语义结构弱 |
| [VideoScan](https://arxiv.org/abs/2503.09387) | 每帧一个 semantic carrier；视觉 token 只在 prefill 使用 | 单帧统一摘要容易损失局部对象、空间与短瞬态证据 |
| [ProVideLLM](https://arxiv.org/abs/2504.13915) | 长期文本摘要 + 短期 DETR-QFormer 视觉 token 的双模态 cache | 文本摘要不可逆，答案所需的未语言化细节可能永久丢失 |
| [LiveVLM](https://arxiv.org/abs/2505.15269) | streaming-oriented KV compression + 问题到来后的长短期检索 | 主要是 cache 管理，缺少任务充分的 latent codec |
| [InfiniPot-V](https://arxiv.org/abs/2506.15745) | TaR 去时间冗余、VaN 保留显著 token，硬性长度无关 KV 上限 | query-agnostic heuristic 不等于未来问题的期望效用 |
| [StreamMem](https://arxiv.org/abs/2508.15717) | generic query tokens 对 visual KV 打分，维持 fixed-size KV memory | generic query 只近似未知未来问题分布；结构与可解释 evidence 弱 |
| [StreamForest](https://arxiv.org/abs/2509.24871) | Persistent Event Memory Forest + fine-grained recent window | 事件树仍由相似性/时间/merge 次数驱动，未显式学习“不可替代证据” |
| [StreamingTOM](https://arxiv.org/abs/2510.18269) | pre-LLM causal token reduction + 4-bit online quantized memory | 高效但以压缩/量化为主，记忆内容的语义充分性未被直接优化 |

### 1.2 第二阶段：从 flat cache 走向层级、事件、推理状态和 fast weights（2025 下半年–2026 上半年）

| 工作 | 新增的结构/机制 | 关键边界 |
|---|---|---|
| [video-SALMONN S](https://arxiv.org/abs/2510.11129v2) | TTT_MEM fast-weight 长期记忆 + 固定 token memory + modality-aware reader；引入 ELViM | 参数记忆可连续吸收历史，但仍会丢弃相似 token；稀有精确事实与干扰控制没有独立 episodic 通道 |
| [VisMem](https://arxiv.org/abs/2511.11007)（CVPR 2026） | short-term visual-dominant + long-term semantic-dominant latent vision memory | 重点是通用视觉理解/推理/生成，不是严格因果、未知问题、无限流式协议 |
| [HERMES](https://arxiv.org/abs/2601.14724v4)（ACL 2026 Main） | 将不同层的 KV cache 解释为多粒度 hierarchical memory，training-free 重用 | “哪一条证据不可替代”仍由 cache 行为间接决定 |
| [FluxMem](https://arxiv.org/abs/2603.02096) | 时间邻接选择 + 空间域合并，自适应 compression ratio | training-free 相似性压缩，缺少下游反事实效用监督 |
| [Thinking in Streaming Video / ThinkStream](https://arxiv.org/abs/2603.12938)（ECCV 2026） | Watch–Think–Speak；以中间 reasoning trace 替换旧视觉 token；Streaming RLVR | textual reasoning memory 容易继承早期误读，且未语言化视觉细节不可恢复 |
| [Think While Watching](https://arxiv.org/abs/2603.11896) | segment-level causal memory、三阶段多轮 CoT 数据与 stage-matched training | 更重视连续推理/多轮协议，细粒度视觉 payload 和独立证据检索仍有限 |
| [OASIS](https://arxiv.org/abs/2604.17052) | hierarchical event memory；短上下文先答，uncertainty 时按 high-level intent 细化检索 | uncertainty/intent 路由仍可能错过不会被语言化的视觉证据 |
| [QueryStream](https://proceedings.iclr.cc/paper_files/paper/2026/hash/0b17d256cf1fe1cc084922a8c6b565b7-Abstract-Conference.html)（ICLR 2026） | query-aware differential pruning + relevance-triggered response | 适用于 query 已知/持续监控某意图；不能替代“写入时未知未来问题”的通用记忆 |

### 1.3 第三阶段：latent evidence allocation、对象锚点、生成期重激活与参数内化（2026-06 至今）

- **SelectStream** 把问题统一为 `when to write / what to keep / how to retrieve / how much to expose`，这是很重要的表述升级；但其记忆仍主要是 projected visual embeddings，surprise 与访问频次不等于对未来答案的因果价值。
- **CausalMem**（[arXiv:2606.25658](https://arxiv.org/abs/2606.25658)）用 online semantic basis 估计冗余，维持固定视觉 memory bank；“Causal”指因果流式更新，而非显式因果事件图。
- **One Token per Multimodal Evidence** 证明单个 latent token 可同时服务 reconstruction/retrieval/generation，但也明确暴露了视频结构缺口。
- **Frames2LoRA** 把视频写入 LoRA 参数，query 时零 visual tokens；当前两段 adapter 直接拼 rank 的实验没有显式时间顺序，论文也把精细空间/对象细节与有序组合列为限制。
- **Latent-VC** 把视觉记忆放进 decoder 内部，针对 reasoning 过程中 visual grounding 衰减；但它保留 raw visual prefix，训练最多 16 帧、评估 16/32/64 帧，不能直接视为无限流式记忆。
- **ObjectStream** 从“按 token 重要性”升级为“按 persistent object 组织证据”；但 latent object 发现、关联、淘汰仍是 saliency、connected components、cosine matching 和 lexicographic ranking 的训练外启发式。
- **StreamFlow** 首次较完整地覆盖 encoding 前过滤、long-term latent consolidation、generation-time on-demand injection；因此后续工作若只做“多尺度记忆 + attention 低时注入”已不够新。

## 2. 现在最值得攻的技术空白

### G1. 现有方法优化“信息量/新颖性”，没有优化“相对廉价侧信息的不可替代性”

显著、变化大、容易重构的信息经常已经能由 caption、OCR、ASR、近期关键帧或模型常识回答；真正值得占用昂贵视觉记忆的，是在这些侧信息给定后仍能改变答案的视觉残差。理想目标不是最大化重构整个视频，而是最大化：

\[
I(M;Y\mid Q,S),\qquad S=\{\text{caption, ASR/OCR, keyframes, recent window}\},
\]

并在预算约束下最小化与 \(S\) 的重复信息。当前 SelectStream/StreamFlow/CausalMem/ObjectStream 均未直接优化这个 conditional sufficiency。

### G2. “输入期遗忘”与“生成期失锚”是两个问题，现有工作通常只解决一个

- StreamMem/HERMES/CausalMem/ObjectStream 主要管理 query 前的长期输入。
- Latent-VC/VisMem 主要防止生成过程视觉证据衰减。
- StreamFlow 已开始连接两者，但触发信号主要是 visual attention mass。attention 低不必然代表证据需要重读，attention 高也不保证证据被正确使用。

仍缺少以**反事实答案损失**监督的 memory reactivation，并缺少能在多步推理中反复“提出子问题—再检索”的闭环。

### G3. 视频记忆缺少“结构保真”：时间、对象身份、状态转移、关系和因果

One-Token Latent Memory 已明确指出独立证据 token 会丢视频顺序；Frames2LoRA 也明确承认 chunk composition 无显式 temporal order；ObjectStream 虽有对象轨迹，却没有 learned identity uncertainty、关系图和因果状态转移。最新 [VideoZeroBench](https://arxiv.org/abs/2604.01569) 显示加入时空证据约束后模型几乎全部崩溃，说明“答对”远未等于“保存并使用了正确视觉证据”。

### G4. 参数记忆与 episodic memory 各自存在互补缺陷，尚未被统一

- Frames2LoRA/TTT memory：query 成本低、可吸收长历史，但易把细节平均进参数，更新也可能互相干扰。
- 外部 latent/KV memory：能保留稀有精确证据，但检索、上下文和存储仍有成本。

最自然的下一步是：参数记忆保存高频规律/全局背景，episodic memory 保存低频、精确、尚未被参数吸收的残差；两者之间应存在可验证的 consolidation 和可删除条件。

### G5. 记忆预算大多固定且靠 heuristic，缺少“每 bit 的预期答案价值”

多数工作固定帧率、token 数、GOP 数或 latent 数。稀疏事件视频和拥挤多事件视频不该使用相同码率。应把写入、slot 数、精度、读取次数和注入层都纳入 constrained optimization，报告 accuracy–storage–latency Pareto，而不是只报一个默认点。

### G6. 评估仍容易把“模型没用记忆”误认为“记忆有效”

必须把 retrieval、compression、injection、decoder-use 四种错误拆开，并加入 cross-video replacement、temporal shuffle、matched-random latent、layer swap、删除时间/对象 type embedding 等干预。否则只看 attention 或最终 accuracy，无法证明记忆被因果使用。

## 3. 方案一：CPLM——条件互补的预测视觉残差记忆（首推）

### 3.1 核心假设与动机

在固定预算下，最优视觉记忆不应重建“视频里有什么”，而应保存“caption/ASR/OCR/关键帧/近期窗口无法恢复、但未来问题可能需要什么”。这会直接避免把大量 token 浪费在可由文本或静态关键帧替代的背景语义上。

### 3.2 相对最近工作的创新点

- 相对 SelectStream：从 surprise/访问优先级升级为**conditional counterfactual utility**，记“不可替代证据”而非“变化大的证据”。
- 相对 StreamFlow：不是 RGB residual，而是**相对多模态侧信息的语义视觉残差**；相机抖动大但答案无关时不应高码率。
- 相对 One-Token Latent Memory：加入时间轴、对象/事件 metadata 和 variable-rate slots，直接解决其论文承认的长视频结构缺口。
- 相对 ObjectStream：对象只是组织轴之一，写入价值由未来 QA regret 学习，而不是 saliency + cosine heuristic。

### 3.3 记忆单元

每个事件单元定义为：

\[
m_i=(k_i,z_i,\tau_i,\mathcal O_i,\ell_i,c_i,u_i),
\]

其中 \(k_i\) 是检索 key，\(z_i\in\mathbb R^{n_i\times d}\) 是 variable-rate latent payload，\(\tau_i\) 是时间区间，\(\mathcal O_i\) 是对象/轨迹索引，\(\ell_i\) 是建议注入层，\(c_i\) 是存储成本，\(u_i\) 是预测的未来问题期望效用。

### 3.4 写入、压缩、检索、注入、淘汰

**数据流**：`video chunk → frozen visual encoder + caption/ASR/OCR/keyframe side encoder → conditional residual → variable-rate slot codec → budgeted event archive → query-conditioned time/object retrieval → selected-layer latent/KV injection → answer`。

1. **写入边界**：以视觉预测误差、对象状态变化和音画不一致共同触发事件边界，而不是只用 feature difference。
2. **条件残差**：令 \(h_v(x_i)\) 为视频事件表征，\(S_i\) 为 caption/ASR/OCR/关键帧，训练 side decoder \(D_\psi\)；

   \[
   r_i=h_v(x_i)-D_\psi(h_s(S_i)).
   \]

3. **variable-rate 压缩**：Perceiver/Slot codec 只编码 \(r_i\)，slot 数 \(n_i\) 由预算控制器给出；高 counterfactual utility 的事件获得更多 slots。
4. **query-agnostic 写入、query-aware 读取**：写入时使用 \(\hat u_i\approx\mathbb E_{q\sim p(q|x_{\le i})}[\Delta_i(q)]\)；query 到来后用 semantic key + time/object graph hybrid retrieval 选 top-\(K\)。
5. **层匹配注入**：payload 不是只拼到输入；对视觉信息最可读出的若干 decoder 层做 gated cross-attention 或 K/V prefix，时间、对象、模态 type embedding 独立保留。
6. **淘汰**：以每 byte 的边际反事实价值排序，同时加 coverage 与 redundancy 项；对罕见对象、遮挡边界和短瞬态设保护，不使用纯 LRU/FIFO。

反事实价值的监督标签：

\[
\Delta_i(q)=\mathcal L_{QA}(q,S,M\setminus m_i)-\mathcal L_{QA}(q,S,M).
\]

### 3.5 训练目标

\[
\begin{aligned}
\mathcal L={}&\mathcal L_{QA}
+\lambda_r\|r_i-\hat r_i\|_2^2
+\lambda_d\mathrm{KL}(p_T(y|V,q)\|p_S(y|S,M,q))\\
&+\lambda_u\|\hat u_i-\Delta_i\|_1
+\lambda_{ret}\mathcal L_{NCE}(q,k_i)
+\lambda_{cov}\mathcal L_{coverage}
+\beta[\sum_i c_i-B]_+.
\end{aligned}
\]

Teacher \(p_T\) 看 full video；student 只看侧信息与 memory。训练时的问题可用于学习未来问题分布，但在线写入接口不接收当前测试问题，避免 query leakage。

### 3.6 三阶段训练

- **Stage A：无问答预训练**。条件 masked reconstruction + future latent prediction，先学“什么能被侧信息预测、什么不能”。
- **Stage B：full-context teacher distillation**。用带 evidence span 的 QA 学 codec、retriever、layer interface 和 counterfactual utility predictor。
- **Stage C：预算课程/约束 RL**。从 2048→1024→512 latent-token 预算逐步压缩，用 QA reward、grounding reward、bytes/latency penalty 联合优化。

### 3.7 推理复杂度与建议预算

- ingest：每帧/事件仍需一次视觉编码，时间约 \(O(TC_v)\)，但不会把历史全部留在 GPU；codec 与 memory 更新按事件在线执行。
- active memory 固定为 \(B\) 个 latent tokens，GPU 空间 \(O(Bd)\)；query 检索用 CPU/ANN 时约 \(O(\log N+Kd)\)。
- decoder 每层额外开销约 \(O(Kd)\)，只在选定层注入。
- 首个可发表原型建议：长期库 512/1024/2048 tokens 三档；每次读取 32/64/128 tokens；近期原始窗口 4–16 帧。

### 3.8 Benchmarks、baselines 与关键 ablation

- **核心 benchmark**：VideoZeroBench（时空 evidence）、Video-MME-v2（分组一致性与多步推理）、Video-MME Long、MLVU、LVBench、LongVideoBench、StreamingBench、OVO-Bench。
- **baselines**：同 backbone/full video、recent-window、uniform/keyframe；StreamMem、HERMES、CausalMem、FluxMem、ObjectStream、SelectStream、StreamFlow；One-Token Latent Memory 的时间扩展版。
- **关键 ablation**：去掉侧信息条件；直接重构 \(h_v\)；surprise 代替 utility；fixed slots；无对象/时间 metadata；输入拼接 vs layer-wise injection；utility per byte vs LRU/FIFO；oracle evidence span/raw clip 上界。

### 3.9 失败模式

- side decoder 太强时把重要细节误判为“可预测”，造成 residual collapse；太弱则退化为普通视频压缩。
- 训练问题分布偏置会让 query-agnostic utility predictor 丢掉测试域证据。
- caption/ASR 错误可能让模型错误地把视觉真相当作重复信息；需保留 disagreement channel。
- variable-rate controller 可能把预算集中到高运动片段，必须用反事实效用与 coverage 约束纠偏。

### 3.10 可证伪预测与 kill criteria

- **预测 P1**：在同 backbone、同 512/1024 latent-token 预算下，conditional residual 应同时优于“直接压缩视觉特征”和 SelectStream/StreamFlow 的 accuracy–storage Pareto，并提高 VideoZeroBench 的 evidence Recall/grounded accuracy；否则“不可替代信息”并非更好的写入目标。
- **预测 P2**：将检索到的 residual 替换为同时间长度的另一视频 residual，答案与 grounding 应显著下降；若下降不超过 matched-random latent，说明 decoder 没有实际使用 memory。
- **Kill**：三随机种子下，相对最强 matched-budget baseline 的平均 QA 增益低于 1.5 pp，且 grounding、bytes、latency 三项均无 Pareto 改善；或 oracle residual 相对普通 codec 的上界增益低于 2 pp。前者停止完整系统扩展，后者直接否定中心假设，转向普通 learned codec。

## 4. 方案二：Causal-Reactivation Grounding Loop——外部情景记忆 + 解码器工作记忆闭环

### 4.1 核心假设与动机

长视频系统存在两次遗忘：历史进入 query 前被压缩掉；正确证据进入 context 后，又在长推理中被语言 token 淹没。二者必须以两个时间尺度的 memory 协同解决，而且“何时重读”应由证据的**因果贡献**决定，而不是只看视觉 attention 大小。

### 4.2 相对最近工作的创新点

- 相对 Latent-VC：增加可扩展、带 provenance 的外部 long-term memory；Latent-VC 的 8-step recurrent cache 可作为 working memory，但不再要求全部 raw video prefix 常驻。
- 相对 StreamFlow：把 VAS threshold 换成由 counterfactual intervention 训练的 **need-to-read trigger**；允许解码中多轮提出 latent subquery、重新检索、更新 cache。
- 相对 OASIS：不只用语言 uncertainty/high-level intent，还显式预测“如果不读证据，答案损失会增加多少”。

### 4.3 记忆单元

- 外部情景单元：\(e_i=(k_i,p_i,\tau_i,b_i,prov_i)\)，其中 \(p_i\) 是 4–16 个 latent evidence slots，\(prov_i\) 保留原帧索引/box/音频区间。
- 解码器工作记忆：\(C_s\in\mathbb R^{S\times d}\)，在生成步 \(s\) 循环更新；容量固定 8–32 slots。

### 4.4 完整机制

**数据流**：`stream → event codec → provenance-preserving external archive；question → initial retrieval → decoder working cache → causal trigger/latent subquery → optional re-retrieval → recurrent cache update + layer injection → answer`。

1. **写入/压缩**：流式事件 codec 建 external archive；先按事件边界压缩，并保留 evidence provenance。
2. **首次检索**：由原问题取 top-\(K\) 情景单元，初始化 working cache。
3. **因果触发**：每隔 \(g\) 个生成 token，trigger 读取当前 hidden state、cache confidence、答案熵和证据覆盖，预测是否值得再次读取：

   \[
   a_s=\sigma f_\omega(h_s,C_s,H_s,coverage_s).
   \]

4. **latent subquery**：若触发，从当前推理状态生成连续 query vector，而非必须生成可见文字；检索新 evidence。
5. **cache 更新与注入**：

   \[
   C_{s+1}=\mathrm{GRU}_{slot}\big(C_s,\mathrm{CrossAttn}(C_s,[p_i]_{i\in R_s})\big),
   \]

   并在若干 decoder 层以 gated K/V 注入；答案 token 仍保持普通自回归。
6. **淘汰**：external archive 按 evidence utility/coverage 淘汰；working cache 按过去若干步的 causal attribution 及任务阶段淘汰，不能单纯 LRU。

trigger 的监督来自 oracle intervention：

\[
d_s=\mathbb 1[\mathcal L(y|\text{no-read at }s)-\mathcal L(y|\text{oracle-read at }s)>\delta].
\]

### 4.5 训练目标

\[
\mathcal L=\mathcal L_{QA}+\lambda_t\mathrm{BCE}(a_s,d_s)
+\lambda_e(1-\mathrm{IoU}_{time/space})
+\lambda_c\mathcal L_{cache-align}
+\lambda_r\mathcal L_{retrieval}
+\beta\,\mathbb E[\#reads+\alpha\#slots].
\]

最终 rollout 可用 GRPO/PPO，reward 为 answer correctness + evidence grounding − retrieval latency − injected tokens。

### 4.6 三阶段训练

- **Stage A**：冻结 backbone，训练 event codec/retriever，使用 temporal/box evidence annotation。
- **Stage B**：oracle evidence teacher-forcing；通过逐步删除/替换 evidence 生成 trigger label，训练 working cache 与层注入。
- **Stage C**：自由生成 rollout；约束 RL 学 read timing、subquery、停止读取与最终答案。

### 4.7 复杂度/预算

- archive 可在 CPU/SSD，ANN 检索 \(O(\log N)\)；GPU 仅保留 recent window、working cache 和当前 top-\(K\)。
- 每题最多 \(R\) 次重读，每次 \(K\) 个 slots，总额外 decoder 复杂度约 \(O(RLKd)\)，通过 \(R\le4\)、\(K\le32\) 做硬上限。
- 对比时必须把 archive 写入成本、ANN latency、GPU/CPU/SSD bytes 全部计入，而不是只报 TPOT。

### 4.8 Benchmarks、baselines、ablation

- **核心**：VideoZeroBench Level-3/4/5、Video-MME-v2、StreamingBench、OVO-Bench Backward Tracing、Video-MME Long、VSI-Bench。
- **baselines**：Latent-VC、VisMem、StreamFlow、OASIS、SelectStream、ReKV、HERMES、recent-window；另设 oracle trigger/oracle evidence。
- **关键 ablation**：VAS vs entropy vs causal trigger；一次性 prefix vs recurrent cache；可见 textual subquery vs latent subquery；1/2/4/8 次 read；无 provenance；不在多层注入；固定 read schedule。

### 4.9 失败模式

- trigger false negative 会让系统“一路自信地错”；需低成本 safety read 与 calibration。
- 生成状态形成的 subquery 可能继承幻觉，造成检索闭环自证；应混入原问题和已验证 evidence key。
- 多次检索带来尾延迟和非确定性，实时场景需硬 deadline。
- intervention label 计算昂贵，可先用小 teacher/offline cache 生成。

### 4.10 可证伪预测与 kill criteria

- **预测 P1**：在相同总读取 token 下，causal trigger 应优于固定 schedule、entropy 和 VAS trigger；在相同 accuracy 下，应减少至少 30% 的 read 次数。
- **预测 P2**：优势应集中在长 CoT/多阶段问题，并随生成步数增长；若短答和长推理收益相同，所谓“生成期失锚”机制未被验证。
- **Kill**：oracle-trigger + oracle-evidence 相对一次性最佳检索的 grounded accuracy 上界小于 2 pp，说明 reactivation 不是主要瓶颈；或 learned trigger 在 accuracy 损失不超过 0.5 pp 时无法减少 30% reads、同读取预算下又不能提升 1.5 pp，则采用更简单的一次检索/StreamFlow 路线。

## 5. 方案三：Order-Aware Adapter Atlas——有序参数记忆 + 稀疏视觉残差

### 5.1 核心假设与动机

当同一个超长视频会被多轮、反复提问时，每次重新喂 visual tokens 是浪费；Frames2LoRA 证明“video → adapter”可行，但固定 rank 倾向保存高层语义，两段 rank concat 又不表示时间顺序。因此最有潜力的是：用参数记忆保存可复用的全局/段落语义，用少量 episodic latent 保存 adapter 无法表达的精细视觉残差，并显式建模有序组合。

### 5.2 相对最近工作的创新点

- 相对 Frames2LoRA：从单 adapter/两段 rank concat 升级为**可检索的 segment adapter atlas、非交换的顺序组合、动态 rank、残差 token 兜底**。
- 相对 SelectStream/StreamFlow：大部分历史在 query 时不占 context；只有被预测为参数记忆不足的细节才注入 token。
- 相对 TTT memory：adapter 是离线/在线一次生成的可索引片段，不必让所有历史持续覆盖同一 fast weights。

### 5.3 记忆单元

\[
m_j=(k_j,A_j,B_j,z_j^{res},\tau_j,r_j,u_j),\qquad \Delta W_j=B_jA_j.
\]

\(A_j,B_j\) 为 segment-specific LoRA，\(z_j^{res}\) 为细节残差 slots，\(\tau_j\) 为时序，\(r_j\) 为动态 rank。

### 5.4 写入/压缩/检索/注入/淘汰

**数据流**：`video segment → frozen VLM hidden states → hypernetwork → segment LoRA + teacher-regret residual → compressed adapter atlas；question → ordered adapter retrieval/composition → confidence gate → optional residual-token retrieval → answer`。

1. **写入**：每个事件段经过 layer-wise VLM hidden states，由 hypernetwork 一次生成 adapter；full-context teacher 与 adapter-only student 的差异再压成 \(z_j^{res}\)。
2. **adapter 字典压缩**：跨 segments 共享低秩 basis：

   \[
   \Delta W_j\approx\sum_{b=1}^{R_b}\alpha_{jb}U_bV_b^\top+E_j,
   \]

   只存系数和小 residual factor，避免每段都保存完整 LoRA。
3. **检索**：query 先检索 \(K_a\) 个 adapters；time-aware router 用 SSM/Transformer 编码其原始顺序和间隔。
4. **非交换组合**：按时间顺序串联 gated adapter，而不是直接求和/拼 rank：

   \[
   h^{j+1}=h^j+g_j(q,\tau_j)B_jA_jh^j,\quad j\in\mathrm{sort}(R_q,\tau).
   \]

   因为每一步作用在上一步结果上，顺序交换会改变输出。
5. **残差注入**：router 预测 adapter confidence；低 confidence 或需 spatial/counting/OCR 时再检索 \(z^{res}\) 以 latent tokens 注入。
6. **淘汰**：先合并相邻且 teacher-regret 小的 adapters；按“被字典解释度 + 查询效用 + 残差不可替代度”淘汰。原始片段删除前要求通过 replay QA 校验。

### 5.5 训练目标

\[
\begin{aligned}
\mathcal L={}&\mathcal L_{QA}
+\lambda_d\mathrm{KL}(p_T(y|V,q)\|p_A(y|q,\Delta W_{R_q},z^{res}))\\
&+\lambda_o\mathcal L_{order}
+\lambda_{comp}\|\Delta W_j-\hat{\Delta W}_j\|_F^2
+\lambda_{orth}\sum_{b\ne b'}|\langle U_b,U_{b'}\rangle|\\
&+\lambda_{res}\mathcal L_{detail}(z^{res})
+\beta(\text{rank-bytes}+\text{latent-bytes}-B)_+.
\end{aligned}
\]

\(\mathcal L_{order}\) 用正确顺序与随机 permutation 的对比 margin；\(\mathcal L_{detail}\) 专门覆盖 object attributes、count、OCR、spatial relation、短瞬态。

### 5.6 三阶段训练

- **Stage A：segment internalization**。复现 Frames2LoRA 基线并加入 mixed caption/QA、动态 rank 与 residual distillation。
- **Stage B：长视频有序组合**。2→4→8→32 segments curriculum；加入跨段 temporal/multi-hop QA 与 permutation negatives。
- **Stage C：多轮查询摊销优化**。同一视频 5–20 个问题，联合优化首问总延迟、后续 TTFT、adapter/latent bytes 与答案质量。

### 5.7 复杂度/预算

- 视频 internalization 一次性 \(O(TC_v)\)，可离线或流式逐段完成。
- 每题检索 \(O(\log N)\)，adapter 额外计算约 \(O(K_aLrd)\)，不随原视频 token 数增长；只在低 confidence 时付 \(K_z\) latent token 代价。
- 第一版建议每段 rank 4–16、检索 2–8 段、全视频 adapter archive 16/64/256 MB 三档；必须报告首问含 internalization 与第 2–20 问的摊销曲线。

### 5.8 Benchmarks、baselines、ablation

- **核心**：HourVideo、Video-MME/Video-MME-v2、LVBench、LongVideoBench、MLVU、ELViM；增加“同一视频 10 问”的 repeated-query protocol 与 temporal permutation test。
- **baselines**：Frames2LoRA v2、full visual context、KV reuse、ReKV、StreamMem、HERMES、CausalMem、SelectStream、StreamFlow。
- **关键 ablation**：rank concat vs sum vs ordered serial composition；无 residual tokens；fixed/dynamic rank；无字典共享；caption-only vs caption+QA；随机顺序；单段/多段；不同 backbone scale。

### 5.9 失败模式

- 多 adapter 串联可能产生干扰或数值放大；需 gate norm、orthogonality 与最多激活段数。
- 精确计数、相机运动、空间细节可能仍压不进低秩参数；residual 通道必须是结构的一部分而非补丁。
- hypernetwork 与目标 backbone/scale 强绑定，跨模型迁移困难。
- 参数化视频有隐私与删除问题；需 segment-level 可撤销 adapter，不应不可分地写进共享 backbone。

### 5.10 可证伪预测与 kill criteria

- **预测 P1**：在 order-sensitive 子集上，正确时序组合应比随机 permutation 至少高 3 pp；若顺序交换不影响答案，则 adapter 没有编码可用的时间过程。
- **预测 P2**：相对 Frames2LoRA v2，adapter atlas 应在多段视频上提高质量，并在同一视频重复提问时出现明确 break-even：累计成本应在第 5 个问题前低于反复 visual-token/KV baseline。
- **Kill**：adapter + residual 在相同总 bytes 下仍不能超过 Frames2LoRA v2 1.5 pp，或达到 full-context 95% 质量所需的 break-even 超过 10 个问题；若 oracle residual 仍无法挽回 object/OCR/spatial 细节，则停止参数记忆主线而保留检索式 latent memory。

## 6. 方案四：WorldGraph-Δ——不确定性感知的对象状态与事件增量记忆

### 6.1 核心假设与动机

很多长视频问题不是问“出现过什么”，而是问“同一对象后来怎么变、谁对谁做了什么、哪个事件导致结果”。保存 patch/token 相似度无法稳定表达 identity、occlusion、state transition 和 relation。ObjectStream 已证明对象锚点的价值，但其对象发现/匹配/淘汰仍是训练外启发式；下一步应把视频压成带不确定性的 learned world state 和稀疏 event deltas。

### 6.2 相对最近工作的创新点

- 相对 ObjectStream：从 latent object track 升级为**状态分布 + 关系 + pre/post condition + association uncertainty**；用 learned utility 与 causal QA 训练写入。
- 相对 SelectStream event graph：节点不是整段通用 latent，而是可持续更新的 entity state 与 event delta，可做路径级多跳检索。
- 相对 One-Token memory：结构轴不是 metadata 附加项，而是核心可计算图。

### 6.3 记忆单元

对象状态：

\[
o_{i,t}=(id_i,a_{i,t},x_{i,t},\Sigma_{i,t},s_{i,t},\tau_t),
\]

其中 \(a\) 是 appearance，\(x\) 是位置/姿态，\(\Sigma\) 表示身份与状态不确定性，\(s\) 是属性/可见状态。

事件增量：

\[
e_j=(actors_j,predicate_j,pre_j,post_j,\Delta z_j,\tau_j,cause_j,prov_j).
\]

### 6.4 完整机制

**数据流**：`frames → detector-free object slots → uncertainty-aware soft association → persistent entity states + sparse event deltas → typed temporal/relational graph；question → neural program → entity/path retrieval → graph tokens + raw latent anchors → answer`。

1. **对象发现**：用 detector-free slot attention 从 backbone patch tokens 产生 8–32 个 object slots；可用 SAM2/DINO/grounded boxes 只作训练 teacher，不在部署时依赖。
2. **关联**：Hungarian/optimal transport cost 联合 appearance、运动预测、空间 overlap、语义属性；保留 soft assignment 与 identity uncertainty，而不是一次 cosine hard match。
3. **写入**：稳定状态只更新 latest state；当 Bayesian surprise、interaction change、appearance/disappearance 或 uncertainty spike 发生时写 event delta，并保留一小组 raw latent anchors。
4. **压缩**：轨迹用 spline/quantized motion state；属性只存 delta；长期稳定段合并为 `(state, duration)`；关系边只在变化时写。
5. **检索**：将问题解析为 neural program（entity / before-after / count / cause / interaction），先检索实体，再沿 temporal/relational edges 做 constrained beam search。
6. **注入**：graph tokens 提供结构与时间，命中的 \(\Delta z\) 提供视觉 payload；两者在 layer-wise cross-attention 中分开 type embedding。
7. **淘汰**：submodular coverage 保留每个 entity 的 last confirmed state、每类 relation 的关键变化与高 uncertainty 边界；只有可由相邻状态插值恢复的 delta 才可合并。

### 6.5 训练目标

\[
\mathcal L=\lambda_a\mathcal L_{assoc}
+\lambda_p\mathcal L_{future-state}
+\lambda_e\mathcal L_{event}
+\lambda_g\mathcal L_{time/box}
+\mathcal L_{QA}
+\lambda_{cf}\mathcal L_{counterfactual}
+\beta\mathcal L_{budget}.
\]

- \(\mathcal L_{assoc}\)：跨增强/遮挡的 cycle consistency + teacher track distillation。
- \(\mathcal L_{future-state}\)：masked trajectory/state prediction。
- \(\mathcal L_{counterfactual}\)：交换 event edge、pre/post 或对象身份后，答案和因果判断必须相应变化。

### 6.6 三阶段训练

- **Stage A：对象/轨迹自监督**。短视频和 Ego4D/TAO 类轨迹数据；遮挡、camera cut、viewpoint augmentation。
- **Stage B：事件图与 causal/temporal QA**。CLEVRER、STAR、NExT-QA、程序性视频与 temporal grounding 数据。
- **Stage C：长视频预算训练**。VideoZeroBench/Video-MME-v2/streaming data；用 oracle tracks→learned tracks curriculum，最后加 budget RL。

### 6.7 复杂度/预算

- 每帧 \(S\) 个 slots、\(M\) 个 active tracks 时，朴素关联 \(O(SM)\)，可用 coarse ANN/空间门控降到稀疏匹配。
- 内存约 \(O(Md+E d_e)\)，通过每实体保留 \(K_s\) 状态、全局最多 \(B_e\) events 固定上限。
- query read 为 top-\(K\) graph path，通常远小于全历史 token；但 object discovery 本身会增加 ingest 开销，必须单独报告 FPS。

### 6.8 Benchmarks、baselines、ablation

- **核心**：VideoZeroBench Level-5、Video-MME-v2、OVO-Bench Backward Tracing/Real-Time Perception、Perception Test、CLEVRER、STAR、EgoSchema、LVBench。
- **baselines**：ObjectStream（最关键）、SelectStream、StreamFlow、CausalMem、StreamForest、MA-LMM、raw/full-context；另报 oracle track/SAM2 上界。
- **关键 ablation**：hard cosine vs soft association；无 uncertainty；snapshot vs delta；无 relation edges；无 causal loss；无 raw anchors；graph retrieval vs flat top-k；oracle vs learned objects。

### 6.9 失败模式

- 拥挤、相似外观、长遮挡、镜头切换会 identity swap；不确定性必须传递到回答置信度。
- 小而低对比、但问题关键的对象可能根本未形成 slot；需全局 residual safety channel。
- 音频/OCR 才能确定的事件不能只靠对象图；world graph 应允许非视觉节点。
- 显式结构可能过度约束开放世界视频；保留 latent payload 以覆盖无法符号化的内容。

### 6.10 可证伪预测与 kill criteria

- **预测 P1**：收益必须集中在 object persistence、before/after、interaction 与 cause 子集，并且 temporal shuffle、identity swap、pre/post swap 会造成方向一致的性能下降；否则 graph 只是额外 token 容器。
- **预测 P2**：oracle tracks/relations 相对 ObjectStream 应在 grounded/object-state 子集至少提升 3 pp，从而证明“结构表达”确实是瓶颈；learned graph 再逐步逼近该上界。
- **Kill**：oracle graph 相对 flat latent memory/ObjectStream 的增益小于 2 pp，直接否定结构化主张；或 learned association 的 identity switch 使其在三个长视频 benchmark 上持续劣于 flat memory，即使使用 oracle retrieval 仍不能恢复，则暂停端到端 learned graph，退回 object anchor + residual 的轻量路线。

## 7. 方案五：Hippocampal-TTT——fast-weight 语义记忆 + 可回放情景残差

### 7.1 核心假设与动机

连续数小时的视频同时包含两类信息：高频规律/背景适合被 TTT 或 adapter 吸收进参数；只出现一次的精确事实必须保存在 episodic memory。单一 fast-weight 容易干扰，单一外部 token memory 又不够省。类 hippocampus–neocortex 的双系统应能在固定预算下兼顾泛化与精确回忆。

### 7.2 相对最近工作的创新点

- 相对 video-SALMONN S：增加受保护的稀疏 episodic capsules、replay consolidation、显式 interference detector 和“何时可安全删除 episode”的判据。
- 相对 Frames2LoRA：fast weights 可在线更新；episodic 通道保存不能被低秩参数表达的细节。
- 相对 SelectStream/One-Token memory：不是所有事件永久占外存；被 fast weights 稳定吸收后可释放，只保留难例与稀有证据。

### 7.3 记忆单元

- 参数长期记忆：选定层的低秩 fast weights \(W_t^{fast}=U_tV_t^\top\)。
- 情景 capsule：\(m_i=(k_i,z_i,\tau_i,u_i,g_i,prov_i)\)，其中 \(g_i\) 是写入时的梯度/干扰摘要。
- consolidation ledger：记录某 episode 是否已被参数记忆在多种 query 下稳定复现。

### 7.4 写入/压缩/检索/注入/淘汰

**数据流**：`stream chunk → long-span prediction/gradient conflict test → low-rank fast-weight update and/or episodic capsule write → periodic protected replay/consolidation；question → fast-weight read → confidence/key gate → optional episode retrieval/injection → answer`。

1. **fast-weight 更新**：对每个 chunk 做长跨度预测/重建：

   \[
   W_t=W_{t-1}-\eta_t\nabla_W\mathcal L_{pred}(x_t,x_{t-\Delta};W_{t-1}).
   \]

2. **episodic 写入门**：预测误差高、QA utility 高或新梯度与历史梯度冲突时写 capsule：

   \[
   s_t=\mathcal L_{pred,t}+\lambda\max(0,-g_t^\top\bar g_{old})+\mu\hat u_t.
   \]

3. **压缩**：fast weights 固定低秩；episode 用 variable-rate latent codec。camera cut 噪声只有 prediction surprise、但无 utility 时不应长期保存。
4. **读取/注入**：fast weights 始终参与 selected layers；若模型 confidence 低或 query 与 capsule key 高匹配，再取 top-\(K\) episodic latents 做 cross-attention。
5. **周期 replay/consolidation**：每 \(C\) 个 chunks 从 protected reservoir 重放，更新 fast weights，使旧 episode 与新知识兼容。
6. **淘汰**：只有当 `fast-weight only` 在该 episode 的 reconstruction、evidence retrieval 和多 query QA 上均低于 regret 阈值，才删除 capsule；否则使用 influence-aware reservoir，不用 FIFO。

### 7.5 训练目标

\[
\begin{aligned}
\mathcal L={}&\mathcal L_{pred}^{long}+\mathcal L_{QA}
+\lambda_{ret}\mathcal L_{NCE}
+\lambda_{rep}\mathrm{KL}(p_{before}(y|m_i)\|p_{after}(y|m_i))\\
&+\lambda_{int}\sum_{i,j}\max(0,-g_i^\top g_j)
+\lambda_{rec}\mathcal L_{episode-rec}
+\beta(\mathrm{rankbytes}+\mathrm{episodebytes}-B)_+.
\end{aligned}
\]

### 7.6 三阶段训练

- **Stage A：TTT cold start**。中等长度视频，长跨度预测 + stable low-rank update。
- **Stage B：双系统 meta-training**。构造交错主题、稀有 needle、延迟数千帧后提问的流，训练 write gate、retriever、replay 和 delete criterion。
- **Stage C：真实超长流 budget RL**。ELViM、Video-MME Long、StreamingBench；reward 同时考虑 retained accuracy、forgetting、update FLOPs、bytes 与 TTFT。

### 7.7 复杂度/预算

- fast weights 固定 rank \(r\)，每 chunk 更新约 \(O(rd)\) 到 \(O(Lrd)\)（依注入层数）；episode archive 固定 \(B_e\) slots。
- query 正常只付 adapter/fast-weight 开销；触发 episodic read 时增加 \(O(Kd)\)。
- replay 每 \(C\) chunks 执行并设 FLOP 上限，报告平均和 p95 ingest latency，避免平均值掩盖周期尖峰。

### 7.8 Benchmarks、baselines、ablation

- **核心**：ELViM、Video-MME Long、HourVideo、StreamingBench、OVO-Bench、LVBench；另建 `rare visual needle after 1/2/3 hours` 与主题切换/回切 stress test。
- **baselines**：video-SALMONN S、Frames2LoRA、StreamMem、HERMES、CausalMem、SelectStream、ObjectStream、StreamFlow、纯 recent-window。
- **关键 ablation**：无 episodic；无 TTT；无 replay；FIFO vs influence reservoir；full-rank vs low-rank；只 surprise vs surprise+interference+utility；不同 replay interval；安全删除判据。

### 7.9 失败模式

- fast-weight drift 或恶意/异常片段会污染长期参数；需 update norm、rollback checkpoint、anomaly gate。
- replay 样本选择偏差会反复强化旧错误；需要 provenance 与 teacher revalidation。
- update/replay 可能破坏严格实时性；必须有硬 compute budget。
- “从参数中删除某段视频”困难，因此 privacy-sensitive episode 应优先保留可撤销外部 capsule，限制 consolidation。

### 7.10 可证伪预测与 kill criteria

- **预测 P1**：双系统应呈功能分工：高频规律主要由 fast weights 回答，rare needle 主要依赖 episode；分别替换两类 memory 时应出现选择性损伤，而非两条通路等价。
- **预测 P2**：在 1/2/3 小时流后，双系统应比 TTT-only 至少提高 10 pp rare-needle retention，且比 episodic-only 节省至少 30% archive bytes，形成质量–存储 Pareto 改善。
- **Kill**：在严格相同 update FLOPs、bytes 和 backbone 下，双系统对 TTT-only 与 episodic-only 都无 Pareto 优势；或 replay 后遗忘率未降低且 p95 ingest latency 超过目标实时帧间隔 2 倍。此时停止在线参数更新，保留可撤销 episodic memory。

## 8. 五个方案的优先级

### 8.1 面向 6–12 个月论文产出的综合优先级

| 排名 | 方案 | 动机强度 | 相对 2026-08 最近工作的区分度 | 实现风险 | 推荐判断 |
|---:|---|---:|---:|---:|---|
| 1 | CPLM 条件互补残差记忆 | 5/5 | 5/5 | 中 | 最清晰的中心论点；可从现有 frozen VLM + Perceiver + retriever 做 MVP，且能正面回答“为什么记这些而不是另一些” |
| 2 | Causal-Reactivation Grounding Loop | 5/5 | 3.5/5 | 中 | VideoZeroBench/Visual Anchoring Decay 给出强实证动机；但必须用 causal trigger 与闭环 read 和 StreamFlow 拉开差异 |
| 3 | Order-Aware Adapter Atlas | 4.5/5 | 5/5 | 中高 | 新颖、对 repeated-query 场景价值大；风险在 adapter 干扰、模型绑定和细节损失 |
| 4 | WorldGraph-Δ | 5/5 | 4/5 | 高 | 最能攻 evidence-grounded 时空推理；但 object identity/关系监督和工程量都大，适合作为长线主项目 |
| 5 | Hippocampal-TTT | 4.5/5 | 4.5/5 | 很高 | 高风险高回报；需要稳定 online update、replay 与严格系统测量，宜在前四个积累 codec/evaluation 后推进 |

### 8.2 高风险高回报排序

若目标更偏架构创新而非短周期：`Adapter Atlas > Hippocampal-TTT > CPLM > WorldGraph-Δ > Grounding Loop`。

### 8.3 最推荐的组合路线

第一篇以 **CPLM** 为主，只做单次 query 与 fixed-budget memory，建立“conditional visual residual”论点；第二篇加入 **Causal-Reactivation**，把 query 前 memory 与生成期 cache 连起来；第三阶段再选择 **Adapter Atlas** 或 **WorldGraph-Δ** 作为结构升级。不要第一篇就把五个方案全部堆进一个模型，否则创新贡献与消融因果链都会变得模糊。

## 9. 所有方案共用的严谨评估协议

### 9.1 四格误差分解

| 时间定位 | payload | 用途 |
|---|---|---|
| oracle segment | raw clip | full evidence 上界 |
| learned retrieval | raw clip | 单测 retrieval |
| oracle segment | latent memory | 单测 compression/injection |
| learned retrieval | latent memory | 完整系统 |

再加 `oracle segment + latent + oracle injection layer`，判断瓶颈是否在 decoder use。

### 9.2 必做的因果使用测试

- cross-video memory replacement；
- retrieved units 时间顺序打乱；
- 删除最相关/随机/同大小 memory；
- matched-random latent tokens；
- 同视频跨层 payload swap；
- 移除 time/object/modality type embeddings；
- 用同义问题改写检验 retrieval 稳定性。

若这些干预对答案几乎无影响，就不能声称模型在使用视觉记忆。

### 9.3 同时报告质量与成本

- QA accuracy/F1、group consistency；
- evidence Recall@K、temporal IoU、spatial IoU、VideoZeroBench Level-3/4/5；
- memory bytes（GPU/CPU/SSD 分开）、active tokens/KV、写入吞吐；
- end-to-end ingest latency、TTFT、TPOT、每题总时延、p95；
- 首问含构建成本和第 2–20 问摊销成本；
- accuracy–storage–latency Pareto，而不是单预算点。

### 9.4 统计与公平性

- 固定 backbone、FPS、resolution、可见视频前缀、问题到达时间、生成长度和硬件；
- Video-MME 等同一视频多问题不是独立样本，置信区间要按 video-level cluster bootstrap；
- 对 paired correct/wrong transitions 做 McNemar，至少 3 个 seeds；
- streaming 方法不能在写入时看到未来帧或未来 query；query-aware 与 query-agnostic 必须分榜。

## 10. 一句话结论

2026 年的竞争前沿已经不是“有没有 memory”，而是：**在写入时未知未来问题、预算固定、生成会失锚的条件下，能否保存相对廉价侧信息真正不可替代的时空视觉证据，并在正确推理步骤以可验证的方式重新激活它。** CPLM 是最适合作为第一篇工作的核心命题；其余四个方案分别把这一命题延展到解码闭环、参数内化、对象世界模型和双系统长期学习。
