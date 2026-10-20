# Maintenance commands

Run from the repository root with Python 3.11 or newer. The tool has no third-party
dependencies. Dictionary searches run offline after the first-use download.

## Dictionary cache

The first command that needs MOE automatically downloads the exact ODS snapshot
from TaigiKeyboard's GitHub repository at the revision pinned in
`references/moe.toml`. It verifies SHA-256 before atomically saving the file under
`.cache/dictionaries/moe/<sha256>/kautian.ods`. This directory is ignored by VCS.
No second repository, machine-local path, or manual setup is required.

To populate or verify the cache explicitly:

```sh
python3 tools/lexicon.py fetch-moe
```

Subsequent lookups read only the cached copy and check its checksum. A download
failure or checksum mismatch stops the operation; there is no unverified fallback
or automatic repinning. Remove a corrupt cache file to reacquire the same pin.

MOE lookup reads the original ODS headword, alternate/contraction/colloquial reading,
dialect, word-comparison, name, surname, variant-character, and definition sheets.
Results retain original headwords/readings and cite the snapshot, sheet, and row.
Numeric MOE headword IDs are preserved from ODS cell values. MOE hits are review
evidence, not a prohibition on a community spelling recommendation.

## Check and add

Create a temporary JSON request outside the tracked tree. For a lookup, the minimum
is:

```json
{
  "preferred_form": "beh",
  "canonical_tl": "beh"
}
```

```sh
python3 tools/lexicon.py check /path/to/request.json
```

The JSON result reports potential matches in current entries, the entire LKK list,
and the pinned MOE dictionary. Inspect sense/etymology and reading before deciding.
It does not prove identity or absence of a word. Related dictionary spellings can
be supplied in `moe_forms`; alternate input readings in `alternate_readings`.
Use optional `hanji_forms` for source-backed or explicitly curated Hanji forms
without asserting MOE inclusion. These forms are included in existing-entry,
LKK and MOE checks; same-form matches still require editorial identity review.
Hanji metadata does not generate CSV output rows. Omit it when unknown.

Before adding, include `sources` with original evidence, as documented in
`schema/README.md`. Do not supply an ID. Optional prose fields are accepted;
otherwise array fields default to empty and status defaults to `imported`.

For a preferred spelling inferred solely from writing rules, include
`"rule_generated": true` in the JSON request. This optional boolean is preserved
as `rule_generated = true` in TOML. Ordinary source-backed or curated entries
can omit it. Original sources remain required: a dictionary can support the
word and reading without supporting the generated spelling. Remove the flag or
set it to `false` when the recommendation is explicitly adopted or corroborated.
The flag does not change review status, duplicate checks or CSV export inclusion.

```sh
python3 tools/lexicon.py add /path/to/request.json
python3 tools/lexicon.py validate
python3 tools/lexicon.py format --check
```

`add` repeats the full offline checks, blocks an existing form/reading or alias pair
unless an explicit distinct-word `identity_note` is provided, reserves the next ID,
and writes the sorted TOML file. Repeating the same identity note also blocks a
duplicate. Unicode input is normalized to NFC. No raw source cells are copied.

## Existing entries and IDs

```sh
python3 tools/lexicon.py next-id
python3 tools/lexicon.py format
python3 tools/lexicon.py validate
```

`next-id` only previews. `format` retains IDs, sorts keys and set-like arrays, and
renames/moves entries to the canonical path after deliberate spelling edits.
`validate` checks the full entry schema, source checksums and locators, ID uniqueness,
homograph distinctions, counter bounds, and canonical formatting/filing. It does
not infer whether a cited source supports an editorial choice.

Entry paths are `entries/<initial>/<prefix>/<preferred-form>--<id>.toml`. The
prefix uses the complete vowel sequence, excluding tones and final consonants:
`beh` files under `b/be/`, while `bu` and `bueh` use `b/bu/` and `b/bue/`.
See `schema/README.md` for zero-initial and syllabic-nasal cases. Readers scan
recursively, including entries awaiting migration from the older layout. Run
`format` to move them without changing IDs or canonical contents. New buckets
are created only when writing an entry, and empty old directories are removed
after moves.

The writer lock serializes local `add` and `format` operations. If a process crashes,
confirm it has stopped before removing `.lexicon.lock/`. The tracked counter must
never move backwards; failed writes may leave reserved gaps. Independently edited
clones require merge-time ID conflict resolution.

Repository validation needs only local source snapshots unless entries themselves
cite MOE. Candidate `check` and `add` always require the pinned MOE copy. All commands
accept `--root PATH` before the subcommand for another checkout or a test fixture.

## Build CSV

```sh
python3 tools/lexicon.py build-csv
python3 tools/lexicon.py build-csv --include-pure-hanji
```

