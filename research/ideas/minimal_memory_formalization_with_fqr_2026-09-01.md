# 记忆不是一种结构：AI 记忆的最小形式化与 FQR-Mem 实例

> 日期：2026-09-01
> 文档性质：独立重思报告，不替代也不修改旧版潜记忆报告
> 与现有方案的关系：保留 [FQR-Mem v2](./fqr_mem_optimized_proposal_2026-08-24.md) 的任务协议和方法主线，只增加一层最小形式化
> 核心边界：本文不要求潜记忆、世界模型、图记忆、固定槽位或某一种模型接口

## 0. 最终判断

你的出发点是对的：当前很多记忆工作直接设计槽位、摘要、检索器或更新规则，却没有先回答“有限记忆究竟应该保留什么”。但原始想法里有三个需要修正的地方：

1. **重建不是记忆的普适定义，而是一种任务选择。**重建像素、重建过去的世界状态、预测未来和回答过去事件问题，要求保存的信息并不相同。
2. **“完美规律下只需状态”只在很强的条件下成立。**如果环境部分可观、随机、不可逆、规律未知或任务询问过去，当前状态都不充分。
3. **面向模型的“投射”不应先被固化为一个新模块。**更干净的做法是限制允许使用记忆的模型与接口，由此直接定义“对该模型可用的记忆”。投射后的 token 可以变多，但没有因此产生新的历史信息。

对原始想法的简要裁决如下：

| 原始判断 | 裁决 | 最小修正 |
|---|---|---|
| 完整记忆应支持重建 | 部分接纳 | 把“重建什么”写成任务族；不默认像素重建 |
| 完美规律下只需状态 | 有条件接纳 | 仅对完全可观、Markov、已知规律且面向现在/未来的任务成立 |
| 记忆需投射给具体模型 | 接纳问题，修改实现 | 定义模型与接口受限的操作风险，不预设 compiler |
| 任务先验可大幅压缩 | 接纳并作为核心 | 由任务分布或 ambiguity set 定义失真 |
| 取回与推理耦合 | 接纳 | 表示为有成本的顺序信息获取 |
| 旧记忆也不可完全观测 | 不作为普适假设 | 仅在随机访问昂贵时加入 write-side read budget |
| 潜记忆是核心载体 | 不接纳为前提 | latent 只作为一种可替换 codec |

建议采用下面的一句话定义：

> **记忆是一个受资源约束的因果策略：它把历史压缩成持久状态，并在任务到来后选择性地向指定推理模型暴露信息，使任务损失尽可能小。**

这个定义有三个层次：

| 层次 | 核心问题 | 不依赖的东西 | FQR-Mem 中的对应物 |
|---|---|---|---|
| 语义充分性 | 哪些历史差异必须保留？ | 具体存储格式 | 未来 grounded task family |
| 操作可用性 | 指定模型能否在有限接口下利用这些差异？ | “必须有编译器”的假设 | 冻结 answerer、读取器与输入预算 |
| 因果可维护性 | 查询未知时能否在线保留这些差异？ | 离线看完整视频的特权 | query-after-write writer |

因此，最合理的结合方式不是把 FQR-Mem 改造成“潜记忆系统”，而是：

> **把 FQR-Mem 定位为“未来查询未知、任务分布不确定、消费者受限”的因果视觉率失真问题的一个可训练实例。**

形式化负责定义问题、上界、下界和失败类型；FQR 负责在这个问题中近似“每个视觉证据的未来条件价值”。

---

## 1. 对原始思想逐条检验

### 1.1 “最完整的记忆应该支持重建”

这个说法可以作为一个上界，但不能作为唯一的记忆定义。

需要先区分四种“重建”：

| 目标 | 需要保留什么 | 当前状态是否通常足够 |
|---|---|---:|
| 精确重建传感器输入 | 场景、视角、噪声和全部不可逆细节 | 否 |
| 重建过去的世界状态 | 每次不可逆变化或随机创新 | 否 |
| 预测未来状态分布 | 当前预测状态、规律及不确定性 | 有条件地是 |
| 回答指定任务 | 只保留改变任务答案或决策的差异 | 通常不确定 |

例如，两段视频最后都停在“杯子在桌上”，但一段中 A 放下杯子，另一段中 B 放下杯子。它们有相同终态，却对“谁放下杯子”给出不同答案。任何只保存终态的记忆都必然失败。

更强的反例是随机和不可逆过程。即使解码器完全知道动力学规律，也无法仅从当前状态反推出已经丢失的随机结果。完美规律只能免除“重复存储固定规律”，不能免除保存该次经历中的随机创新。

因此，重建应该被写成一个任务族，而不是记忆的先验本体：

- 如果任务族包含所有像素查询，得到接近无损视频编码的问题；
- 如果任务族只包含未来预测，得到预测状态或 belief state；
- 如果任务族包含过去事件查询，必须保留 episodic innovations；
- 如果任务族是下游 QA，记忆只需保留会改变答案与证据的历史差异。

### 1.2 “完美世界模型编码出的记忆应该只有状态”

这句话有两个版本。

弱版本是正确但近乎同义反复的：如果把“状态”定义成“对全部目标任务充分的最小历史统计量”，那么完美记忆当然是状态。

强版本——“当前物理状态足够替代历史”——需要同时满足：

1. 环境对目标任务是 Markov 的；
2. 当前状态完全可观；
3. 动力学固定且已被解码器掌握；
4. 任务只关心现在或未来；
5. 若要求精确未来，未来没有未编码的随机性；
6. 若要求重建过去，动力学还必须可逆。

