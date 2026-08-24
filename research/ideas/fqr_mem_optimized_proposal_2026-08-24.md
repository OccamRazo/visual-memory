# FQR-Mem v2：面向未知未来问题的条件证据视觉记忆

> 英文暂定名：**FQR-Mem: Future-Query-Robust Conditional Evidence Memory for Ultra-Long Video**
>
> 日期：2026-08-24
>
> 状态：优化后的研究方案，尚未经过实验验证
>
> 文献依据：[FQR-Mem：2026 年相关文献证据表](../literature/fqr_mem_2026_literature_evidence.md)

## 0. 执行结论

FQR-Mem 值得继续，但必须把论文问题收窄为：

> 当视频只能流式看一次、写入时不知道未来问题、视觉记忆总预算固定、ASR/OCR/描述等低成本 side information 已经存在、原视频不能回放时，应该保存哪些**无法由 side information 可靠替代**的视觉证据，才能在事先声明的问题与证据分布变化下，最小化未来问题的上尾 grounded regret？

它不是一般的视频摘要、通用 token 压缩、query-aware 选帧或无限上下文方法。论文能否达到 ICLR/CVPR 水平，取决于以下三个结果是否同时成立：

1. **现象成立：**视觉事件的未来回答价值与 salience、surprise、通用语义覆盖显著不同，而且这种差异主要出现在 side information 不充分、跨模态冲突和多事件组合问题上。
2. **方法成立：**反事实条件效用监督在相同总字节预算下优于强 query-hidden writer，而不仅是优于均匀采样。
3. **稳健性成立：**层次化尾部风险训练能改善预先定义 shift family 的 worst-group/upper-tail regret，且平均性能损失受控。

最优先动作不是训练完整系统，而是先做一个两周内可否证的 phenomenon study。若条件价值 oracle 本身不能稳定击败 surprise 和通用压缩，立即停止 FQR-Mem 主线。

## 1. 相比原方案的系统性修改

| 原方案成分 | 主要问题 | v2 修改 |
|---|---|---|
| 用视觉特征减去文本重建特征得到 residual | 特征空间不保证可减；错误 caption 可能把真实视觉内容“解释掉” | 改为可靠度感知的**条件证据 codec**，显式分离索引 key、视觉 payload 和跨模态 disagreement |
| 用事件 leave-one-out 估计价值 | 完整枚举成本高；忽略多事件互补 | 用分层抽样的 coalition counterfactual，联合学习单事件边际价值和 bundle synergy |
| flat question-type Group DRO | 只覆盖组间变化，可能漏掉组内证据稀有度、延迟和 side 质量变化 | 改为层次 ambiguity set：题型为粗组，证据条件为子组，并优化 upper-tail regret |
| “对未来问题稳健”作为宽泛主张 | 任意未来分布泛化不可辨护 | 只对事先声明的 prior shift、组合 shift、side corruption、evidence delay/rarity、有限 domain shift 做主张 |
| 用平均 QA 验证 | 可被语言先验和猜测掩盖 | 核心指标改为 full-context answer regret、grounded evidence miss、worst-group 与 CVaR |
| 记忆槽位固定且同质 | 不同事件需要不同码率，槽数也不能公平表示资源 | 用总活动字节为硬预算，每个事件允许多码率 payload；同时报告持久字节和计算成本 |
| 只验证检索到记忆 | 无法证明模型真的使用正确证据 | 加 memory deletion、matched random deletion、evidence swap 和 side corruption 因果测试 |

## 2. 论文要回答的科学问题

### 2.1 核心问题

长视频视觉记忆的真正瓶颈可能不是“历史太长”，而是：系统在问题出现前不知道未来会需要哪一种视觉细节。通用显著性偏向大动作和场景变化；surprise 偏向不可预测内容；caption/ASR 偏向可语言化语义；但未来问题可能询问小物体状态、人物身份、数量、空间关系、短暂异常、跨时刻变化或视听冲突。

因此，记忆价值应被定义为：**在已给定 side information 和当前记忆后，保存该视觉证据能减少多少未来回答与取证损失**，而不是该事件自身多显著、多新颖或能被重建得多好。

### 2.2 可证伪假设

#### H0：条件价值现象

在视觉依赖问题上，按真实反事实未来 regret 排序的事件集合，在相同字节预算下优于 salience、surprise、semantic diversity 和通用 token compression。