The default command validates the repository and atomically writes
`dist/lexicon.csv`, excluding entries whose preferred forms are pure Hanji.
`--include-pure-hanji` writes `dist/lexicon-all.csv` with all entries instead,
leaving the default file untouched. Filtering uses `preferred_form`, independently
of Hanji metadata in `moe_forms` or `hanji_forms`. Punctuation, spaces and combining
marks do not make a pure-Hanji form mixed: `後--日` is excluded by default.
Both UTF-8 files have an exact `preferred_form,tl` header, LF line endings, and rows
sorted by written form and then reading using Unicode code-point order. Identical
rows are emitted once, including rows shared by unrelated homographs. The TOML
records, IDs, source snapshots, and allocation counter are unchanged.

Each included entry contributes its `preferred_form` with its `canonical_tl`.
For each `alternate_readings` value:

- If the preferred form contains only Hanji, retain that form for every reading.
  Punctuation, spaces, and combining marks are ignored for this classification,
  so `後--日` retains its written form for both `āu--ji̍t` and `āu--li̍t`.
- For fully romanized forms, use each alternate reading as its written output.
- For mixed forms, preserve Han characters and separators, and replace only the
  romanized syllables with the corresponding syllables of the alternate reading.
  Alignment requires one Han character or romanized syllable per reading syllable,
  with the written romanization matching the canonical reading. Contractions,
  mismatched spellings, or changed neutral-tone boundaries require explicit review;
  the build fails before replacing the CSV instead of guessing a spelling.

For example, `beh` with alternate `bueh` produces:

```csv
preferred_form,tl
beh,beh
bueh,bueh
```

A Hanji entry `欲` with readings `beh` and `bueh` produces `欲,beh` and `欲,bueh`
only in the inclusive export. A mixed entry `想beh` with readings `siūnn-beh` and
`siūnn-bueh` produces
`想beh,siūnn-beh` and `想bueh,siūnn-bueh`. Likewise, `beh食飯` with alternate
`bueh-tsiah-pn̄g` produces `bueh食飯,bueh-tsiah-pn̄g`. If only a Han-written
syllable changes pronunciation, its written form stays the same: `hip相` supports
both `hip-siòng` and `hip-siōng`.

These output spellings are generated by `spelling_readings(entry)`; alternate
readings stay in one editorial record, with the original ID and provenance.
`moe_forms` are evidence fields and do not generate output rows. All review statuses
are included; exporting does not mark entries reviewed. Tone marks, spaces, and
single/double hyphens are preserved.

`dist/` is ignored. A validation failure leaves an existing CSV untouched. The
build shares the maintenance writer lock to avoid racing with `add` or `format`.
MOE is fetched and verified only when required by source citations, using the
same pinned cache as validation.

The manual **Build CSV** GitHub Actions workflow runs tests and both commands,
then makes `lexicon.csv` and `lexicon-all.csv` available in the
`hanlo-lexicon-csv` run artifact. It can be run from the repository's Actions tab.
Local builds need no GitHub account
or remote. JSON exports remain unimplemented.

## CSV releases

The **Release CSV** workflow runs on pushes of tags matching `v*`. It tests the
maintenance tools, checks formatting, validates the data, and builds both CSVs
with the local commands. It packages `lexicon.csv`, `lexicon-all.csv`, `RIGHTS.md`,
and `SHA256SUMS` covering both CSVs and the rights file, then creates a draft
release with those assets before publishing it. Tags with a
hyphen, such as `v0.1.0-rc.1`, become prereleases. Existing releases are never
overwritten; a failed publish can leave a draft for the maintainer to inspect.

To release a published commit while using Jujutsu, create a tag through the GitHub
API (replace the version and full commit SHA):

```sh
gh api --method POST repos/madmaxieee/hanlo-lexicon/git/refs \
  -f ref=refs/tags/v0.1.0 -f sha=FULL_COMMIT_SHA
```

Creating the tag with your authenticated GitHub account triggers the workflow.
Use a new version for each release. Publish the commit to `main` with `jj git push`
before tagging it. The workflow checks out the tagged commit, never a moving
branch head. Source reuse notices remain part of every release; exporting does
not change review statuses or establish a new license.

For a dry run, select **Release CSV → Run workflow** on `main` and leave `publish`
unchecked. This runs the complete build and uploads a run artifact without a tag
or release. To publish an existing tag manually, dispatch on that tag with
`publish=true` (for example, `gh workflow run release-csv.yml --ref v0.1.0 -f
publish=true`). This also supports tags created by another workflow whose default
GitHub token does not trigger a new workflow run.

Download the assets from the repository's Releases page and verify them in the
same directory with `sha256sum --check SHA256SUMS` (macOS: `shasum -a 256 --check
SHA256SUMS`). The CSV's contents and review-status policy are described above.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

Tests use small temporary ODS/TSV fixtures and cover duplicate/alias behavior,
homographs, source verification, ID allocation, concurrency, formatting, Unicode,
and the CSV output rules above.

## TSBP discovery and custom review

The reusable issue harvester, standalone review UI and approval importer live in
`tools/tsbp/`. See [the TSBP workflow](tsbp/README.md) for output-folder commands,
structured custom requests and tests. Generated corpus data, review exports and
local browser decisions remain outside the repository.