现实视频通常至少违反其中两项。部分可观环境更适合用 belief state 或 predictive state，而不是单一物理状态。因果状态工作也把状态定义为对未来预测等价的历史划分，而不是直接假设一帧就是状态（[Zhang et al., 2019](https://arxiv.org/abs/1906.10437)）。

结论是：**状态不是预设的数据结构，而是相对于任务族定义出来的历史等价类。**

### 1.3 “完美记忆还要投射到具体模型的输入空间”

这个观察抓住了一个真实问题：信息“存在于存储中”和模型“能够利用它”不是一回事。

但不建议把它直接物化为一个必需的 memory compiler，原因有三点：

1. 编译器、检索器、解压器和提示构造器的边界取决于实现，难以形成稳定定义；
2. 一个强模型和一个弱模型面对同一存储会有不同性能，问题来自允许的 decoder family，而不只是模态转换；
3. 接口变长只表示编码冗余增加，不表示历史信息增加。

更简洁的处理是同时定义两个风险：

$$
\mathcal{L}_{\mathrm{sem}}(M)
=
\inf_g
\mathbb{E}\!\left[\ell\bigl(Y,g(M,Q,S)\bigr)\right],
$$

其中 $g$ 可以是任意足够强的解码器；以及

$$
\mathcal{L}_{\mathrm{op}}(M;\theta,\mathcal{A})
=
\inf_{A\in\mathcal{A}}
\mathbb{E}\!\left[
\ell\bigl(Y,F_\theta(Q,S,A(M,Q,S))\bigr)
\right],
$$

其中 $F_\theta$ 是指定模型，$\mathcal{A}$ 是允许的读取与接口机制。

二者的差

$$
G_{\mathrm{use}}
=
\mathcal{L}_{\mathrm{op}}-
\mathcal{L}_{\mathrm{sem}}
$$

就是**可用性缺口**。这直接表达了你的“模型相关投射”，但不要求提前决定投射是文本、视觉 token、KV、latent 还是工具调用。Decodable Information Bottleneck 已经说明，表示的充分性和最优性会随可用预测器族改变（[Dubois et al., 2020](https://proceedings.neurips.cc/paper/2020/hash/d8ea5f53c1b1eb087ac2e356253395d8-Abstract.html)）。

如果读取结果 $Z$ 只由 $M$、查询和 side information 生成，那么数据处理不等式给出：

$$
I(H;Z\mid Q,S)
\leq
I(H;M\mid Q,S).
$$

所以“投射”可以把 1 KB 的存储解压成 4 KB token，却不能凭空补回已被写入器删除的历史事实。模型自身知识可以补充世界常识，但不能可靠恢复该视频中特有的随机事件。

### 1.4 “任务先验会极大降低记忆容量”

这个判断成立，而且应该成为形式化的中心。

Information Bottleneck 的基本思想就是保存与目标有关的信息，而非输入的全部信息（[Tishby et al., 2000](https://arxiv.org/abs/physics/0004057)）。任务语义与 side information 共同进入率失真目标，也有直接的信息论先例（[Guo et al., 2022](https://arxiv.org/abs/2208.06094)）。

但需要接受一个后果：一旦任务先验改变编码，所得记忆就不再是“普适完美记忆”，而是**任务相对的最优记忆**。

不建议真的执行“先构造世界完美记忆，再按任务压缩，再投射给模型”这三个昂贵阶段。正确用法是：

- 把世界完整记忆当作理论 oracle；
- 把任务充分记忆当作信息上界；
- 直接训练受资源约束的任务相对 writer；
- 用 oracle gap 判断丢失发生在哪一层。

### 1.5 “取回与推理深度耦合”

这个判断成立，但它描述的是**顺序信息获取**，不要求记忆本体是图或扩散场。

推理第 $k$ 步根据问题、已有证据和中间结论选择下一次读取动作：

$$
a_k
\sim
\pi_k(\cdot\mid Q,S,r_{k-1},Z_{<k}),
$$

$$
Z_k
\sim
R_k(\cdot\mid M,a_k),
\qquad
r_k
=
U_\theta(r_{k-1},Z_k).
$$

$Z_k$ 就是“根据当前线索对记忆做选择性编码”的结果；随后它通过合法接口被目标模型吸收。一次性检索只是 $K=1$ 的特例。

理想停止规则比较下一次读取的期望价值与成本：

$$
\operatorname{VOI}_k
=
\mathbb{E}\!\left[
\mathcal{L}(r_{k-1})-\mathcal{L}(r_k)
\mid \mathcal{I}_{k-1}
\right].
$$

当 $\operatorname{VOI}_k$ 不大于一次读取的价格时停止。现实中真实损失在推理时未知，因此需要学习一个 value-of-information critic。2026 年的 DeepControl 也从“继续检索与检索粒度”两个维度控制推理期信息获取，说明这个方向成立，但它研究的是搜索增强推理，不是持久视频记忆（[Xiong et al., 2026](https://arxiv.org/abs/2602.01672)）。

### 1.6 “流式更新时，旧记忆也不是完全可观”

这不是记忆问题的普遍事实，而是一个可选的系统约束。

在逻辑层，writer 可以直接访问整个 $M_{t-1}$：

$$
M_t
\sim
W_t(\cdot\mid M_{t-1},O_t,S_t).
$$

如果记忆过大、分布式存放或随机访问昂贵，才需要先读取旧记忆：

$$
\widetilde M_{t-1}
\sim
R^{\mathrm{write}}(\cdot\mid M_{t-1};B_{\mathrm{wr}}),
$$

$$
M_t
\sim
W_t(\cdot\mid \widetilde M_{t-1},O_t,S_t).
$$

这里的“不完全可观”是**访问预算造成的操作性不可观**，不是记忆在认识论上神秘地隐藏了自己。FQR-Mem 第一版不应强制加入该限制；只有当实际存储大到无法扫描，或实验显示 writer 访问成本主导时，再把 $B_{\mathrm{wr}}$ 加入主协议。

---

## 2. 最小形式化

### 2.1 基本对象

令：

- $H_t=(O_{1:t},A_{1:t-1})$：时刻 $t$ 的完整交互历史；纯视频时可以省略动作；
- $S_t$：无需从视觉记忆重复保存的 side information，如时间戳、ASR、OCR；
- $T=(Q,Y,\ell)$：一个任务，包括问题、目标和损失；
- $P_T$：未来任务分布；
- $\mathcal{U}$：允许的任务与证据分布集合，用于描述未知未来和 shift；
- $M_t$：持久记忆；
- $W$：查询不可见的因果 writer；
- $R,\pi$：查询可见的读取通道和读取策略；
- $F_\theta$：实际消费记忆的模型；
- $\mathbf B$：存储、写入、读取、接口与计算预算。

这套定义故意不规定 $M_t$ 的类型。它可以是帧、文本、事件表、latent、KV、参数、混合索引，甚至可执行程序。

### 2.2 记忆的充分性

对任务族 $\mathcal T$，若对每个 $T\in\mathcal T$ 都有

$$
P(Y\mid H,Q,S)
=
P(Y\mid M,Q,S),
$$

则称 $M$ 在 side information $S$ 下对 $\mathcal T$ **精确充分**。等价地，

$$
Y\perp H\mid M,Q,S.
$$

这一定义给出一个非常直接的“记忆是什么”：记忆必须保留所有会改变目标条件分布的历史差异，其余差异允许遗忘。

可以进一步定义历史等价关系：

$$
h\sim_{\mathcal T,S}h'
\quad\Longleftrightarrow\quad
P(Y\mid h,q,S)
=
P(Y\mid h',q,S),
\quad \forall q\in\operatorname{supp}(\mathcal T).
$$

最小的精确记忆就是这个等价类的编号。它不唯一：任何一一可逆的重编码都同样完美。因此，“完美记忆应该长成某种 latent”在数学上没有可辨识性依据。

### 2.3 近似充分性和率失真

现实任务允许误差。对任意历史压缩 $M=\phi(H,S)$，定义任务失真为相对完整历史 Bayes 风险的增加：

$$
D_{P_T}(M)
=
\inf_g
\mathbb E_{P_T}\!\left[\ell\bigl(Y,g(M,Q,S)\bigr)\right]
-
\inf_f
\mathbb E_{P_T}\!\left[\ell\bigl(Y,f(H,Q,S)\bigr)\right].
$$

于是理想的任务相对率失真函数可以写为：

$$
R_{\mathcal T}(D)
=
\inf_{\phi}
\mathbb E\!\left[L_{\mathrm{code}}(\phi(H,S))\right]
\quad
\text{s.t.}
\quad
D_{P_T}(\phi(H,S))\leq D.
$$

$L_{\mathrm{code}}$ 是实际可解码码长。互信息 $I(H;M\mid S)$ 可以作为信息论分析量或下界，但**不能直接当作磁盘字节、token 数或 KV 显存**。

### 2.4 “世界完整记忆”的正确位置

“世界完整”不是脱离任务的绝对概念。它应定义为一个故意放得很宽的任务族 $\mathcal T_{\mathrm{world}}$：

$$
M_{\mathrm{world}}
\text{ 对 }
\mathcal T_{\mathrm{world}}
\text{ 充分。}
$$

不同选择对应不同上界：

- 所有过去像素查询：传感器完整；
- 所有过去世界状态查询：轨迹完整；
- 所有未来可预测查询：预测完整；
- 所有可行动决策：决策完整。

因此不应该争论“哪一个才是真正完美”，而应显式写出任务族、可用规律、side information 和损失。形式化的价值正是把这些隐藏条件暴露出来。

### 2.5 模型相对的操作率失真

给定消费者 $F_\theta$ 和合法接口族 $\mathcal A$，定义：

$$
R_{\mathcal T,\theta,\mathcal A}^{\mathrm{op}}(D)
=
\inf_{W,R,A\in\mathcal A}
C_{\mathrm{store}}(M)
$$

满足

$$
\mathcal L_{\mathrm{op}}(M;\theta,\mathcal A)
-
\mathcal L_{\mathrm{ref}}(H;\theta)
\leq D.
$$

这就是你的“同一完美记忆面对不同语言模型，需要不同使用形式”的严格版本。不同模型对应不同的操作前沿，而不是不同的真相。

如果长期存储要跨模型升级，应把消费者设为集合 $\Theta$，优化最坏情况或平均情况：

$$
\sup_{\theta\in\Theta}
\mathcal L_{\mathrm{op}}(M;\theta,\mathcal A_\theta).
$$

但这会增加容量需求。FQR-Mem 初期只需用两个不同能力的冻结消费者测量迁移，不必为每个模型持久保存一份“编译后记忆”。

### 2.6 因果写入与查询隐藏

长视频记忆的关键不是一般压缩，而是：写入时不能看到未来帧和未来问题。

$$
M_t
\sim
W_t(\cdot\mid M_{t-1},O_t,S_t;\mathcal U).
$$

$W_t$ 可以知道训练期任务分布或 ambiguity set $\mathcal U$，但不能接收测试问题 $Q$。对同一视频和 side information，换一个事后问题不应改变已经冻结的 memory snapshot。

这与非前瞻率失真的因果约束一致：编码器只能依赖当前和过去，不能预见未来（[Kourtellaris et al., 2013](https://arxiv.org/abs/1304.6528)）。

### 2.7 顺序读取

读取阶段允许问题可见，并允许推理状态改变下一次读取：

$$
r_0=\operatorname{Init}_\theta(Q,S),
$$

$$
a_k\sim\pi_k(\cdot\mid Q,S,r_{k-1},Z_{<k}),
$$

$$
Z_k\sim R_k(\cdot\mid M,a_k),
$$

$$
r_k=U_\theta(r_{k-1},Z_k),
\qquad
\widehat Y=G_\theta(r_K).
$$

这套形式同时覆盖：

- 一次检索：$K=1$；
- coarse-to-fine：先事件索引，再高码率证据；
- 多跳：上一步实体成为下一步地址；
- 反证检索：根据当前假设主动找冲突证据；
- 自适应停止：边际信息价值不足时结束。

它不要求“在 latent 空间扩散”。扩散、图遍历、向量搜索或数据库查询只是 $\pi$ 与 $R$ 的候选参数化。

### 2.8 多资源前沿

单独报告“memory token 数”会把不同成本混在一起。至少需要区分：

$$
\mathbf B
=
(B_{\mathrm{store}},
B_{\mathrm{write}},
B_{\mathrm{read}},
B_{\mathrm{interface}},
B_{\mathrm{compute}}).
$$

- $B_{\mathrm{store}}$：持久保存的活动字节；
- $B_{\mathrm{write}}$：流式编码时间、显存或 FLOPs；
- $B_{\mathrm{read}}$：从持久记忆读取的总字节；
- $B_{\mathrm{interface}}$：真正送入消费者的 token、视觉 token 或 KV；
- $B_{\mathrm{compute}}$：读取轮数及推理计算。

“投射放大”表现为 $B_{\mathrm{interface}}/B_{\mathrm{store}}$ 较大，而不是宣称记忆信息量增加。

---

## 3. 统一优化问题

令完整系统为

$$
\Gamma=(W,R,\pi,A,F_\theta).
$$

对任务与证据分布 $P\in\mathcal U$，定义 grounded regret：

$$
\operatorname{Reg}_{P}(\Gamma)
=
\mathbb E_P\!\left[
\ell_{\mathrm{ans}}(Y,\widehat Y)
+
\rho\,\ell_{\mathrm{ground}}(E,\widehat E)
\right]
-
\mathcal L^{\mathrm{ref}}_{P}.
$$

其中 $\mathcal L^{\mathrm{ref}}_{P}$ 必须明确是哪一种参考：

- Bayes oracle：测量理论信息损失；
- 完整历史加同一消费者：测量存储和读取造成的系统损失；
- 高预算 query-aware evidence oracle：用于完整视频无法直接输入模型时。

FQR-Mem 对应的总问题是：

$$
\Gamma^*(\mathbf B)
\in
\arg\min_{\Gamma}
\sup_{P\in\mathcal U}
\operatorname{Reg}_{P}(\Gamma)
$$

满足

$$
M_t
\sim
W_t(M_{t-1},O_t,S_t),
$$

以及

$$
C_j(\Gamma)
\leq
B_j,
\qquad
j\in
\{\mathrm{store},\mathrm{write},\mathrm{read},\mathrm{interface},\mathrm{compute}\}.
$$

这一个式子已经容纳了原始想法中真正必要的因素：

- 任务通过 $\mathcal U$ 和损失决定什么值得记；
- 世界知识和 side information 通过 $F_\theta$、$S$ 决定什么无需重复记；
- 模型差异通过 $F_\theta$ 与 $\mathcal A$ 决定什么可被使用；
- 迭代取回通过 $R$、$\pi$ 和读取轮数决定；
- 流式性通过 writer 的因果分解决定；
- 旧记忆访问限制在需要时作为 $B_{\mathrm{wr}}$ 增加。

形式化之后，所谓 frame memory、latent memory、KV compression、summary memory、event graph 都只是同一可行域中的不同 $\Gamma$，可以在相同约束下比较。

---

## 4. 形式化立即暴露出的五个规律

这些结论主要是定义的直接推论。它们适合作为 sanity check 和理论起点，但单独不足以构成顶会理论贡献。

### 4.1 任务族越宽，最小所需容量不会更小

若 $\mathcal T_1\subseteq\mathcal T_2$，则在相同失真阈值下：

$$
R_{\mathcal T_1}(D)
\leq
R_{\mathcal T_2}(D).
$$

这严格表达了“任务先验减少容量”。同时也说明不存在脱离任务范围的唯一最小记忆。

### 4.2 更强的消费者族不会需要更多最优容量

若允许的消费者与接口族满足 $\mathcal F_1\subseteq\mathcal F_2$，则：

$$
R^{\mathrm{op}}_{\mathcal T,\mathcal F_2}(D)
\leq
R^{\mathrm{op}}_{\mathcal T,\mathcal F_1}(D).
$$

强模型可以模拟弱模型，所以其最优前沿不会更差。实践中如果更强模型反而更差，原因应是训练、接口或优化失败，而不是信息论必然性。

### 4.3 查询后编码严格支配查询前编码

查询可见 writer 的策略集合包含查询隐藏 writer，所以：

$$
D^*_{\mathrm{post\text{-}query}}(B)
\leq
D^*_{\mathrm{pre\text{-}query}}(B).
$$

而且不等式可以严格成立。考虑历史包含两个独立比特 $(X_1,X_2)$，记忆只能保存一比特，查询均匀询问其中一个：

- 查询后编码只保存被询问的比特，错误率为 $0$；
- 查询前编码必须在不知道问题时写入，最优平均错误率为 $1/4$。

这个“pre-query premium”是 FQR-Mem 最值得正式研究的理论量，而不是泛化地再定义一次记忆。

### 4.4 只存当前状态不可能回答一般过去问题

若存在 $h\neq h'$ 满足同一当前状态 $x_t(h)=x_t(h')$，但某个任务有

$$
P(Y\mid h,q)
\neq
P(Y\mid h',q),
$$

那么任何 $M=f(x_t)$ 都无法对该任务精确充分。这给出了“状态记忆”失败的最小反例，不依赖网络结构。

### 4.5 多轮读取的最优值不会更差，但学习结果可能更差

在总读取和计算预算相同、允许跳过多余轮次时，$K$ 轮策略包含 $K-1$ 轮策略，因此最优损失不增：

$$
\mathcal L^*_{K}
\leq
\mathcal L^*_{K-1}.
$$

实际训练中，多轮系统可能因信用分配、错误累积和额外延迟而变差。因此实验必须匹配总读取字节和总计算，而不能只比较轮数。

---

## 5. 用 oracle ladder 解耦失败原因

各因素相互作用，不能声称总误差唯一地等于若干独立项之和。更可靠的方法是逐项替换为 oracle，观察前沿变化。

| 替换 | 比较 | 暴露的问题 |
|---|---|---|
| 完整历史 → oracle 最小任务记忆 | 保留无限强 decoder | 任务本身可压缩多少 |
| oracle 记忆 → 实际因果 writer | 保留 oracle reader | 写入与遗忘是否正确 |
| oracle reader → 有限读取器 | 保留同一存储 | 证据是否在、但没有被找到 |
| unrestricted decoder → 指定模型 | 保留同一 read transcript | 信息是否存在、但模型不会用 |
| gold evidence → 实际推理 | 保留相同消费者 | 推理与答案头是否失败 |
| offline writer → causal writer | 匹配容量 | 流式约束的代价 |
| query-known writer → query-hidden writer | 匹配容量 | 未知未来问题的代价 |

建议固定术语：

- **保留缺口**：完整历史与实际 $M$ 的语义风险差；
- **访问缺口**：oracle full read 与实际读取器的差；
- **可用性缺口**：unrestricted decoder 与固定消费者的差；
- **推理缺口**：gold evidence 与实际答案的差；
- **因果缺口**：offline 与 causal writer 的差；
- **未来查询缺口**：query-known 与 query-hidden writer 的差。

这比给每类错误设计一个固定记忆子模块更有解释力，也更容易形成可证伪实验。

---

## 6. FQR-Mem 在框架中的准确位置

### 6.1 FQR 不是整个记忆理论，而是一个关键制度

FQR-Mem 选择了如下制度：

| 形式化变量 | FQR-Mem 的选择 |
|---|---|
| 历史 $H$ | 只能流式观看一次的超长视频 |
| 任务时序 | query-after-write |
| 任务知识 | 训练期知道问题族，不知道测试实例问题 |
| 不确定性 | 层次 ambiguity set 与预声明 shift |
| side information $S$ | ASR、OCR、时间戳、低频 query-agnostic 描述 |
| 主要失真 | answer regret + grounded evidence loss |
| 物理约束 | 固定活动字节、禁止原视频回放 |
| 消费者 | 冻结 VLM/LLM 与受限输入接口 |

因此更准确的定位是：

> **FQR-Mem 是 robust pre-query causal operational rate-distortion 在长视频 grounded QA 上的实例。**

### 6.2 最近工作的边界：DeMem

2026 年的 DeMem 已经明确把智能体记忆写成决策中心的率失真问题：记忆应保留会导致最优决策冲突的历史差异，并给出 memory-distortion frontier 和在线划分学习（[Zou et al., 2026](https://arxiv.org/abs/2605.10870)）。因此不能声称“首次用率失真形式化 AI 记忆”。

真正的区别在编码时机和资源制度：

| 维度 | DeMem | 本文形式化下的 FQR-Mem |
|---|---|---|
| 编码输入 | 编码器可使用 $(H,Q)$ | writer 只能使用 $H,S,\mathcal U$ |
| 记忆对象 | 查询条件下的运行时决策状态 | 查询到来前冻结的持久视觉状态 |
| 预算主项 | $K$ 个 decision states | 活动存储、读取、接口和计算 |
| 任务 | 语言智能体决策/对话 | grounded 长视频问题与证据 |
| 不确定性 | 已给定当前 context/query | 未来任务分布和证据 shift |
| 读取 | 记忆状态直接服务决策 | 可进行受限、多轮、模型相关读取 |

最重要的数学区别是：

$$
M_{\mathrm{DeMem}}=g(H,Q),
\qquad
M_{\mathrm{FQR}}=g(H;\mathcal U),
$$

后者必须用同一个 snapshot 支持许多可能问题。因此 FQR 应研究的是 **pre-query forgetting boundary**：在不知道具体 $Q$ 时，哪些历史仍可被合并。

如果最终实验没有显示 pre-query、视觉 grounding 或多资源约束带来新的规律，那么这项工作会被合理地视为 DeMem 的视频应用，而不是独立贡献。

### 6.3 FQR 的边际价值是形式化目标的近似

令鲁棒风险为：

$$
\mathcal R_{\mathcal U}(M,S)
=
\sup_{P\in\mathcal U}
\mathbb E_P\!\left[
\ell_{\mathrm{ans}}+
\rho\ell_{\mathrm{ground}}
\mid M,S
\right].
$$

候选事件 $e$ 在码率 $b$ 下的条件价值是：

$$
v_{\mathcal U}(e,b\mid M,S)
=
\mathcal R_{\mathcal U}(M,S)
-
\mathcal R_{\mathcal U}
\bigl(M\oplus c_b(e,S),S\bigr).
$$

单位存储价值为：

$$
u(e,b\mid M,S)
=
\frac{v_{\mathcal U}(e,b\mid M,S)}{C_{\mathrm{store}}(c_b(e,S))}.
$$

这正是 FQR v2 中 conditional codec、coalition counterfactual 和 robust utility critic 的规范解释：它们不是“又一种启发式结构”，而是在近似求解鲁棒任务率失真问题中的边际风险下降。

### 6.4 对 FQR v2 的最小修改

只建议增加五项，不重做现有系统：

1. **在论文开头加入统一问题。**明确 $H,S,\mathcal U,F_\theta,\mathbf B$，把 FQR 定位为该制度的求解器。
2. **把语义充分性与模型可用性分开评测。**同一 memory snapshot 同时交给高能力 oracle decoder 和目标消费者，报告 usability gap。
3. **把一次读取作为主结果，多轮读取作为受控扩展。**先比较 $K=1$ 与 $K=2$，匹配总 read bytes、interface tokens 和 FLOPs。
4. **加入三个关键 oracle。**offline writer、query-known writer、oracle reader；它们分别测因果、未来查询和访问缺口。
5. **报告完整资源向量。**主图仍可固定其余预算画 storage–regret 曲线，附表报告 write/read/interface/compute。

明确不建议加入：

- 预设的“规范潜记忆”；
- 强制的状态/事件/规律四分结构；
- 必需的 memory compiler；
- 没有证据支持的图扩散读取；
- 为解决旧记忆可观性而新增根索引；
- 同时训练新 backbone、世界模型和完整 RL 读取器。

latent 只保留为一种候选 codec，并与帧、文本、事件表和 hybrid 在相同物理预算下比较。

---

## 7. 最小而有论文价值的研究问题

形式化本身太一般，不能自动支撑 ICLR/CVPR。论文必须回答一个新的、可量化的问题：

> **在查询未知且视频不可回放时，任务不确定性、消费者能力和读取预算如何共同决定必须保留的历史差异？FQR 的条件反事实写入能否稳定推进这条多资源前沿？**

建议将研究拆成三个主问题。

### RQ1：未知未来任务使记忆多付出多少容量？

定义 pre-query premium：

$$
\Pi_{\mathrm{pre}}(B)
=
D^*_{\mathrm{pre\text{-}query}}(B)
-
D^*_{\mathrm{post\text{-}query}}(B).
$$

研究 $\Pi_{\mathrm{pre}}$ 如何随以下因素变化：

- 任务族大小与熵；
- 任务之间所需证据的冲突程度；
- side information 充分度；
- 视觉证据的稀有度和延迟；
- 允许的失真和存储预算。

预期规律：任务越不确定、证据集合越互斥，pre-query premium 越大；side information 越充分，视觉 premium 越小。

### RQ2：信息保留与模型可用之间有多大缺口？

固定同一 memory snapshot，依次使用：

1. oracle structured decoder；
2. 强 VLM；
3. 中等 VLM；
4. 同一模型的 text、frame、latent/hybrid 接口。

主测量不是只看最终准确率，而是：

$$
G_{\mathrm{use}}(B)
=
\mathcal L_{\mathrm{op}}(B)
-
\mathcal L_{\mathrm{sem}}(B).
$$

若 oracle 能恢复答案而目标模型不能，问题在接口或消费者；若 oracle 也不能，问题在 writer，不能用更复杂检索器掩盖。

### RQ3：推理耦合读取何时真正有用？

仅在需要跨事件组合的问题上比较：

- $K=1$ 一次读取；
- $K=2$ 先粗后细；
- $K=2$ 推理驱动第二跳；
- query-aware full-read oracle。

必须匹配总 read bytes、interface tokens 和推理 FLOPs。若多轮只在给更多 token 时提升，就不能归因于“推理—记忆耦合”。

---

## 8. 实验设计

### 8.1 Formal Memory Gym：先验证定义，不先训练大模型

建立一个极小的可控视频世界，生成 10–60 分钟符号化或渲染视频。每个样本都能计算精确最小充分记忆和 oracle frontier。

四类世界：

| 世界 | 关键性质 | 用来否证什么 |
|---|---|---|
| Reversible | 完全可观、确定、可逆 | 状态记忆成立的正例 |
| Irreversible | 相同终态来自不同历史 | “终态足够”的反例 |
| Aliased | 当前观测相同、隐藏状态不同 | 单帧状态与纯视觉摘要 |
| Stochastic/Drift | 随机创新或规律变化 | “规律已知即可重建” |

五类任务：

- 当前状态；
- 未来预测；
- 过去事件；
- 事件顺序；
- 两个远距离证据的组合问题。

需要画三张决定性图：

1. task-family size–minimum storage；
2. task uncertainty–pre-query premium；
3. store/read/interface 三个预算分别变化时的 regret frontier。

如果这些基本规律不能被受控实验稳定复现，说明形式化没有被实现正确，不应进入真实长视频。

### 8.2 自然长视频上的 FQR 主实验

继续使用 FQR v2 的 query-after-write 和 FQR-Shift 协议，但把对比组织成前沿而非单点排名。

写入方法：

- 均匀或 reservoir；
- salience/surprise；
- semantic diversity；
- query-hidden learned memory；
- FQR conditional counterfactual writer；
- offline、query-known 两个 oracle。

存储形式：

- 原帧或关键帧；
- query-agnostic caption；
- event record；
- latent codec；
- hybrid。

存储形式不是主贡献，目的是证明规范目标在多个表示上都成立。如果 FQR 只在某个自定义 latent 上有效，应把贡献降格为该 codec，而不能声称一般记忆原则。

主指标：

- matched active bytes 下的 worst-group grounded regret；
- $\operatorname{CVaR}_{0.9}$；
- pre-query premium；
- semantic retention gap；
- access gap；
- usability gap；
- store/read/interface/compute 前沿；
- 证据删除、冲突替换和时间打乱的因果响应。

### 8.3 五个可证伪假设

**H1：任务相对性。**扩大任务族会提高达到相同失真的最小容量；过去事件任务加入后，纯终态方法出现不可消除误差。

**否证条件：**在排除数据泄漏后，跨多个预算和随机种子都看不到任务族扩展的容量代价。

**H2：FQR 条件价值。**在相同存储格式下，仅把启发式写入目标替换为 sampled counterfactual robust value，就能改善 worst-group grounded regret。

**否证条件：**oracle conditional value 本身不能稳定优于 surprise/diversity，或收益只来自更强 teacher 与额外计算。

**H3：模型可用性。**同一存储的语义风险与操作风险存在稳定、可测的缺口，并随消费者能力和接口预算变化。

**否证条件：**所谓缺口完全由不同上下文长度、不同计算或不同训练数据解释。

**H4：迭代读取。**在证据组合问题上，推理条件的第二跳在匹配总读取与计算时优于一次读取。

**否证条件：**收益消失于预算匹配，或第二跳只重复第一跳证据。

**H5：pre-query premium 可预测。**premium 随任务证据冲突度和 ambiguity set 半径单调增加，并被 FQR 相对通用 writer 更快缩小。

**否证条件：**变化无规律，或 FQR 只拟合训练问题频率而在预声明 shift 下恶化。

---

## 9. 理论部分应做到什么程度

仅给出统一符号和上述单调性不够成为 ICLR 理论贡献。最低可接受理论包应包含：

1. **pre-query 等价类与 approximate merge distortion 的定义；**
2. **pre-query premium 的上下界；**至少对有限任务和有限记忆状态给出可计算形式；
3. **严格分离例子；**证明 query-known 与 query-hidden 的最优失真可以有常数差距；
4. **鲁棒任务族结果；**ambiguity set 扩张如何改变安全遗忘边界；
5. **FQR surrogate 的一致性或误差界；**说明 sampled counterfactual value 在什么条件下近似真实边际失真下降。

最有价值、也最难的是第 5 点。若做不到，不要把 FQR utility critic 宣称为理论最优解；应称其为该形式化目标的经验近似。

一个可操作的 approximate merge distortion 是：对一组将共享同一 memory state 的历史簇 $C$，定义

$$
d_P(C)
=
\min_g
\mathbb E_P\!\left[
\ell\bigl(Y,g(Q,S)igr)
\mid H\in C
\right]
-
\mathbb E_P\!\left[
\min_{\widehat y}
\mathbb E\bigl[\ell(Y,\widehat y)\mid H,Q,S\bigr]
\mid H\in C
\right].
$$

鲁棒合并代价为

$$
d_{\mathcal U}(C)
=
\sup_{P\in\mathcal U}d_P(C).
$$

在 $K$ 状态理想化下，writer 要寻找历史划分 $\{C_1,\ldots,C_K\}$，使加权合并代价最小；流式要求该划分可由因果状态更新实现。真实 FQR 的变长证据存储是这一理想化的结构化近似。

---

## 10. 论文叙事与创新边界

### 10.1 不建议的题目

不建议使用“统一 AI 记忆理论”或“完美世界记忆”作为主标题。范围太大，且会被信息瓶颈、POMDP sufficient statistics、predictive states、value-directed compression 和 DeMem 直接挑战。POMDP 中按决策价值压缩 belief state 的思想也早已存在（[Poupart and Boutilier, 2004](https://proceedings.neurips.cc/paper/2004/hash/81c2f886f91e18fe16d6f4e865877cb6-Abstract.html)）。

### 10.2 更可信的论文题目

> **FQR-Mem: Pre-Query Rate-Distortion for Causal Visual Memory**

或

> **What Must a Video Remember Before the Question Is Known?**

### 10.3 可支撑 ICLR/CVPR 的贡献组合

如果结果成立，可以形成四项贡献：

1. **问题：**系统定义并测量查询未知的持久视觉记忆前沿，而不是查询已知压缩或一般运行时 agent memory；
2. **理论：**定义 pre-query forgetting boundary/premium，给出分离结果和鲁棒任务族分析；
3. **方法：**FQR 用条件、反事实、鲁棒边际价值近似求解因果写入；
4. **验证：**用 oracle ladder 将保留、访问、可用性和推理失败分开，并在受控世界和自然长视频上验证前沿规律。

更偏 ICLR 的版本应强化等价类、率失真、鲁棒性和模型相对可解码性。更偏 CVPR 的版本应强化 grounded visual evidence、真实长视频、视觉表示比较和严格资源核算。现在不需要锁定投稿方向。

### 10.4 必须避免的过度声明

- 不是首个 AI memory formalization；
- 不是首个 task-aware compression；
- 不是首个 decision-centric memory；
- 不是首个迭代 retrieval；
- 不证明存在唯一“完美记忆表示”；
- 不把接口 token 变多解释为信息量增加；
- 不把一种 latent codec 的收益外推为一般记忆理论。

---

## 11. 执行顺序与止损门槛

### Gate 0：两周内验证形式化是否产生新现象

只完成 Formal Memory Gym、精确 oracle 和 pre-query/post-query 曲线。

通过条件：

- 能复现状态记忆成立与失败的受控边界；
- pre-query premium 随任务冲突度出现稳定规律；
- storage、read、interface 三类瓶颈能被 oracle ladder 正确区分。

失败则停止“大一统形式化”叙事，仅把定义作为 FQR 实验协议。

### Gate 1：验证 FQR 目标，而不是结构

固定同一表示和同一 writer 架构，只更换训练目标：surprise、平均 counterfactual value、robust counterfactual value。

通过条件沿用 FQR v2 Gate A，并增加：收益必须至少在两种存储形式上复现。

失败则不能声称目标具有表示无关性。

### Gate 2：验证模型可用性

固定 memory snapshot，在两个消费者和至少两种接口上测 semantic/operational gap。

通过条件：缺口可重复，且接口改进能缩小操作风险而不会改变 oracle semantic risk。

失败则删除“模型相关投射”主贡献，不为它新增模块。

### Gate 3：验证推理耦合读取

只在 Gate 1 后加入 $K=2$，严格匹配总预算。

通过条件：在预注册的多证据问题上提升，并且第二跳具有新增证据和可解释地址变化。

失败则保持一次读取，不影响形式化和 FQR writer 主线。

### 推荐产物

```text
experiments/
  EXP-202609xx-formal-memory-gym/
  EXP-202609xx-prequery-frontier/
  EXP-202610xx-fqr-objective/
  EXP-202610xx-usability-gap/
  EXP-202611xx-iterative-read/
```

每个实验都应冻结随机种子、生成器版本、任务分布、消费者版本和完整资源核算。

---

## 12. 最终建议

最小而合理的结合方案是：

1. **不要再把潜记忆当作理论核心。**记忆表示保持开放；
2. **把“完美记忆”改写为任务族下的最小充分历史等价类。**世界完整和传感器重建只是不同 oracle；
3. **把“模型投射”改写为模型与接口受限的操作风险。**单独测量可用性缺口，而非先造一个 compiler；
4. **把“推理耦合取回”改写为有成本的顺序信息获取。**从 $K=1$ 到 $K=2$ 做最小验证；
5. **把“旧记忆不可观”降为可选的 write-access budget。**当前不进入 FQR 主系统；
6. **把 FQR 聚焦到真正新的地方：pre-query causal memory。**它用任务分布而非实际问题，学习在有限字节内保存哪些历史区分；
7. **把论文成败绑定到 pre-query premium、oracle ladder 和多表示复现。**这些成立，形式化才不仅是重新命名。

最值得先做的不是扩展网络，而是证明下面这句话是否真的成立：

> **在未来问题未知时，记忆的困难不是“压缩得像不像过去”，而是在任务分布、模型能力和读取预算共同约束下，提前保留那些事后不能重新获得、又可能改变答案的历史区分。**

如果 Formal Memory Gym 和 FQR Gate 1 能支持这句话，它足以成为一篇有清晰根问题、理论对象和视觉实证的 ICLR/CVPR 级工作主线；如果不能，应该尽早把形式化降为分析工具，而不是继续堆叠结构。

---

## 参考文献锚点

1. Tishby, Pereira, and Bialek. [The Information Bottleneck Method](https://arxiv.org/abs/physics/0004057). 2000.
2. Poupart and Boutilier. [VDCBPI: An Approximate Scalable Algorithm for Large POMDPs](https://proceedings.neurips.cc/paper/2004/hash/81c2f886f91e18fe16d6f4e865877cb6-Abstract.html). NeurIPS 2004.
3. Kourtellaris, Charalambous, and Stavrou. [Nonanticipative Rate Distortion Function for General Source-Channel Matching](https://arxiv.org/abs/1304.6528). 2013.
4. Zhang et al. [Learning Causal State Representations of Partially Observable Environments](https://arxiv.org/abs/1906.10437). 2019/2021.
5. Dubois et al. [Learning Optimal Representations with the Decodable Information Bottleneck](https://proceedings.neurips.cc/paper/2020/hash/d8ea5f53c1b1eb087ac2e356253395d8-Abstract.html). NeurIPS 2020.
6. Guo et al. [Semantic Compression with Side Information: A Rate-Distortion Perspective](https://arxiv.org/abs/2208.06094). 2022.
7. Xiong et al. [Adaptive Information Control for Search-Augmented LLM Reasoning](https://arxiv.org/abs/2602.01672). 2026.
8. Zou et al. [Remember the Decision, Not the Description: A Rate-Distortion Framework for Agent Memory](https://arxiv.org/abs/2605.10870). 2026.
9. 项目内部文献证据表：[FQR-Mem 2026 Literature Evidence](../literature/fqr_mem_2026_literature_evidence.md).
