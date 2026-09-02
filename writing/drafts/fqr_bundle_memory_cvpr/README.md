# FQR Bundle Memory CVPR draft

## Overleaf 使用

将本目录中的以下文件一并上传到 Overleaf：

- `main.tex`：论文主文件
- `references.bib`：参考文献
- `cvpr.sty`：官方 CVPR 样式
- `ieeenat_fullname.bst`：官方参考文献样式

在 Overleaf 中把主文件设为 `main.tex`，编译器使用 `pdfLaTeX`。

样式文件来自官方 `cvpr-org/author-kit` 的 `CVPR2026-v1(latex)` 标签（commit `12909ae437f6dbc7435069cfdb4ca44c18e6a02f`）。`cvpr.sty` 未修改；`ieeenat_fullname.bst` 仅清理了一个行尾空格，样式逻辑未变。当前尚无更新的正式 CVPR 年度模板；新模板发布后应替换 `cvpr.sty`、`ieeenat_fullname.bst`，并更新 `main.tex` 中的会议年份。

## 当前状态

这是实验前完整初稿。结果、分析结论和最终 Figure 1 尚未生成；正文中的橙色 `Result pending` 框和表格中的 `--` 是有意保留的占位，不代表数值为零。