若 oracle 层面都不成立，FQR-Mem 没有继续开发价值。

#### H1：条件互补性

给定 ASR/OCR/caption 后学习的视觉 payload，比无条件视觉压缩更高效；优势集中在四类样本：视觉独占、视听互补、跨模态冲突、side information 低可靠度。

#### H2：未来问题尾部稳健性

相较 ERM 和 flat Group DRO，层次化风险训练能降低预先定义 shift family 下的 worst-group 和 upper-tail grounded regret，而平均准确率下降不超过预注册容忍范围。

#### H3：组合证据价值

对需要两个或更多远距离事件的问题，加入 bundle synergy 监督后，完整证据集合召回率和 grounded QA 显著改善；单事件独立打分不足以恢复该收益。

#### H4：记忆的因果使用

删除 FQR-Mem 选中的正确证据应显著降低对应问题性能；删除相同数量、相同码率的随机记忆项影响更小；用外观相近但事实冲突的证据替换时，答案应可预测地变化。

## 3. 严格任务协议

### 3.1 Query-after-write 主设定

给定连续视频流：

$$
V_{1:T} = \{x_1, x_2, \ldots, x_T\},
$$

事件化模块将它因果地划分为：

$$
E_{1:N} = \{e_1, e_2, \ldots, e_N\}.
$$

与视频同步、且不依赖未来问题的 side information 记为：

$$
S_{1:N} = \{s_1, s_2, \ldots, s_N\},
$$

其中可包含原生 ASR、OCR、时间戳、低频 query-agnostic caption 和其他明确计费的结构化线索。

写入器在时刻 $i$ 只能访问：

$$
W_i: (e_{\le i}, S_{\le i}, M_{i-1}) \rightarrow M_i,
$$

并且严格不能访问测试问题 $q$。在视频已处理或在线查询时刻 $u$ 到达后，读取器才看到问题：

$$
\hat y, \hat E_q = R(q, S_{\le u}, M_u, C_u),
$$

其中 $C_u$ 是固定长度的最近窗口。评测在预先指定的 checkpoint 保存 snapshot；同一 checkpoint 的所有问题必须复用同一个冻结 snapshot，不能针对问题重新编码、改写或回看历史视频。

### 3.2 硬资源约束

主实验使用总活动视觉记忆字节约束：

$$
\operatorname{Bytes}(M_u) + \operatorname{Bytes}(C_u) \le B.
$$

side information 另设固定预算：

$$
\operatorname{Bytes}(S_{\le u}) \le B_S,
\qquad
B_{\mathrm{total}} = B + B_S.
$$

主比较在完全相同的 $S$ 和 $B_S$ 下扫描视觉预算 $B$，并额外给出以 $B_{\mathrm{total}}$ 为横轴的结果，防止方法通过无限文本记忆绕过视觉预算。

同时记录但不混入主硬约束的资源包括：

- side information 的持久字节；
- side information 生成 FLOPs 与时延；
- 每分钟写入计算；
- 读取 TTFT、总解码时延和峰值显存；
- 是否发生原视频 I/O。

主设定禁止 raw-video replay 或无限 cold store。允许回放原视频的版本单列为 `raw-access` 次要设定，与 LongVideo-R1、LongVT 等 agentic retrieval 方法比较。

### 3.3 Side information 的三级计费

为避免免费 caption 带来的不公平，至少报告三档：

1. `Native`：仅使用视频自带音轨转写、时间戳和可直接取得的 OCR。
2. `Generated-lite`：加入统一、低频、query-agnostic caption；完整计算与存储计费。
3. `Generated-rich`：加入对象轨迹、事件摘要或其他昂贵线索；只作为资源更宽松的扩展实验。

主结论应在 `Native` 和 `Generated-lite` 都成立；否则方案可能只是依赖昂贵文本预处理。

## 4. 目标函数：未来 grounded regret，而非通用信息量

### 4.1 单问题 regret

对问题 $q$，令使用完整视频的同一冻结 backbone 得到参考任务损失 $\ell_{\mathrm{full}}(q)$，使用冻结记忆得到 $\ell_M(q)$。若完整视频超过 backbone 上下文，则用固定的高预算 query-aware evidence oracle 作为参考；所有方法必须共享同一参考。答案 regret 定义为：

