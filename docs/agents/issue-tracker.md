# Issue tracker: local Markdown

Engineering specs and tickets live under `.scratch/<feature-slug>/`. “Publish to
the issue tracker” means write a local file here. External publication still
requires the maintainer's explicit request.

- Spec: `spec.md` in the feature directory.
- Tickets: `issues/NN-<slug>.md`, one per file, numbered from `01`.
- Triage: a `Status:` line using the roles in [triage-labels.md](triage-labels.md).
- Blocking edges: `Blocked by: NN, NN`, referring to tickets in that feature.
- Comments: append under `## Comments` in the ticket.
- Completed implementation: record the outcome and set `Status: resolved`.

Fetch a ticket by reading its referenced path. A ticket is ready when its blockers
are resolved and its triage status is `ready-for-agent`. Claim it with
`Status: claimed` before implementation.

For wayfinding, use `.scratch/<effort>/map.md` and one child ticket per question
under `issues/`. Record `Type: research`, `prototype`, `grilling`, or `task`.
Claim ready tickets with `Status: claimed`; resolve them by appending `## Answer`,
setting `Status: resolved`, and adding a context pointer to the map.

Keep work plans here; durable editorial decisions belong in
[decisions/](../../decisions/README.md), and word-specific evidence belongs in
the entry fields defined by the [schema](../../schema/README.md).
