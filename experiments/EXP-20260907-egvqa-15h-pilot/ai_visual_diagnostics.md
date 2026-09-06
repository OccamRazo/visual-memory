# E1 两道 Full 错误题的补充 AI 视觉诊断

reviewer_type: `AI`；reviewer: `Codex agent`；kind: `secondary_visual_diagnostic`；explicitly_not_human: `true`。

这是事后、已见题目/参考/预测的 AI 材料核查，不是人工审核或盲审，不构成人工校准、联合依赖确认或正式重判。仅查看两题实际 Full 输入的 40 帧，不查看额外视频帧，不请求额外 VLM API，不改冻结源码、模型输出、分数或任何人工审核状态。以下把载荷中可见的内容与尚待核验的解释分开记录。

## 选择规则与材料校验

使用现有 `src/egvqa_pilot/analysis.py::aggregate_e1`，输入本 run 的 `eval_manifest.json['questions']` 与 `e1_pairs.jsonl`，得到 `valid_pair=True` 的 44 题；其中 `scores['Full']==0` 共 33 题。对这 33 个 question ID 调用现有 `fixed_hash_order(ids, seed=43)`，即按 `(sha256('43:' + question_id), question_id)` 升序取前两题。两题原始 Full verdict 均为 `incorrect`，执行与解析均完成。聚合得到的自动联合候选为 0；本次失败诊断不会产生新的联合候选或人工确认。

| 次序 | Question ID | 选择 SHA-256 |
|---|---|---|
| 1 | `PtbGXfb6B1I_q01` | `042bcf1b0d9e8e1359fdcc0811c228574029f5ade9044f9d4ab27aacbcad4c80` |
| 2 | `DBgap0YANhs_q02` | `12ea6430f871a9234153da8a41c010f5cb866fad4e6e0812a5bd89ec5dcfd20f` |

按各题 manifest 的 `conditions.Full.group_ids` 顺序，从 `pixels.npz['images'][group.image_index]` 提取全部帧。两题各 5 组 × 4 帧，均为有效的 224×224 RGB uint8 图像。40/40 帧的像素 SHA-256 同时匹配 manifest 的 `frame_hashes` 和 `calls.jsonl` 对应真实 Full 请求的 `source_sha256`、`rgb_sha256`；group ID、PTS、帧顺序及数量也一致。两个源 manifest 和 NPZ 的文件 SHA 在导出前后不变。

拼图逐像素粘贴原尺寸帧，仅在帧外增加 ID/PTS 标签和留白；未缩放、裁剪、增强或覆盖原始图像。标签时间显示到六位小数，下表显示到三位；完整浮点 PTS 与逐帧哈希保存在[校验记录](run-20260907T0206+0800/ai_visual_diagnostics_assets/selection_and_payload_checks.json)。[本地导出脚本](run-20260907T0206+0800/ai_visual_diagnostics_assets/build_contact_sheets.py)只生成展示材料，复现命令从仓库根目录运行：

```bash
.venv/bin/python experiments/EXP-20260907-egvqa-15h-pilot/run-20260907T0206+0800/ai_visual_diagnostics_assets/build_contact_sheets.py
```

## 1. PtbGXfb6B1I_q01：点火前的火坑准备顺序

视频 ID：`PtbGXfb6B1I`。真实请求 ID：`E1:PtbGXfb6B1I_q01:E1:Full:answer:1`。

问题：What steps are involved in preparing the fire pit before lighting the stick?

参考：First, dig the soil, then insert the stick into the big hole, and finally adjust it using the small hole.

Full 预测：Digging a hole, arranging stones around it, and placing kindling inside before lighting.

材料：[Full 原尺寸拼图](run-20260907T0206+0800/ai_visual_diagnostics_assets/PtbGXfb6B1I_q01_Full.png)、[载荷 manifest](run-20260907T0206+0800/prepared/PtbGXfb6B1I/e1/PtbGXfb6B1I_q01/manifest.json)、[原始 NPZ](run-20260907T0206+0800/prepared/PtbGXfb6B1I/e1/PtbGXfb6B1I_q01/pixels.npz)。

