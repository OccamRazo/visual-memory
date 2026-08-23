# Visual Memory Project Guide

## Project goals

This project studies visual memory in large models: how a model selects, compresses, stores, retrieves, and updates information from a continuous visual stream. The current primary setting is ultra-long video understanding, with particular interest in its relationship to sparse attention, KV cache, external or parametric memory, and evaluation methods.

The repository should preserve the complete research process, from literature review, problem formulation, and hypotheses through experiments, analysis, and paper writing. Existing surveys are exploratory material and do not represent a final approach or conclusion.

## Communication

- The user prefers Chinese. Communicate with the user in Chinese by default, including progress updates, questions, explanations, and handoff summaries, unless the user explicitly requests another language.

## Repository structure

Create directories only when they are actually needed. The recommended structure is:

```text
research/
  ideas/          # Early ideas, survey reports, and proposal drafts
  literature/     # Literature notes, evidence tables, and citation data
  hypotheses/     # Testable research questions and hypotheses
src/              # Reusable model, data, and evaluation code
experiments/      # Configurations, scripts, records, and results by experiment ID
data/             # Data documentation, splits, and small metadata; no large raw data
docs/             # Project conventions, development plans, and collaboration workflows
notes/
  sessions/       # One ID-addressable note per Codex/ChatGPT session
writing/
  drafts/         # Outlines and paper drafts
  figures/        # Final figures and instructions for generating them
```

Use `EXP-YYYYMMDD-short-name/` for experiment directories. Every experiment must include at least one `README.md` recording its objective, hypothesis, data and model versions, configuration, run instructions, metrics, results, and conclusions.

## Session notes

- Use `.agents/skills/session-notes/SKILL.md` when starting or resuming a session, retrieving a known session note, deciding whether durable context should be recorded, and preparing a Git handoff.
- Session notes are concise navigation aids, not the sole source of truth. Keep complete evidence and results in the relevant research or experiment files.

## Multi-device Git collaboration

- All development devices are peer nodes; there is no authoritative workstation. Devices hand off the project only through Git states that have been committed and pushed.
- Before starting or taking over a task, read this file, use the `session-notes` skill to resolve and read the current session note when it exists, and read any relevant experiment documentation. Then fetch the latest state from `origin`, confirm that the worktree is clean, and update the target branch.
- Small, low-risk documentation-only changes may be made directly on a clean, up-to-date `main`. Use a `work/<short-name>` branch for code changes, experiments, or work that requires cross-device handoff. Continue a given task on only one device at a time; another device may take over only after an explicit handoff.
- Follow `.agents/skills/git-handoff/SKILL.md` for takeover and handoff. If branches have diverged, stop and report the divergence; do not automatically rebase, merge, overwrite, or force-push.
- A handoff must leave a focused, understandable commit and push the current branch. Never hand off through uncommitted files or a stash.
- Report only checks actually run on the current device. When the required environment is unavailable, explicitly mark the check as `未运行` (not run); never claim that unexecuted code has passed validation.
- Keep large datasets, logs, checkpoints, and output artifacts on the device where they were produced. Do not synchronize them through Git; commit only concise results, reproduction details, and necessary local-location notes when appropriate.

## Working constraints

- Read relevant material before making changes. Preserve original surveys and failed experiments; never silently overwrite historical results.
- Distinguish literature facts, inferences, and ideas awaiting validation. Verifiable facts should cite a paper, link, or other source.
- Experiments must be reproducible: fix and record random seeds, environment, configuration, commands, and key versions. Store results by independent run.
- Prefer the smallest verifiable change. Put shared logic in `src/` rather than copying it across experiments and allowing the copies to diverge.
- Do not commit datasets, model weights, large logs, caches, or secrets. Record acquisition instructions and local path conventions in `data/` or the relevant experiment documentation.
- Figures must be traceable to their data and generation method. Never edit numeric values by hand to improve presentation.
- Match conclusions to the strength of the evidence, and record negative results, limitations, anomalies, and unresolved questions.
- Use Chinese by default when documenting the research process; submission-facing content may be in English. Keep file names, experiment IDs, and code identifiers concise and consistent.
- Do not lock in a specific model, dataset, technical approach, or submission target without an explicit request.
