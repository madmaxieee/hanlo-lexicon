# Han-Lo Lexicon

A community-curated collection of Taiwanese Han-Lo writing recommendations,
starting from the [LKK word list](sources/lkk-2024-05-10/word-list.tsv).

## Layout

- `entries/<initial>/*.toml`: editable vocabulary records.
- `rules/`: conventions and context-dependent writing patterns.
- `sources/`: unmodified source snapshots and their metadata.
- `decisions/`: editorial decisions affecting multiple entries.
- `schema/`: the entry schema and field conventions.
- `tools/`: maintenance commands and CSV builds.
- `.agents/skills/maintain-lexicon/`: project-local vocabulary maintenance skill.
- `.github/workflows/`: CSV build artifacts and tagged CSV releases.

Entries are filed by the complete consonantal initial of the first syllable of
`canonical_tl`. `zero/` holds zero-initial entries, including syllabic nasals.
Use `kh`, `ph`, `th`, `ts`, and `tsh` as separate directories. Alternate readings
stay with their entry even when their initials differ.

Each record has a permanent integer ID. Filenames combine the preferred written
form with a zero-padded ID, such as `bái--000007.toml`.
Correcting a canonical reading may move a file without changing its ID.
Preserve unrelated homographs even when spelling and reading both match, using a
distinct identity note. Canonical readings select a filing reference, not a superior dialect.

TOML files are the editable source. Build a CSV locally with
`python3 tools/lexicon.py build-csv`; the result is `dist/lexicon.csv` with columns
`preferred_form,tl`. This default export excludes pure-Hanji preferred forms.
Use `python3 tools/lexicon.py build-csv --include-pure-hanji` to write
`dist/lexicon-all.csv` containing all forms. Alternate outputs preserve the
preferred form's Han characters and change its romanized syllables to match the
alternate reading.
Hanji-only forms retain the same suggested Hanji for every reading. Identical
CSV rows are deduplicated while distinct TOML word identities are preserved.
See `tools/README.md` for examples and GitHub Actions build/release instructions.
Optional `hanji_forms` records Hanji spellings independently of MOE inclusion;
it is lookup metadata and does not add CSV output rows. The TSBP discovery and
review tools are documented in `tools/tsbp/README.md`.
Both GitHub workflows generate both CSV versions. Tagged releases include
`lexicon.csv`, `lexicon-all.csv`, `SHA256SUMS`, and `RIGHTS.md`.
JSON exports and contribution forms are not implemented.

See `schema/README.md` for record conventions and `RIGHTS.md` for source rights.

## Maintain entries

Use the `maintain-lexicon` project skill or the commands in `tools/README.md`.
The tool checks existing entries, the full LKK snapshot, and a checksum-pinned
copy of the original MOE ODS. On first use the tool downloads that exact snapshot
from TaigiKeyboard GitHub into ignored `.cache/dictionaries/moe/`; later lookups
work offline. The next unused ID is tracked only in `id-sequence.toml`; the tool
allocates new IDs under a local writer lock.
