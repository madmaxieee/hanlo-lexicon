# Han-Lo Lexicon

A community-curated collection of Taiwanese Han-Lo writing recommendations,
starting from the LKK word list. The project is a local pilot.

## Layout

- `entries/<initial>/*.toml`: editable vocabulary records.
- `rules/`: conventions and context-dependent writing patterns.
- `sources/`: unmodified source snapshots and their metadata.
- `decisions/`: editorial decisions affecting multiple entries.
- `schema/`: the entry schema and field conventions.
- `tools/`: future validation and export commands.
- `.github/workflows/`: reserved for validation and release workflows.

Entries are filed by the complete consonantal initial of the first syllable of
`canonical_tl`. `zero/` holds zero-initial entries, including syllabic nasals.
Use `kh`, `ph`, `th`, `ts`, and `tsh` as separate directories. Alternate readings
stay with their entry even when their initials differ.

Each record has a permanent ID. Filenames combine a readable ASCII slug with
that ID; the slug is a navigation aid, not a phonetic encoding or identity key.
Correcting a canonical reading may move a file without changing its ID.
Preserve distinct written-form/reading pairs. Canonical readings select a filing
reference, not a superior dialect.

TOML files are the editable source. CSV and JSON downloads will be generated;
generated exports belong in `dist/` locally and in release assets when published.
Release automation and contribution forms are not implemented in this pilot.

See `schema/README.md` for record conventions and `RIGHTS.md` for source rights.