$$
r_{\mathrm{ans}}(q; M, S)
=
\left[
\ell_M(q; M, S) - \ell_{\mathrm{full}}(q; V, S)
\right]_+.
$$

若数据包含真实支持证据 $E_q^\star$，定义 evidence miss：

$$
r_{\mathrm{ev}}(q; M, S)
=
1 - \operatorname{GroundF1}(\hat E_q, E_q^\star).
$$

组合 regret 为：

$$
r(q; M, S)
=
r_{\mathrm{ans}}(q; M, S)
+
\rho\, r_{\mathrm{ev}}(q; M, S),
$$

其中 $\rho$ 在验证集预注册，主结果同时分开报告两个分量，避免权重掩盖失败。

完整视频参考不是绝对真值。若 backbone 在完整视频上也答错，样本仍可用于 grounding 或人工答案损失，但不应把错误 teacher 当作正确伪标签。

### 4.2 层次风险组

粗组 $g$ 描述问题能力，例如：

- identity/entity；
- action/event；
- spatial；
- temporal/order；
- count；
- state/change；
- causal/multi-hop；
- OCR/fine detail；
- audiovisual；
- cross-modal conflict。

每个粗组内部再用子组 $h$ 描述证据条件：

- `side-only sufficient`、`visual-only`、`multimodal complementary`、`cross-modal conflict`；
- 单事件或多事件；
- 证据跨度与到达延迟；
- 证据稀有度与持续时间；
- side information 可靠度；
- 视频域。

不直接对所有轴做笛卡尔积，以免产生大量空组。先按粗组训练，再在每个粗组内对实际有足够样本的证据子组做鲁棒优化。

### 4.3 层次 ambiguity set

总体目标写为：

$$
\min_{\theta}
\quad
(1-\eta)\,\mathbb E[r]
+
\eta
\max_{w \in \mathcal U_{\mathrm{inter}}}
\sum_g w_g
\max_{v_g \in \mathcal U_g}
\sum_h v_{h\mid g}
\left(
\mathbb E[r \mid g,h]
+
\kappa\,\operatorname{CVaR}_{\alpha}(r \mid g,h)
\right)
+
\lambda\,\mathcal C(M).
$$

$\mathcal U_{\mathrm{inter}}$ 控制粗组先验变化，$\mathcal U_g$ 控制组内证据条件变化；二者可用围绕经验分布的 capped simplex 或 $\chi^2$ 球实现。半径必须在测试前由验证 shift 选择，不能根据最终测试结果调整。

对损失的 upper-tail CVaR 使用标准形式：

$$
\operatorname{CVaR}_{\alpha}(r)
=
\min_{\tau}
\left[
\tau
+
\frac{1}{1-\alpha}
\mathbb E\left[(r-\tau)_+\right]
\right].
$$

这里的“未来稳健”只表示对上述 ambiguity set 的经验稳健性，不表示对任意未知题型或任意分布外问题的保证。

## 5. 记忆表示：可靠度感知的条件证据，而非特征相减

### 5.1 单个记忆项

每个事件的记忆项定义为：

$$
m_i = (k_i, z_i, d_i, \tau_i, p_i, a_i, c_i).
$$

各字段含义：

- $k_i$：小型语义索引 key，用于问题到达后的检索；
- $z_i$：视觉证据 payload，可选多个码率；
- $d_i$：视觉与 side information 的 disagreement/witness 表示；
- $\tau_i$：时间范围、持续时间和事件顺序；
- $p_i$：来源与变换 provenance，可追溯到原事件；
- $a_i$：ASR/OCR/caption 等 side channel 的可靠度向量；
- $c_i$：该项真实活动字节和读取成本。

语义 key 与视觉 payload 必须分开计费。key 可以对大量事件提供低成本可检索性，payload 只分配给条件视觉价值高的事件。

### 5.2 条件 codec

视觉编码 $h_v(e_i)$、side 编码 $h_s(s_i)$ 与可靠度 $a_i$ 共同产生 payload：

$$
z_i^{(b)}
=
Q_b\left(
E_{\mathrm{cond}}
\left(h_v(e_i), h_s(s_i), a_i\right)
\right),
$$

其中 $b$ 表示码率档位，$Q_b$ 是量化或 token bottleneck。关键约束是编码器不接收 query；训练时对一组问题求期望，只让 payload 学会保存 side information 尚未覆盖的证据。

建议的 codec 损失为：

