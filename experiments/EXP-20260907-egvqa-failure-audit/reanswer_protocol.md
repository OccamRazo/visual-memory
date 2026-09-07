# 单匿名包独立 AI 作答指令

这是视觉问答子任务，不是仓库开发、Git 接管或历史检索。每个新上下文仅处理初始任务指定的一个 packet_id。

允许读取本文件，以及以下固定 run 内 `blind_packets/<packet_id>/input.json` 和该 JSON 的 `image_pages` 所列图片：

`/root/autodl-tmp/projects/visual-memory/experiments/EXP-20260907-egvqa-failure-audit/run-20260907T0909+0800`

不得查看其他包、参考答案、原模型预测、条件名称/映射、研究报告、其他回答文件或网络。不要启动额外子代理。不进行 Git 操作。

1. 读取指定 input.json。其 prompt 是作答要求，visible_frames 给出每张图的原始 ID 和精确 PTS。
2. 有 image_pages 时必须用 view_image(detail='original') 查看全部页面。图片是原尺寸帧的展示拼图，四帧一行，行外标签不属于原视频画面。没有图片时按 prompt 作答，不另找视频。
3. 仅根据当前问题、帧图和时间信息独立作答。英文 answer 最多30词，citations 只能使用 allowed_citation_ids 中的ID；不臆造未展示的细节。无需给推理过程。
4. 将结果写到上述 run 的 `responses/<packet_id>.json`，不要覆盖任何其他文件。JSON 字段：packet_id、answer、citations、reviewer_type（AI）、reference_seen（false）、other_packets_seen（false）、viewed_image_paths（实际看过的列表）。若实际意外见到参考或其他包，须如实改标并报告，不能声称未见。
5. 最终仅报告保存完成，不在其他位置输出或修改分数。

这些字段记录作答者的执行声明，不表示操作系统强制访问隔离。此轮是不同模型与展示方式的补充诊断，不是原Qwen的等预算性能复现，也不是人工校准。
