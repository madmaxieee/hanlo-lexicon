# Han-Lo Lexicon

A community-curated collection of Taiwanese Han-Lo writing recommendations,
starting from the LKK word list. The project is a local pilot.

## Layout

- `entries/<initial>/*.toml`: editable vocabulary records.
- `rules/`: conventions and context-dependent writing patterns.
- `sources/`: unmodified source snapshots and their metadata.
- `decisions/`: editorial decisions affecting multiple entries.
- `schema/`: the entry schema and field conventions.
- `tools/`: offline maintenance commands; release exports are planned.
- `.agents/skills/maintain-lexicon/`: project-local vocabulary maintenance skill.
- `.github/workflows/`: reserved for validation and release workflows.

Entries are filed by the complete consonantal initial of the first syllable of
`canonical_tl`. `zero/` holds zero-initial entries, including syllabic nasals.
Use `kh`, `ph`, `th`, `ts`, and `tsh` as separate directories. Alternate readings
stay with their entry even when their initials differ.

Each record has a permanent integer ID. Filenames combine the preferred written
form with a zero-padded ID, such as `bái--000007.toml`.
Correcting a canonical reading may move a file without changing its ID.
Preserve unrelated homographs even when spelling and reading both match, using a
distinct identity note. Canonical readings select a filing reference, not a superior dialect.

TOML files are the editable source. CSV and JSON downloads will be generated;
generated exports belong in `dist/` locally and in release assets when published.
Release automation and contribution forms are not implemented in this pilot.

See `schema/README.md` for record conventions and `RIGHTS.md` for source rights.

## Maintain entries

Use the `maintain-lexicon` project skill or the commands in `tools/README.md`.
The tool checks existing entries, the full LKK snapshot, and a checksum-pinned
copy of the original MOE ODS. On first use the tool downloads that exact snapshot
from TaigiKeyboard GitHub into ignored `.cache/dictionaries/moe/`; later lookups
work offline. New IDs come from `id-sequence.toml` under a local writer lock.
