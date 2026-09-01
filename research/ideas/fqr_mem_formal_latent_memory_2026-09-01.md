# FQR-Mem v3：未来查询风险下的形式化潜记忆

> - 日期：2026-09-01
> - 状态：研究方案；尚无实验结果
> - 基础版本：[FQR-Mem v2](./fqr_mem_optimized_proposal_2026-08-24.md)
> - 文献基础：[FQR-Mem 2026 年相关文献证据表](../literature/fqr_mem_2026_literature_evidence.md)

本文不覆盖 FQR-Mem v2，而是在其“query-after-write、固定预算、未来查询风险、grounded regret”设定上，引入一套可分解的记忆形式化。文中使用以下标记：

- **[事实]**：由已有理论或文献直接支持；
- **[推论]**：由定义或假设推出，但尚未在本项目中验证；
- **[方案]**：建议实现和实验验证的设计；
- **[边界]**：必须显式声明的适用条件或反例。

---

## 0. 执行结论

### 0.1 一句话方案

**[方案]** 将 AI 记忆定义为一串受任务、模型与资源约束的条件信道，而不是一个手工设计的数据结构：

$$
H_t
\longrightarrow Z_t^\star
\longrightarrow M_t
\overset{\text{adaptive read}}{\longrightarrow} U_{1:K}
\overset{\text{model compiler}}{\longrightarrow} P_{1:K}^{(\theta)}
\longrightarrow \hat Y_Q .
$$

其中：

- $H_t$：截至时刻 $t$ 的完整视觉历史；
- $Z_t^\star$：世界层的**规范潜记忆**，是理论参照，不要求部署时完整物化；
- $M_t$：在任务先验、未来查询风险和固定预算下实际保存的**持久潜记忆**；
- $U_k$：第 $k$ 轮推理根据当前线索，从 $M_t$ 选择性再编码得到的**读码**；
- $P_k^{(\theta)}$：面向具体消费模型 $F_\theta$ 的**工作记忆表示**，可以是软 token、KV、跨注意力状态或其他模型接口；
- $\hat Y_Q$：模型在多轮“推理—取回”后给出的答案及证据。

### 0.2 最重要的概念拆分

FQR-Mem v2 中的 conditional codec 同时承担了世界内容编码、任务选择和模型可用性转换。v3 将其拆成四个不同问题：

1. **世界记住了什么**：规范潜记忆是否足以表示可预测状态、历史事件和变化规律；
2. **任务值得保存什么**：FQR task lens 如何在查询不可见时分配持久存储码率；
3. **当前应该读什么**：推理状态如何驱动选择性地址、粒度和读码率；
4. **具体模型怎样才能用**：模型专属 compiler 如何把读码转换到其输入或隐状态空间。

这个拆分带来两个直接收益：

- 可以区分“没有写入”“写入但没取回”“取回但接口不合适”“模型看到了但不会用”；
- 可以研究同一个规范潜记忆能否服务不同能力、不同接口的消费模型，而不必为每个模型重新存储原视频。

### 0.3 论文的核心科学命题

**[方案]** 首篇论文不应把主贡献表述为“新的长视频 memory bank”，而应检验以下命题：

> 在严格 query-after-write 和固定总资源下，视觉记忆可以被分解为规范潜状态、未来查询风险下的任务码率分配、推理耦合的自适应读码、以及模型专属记忆编译；这种分解不仅提高性能—资源前沿，而且能定位现有记忆系统失败发生在哪一层。

### 0.4 必须先修正的一个直觉

“掌握完美世界规律后，记忆只需要当前状态”不是无条件成立的。

- 对**确定、完全可观、Markov 世界中的未来预测任务**，当前状态和已知动力学可以充分；
- 对**部分可观世界**，通常需要关于隐状态的信念或预测状态；
- 对**随机世界**，还需要不确定性或无法由当前状态反推出的创新量；
- 对**询问过去偶发事件的任务**，即使当前状态和动力学完美，仍可能需要情景事件账本。

因此，本方案不把“完美记忆”简单等同于当前状态，而定义为：

$$
Z_t^\star
=
\left(
B_t,\ E_t,\ \Omega_t,\ I_t
\right),
$$

其中 $B_t$ 是信念或预测状态，$E_t$ 是不可由当前状态恢复的情景创新，$\Omega_t$ 是局部动力学或规律后验，$I_t$ 是有界的地址与溯源信息。

---

## 1. 从原始思想到可检验形式

| 原始思想 | 保留的核心 | 需要补充的边界 | v3 中的形式化组件 |
|---|---|---|---|
| 最完整的记忆支持重建 | 用解码任务定义“信息是否还在” | 必须说明重建传感器像素、世界状态还是任务目标 | 三层 distortion：sensor、world、task |
| 完美规律下只需状态 | 动力学知识可替代重复轨迹 | 只对特定未来任务和可观测性假设成立 | $B_t+E_t+\Omega_t$ 分解 |
| 任务先验可大幅压缩记忆 | 任务分布决定允许丢弃的信息 | 实际未来问题不可泄漏给 writer | FQR task lens 与 ambiguity set |
| 完美记忆需变成模型能用的形式 | 存储表示与消费表示不同 | 投射不能凭空增加视频信息 | model-specific memory compiler |
| 取回与推理深度耦合 | 中间推理结果是下一轮取回线索 | 需显式计费读带宽、上下文和推理轮数 | adaptive read codec 与 VOI 停止 |
| 流式更新以旧记忆为条件 | 新片段需与既有实体和事件关联 | 旧记忆在计算预算下不可完全查看 | read-before-write 与两阶段提交 |

### 1.1 “完美记忆”不是脱离目标的绝对对象

