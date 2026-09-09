# 潜记忆技术分类周报（重写版）

内容源为 `latent_memory_technical_12slides_2026-09-10.md`，阅读／打印版为同名 HTML。封面与结束页各 1 页，正文 10 页；五条技术路线各“总体设计＋代表设计”两页。

本版按记忆的计算形态分类，任务仅作为应用标签。代表设计为 Mem-W、HERMES、δ-mem、Engram、Context Distillation。完整 40 篇映射与设计详解见 [技术报告](../../../research/literature/latent_memory_technical_taxonomy_2026-09-10.md)。2026-09-09 版本保留为历史记录。

重建需 Node.js、marked、playwright：运行 `node build_weekly.mjs`；可用 `CHROME_PATH` 指定本机 Chrome。首次渲染公式需访问 MathJax CDN，生成后的 HTML 已内嵌公式 SVG，可离线阅读。`SKIP_RENDER=1` 只生成保留 LaTeX 的动态 HTML。

本版用可编辑步骤说明和 LaTeX 公式展开设计，不复制整页论文截图。论文来源位于每页“备注与来源”。打印样式每页固定 1120×700 CSS 像素；浏览器打印可另存 PDF。
