---
name: git-handoff
description: Take over or hand off a work/task-name Git branch between peer development devices. Use when starting or resuming a task from origin, or when preparing committed work for another device; do not use it to merge, delete branches, create remotes, or synchronize artifacts.
---

# Git Handoff

## 接手

1. 阅读仓库根目录的 `AGENTS.md`、当前 session note，以及与任务相关的实验 `README.md` 或说明文件。
2. 运行 `git status --short --branch` 检查当前工作区。若存在修改、暂存内容或未跟踪文件，立即停止并说明；不要 stash、提交、覆盖或删除这些内容。
3. 运行 `git fetch origin` 获取远端状态。
4. 更新或创建目标分支：
   - 已有本地 `work/<short-name>` 时，切换到该分支，并用 `git merge --ff-only origin/work/<short-name>` 更新。
   - 仅远端存在任务分支时，用 `git switch --track -c work/<short-name> origin/work/<short-name>` 创建本地跟踪分支。
   - 远端也不存在任务分支时，从最新 `origin/main` 用 `git switch --no-track -c work/<short-name> origin/main` 创建新任务分支。
   - fast-forward-only 更新失败或本地与远端分叉时，停止并报告两侧提交差异；不得自动 rebase、merge、reset、覆盖或 force-push。
5. 查看最新提交和相对 `origin/main` 的差异，结合交接信息确认一个明确的下一步后再开始修改。

## 交接

1. 检查 `git status`、工作区差异和暂存区差异，只选择当前任务范围内的文件；不得把无关改动纳入交接。
2. 运行当前设备具备条件执行的检查，并准确记录命令与结果。无法执行的检查写为 `未运行：<检查> — <原因>`，不得把未运行项目表述为已验证。
3. 按 `AGENTS.md` 的规则判断是否需要向当前 session note 追加长期有价值的信息，不记录操作流水。
4. 确认当前分支为 `work/<short-name>`，选择性暂存任务文件，复查暂存差异，创建内容完整且可理解的 commit；然后用 `git push -u origin work/<short-name>` 推送。不得自动 merge、删除分支或 force-push。
5. 返回分支名、`git rev-parse HEAD` 得到的 commit SHA、已运行和未运行的验证、唯一下一步，以及后续确有需要时的本地输出位置。大型数据、日志、checkpoint 和输出产物不得进入 Git。
