# 周报论文图来源

用于 2026-09-09 潜记忆周报的学术说明，图像直接取自原论文 HTML，未改变实验数字或图意。版权归原作者／出版方。这里只保存周报所用四张小图，不收录论文全文。

| 文件 | 原图／页内位置 | 原始地址 | 获取日期 |
|---|---|---|---|
| lclm_agent.png | LCLM Fig.6；周报第 03 页 | https://arxiv.org/html/2606.09659v1/agent.png | 2026-09-09 |
| mem_w_framework.png | Mem-W Fig.1；周报第 05 页 | https://arxiv.org/html/2605.09317v1/framework_final.png | 2026-09-09 |
| metis_framework.png | Metis Fig.2；周报第 07 页 | https://arxiv.org/html/2607.26760v2/figure_framework.png | 2026-09-09 |
| adapter_memory_routing.png | Context Distillation Fig.5；周报第 11 页 | https://arxiv.org/html/2605.28889v1/rag.png | 2026-09-09 |

Markdown 为可编辑内容稿；HTML 为与上期风格一致的阅读／打印版，依相对路径读取上述图片。无需外网字体。交付 HTML 的公式已由 MathJax 转成内嵌 SVG，离线可读。

重建：安装 Node.js、marked、playwright 后，在上一级运行 `node build_weekly.mjs`。可以用 `CHROME_PATH` 指定 Chrome 路径；首次渲染公式需要访问 MathJax CDN。`SKIP_RENDER=1` 只生成保留 LaTeX 的动态渲染 HTML。Markdown 是内容源，修改后应重建并复查页面。
