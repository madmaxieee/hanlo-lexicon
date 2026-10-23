# Han-Lo Lexicon

A community-curated collection of Taiwanese Han-Lo writing recommendations,
starting from the [LKK word list](sources/lkk-2024-05-10/word-list.tsv).

## Layout

- `entries/<initial>/<prefix>/*.toml`: editable vocabulary records.
- `rules/`: conventions and context-dependent writing patterns.
- `sources/`: unmodified source snapshots and their metadata.
- `decisions/`: editorial decisions affecting multiple entries.
- `schema/`: the entry schema and field conventions.
- `tools/`: maintenance commands and CSV builds.
- `.agents/skills/maintain-lexicon/`: project-local vocabulary maintenance skill.
- `.github/workflows/`: CSV build artifacts and tagged CSV releases.

Entries are filed by the complete consonantal initial of the first syllable of
`canonical_tl`, then that initial plus the complete vowel sequence. For example,
`beh` files under `b/be/`, `bu` under `b/bu/`, and `bueh` under `b/bue/`.
Tone marks and final consonants do not affect the prefix. Only occupied
directories are created. `zero/` holds zero-initial entries, including syllabic nasals.
Use `kh`, `ph`, `th`, `ts`, and `tsh` as separate directories. Alternate readings
stay with their entry even when their initials differ.

Each record has a permanent integer ID. Filenames combine the preferred written
form with a zero-padded ID, such as `bái--000007.toml`.
Correcting a canonical reading may move a file without changing its ID.
Optional `rule_generated = true` distinguishes preferred spellings inferred only
from writing rules from source-backed or curated recommendations. It does not
replace review status or source citations.
Preserve unrelated homographs even when spelling and reading both match, using a
distinct identity note. Canonical readings select a filing reference, not a superior dialect.

TOML files are the editable source. Build a CSV locally with
`python3 tools/lexicon.py build-csv`; the result is `dist/lexicon.csv` with columns
`preferred_form,tl`. This default export excludes pure-Hanji preferred forms.
Use `python3 tools/lexicon.py build-csv --include-pure-hanji` to write
`dist/lexicon-all.csv` containing all forms. Alternate outputs preserve the
preferred form's Han characters and change its romanized syllables to match the
alternate reading.
Alternates with fewer syllables than the canonical reading are treated as
contractions and use the full alternate reading as both suggested form and TL.
Other Hanji-only readings retain the same suggested Hanji. Identical
CSV rows are deduplicated while distinct TOML word identities are preserved.
Add `--canonical-only` to either command to export only each entry's
`preferred_form,canonical_tl` pair, skipping alternate readings. These exports
write `dist/lexicon-canonical.csv` and `dist/lexicon-all-canonical.csv`, respectively.
See `tools/README.md` for examples and GitHub Actions build/release instructions.
Optional `hanji_forms` records Hanji spellings independently of MOE inclusion;
it is lookup metadata and does not add CSV output rows. The TSBP discovery and
review tools are documented in `tools/tsbp/README.md`.
For read-only pure-Hanji corpus matching, overlap analysis, and combo coverage,
see [pure-Hanji discovery](tools/README.md#pure-hanji-corpus-discovery).
Both GitHub workflows generate both CSV versions. Tagged releases include
`lexicon.csv`, `lexicon-all.csv`, `SHA256SUMS`, and `RIGHTS.md`.
JSON exports and contribution forms are not implemented.

See `schema/README.md` for record conventions and `RIGHTS.md` for source rights.

## Shortcuts with just

With `just` installed, run `just` to list commands. Recipes use the project folder
as their working directory, including when invoked from a subdirectory.

| Command | Result |
| --- | --- |
| `just export` | `dist/lexicon.csv`, including alternate readings |
| `just export-all` | `dist/lexicon-all.csv`, including pure Hanji |
| `just export-canonical` | `dist/lexicon-canonical.csv`, canonical readings only |
| `just export-all-canonical` | `dist/lexicon-all-canonical.csv`, all forms, canonical readings only |
| `just validate` | Validate entries and source references |
| `just format-check` | Check formatting without edits |
| `just format` | Apply canonical formatting and entry paths |
| `just test` | Run the maintenance tool tests |
| `just check` | Run validation, formatting checks, and tests |

The Python commands remain available without `just`.

## Maintain entries

Use the `maintain-lexicon` project skill or the commands in `tools/README.md`.
The tool checks existing entries, the full LKK snapshot, and a checksum-pinned
copy of the original MOE ODS. On first use the tool downloads that exact snapshot
from TaigiKeyboard GitHub into ignored `.cache/dictionaries/moe/`; later lookups
work offline. The next unused ID is tracked only in `id-sequence.toml`; the tool
allocates new IDs under a local writer lock.
