---
name: git-handoff
description: Take over or hand off Git work between peer development devices. Use for work/task-name branches, or for a small, low-risk documentation-only change made directly on an up-to-date main; do not use it to merge, delete branches, create remotes, or synchronize artifacts.
---

# Git Handoff

## Takeover

1. Read the repository-root `AGENTS.md`, then follow `.agents/skills/session-notes/SKILL.md` to resolve and read the current session note when it exists. Read any experiment `README.md` or other documentation relevant to the task.
2. Run `git status --short --branch` to inspect the worktree. If it contains modified, staged, or untracked files, stop immediately and explain; do not stash, commit, overwrite, or delete them.
3. Run `git fetch origin` to retrieve the current remote state.
4. Update or create the target branch:
   - For a small, low-risk documentation-only change that qualifies for the `main` exception in `AGENTS.md`, run `git switch main` and `git merge --ff-only origin/main`.
   - If a local `work/<short-name>` branch exists, switch to it and update it with `git merge --ff-only origin/work/<short-name>`.
   - If the task branch exists only on the remote, create a local tracking branch with `git switch --track -c work/<short-name> origin/work/<short-name>`.
   - If the task branch does not exist locally or remotely, create it from the latest `origin/main` with `git switch --no-track -c work/<short-name> origin/main`.
   - If the fast-forward-only update fails or the local and remote branches have diverged, stop and report the commits on both sides. Do not automatically rebase, merge, reset, overwrite, or force-push.
5. Review the latest commits and the difference from `origin/main`. Use the handoff information to identify one clear next step before making changes.

## Handoff

1. Inspect `git status`, the worktree diff, and the staged diff. Select only files within the current task scope; do not include unrelated changes in the handoff.
2. Run every relevant check that the current device supports, and record each command and result accurately. Mark unavailable checks as not run and include the reason; never present an unexecuted check as verified.
3. Follow `.agents/skills/session-notes/SKILL.md` to decide whether this session has a durable update and to write it to the correct note when needed.
4. Commit and push from an eligible branch:
   - On `main`, proceed only when every change is small, low-risk, and documentation-only. Run `git fetch origin` and require the local `HEAD` to equal `origin/main` before committing; if the remote has advanced, stop and report it. Selectively stage the documentation files, review the staged diff, create a complete, understandable commit, and run `git push origin main`.
   - On `work/<short-name>`, selectively stage the task files, review the staged diff, create a complete, understandable commit, and run `git push -u origin work/<short-name>`.
   - On any other branch, stop and report that the branch is ineligible for handoff. Do not automatically merge, delete branches, or force-push.
5. Return the branch name, the commit SHA from `git rev-parse HEAD`, checks run and not run, one clear next step, and a local output location only when later work genuinely needs it. Do not add large datasets, logs, checkpoints, or output artifacts to Git.
