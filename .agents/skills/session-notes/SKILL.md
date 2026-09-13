---
name: session-notes
description: Resolve and maintain the current platform session's repository note and read the shared task entry point when starting, resuming, or handing off work. Use for durable context, not transcripts, full work results, or routine progress logs.
---

# Session Notes

Keep one concise note per platform session, intended for Git tracking. Its exact session ID is the lookup key; never inspect note contents to determine ownership.

## Read shared context

Read the repository-root `AGENTS.md` and `docs/STATUS.md` when it exists. The status file supplies the current task, state, authoritative references, and next action across sessions. Follow relevant links to verify its claims; a stale status entry does not override actual files or current user instructions.

Update the shared status only when those facts materially change. Keep accepted decisions brief and link their authoritative location. Do not copy session histories into it, automatically resume unrelated tasks, or infer cross-device handoff authorization from a status entry.

## Resolve the current note

1. Obtain the platform's exact stable session ID. In Codex, use `CODEX_THREAD_ID`; fall back to `CODEX_SESSION_ID` only when the thread ID is unavailable. On another host, use only a stable session ID explicitly exposed by that host.
2. Require a filename-safe ID. Preserve a Codex ID's complete UUID form; do not shorten, normalize, decorate, or replace it with a timestamp or topic.
3. Derive the path directly as `notes/sessions/<session-id>.md`.
4. Read that exact file if it exists. Otherwise, this session has no note yet; do not search for or reuse another note.

When a stable, filename-safe ID is unavailable, skip only session-note lookup and creation. Continue authorized work and use authoritative task files and the shared status for durable information. Briefly report the limitation when it affects continuity; do not invent an ID or infer ownership from content, timestamps, or directory order.

## Create and maintain the note

Create the ID-derived file only when the session has durable information worth preserving. Use a compact header in the repository's preferred language, for example:

```markdown
# Session: <concise description>

Session ID：`<exact-session-id>`

记录创建时间：YYYY-MM-DDTHH:MM±HH:MM
```

The title is descriptive metadata, not an identifier. It may be refined without renaming the file.

Append entries chronologically as `- YYYY-MM-DDTHH:MM±HH:MM [tag] content`. Use the full local date and numeric UTC offset, for example `2026-08-24T10:59+08:00`. Useful tags include `[约定]`, `[决策]`, `[发现]`, `[结果]`, `[限制]`, `[待办]`, and `[更正]`.

Record only durable agreements, decisions, verified findings, meaningful outcomes, constraints, and explicit next actions. Link authoritative files rather than copying their contents. Preserve corrections as new entries.

Do not record transcripts, routine commands, temporary progress, resolved minor errors, unverified guesses, details readily recoverable from Git, or secrets. Keep complete evidence and results in the task's own files.

## Retrieve another known note

Use another session's exact ID only when that session is explicitly identified by the user or a relevant task reference. Derive its path directly. A missing file is not permission to search other notes for a substitute or treat another session's note as the current one.