| Full 组顺序 / ID | 实际 PTS（秒） | 标注对应与载荷观察 |
|---|---|---|
| 1 / `g709fb595b5c0` | 46.000, 84.333, 122.633, 160.967 | 标注为挖土 `[46,161]`；前三帧能看到人在土面使用工具，末帧为暗处洞内视角。 |
| 2 / `g342acd58812b` | 161.000, 164.667, 168.300, 171.967 | 标注为将木棍放入大孔 `[161,172]`；可见洞内、模糊过亮画面和地面孔洞，未明确看到完整插入动作。 |
| 3 / `g04fb4cba3227` | 172.000, 176.667, 181.300, 185.967 | 标注为经小孔调整木棍 `[172,186]`；首帧是孔洞，后三帧已有明显火焰、木枝和石块边缘，未明确看到小孔调整动作。 |
| 4 / `g947912a0b850` | 201.400, 206.067, 210.733, 215.400 | Full 内的非标注时间组；包含过亮画面、燃烧火坑和人物近景。 |
| 5 / `g39bff14b5ca8` | 253.700, 258.367, 263.033, 267.700 | Full 内的非标注时间组；可见燃烧木枝、石块边缘及附近孔洞。 |

**问题所需事实。** 按题目与参考，需要分别识别挖土、向较大的孔插入同一木棍、通过较小的孔调整木棍，并把三步排列在点火之前；看到两个孔或燃烧后的木枝本身不足以确认这些具体动作及其顺序。

**视觉可辨识性。** 当前帧对“挖土”和“后续火坑里有木枝、石块、火焰”的支持较强。对于“哪个是大孔/小孔、木棍从哪里插入、通过哪个孔调整”，本次 AI 无法在给定 224×224 稀疏帧中可靠确认。尤其第 2 组有模糊/过亮帧，而第 3 组的多数采样帧已是点燃状态。时间戳落在标注区间内这一机械事实，不能直接证明所需动作已经可辨识。

**参考与预测差异。** 预测保留挖洞，却以“围石头、放引火物”替代“大孔插棍、小孔调整”。石块和木枝在图中确实存在，因此不能把这些物体的出现本身称为无视觉根据；但本次看到的帧没有明确展示“排列石块”的动作，更没有证明它与插棍/调整具有相同含义。原始本地 judge 记为 `incorrect`（理由：`Omits key steps and adds kindling`），本报告不改分。

**未解决的解释。** 当前材料容许抽帧遗漏动作、分辨率/遮挡限制、时间标注与动作未精确对齐，或消费者将后续可见场景概括成常见生火步骤等解释，无法独立区分。第 3 标注组已经出现火焰，使“点火前调整”的具体时间对应值得人工复查，但尚不能据此断言参考错误。两个非标注时间组仍呈现同一火坑与木枝，故“时间上无重叠”也不证明没有语义上的替代线索；本次未核验任何替换条件，不能对干预的语义有效性作确认。

## 2. DBgap0YANhs_q02：烹调前蔬菜混合物的准备顺序

视频 ID：`DBgap0YANhs`。真实请求 ID：`E1:DBgap0YANhs_q02:E1:Full:answer:1`。

问题：What sequence of steps is involved in preparing the vegetable mixture before cooking?

参考：Add vegetables, yogurt, cream, cheese; then add mint, coriander, turmeric, chili powder, masala, salt, tomatoes; mix potatoes and onions.

Full 预测：Add yogurt, mix ingredients, add peanut butter, and then prepare the cooking vessel.

材料：[Full 原尺寸拼图](run-20260907T0206+0800/ai_visual_diagnostics_assets/DBgap0YANhs_q02_Full.png)、[载荷 manifest](run-20260907T0206+0800/prepared/DBgap0YANhs/e1/DBgap0YANhs_q02/manifest.json)、[原始 NPZ](run-20260907T0206+0800/prepared/DBgap0YANhs/e1/DBgap0YANhs_q02/pixels.npz)。

