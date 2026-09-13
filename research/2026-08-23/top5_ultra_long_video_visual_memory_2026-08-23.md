# 超长视频视觉记忆：经近期文献核验后的五个优先研究方向

> 调研截止：2026-08-23
> 目标：在三份既有调研的基础上，重新核验最近邻工作，筛出五个仍有清晰论文空间的方向。
> 证据口径：正式会议论文与作者公开的 arXiv/OpenReview 一手材料分开看待；2026 年 8 月的新预印本尚缺独立复现，文中性能数字只代表原作者报告。

## 0. 结论先行

最值得优先投入的五个方向是：

| 排名 | 方案 | 一句话中心命题 | 来源方案 | 综合分 | 建议定位 |
|---:|---|---|---|---:|---|
| 1 | **FQR-Mem：未来查询鲁棒的条件互补记忆** | 不保存“普遍显著”的视觉内容，而保存相对 caption/ASR/OCR/近期窗口不可替代、且对未来尾部问题仍有用的视觉证据 | CPLM + DRO-FutureMem | **92/100** | 首篇主线；ICLR/CVPR 均合适 |
| 2 | **RTC-Mem：回溯式时间信用记忆** | 后续事件应通过反事实预测贡献，给早期不起眼但后来证明关键的事件补发保留信用 | RTC-Mem | **87/100** | 问题最有辨识度；先小规模证伪 |
| 3 | **EvictCert-Mem：可校准的淘汰证书记忆** | 问题到来后，应能判断答案是否依赖已经被淘汰的证据，并定位、回取或拒答 | EVC-Mem 的收窄版 | **86/100** | 最快闭环；偏 CVPR，形式化后也适合 ICLR |
| 4 | **SR-EventKV：逐级细化的事件 KV 编码器** | 所有事件保留可发现的极低码率基础层，查询到来后只为相关事件购买更多比特，并控制 attention 输出误差 | SR-EventKV + LateBind-Video | **84/100** | ICLR 方法/理论或 CVPR 系统论文 |
| 5 | **SSCM：语义惊奇驱动的多时间尺度连续谱记忆** | 参数记忆不应按固定频率或像素变化更新，而应按跨模态语义惊奇路由到不同更新时钟并逐级晋升 | SSCM + Hippocampal-TTT | **81/100** | 高风险旗舰方向；不建议作为第一个大实现 |

**首篇建议选 FQR-Mem。** 它最直接回答视觉记忆的核心科学问题：“在写入时不知道未来问题的条件下，为什么应该记住这一条视觉证据，而不是另一条？”它也能把三份报告中最强的两个想法——条件互补价值与尾部问题鲁棒性——合并成一个单一、可证伪的论文命题。

