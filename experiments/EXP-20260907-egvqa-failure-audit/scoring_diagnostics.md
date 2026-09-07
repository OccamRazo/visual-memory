# EG-VQA 判分与答案文本诊断

这是事后文本审计：没有重跑视觉模型、没有修改原分数，也不构成人工盲审或独立视觉重答。

全量检查 512 个条件：483 个正常完成，29 个构造失败（4 题）单列。所有非空答案传给 judge 的问题、参考、预测与原记录完全一致。

## 确定存在的评分不一致

同题完全相同非空答案有 57 个重复组；其中 6 组、21 条记录出现不一致评分。仅规范化大小写、标点和空白仍得到相同冲突数。

E2 有 7 组／14 个条件拥有相同问题、快照哈希和有序单元 ID；生成答案全部完全一致，但其中 2 组评分不同：种植题 J3Kg76JODsk_q01 的 R0/R1，以及相扑题 v_0zjA3KPnLK8_q02 的 R0/R2。这些差异发生在评分阶段。

### v_0zjA3KPnLK8_q02

问题：What is the main activity taking place in the scene with the two men and the crowd?

参考：The main activity is wrestling, with two men throwing each other down in front of a crowd.

完全相同预测：Sumo wrestling match

| 条件 | 判分 | 原 judge 理由 |
|---|---|---|
| E1 Irrel-2 | correct | Identifies wrestling as main activity |
| E1 Irrel-1 | incorrect | Sumo is not specified in reference |
| E1 Key-2 | incorrect | Sumo not specified in reference |
| E1 Key-1 | correct | Sumo matches wrestling description |
| E1 Full | correct | Wrestling match matches reference |
| E2 R* | correct | Sumo wrestling matches involve wrestling and crowds. |
| E2 R0 | correct | Sumo wrestling matches involve wrestling and crowds. |
| E2 R1 | correct | Sumo wrestling match matches reference |
| E2 R2 | incorrect | Misidentifies as sumo wrestling |

### v_0zjA3KPnLK8_q04

问题：What sequence of events leads to the ongoing wrestling between the two men?

参考：The men start kneeling, then one throws the other down, leading to ongoing wrestling.

完全相同预测：The wrestlers prepare, engage in combat, and continue wrestling as shown in frames g68c1e955a4ea, g9c08fdb10483, and g79d0c302e2d0.

| 条件 | 判分 | 原 judge 理由 |
|---|---|---|
| E1 Full | correct | Sequence matches reference description |
| E1 Irrel-1 | incorrect | References frames not in reference |

### v_Ktun1-2Y540_q01

问题：How does the woman's interaction with the hula hoop change throughout the event?

参考：She initially spins with it, then continues dancing and smiling at people.

完全相同预测：She starts spinning it, then holds it, and later spins it again with different movements.

| 条件 | 判分 | 原 judge 理由 |
|---|---|---|
| E1 Key-2 | correct | Matches spinning and smiling sequence |
| E1 Irrel-1 | incorrect | Holds hoop not mentioned in reference |
| E1 Full | incorrect | Adds holding hoop, contradicts reference |
| E2 R* | incorrect | Adds unsupported action of holding hoop |

### v_NGk3v4sKqdg_q04

问题：What activities are people engaged in with bicycles?

参考：People work on bicycles, put chains on them, pump air into the tires, and ride the bicycles.

完全相同预测：People are repairing, inspecting, and riding bicycles.

| 条件 | 判分 | 原 judge 理由 |
|---|---|---|
| E1 Key-2 | correct | Activities align with reference |
| E1 Irrel-2 | incorrect | Omits key activities, adds none |

### J3Kg76JODsk_q01

问题：What steps are involved in planting seeds in pots?

参考：Add organic soil, arrange it, place seeds, cover with soil.

完全相同预测：Prepare pot, add soil, place seed, cover with soil, water gently.

| 条件 | 判分 | 原 judge 理由 |
|---|---|---|
| E2 R0 | correct | Matches reference steps exactly |
| E2 R1 | incorrect | Omits arranging soil step |

### v_0zjA3KPnLK8_q04

问题：What sequence of events leads to the ongoing wrestling between the two men?

参考：The men start kneeling, then one throws the other down, leading to ongoing wrestling.

完全相同预测：Initial grappling, followed by attempts to throw or pin, with wrestlers resetting positions repeatedly.

| 条件 | 判分 | 原 judge 理由 |
|---|---|---|
| E2 R0 | correct | Matches wrestling sequence accurately |
| E2 R1 | incorrect | Contradicts reference sequence of kneeling first |