$$
\mathcal L_{\mathrm{codec}}
=
\mathbb E_q\left[
\ell_{\mathrm{task}}(q; S, z_i)
+
\rho\,\ell_{\mathrm{ground}}(q; S, z_i)
\right]
+
\beta\,\operatorname{Bits}(z_i)
+
\gamma\,\mathcal L_{\mathrm{redundancy}}(z_i, S).
$$

$\mathcal L_{\mathrm{redundancy}}$ 只能抑制能够被**可靠** side channel 替代的内容。若 caption 与视觉冲突或置信度低，模型应通过 $d_i$ 和 $a_i$ 保留视觉 witness，而不能强制视觉表示向 caption 对齐。

### 5.3 多码率候选

对每个事件生成少量离散候选，例如 `key-only`、`low`、`medium`、`high`。writer 学习的是“事件—码率”联合选择，而非先选事件再统一压缩。这样可以用少量字节记录普通事件，以较高码率记录 OCR、小物体、计数和短暂状态变化。

## 6. 反事实效用监督

### 6.1 为什么不能只做 leave-one-out

完整 leave-one-out 要对每个事件、每个问题重复长视频推理，成本不可承受；更重要的是，单独删除一个事件无法区分替代证据与互补证据。FQR-Mem v2 使用分层采样 coalition。

对一个不含事件 $i$ 的候选记忆子集 $C$，定义事件边际价值：

$$
\Delta_i(q \mid C, S)
=
r(q; C, S)
-
r(q; C \cup \{i\}, S).
$$

对题型和证据条件分组后：

$$
u_i^{g,h}
=
\mathbb E_{q \sim P(\cdot \mid g,h),\, C}
\left[
\Delta_i(q \mid C, S)
\right].
$$

为了学习多事件互补，定义二阶 synergy：

$$
\sigma_{ij}(q \mid C)
=
\Delta_{\{i,j\}}(q \mid C)
-
\Delta_i(q \mid C)
-
\Delta_j(q \mid C).
$$

只对真实 grounding 邻接、同一实体跨时刻、或 teacher 检索到的候选对计算 $\sigma_{ij}$，避免二次组合爆炸。

### 6.2 标签生成策略

1. 根据真实 temporal grounding 或高召回 teacher 建立问题—事件候选图。
2. 对每个问题采样 `empty/recent-only/side-only/random/near-oracle` 等不同难度的 coalition。
3. 运行同一冻结 answerer，计算加入事件前后的答案与 grounding regret。
4. 按粗组和证据子组平衡抽样，避免大量容易的文本充分问题主导标签。
5. 将昂贵的反事实标签蒸馏到轻量 utility critic；在线写入只运行 critic，不运行多次 answerer。
6. 保存所有 teacher 版本、prompt、随机种子、coalition 和输出，防止伪标签不可复现。

### 6.3 防止训练期 query 泄漏

训练问题可以用于产生“什么证据将来有用”的监督，但不能作为 writer 的输入。必须实施三项自动检查：

- writer 的计算图和缓存 key 中不存在 question token 或 question embedding；
- 同一视频只生成一个 memory snapshot，随后服务该视频的全部问题；
- 在完全替换问题文本顺序、隐藏 question ID 后，snapshot 的字节哈希保持不变。

## 7. 固定预算在线 writer

### 7.1 Utility critic

critic 输入事件候选、当前 memory summary、side 可靠度、时间信息和码率，输出：

$$
\hat{\mathbf u}_i^{(b)}
=
\left\{
\hat u_i^{g,h,(b)}
\right\}_{g,h},
\qquad
\hat{\mathbf s}_i^{(b)}
=
\left\{
\hat s_i^{g,h,(b)}
\right\}_{g,h},
$$

其中 $\hat u$ 是预测边际 regret reduction，$\hat s$ 是 epistemic uncertainty。critic 同时预测与当前记忆的替代性和潜在 bundle partner。

### 7.2 鲁棒单位字节增益

由层次 DRO 产生的对抗权重记为 $\omega_{g,h}$。事件—码率候选的近似分数为：

$$
\operatorname{Score}(i,b \mid M)
=
\frac{
\sum_{g,h}
\omega_{g,h}
\left(
\hat u_i^{g,h,(b)}
+
\xi\,\hat s_i^{g,h,(b)}
\right)
+
\zeta\,\widehat{\operatorname{Syn}}(i,M)
-
\mu\,\operatorname{Red}(i,M)
}{c_i^{(b)}}.
$$

