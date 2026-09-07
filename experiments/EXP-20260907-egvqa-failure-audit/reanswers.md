# 四题各设置的独立 AI 重答

每个不同输入使用新上下文，只展示原问题及原尺寸帧包。参考、原预测及条件名在作答时隐藏；原检索选择不变。相同输入共用一个答案：44个逻辑条件，42次独立视觉/无图作答。

下表“复核”是两名新上下文AI文本审核者的 A/B 判定：✓正确、×错误、?参考有歧义。原答案与新答案混合匿名、同题同文只判一次。审核不是人工校准，表格不估计总体正确率。模型、展示接口和推理预算与原Qwen不同。

## v_0zjA3KPnLK8_q02

选择层：`same_answer_scoring_disagreement`。

问题：What is the main activity taking place in the scene with the two men and the crowd?

参考：The main activity is wrestling, with two men throwing each other down in front of a crowd.

| 条件 | 独立重答（英文原文） | 引用ID | 新答复核 A/B | 原答复核 A/B |
|---|---|---|---|---|
| E1 Full | Two men are competing in a sumo wrestling match while a crowd watches. | g3a7028df0f0f, g5127ddfc7668, gec53fb17d683 | ✓/✓ | ✓/✓ |
| E1 Key-1 | The two men are competing in a sumo wrestling match while a crowd watches. | g5127ddfc7668, gec53fb17d683 | ✓/✓ | ✓/✓ |
| E1 Key-2 | Two men are competing in a sumo wrestling match while a crowd watches. | g3a7028df0f0f, g5127ddfc7668 | ✓/✓ | ✓/✓ |
| E1 Irrel-1 | Two men are competing in a sumo wrestling match while a crowd watches. | g3a7028df0f0f, g5127ddfc7668 | ✓/✓ | ✓/✓ |
| E1 Irrel-2 | Two men are competing in a sumo wrestling match while a crowd watches. | g3a7028df0f0f, gec53fb17d683 | ✓/✓ | ✓/✓ |
| E1 Blind | The available evidence is insufficient to determine the main activity. |  | ×/× | ×/× |
| E2 R0 | The two men are participating in a sumo wrestling match in front of a crowd of spectators. | c000056, c000059 | ✓/✓ | ✓/✓ |
| E2 R1 | Two men are competing in a sumo wrestling match while a crowd watches. | c000054, c000076 | ✓/✓ | ✓/✓ |
| E2 R2 | The two men are participating in a sumo wrestling match in front of a crowd of spectators. | c000056, c000059 | ✓/✓ | ✓/✓ |
| E2 R* | Two men are competing in a sumo wrestling match while a crowd watches. | c000028 | ✓/✓ | ✓/✓ |

## l2OTMq4aluc_q06

选择层：`other_R2_loss`。

问题：What actions are performed on the cloth in the video?

参考：The cloth is cut, measured, and stitched.

| 条件 | 独立重答（英文原文） | 引用ID | 新答复核 A/B | 原答复核 A/B |
|---|---|---|---|---|
| E1 Full | The cloth is laid flat, shaped using paper patterns, cut into pieces, and machine-sewn to transform the pink dress into a halter-style romper. | gbd6c382116e8, gdef5a38a5b53, g4309c7ec4156, g371ce89083d4 | ×/× | ×/× |
| E1 Key-1 | The pink dress is laid out, cut into pattern pieces, pinned, and machine-sewn into a shorter halter-style outfit, which is then tried on. | gbd6c382116e8, gdef5a38a5b53, g4309c7ec4156, gba6ff86476cf | ×/× | ×/× |
| E1 Key-2 | The cloth is laid out, pinned to paper patterns, cut into pieces, and sewn together to transform a long pink dress into a short halter outfit. | gbd6c382116e8, gdef5a38a5b53, g4309c7ec4156, gba6ff86476cf | ×/× | ×/× |
| E1 Key-3 | The pink cloth is laid flat, marked using patterns, cut into pieces, and sewn together to remake the dress into a new outfit. | gbd6c382116e8, g4309c7ec4156, gba6ff86476cf | ×/× | ×/× |
| E1 Key-4 | The pink garment is laid flat, positioned under sewing patterns, cut and reshaped into a halter-neck romper, then tried on and modeled. | gbd6c382116e8, gacc3dc029532, gdef5a38a5b53, gba6ff86476cf, g371ce89083d4 | ×/× | ×/× |
| E1 Irrel-1 | The cloth is laid out, pinned to paper patterns, cut into pieces, and sewn together to turn a long pink dress into a short halter outfit. | gdef5a38a5b53, g4309c7ec4156, gba6ff86476cf | ×/× | ×/× |
| E1 Irrel-2 | The cloth is laid out with pattern pieces, cut into sections, and sewn into a new outfit, which is then tried on and modeled. | gdef5a38a5b53, g4309c7ec4156, gba6ff86476cf | ×/× | ×/× |
| E1 Blind | The available evidence is insufficient to determine what actions are performed on the cloth. |  | ×/× | ×/× |
| E2 R0 | The cloth is measured, marked, cut into pieces, folded and arranged, then sewn together using a sewing machine. | c000076, c000078, c000082, c000132, c000136, c000138 | ✓/✓ | ×/× |
| E2 R1 | The cloth is measured, unfolded and spread flat, repositioned and aligned, then sewn together using a sewing machine. | c000076, c000106, c000111, c000136, c000138 | ×/× | ✓/✓ |
| E2 R2 | The cloth is measured, cut into sections with scissors, then lifted, turned, spread out, and smoothed by hand. | c000075, c000078, c000082, c000132, c000136 | ×/× | ×/× |
| E2 R* | The cloth is laid flat, measured and marked, cut with a rotary cutter, then folded and rearranged by hand. | c000076, c000078, c000089, c000136 | ×/× | ×/× |

