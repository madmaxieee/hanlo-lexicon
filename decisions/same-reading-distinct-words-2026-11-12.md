# Same-reading words are separate entries

[Decisions](README.md) · [Glossary](../GLOSSARY.md)

## Decision

On 2026-11-12 the maintainer resolved that words which merely share a canonical
reading (and, where applicable, a written form) but are not the same word are
separate entries, each with its own ID. Do not ask again for this pattern and do
not merge the new word into the existing entry, add its Hanji to that entry or map
it to that entry as a source spelling.

Give the later entry an evidence-backed `identity_note` stating what distinguishes
it, such as a different MOE headword and definition or different curated Hanji.

## Output behavior

- The keyboard/release CSV (`build-csv`) is for an input-method dictionary and has
  columns `tl,preferred_form`. Entries that produce an identical row are emitted
  once, so separate homographs still appear as a single row when both are exported.
  Pure-Hanji preferred forms remain excluded.
- Reader-facing exports retain homographs under their own IDs, so both entries
  appear in the human-readable version.

## Applied in TSBP issue 382

| Anchor | Existing entry | New entry | Distinguishing evidence |
| --- | --- | --- | --- |
| `lé` | 4438 `禮` (`lé`) | 5162 `lé`, alternate `lué` | MOE 詈 (咒罵) versus 禮 (rites, gifts) |
| `peh-tsiūnn` | 166 `peh` (擘, LKK) | 5163 `peh`, Hanji 𬦰 | MOE 𬦰 (爬、攀登) versus 擘 |

The custom request `khuàinn` had no existing entry. The maintainer confirmed that
its source is the cited article, and it was added as 5164. All three remain
`imported`.