这里的 uncertainty bonus 用于给少见但可能关键的证据少量探索空间；其上限必须受控，避免把噪声当作新奇事件全部写入。

### 7.3 Admission、降码率与替换

当 memory 未满时，选择分数最高的非负候选写入。memory 已满时，联合考虑：

1. 新事件以何种码率进入；
2. 哪个旧项降码率；
3. 哪个旧项被删除；
4. 是否只写入 key、不写 payload；
5. 是否与已有事件形成需要共同保留的 bundle。

只有新 memory 的预测层次风险降低超过阈值 $\delta$ 才执行交换。阈值和最大写入频率用于避免 memory thrashing。

### 7.4 在线伪代码

```text
initialize fixed-byte memory M and recent window C

for each causal event e_i:
    s_i, reliability_i = build_query_agnostic_side_information(e_i)
    update_recent_window(C, e_i)
    candidates = conditional_codec(e_i, s_i, reliability_i, rate_levels)

    for candidate in candidates:
        utility, uncertainty = critic(candidate, M, s_i, reliability_i)
        robust_gain = hierarchical_gain_per_byte(
            utility, uncertainty, redundancy(candidate, M), synergy(candidate, M)
        )

    apply_best_feasible_admit_downgrade_or_swap(M, candidates, robust_gain)
    assert bytes(M) + bytes(C) <= total_budget

freeze M before any question is revealed

for each future question q:
    retrieved = query_aware_read(q, frozen=M, side_information=S)
    answer, evidence = grounded_answer(q, retrieved, S)
```

## 8. 读取器：问题可见，但不能补写历史

读取阶段允许使用 query，这是任务本身的必要条件。推荐分三步：

1. 用 $k_i$、时间和实体字段做高召回候选检索；
2. 用 query 对视觉 payload、disagreement 和 bundle edge 重排；
3. 输出答案的同时输出所用 memory item 与时间证据。

若读取器判断证据不足，主设定只能扩大对**冻结 memory** 的读取范围，不能回看被丢弃视频。`raw-access` 扩展设定可以重新访问原视频，但必须单列原视频 I/O 和时延。

## 9. FQR-Shift 评测协议

### 9.1 候选数据源

首轮不急于新建大 benchmark，而从有明确长程或 grounding 属性的数据中构造统一协议。候选池包括：

- 流式记忆：MementoBench、RIVER、StreamingBench/OVO-Bench；
- 远距离多证据：MMR-V；
- 场景级遗忘：SceneBench；
- 可验证证据：EG-VQA、VideoZeroBench、E-VQA/ST-Evidence；
- 跨日外部验证：EgoMonth。

这些是候选而非锁定清单。实验开始前需核验数据许可、可下载性、视频时长分布、原始帧可用性和问题泄漏风险。MVP 应选择至少三个互补来源，而不是堆叠大量近似 benchmark。

### 9.2 四类 side-sufficiency 分桶

每个问题根据人工证据、side-only baseline 和视觉消融结果分到：

1. `S-only`：仅 side information 足以稳定回答；
2. `V-only`：答案依赖 side 未表达的视觉内容；
3. `V+S`：需要视听/OCR/文本与视觉联合；
4. `Conflict`：side information 错误、不完整或与视觉冲突。

分桶器本身需要在人工标注子集上校准，不能只用同一个 teacher 自标自评。

### 9.3 五类预声明 shift

1. **Question-prior shift：**训练和测试题型支持相同，但先验权重反转或长尾组上升。
2. **Composition shift：**训练见过原子能力，测试出现新的能力组合，如身份 + 次序 + 状态变化。
3. **Side-quality shift：**ASR 噪声、OCR 缺失、caption 过度概括或自然跨模态冲突比例变化。
4. **Evidence shift：**关键证据更短、更稀有、离问题更远，或需要更多分散事件。
5. **Finite domain shift：**在预先选择的有限视频域间迁移；不声称开放世界任意域泛化。

主表分别报告单轴 shift；组合 shift 用于压力测试。所有 shift 生成规则和 ambiguity radius 在测试前冻结。

### 9.4 数据切分与污染控制

