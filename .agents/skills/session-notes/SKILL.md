---
name: session-notes
description: Resolve and maintain the repository note belonging to the current platform session. Use when starting or resuming a session, preserving durable context, retrieving a known session note, or preparing a Git handoff; do not use for chat transcripts, general research notes, experiment logs, or routine task status.
---

# Session Notes

Maintain one concise, Git-tracked note per platform session. The exact session ID in the filename is the lookup key; never inspect note contents to determine ownership.

## Resolve the Note

1. Read the repository-root `AGENTS.md`.
2. Obtain the platform's exact stable session ID. In Codex, use `CODEX_THREAD_ID`; fall back to `CODEX_SESSION_ID` only when the thread ID is unavailable. On another host, use only the stable session ID explicitly exposed by that host.
3. Require a filename-safe ID. Codex IDs must retain their complete UUID form. Do not shorten, normalize, decorate, or replace the ID with a timestamp or topic.
4. Derive the path directly as `notes/sessions/<session-id>.md`.
5. If that exact file exists, read it as the current session's note. If it does not exist, treat the session as having no note yet; do not search for or reuse another note.

Stop and report the limitation when no stable session ID is available. Never infer the current note from file contents, topic names, timestamps, modification times, directory order, or the most recently used file.

## Create the Note

Create the ID-derived file only when the session first has durable information worth preserving. Use this compact header:

```markdown
# Session: <concise description>

Session ID：`<exact-session-id>`

开始时间：YYYY-MM-DDTHH:MM±HH:MM
```

The title is descriptive metadata, not an identifier. It may be refined without renaming the file. Follow the repository language preference in `AGENTS.md`.

## Record Durable Context

Append concise entries in chronological order using `- YYYY-MM-DDTHH:MM±HH:MM [tag] content`. Use ISO 8601 minute precision with the full local calendar date and numeric UTC offset, for example `2026-08-24T10:59+08:00`. Never use a time-only value or an ambiguous timezone abbreviation such as `CST`. Use `[约定]`, `[决策]`, `[发现]`, `[结果]`, `[限制]`, `[待办]`, or `[更正]`.

Record only information that will remain useful when the session is resumed: important agreements or decisions, verified findings, meaningful results, constraints that affect the approach, and explicit open questions or next steps. Link the authoritative repository file when useful.

Do not record chat transcripts, routine commands, temporary progress, resolved minor errors, unverified guesses, information easily recovered from Git, or secrets. Keep complete evidence and experiment results in their proper research or experiment files. When correcting a durable entry, append a `[更正]` entry instead of silently rewriting history.

## Retrieve or Resume

Resolve the current session again from the platform ID and open only the exact ID-derived path. To retrieve another known session, derive its path from that session's exact ID. A missing path means no note exists for that ID; it is not permission to identify a substitute by scanning note bodies.
