# Double-hyphen LKK entries, 2026-10-19

## Scope and source coverage

Scan all 894 data records in the original `lkk-2024-05-10` TSV using the
`建議用字` (recommended written form) column. Exactly six records begin with
`--`. They represent eight written forms:

| Parsed source record | Preferred form | Canonical TL | Alternate readings |
| --- | --- | --- | --- |
| 7 | `--a` | `--a` | none |
| 7 | `--ā` | `--ā` | none |
| 7 | `--à` | `--à` | none |
| 8 | `--ê` | `--ê` | none |
| 9 | `--ah` | `--ah` | none |
| 10 | `--啊` | `--ah` | none |
| 360 | `--lah` | `--lah` | none |
| 377 | `--leh` | `--leh` | none |

Record numbers are one-based parsed TSV records, including the header. The
source SHA-256 remains
`903c4193aa011163493289dde79b01e1be7e19b0c5afecb4c7216dd4205431c1`.
The snapshot is unchanged.

## Representation and checks

At the maintainer's explicit request, represent the three forms in LKK record 7
as separate entries. Preserve ID 363 for `--a` and allocate IDs 369 and 370 for
`--ā` and `--à`, respectively. Each form is its own canonical reading, with no
alternate readings. This representation records the requested separation without
asserting distinct lexical identities. Preserve the source's `隨前變調` annotation
in `usage_notes` for all three entries and for record 8, without inventing a
tone-selection rule. The CSV output still includes all eight written forms.

Use the source's explicit `--ah` reading for `--啊`. For romanized headwords
without a separate reading, use the romanized headword itself. Preserve every
leading double hyphen. Do not combine `--ah` (record 9, MOE `矣`) with `--啊`
(record 10, a sentence-final particle written in Hanji).

Check each candidate against existing records, the complete LKK snapshot, and
the checksum-pinned MOE ODS. The lookup helper does not split the comma-separated
recommended-form cell in record 7, so verify that source record and all three
forms directly as part of the full-column scan. The other five candidates have
matching MOE readings on the `詞目` sheet, at rows 4370, 3337, 7018, 7068,
and 4770, respectively; retain these precise citations alongside LKK evidence.
The three variants in record 7 have no MOE hit and remain supported by LKK.

Retain the simple LKK MOE-column spellings `矣`, `啦`, and `咧`, which the pinned
MOE snapshot confirms. Leave blank source MOE fields unpopulated.
The existing `leh` entry (ID 120, LKK record 376) corresponds to `在、正在`;
LKK record 377 and MOE row 4770 support the separate `--leh` particle.
No existing exact form/reading pair covers any requested addition.

The maintenance tool allocated IDs 363 through 368 for the initial six additions
and IDs 369 and 370 when splitting the forms in record 7. All eight entries remain
`imported`. Existing IDs 1 through 362 and their file contents stay unchanged.
The repository now has 370 records, with next unused ID 371.