**[事实]** 信息瓶颈把压缩描述定义为：在压缩输入的同时保留关于指定相关变量的信息；因此“最小充分表示”必须先指定相关变量。[Information Bottleneck](https://arxiv.org/abs/physics/0004057)

**[推论]** 如果没有说明希望重建或预测什么，就不存在唯一且可比较的“完美记忆”。至少要区分三个目标族：

1. **传感器重建** $\mathcal G_{\mathrm{sensor}}$：重建原始帧、音频和时间戳；
2. **世界重建** $\mathcal G_{\mathrm{world}}$：恢复产生观测的状态、对象、关系、事件和可预测未来；
3. **任务重建** $\mathcal G_{\mathcal T}$：恢复任务分布可能询问的目标。

像素级无损重建会迫使系统保存传感器噪声、压缩伪影和与任务无关的纹理。因此，它可以作为最强信息上界，但不应被直接称为唯一正确的世界记忆目标。

### 1.2 “状态足够”的精确条件

设世界状态为 $X_t$，动力学为 $P_\omega(X_{t+1}\mid X_t,A_t)$，观测为 $O_t\sim P(O_t\mid X_t)$。

**命题 1：未来任务的状态充分性。**

若世界完全可观、动力学参数 $\omega$ 已知、过程满足 Markov 性，且所有目标只依赖于 $X_t$ 之后的轨迹，则 $X_t$ 对这类未来目标是充分统计量。

其依据是：

$$
P(Y_Q\mid H_t,Q,\omega)
=
P(Y_Q\mid X_t,Q,\omega).
$$

**[事实]** 预测状态表示进一步说明，状态也可以由一组关于未来可观测量的多步条件预测来定义，而不必等同于不可观测的物理变量。[Predictive Representations of State](https://proceedings.neurips.cc/paper/2001/file/1e4d36177d71bbb3558e43af9577d70e-Paper.pdf)

**命题 2：过去事件破坏 state-only 充分性。**

若存在两个历史 $h_t$ 与 $h'_t$ 满足相同当前状态 $X_t$，但某个过去事件查询的答案不同，则任何只保存 $X_t$ 的记忆都无法同时正确回答这两个历史。

这是一个直接反例：

$$
X_t(h_t)=X_t(h'_t),
\qquad
Y_Q(h_t)\neq Y_Q(h'_t).
$$

因此，面向长视频回溯问答时必须保存至少一部分**情景创新** $E_t$，例如“谁在何时把哪个物体交给了谁”，即使该事件没有改变最终世界状态。

### 1.3 部分可观时，作为条件的记忆也只能被部分读取

**[事实]** 在 POMDP 中，历史通常通过关于隐状态的 belief state 汇总；部分可观测性把状态估计和决策耦合起来。[Planning and Acting in Partially Observable Stochastic Domains](https://www.cassandra.org/arc/papers/aij98.pdf)

**[推论]** 流式记忆系统存在第二层部分可观测性：

- 外部世界对模型部分可观；
- 已存记忆虽然物理存在，但在固定读带宽和计算预算下也不能被一次性全部检查。

因此 writer 在更新前实际看到的不是 $M_{t-1}$，而是一个有成本的记忆视图：

$$
V_t^{\mathrm{write}}
\sim
P_\rho
\left(
V\mid M_{t-1},a_t^{\mathrm{write}}
\right).
$$

这使流式更新本身成为一个受限的主动观测问题。

### 1.4 “投射会放大体积”不等于信息增加

**命题 3：模型编译的信息边界。**

若模型接口表示 $P^{(\theta)}$ 只由读码 $U$、查询 $Q$ 和模型预训练知识 $K_\theta$ 生成，则数据处理不等式给出：

$$
I\!\left(
Y_Q;P^{(\theta)}
\mid Q,K_\theta
\right)
\leq
I\!\left(
Y_Q;U
\mid Q,K_\theta
\right).
$$

**[推论]** 模型投射可以把一个短潜变量展开成很多 token 或 KV，但不能创造原记忆中不存在的视频事实。体积放大反映的是：

- 消费模型接口的编码效率；
- 模型知识不完备导致需要更显式的证据；
- 推理过程需要的中间结构；
- 冗余表达带来的鲁棒性。

因此，本方案将这一层称为**记忆编译**，而不是信息增强。

---

## 2. 问题设定与因果时序

### 2.1 世界、历史、任务与消费模型

定义：

- $X_t$：不可直接完全观测的世界状态；
- $O_t$：第 $t$ 个视频片段及可用音频、时间等观测；
- $H_t=(O_{1:t},A_{1:t-1})$：完整历史，$A$ 可包含相机或智能体动作；
- $\mathcal T$：任务族；
- $Q\sim P_{\mathcal T}(Q\mid H_t)$：写入完成后才出现的查询；
- $Y_Q$：查询对应的目标答案与证据；
- $S_Q$：查询时合法可用的 side information；
- $F_\theta$：冻结或受控训练的消费模型；
- $\Theta$：同一持久记忆希望支持的消费模型集合；
- $K_\theta$：消费模型在当前视频之前已获得的参数化知识。

### 2.2 严格 query-after-write 协议

主协议继续沿用 FQR-Mem v2：

1. 视频流到达，writer 只能访问当前观测、合法 side information、任务先验和受限旧记忆视图；
2. writer 完成 $M_t$ 的更新；
3. 实际查询 $Q$ 才被揭示；
4. 系统只能读取 $M_t$，不可重新访问原始视频；
5. 消费模型通过多轮取回和推理产生答案与 grounding。

非前视约束写为：

$$
P
\left(
M_t
\mid
H_t,\mathcal T,S_{1:t},M_{t-1},Q
\right)
=
P
\left(
M_t
\mid
H_t,\mathcal T,S_{1:t},M_{t-1}
\right).
$$

其中 $\mathcal T$ 是训练期任务分布或其不确定集合，实际测试查询 $Q$ 不得作为 writer 输入。

### 2.3 资源不是一个 token 数，而是一个向量

记忆系统至少涉及以下独立资源：

$$
\mathbf B
=
\left(
B_{\mathrm{store}},
B_{\mathrm{write}},
B_{\mathrm{read}},
B_{\mathrm{interface}},
B_{\mathrm{compute}}
\right).
$$

- $B_{\mathrm{store}}$：持久记忆总比特；
- $B_{\mathrm{write}}$：流式更新时的读写带宽和计算；
- $B_{\mathrm{read}}$：回答一次查询可从持久记忆读取的总比特；
- $B_{\mathrm{interface}}$：注入消费模型的 token、KV 或激活字节；
- $B_{\mathrm{compute}}$：取回轮数、模型调用次数和 FLOPs。

只控制输入 token 而不控制持久存储、读带宽或回放权限，会把不同问题混在一起。

### 2.4 参数化知识的计费边界

**[方案]** 首篇论文主要研究**单个视频/情景内形成的非参数化记忆**。模型和 compiler 在视频到来之前已经固定，记为 side information：

$$
K_{\mathrm{pre}}
=
\left(
\theta,\eta,\text{training corpus}
\right).
$$

但必须报告：

- 消费模型与 compiler 的参数量和训练数据；
- compiler 是否针对消费模型单独训练；
- 是否使用了原视频或测试查询泄漏；
- 若比较“总记忆”，则另外报告参数更新的描述长度或摊销成本。

这样可以防止 compiler 把测试视频事实偷偷吸收到参数中。

### 2.5 普适形式与本文范围

上述变量并不要求历史一定是视频：$H_t$ 可以是任意连续经验流，$Q$ 可以是未来预测、行动、问答或规划目标，$F_\theta$ 可以是语言模型、视觉语言模型或策略模型。因此，条件信道分解本身可用于更一般的 AI 记忆。

**[边界]** 首篇工作只在超长视频的情景记忆上验证，不试图一次性解决参数化知识更新、跨智能体共享和终身学习。先把可观测变量、资源和反例做清楚，比宣称“统一全部 AI 记忆”更可证伪。

---

## 3. 形式化定义

### 3.1 历史等价与规范记忆

给定目标变量族 $\mathcal G$，定义两个历史的等价关系：

$$
h\sim_{\mathcal G}h'
\iff
\forall G\in\mathcal G,\quad
P(G\mid H=h,S)
=
P(G\mid H=h',S).
$$

**定义 1：规范记忆。**

$Z^\star_{\mathcal G}(H)$ 是历史关于 $\mathcal G$ 的等价类标识；如果两个历史对所有目标变量有相同条件分布，它们可以映射到同一记忆状态。

后文不带下标的 $Z_t^\star$ 特指 $\mathcal G_{\mathrm{world}}$ 上的规范潜记忆；$M_t$ 则是面向任务族 $\mathcal T$、资源预算和支持模型集合的部署记忆。即使是 $\mathcal G_{\mathrm{world}}$，也必须声明环境边界和 decoder 已知规律，因此它仍不是脱离世界模型的绝对对象。

这种定义有三个性质：

1. 它不绑定某个神经网络结构；
2. 它明确依赖目标族 $\mathcal G$ 和 decoder 已知的 side information；
3. 最小表示通常只在可逆变换或统计等价意义下唯一，而不是一个唯一向量坐标系。

### 3.2 近似充分性

对于一个由历史生成的记忆 $Z=f(H)$，定义目标族上的信息缺口：

$$
\epsilon_{\mathcal G}(Z)
=
\mathbb E_{G\sim\mathcal G}
\left[
D_{\mathrm{KL}}
\left(
P(G\mid H,S)
\Vert
P(G\mid Z,S)
\right)
\right].
$$

在相应条件成立时，它等价于条件互信息：

$$
\epsilon_{\mathcal G}(Z)
=
I(G;H\mid Z,S).
$$

若 $\epsilon_{\mathcal G}(Z)\leq\epsilon$，称 $Z$ 对目标族 $\mathcal G$ 是 $\epsilon$-充分的。

对任务族 $\mathcal T$：

$$
\epsilon_{\mathcal T}(M)
=
\mathbb E_{q\sim P_Q}
\left[
I
\left(
Y_q;H_t
\mid M_t,Q=q,S_q
\right)
\right].
$$

该量描述“答案所需历史信息中，还有多少没有被记忆保留”，但真实视频上不能直接精确计算，需要用 oracle decoder、预测损失和干预实验估计。

### 3.3 三种重建与 distortion

定义三类失真：

$$
D_{\mathrm{sensor}}
=
\mathbb E
\left[
d_{\mathrm{sensor}}
\left(
H,\hat H(Z)
\right)
\right],
$$

$$
D_{\mathrm{world}}
=
\mathbb E
\left[
d_{\mathrm{world}}
\left(
X_{1:t},\hat X_{1:t}(Z)
\right)
\right],
$$

$$
D_{\mathrm{task}}
=
\mathbb E_{Q}
\left[
\ell_Q
\left(
Y_Q,\hat Y_Q(Z)
\right)
\right].
$$

三者分别回答：

- 原始传感器信号能否恢复；
- 世界状态、对象、事件和未来分布能否恢复；
- 指定任务的答案和证据能否恢复。

**[边界]** $D_{\mathrm{sensor}}$ 最小并不必然带来最小 $D_{\mathrm{task}}$；反之，任务压缩可能故意丢掉绝大多数像素。

### 3.4 世界码率、任务码率与模型可用码率

世界层 rate-distortion：

$$
R_{\mathcal G}(D)
=
\inf_{P(Z\mid H)}
I(H;Z\mid S)
\quad
\text{s.t.}\quad
\mathbb E[d_{\mathcal G}]\leq D.
$$

未来查询分布不确定时的鲁棒任务码率：

$$
R_{\mathcal T}^{\mathrm{rob}}(D)
=
\inf_{P(M\mid H)}
I(H;M\mid S)
$$

满足：

$$
\sup_{P_Q\in\mathcal U(P_0)}
\mathbb E_{Q\sim P_Q}
\left[
d_Q(H,M)
\right]
\leq D.
$$

模型可用码率则显式依赖消费模型：

$$
R_{\mathcal T,\theta}^{\mathrm{use}}(\epsilon)
=
\inf
\mathbb E[\operatorname{bits}(M)]
$$

满足：

$$
\sup_{P_Q\in\mathcal U(P_0)}
\mathbb E
\left[
\operatorname{Regret}_{\theta}(Q;M)
\right]
\leq\epsilon,
$$

其中优化还包括合法的 reader 和 model compiler。

**[推论]** 两个模型可能面对同一世界、同一任务，却有不同的 $R_{\mathcal T,\theta}^{\mathrm{use}}$。更弱或接口更低效的模型可能需要更详细、更冗余的读码和更大的工作上下文。

**命题 4：任务族单调性。**

若 $\mathcal T_1\subseteq\mathcal T_2$，二者使用相同失真阈值、side information 和风险口径，则可行编码集合满足反向包含，从而：

$$
R_{\mathcal T_1}^{\mathrm{rob}}(D)
\leq
R_{\mathcal T_2}^{\mathrm{rob}}(D).
$$

这给出了“任务先验越集中，记忆越可压缩”的精确版本；若任务族扩展到任意传感器重建，任务记忆会逐渐逼近世界或传感器层记忆。

### 3.5 接口放大系数

定义：

$$
\alpha_\theta
=
\frac{
\mathbb E
\left[
\sum_{k=1}^{K}
\operatorname{bits}
\left(
P_k^{(\theta)}
\right)
\right]
}{
\mathbb E
\left[
\sum_{k=1}^{K}
\operatorname{bits}(U_k)
\right]
}.
$$

$\alpha_\theta>1$ 表示模型接口展开了潜读码；它是**表示和接口成本**，不是新增的情景信息量。

---

## 4. 规范潜记忆：状态、事件、规律与索引

### 4.1 四部分分解

**[方案]**

$$
Z_t^\star
=
\left(
B_t,E_t,\Omega_t,I_t
\right).
$$

#### 1. 信念或预测状态 $B_t$

$B_t$ 表示当前世界的可预测状态：

$$
B_t
\approx
P
\left(
X_t,\text{future observations}
\mid H_t
\right).
$$

在完全可观环境中，它可退化为当前状态；在遮挡或歧义下，它必须保留多峰假设和校准不确定性，而不能只是一个点估计。

#### 2. 情景创新账本 $E_t$

$E_t$ 保存无法从当前状态与已知规律恢复、但可能被未来查询询问的历史创新：

$$
E_t
=
\left\{
e_i:
\text{event residual not recoverable from }(B_t,\Omega_t)
\right\}.
$$

典型内容包括：

- 身份绑定和首次出现；
- 不改变最终状态的动作；
- 稀有但可查询的局部视觉细节；
- 事件发生时间、顺序和参与实体；
- 随机转移产生的创新量；
- 对状态估计产生分歧的关键观测。

#### 3. 动力学或规律后验 $\Omega_t$

$\Omega_t$ 表示当前环境中可复用的变化规律、局部 schema 或其不确定性：

$$
\Omega_t
\approx
P
\left(
\omega
\mid H_t
\right).
$$

如果规律已完全存于模型参数且环境平稳，$\Omega_t$ 可以很小；若场景具有新规则、角色习惯或机制变化，则需要保存局部残差。

#### 4. 地址、时间与溯源 $I_t$

$I_t$ 保存有界的寻址信息：

- 时间区间与事件层级；
- 实体和关系键；
- 因果或共现边；
- 来源片段、置信度和更新版本；
- 可用码率层级与解码依赖。

它不应无限增长，也不应成为不计费的完整文本摘要。

### 4.2 为什么这仍然是“潜记忆”

四个分量是**语义角色**，不是规定必须保存符号文本：

- $B_t$ 可以是连续 belief slots 或预测状态 token；
- $E_t$ 可以是向量量化的事件残差；
- $\Omega_t$ 可以是低秩动力学适配状态；
- $I_t$ 可以是紧凑键、时间编码和 provenance graph。

**[事实]** 近期工作已经表明，存储态和模型消费态可以不同：M+ 使用可扩展潜空间长期记忆与共同训练的 retriever；SeDeM 先保存压缩隐状态，再选择、解压并注入生成模型；One Token per Multimodal Evidence 则把单个多模态证据压到潜 token 中，同时训练重建、检索和生成。[M+](https://arxiv.org/abs/2502.00592) · [SeDeM](https://arxiv.org/abs/2608.00311) · [One Token per Multimodal Evidence](https://arxiv.org/abs/2606.10572)

本方案与这些工作的区别不只是压缩率，而是把“世界充分性、任务码率、读取码率和模型接口”定义为不同对象。

### 4.3 部署记忆不等于完整物化 $Z_t^\star$

$Z_t^\star$ 是理论 oracle。部署系统保存的是预算化近似：

$$
M_t
=
\mathcal A_\psi
\left(
Z_t^\star;
\mathcal T,\mathcal U(P_0),\mathbf B
\right).
$$

实际实现不需要先生成无损 $Z_t^\star$ 再压缩；可以用共享编码器直接产生候选潜变量，再用不同监督分别约束规范层和任务层。关键是训练和评测中保留这两个概念接口，使错误可以被诊断。

### 4.4 一个记忆原子的建议结构

每个持久记忆原子记为：

$$
m_i
=
\left(
k_i,z_i,\tau_i,\ell_i,\sigma_i,p_i,r_i,c_i
\right),
$$

其中：

- $k_i$：内容地址或实体键；
- $z_i$：潜 payload；
- $\tau_i$：时间范围；
- $\ell_i$：state、event 或 dynamics 类型；
- $\sigma_i$：不确定性；
- $p_i$：溯源和依赖；
- $r_i$：可用码率层级；
- $c_i$：存储、读取和解码成本。

原子只是计算接口。真正有价值的证据可能是一个 bundle，因此 FQR 仍需学习组合价值，而不能只为每个原子独立打分。

---

## 5. 统一系统结构

~~~mermaid
flowchart LR
    O[流式视频观测 O_t] --> C[规范潜编码器]
    Old[旧记忆只读快照 M^-] --> WR[写入前受限取回]
    WR --> C
    C --> Cand[状态 / 事件 / 规律候选]
    Cand --> Lens[FQR task lens<br/>未来查询风险与多码率分配]
    Lens --> Commit[两阶段提交]
    Commit --> Store[(持久潜记忆 M_t)]

    Q[查询 Q] --> Ctrl[推理耦合取回控制器]
    Store --> Read[自适应 read codec]
    Ctrl --> Read
    Read --> U[选择性潜读码 U_k]
    U --> Comp[模型专属 memory compiler]
    Comp --> P[工作记忆 P_k]
    P --> Model[消费模型 F_theta]
    Model --> State[中间推理状态 h_k]
    State --> Ctrl
    Model --> Ans[答案 + 时空证据]
~~~

### 5.1 每个模块只有一个主要责任

| 模块 | 主要问题 | 不应偷偷承担的责任 |
|---|---|---|
| 规范潜编码器 | 哪些状态、事件和规律存在 | 不根据实际测试问题选择证据 |
| FQR task lens | 未知未来查询下如何分配持久码率 | 不决定具体模型的 token 格式 |
| read codec | 当前轮读取哪些地址、什么精度 | 不重新访问原始视频 |
| memory compiler | 如何让 $F_\theta$ 使用读码 | 不创造未存储的视频事实 |
| retrieval controller | 何时读、读哪里、何时停止 | 不拥有免费无限读带宽 |
| streaming updater | 如何把新观测与旧记忆一致地合并 | 不把当前候选先写入再用其检索自身 |

### 5.2 v2 到 v3 的关键变化

| FQR-Mem v2 | FQR-Mem v3 |
|---|---|
| conditional evidence codec 是核心表示 | 规范潜记忆与任务预算化记忆分开 |
| writer 直接估计记忆项效用 | writer 对 state、event、dynamics 候选分配码率 |
| reader 主要做 query-aware 读取 | reader 是多轮 adaptive re-encoding policy |
| 表示默认直接供模型使用 | 增加显式 model-specific compiler |
| 主要分解写入与读取 | 进一步分解编码、任务选择、取回、读码、编译、使用、更新 |
| side information 影响 codec | 模型知识和情景记忆分别计费，防止信息偷渡 |

---

## 6. FQR 的新角色：任务镜头，而不是完整记忆定义

### 6.1 写入时的未来查询风险

定义同一消费模型在完整合法历史证据和记忆交互下的损失：

$$
\mathcal L_{\theta}^{\mathrm{full}}(Q,H)
$$

与：

$$
\mathcal L_{\theta}^{\mathrm{mem}}
\left(
Q,M;\rho_\theta,\eta_\theta
\right).
$$

单查询 grounded regret 定义为：

$$
r_\theta(Q;M)
=
\left[
\mathcal L_{\theta}^{\mathrm{mem}}
\left(
Q,M
\right)
-
\mathcal L_{\theta}^{\mathrm{full}}
\left(
Q,H
\right)
\right]_+.
$$

其中：

$$
\mathcal L_\theta
=
\ell_{\mathrm{answer}}
+
\lambda_g\ell_{\mathrm{ground}}
+
\lambda_c\ell_{\mathrm{calibration}}.
$$

使用同一个消费模型的 full-evidence oracle，可以尽量把“模型本身不会回答”与“记忆丢失了证据”分开。

若希望一份持久记忆支持模型集合 $\Theta$，定义：

$$
r_\Theta(Q;M)
=
\operatorname{RiskAgg}_{\theta\in\Theta}
\left[
r_\theta(Q;M)
\right],
$$

其中 $\operatorname{RiskAgg}$ 可以是平均、worst-model 或 CVaR。主方案采用模型集合上的风险聚合；只用单个 $\theta$ 优化的版本记为 consumer-tuned FQR，它可以作为性能上界，但不能同时声称持久记忆具有跨模型规范性。

还应实现一个更彻底解耦的 semantic FQR：用冻结的任务充分性 probe 评估答案与证据能否从 $M$ 解码，而不使用任何目标消费模型。它测量 task sufficiency，但会受 probe 能力影响。模型集合风险版本测量 operational usability，但会受 $\Theta$ 的覆盖范围影响。二者并列报告，正好暴露“任务信息仍在”和“指定模型能否使用”之间的差距。

### 6.2 层次 ambiguity set

实际未来问题分布未知，只假设位于：

$$
P_Q
\in
\mathcal U(P_0).
$$

建议层次包括：

- 查询类型；
- 证据跨度和稀有度；
- 视觉依赖强度；
- side information 可靠度；
- 视频域和长度；
- 单证据与组合证据；
- 任务组内的细粒度分布变化。

**[事实]** 2026 年的层次歧义集工作说明，仅在粗粒度 group 间做 worst-case 仍可能遗漏组内变化。[Mitigating Spurious Correlation via Distributionally Robust Learning with Hierarchical Ambiguity Sets](https://proceedings.iclr.cc/paper_files/paper/2026/hash/c4f85da01632a2211c785f482cb3e043-Abstract-Conference.html)

### 6.3 FQR task lens 的优化对象

给定当前规范候选集合 $\mathcal C_t$、只读旧快照 $M_{t-1}^{-}$ 和每个候选的多码率版本，task lens 选择持久记忆：

$$
M_t
=
\arg\min_{
M\in
\mathfrak F
\left(
M_{t-1}^{-}\cup\mathcal C_t,
B_{\mathrm{store}}
\right)
}
\sup_{P_Q\in\mathcal U(P_0)}
\mathbb E_{Q\sim P_Q}
\left[
r_\Theta(Q;M)
\right]
$$

满足：

$$
\operatorname{bits}(M)\leq B_{\mathrm{store}}.
$$

训练时可以使用 Lagrangian，正式比较必须回到同一硬预算。

### 6.4 任务先验影响哪些层

任务机制不直接改变“什么是世界层规范信息”，但会影响规范层之后的三个决策：

1. **持久化**：哪些规范因素值得物化，以及每个因素保存多少比特；
2. **读取**：某个具体查询和当前推理状态下，哪些因素值得被选择性再编码；
3. **编译**：在该任务族中，消费模型需要哪些显式中间结构和多大接口展开。

形式上：

$$
M_t
\sim
P_\psi
\left(
M\mid Z_t^\star,\mathcal T,\mathbf B
\right),
$$

$$
U_k
\sim
P_\rho
\left(
U\mid M_t,Q,h_k,\mathcal T,\theta,\mathbf b_k
\right).
$$

模型接口进一步满足：

$$
P_k^{(\theta)}
=
C_{\eta_\theta}^{(\theta)}
\left(
U_k,Q,h_k,\mathcal T,K_\theta
\right).
$$

这样既保留规范记忆的定义，又允许任务分布降低持久存储、选择性读取和模型接口的实际开销。需要跨模型复用时，持久化阶段使用 $\Theta$ 上的聚合风险；读取和编译仍可针对当前 $\theta$。

### 6.5 组合证据价值

对于记忆 bundle $S$，定义删除后的反事实效用：

$$
u(S)
=
\sup_{P_Q\in\mathcal U(P_0)}
\mathbb E_Q
\left[
\mathcal L_\theta(Q;M\setminus S)
-
\mathcal L_\theta(Q;M)
\right].
$$

若：

$$
u(\{i,j\})
>
u(\{i\})+u(\{j\}),
$$

则 $i,j$ 存在互补性。writer 应保存完整证据组合，而不是只按单项分数排序。训练可延续 v2 的 sampled coalition counterfactual，辅以稀疏 Shapley 近似或 bundle ranking。

---

## 7. 取回的形式化：自适应再编码

### 7.1 取回不是一次最近邻查询

第 $k$ 轮推理状态定义为：

$$
s_k
=
\left(
Q,h_k,\mu_k,
b_k^{\mathrm{read}},
b_k^{\mathrm{interface}},
b_k^{\mathrm{compute}}
\right),
$$

其中 $h_k$ 是消费模型中间推理状态，$\mu_k$ 是控制器根据已读证据形成的记忆相关信念。

控制器选择：

$$
a_k
=
\left(
\mathcal A_k,
\nu_k,
\beta_k
\right)
\sim
\pi_\rho(a\mid s_k,I_t),
$$

其中：

- $\mathcal A_k$：地址或时间—实体区域；
- $\nu_k$：读取视角或证据类型；
- $\beta_k$：本轮码率和精度。

read codec 产生：

$$
U_k
\sim
P_{\mathrm{read}}
\left(
U\mid M_t,a_k
\right).
$$

因此，取回同时决定“读哪里”和“怎样编码所读内容”，而不是从数据库原样复制一个条目。

### 7.2 推理—取回闭环

模型专属 compiler 和消费模型依次更新：

$$
P_k^{(\theta)}
=
C_{\eta}^{(\theta)}
\left(
U_k,Q,h_k,K_\theta
\right),
$$

$$
h_{k+1}
=
F_\theta
\left(
h_k,Q,P_k^{(\theta)}
\right).
$$

新的 $h_{k+1}$ 包含局部结论、未解决槽位、冲突和置信度，成为下一轮取回线索。

**[事实]** IRCoT、FLARE 和 Self-RAG 都提供了“推理中间状态决定后续检索”的语言任务证据，但没有解决固定视觉存储、潜读码和模型接口的联合计费。[IRCoT](https://aclanthology.org/2023.acl-long.557/) · [FLARE](https://aclanthology.org/2023.emnlp-main.495/) · [Self-RAG](https://proceedings.iclr.cc/paper_files/paper/2024/file/25f7be9694d7b32d5cc670927b8091e1-Paper-Conference.pdf)

### 7.3 记忆空间内部扩散

除模型产生的新语义查询外，控制器可沿记忆内部关系传播。例如：

$$
w_{k+1}
=
\operatorname{softmax}
\left(
g_\rho(Q,h_k)
+
\gamma A_Mw_k
\right),
$$

其中 $A_M$ 是由时间邻接、实体一致性、事件依赖和 learned affinity 构成的稀疏转移算子。

**[边界]** 这只是可选实现，不是理论定义。若简单语义—时间检索已经达到相同性能—资源前沿，则不应把 graph diffusion 作为必要结构。

### 7.4 基于信息价值的停止

定义候选读取动作的近似价值：

$$
\operatorname{VOI}(a\mid s_k)
=
\mathbb E
\left[
\hat{\mathcal L}(s_k)
-
\hat{\mathcal L}(s_{k+1}\mid a)
\right]
-
\lambda_r\operatorname{bits}(U)
-
\lambda_p\operatorname{bits}(P)
-
\lambda_c\operatorname{compute}(a).
$$

若：

$$
\max_a\operatorname{VOI}(a\mid s_k)\leq 0,
$$

或预算耗尽，则停止读取并回答。

**[事实]** OASIS、REVEAL 和 2026 年若干 agentic long-video 方法已说明“证据不足后再检索”和自适应停止是强基线；本方案的新增点是把它们放入持久码率、读码率和模型接口共同受限的形式化中。[OASIS](https://arxiv.org/abs/2604.17052) · [REVEAL](https://arxiv.org/abs/2608.08612)

---

## 8. 模型专属记忆编译

### 8.1 compiler 的定义

model compiler 是一个模型相关、视频无关的条件映射：

$$
C_{\eta}^{(\theta)}:
\left(
U_k,Q,h_k,K_\theta
\right)
\mapsto
P_k^{(\theta)}.
$$

可选输出接口包括：

- 视觉 soft tokens；
- cross-attention key/value；
- 指定层的 KV 或 adapter state；
- 可解码的小图像或局部视频；
- 面向黑盒模型的结构化文本加视觉证据。

首选 latent-to-latent 接口，因为它最能检验潜记忆；文本或像素解码应作为兼容性基线，而不是默认唯一方案。

### 8.2 为什么 compiler 与 retrieval 必须分开

同一个 $U_k$ 可以被不同 compiler 映射给不同模型：

$$
P_k^{(\theta_1)}
=
C_{\eta_1}^{(\theta_1)}(U_k,\cdot),
\qquad
P_k^{(\theta_2)}
=
C_{\eta_2}^{(\theta_2)}(U_k,\cdot).
$$

这允许直接检验：

- 存储能否跨模型复用；
- 性能差异来自记忆内容还是接口；
- 弱模型是否需要更大的 $\alpha_\theta$；
- 模型升级后是否无需重新编码历史视频。

### 8.3 处理模型知识不完备

模型知识不完备不意味着 compiler 可以创造事实。正确的处理方式是让 task lens 和 read codec 为该模型提供更显式的支持证据：

$$
U_k^{(\theta)}
=
\operatorname{Read}
\left(
M_t;
Q,h_k,\operatorname{capability}(\theta)
\right).
$$

例如，强模型可能只需一个潜事件向量；弱模型可能需要同时读出实体属性、时间顺序和两段局部视觉证据。

### 8.4 compiler 的训练

冻结 $F_\theta$ 后，用完整证据路径作为 teacher：

$$
\begin{aligned}
\mathcal L_{\mathrm{compiler}}
={}&
D_{\mathrm{KL}}
\left(
P_\theta
\left(
Y\mid H,Q
\right)
\Vert
P_\theta
\left(
Y\mid P_{1:K}^{(\theta)},Q
\right)
\right)
\\
&+
\lambda_g\ell_{\mathrm{ground}}
\\
&+
\lambda_i\operatorname{bits}
\left(
P_{1:K}^{(\theta)}
\right).
\end{aligned}
$$

若无法读取模型 logits 或 hidden states，则使用答案分布、证据定位和反事实一致性蒸馏。

### 8.5 防止 compiler 信息偷渡

必须执行：

1. compiler 在测试视频到来前冻结；
2. compiler 不能访问原始视频，只能访问 $U_k$；
3. 对 $U_k$ 做删除、交换和随机化测试；
4. 对同一 $U_k$ 比较不同 compiler；
5. 报告 compiler 单独从 $Q$ 作答的性能；
6. 报告输出比特和接口放大系数；
7. 若 compiler 内含大规模专属知识库，单独计为 side information。

---

## 9. 流式记忆：受限旧记忆条件下的 read-before-write

### 9.1 为什么需要根可观测性

如果 updater 既不能查看完整旧记忆，也没有任何有界索引或内容寻址原语，它就无法有目的地选择应读取的旧内容，只能随机或穷举。

**命题 5：无索引读取下的命中上界。**

若 $N$ 个记忆槽在读取前对控制器可交换，目标槽均匀分布，控制器没有任何依赖记忆内容的 root index 或内容寻址原语，那么使用 $b$ 次不重复槽读取时：

$$
P(\text{hit target})
\leq
\frac{b}{N}.
$$

因此，当 $b=o(N)$ 时，目标命中率趋近于零。要实现可扩展的选择性读取，系统必须支付并声明某种记忆相关的寻址信息。

**[推论]** 任意可扩展的部分可观记忆系统都必须声明一个“根可观测性假设”：

- 一个固定容量的 root index；
- 一个有成本的内容寻址接口；
- 或一个固定容量的当前 belief state。

本方案选择：

$$
I_t^{\mathrm{root}}
\quad\text{with}\quad
\operatorname{bits}
\left(
I_t^{\mathrm{root}}
\right)
\leq B_{\mathrm{root}}.
$$

所有未常驻信息都必须通过计费的 read 操作获得。

### 9.2 两阶段更新

对每个新观测 $O_t$：

**阶段 A：只读关联。**

$$
a_t^{\mathrm{write}}
=
\pi_w
\left(
O_t,I_{t-1}^{\mathrm{root}}
\right),
$$

$$
V_t^{\mathrm{old}}
=
\operatorname{Read}
\left(
M_{t-1}^{-},a_t^{\mathrm{write}}
\right).
$$

其中 $M_{t-1}^{-}$ 是不可变旧快照。

**阶段 B：候选生成与原子提交。**

$$
\mathcal C_t
=
E_\phi
\left(
O_t,V_t^{\mathrm{old}}
\right),
$$

$$
\Delta M_t
=
\operatorname{FQRAllocate}
\left(
\mathcal C_t,M_{t-1}^{-},
\mathcal T,\mathbf B
\right),
$$

$$
M_t
=
\operatorname{Commit}
\left(
M_{t-1}^{-},\Delta M_t
\right).
$$

这样可避免当前候选在尚未验证时参与检索并强化自身，减少自指循环、重复实体和错误合并。

### 9.3 更新需要回答的四个问题

1. 新观测是在更新已有状态，还是产生新事件；
2. 它是否改变对局部动力学 $\Omega_t$ 的判断；
3. 哪些旧记忆成为冗余，哪些旧事件仍不可恢复；
4. 在固定预算下，应删除、降码率、合并还是新建。

### 9.4 流式 updater 伪代码

~~~text
input: old snapshot M_minus, bounded root index I_root, new chunk O_t

probe       <- write_probe(O_t, I_root)
old_view    <- paid_read(M_minus, probe, write_read_budget)
candidates  <- canonical_encoder(O_t, old_view)
utilities   <- future_query_risk(candidates, M_minus, task_prior)
delta       <- robust_multirate_allocator(candidates, utilities, budgets)
M_t         <- atomic_commit(M_minus, delta)
I_root      <- bounded_root_update(I_root, delta)

return M_t, I_root
~~~

训练时可对单次更新内的旧快照使用 stop-gradient 或 target snapshot；跨时间仍需允许学习长期更新策略。

---

## 10. 统一优化目标

### 10.1 端到端目标

设一段视频最终形成 $M_T$，查询需要 $K(Q)$ 轮取回。建议的训练 Lagrangian 为：

$$
\begin{aligned}
\min_{
\phi,\psi,\pi_w,
\{\rho_\theta,\eta_\theta\}_{\theta\in\Theta}
}
\quad&
\sup_{P_Q\in\mathcal U(P_0)}
\mathbb E
\left[
\operatorname{RiskAgg}_{\theta\in\Theta}
\left[
r_\theta
\left(
Q;M_T,U_{1:K},P_{1:K}^{(\theta)}
\right)
\right]
\right]
\\
&+
\beta_s
\mathbb E
\left[
\operatorname{bits}(M_T)
\right]
\\
&+
\beta_w
\mathbb E
\left[
\sum_{t=1}^{T}
\operatorname{cost}_{\mathrm{write}}(t)
\right]
\\
&+
\beta_r
\mathbb E
\left[
\sum_{k=1}^{K}
\operatorname{bits}(U_k)
\right]
\\
&+
\beta_p
\mathbb E
\left[
\sum_{k=1}^{K}
\operatorname{bits}
\left(
P_k^{(\theta)}
\right)
\right]
\\
&+
\beta_c
\mathbb E
\left[
\operatorname{compute}(K)
\right].
\end{aligned}
$$

### 10.2 正式评测采用硬约束

训练可用软惩罚，论文主结果应满足：

$$
\operatorname{bits}(M_t)
\leq
B_{\mathrm{store}},
$$

$$
\sum_k\operatorname{bits}(U_k)
\leq
B_{\mathrm{read}},
$$

$$
\sum_k\operatorname{bits}
\left(
P_k^{(\theta)}
\right)
\leq
B_{\mathrm{interface}},
$$

$$
K
\leq
B_{\mathrm{round}}.
$$

主图应是多维约束下的 Pareto frontier，而不是只报一个预算点。

### 10.3 信息传递链的基本不等式

在给定合法 side information、固定策略及其随机种子后，把整个自适应交互视为一个 transcript：

$$
H_t
\rightarrow
Z_t^\star
\rightarrow
M_t
\rightarrow
U_{1:K}
\rightarrow
P_{1:K}^{(\theta)}
\rightarrow
\hat Y_Q
$$

若该 transcript 不访问原视频或其他未计费的情景信息，则构成条件 Markov 链。此时：

$$
I(Y_Q;H_t\mid Q,S,K_\Theta)
\geq
I(Y_Q;M_t\mid Q,S,K_\Theta)
\geq
I(Y_Q;U_{1:K}\mid Q,S,K_\Theta)
\geq
I(Y_Q;P_{1:K}^{(\theta)}\mid Q,S,K_\Theta).
$$

**[推论]** 每一层都只能保持或丢失历史信息；模型专属 compiler 的价值不是打破不等式，而是让给定信息更容易被有限能力的 $F_\theta$ 使用。

---

## 11. 误差分解与 oracle ladder

### 11.1 七类失败

总失败至少可分为：

1. **世界编码误差**：规范潜变量没有捕获状态、事件或规律；
2. **任务压缩误差**：FQR task lens 在固定持久预算下删错内容或码率；
3. **取回决策误差**：地址、粒度或停止时机错误；
4. **读码误差**：选对内容但选择性编码损坏了关键信息；
5. **编译误差**：读码有信息，但模型接口表达不合适；
6. **使用误差**：模型看到充分证据却未正确推理或 grounding；
7. **在线更新误差**：流式合并、覆盖、实体绑定或过期处理错误。

**[事实]** WorldMemArena 将记忆拆成写入、维护、检索和使用，并观察到“存得更好”不保证任务表现更好，这支持必须做阶段诊断。[WorldMemArena](https://arxiv.org/abs/2605.29341)

### 11.2 固定顺序的 oracle ladder

| 层级 | 配置 | 主要测量 |
|---|---|---|
| O0 | 同一消费模型直接访问完整合法原视频证据 | 模型能力上界 |
| O1 | ground-truth state、event、dynamics + oracle reader/compiler | 规范表示上界 |
| O2 | learned $Z^\star$ + oracle task allocation/reader/compiler | 世界编码误差 |
| O3 | learned $M$ + oracle reader/compiler | task lens 误差 |
| O4 | learned reader + 无损 selected payload + oracle compiler | 取回决策误差 |
| O5 | learned read codec + oracle/model-native injection | 读码误差 |
| O6 | learned compiler + 强制提供 gold evidence | 编译与使用边界 |
| O7 | 完整系统 | 端到端表现 |

每一级与上一级的差值形成操作性诊断。

**[边界]** 这些差值依赖替换顺序，并非天然唯一的因果分解。论文中应固定顺序，另用少量 Shapley 或交叉替换检查组件交互，不能把差值夸大为独立可加的真实误差。

### 11.3 必做干预

- 删除被 reader 使用的记忆，答案和 grounding 应显著下降；
- 用同类但错误的记忆交换，模型不应保持原答案；
- 保持 payload、随机化地址，检验是否依赖索引捷径；
- 保持地址、扰动视觉细节，检验是否真正使用视觉内容；
- 给 gold 读码但换 compiler，定位接口失败；
- 给 gold evidence 但保持消费模型，定位纯推理失败。

---

## 12. 可实现的系统版本

### 12.1 规范候选生成

每个视频 chunk 通过共享视觉编码器得到局部 token，随后产生三类候选：

1. **state candidate**：更新当前实体、属性、关系和未决 belief；
2. **event candidate**：编码相对预测的创新和不可逆历史事实；
3. **dynamics candidate**：编码重复转移、行为 schema 或规则变化。

训练信号包括：

- 多尺度未来预测；
- 受控环境中的 state reconstruction；
- 遮挡后实体一致性；
- temporal order 与 event boundary；
- 从 $B_t,\Omega_t$ 解码失败的 residual；
- ground-truth 或伪标注的时空证据。

### 12.2 多码率潜编码

每个候选生成离散码率层：

$$
z_i^{(1)}
\subset
z_i^{(2)}
\subset
\cdots
\subset
z_i^{(L)}.
$$

可以采用残差向量量化、可伸缩 token 层或稀疏低秩 payload。低码率保留身份、类型和粗时间；高码率补充局部外观、细动作和不确定性。

### 12.3 FQR writer

writer 的 utility critic 输入：

- 候选的 state、event、dynamics 类型；
- 与旧记忆的可替代性；
- 任务组上的反事实 regret；
- 证据 bundle 互补性；
- 视觉依赖与 side-information 可靠度；
- 受支持消费模型集合 $\Theta$ 上的失败风险；
- 每个码率层的存储和未来读取成本。

如果只输入一个目标模型的 capability，必须将该实验标记为 consumer-tuned memory，而不能用于证明跨模型复用。

writer 在固定预算内执行：

- admission；
- multi-rate downgrade；
- merge；
- eviction；
- provenance-preserving replacement。

### 12.4 读阶段

第一轮从查询中生成粗粒度时间、实体和关系 probe；后续轮根据模型的：

- 未解决实体槽位；
- 因果链缺口；
- 时间冲突；
- grounding 不充分；
- 置信度下降；

生成新 probe。每轮先确定地址，再确定读码率，最后由 compiler 决定接口形式。

### 12.5 与现有 FQR v2 的复用

可以直接复用：

- query-after-write 数据协议；
- fixed active visual bytes；
- side information 三级计费；
- future grounded regret；
- hierarchical DRO 或 CVaR；
- sampled coalition counterfactual；
- FQR-Shift；
- memory deletion、swap 和 grounding 测试。

需要重构：

- conditional codec 拆成 canonical encoder、read codec 和 compiler；
- utility critic 增加 state、event、dynamics 类型及 model capability；
- reader 改为多轮策略；
- writer 增加 read-before-write 更新路径；
- 评测增加接口和阶段级资源。

---

## 13. 训练课程：避免一开始端到端塌缩

### Stage A：规范潜记忆

先在可控世界中训练：

$$
\mathcal L_{\mathrm{canonical}}
=
\lambda_s\ell_{\mathrm{state}}
+
\lambda_p\ell_{\mathrm{prediction}}
+
\lambda_e\ell_{\mathrm{event}}
+
\lambda_d\ell_{\mathrm{dynamics}}
+
\lambda_u\ell_{\mathrm{uncertainty}}
+
\beta R(Z).
$$

目标不是追求像素完美，而是验证 $B,E,\Omega$ 的必要边界。随后在真实视频上用 masked reconstruction、future prediction、temporal consistency 和 grounding 代理继续训练。

### Stage B：FQR task lens

冻结或慢速更新 canonical encoder，离线采样未来查询和证据组合，生成：

- 单项删除 regret；
- coalition 删除 regret；
- 多码率损失曲线；
- query group 和组内难度标签。

训练 utility critic 排序候选，并在 ambiguity set 下优化固定预算 allocator。训练中的查询只用于构造任务先验和监督，不允许作为相应测试样本 writer 的输入。

### Stage C：model compiler

对每个冻结消费模型单独训练 compiler：

1. full-evidence teacher；
2. gold selected evidence；
3. learned latent read code；
4. 控制接口预算；
5. 做 memory deletion/swap，确保输出受 $U_k$ 因果影响。

先固定 reader，避免 compiler 和 reader 相互掩盖。

### Stage D：迭代 reader

先用 oracle marginal utility 轨迹做 imitation：

$$
\mathcal L_{\mathrm{reader}}^{\mathrm{IL}}
=
-
\sum_k
\log
\pi_\rho
\left(
a_k^\star\mid s_k
\right).
$$

再用 grounded regret 与资源成本做 policy optimization：

$$
R_k
=
-
r_\theta
-
\lambda_r\operatorname{bits}(U_k)
-
\lambda_p\operatorname{bits}(P_k)
-
\lambda_c K.
$$

完整版本可训练 memory-space diffusion；最小版本先采用两轮 query refinement。

### Stage E：流式更新

使用只读旧快照训练：

- 实体和事件关联；
- state update 与 event append 的区分；
- 冗余合并；
- 过期和冲突处理；
- 长期干扰与随机访问；
- root index 固定容量。

### Stage F：受控联合微调

只有 A–E 各自通过 oracle gate 后，才做低学习率联合微调。始终保留模块冻结消融，否则端到端性能无法说明形式化分解是否成立。

---

## 14. 实验设计

### 14.1 第一组：已知生成过程的可控长视频世界

这是整篇论文最关键的实验，因为真实视频没有“完美世界状态”标签，无法验证形式化边界。

建议构造包含对象、身份、遮挡、交互、随机事件和局部规则的视频生成器，记录：

- ground-truth $X_t$；
- belief 所需的隐变量；
- 每个随机 innovation；
- 动力学版本；
- query 的最小证据集合；
- 历史间的可控等价关系。

四个递增环境：

| 环境 | 世界性质 | 查询 | 理论预期 |
|---|---|---|---|
| C1 | 完全可观、确定、Markov | 只问未来 | current state 接近充分 |
| C2 | 遮挡、身份歧义 | 问当前和未来 | belief 优于 point state |
| C3 | 随机事件、终态相同 | 问过去事件 | state-only 必然失败，需 $E_t$ |
| C4 | 规律切换或新 schema | 反事实和未来 | 需 $\Omega_t$ 或规律后验 |

控制变量：

- 序列长度；
- 遮挡强度；
- 状态维度；
- 事件稀有度；
- 任务分布熵；
- 查询分布 shift；
- 消费模型能力；
- 存储、读取、接口和计算预算。

### 14.2 第二组：真实超长视频

不在方案阶段锁定单一数据集。选择原则是：

1. 一个严格 streaming 或 egocentric 长视频源；
2. 一个带时间或空间证据标注的多跳视频问答源；
3. 能区分最近窗口感知与长期历史记忆；
4. 能执行 query-after-write，且主实验禁止原视频回放；
5. 能构造 FQR-Shift 中的任务组和组合 shift。

候选与证据见现有[文献证据表](../literature/fqr_mem_2026_literature_evidence.md)。Grounded evaluation 可参考 E-VQA、EG-VQA 和 VideoZeroBench 的答案—证据联合要求。[Evidence-Backed Video Question Answering](https://arxiv.org/abs/2607.11862) · [EG-VQA](https://arxiv.org/abs/2606.24797) · [VideoZeroBench](https://arxiv.org/abs/2604.01569)

### 14.3 核心可证伪假设

#### H1：state-only 的适用边界

- C1 上 state-only 与完整规范记忆接近；
- C2 上 belief 明显优于 point state；
- C3 上增加 event innovations 才能恢复过去事件；
- C4 上显式 dynamics posterior 改善规则变化后的预测。

若结果不随环境假设变化，说明规范组件没有学到预期语义，或 benchmark 没有真正隔离变量。

#### H2：形式化分解优于单体 conditional codec

在相同持久存储和总训练计算下，分解模型应：

- 达到更好的性能—资源前沿，或
- 在性能相近时显著改善 oracle error localization 和跨模型复用。

若两者都不成立，则不能声称分解架构本身优越，只能保留形式化诊断贡献。

#### H3：FQR task lens 降低鲁棒任务码率

相对 uniform、reservoir、surprise 和通用信息量 writer，FQR 应在：

- 平均 grounded regret；
- worst-group；
- CVaR；
- 组合 shift；

上同时改善，尤其在视觉依赖、稀有、多证据问题中。

#### H4：规范存储可跨消费模型复用

用多个支持模型上的聚合风险写入并固定同一个 $M_t$，只替换 $C_\eta^{(\theta)}$：

- 两个能力或接口不同的消费模型都应受益；
- 不重新编码视频也能适配新模型；
- 较弱模型预期具有更大的读码或接口放大系数。
- 至少加入一个未参与 writer 风险训练的 held-out consumer，检验是否只是模型集合过拟合。

若必须为每个模型重新训练并重写 $M_t$，则“规范潜记忆可迁移”主张失败。

#### H5：迭代读码优于一次性读取

在相同总 $B_{\mathrm{read}}$ 和 $B_{\mathrm{interface}}$ 下，多轮 reader 应主要改善：

- 多跳证据；
- 长时间跨度；
- 初始查询歧义；
- 证据冲突；
- grounding 充分性。

若收益只来自更多模型调用而非更好的证据选择，固定计算后应消失。

#### H6：read-before-write 减少流式干扰

相对直接全局更新，它应降低：

- 错误实体合并；
- 当前片段重复写入；
- 旧事件被覆盖；
- 状态—事件类型混淆；
- 长序列中的关联漂移。

#### H7：compiler 真正改善可用性，而非扩大上下文

在匹配接口字节和调用计算后，learned compiler 应优于：

- 直接注入 latent；
- 通用线性投射；
- 解码为 caption；
- 解码为少量像素帧。

若只在更大接口预算下获益，不能声称是更好的模型适配。

### 14.4 主基线

#### Query-hidden 公平基线

- uniform sampling；
- reservoir sampling；
- recency；
- surprise 或 prediction-error writer；
- query-agnostic token merging；
- 固定预算 KV compression；
- scene/event summary；
- SelectStream、CausalMem、FluxMem 类动态 latent memory；
- FQR-Mem v2 单体 conditional codec；
- state-only、event-only、text-only 与 visual-only。

**[事实]** SelectStream 和 CausalMem 是最接近的 query-hidden fixed-budget 系统级对照；SURGE 是重要的 surprise 基线；StreamingVLM 和 FlexMem 分别代表紧凑窗口/KV 路径。[SelectStream](https://arxiv.org/abs/2606.16353) · [CausalMem](https://arxiv.org/abs/2606.25658) · [SURGE](https://proceedings.iclr.cc/paper_files/paper/2026/hash/07b92344686c19cf3ffc335a0f565406-Abstract-Conference.html) · [StreamingVLM](https://proceedings.iclr.cc/paper_files/paper/2026/hash/6445dd88ebb9a6a3afa0b126ad87fe41-Abstract-Conference.html) · [FlexMem](https://arxiv.org/abs/2603.29252)

#### Query-known 特权 oracle

- 给定真实问题后的 frame/event selection；
- 可回放原视频的 agentic navigation；
- gold evidence index；
- full video 或 full latent history；
- actual future query 泄漏给 writer。

这些只能作为上界，不能与 query-hidden writer 混为公平基线。

### 14.5 指标

| 维度 | 指标 |
|---|---|
| 答案 | accuracy、F1、calibration、同一模型 full-evidence regret |
| 证据 | temporal IoU、spatial grounding、evidence precision/recall、answer-and-evidence joint score |
| 尾部稳健 | worst-group、CVaR、组合 shift、置信区间 |
| 世界充分性 | state error、predictive NLL、event recovery、dynamics identification |
| 持久存储 | bits/frame、总字节、memory growth curve |
| 读取 | query 总读比特、访问原子数、读放大 |
| 模型接口 | token/KV/activation bytes、$\alpha_\theta$ |
| 计算 | writer latency、reader latency、模型调用、FLOPs |
| 流式维护 | interference、update correctness、entity consistency、forgetting curve |
| 因果使用 | deletion drop、swap sensitivity、counterfactual grounding |

主结果至少画：

1. grounded regret—持久存储前沿；
2. grounded regret—总读取比特前沿；
3. grounded regret—接口字节前沿；
4. worst-group—总系统成本前沿；
5. 序列长度增长时的稳定性；
6. 不同消费模型的可用码率与接口放大。

### 14.6 决定性消融

- point state vs belief；
- state-only vs state+event vs state+event+dynamics；
- 规范层与任务层合并 vs 分离；
- 无 task lens；
- expected risk vs CVaR vs hierarchical ambiguity；
- 独立原子效用 vs coalition utility；
- 一次读取 vs 两轮 vs完整自适应；
- 无 memory-space diffusion；
- 固定读码率 vs自适应读码率；
- 直接 latent injection vs通用 projector vs模型专属 compiler；
- writer 查看完整旧记忆 vs仅受限 retrieved view；
- write-before-read vs read-before-write；
- 无 root budget；
- 无 provenance；
- compiler 不做删除/交换约束。

---

## 15. 最小可发表单元与范围控制

### 15.1 首篇论文必须包含

1. 规范记忆、任务记忆、读码和模型编译的形式定义；
2. state-only 充分性的条件与 past-event 反例；
3. $B+E+\Omega+I$ 规范潜记忆；
4. FQR task lens 的 robust rate-distortion 目标；
5. 至少两轮推理耦合的 adaptive read codec；
6. 一个可跨两个消费模型的 compiler 实验；
7. 可控 POMDP 长视频 benchmark；
8. 一个真实超长视频设定；
9. oracle ladder 与固定多资源计费；
10. query-after-write、no replay 和 grounded regret。

### 15.2 首篇论文可以简化

- memory-space diffusion 只做可选两跳图扩散；
- $\Omega_t$ 可先用规则 ID 或低维 dynamics posterior；
- compiler 先支持两种模型接口；
- 流式 updater 先做固定 root index；
- 不必同时覆盖视觉、文本、音频的所有组合；
- 不必声称建立通用 AI 记忆终极理论。

### 15.3 后续工作

- 无显式状态监督的真实世界 causal state learning；
- 可学习的非平稳 dynamics memory；
- 长期参数化记忆与情景记忆的统一计费；
- 多智能体共享规范记忆；
- 记忆隐私、删除与可审计性；
- compiler 在模型升级和黑盒 API 间的零样本迁移；
- 月级或终身视频流。

---

## 16. 14 周推进计划与止损门槛

### Gate A，1–2 周：形式化边界可观测

完成 C1–C4 生成器和 state-only 反例。

通过条件：

- C1 中 state 接近充分；
- C2、C3、C4 分别暴露 belief、event、dynamics 的必要性；
- query-after-write 和 evidence oracle 可自动验证。

失败处理：先修 benchmark 或重新界定充分性，不进入复杂真实视频系统。

### Gate B，3–4 周：规范潜记忆

训练 $B,E,\Omega$，绘制 world rate-distortion。

通过条件：

- oracle decoder 能分别恢复预期目标；
- 分量交换和删除产生符合理论的任务退化；
- 多码率潜变量曲线稳定。

### Gate C，5–6 周：FQR task lens

加入 sampled coalition counterfactual 和层次风险。

通过条件：

- 在相同存储下优于 surprise、通用压缩和 v2 monolithic codec；
- 收益集中在预先声明的长尾组，不只来自平均题；
- 无测试 query 泄漏。

### Gate D，7–8 周：model compiler

固定同一存储，训练两个消费模型的 compiler。

通过条件：

- 至少一个模型上 matched-interface 优于通用 projector；
- 同一存储无需重写；
- deletion/swap 证明模型使用读码。

### Gate E，9–10 周：迭代 reader 与流式更新

实现两轮 reader、VOI 停止和 read-before-write。

通过条件：

- 匹配总读取和计算后改善多跳或歧义查询；
- 流式干扰低于直接更新；
- root、read、interface 成本完整记录。

### Gate F，11–12 周：真实视频验证

接入一个 streaming/egocentric 和一个 grounded long-video setting，运行 FQR-Shift。

通过条件：

- 至少在视觉依赖、稀有或组合证据子集上形成稳定 Pareto 改善；
- oracle ladder 能解释主要残余误差；
- 三个随机种子和 bootstrap 置信区间完成。

### 13–14 周：论文证据闭环

- 冻结协议和主表；
- 完成全部决定性消融；
- 复核资源计费与数据泄漏；
- 整理失败结果和适用边界；
- 根据结果选择偏理论学习或偏视觉系统的叙事，不预先锁定投稿会议。

---

## 17. 论文动机与贡献结构

### 17.1 现有工作的根本缺口

**[事实]** 2026 年长视频记忆已经覆盖动态记忆、层次事件、KV 压缩、surprise、query-aware navigation、证据充分性和固定预算 latent bank；“再设计一个 memory bank”本身已不足以构成强贡献，详见现有[40 篇证据表](../literature/fqr_mem_2026_literature_evidence.md)。

**[推论]** 更根本的空白是：

- 没有统一说明“世界信息保留”“任务压缩”“读阶段选择”“模型可用表示”分别是什么；
- 性能失败时无法定位是哪一层；
- 存储 token、读取 token、模型上下文和推理计算常被混合计费；
- “完美记忆只需状态”“投射能补偿模型知识”等直觉缺少适用边界；
- 流式系统通常默认可以免费查看全部旧记忆来更新新记忆。

### 17.2 预期贡献

如果实验支持，本工作可以主张：

1. **形式化贡献**：把视觉记忆定义为规范编码、任务预算化、自适应读码和模型编译组成的条件信道链；
2. **边界贡献**：给出 state-only 充分性的条件、过去事件反例和部分可观旧记忆的 root observability 要求；
3. **方法贡献**：提出 $B+E+\Omega+I$ 规范潜记忆、FQR task lens、reasoning-coupled read codec、model-specific compiler 与 read-before-write；
4. **评价贡献**：提出多资源 operational memory rate、接口放大系数和七阶段 oracle ladder；
5. **实证贡献**：在可控 POMDP 视频和真实超长视频上验证哪些记忆成分在何种任务下必要。

### 17.3 两种可能的论文叙事

#### 偏 ICLR 的表示学习与形式化路线

重点：

- 充分性、rate-distortion 和模型相对可用码率；
- state、belief、event、dynamics 的边界；
- controlled world 的强因果实验；
- 规范存储跨模型复用。

这更接近以基本问题、学习原则和可证伪实验为中心的论文。

#### 偏 CVPR 的视觉记忆系统路线

重点：

- 超长视频 fixed-budget latent memory；
- grounded evidence；
- query-after-write；
- FQR-Shift；
- 流式更新、真实吞吐和真实长视频 Pareto frontier。

最终叙事应由 Gate A–F 的结果决定，而不是预先锁定。

---

## 18. 主要风险与反驳标准

### 风险 1：规范潜记忆仍是人为模块命名

反驳要求：每个分量必须通过 C1–C4 的必要性实验、删除/交换干预和 oracle decoder 定义，而不是只画模块图。

### 风险 2：形式化只是信息瓶颈换名

反驳要求：明确展示新增问题——未来查询歧义集、模型相对可用码率、迭代读取、接口放大、部分可观旧记忆和流式两阶段更新。

### 风险 3：compiler 只是更大的 projector

反驳要求：匹配接口字节和计算；同一存储跨模型；报告 $\alpha_\theta$；执行信息偷渡测试。

### 风险 4：迭代取回收益来自更多计算

反驳要求：匹配总模型调用、读比特和接口字节；报告一次性 oracle selection 上界。

### 风险 5：任务先验压缩破坏开放任务能力

反驳要求：绘制任务熵和 ambiguity set 半径变化下的 rate-distortion；承认任务越开放，所需记忆越接近世界层记忆。

### 风险 6：真实视频没有世界状态，规范层不可验证

反驳要求：controlled world 负责机制验证；真实视频只报告预测、重建、grounding 和任务 regret 代理，不把代理称为真实充分性。

### 风险 7：root index 成为免费无限记忆

反驳要求：固定 $B_{\mathrm{root}}$；把所有动态文本和 payload 计入持久预算；单独绘制 root budget 消融。

### 风险 8：范围过大

反驳要求：首篇只保留最小两轮 reader、两个 consumer、一个 controlled benchmark 和一个真实主设定；复杂 diffusion、终身学习和参数记忆统一放到后续。

---

## 19. 当前最值得立即验证的三个实验

### 实验 1：state-only 边界

构造两个终态相同但过去事件不同的视频，并同时设置未来预测题和过去事件题。

预期：

- state-only 在未来预测上足够；
- state-only 在过去事件题上不可辨识；
- 加入最小 event innovation 后恢复。

这是整个形式化最清楚、成本最低、最能说明根本问题的实验。

### 实验 2：同一潜存储、不同模型编译

固定一份 latent store，选两个能力或接口不同的消费模型，只训练各自 compiler。

测量：

- operational memory rate；
- 接口放大系数；
- matched-budget grounded regret；
- 是否无需重写历史。

该实验直接验证“完美记忆”和“模型可用记忆”不是同一对象。

### 实验 3：一次读取与推理耦合读取

在同一总读比特和接口字节下比较：

- 一次 top-$K$；
- 两轮 query refinement；
- oracle evidence sufficiency stop。

专门选择多跳、时间冲突和初始歧义问题。若两轮读取没有稳定收益，就暂缓复杂 memory diffusion。

---

## 20. 文献锚点

### 20.1 形式化基础

- [Information Bottleneck](https://arxiv.org/abs/physics/0004057)：相关变量条件下的压缩与充分表示；
- [Predictive Representations of State](https://proceedings.neurips.cc/paper/2001/file/1e4d36177d71bbb3558e43af9577d70e-Paper.pdf)：以未来预测定义状态；
- [Planning and Acting in Partially Observable Stochastic Domains](https://www.cassandra.org/arc/papers/aij98.pdf)：POMDP 与 belief state；
- [Semantic Compression with Side Information](https://arxiv.org/abs/2208.06094)：任务导向视频压缩和 side information；
- [Sequential Source Coding for Stochastic Systems Subject to Finite Rate Constraints](https://mitter.lids.mit.edu/publications/C45_seq_source_ecc05.pdf)：因果顺序编码和有限码率。

### 20.2 潜记忆和模型接口

- [M+](https://arxiv.org/abs/2502.00592)；
- [One Token per Multimodal Evidence](https://arxiv.org/abs/2606.10572)；
- [SeDeM](https://arxiv.org/abs/2608.00311)；
- [In-context Autoencoder](https://arxiv.org/abs/2307.06945)；
- [MemDefrag](https://arxiv.org/abs/2607.05969)；
- [Task-Aware Structured Memory](https://arxiv.org/abs/2606.11853)。

### 20.3 推理耦合取回

- [IRCoT](https://aclanthology.org/2023.acl-long.557/)；
- [FLARE](https://aclanthology.org/2023.emnlp-main.495/)；
- [Self-RAG](https://proceedings.iclr.cc/paper_files/paper/2024/file/25f7be9694d7b32d5cc670927b8091e1-Paper-Conference.pdf)；
- [Context Gathering Decision Process](https://arxiv.org/abs/2605.07042)。

### 20.4 长视频记忆、稳健性与证据

- [FQR-Mem 2026 年相关文献证据表](../literature/fqr_mem_2026_literature_evidence.md)；
- [SelectStream](https://arxiv.org/abs/2606.16353)；
- [CausalMem](https://arxiv.org/abs/2606.25658)；
- [OASIS](https://arxiv.org/abs/2604.17052)；
- [WorldMemArena](https://arxiv.org/abs/2605.29341)；
- [Evidence-Backed Video Question Answering](https://arxiv.org/abs/2607.11862)；
- [Hierarchical Ambiguity Sets](https://proceedings.iclr.cc/paper_files/paper/2026/hash/c4f85da01632a2211c785f482cb3e043-Abstract-Conference.html)。

---

## 21. 最终建议

1. 将本方向命名为 **FQR-Mem v3: Formal Latent Memory under Future-Query Risk**，暂不另造过多缩写；
2. 把 $Z^\star$ 作为理论 oracle，把 $M$ 作为实际任务条件持久记忆，避免声称部署时保存“完美记忆”；
3. 把 state-only 直觉改成带假设的命题，并用 past-event 反例建立论文动机；
4. 把模型投射改称 model-specific memory compiler，严格说明它不增加视频信息；
5. 把 retrieval 定义成由推理状态驱动的选择性再编码，并同时计费读码和模型接口；
6. 把流式更新写成旧快照上的 read-before-write，显式限制 root observability；
7. 第一优先级不是实现完整系统，而是完成第 19 节的三个决定性实验；
8. 只有在 controlled world 的变量解耦成立后，再把该形式化扩展到真实超长视频。

如果三个决定性实验成立，这个工作就不再是“手工设计一个更好的 memory bank”，而是在回答一个更基础的问题：

> 对给定世界、任务族、消费模型和资源预算，什么信息必须被持久保存，什么信息应在推理时重新编码，以及多少额外表示只是模型接口为使用这些信息所支付的代价？
