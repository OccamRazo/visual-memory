# Repository Guide

## Project goals

This project studies visual memory in large models: how a model selects, compresses, stores, retrieves, and updates information from a continuous visual stream. The current primary setting is ultra-long video understanding, with particular interest in its relationship to sparse attention, KV cache, external or parametric memory, and evaluation methods.

## Communication

- Communicate in Chinese by default, unless the user requests another language.
- Keep repository-management rules reusable. Put domain-specific structure and requirements in [Project conventions](docs/project-guide.md); do not embed them in management skills.

## Repository navigation

- [Project conventions](docs/project-guide.md): project-specific directories and working requirements. Read when relevant to the task.
- [Project status](docs/STATUS.md): the current task, status, authoritative references, and next action across sessions.
- [Work records](docs/work-records.md): small, versionable run records and local artifact locations.
- [Session notes skill](.agents/skills/session-notes/SKILL.md): resolve and maintain the current session's note.
- [Git handoff skill](.agents/skills/git-handoff/SKILL.md): inspect Git readiness, continue local work, and transfer work between devices.

Create directories and records only when they are needed.

## Starting and continuing work

- Read this file and `docs/STATUS.md` when it exists. Use the session-notes skill to resolve the current session note, then read the source material relevant to the task.
- Inspect existing changes before editing. Preserve work outside the task scope; continue known changes belonging to the current task.
- Missing Git metadata, remote access, or a stable session ID limits only the operations that require them. Continue authorized local work that does not depend on the missing prerequisite, and report the limitation when relevant.
- Pause an affected edit or Git operation when it would discard changes outside the intended task, when branch histories diverge, or when ownership of overlapping changes is unclear. Continue independent work.
- Update `docs/STATUS.md` only when the task, status, accepted decision, or next action materially changes. Keep it a short current snapshot with links to authoritative files, not a transcript or a copy of their contents. Include a branch and handoff reference when applicable; mark unknown values explicitly.
- A status entry is context, not authorization to resume work on another device or to publish changes.

## Git collaboration

- Repository defaults: remote `origin`, base branch `main`, task branches `work/<short-name>`. These are conventions, not proof that the corresponding Git objects exist.
- Use the Git handoff skill when preparing a branch, taking over work, or handing it off. Read-only reviews and same-device continuation do not require the full takeover sequence on every turn.
- Small, low-risk documentation-only tasks may start directly on a clean, up-to-date `main`. Use a task branch for code or other substantial work. Continue an existing task on its current appropriate branch.
- Devices are peers. Continue a task on one device at a time; a different device takes over only after explicit handoff through committed and pushed work.
- Preserve history. Fast-forward updates are allowed; do not automatically create merge commits, rebase, reset, force-push, or delete branches.
- Handoff transfers only the identified task's committed and pushed state. Do not use a stash or uncommitted files as the transfer mechanism.

## Work records and artifacts

- Follow [Work records](docs/work-records.md) when work produces results worth preserving. Keep small records and reproduction inputs outside ignored artifact directories.
- Keep large data, logs, checkpoints, and generated artifacts on the producing device. Commit only concise records and necessary location references.
- Store separate records for independent runs. Preserve failed results and original evidence; link corrections and replacements instead of silently overwriting them.
- Do not commit secrets, caches, or large generated files.

## Working constraints

- Read relevant material before making changes. Prefer the smallest verifiable change and avoid unrelated cleanup.
- Distinguish verified facts, interpretations, and proposals. Link the evidence supporting consequential claims.
- Run checks appropriate to the change. Report only checks actually run on the current device; use `not run` with the reason for unavailable checks.
- Keep full evidence in the relevant work files. Session notes and project status provide navigation and durable context.