- 按原视频、来源/uploader 和近重复内容切分，不能按 QA 行随机切分；
- 同一事件的改写问题只能处于同一 split；
- 测试 composition 不得以完整模板出现在训练集；
- side corruption 的随机种子与强度写入配置；
- 对闭源 caption/teacher 记录模型版本和日期；
- 训练 writer 时可使用训练问题产生监督，但测试问题只能在 snapshot 冻结后释放。

## 10. 基线与公平比较

### 10.1 Query-hidden 公平主基线

所有方法写入时都看不到测试问题：

- `No-memory / side-only`；
- uniform、recent-only、reservoir sampling；
- salience、motion、semantic diversity；
- SURGE-style surprise；
- StreamingVLM-style recent vision + long text；
- VideoChat-Flash、FlashVID、CRAFT、ForestPrune 类通用 token compression；
- FlexMem、FluxMem、MuKV 类 KV/层次视觉记忆；
- Memento、SelectStream、CausalMem 类流式 memory bank；
- MemoryCard 类 event gist + representative moments。

若官方实现或兼容 backbone 不可用，应区分“官方复现”“移植实现”“概念等价基线”，不能混写。

### 10.2 Query-known 特权 oracle

以下方法在选择时知道问题，不属于公平主基线，但能量化未知问题造成的代价：

- QViC-MF；
- MARC；
- Query-Conditioned Evidential Keyframe Sampling；
- GCR、EcoFrame、EviSelect、ReMem；
- LongVideo-R1、LongVT；
- 使用真实 temporal evidence 的 oracle selector。

### 10.3 上界与下界

- `Full-context same backbone`：完整视频上界；
- `Ground-truth evidence`：只提供真实证据片段的取证上界；
- `Side-only`：条件视觉增益的零点；
- `Random memory`：检验记忆容量本身而非选择策略；
- `Query-aware raw-access`：允许回放原视频的系统上界。

### 10.4 公平条件

主比较固定：backbone、视觉编码分辨率、事件候选池、side information、总活动字节、最近窗口、最大写入计算和读取候选上限。若某方法只能按 token 计费，必须换算实际 dtype 下的字节，并同时给出 token 数。

## 11. 指标与统计检验

### 11.1 任务质量

- 平均 QA accuracy 或开放式任务得分；
- 各粗组与子组 accuracy；
- worst-group accuracy；
- full-context answer regret；
- temporal/spatial GroundF1；
- 完整 evidence bundle recall；
- upper-tail regret 的 $\operatorname{CVaR}_{0.9}$ 和 $\operatorname{CVaR}_{0.95}$。

### 11.2 记忆效率

条件价值密度定义为：

$$
\operatorname{CVD}(M)
=
\frac{
\mathcal L(S) - \mathcal L(M,S)
}{
\operatorname{Bytes}(M)
},
$$

即每个活动字节相对于 side-only 减少的任务损失。还应报告：

- budget–performance 曲线与 AUC；
- 距 query-aware evidence oracle 的 gap closure；
- 每分钟写入 FLOPs、墙钟时延和显存；
- 读取 TTFT 与总时延；
- side information 成本；
- 原视频读取字节数，主设定应为零。

### 11.3 记忆因果性

- 删除 top-utility memory；
- 删除相同数量和码率的随机 memory；
- 删除真实 supporting memory；
- 以相似外观但事实冲突的 memory 替换；
- 打乱时间戳、实体链接或 bundle edge；
- corruption side information 后观察 disagreement payload 是否补偿。

### 11.4 统计方案

- 以**视频**而不是 QA 行为重采样单位，避免同视频问题相关性造成虚假显著；
- 训练模块至少 3 个独立种子；
- 主指标报告 95% paired bootstrap 置信区间；
- 分类答案可补充 paired permutation 或 McNemar 检验；
- 多 benchmark/多组比较采用预声明主终点，并对次要比较做 Holm 校正；
- LLM judge 只用于无法自动评分的开放答案，并在人工子集上报告一致性。

建议唯一主终点为：**matched active bytes 下，预声明 shift 的 worst-group grounded regret**。

## 12. 决定性消融

