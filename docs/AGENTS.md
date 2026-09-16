# Docs Directory

These rules apply to `docs/` and its subdirectories, supplementing the repository-root `AGENTS.md`.

- Store project conventions, collaboration guidance, and execution plans for research, engineering, and validation here. Keep literature surveys and research proposals in `research/`, experiment records in `experiments/`, paper drafts in `writing/`, and session notes in `notes/sessions/`. Link to those materials instead of duplicating them.
- Organize directories by purpose or topic, not by date. Prefer existing directories and add subdirectories only when distinct topics need separation; do not create empty placeholder directories.
- Keep project-level entry points, conventions, collaboration guidance, and `STATUS.md` at the root of `docs/`. Store execution plans in `docs/plan/`. Add other topic directories as their content grows.
- Use stable, descriptive filenames. Record dates and versions inside documents when useful. Preserve existing dated filenames; do not rename or move files merely to standardize naming.
- Update the existing document for routine clarifications, reordered steps, and minor revisions. Save alternatives that must coexist or substantial versions worth preserving separately, stating their scope, predecessor or successor, and the current authoritative entry point. Preserve original evidence and historical conclusions.
- Maintain existing `README.md` indexes and add topic indexes when needed. `plan/README.md` should identify the current plan and distinguish historical versions from alternatives; do not label superseded documents as competing current main plans.
- Keep `STATUS.md` limited to the current task, status, authoritative references, and next action. Put full designs in their own documents. Update the status only when the task, status, accepted decisions, or next action materially changes; do not turn it into a discussion or work log.
- Update affected indexes and references when adding, moving, renaming, or superseding documents. Check local links and script paths after moves. Preserve external citations and links to historical Git revisions.
- State each plan's status and distinguish proposed designs, completed results, and hypotheses awaiting validation. Link actual results to their experiment records; do not present planned metrics or checks as completed results.
- After edits, check relevant links, section references, and document status for consistency. Use the smallest structural change needed and preserve files and edits outside the task scope.