| Full 组顺序 / ID | 实际 PTS（秒） | 标注对应与载荷观察 |
|---|---|---|
| 1 / `ged32d3072ab4` | 133.000, 143.640, 154.320, 164.960 | 标注为加蔬菜、酸奶、奶油、奶酪 `[133,165]`；多为人物操作台全景，154.320 秒近景可见白色稠状物倒入装有切块食材的玻璃碗。 |
| 2 / `g1c0013ae6ec7` | 165.000, 183.640, 202.320, 220.960 | 标注为加草本、调味料、番茄 `[165,221]`；前三帧多为操作台全景，220.960 秒近景可见搅拌碗内带白色酱状物、红色及浅色块状食材的混合物。 |
| 3 / `ge4d62ed67cd3` | 224.000, 229.320, 234.640, 239.960 | 标注为混入土豆与洋葱 `[224,240]`；224.000 秒有盛放浅色块和紫红色环状食材的盘子，随后可见玻璃碗内混合物，但细节不足以独立确认全部成分。 |
| 4 / `g5200f0648c0f` | 240.000, 250.680, 261.320, 272.000 | Full 内的非标注时间组；人物继续操作/讲解，261.320 秒出现原视频自带 `TIP` 文字框，内容涉及炊具下加锅以分散热量的烹饪建议。 |
| 5 / `g5b38488ee57b` | 275.840, 286.520, 297.160, 307.840 | Full 内的非标注时间组；后两帧为勺子接近锅及锅内浅色物质的近景，能支持“开始处理炊具/锅中材料”的宽泛观察。 |

**问题所需事实。** 按参考，需要辨认先加入的蔬菜及三类乳制品，随后加入的草本、具体粉状调味料和番茄，再混入土豆与洋葱。要完整核实该长食材列表，需要比“倒入白色物质、加料、搅拌”更细的成分识别；仅凭颜色相近的液体或粉末通常无法在这些帧中可靠区分。

**视觉可辨识性。** 加入稠状物、碗中已有切块食材、后续搅拌等大动作可辨认；酸奶/奶油/奶酪之间、薄荷/香菜之间以及多类香料之间，本次 AI 不能仅凭给定帧逐一确认。前两组的多帧为人物与整张操作台的全景，容器和食材占用像素有限；每个长标注区间只抽四帧，也不能保证每个短暂加料动作都被展示。当前帧没有让我可靠识别出花生酱。

**参考与预测差异。** 预测只保留酸奶与泛化的混合动作，遗漏大部分食材及参考要求的阶段顺序，新增“花生酱”，最后转向处理炊具。处理炊具与后续非标注时间组的画面存在表面对应，但不等于回答了本题要求的蔬菜混合物准备过程。预测引用了 `ged32d3072ab4`、`ge4d62ed67cd3`、`g5b38488ee57b`，未引用第 2 标注组；引用选择本身不足以证明模型完全未使用该组。原始本地 judge 记为 `incorrect`（理由：`Adds peanut butter not in reference`），本报告不改分。

**未解决的解释。** “花生酱”可能来自对某个浅色块/糊状物的误识别或常识补全，但没有足够证据定位其来源；不能直接指定是哪一帧导致。第 4 组可见原视频自带的烹饪文字，因此本题材料存在画面文字线索，不能确认“无文字线索”，也不能仅凭该提示断言存在金标答案泄漏。消费者识别困难、有限帧表示、无关后续片段吸引注意以及参考食材列表对视觉输入的要求过细，都仍是待验证解释，不能只由这两题归因到记忆或检索机制。

## 证据边界与留待人工核验的内容

本次仅选取 Full 已判错的两题，带有明确的失败条件选择，不能估计总体视觉可答率或任何错误原因的占比。没有观察原视频连续动作、音频、更多分辨率或所有替换条件；未独立验证完整参考正确性、独立必要事实、替代线索和答案是否真正受引用帧支持。因此两题的视觉充分性均保持“AI 未能完整确认、待人工核验”，不得写入正式 `audit.jsonl` 作为人工通过记录。

最具体的人工核验点是：火坑题的“大孔插入/小孔调整”是否真实发生在标注区间、是否被现有帧保留；蔬菜题的每项指定食材是否能由现有视觉载荷独立确定，以及可见文字和后续炊具画面对回答边界的影响。当前补充观察只为这项核验提供定位，不改变冻结实验结论。
