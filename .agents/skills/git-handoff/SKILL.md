---
name: git-handoff
description: Prepare a Git branch, continue local work, or take over and hand off committed work between peer devices. Use for branch preparation and explicit handoffs; ordinary read-only reviews do not require synchronization.
---

# Git Handoff

Use the repository's branch and remote conventions from [AGENTS.md](../../../AGENTS.md). Commands below use the defaults `origin`, `main`, and `work/<short-name>`; adapt them if the repository specifies others.

## Inspect and choose the workflow

1. Read the repository guide, `docs/STATUS.md` when present, the current note through [session-notes](../session-notes/SKILL.md), and relevant task files.
2. Check whether the directory is a Git worktree. If it is, inspect `git status --short --branch`, the working diff, and the staged diff before making changes.
3. Choose the applicable case:
   - **No Git metadata, or no first commit:** Continue authorized local work. Repository initialization and the first commit belong to a setup task; do not infer them from an ordinary edit or handoff request.
   - **Missing remote, base ref, or network access:** Continue work on a known local task when safe. Defer synchronization or takeover that needs the missing state; report exactly what is unavailable. Do not invent a remote URL or configure one without existing setup authorization.
   - **Read-only review:** Inspect the relevant state and files; no fetch, branch switch, or clean worktree is required.
   - **Same-device continuation:** Stay on the appropriate task branch and preserve its changes. Do not repeat takeover or fetch on every turn.
   - **New task, branch change, or cross-device takeover:** Use the preparation steps below.

Modified, staged, or untracked files do not by themselves block local work. Continue changes known to belong to the current task and leave unrelated work intact. If an edit overlaps changes whose ownership is unclear, pause that edit and continue independent work. Do not automatically stash, commit, discard, or overwrite pre-existing changes to make the worktree clean.

## Prepare or take over a branch

- Before switching or fast-forwarding a branch, require a clean worktree for that operation, or use a separate worktree when an existing, verified source ref makes that appropriate. A separate worktree does not transfer uncommitted work or establish ownership of an active task.
- Fetch `origin` before selecting a remote starting point or accepting a cross-device handoff. If fetch fails, do not describe cached remote refs as current.
- For takeover, require an explicit handoff and its branch and commit reference. Confirm the fetched branch contains that commit and review any later commits; resolve unclear ownership before continuing that task.
- For a new task, use the latest fetched `origin/main`: start a task branch with `git switch --no-track -c work/<short-name> origin/main`, or use the documentation-only `main` exception in the repository guide.
- For an existing target branch, compare that branch with its remote counterpart. When it exists locally, switch to it under the worktree-readiness rule before applying any update below:

| Target state | Action |
| --- | --- |
| Local and remote branches exist and are equal | Keep the branch. |
| Local branch is only behind its remote | Update with `git merge --ff-only origin/<branch>` once the worktree is ready. |
| Local branch is only ahead of its remote | Preserve the local commits and inspect them. Continue if they belong to this local task; for takeover, account for them against the handoff before proceeding. |
| Local and remote histories have diverged | Pause synchronization and report commits on both sides. Continue independent work. |
| Only the remote branch exists | Create a tracking branch with `git switch --track -c <branch> origin/<branch>`. |
| Only the local task branch exists | Continue a known, not-yet-pushed local task; no remote update is needed. Its first publication uses `git push -u origin <branch>`. Do not treat this state as a verified remote handoff. |
| Neither task branch exists | Create it only for a new task from the verified base. A missing handoff branch requires resolving the source. |

If `main` is ahead of its remote or has diverged, it does not qualify as an up-to-date base for the documentation-only exception. Preserve its commits and resolve the intended starting state. A failed fast-forward is not permission to create a merge commit, rebase, reset, or force-push.

## Hand off

An explicit handoff request authorizes the task's focused commit and push. Ordinary completion does not require publication.

1. Inspect working and staged changes. Select only task files or hunks; preserve unrelated changes and do not include unrelated staged content in the commit.
2. Run the checks appropriate to this change and available on this device. Report unavailable required checks as `not run` with the reason.
3. Update project status and the current session note only when durable context has changed. Link authoritative files and identify the next action.
4. Fetch `origin` and inspect the target branch relation before publishing:
   - On `main`, require a small, low-risk documentation-only change and local `HEAD` equal to `origin/main` before creating the handoff commit.
   - On a task branch, allow an equal or locally ahead history, or a known local task's first push. If the remote has advanced or diverged, defer publication and preserve local work until the branch can be reconciled under the preparation rules.
   - On an ineligible branch or with unavailable remote state, defer publication and report the limitation.
5. Review the exact staged patch, make a focused commit, and push the current branch; use `git push -u origin <branch>` for its first push. If the remote advances during publication and rejects the push, fetch and reassess; never force-push.
6. Verify that the push succeeded and no task changes remain uncommitted. Report the branch, commit SHA, checks, excluded local work if any, and next action. If commit or push failed, report the partial state and do not claim the handoff is complete.

Record the resulting SHA in the handoff message. A repository status file may point to the task branch and accompanying handoff message; it need not contain the hash of the commit that writes it.