## 同答统一评分的敏感性（不替代主结果）

把每个已证实冲突的完全相同答案组统一成 0 或 1，穷举 64 种赋值；组的真值未知，禁止以多数票充当金标。其他记录一律保留原分数。

- 仅让 R1/R2 完全相同的预测同分：R2−R1 从 −6/48 变为 −5/48，即 -10.42%；95% CI [-0.22916666666666666, 0.020833333333333332]。
- 对全部 6 组强制一致，R2−R1 点估计范围 [-0.14583333333333334, -0.10416666666666667]，各方案 CI 端点总包络 [-0.25, 0.020833333333333332]。这是情景包络，不是新置信区间。
- E1 的 D 点估计范围 [0.02272727272727273, 0.03787878787878788]；联合候选数范围 [0, 0]。

能确定至少一个 R2 退步来自 judge 不一致，但该缺陷不能单独解释全部净退步；统一其他冲突也可能降低 R1 漏判带来的表观劣势，不能只修正有利于 R2 的一题。

## E1 失败分布

44 题中 Full 正确 11 题；22 题所有有图条件均不正确。D 的正/零/负计数：{'negative': 7, 'zero': 30, 'positive': 7}。

Full 正确题中，至少一次 Key 变错 6 题，至少两次变错 3 题；两次 Irrel 均正确 7 题。Full 错但至少一个 Key 对有 8 题。

逐题宏平均 Full−Key=-0.0189，Full−Irrel=-0.0227。D 的 Full 项会代数相消，D 本身衡量 Irrel 与 Key 的差；需要同时看 Full 的低可答率和个案条件。

## 30 词限制

按空白分词，48 条参考长度：{'n': 48, 'min': 7, 'median': 12.5, 'mean': 12.895833333333334, 'max': 20, 'above_30': 0}。所有参考均不超过 30 词，因此不能把总体失败简单归因为参考本身装不进 30 词。

| 条件 | 答案数 | 平均词数 | 超过 30 词 | 空字符串 | 文本内引用 ID | insufficient |
|---|---:|---:|---:|---:|---:|---:|
| E1:Blind | 44 | 2.84 | 0 | 33 | 0 | 5 |
| E1:Full | 44 | 14.25 | 0 | 0 | 3 | 1 |
| E1:Irrel | 88 | 14.23 | 0 | 0 | 4 | 0 |
| E1:Key | 115 | 14.25 | 0 | 0 | 5 | 0 |
| E2:R* | 48 | 13.33 | 0 | 0 | 0 | 0 |
| E2:R0 | 48 | 13.17 | 0 | 0 | 1 | 0 |
| E2:R1 | 48 | 12.96 | 0 | 0 | 1 | 0 |
| E2:R2 | 48 | 13.12 | 0 | 0 | 1 | 0 |

短答案约束、文本内额外复述引用 ID 可能占用可表达事实的空间；但本分析没有做解除长度限制的对照，无法量化因果贡献。

## E2 全部 8 个 loss 与 2 个 gain

这里只报告文本和原 judge 差异，不把参考之外的视觉描述自动当成幻觉。参考是不穷尽的文字，判分器不能看视频。

### l2OTMq4aluc_q06 (loss)

问题：What actions are performed on the cloth in the video?

参考：The cloth is cut, measured, and stitched.

R1 (correct): Measuring, cutting, and sewing the cloth.

R1 理由：Measuring, cutting, sewing matches reference

R2 (incorrect): Measuring, folding, and adjusting the cloth.

R2 理由：Omits stitching and adds folding

相同预测=False；相同选中单元=False。

### v_0zjA3KPnLK8_q02 (loss)

问题：What is the main activity taking place in the scene with the two men and the crowd?

参考：The main activity is wrestling, with two men throwing each other down in front of a crowd.

R1 (correct): Sumo wrestling match

R1 理由：Sumo wrestling match matches reference

R2 (incorrect): Sumo wrestling match

R2 理由：Misidentifies as sumo wrestling

相同预测=True；相同选中单元=False。

### v_D5xp0LuEcKw_q04 (loss)

问题：How does the interaction between the man and woman change from the beginning to the end of the video?

参考：They transition from meeting to dancing elegantly and then to synchronized dancing.

R1 (correct): From initial separate movements to close embrace and synchronized dancing, culminating in a final pose.

R1 理由：Close embrace and synchronized dancing match reference.

R2 (incorrect): From standing apart to embracing and dancing closely, then performing a dance routine with text overlays.

R2 理由：Adds text overlays not in reference

相同预测=False；相同选中单元=False。

### DBgap0YANhs_q01 (loss)

