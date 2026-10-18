# Entry format, version 1

Each `entries/<initial>/*.toml` file represents one editorial recommendation with
one canonical TL reading and one preferred written form. Parse TOML into a data
object and validate it against `entry.schema.json` (JSON Schema draft 2020-12).

## Fields

- `schema_version`: `1`.
- `id`: permanent `e` plus six digits. IDs do not encode source row numbers.
- `canonical_tl`: the normalized TL filing reading, including tone marks.
- `preferred_form`: recommended output; may be Hanji, romanization, or mixed.
- `alternate_readings`: alternate input readings explicitly supported by evidence;
  exclude `canonical_tl` itself. An alias does not replace the preferred output.
- `moe_forms`: spellings from the source's MoE column, kept distinct from recommendations.
- `other_spellings`: spellings from the source's variant column.
- `mandarin_meanings`: Mandarin glosses, not invented translations.
- `examples`: source examples, retaining original spelling and punctuation.
- `review_status`: `imported`, `reviewed`, or `disputed`.
- `usage_notes`, `editorial_rationale`: optional multiline text. Omit when unknown.
- `sources`: one or more source references with a snapshot ID, one-based logical
  record number, and a `fields` table preserving the exact original cell strings.

For TSV snapshots, record 1 is the header; for headerless CSV snapshots, record 1
is the first vocabulary pair. These are parsed record numbers, not physical line
numbers when a quoted field contains newlines. Source IDs resolve to the `id`
field of a `sources/<snapshot>/metadata.toml` file.

Keep all original source cells in `sources[].fields`, including empty cells.
Structured arrays may split an explicit enumeration, while the archived source
and exact fields preserve its original presentation. An empty array means that
the imported source supplies no values for that field, not that alternatives do
not exist. Missing optional prose means that no explanation is recorded.

## Repository checks

In addition to schema validation, check globally unique IDs, distinct preferred
form/canonical-reading pairs, correct initial directories, source IDs and row
bounds, exact source-field matches, and snapshot SHA-256 checksums. Do not use
preferred spelling alone as a deduplication key.

## Pilot selection

Select the first ten distinct output forms in the romanized curated CSV, in file
order, grouping explicit input aliases under their output's entry. This selects
twelve input/output rows because two entries have alternate input readings.
Keep pilot records `imported`; selection is not community acceptance.
