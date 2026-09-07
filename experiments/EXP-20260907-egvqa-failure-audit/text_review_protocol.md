# 匿名文本复核指令

本任务不是仓库开发或 Git 接管。每个新上下文只复核初始任务指定的 A 或 B 文件，不查看另一个审核者、图片、条件映射、研究报告、历史分数或其他答案文件；不联网，不启动子代理，不操作 Git。数据已将同题同参考同预测去重，排序种子分别为 43/44。

只读本文件和初始任务指定的 `blind_text_review_A.json` 或 `blind_text_review_B.json`。沿用冻结实验的以下英文 rubric，逐条独立评价，不能按答案来源或期望实验方向改变标准：

> Evaluate each anonymous prediction against its question and reference answer. Use the same strict rule for every prediction: "correct" only if the conclusion is semantically correct, with no meaning-changing omission or contradiction; otherwise "incorrect". Use "uncertain" only when reference ambiguity prevents a reliable decision. A statement that evidence is insufficient does not answer a determinate reference question. Extra claims that contradict the reference make an answer incorrect. You cannot inspect the video. Return only a JSON object with a "results" array. For each supplied id, return keys "id", "verdict" ("correct", "incorrect", or "uncertain"), and "reason" (at most eight words).

写到初始任务指定的 `text_review_A.json` 或 `text_review_B.json`，必须包含每个输入 id 且仅一次。顶层添加 `reviewer_type: "AI"`，不得冒充人工审核。理由用至多八个英文词；不输出长推理。可以用 Python 写文件和检查 id/字数等格式，但语义判定必须由你逐项完成，不能写关键词规则代替评价。

最终只报告已保存。两名 AI 的分歧会原样保留，不以协商或多数票伪造金标。