## v_NGk3v4sKqdg_q04

选择层：`R2_gain`。

问题：What activities are people engaged in with bicycles?

参考：People work on bicycles, put chains on them, pump air into the tires, and ride the bicycles.

| 条件 | 独立重答（英文原文） | 引用ID | 新答复核 A/B | 原答复核 A/B |
|---|---|---|---|---|
| E1 Full | People are repairing and adjusting bicycles, handling wheels, watching demonstrations, and riding bikes. | gab66db18f160, g8b5d69c8ce72, g1b1cf4351299, g733b6afd415c | ×/× | ×/× |
| E1 Key-1 | People repair and adjust bicycles, handle wheels, watch others fixing bikes, and ride bicycles. | g823d45bf9d3e, g1b1cf4351299, g733b6afd415c | ×/× | ×/× |
| E1 Key-2 | People are repairing and maintaining bicycles, handling wheels and tires, helping children with bikes, and riding bicycles. | g823d45bf9d3e, g8b5d69c8ce72, g733b6afd415c | ×/× | ×/× |
| E1 Key-3 | Adults repair and adjust bicycles while children watch, help, and handle a detached bicycle wheel. | g823d45bf9d3e, g8b5d69c8ce72, g1b1cf4351299 | ×/× | ×/× |
| E1 Irrel-1 | Adults and children handle bicycle wheels, repair and adjust bikes, and ride bicycles. | g823d45bf9d3e, g8b5d69c8ce72, g733b6afd415c | ×/× | ×/× |
| E1 Irrel-2 | People are repairing bicycles, working on wheels and other parts, helping children with bikes, and riding bicycles. | g823d45bf9d3e, g8b5d69c8ce72, g1b1cf4351299, g733b6afd415c | ×/× | ×/× |
| E1 Blind | The available evidence is insufficient to determine what activities people are engaged in with bicycles. |  | ×/× | ×/× |
| E2 R0 | People are repairing and adjusting bicycles, working on wheels and chains, while children watch and handle a bicycle wheel. | c000004, c000009, c000012, c000041, c000076 | ×/× | ×/× |
| E2 R1 | People are repairing and adjusting bicycles, working on wheels and drivetrain parts, while children handle bikes and a detached wheel. | c000004, c000005, c000010, c000076 | ×/× | ×/× |
| E2 R2 | People repair and adjust bicycles and their wheels, while children watch, help handle bicycle parts, and ride bikes. | c000004, c000012, c000041, c000076, c000085 | ×/× | ×/× |
| E2 R* | People are inspecting and repairing bicycles, adjusting wheels and other parts, while children watch and help handle the bikes. | c000004, c000005, c000041, c000043, c000076 | ×/× | ×/× |

## PtbGXfb6B1I_q01

选择层：`E1_Full_incorrect`。

问题：What steps are involved in preparing the fire pit before lighting the stick?

参考：First, dig the soil, then insert the stick into the big hole, and finally adjust it using the small hole.

| 条件 | 独立重答（英文原文） | 引用ID | 新答复核 A/B | 原答复核 A/B |
|---|---|---|---|---|
| E1 Full | Dig a main pit and a nearby air hole, connect them with a tunnel, line the pit’s edge with stones, and arrange sticks inside. | g709fb595b5c0, g342acd58812b, g04fb4cba3227, g39bff14b5ca8 | ×/× | ×/× |
| E1 Key-1 | Dig the main pit and a smaller connected air hole, clear loose soil, line the edge with stones, and arrange small sticks inside. | g3164a72903d2, g342acd58812b, g04fb4cba3227 | ×/× | ×/× |
| E1 Key-2 | Dig the main pit and a smaller adjoining air hole, connect them underground, line the pit’s edge with stones, and place dry sticks inside. | g3164a72903d2, g709fb595b5c0, g04fb4cba3227, g947912a0b850 | ×/× | ×/× |
| E1 Key-3 | Dig the main pit and a nearby air hole, connect them underground, then arrange stones and dry twigs in the fire pit. | g3164a72903d2, g709fb595b5c0, g342acd58812b, g947912a0b850 | ×/× | ×/× |
| E1 Irrel-1 | Dig the main pit and a smaller air hole, connect them underground, clear loose soil, arrange stones along the rim, and place sticks inside. | g3164a72903d2, g709fb595b5c0, g342acd58812b, g04fb4cba3227 | ×/× | ×/× |
| E1 Irrel-2 | Dig a main pit and a smaller adjoining air hole, connect them underground, then arrange stones around the pit and place sticks inside. | g3164a72903d2, g709fb595b5c0, g342acd58812b, g04fb4cba3227 | ×/× | ×/× |
| E1 Blind | The available evidence is insufficient to determine the steps involved in preparing the fire pit before lighting the stick. |  | ×/× | ×/× |
| E2 R0 | The available evidence is insufficient to identify the preparation steps; all supplied frames show an already burning fire pit. | c000121, c000130, c000132, c000134, c000136, c000138 | ×/× | ×/× |
| E2 R1 | The available evidence is insufficient to identify the preparation steps; all supplied frames show an already burning fire pit. | c000121, c000130, c000132, c000134, c000136, c000138 | ×/× | ×/× |
| E2 R2 | The available evidence is insufficient to determine the preparation steps; the frames show the fire pit already burning. | c000124, c000130 | ×/× | ×/× |
| E2 R* | Dig a pit in the ground, place stones along its edge, and arrange small sticks and twigs inside as kindling. | c000023, c000089, c000130 | ×/× | ×/× |
