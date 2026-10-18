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

## Personal curated batch

The personal lists dated 2026-10-18 contain 397 romanized input/output pairs and
25 Hanji pairs. Their full batch is represented by 362 entries, including the
original ten pilot entries with IDs 1 through 10. New entries use IDs 11 through
362; the next unused ID is 363.

Alternate readings stay with their word. Unrelated source homographs remain
separate records with distinct identity notes. The maintainer selected `leh` and
`kánn-ná` as preferred forms and MOE's `tshì-môo-thâng` reading for `刺毛蟲`.
See [the import decisions](decisions/personal-curated-import-2026-10-19.md) for
input checksums, coverage, and source interpretation.

Each entry cites original LKK evidence; the corrected `刺毛蟲` reading also cites
the pinned MOE dictionary. Original spreadsheet content remains in the archived
TSV. All 362 records are `imported` and await editorial review.