| 消融 | 要回答的问题 |
|---|---|
| 无 side information | 优势是否只是一般视觉压缩？ |
| 无条件 codec vs 条件 codec | 条件表示本身是否有效？ |
| 直接 feature subtraction vs conditional codec | 原 residual 假设是否错误？ |
| 移除 reliability $a_i$ | caption/ASR 错误时是否会误删视觉真相？ |
| 移除 disagreement $d_i$ | 跨模态冲突组的收益来自哪里？ |
| surprise/salience 标签替代反事实标签 | 反事实监督是否真正必要？ |
| leave-one-out vs sampled coalition | coalition 是否提高标签质量/成本比？ |
| 移除 synergy | 多事件问题是否退化？ |
| ERM vs flat Group DRO vs hierarchical DRO | 稳健收益来自哪里？ |
| 平均风险 vs CVaR | 上尾优化是否只牺牲平均性能？ |
| 固定槽位 vs 固定字节、多码率 | 资源分配是否需要码率自适应？ |
| 无最近窗口 | 长期 memory 是否被近期视觉掩盖？ |
| 冻结 reader vs 联合训练 reader | 收益是否依赖特定 decoder 适配？ |
| snapshot 哈希泄漏测试 | writer 是否偷看了问题？ |

## 13. 分阶段开发与止损门槛

所有数值是**测试前的候选预注册阈值**，不是已有结果。正式阈值应在 pilot 后、主测试前冻结。

### Gate A：现象验证，1–2 周

建立小规模 grounded 子集和 oracle event utility，不训练完整 writer。

继续条件：

- 在至少 2 个互补数据源上，conditional oracle 相对最强 query-hidden generic/surprise selector 的 visual-dependent worst-group 提升至少 3 个绝对点；
- paired 95% CI 下界大于 0；
- 优势不是只来自一个题型或单一 side corruption。

否则：停止 FQR-Mem，转向更基础的视觉证据 benchmark 或读阶段 sufficiency 研究。

### Gate B：条件 codec，3–4 周

继续条件：

- 在相同活动字节下，conditional codec 显著优于无条件 codec；
- 在 `Conflict` 组不因 caption 错误而系统性退化；
- 相对 query-aware raw evidence oracle 的差距至少关闭 40%，且比通用压缩高 10 个百分点以上。

否则：保留研究发现，但不进入鲁棒 writer。

### Gate C：utility critic，5–6 周

继续条件：

- held-out 视频上，critic 的 event ranking 明显优于 surprise/salience；
- top-budget evidence recall 至少提高 10% 相对值；
- coalition distillation 的标签成本可接受，且 bundle 任务有可测 synergy。

### Gate D：鲁棒 writer，7–9 周

继续条件：

- 相对 ERM writer，预声明 shift 的 worst-group accuracy 提高至少 2 个绝对点或 worst-group regret 相对下降至少 10%；
- 平均 accuracy 损失不超过 1 个绝对点；
- 至少两个不同 shift 轴上成立，而非只拟合一个人工 corruption。

### Gate E：论文级证据，10–12 周

继续投稿条件：

- 击败至少一个 2026 强 query-hidden memory 方法和一个强通用 compression 方法；
- memory deletion/swap 证明模型使用了正确证据；
- 两个 backbone 尺度或两个架构族上趋势一致；
- 成本表完整，不依赖免费 caption 或隐藏 raw-video replay。

## 14. 建议的 12 周路线图

| 周 | 目标 | 主要产物 |
|---:|---|---|
| 1 | 统一 query-after-write harness、事件单位、side 成本 | `EXP-YYYYMMDD-fqr-phenomenon/README.md` 与冻结协议 |
| 2 | oracle conditional value vs surprise/salience | phenomenon 报告、Gate A 决策 |
| 3–4 | 可靠度感知 conditional codec、多码率 | codec 曲线、Conflict 分析、Gate B 决策 |
| 5 | sampled coalition 标签生成 | 可复现 teacher cache 与成本分析 |
| 6 | utility critic 与 ranking eval | held-out ranking、evidence recall、Gate C 决策 |
| 7 | 固定字节 admission/swap writer | 单分布 matched-budget 结果 |
| 8 | flat/层次 DRO 与 CVaR | shift validation、超参数冻结 |
| 9 | 三类主数据源完整运行 | 主表初版、Gate D 决策 |
| 10 | 强基线、query-aware oracle、第二 backbone | 公平性与泛化表 |
| 11 | 消融、因果使用和统计检验 | 全部关键图表与失败案例 |
| 12 | 论文叙事、复现实验审计 | 投稿草稿、reproducibility checklist、Gate E 决策 |