**EvictCert-Mem 必须重写新颖性主张。** [REVEAL](https://arxiv.org/abs/2608.08612) 已于 2026-08-09 直接研究长视频 QA 的显式证据充分性、缺失线索定位和定向再检索；[MemVAU](https://openreview.net/forum?id=shStSIP0aE) 又进一步验证逐维证据并保护互补条目。因此不能再把“首次验证证据是否充分”作为贡献；可辩护的新点应锁定在：**压缩发生时生成 eviction witness，查询未知，随后区分淘汰/检索/推理/无答案四类失败，并校准 missed-evidence 假阴性风险。**

这五项都只有在下文的关键假设被实验支持时，才足以形成 ICLR/CVPR 级论文；动机强不等于结果必然可发表。

下文按“主线 → 快速可靠性诊断 → 高新颖性机制 → 表示与架构”的验证依赖展开，因此 EvictCert-Mem 的章节先于优先级更高但需先建诊断集的 RTC-Mem。

---

## 1. 如何从原有方案中筛选

### 1.1 标记约定

- **[事实]**：可由所引一手论文或数据直接支持。
- **[判断]**：基于文献竞争、实现风险与论文完整度的研究决策。
- **[假设]**：必须通过实验验证，不作为既有结论陈述。

### 1.2 评分标准

评分是研究决策判断，不是客观测量：

| 维度 | 权重 | 判断问题 |
|---|---:|---|
| 截至当前的新颖性 | 30% | 最近邻是否已完成相同问题定义与核心机制？ |
| 中心命题与可证伪性 | 25% | 能否用一句话说明，并用关键实验推翻？ |
| 科学意义与影响上限 | 20% | 是否触及记忆的写入、遗忘、召回或更新原理，而非只加模块？ |
| 约六个月内的可行性 | 15% | 是否可从冻结 3B/7B VideoLLM 和小模块做出可信结果？ |
| 证据与评测成熟度 | 10% | 是否已有可用 benchmark、grounding 标注和强基线？ |

| 候选聚类 | 新颖性 | 可证伪性 | 意义 | 可行性 | 评测 | 加权分 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---|
| FQR-Mem | 4.5 | 4.8 | 4.8 | 4.1 | 4.6 | 92 | 选入 |
| RTC-Mem | 4.5 | 4.6 | 4.5 | 3.5 | 4.2 | 87 | 选入 |
| EvictCert-Mem | 3.2 | 4.9 | 4.9 | 4.5 | 4.8 | 86 | 选入，但须避开 REVEAL/MemVAU |
| SR-EventKV | 3.8 | 4.8 | 4.7 | 3.2 | 4.5 | 84 | 选入 |
| SSCM | 4.0 | 4.3 | 5.0 | 2.5 | 4.2 | 81 | 选入，高风险 |
| ME-TimeKV（TM-KV + ChronoCache） | 3.0 | 4.8 | 4.1 | 4.2 | 4.4 | 80 | 候补；先做敏感性诊断 |
| TrackRoute-NSA | 3.6 | 4.2 | 4.4 | 2.1 | 3.6 | 75 | kernel 与 tracking 风险过高 |
| RD-KV / WorldGraph-Δ | 2.6 | 4.1 | 4.4 | 2.8 | 4.3 | 71 | 被实体状态记忆新作明显挤压 |
| Causal-Reactivation | 2.8 | 3.8 | 4.1 | 3.2 | 4.2 | 70 | 主动检索与证据校验赛道拥挤 |
| Adapter Atlas | 3.2 | 3.8 | 3.8 | 2.4 | 3.2 | 68 | 参数组合成本高、首篇叙事较窄 |

### 1.3 2026 年 8 月增量文献带来的实质变化

1. **证据充分性已成为显式研究对象。** [REVEAL](https://arxiv.org/abs/2608.08612) 用 rubric 验证证据充分性并定向补检；[GCR](https://arxiv.org/abs/2608.01660) 已用 Ground–Cover–Refine 处理查询已知时的互补证据与遗漏区域。因此 EVC 只能主打“因压缩淘汰造成的缺失是否可检测和校准”，不能泛称 evidence sufficiency。
2. **查询时主动选证据也已高度拥挤。** [EcoFrame](https://arxiv.org/abs/2608.03918) 用输出熵决定是否扩展帧预算、再用 attention prior 定位局部搜索区域；[EviSelect](https://arxiv.org/abs/2608.05780) 直接利用目标 MLLM 的内部 attention，并以 GRPO 学习动态时空采样。因此，“根据问题多轮找帧”本身已不足以支撑新论文，必须转向查询未知时的写入原则、压缩后缺失诊断或固定检索下的生成期机制。
3. **普通的 adaptive token fusion 已更拥挤。** [CRAFT](https://arxiv.org/abs/2608.01644) 是 query-agnostic 的递归自适应融合，在约 $8\times$ 压缩时作者报告保留约 97% 平均准确率，还显式保存融合 token 的真实时空坐标。单纯“自适应合并 + 坐标保留”不再足够。
4. **任务感知率失真也已有强邻居。** [AATC](https://arxiv.org/abs/2608.14191) 已从 transform coding 推导 attention-aware distortion 和反向注水式 bit allocation，并在文本长上下文上报告约 $5.8\times$ 近无损压缩。SR-EventKV 的新意必须是视频事件级、可随机访问、逐级细化、查询后增精和遗漏误差控制的组合，而不是“首次任务感知分配比特”。
5. **实体状态记忆已快速成熟。** [StateTrace](https://arxiv.org/abs/2608.18532) 已构建对象轨迹、关系和状态转移组成的可复用记忆，并发布 HSR-Bench；再加上 [ObjectStream](https://arxiv.org/abs/2607.28312)、[ViSAGE](https://arxiv.org/abs/2607.28678) 和 [Event-Causal RAG](https://arxiv.org/abs/2605.06185)，RD-KV/WorldGraph-Δ 若只做实体图或状态更新，新颖性不足。
6. **真正的长周期记忆有了更强评测动机。** [EgoMonth](https://arxiv.org/abs/2608.13113) 覆盖 300 多小时、20–120 天、1,443 个 QA；作者报告最佳模型 71.8%，校正后人类基线 94.2%。这使“多时间尺度、抗干扰、跨日记忆”从概念动机变成了可测问题。
7. **事件生命周期开始进入真实流式系统。** [StreamSoccer](https://arxiv.org/abs/2608.19723) 用固定预算 active memory 和 historical event records 支持当前、近期与历史解说。这进一步说明“以事件为原子”本身不是贡献，必须研究价值分配、编码或更新规律。

---

## 2. 共同论文主张与统一实验协议

### 2.1 总体科学主张

三份报告和增量文献共同指向一个更准确的问题定义：

> 超长视频视觉记忆不是把更多帧塞进上下文，而是在未来任务未知、资源有界、廉价侧信息已存在的条件下，选择、压缩、更新并可验证地恢复不可替代的视觉证据。

这个定义包含一个不能回避的信息论边界：**严格常数总存储不可能无损支持任意长视频上的任意未来问题。** 论文应明确选择以下设置之一，并分别报告，不得混淆：

1. 固定 GPU/HBM，CPU/NVMe 冷存储随视频增长；
2. 固定 GPU 与固定总存储，允许有校准风险或拒答；
3. 可访问原视频，记忆只保存索引/摘要并按需重编码；
4. 原视频不可访问，所有被删除的细节都不可恢复。

### 2.2 三种协议必须分开

1. **q-before-write**：写入前已知问题，只作为 query-aware oracle 或传统 VideoQA 设置。
2. **q-after-stream**：问题在视频写入后或流中某时刻出现；writer 严格看不到未来问题。这是五个方向的主协议。
3. **multi-query reuse / proactive**：同一段历史支持多个后续问题或主动提醒，检验持久记忆的摊销价值。

任何使用测试问题指导历史压缩、事件边界、caption 或 cold-store 建设的方法，都不能计入 q-after-stream 主结果。

### 2.3 统一的四格误差分解

|  | 原始/高保真证据 | 压缩 latent/KV |
|---|---|---|
| **Oracle 检索** | 测 reader/推理上限 | 测 codec 是否已损坏证据 |
| **学习检索** | 测 retrieval 错误 | 端到端系统结果 |

如果 `oracle retrieval + compressed representation` 已明显低于 `oracle retrieval + raw evidence`，继续堆 retrieval/router 没有意义，应先修表示；反之则优先修召回。

### 2.4 公共评测与指标

- **普通长视频**：Video-MME、MLVU、LVBench、LongVideoBench。
- **证据可验证**：[VideoZeroBench](https://arxiv.org/abs/2604.01569)、[E-VQA / ST-Evidence](https://arxiv.org/abs/2607.11862)、[EG-VQA](https://arxiv.org/abs/2606.24797)。VideoZeroBench 作者报告在答案与时空证据同时正确的最严格 Level-5 下，没有模型超过 1%，说明只报 QA accuracy 不足以证明使用了视觉记忆。
- **超长期**：EgoMonth、[MementoBench](https://proceedings.iclr.cc/paper_files/paper/2026/hash/3b5f4587a0bdb81ecc6ce9d82320a5c2-Abstract-Conference.html)、[RIVER](https://proceedings.iclr.cc/paper_files/paper/2026/hash/1022661f3f43406065641f16ce25eafa-Abstract-Conference.html)；数据许可或公开性不足时，先用可控合成长依赖集完成机制诊断。
- **内容轴**：瞬时 OCR、小物体属性、对象重现、状态改变、顺序、持续时间、audio-only、跨模态冲突、setup–payoff、两段及多段联合证据。
- **延迟轴**：10 秒至数小时按对数间隔，报告 retention–delay AUC，而非只有平均分。
- **资源账本**：峰值 HBM、总存储 bytes/min、写入 FLOPs、实时 FPS、TTFT、CPU/GPU/NVMe I/O、平均与 p95 延迟、多查询摊销成本。
- **可靠性**：evidence recall/F1、missed-evidence FNR、risk–coverage、ECE、证书违反率、跨问题组 worst-group accuracy 与 CVaR。

### 2.5 必做的因果检查

- 删除 top-retrieved memory，答案与 evidence score 应显著下降；
- 用语义相近但来自另一视频的 memory 替换，模型不应保持原答案；
- 时间打乱、实体替换、字幕—画面冲突和 matched-random latent；
- 与 recent-window-only、uniform sampling 和 caption/ASR-only 强基线比较；
- 固定 backbone、分辨率、FPS、总 bytes 和 reader token budget，避免把更多计算误报为更好记忆。

---

## 3. FQR-Mem——未来查询鲁棒的条件互补记忆

### 3.1 可支撑完整论文的动机

**[事实]** 已有 query-agnostic 流式记忆，例如 [StreamMem](https://arxiv.org/abs/2508.15717) 和 [InfiniPot-V](https://proceedings.neurips.cc/paper_files/paper/2025/hash/caef5f5e658aa1f7565f063a2cd99726-Abstract-Conference.html)，主要依据 generic query、时间冗余或 value norm 在固定预算内保留 KV；[SelectStream](https://arxiv.org/abs/2606.16353) 进一步做 surprise 写入、优先级整合和 query-conditioned 读出。另一方面，[Query-Conditioned Evidential Keyframe Sampling](https://arxiv.org/abs/2604.01002) 和 GCR 在问题已知时选择证据。

**[判断]** 这些工作没有同时回答两个问题：

1. 已有 caption、ASR/OCR、关键帧和近期窗口时，哪部分视觉信息仍不可替代？
2. 当未来问题类型和频率发生变化时，如何避免平均重要性策略系统性遗忘低频合法问题？

**[假设]** 视觉记忆真正应最大化的是“给定廉价侧信息后的未来反事实答案价值”，并以 worst-group/CVaR 约束尾部问题，而不是最大化平均显著性、运动或重建质量。

这形成了足够强的论文中心：**从 saliency memory 转向 conditional, future-query-robust evidence allocation。**

### 3.2 方法骨架

对事件 $e_t$，侧信息记为 $S_t=\{\text{caption, ASR, OCR, recent context}\}$，视觉表示为 $x_t$。先学习条件残差：

$$
r_t = E_v(x_t)-D_s(S_t),
$$

并显式保留视觉与侧信息冲突，而不是把错误 caption 能“解释”的视觉真相当作冗余。

full-context teacher 用删除事件或关系超边的反事实，给出问题 $q$ 下的边际价值：

$$
\Delta(e,q\mid S,M)=
\mathcal L_{ans}(q;M,S)-\mathcal L_{ans}(q;M\cup e,S)
+\rho\,\Delta R_{evidence}.
$$

writer 不能看到实际未来问题，只能根据事件、侧信息和历史 memory 预测一组 future-query facets（who/what/where/when/count/change/causal/OCR/audio/conflict）的 utility。固定预算选择写成：

$$
\max_{\pi:C(M_\pi)\le B}
\min_{P\in\mathcal U(P_0)}
\mathbb E_{q\sim P}[U(M_\pi,q\mid S)]
-\lambda C_{write},
$$

实现先用问题组上的 CVaR/worst-group reweighting，而不是一开始求复杂的通用 DRO。事件内存在依赖的“人物—动作—结果”以超边联合保留；固定一小部分 exploration quota，防止多轮历史问题把 memory 收缩到已知主题。

### 3.3 与最近邻的严格边界

- 相对 StreamMem/InfiniPot-V：不是另一个 query-agnostic saliency score，而是**给定侧信息后的反事实互补价值 + 未来问题分布尾部风险**。
- 相对 SelectStream：不是以 local surprise 近似未来价值；surprise 可作为特征，但不是监督目标。
- 相对 query-conditioned sampling/GCR：writer 看不到实际问题；这些方法应作为 q-before-write oracle。
- 相对 CoRDS/普通 coreset：不是只覆盖 embedding 几何，而是覆盖下游问题组和 evidence requirements。
- 相对原 CPLM：加入显式的问题分布漂移和 rare-event safety；相对原 DRO-FutureMem：条件在 side information 上，只保存真正视觉互补量。二者应合成一篇，不宜拆成两个近似 writer。

### 3.4 决定性实验

**H1：条件互补性。** 在相同 bytes 下，FQR-Mem 对 caption/ASR 不充分、视觉—文本冲突、细粒度属性和状态变化问题的收益，应显著高于 caption 可充分回答的问题；去掉 side-information conditioner 后该差异消失。

**H2：尾部鲁棒性。** 训练与测试交换问题类型频率，或完整留出 OCR/count/audio/conflict 中的一类；FQR-Mem 应提升 worst-group/CVaR，而不是只改善平均准确率。

**H3：确实使用所存证据。** 删除模型宣称关键的残差事件，答案和 grounded evidence 必须同步下降；替换成相似无关事件不能保持结果。

最小实验包：

- 冻结一个 3B/7B VideoLLM，只训练 event encoder、utility critic 和 streaming swap policy；
- LVBench/Video-MME-long 做通用结果，VideoZeroBench 或 EG-VQA 做 evidence 结果；
- 自建小型 delayed-query distribution-shift 子集，控制稀有事件、问题类型和 side-information sufficiency；
- 基线至少包括 uniform、recent-only、caption/ASR-only、StreamMem、InfiniPot-V、SelectStream-style surprise、query-known evidence selector 和 full-context teacher；
- 报平均、worst-group、CVaR@10%、evidence recall、bytes、write cost、TTFT 和三随机种子。

### 3.5 止损标准与论文包装

以下任一出现时，应停止扩展 router：

1. 两个数据集上，CVaR writer 在三随机种子下不能稳定改善 worst-group，或改善只来自明显牺牲平均性能；
2. conditional residual 与直接存原视觉 embedding 在等 bytes 下无差异；
3. oracle retrieval 下 latent 表示远低于 raw evidence，说明瓶颈是 codec 而非 writer；
4. utility critic 对留出问题类型近似随机，无法支持“未来查询鲁棒”的主张。

可用论文题目：**Remember What Future Questions Cannot Reconstruct: Distributionally Robust Complementary Memory for Streaming Video**。

完整贡献应控制为四点：新设置与目标、conditional robust writer、delayed-query shift protocol、准确率—证据—成本三维结果。不要同时加入复杂 Agent、TTT 和新 sparse kernel。

---

## 4. EvictCert-Mem——可校准的淘汰证书记忆

### 4.1 可支撑完整论文的动机

**[事实]** OASIS 在答案不充分时按需检索；REVEAL 已显式检查证据充分性并找出缺失线索；[E-VQA](https://arxiv.org/abs/2607.11862)、[EG-VQA](https://arxiv.org/abs/2606.24797) 和 VideoZeroBench 则表明答案正确与证据正确明显脱钩。

**[判断]** 仍未被直接解决的更窄问题是：**当一个 query-hidden、固定预算 writer 已经执行淘汰时，系统能否知道必要证据曾经存在但已被自己删除？** 只看当前答案熵或当前检索集合无法区分：

- 证据仍在但推理困难；
- 检索器没找到仍在库中的证据；
- 证据已经被压缩/淘汰，活跃库中根本不存在；
- 问题在已观察视频中本来就无答案。

论文应把任务定义为 **compression-induced missing-evidence detection**，而不是笼统的 evidence sufficiency。

### 4.2 方法骨架

每次淘汰区间 $b$ 时，在问题未知的条件下生成极小的 eviction witness：

$$
w_b=\{h_b^{sem},h_b^{vis},h_b^{ocr},h_b^{audio},
[t_s,t_e],u_b,\text{provenance pointer}\}.
$$

其中包括语义投影、对象/动作/OCR/audio hash、状态变化与感知不确定性；witness tree 只用于判断“可能缺了什么”和定位，不直接充当答案证据。高保真块可在 CPU/NVMe，或在严格总预算设置下只保存高风险 cold blocks。

问题到来后，覆盖检测器联合读取 $q$、active memory 和 witness tree：

$$
g_\theta(q,M_{active},W)
\rightarrow
p(z\in\{covered,retrieval\ failure,evicted,unanswerable\}),
\quad p(b\mid z=evicted).
$$

训练数据通过 full-context evidence 标注和受控删除生成：删除必要证据、删除等量非必要证据、保留证据但让 retriever 失败、以及原视频无答案。推理采取三路决策：直接回答、回取/重编码、或校准拒答。

可把目标写成 selective-risk 约束：在校准分布上控制“证据已淘汰却仍回答”的风险不超过 $\delta$，同时最小化 I/O 和拒答率。split conformal 只在交换性近似成立的同分布设置下声明覆盖；分布外结果只报告经验风险，不夸大保证。

### 4.3 与最近邻的严格边界

- 相对 REVEAL：REVEAL 验证当前检索证据是否满足 rubric；本方案的证据来自**淘汰时留下、问题未知的 witness 与 provenance**，目标是识别 compression-induced absence。
- 相对 [MemVAU](https://openreview.net/forum?id=shStSIP0aE)（匿名投稿稿）：MemVAU 在已知的 What/Who/Where/How 四维 rubric 下验证证据并保护互补条目；本方案面向任意事后问题，且必须区分淘汰、检索、推理与无答案四类失败。
- 相对视频生成中的 [Surprise Forcing](https://arxiv.org/abs/2607.18436)：为淘汰帧保留 descriptor 本身不是新点；本方案不以 novelty 决定保留，而以 witness 检测 query 所需证据是否已不在 active memory，并校准 silent-failure 风险。
- 相对 OASIS：触发信号不是一般答案不确定性，而是必要证据已不在 active memory 的风险。
- 相对 GCR/VideoLucy：不是查询已知后的 coverage/refinement，而是先看后问条件下对已删除内容的可检测性。
- 相对 ReKV/REFORM 类存取系统：贡献不在“能 offload/reload”，而在“何时必须 reload、缺失位置能否定位、假阴性风险是否可校准”。
- 相对文本 KV 工作：[IndexMem](https://arxiv.org/abs/2605.25475) 把被淘汰 token 压入 latent state，[ArkVale](https://openreview.net/forum?id=4oAt5L4lYe) 用 page digest 召回动态重要 KV，[KV-Rescue](https://arxiv.org/abs/2608.15797) 用 entropy/compressibility 检测淘汰后的退化；它们都未定义视觉问题所需证据是否已被淘汰、失败类型与 grounded risk calibration。
- 相对文本 [SURE-RAG](https://arxiv.org/abs/2605.03534)：任务是视觉压缩生命周期中的 provenance-aware missingness，而非一般 passage sufficiency。

### 4.4 决定性实验

**H1：缺失类型可区分。** 在 matched QA confidence 下，模型能区分 reasoning failure、retrieval failure、eviction 和 unanswerable。

**H2：witness 有独立价值。** 在 matched answer coverage 或 matched I/O 下，witness-based detector 的 missed-evidence FNR 应低于答案熵、self-verification、REVEAL-style rubric 和无 witness 检测器。

**H3：校准能转化为系统收益。** 降低高置信错误的同时，I/O 与拒答没有退化到“几乎总回取/总拒答”的平凡解。

最小实验包：

- 从带 temporal evidence 的 LVBench、VideoZeroBench、EG-VQA/E-VQA 构造 counterfactual eviction benchmark；
- 冻结 VideoLLM，只训练 witness encoder、四分类/定位器和 threshold calibrator；
- 设置严格固定总存储与固定 HBM + 可增长冷存储两条曲线；
- 报 missed-evidence AUROC/AUPRC、FNR@95% answer coverage、risk–coverage、定位 recall、恢复后 QA/evidence gain、witness bytes、I/O 与 p95 TTFT；
- oracle witness、随机 witness、纯文本 witness、无 provenance、无 calibration 和 answer-entropy trigger 都要消融。

### 4.5 止损标准与论文包装

在四周诊断中，若 witness detector 在 matched coverage 下不能稳定优于 REVEAL-style rubric/答案熵，或其有效策略退化为几乎总回取，则该方向不再具有足够独立价值。另一个止损点是 witness 开销接近保存低清原帧的开销；此时直接保留低清证据更合理。

可用论文题目：**Do Video Memories Know What They Forgot? Calibrated Detection and Recovery of Evicted Visual Evidence**。

CVPR 版本可强调 grounded evidence 与可靠 VideoQA；ICLR 版本需要更清晰的 selective-risk 形式化、校准假设和压缩诱发缺失的任务定义。

---

## 5. RTC-Mem——回溯式时间信用记忆

### 5.1 可支撑完整论文的动机

许多关键事件在发生时并不显著：拿起钥匙、把药放进口袋、记住一个人的临时位置。只有后续出现“开门”“服药提醒”或“物体再次被寻找”时，早期事件的重要性才显现。local surprise、当前 attention、value norm 和 query-agnostic saliency 都只能依据写入当时的信息。

**[事实]** [ViSAGE](https://arxiv.org/abs/2607.28678) 用延迟身份线索修正早期实体记忆；[Event-Causal RAG](https://arxiv.org/abs/2605.06185) 做双向因果链检索；[RetroAttention](https://proceedings.iclr.cc/paper_files/paper/2026/hash/f4daa773a5bb2d562a9204a7e2225a67-Abstract-Conference.html) 用后来载入的 KV 修订文本生成中的过去 attention output；[Self Gradient Forcing](https://arxiv.org/abs/2607.20368) 则在长视频生成中让未来帧损失监督更早的 context KV。

**[判断]** 仍有空间的问题是：在视频理解、未来 query 未知和固定预算下，用旧事件对后续观察的**反事实边际预测贡献**分配 temporal credit，并让 credit 直接改变 retention/promotion。

### 5.2 方法骨架

事件 $j$ 初始只得到 local utility 和低码率 forensic sketch。新事件 $t$ 到来时，定义：

$$
c_{t,j}=\mathcal L_{pred}(z_t\mid M_{<t}\setminus m_j)
-\mathcal L_{pred}(z_t\mid M_{<t}).
$$

精确 leave-one-out 只在 teacher 数据的一小部分计算，用来训练 influence critic $\hat c_\phi(z_t,m_j,M_{<t})$。在线只对 ANN/causal prefilter 找到的少量候选做 credit sweep：

$$
u_j^t=\gamma u_j^{t-1}
+\eta[\hat c_\phi(z_t,m_j)-b_{freq}(j,t)]_+.
$$

减去频率 baseline，防止重复背景因易预测而获得虚高信用。高 credit 触发：从 active 到 protected tier、从 base 到 enhancement layer，或在原视频可访问时重新编码；严格流式且原像素已丢失时，只能晋升已有 sketch，不能声称恢复细节。

### 5.3 与最近邻的严格边界

- 相对 ViSAGE：不是用延迟身份线索统一实体 ID，而是通用的 future-prediction marginal contribution，并用于保留决策。
- 相对 RetroAttention：不修订过去的 attention output，而修订过去 memory item 的未来存储优先级。
- 相对 Self Gradient Forcing：任务是视频理解而非生成；credit 控制 query-hidden fixed-budget retention，而非只优化生成上下文 KV。
- 相对 event-causal graph：不依赖显式语言化因果边，核心是可学习的反事实贡献和 promotion law。
- 相对 SSCM：RTC 是“谁应获得延迟信用”的训练/控制信号；SSCM 是“写进哪一个参数时间尺度”的架构。首篇不要强行合并完整 SSCM。

### 5.4 决定性实验

**H1：延迟信用优于局部显著性。** 在 setup–payoff、物体先出现后使用、程序步骤和长间隔因果对上，RTC 对 setup evidence 的 retention–delay AUC 高于 surprise/attention/value norm。

**H2：credit 学到依赖而非重复。** 加入高频重复但与 payoff 无关的 hard negatives；只有条件反事实版本应避免给它们高信用。

**H3：跨域泛化。** influence critic 在留出视频域或留出事件关系上仍能排序关键 setup；否则只是数据集模板分类器。

最小实验包：

- 先建立 10 秒至 1 小时的合成/半合成 setup–payoff 诊断集，再上 [MMR-V](https://proceedings.iclr.cc/paper_files/paper/2026/hash/6f1989abe9562c5cd306e070725fe0a3-Abstract-Conference.html)、RIVER、LongVideoBench 或 EgoMonth 可用子集；
- 冻结视频 encoder 和 reader，只训练 multi-horizon predictor、credit critic 与固定预算 selector；
- 比较 local surprise、historical attention、StreamMem、future prediction without leave-one-out、query-time backtracking 和 oracle credit；
- 报 setup recall、retention–delay AUC、credit calibration/ranking、重复干扰鲁棒性、每分钟 credit sweep 成本；
- 在线 causal 结果与视频结束后的 backward sweep 结果必须分开。

### 5.5 止损标准与论文包装

若控制重复频率后，$\hat c$ 与真正的 setup dependence 不再相关；或 oracle credit 有效但 learned critic 在两个域上都不优于 local surprise，则应停止。若 credit sweep 成本随历史线性增长且近邻预筛无法控制，也不适合作为流式记忆方案。

可用论文题目：**Credit Arrives Late: Retrospective Temporal Credit for Query-Hidden Video Memory**。

论文最有价值的结果不是普通 benchmark 增加一两个点，而是清楚证明“重要性会随未来观察改变”，并展示现有一次性写入分数在可控任务上的系统失败。

---

## 6. SR-EventKV——逐级细化的事件 KV 编码器

### 6.1 可支撑完整论文的动机

hard eviction 对未知问题不可逆；统一低秩或统一量化则把相同预算浪费在简单事件与复杂事件上。已有工作已覆盖相当多组件：

- [MuKV](https://arxiv.org/abs/2605.22269)：patch/frame/segment 多粒度视频 KV；
- [VarRate](https://arxiv.org/abs/2607.15498)：每 token 非零、可变低秩预算；
- [DeltaKV](https://arxiv.org/abs/2602.08005)：相对历史参考的残差编码；
- [VideoLucy](https://openreview.net/forum?id=To7Rs2wsTd)：从粗到细的层次记忆回溯；
- AATC：attention-aware transform coding 和 bit allocation；
- [Quant VideoGen](https://arxiv.org/abs/2602.02958)：视频生成 KV 的 progressive residual quantization。

因此新意不能是“多粒度”“可变 rank”“残差”或“渐进读取”中的任一个。可辩护的完整组合是：

> 面向 q-after-stream 的事件级嵌套 KV bitstream；所有事件都有可发现的 base layer，enhancement layer 可独立随机访问；allocator 依据 query 和 attention-output error 逐级增精；成本按真实编码 bits 与 I/O 计量。

### 6.2 方法骨架

对事件 $j$ 的 $X_j=[K_j,V_j]$ 编成嵌套层：

$$
c_j^0,c_j^1,\ldots,c_j^R=E(X_j),\qquad
\hat X_j(r)=D_0(c_j^0)+\sum_{s=1}^{r}D_s(c_j^s).
$$

- $c^0$：所有事件必留的极低码率 discoverability sketch，包括 key centroid、时间区间、实体/OCR hash、value norm 和残差半径；
- $c^{1:R}$：外观、运动、OCR、关系等残差，按 event page 连续存放于 CPU/NVMe；
- query 到来后，allocator 每步选择使预计 attention-output error/bit 降幅最大的 `(event, layer)`，直至预算或风险阈值。

理论只主张局部性质：对单层、单 head，利用未加载 page 的 logit 上界、已加载 K/V 的重建半径和 value norm，给出 $\lVert o_{full}-o_{loaded}\rVert$ 的保守上界。不得把它直接称为“答案正确性证书”；跨层传播需要额外 Lipschitz 假设或经验校准。

训练采用 full-cache teacher 蒸馏 attention output 与答案分布，并用 entropy model 计算真实 bit rate：

$$
\mathcal L=
\operatorname{KL}(p_{full}\|p_{codec})
+\lambda\sum_l\|o_l^{full}-o_l^{codec}\|_2^2
+\beta\sum_{j,s\le r_j}-\log_2p(c_j^s)
+\gamma\mathcal L_{ground}.
$$

### 6.3 与最近邻的严格边界

- 相对 AATC：从文本 calibration-set bit allocation 扩展到视频事件、query-late successive refinement、随机访问与真实 I/O；不能再声称首次 attention-aware coding。
- 相对 MuKV：不是固定多粒度表示，而是一个前缀可解码的嵌套码流和按 query 增精的 rate controller。
- 相对 VarRate：base layer 保证事件可发现，更多 rank/bit 在问题到来后分配，而非一次性依据当前 salience 固定。
- 相对 VideoLucy：不是预先生成不同粒度 caption 后 Agent 回溯，而是模型内部 KV 的实际码流和误差控制。
- 相对 LateBind-Video 原案：删去过大的“通用视频语义 codec”叙事，聚焦 event KV 和可验证的 attention distortion，降低工程面。

### 6.4 决定性实验

**H1：successive refinement 优于一次性压缩。** 在相同总 bits 和 HBM 下，多问题类型应能从同一 base stream 购买不同 enhancement layers，并优于固定 rank/固定多粒度。

**H2：base 保持 discoverability。** 对稀有 OCR、小物体、短动作和远距关系，base-only coarse retrieval recall 必须足以找到需增精事件。

**H3：误差估计能指导真实收益。** bound/risk 排序与加载后的 attention error、答案/evidence 增益相关；否则证书只是很松的装饰。

最小实验包：

- 先只选 2–4 个 LLM layers 和 event-level KV，不做全模型 codec；
- 在 Video-MME-long、LVBench、LongVideoBench 和一个 evidence benchmark 上比较 full KV、[VidKV](https://arxiv.org/abs/2503.16257)、MuKV、VarRate、DeltaKV、AATC-adapted、VideoLucy-style hierarchy；
- 三套公平预算：固定 HBM、固定总 bits、固定端到端延迟；PCIe/NVMe 计入；
- 报 accuracy/evidence–bit Pareto、base retrieval recall、bound tightness/违反率、TTFT、I/O、多 query 摊销收益；
- 比较读取 enhancement layer 与直接重编码原视频片段的延迟。

### 6.5 止损标准与论文包装

若 base layer 对关键证据的召回无法超过简单低清 keyframe/hash 索引，或加载 enhancement layer 的 p95 延迟不低于重编码原片段，则系统价值不足。若确定性上界在绝大多数 query 上都接近 1、不能排序加载收益，则删除“certificate”主张，退回纯 learned allocator，不应勉强包装理论。

可用论文题目：**A Little Bit for Every Event: Successive-Refinement KV Memory for Query-Late Long-Video Understanding**。

---

## 7. SSCM——语义惊奇驱动的多时间尺度连续谱记忆

### 7.1 可支撑完整论文的动机

显式 KV/archive 即使把 GPU 占用固定，索引或冷存储仍会随视频增长。参数化 test-time memory 提供另一条路线：用固定大小的 fast weights 持续吸收经验。但视频中的像素/feature surprise 会把镜头切换、抖动、模糊和光照变化误判为长期重要；单一更新时钟也会让重复场景覆盖早期语义。

**[事实]** [video-SALMONN S](https://arxiv.org/abs/2510.11129) 已把 TTT memory 用于固定预算的小时级流式音视频理解；[Nested Learning / HOPE](https://arxiv.org/abs/2512.24695) 提出 continuum memory；[Online Neural Space Time Memory](https://arxiv.org/abs/2607.15271) 在动态新视角合成中解耦 memory update 与 application 的频率。同时，[SURGE](https://proceedings.iclr.cc/paper_files/paper/2026/hash/07b92344686c19cf3ffc335a0f565406-Abstract-Conference.html) 已用 token prediction error 做 surprise-guided pruning，[Cambrian-S](https://arxiv.org/abs/2511.04670) 已用下一帧 latent prediction error 驱动流式记忆和事件分割，Surprise Forcing 则在视频生成中用 novelty 管理淘汰帧。因此“把 TTT 用到视频”“使用多个频率”或“按 surprise 写记忆”中的任一个都不够新。

**[判断]** 有论文空间的组合必须同时包含：

1. 多模态**语义**预测残差，而非像素变化；
2. 可学习的多时钟路由；
3. 从快层到慢层的证据晋升；
4. 显式抗干扰与稳定性机制；
5. q-after-stream 视频理解验证，而非只做生成或重建。

### 7.2 方法骨架

对视觉、音频和字幕表征，以对象/动作/状态、audio event、多步未来 latent 和跨模态一致性定义 surprise：

$$
s_t=\sum_m\pi_t^m
D(y_t^m,f_{W_{t-1}}(k_t^m))
+\lambda D_{cross}(x_t^v,x_t^a,x_t^s).
$$

$\pi_t^m$ 是感知不确定性权重，避免低质量模态支配更新。维护 $L$ 个不同半衰期、固定容量的低秩 memory modules，router 输出更新权重：

$$
r_t^\ell=\operatorname{softmax}_\ell
g_\theta(s_t,\bar s_t^{(\tau_\ell)},\Delta s_t,
\text{duration},\text{modal agreement}).
$$

快层吸收短暂但可信的变化；只有持续、跨模态一致且在 eligibility trace 中稳定的残差才晋升到慢层。每层只做固定 1–4 步低秩更新，并用固定数量 anchors、functional regularization、update-norm clipping 和 rollback checkpoint 抑制漂移。近期精确 KV 独立保留，避免让参数记忆承担即时感知。

### 7.3 与最近邻的严格边界

- 相对 video-SALMONN S：不是单一 TTT memory + prompt reader，而是 semantic surprise、多时钟路由、晋升和抗干扰的联合更新律。
- 相对 HOPE：把抽象 continuum memory 落到多模态视频语义、明确的 q-after-stream 评测与 evidence retention。
- 相对 Online Neural Space Time Memory：不仅固定/周期更新，而是内容条件的可学习时钟；任务是长视频理解而非 NVS。
- 相对 SURGE/Cambrian-S/Surprise Forcing：不是用 token/latent prediction error 或 novelty 做一次性 pruning/admission，而是用对象—动作—状态与跨模态一致性的语义残差，决定参数记忆的更新时钟和跨层晋升。
- 相对 Titans：surprise 由跨模态语义预测和状态变化定义，避免直接迁移文本 surprise。
- 相对 RTC：SSCM 决定更新在哪个时间尺度；RTC 决定某个旧事件是否因后来观察获得信用。第一阶段只做 SSCM，不加入完整 RTC。

### 7.4 决定性实验

**H1：语义 surprise 更接近未来证据价值。** 在镜头切换/抖动 hard negatives 与低运动状态改变 positives 上，semantic surprise 对未来 evidence utility 的排序优于 feature distance、prediction error 和 scene boundary。

**H2：多时钟降低干扰。** 在重复日常活动和 log-spaced delay 下，多时钟 + promotion 的 retention–delay AUC 高于单一 TTT、固定双 memory 与 reservoir replay。

**H3：固定状态下真正扩展时间。** 增长视频时长时，状态大小不变、更新成本稳定，且对跨日/跨小时问题的性能退化慢于最近窗口与单时钟基线。

最小实验包：

- 先在冻结 encoder + 小型 memory MLP/LoRA 上做，不直接 end-to-end 训练 7B；
- 构造视觉抖动、场景切换、低运动状态变化、跨模态冲突和重复日程的诊断流；
- 再评 MementoBench/RIVER/EgoMonth 可用部分，并与 video-SALMONN S、单 TTT、固定 update frequency、dual memory 和无梯度 event archive 比较；
- 报 retention–delay AUC、干扰后恢复、更新次数/时间、状态 bytes、drift、rollback 次数、QA 与 evidence recall；
- 必须展示运行时间随流长度不增长，而不只展示显存固定。

### 7.5 止损标准与论文包装

若小模型诊断中 semantic surprise 不能稳定优于简单 event boundary/feature distance，或多时钟在固定状态下没有降低干扰，就不应扩展到大 VideoLLM。若 online update 的延迟或漂移使系统必须频繁回滚，也应转向显式 event memory。

可用论文题目：**Not Every Surprise Lasts: Semantic Multi-Clock Memory for Continual Video Understanding**。

这是五项中影响上限最高但实现风险最大的方向，适合在 FQR-Mem/RTC 的诊断基础和统一数据协议成熟后推进。

---

## 8. 为什么其余原方案当前不进入前五

### 8.1 ME-TimeKV：最强候补，但先做两周敏感性实验

TM-KV + ChronoCache 的问题很清楚：压缩 token 代表一个时间分布，cache address 不等于物理视频时间。然而最近邻已经密集出现：TIE 编码时间区间，ST-Merge 用加权质心修正 merge 后位置，[Kamera](https://arxiv.org/abs/2606.23581) 做 position-invariant KV reuse 和 RoPE 重旋转，CRAFT 保存融合 token 的真实时空坐标。

只在以下诊断成立时重新升为主方向：同一视频改变 FPS、block size、merge tree 或检索拼接顺序时，现有中心时刻/端点/TIE/CRAFT-style coordinate 的 temporal QA、grounding 或 routing recall 出现稳定显著差异，而 content-weighted time measure 能修复。否则它更像精巧但影响有限的位置编码模块。

### 8.2 RD-KV、WorldGraph-Δ、TrackRoute-NSA

[StateTrace](https://arxiv.org/abs/2608.18532)、[ObjectStream](https://arxiv.org/abs/2607.28312)、[ViSAGE](https://arxiv.org/abs/2607.28678)、[Event-Causal RAG](https://arxiv.org/abs/2605.06185) 和 [WorldMM](https://openaccess.thecvf.com/content/CVPR2026/html/Yeo_WorldMM_Dynamic_Multimodal_Memory_Agent_for_Long_Video_Reasoning_CVPR_2026_paper.html) 已覆盖对象轨迹、状态变化、关系、延迟身份修正与因果检索。若没有端到端 entity binding、内部 typed KV、真实 sparse kernel 加速和跨遮挡稳定性，容易被评价为“又一张实体图”。TrackRoute-NSA 还同时承担 tracking error、动态 packing 和 kernel 工程风险，不适合作为当前第一优先级。

### 8.3 Causal-Reactivation

[OASIS](https://openaccess.thecvf.com/content/CVPR2026/html/Liang_OASIS_On-Demand_Hierarchical_Event_Memory_for_Streaming_Video_Reasoning_CVPR_2026_paper.html)、[LongVT](https://openaccess.thecvf.com/content/CVPR2026/html/Yang_LongVT_Incentivizing_Thinking_with_Long_Videos_via_Native_Tool_Calling_CVPR_2026_paper.html)、[LongVideo-R1](https://openaccess.thecvf.com/content/CVPR2026/html/Qiu_LongVideo-R1_Smart_Navigation_for_Low-cost_Long_Video_Understanding_CVPR_2026_paper.html)、[Video-MTR](https://openreview.net/forum?id=UhPwL6LYOc)、[FrameThinker](https://openreview.net/forum?id=nsNpsCpVG1)、[EventMemAgent](https://arxiv.org/abs/2602.15329)、[GenEvA](https://arxiv.org/abs/2607.28516)、REVEAL、GCR、EcoFrame 和 EviSelect 已形成密集的 query-time 主动搜索、证据聚合与补证据赛道。除非能证明 generation-time reactivation 解决的是“证据已进入 context 后的 visual anchoring decay”，并在固定 retrieval 结果下显著优于普通重读，否则新颖性与归因都不够干净。

### 8.4 Adapter Atlas / 参数记忆分片

[Frames2LoRA](https://arxiv.org/abs/2606.04351)、[VideoMind / Chain-of-LoRA](https://arxiv.org/abs/2503.13444) 和各类参数编辑/组合方法已使“把视频写入参数或用多个 LoRA 承载视频能力”成为相邻方向。它面临写入成本、多 adapter 合成干扰、原始证据不可审计和多查询才可能摊销等问题。更适合重复访问同一视频库的后续项目，而非当前最普适的超长视频记忆问题。

---

## 9. 推荐执行顺序

### 阶段 A：先建最小 Video Memory Gym（2 周）

只实现共同协议，不急着实现五个方法：

1. q-before-write、q-after-stream、multi-query 三种数据入口；
2. uniform、recent-only、caption/ASR-only、full-context/oracle retrieval 四个基础线；
3. oracle/raw、learned/raw、oracle/latent、learned/latent 四格分解；
4. evidence span、问题组、delay、bytes、HBM、I/O、TTFT 的统一日志；
5. counterfactual deletion/swap/time-shuffle 测试。

### 阶段 B：并行做两个小诊断，但只选一个主论文（4–6 周）

- **FQR-Mem MVP**：固定 question taxonomy + 离线 teacher utility + greedy/CVaR streaming swap；先不学习 latent query basis。
- **EvictCert-Mem MVP**：对同一批 teacher evidence 做必要/非必要删除，只训练 witness detector；首先与 REVEAL-style rubric 和答案熵比较。

第六周按预注册标准选择：如果 FQR 的 worst-group 曲线明显成立，进入主线；如果 writer 效果弱但 EvictCert 能显著降低 silent failure，则转向可靠性论文。不要把两者全部堆进首篇，否则 reviewer 难以判断提升来自“少忘”还是“知道忘了”。

### 阶段 C：机制扩展

1. 用 RTC 小数据诊断“延迟重要性”是否真实存在；若成立，可作为 FQR 的下一篇 writer 更新机制。
2. 如果 oracle latent 已成为主要瓶颈，再投入 SR-EventKV；否则先不要做 codec 大工程。
3. SSCM 只在语义 surprise 与多时钟的小模型结果通过止损线后扩展。

---

## 10. 一篇强论文必须闭合的证据链

无论选择哪一项，至少需要同时满足：

1. **问题真实存在**：受控诊断证明现有方法有系统失败，而非只在平均 benchmark 上差一点。
2. **机制解决对应问题**：关键组件对失败轴产生定向改善，普通规模增大或额外 token 不能解释。
3. **记忆确实被使用**：删除、替换、打乱所检索证据会改变答案和 grounding。
4. **资源比较公平**：固定 backbone、视频采样、bytes、reader budget，并计入写入、I/O 和尾延迟。
5. **结论不过界**：局部 attention 误差界不等于答案保证；同分布 conformal calibration 不等于 OOD 保证；固定 HBM 不等于固定总信息。
6. **至少两个自然数据集 + 一个受控诊断集**：自然数据证明外部有效性，诊断集建立因果归因。
7. **负结果和止损透明**：报告 query leakage、side-information error、cold-store 增长、失败问题组与 seed 方差。

满足这条证据链，FQR-Mem、EvictCert-Mem 或 RTC-Mem 的动机和贡献完整度足以支撑 ICLR/CVPR 投稿；缺少其中两三项，即使系统分数较高，也容易被评价为又一个长视频检索/压缩管线。

---

## 11. 本轮重点核验的一手来源

### 2026 年 8 月关键增量

- [CRAFT: Compression via Recursive Adaptive Fusion of Video Tokens for Vision-Language Models](https://arxiv.org/abs/2608.01644)
- [Ground, Cover, and Refine: Evidence-Centric Frame Selection for Long-Video Question Answering](https://arxiv.org/abs/2608.01660)
- [When and Where to Look: Adaptive Visual Evidence Scheduling for Efficient Long Video Understanding / EcoFrame](https://arxiv.org/abs/2608.03918)
- [Evidence-Driven Dynamic Visual Selector for Efficient Long Video Understanding / EviSelect](https://arxiv.org/abs/2608.05780)
- [REVEAL: A Rubric-Guided Agent for Explicit Evidence Sufficiency Verification in Long-Video Question Answering](https://arxiv.org/abs/2608.08612)
- [EgoMonth: A Month-Level Egocentric Video Benchmark for Long-Term Spatiotemporal Memory](https://arxiv.org/abs/2608.13113)
- [KV Cache Compression Through the Lens of Transform Coding](https://arxiv.org/abs/2608.14191)
- [StateTrace: An Object-Centric Framework for Hidden-State Spatiotemporal Reasoning in Long Videos](https://arxiv.org/abs/2608.18532)
- [StreamSoccer: Event-Driven Memory for Streaming Soccer Commentary](https://arxiv.org/abs/2608.19723)

### 核心比较工作与评测

- [What Should a Streaming Video Model Remember? / SelectStream](https://arxiv.org/abs/2606.16353)
- [StreamMem: Query-Agnostic KV Cache Memory for Streaming Video Understanding](https://arxiv.org/abs/2508.15717)
- [InfiniPot-V: Memory-Constrained KV Cache Compression for Streaming Video Understanding](https://proceedings.neurips.cc/paper_files/paper/2025/hash/caef5f5e658aa1f7565f063a2cd99726-Abstract-Conference.html)
- [OASIS: On-Demand Hierarchical Event Memory for Streaming Video Reasoning](https://openaccess.thecvf.com/content/CVPR2026/html/Liang_OASIS_On-Demand_Hierarchical_Event_Memory_for_Streaming_Video_Reasoning_CVPR_2026_paper.html)
- [VideoLucy: Deep Memory Backtracking for Long Video Understanding](https://openreview.net/forum?id=To7Rs2wsTd)
- [Query-Conditioned Evidential Keyframe Sampling for MLLM-Based Long-Form Video Understanding](https://arxiv.org/abs/2604.01002)
- [Evidence-Backed Video Question Answering](https://arxiv.org/abs/2607.11862)
- [EG-VQA: Benchmarking Verifiable Video Question Answering with Grounded Temporal Evidence](https://arxiv.org/abs/2606.24797)
- [VideoZeroBench: Probing the Limits of Video MLLMs with Spatio-Temporal Evidence Verification](https://arxiv.org/abs/2604.01569)
- [Memento: Toward an All-Day Proactive Assistant for Ultra-Long Streaming Video](https://proceedings.iclr.cc/paper_files/paper/2026/hash/3b5f4587a0bdb81ecc6ce9d82320a5c2-Abstract-Conference.html)
- [RIVER: A Real-Time Interaction Benchmark for Video LLMs](https://proceedings.iclr.cc/paper_files/paper/2026/hash/1022661f3f43406065641f16ce25eafa-Abstract-Conference.html)
- [MMR-V: What's Left Unsaid? A Benchmark for Multimodal Deep Reasoning in Videos](https://proceedings.iclr.cc/paper_files/paper/2026/hash/6f1989abe9562c5cd306e070725fe0a3-Abstract-Conference.html)
- [MuKV: Multi-Grained KV Cache Compression for Long Streaming Video Question-Answering](https://arxiv.org/abs/2605.22269)
- [VarRate: Training-Free Variable-Rate KV Cache Compression for Long-Context LLMs](https://arxiv.org/abs/2607.15498)
- [DeltaKV: Residual-Based KV Cache Compression via Long-Range Similarity](https://arxiv.org/abs/2602.08005)
- [TIE: Time Interval Encoding for Video Generation over Events](https://arxiv.org/abs/2605.10543)
- [Kamera: Unified Position-Invariant Multimodal KV Cache for Training-Free Reuse](https://arxiv.org/abs/2606.23581)
- [Fast Enough to Act / ST-Merge](https://arxiv.org/abs/2606.29350)
- [RetroAttention: Retrospective Sparse Attention for Efficient Long-Context Generation](https://proceedings.iclr.cc/paper_files/paper/2026/hash/f4daa773a5bb2d562a9204a7e2225a67-Abstract-Conference.html)
- [Self Gradient Forcing: Native Long Video Extrapolation](https://arxiv.org/abs/2607.20368)
- [video-SALMONN S: Streaming Audio-Visual LLMs Beyond Length Limits via Memory](https://arxiv.org/abs/2510.11129)
- [Nested Learning: The Illusion of Deep Learning Architectures](https://arxiv.org/abs/2512.24695)
- [Online Neural Space Time Memory for Dynamic Novel View Synthesis](https://arxiv.org/abs/2607.15271)
- [Event-Causal RAG: A Retrieval-Augmented Generation Framework for Long Video Reasoning in Complex Scenarios](https://arxiv.org/abs/2605.06185)
- [SURGE: Surprise-Guided Token Reduction for Efficient Video Understanding with VLMs](https://proceedings.iclr.cc/paper_files/paper/2026/hash/07b92344686c19cf3ffc335a0f565406-Abstract-Conference.html)
- [Cambrian-S: Towards Spatial Supersensing in Video](https://arxiv.org/abs/2511.04670)
- [Surprise Forcing: What to Remember, When to Skip in Long Video Generation](https://arxiv.org/abs/2607.18436)
- [MemVAU: Agentic Visual Evidence Memory for Video Anomaly Understanding（匿名投稿稿）](https://openreview.net/forum?id=shStSIP0aE)
- [IndexMem: Learned KV-Cache Eviction with Latent Memory for Long-Context LLM Inference](https://arxiv.org/abs/2605.25475)
- [ArkVale: Efficient Generative LLM Inference with Recallable Key-Value Eviction](https://openreview.net/forum?id=4oAt5L4lYe)
- [KV-Rescue: Recovering Reasoning Language Model KV Eviction Loss via Stepwise Interleaving](https://arxiv.org/abs/2608.15797)
