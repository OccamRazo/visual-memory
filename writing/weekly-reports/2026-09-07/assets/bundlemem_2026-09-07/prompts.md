# BundleMem PPT 配图记录

生成日期：2026-09-07。

三图均使用内置 `image_gen` 生成，人工文字提示驱动；本会话由 AI 逐图核验节点、文字及方法边界。不是实验数据图或真实视频帧。对应来源为 `docs/plan/cvpr2027_bundlemem_closed_loop_design.md` 和 `docs/plan/egvqa_15h_single_gpu_validation_plan.md`，资料版本为 `fcd7ecf`。

## 05_bundle_concept.png

用途：第 5 页，固定四项预算的 AND / OR 概念例。x 为无关项，非实测数据。

```text
Create a clean academic presentation diagram in Chinese, wide landscape 16:9, high resolution, pure white background, dark navy typography and restrained blue and orange, flat precise educational style. No decoration, logos, photos or invented numerical results. All text large and crisp.
Title: "完整证据组：组内 AND，组间 OR"
Top half, two parallel horizontal evidence paths. First blue path labelled "路径 A" has three nodes with exact text "a" then "b" then "c", joined by solid blue lines. Above it label "三条共同支持答案". Second orange path labelled "路径 B" has two nodes "d" and "e", joined by solid orange line. Above it label "另一条充分路径". Both paths independently connect at the right to a single label "回答 q". Put "OR" between paths, and "AND" underneath each path.
Bottom half: two well-separated flat comparisons, no UI card grid. Left heading "零散保留", show ONLY four retained nodes a, b, d, x (a,b blue, d orange, x neutral gray). Caption exactly "两条路径都不完整". Right heading "完整保留", show ONLY four retained nodes a, b, c, x (a,b,c blue, x neutral gray), and connect a b c by one continuous blue line. Caption exactly "保住一条完整路径".
Bottom footnote "概念示例，非实验结果". Same storage budget four equal-sized evidence units in both bottom comparisons. x is irrelevant, c missing from left, e missing from left. Do not accidentally draw or include missing c/e in left retained set. Do not display any accuracy, recall percentage or invented result. Wide whitespace, no overlapping arrows or labels.
```

## 07_framework.png

用途：第 7 页，拟实施的闭环读写方案。问题仅进入 reader，训练标签仅用于离线参数学习。当前 E1/E2 未实现该完整学习系统。

```text
Create a polished academic schematic diagram for a Chinese research presentation, wide 16:9 landscape on white, dark navy large typography, blue and muted orange connectors, flat and minimal, no decorative illustrations. Exact title "BundleMem 总体方案". It is a proposed method, not an implemented performance result.
Main horizontal sequence at middle: "视频流" -> "来源胶囊" -> "集合写入器" -> "预算内记忆" -> "组合读取器" -> "充分性检查" -> "回答与引用". Use clean spacious boxes and simple directed arrows, each short label fully legible. If necessary break after budget memory into second row to keep type large; prioritize a clean two-row layout with generous space.
Place a label above the writer side "写入时未知问题". A separate node "问题 q" enters ONLY "组合读取器" and has NO connection to writer or capsule. Below "充分性检查", draw a loop returning to "组合读取器" with exact label "缺证且仍可补取". Also branch from sufficiency to a small terminal "证据不足" labelled "预算耗尽". The "回答与引用" branch is labelled "证据足够".
At the very bottom, separated by a dashed horizontal line, draw an offline training strip: "训练期问题与干预" -> "读写价值学习". From "读写价值学习" dashed arrows point to BOTH "集合写入器" and "组合读取器". Label this strip "仅离线训练". Keep these training arrows separate from normal dataflow and avoid overlaps.
Small footer "方案设计，尚未完成端到端验证".
Do not add original-video replay or any arrow from a question to the writer. There must be no test-answer feedback learning loop. Do not depict robots, benchmarks, or numerical results.
```

## 12_intervention.png

用途：第 12 页，最终以三组标注时间证据、两组干扰展示 E1 的规模匹配干预。字母不是实际事件或语义金标。

```text
Create a precise academic schematic for a Chinese research slide on white background, wide 16:9, clean dark navy typography, restrained blue, gray and orange, flat scientific educational style, large legible text, no decoration. Title "E1 联合证据干预".
Four horizontal rows with generous spacing. Each of the first three rows contains EXACTLY six equally sized square image-group symbols, with letters clearly printed in centers.
Row 1 label "Full", then six symbols labelled a, b, c, u, v, w in exactly that order. a b c blue, u v w gray. Right row note "标注组与干扰组".
Row 2 label "Key", then a, d, c, u, v, w. a c blue, d u v w gray. Outline ONLY d in orange. Right row note "替换一个标注组".
Row 3 label "Irrel", then a, b, c, u, z, w. a b c blue, u z w gray. Outline ONLY z in orange. Right row note "替换一个无关组".
Row 4 label "Blind", then NO image symbols, just text "不给历史图片".
Below rows legend: blue small symbol "标注时间组" and gray small symbol "干扰组".
Footer two short lines: "每组四帧，有图条件规模相同" and "构造示意，联合必要性仍需核验".
Do not show photographs, predictions, checkmarks, success/failure, or performance numbers. This figure illustrates a three-annotated-group example only; it does not prove a b c are semantically necessary. Ensure all replacement symbols are different from all remaining symbols within their row. No arrows connecting rows.
```


### 最终协议校正

最终采用三组标注时间证据、两组干扰的五组示例，Key 与 Irrel 复用同一替换组 d。上一节为初次生成提示，以下编辑指令产生交付图片；初版图片不交付。

```text
Edit the attached E1 diagram to match the actual intervention protocol. Keep the exact visual style, white background, title, row labels, right-side row notes, legend and footers.
Change the first three rows to EXACTLY FIVE equally sized, well-spaced group symbols each. Remove the final w square from every row and rebalance the spacing across the diagram.
Exact final rows:
Full: a, b, c, u, v.
Key: a, d, c, u, v.
Irrel: a, b, c, u, d.
The same replacement group d must appear in BOTH Key and Irrel. There must be NO z or w anywhere.
a/b/c have blue outlines, u/v gray outlines. Outline the replacement d orange in BOTH rows. Keep each row aligned and the same five-column width.
Add a small centered note just above the two footer lines: "Key 与 Irrel 使用同一替换组 d".
No other changes. Do not add any sixth box, extra letters, results or predictions. The complete package has three annotated groups and TWO distractor groups.
```