问题：How does the dish change from the vegetable mixture to the final layered biryani?

参考：Vegetable mixture placed in pot; rice layered on top; soaked raisins and fried onions added on rice.

R1 (correct): The vegetable mixture is seasoned, cooked with rice, and layered to form the final biryani dish.

R1 理由：Layering rice and toppings matches reference.

R2 (incorrect): The vegetable mixture is layered with rice, garnished with nuts and herbs, and cooked to form the final biryani.

R2 理由：Garnished with nuts and herbs not in reference

相同预测=False；相同选中单元=False。

### v_-UWE4jXuLoo_q03 (loss)

问题：What sequence of activities does the boy perform at the skate park?

参考：The boy balances on a board, then performs moves such as jumping, flipping, and ramping.

R1 (correct): Skateboarding, performing tricks on ramps, and transitioning between different areas of the skate park.

R1 理由：Balancing, jumping, flipping, ramping covered

R2 (incorrect): Skateboarding, then performing tricks on ramps, followed by steps labeled 'STEP ONE' and 'STEP THREE'.

R2 理由：Omits key skateboarding moves

相同预测=False；相同选中单元=False。

### v_NGk3v4sKqdg_q04 (gain)

问题：What activities are people engaged in with bicycles?

参考：People work on bicycles, put chains on them, pump air into the tires, and ride the bicycles.

R1 (incorrect): People are repairing or assembling bicycles, including adjusting wheels and components.

R1 理由：Omits pumping tires, adds unmentioned repairs

R2 (correct): People are repairing, assembling, and riding bicycles.

R2 理由：Repairing, assembling, and riding matches reference

相同预测=False；相同选中单元=False。

### v_Ktun1-2Y540_q01 (loss)

问题：How does the woman's interaction with the hula hoop change throughout the event?

参考：She initially spins with it, then continues dancing and smiling at people.

R1 (correct): She starts spinning it around her waist, then lifts and swings it overhead, and later spins it around her waist again.

R1 理由：Spins, dances, smiles at people

R2 (incorrect): She starts by spinning it around her waist, then lifts it above her head, and later spins it around her hips and arms.

R2 理由：Adds actions not in reference

相同预测=False；相同选中单元=False。

### v_0zjA3KPnLK8_q01 (gain)

问题：How does the interaction between the two men change from the beginning to later in the video?

参考：The interaction escalates from kneeling down to wrestling and throwing each other down.

R1 (incorrect): Initially, one man walks away; later, they face each other, engage in a sumo match, and one is pushed out.

R1 理由：Misrepresents wrestling as sumo match

R2 (correct): Initially, one man is seated calmly. Later, they engage in a wrestling match, then one stands victorious while the other is down.

R2 理由：Wrestling escalation matches reference

相同预测=False；相同选中单元=False。

### v_bJ695Pp7Vng_q01 (loss)

问题：What activities are depicted in the images related to the water polo game?

参考：Images show girls competing, making faces, holding arms up, getting hit, and exiting the pool.

R1 (correct): Players swimming, passing, and shooting a ball in water polo.

R1 理由：Semantically matches water polo activities

R2 (incorrect): Players swimming, holding, and shooting a ball in water polo.

R2 理由：Omits specific facial and exit actions

相同预测=False；相同选中单元=False。

### v_Ktun1-2Y540_q03 (loss)

问题：How does the woman's interaction with the hula hoop evolve?

参考：Initially standing, she later spins and dances with the hula hoop.

R1 (correct): She starts spinning it around her waist, then lifts and swings it overhead, and later spins it around her waist again.

R1 理由：Matches reference description

R2 (incorrect): She starts spinning it around her waist, then lifts and maneuvers it above her head, and later spins it around her hips and legs.

R2 理由：Omits initial standing and adds unsupported actions

相同预测=False；相同选中单元=False。

## 事实与待验证解释

事实：相同 question/reference/prediction 在不同四题 judge batch 中被不同判分；若干理由把‘参考未提及’直接当成错误，另一些又宽松接受省略。这使原始差值混入评价噪声。

假说：批次上下文、答案简化与额外描述的处理不一致可能造成该现象。本审计没有更换批次顺序复判，不能拆分各因素。

事实：部分 R1/R2 差异是明确动作或食材变化，另一些只是近义措辞、额外画面描述。这些需要逐设置独立视觉重答，再与参考比对；仅看文本不能判断谁更忠实画面。

限制：只有 12 视频；这里所有敏感性均事后设计；同答统一只修复可证明的不一致，不保证其他分数正确。原置信区间只描述视频抽样波动，不能覆盖 judge 系统性偏差。
