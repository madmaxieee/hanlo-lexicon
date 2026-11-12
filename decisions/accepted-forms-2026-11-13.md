# Accepted forms

[Decisions](README.md) · [Glossary](../GLOSSARY.md) · [Schema](../schema/README.md)

## Decision

On 2026-11-13 the maintainer asked for a way to keep a second spelling of the
same word as valid output without making it the recommendation. Entries gain an
optional `accepted_forms` array:

- The keyboard CSV exports the preferred form and every accepted form, each with
  the entry's readings. The pure-Hanji filter now applies to each output form
  rather than to the whole entry.
- Reader-facing exports list only the preferred form.
- Duplicate checks and later TSBP harvests treat accepted forms as tracked
  spellings. A candidate matching an accepted form and reading is an
  `accepted_pair`, refused like an exact pair.

## Applied after TSBP issue 382 review batch 2

These approvals were the same words as existing entries. Preferred forms and IDs
are unchanged; the approved spelling became an accepted form with its MOE and
article citations.

| Entry | Preferred form | Accepted form | Approval |
| --- | --- | --- | --- |
| 1043 | `磕` | `kha̍p` | `kha̍p`, MOE 磕, 詞目 row 11237 |
| 942 | `密` | `ba̍t` | `ba̍t`, MOE 密, 詞目 row 7136 |
| 4271 | `mî-tsinn` | `綿tsinn` | source spelling `綿chiⁿ`, MOE 綿精, 詞目 row 14441 |
| 542 | `liàn-tńg` | `輾轉` | `輾tńg`; the maintainer chose 輾轉 over the mixed spelling |

`輾轉` is pure Hanji, so it adds no keyboard row; it is recorded for duplicate
checks and Hanji harvests. The approval `páiⁿ` was dropped.
