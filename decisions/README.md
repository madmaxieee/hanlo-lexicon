# Editorial decisions

This directory preserves explicit editorial decisions and import history.
Use the [glossary](../GLOSSARY.md) for terminology, the [schema](../schema/README.md)
for current record conventions, and the
[maintenance skill](../.agents/skills/maintain-lexicon/SKILL.md) for the current workflow.

## Standing decisions

Read these when the affected writing or evidence question arises. Each record
also preserves its original scope and entry-level resolutions.

- [个, 仔, and sense-dependent 甲](combo-spellings-2026-10-21.md): adopted component
  writing and the deliberate 甲 conflict; 【替】 remains a contextual preference.
- [Curated Hanji and 𠞭](hanji-forms-2026-10-20.md): Hanji metadata can record a
  curated form without asserting whole-word MOE inclusion or changing output.
- [Same-reading words are separate entries](same-reading-distinct-words-2026-11-12.md):
  unrelated words sharing a reading get their own entry with an `identity_note`;
  keyboard CSV still emits one row.
- [Post-import related recommendations](tsbp-386-batch2-import-2026-10-26.md#post-import-related-recommendation-workflow):
  regenerate against the current inventory and retain the matching seed spelling.

## Import history

These are dated audit records, including explicit word-level conflict resolutions.
Counts, cache paths, and pending suggestions describe the recorded run. Check
current entries and regenerate evidence before acting on an old suggestion.
Keep these records at their existing paths so entry citations and handoffs remain usable.

### LKK and MOE

- [LKK selection, 2026-10-19](lkk-selection-import-2026-10-19.md).
- [Leading double-hyphen LKK entries, 2026-10-19](double-hyphen-import-2026-10-19.md).
- [Full LKK coverage and existing-entry resolutions, 2026-10-21](lkk-full-import-review-2026-10-21.md).
- [MOE loanword appendix, 2026-10-22](moe-loanword-appendix-import-2026-10-22.md).

### TSBP, by issue

- Issue 385: [Roman batch 1](tsbp-385-batch1-import-2026-11-01.md),
  [Roman batch 2](tsbp-385-batch2-import-2026-11-01.md),
  [Roman batch 3](tsbp-385-batch3-import-2026-11-02.md),
  [Hanji batch](tsbp-385-hanji-import-2026-11-02.md).
- Issue 386: [Roman batch 1 and related approvals](tsbp-386-batch1-import-2026-10-24.md),
  [Roman batch 2 and related approvals](tsbp-386-batch2-import-2026-10-26.md),
  [Hanji batch](tsbp-386-hanji-import-2026-10-26.md).
- [Issue 388, including adopted tshap雜](tsbp-388-import-2026-10-22.md).
- [Issue 389 and conflict resolutions](tsbp-389-import-2026-10-21.md).
- [Issue 390 pilot and follow-up batches](tsbp-pilot-import-2026-10-19.md).
- [All issues: neutral-tone `--` forms, 2026-11-08](tsbp-neutral-tone-import-2026-11-08.md).

## Active source mappings

[tsbp-source-mappings.json](tsbp-source-mappings.json) records explicit whole-word
source spellings mapped to existing entries. This is active decision data rather
than an import narrative. Use the
[source-mapping workflow](../.agents/skills/review-tsbp-roman/SKILL.md#source-spellings-of-existing-words)
to validate and persist exported decisions; harvests detect stale targets.

## Record a decision

Record decisions affecting multiple entries, explicit identity/spelling resolutions,
and import audits here. Keep word-specific notes and original citations in entry
TOML as required by the schema; link to them rather than duplicating a word list
when no batch audit is needed.

General writing conventions and context-dependent patterns belong in sourced
decision records here. Distinguish inherited guidance from maintainer choices.

A decision record should state the question, source evidence or discussion,
explicit adopted resolution, affected entry IDs or workflow, and any known reason
for the choice. Omit unknown reasons. Include the date and use a descriptive
filename consistent with the existing records. Reference earlier records when a
later decision revises them, preserving the original account.

For architectural decisions, record only real choices that are costly to reverse,
surprising without context, and grounded in an actual trade-off. Do not invent
retrospective rationale to fill a template. Temporary plans belong in the
[local issue tracker](../docs/agents/issue-tracker.md).
