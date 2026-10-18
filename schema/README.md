# Entry format, version 1

Each `entries/<initial>/<preferred-form>--<id>.toml` file represents an editorial
recommendation for a word. Use `tools/lexicon.py` to allocate IDs, check candidates,
format files, and validate this schema.

## Fields

- `schema_version`: `1`.
- `id`: a permanent positive integer. The pilot uses 1 through 10. IDs do not encode
  a spelling, reading, source row, or sense number.
- `canonical_tl`: a verified TL filing reading, including tone marks.
- `preferred_form`: recommended output; may be Hanji, romanization, or mixed.
- `alternate_readings`: explicitly supported alternate input readings, excluding
  `canonical_tl` itself. An alias does not replace the preferred output.
- `moe_forms`: verified MOE spellings, distinct from the preferred recommendation.
- `review_status`: `imported`, `reviewed`, or `disputed`.
- `identity_note`: optional concise explanation distinguishing an unrelated word
  with the same written form/reading. Related senses need not become separate entries.
- `usage_notes`, `editorial_rationale`: optional prose. Omit when unknown.
- `sources`: original evidence, using one of the reference shapes below.

Empty arrays mean that no values are recorded, not that alternatives do not exist.
Meanings, examples, other spellings, and copied original cells are not entry fields.
Dictionary definitions displayed by lookup are external evidence for editorial review.

## Original references

Local source reference:

```toml
[[sources]]
row = 55
snapshot = "lkk-2024-05-10"
```

MOE references use the ID pinned in `references/moe.toml` and additionally name
the ODS sheet in `sheet`. The original ODS stays in the ignored download cache.
LKK snapshot IDs resolve to `sources/<snapshot>/metadata.toml`. Record numbers
are one-based, include the header as record 1, and count parsed records rather
than physical lines inside quoted fields. ODS row numbers include repeated rows.

Published external evidence can use `url` and a precise `locator`, such as a
dictionary entry ID, section, or page. Use HTTP(S) URLs. Cite either a snapshot/row
or a URL/locator. A pointer establishes provenance, not semantic agreement: review
the actual source. Do not cite a cleaned personal CSV as independent evidence.

## Identity and allocation

Written form and canonical reading identify a candidate word, not necessarily a
unique editorial record. Preserve unrelated homographs even if both fields match.
Every additional same-pair word needs a distinct `identity_note`; an exact repeated
identity is rejected. Alternate-reading overlap is also checked before adding.

`id-sequence.toml` records the next unused integer. `add` reserves it under a local
writer lock before writing the entry. IDs remain stable through renaming, deletion,
or merging. Never decrement the counter. A failed write can leave a gap; gaps are
valid and reserved numbers must not be reused. `next-id` previews without reserving.
Separate clones can still allocate the same number; validate and resolve collisions
before merging, without silently renumbering already published entries.

## Canonical formatting and paths

Entry keys and source-reference keys are alphabetical. Set-like arrays and source
references have deterministic ordering. Entries use NFC Unicode, UTF-8, LF, and a
single final newline. Prose is serialized as a quoted TOML string with explicit
newline escapes. Source snapshots remain byte-for-byte unchanged.

The filename uses the preferred form and an ID padded to at least six digits:
`beh--000005.toml`, `bái--000007.toml`. Preserve Hanji and tone marks. Percent-escape
filesystem-reserved characters and `%`; the script owns this encoding. Never parse
identity or reading from the filename: the TOML fields are authoritative.

File under the first syllable's complete TL consonantal initial. Distinguish `kh`,
`ph`, `th`, `ts`, and `tsh`. Zero-initial syllables, including syllabic `m` and `ng`,
go under `zero/`; a leading neutral marker does not change filing. Filing does not
validate a pronunciation. Inventory reference: TaigiKeyboard's
`docs/phonetics/taigi-phonetics-reference.md` sections 2/9 and
`taigi-converter/src/tables.js`.

Checks preserve tone distinctions and single/double hyphens. Search normalizes NFC,
case, and whitespace; it does not convert POJ, remove tones, or infer semantic identity.