模型、数据集和具体预算值暂不锁定。MVP 优先选可冻结的开放 3B/7B 级视频 backbone、三个互补数据源和 3–4 个实际字节预算点；在 Gate A 前不进行大规模端到端训练。

## 15. 最小可发表单元与完整版

### 15.1 最小可发表单元

如果资源有限，最小论文应包含：

1. 严格 query-after-write 协议；
2. 条件未来价值现象与反事实标签；
3. 固定字节 utility writer；
4. 至少三种 shift 与 grounded regret；
5. 与 surprise、CausalMem/SelectStream 类 memory、通用 compression 和 query-aware oracle 对比；
6. 因果 memory-use 验证。

conditional codec 可先使用简单 bottleneck，synergy 只处理真实 evidence pair。不要在第一版同时承担新 backbone、新 benchmark、新 RL 算法和新 memory architecture。

### 15.2 完整版

完整版再加入：

- 可靠度与 disagreement 通道；
- 多码率 payload；
- bundle synergy 图；
- 层次 ambiguity set；
- 多日视频外部验证；
- raw-access 扩展设定。

## 16. 预期论文贡献

如果实验支持假设，可以形成四项清晰贡献：

1. **问题定义：**首次系统隔离 query-after-write 固定预算视觉记忆，并把 side information、原视频回放和总资源计费写成严格协议。
2. **科学发现：**证明事件的未来条件证据价值不同于 surprise、显著性和通用语义覆盖，并定位差异出现的证据条件。
3. **方法：**用 sampled coalition counterfactual 学习条件视觉 payload 与单位字节效用，并以层次化 upper-tail regret 驱动在线写入。
4. **验证：**用 grounded regret、预声明 shift 和 memory intervention 证明系统保存并实际使用了对长尾未来问题有用的视觉证据。

ICLR 叙事更适合强调：条件信息价值、反事实监督、ambiguity set 与平均—尾部风险规律。CVPR 叙事更适合强调：视觉证据表示、长视频 grounding、固定预算系统和充分的视觉实验。最终投稿方向应由 Gate A–D 的结果决定，而不是现在锁定。

## 17. 主要审稿风险与预先回答

### 风险 1：“这只是 CausalMem/SelectStream 加 Group DRO”

回答必须来自实验而非措辞：在同一 writer 架构上，只替换 surprise/semantic information 标签为 conditional counterfactual utility；再只替换 ERM 为 hierarchical risk。若两步各自有独立收益，贡献才成立。

### 风险 2：“未来问题稳健性是假命题”

不声称任意未来泛化；明确给出可复现 shift family、ambiguity radius 和失败边界，并报告支持扩张到新原子题型时的性能崩溃。

### 风险 3：“训练问题已经泄漏给 writer”

训练问题只产生监督；测试时每个视频只有一个预问题 snapshot，hash 不受问题顺序和内容影响。所有 query-known 方法单列 oracle。

### 风险 4：“收益来自 caption/teacher 规模”

报告 `Native` 和 `Generated-lite` 两档；所有方法共享 side information；做 caption corruption 和小规模人工标注校准；完整列出 teacher 成本。

### 风险 5：“反事实标签太贵、不可扩展”

报告每小时视频的 teacher 调用数、coalition 数与总 GPU 时间；对比 leave-one-out；展示标签子采样曲线和 critic 蒸馏后的在线成本。

### 风险 6：“答案提升不代表视觉记忆”

以 grounded evidence 为主终点之一，并做删除、替换、时间打乱、side 冲突测试；若答案不随正确视觉证据干预变化，就不能声称视觉记忆成功。

### 风险 7：“只在人工 shift 上有效”

同时使用自然组差异（真实 ASR/OCR 质量、真实长延迟、多事件、跨域）与受控 corruption；主结论至少包含一种自然 shift。

## 18. 最终建议

建议立刻推进 Gate A，而不是先实现完整 FQR-Mem。第一阶段只需回答一个决定性问题：

> 在相同视觉字节预算下，知道 side information 后由未来 grounded regret 定义的 oracle 选择，是否稳定优于 surprise、通用语义覆盖和强 query-agnostic compression？

若答案是肯定的，FQR-Mem v2 具备清楚的科学现象、直接的 2026 竞争差异和完整的论文路径；若答案是否定的，应尽早终止，避免把数月资源投入一个只在叙事上成立的“视觉 residual memory”。
