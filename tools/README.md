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

## Existing-entry queries and SQLite index

```sh
python3 tools/lexicon.py query 'mí-sooh'
python3 tools/lexicon.py query --id 689
python3 tools/lexicon.py query 'mí-sooh' --no-cache
```

`query` returns complete existing entry records and their TOML paths. Text matches
preferred, MOE or Hanji forms, canonical TL and alternate readings exactly after
NFC/case/whitespace normalization. Tones and single/double hyphens stay distinct;
homographs remain separate records. Query by text or by ID, not both. This is an
entry-only query: it needs no dictionary download and does not replace the full
offline `check` required before import.

The disposable SQLite index lives at `.cache/entries.sqlite3`, separately in each
workspace. TOML remains authoritative. Every cached query discovers the current
entry files and checks size, nanosecond mtime/ctime, device and inode. New or changed
files are parsed and schema-validated; deleted and renamed paths are removed.
The index retains normalized lookup keys, IDs, full entry fields and provenance.
Changes to the schema, maintenance implementation or workspace root invalidate
the index. A first query builds it; later queries parse only changed files.

`check` uses this index for its existing-entry portion and still performs the
original LKK and checksum-pinned MOE checks. Full `validate`, `format`, and import
preflight read entry TOML directly, independently of the SQLite index. A corrupt,
locked or unavailable database falls back to the authoritative TOML reader; delete
the database to rebuild it. `query --no-cache` bypasses it explicitly. The cache
never allocates IDs, modifies entries, or becomes a source citation.

Both the TSBP and pure-Hanji harvesters use `entry_snapshot` to load all entry
fields and original-byte SHA-256 hashes through this same cache. Warm snapshots
parse only changed TOML files; report fingerprints and source references retain
the exact original hashes. Existing v1 databases are upgraded automatically.
The pure-Hanji harvester compares a second snapshot before publishing, rejecting
changed, added, removed or renamed entry files. Import previews reuse the snapshot
and one in-memory dictionary index; the final writer still validates TOML directly.

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

Checks also return `related_moe_entries` for human-review import suggestions.
The search requires exact shared Hanji/TL combos, never Hanji alone or
pronunciation similarity: two Hanji AB
match XAB, ABX, XYAB and ABXY; three Hanji ABC match AB, BC, XABC and ABCX.
Seeds come from supplied `preferred_form`, `moe_forms` or `hanji_forms`, including
verified MOE variants, or an explicitly cited MOE reading/headword row. A
reading-only dictionary hit does not supply Hanji. Every shared glyph and its
aligned syllable must agree, including tones and neutral markers. Compare each
canonical or explicitly recorded alternate reading as a complete sequence; do
not mix syllables across alternatives. For example, 中ng / tiong-ng does not
match 中央公園 / Tiong-iong Kong-hn̂g because 央/ng differs from 央/iong.
Mixed/romanized requests need
supplied Hanji or that explicit MOE source selection. Only literal contiguous
Hanji count; glyph variation selectors stay attached to their character. Explicit
MOE annotations are ignored for matching and retained in the original evidence.

Suggestions cover numbered `詞目` entries and their recorded variant forms,
without comparison/name/surname-sheet duplicates. Each retains its MOE identity,
original headword, reading, definitions and source row, plus `relations` naming
the `base_form`, `matched_form`, `pattern` and original `combo_matches` proofs.
Only reading choices that satisfy a shared combo match are offered for spelling
proposals and import review. Unalignable/contraction readings cannot establish
a match. Homographs remain separate and
results follow dictionary order. The requested word is omitted; suggestions do
not recursively seed more suggestions. Shapes alone do not establish semantic
relationship. `check`, `add` and per-request `add-batch` reports expose the same
suggestions, independently of review status. Present them when importing
human-reviewed entries; they require their own review and import authorization.
They never affect duplicate checks, allocate IDs, change review status, or enter
entry TOML as metadata.

For a longer related entry, `writing_suggestions` applies the existing combo
inventory to each sourced reading separately. Tone and neutral-boundary keys
remain exact. Every position includes Hanji, TL and all supported outputs with
supporting entry IDs, preferred forms, readings, original sources and review
status. Generated and disputed entries do not supply writing recommendations;
other statuses retain their actual labels. One supported output per position
produces a `consistent` complete spelling. Multiple outputs produce `conflicting`,
with evidence for every Hanji and romanized alternative and no majority choice.
Unknown positions produce `incomplete`; contractions/unsupported alignments are
`unalignable`. Neither gets an invented fallback spelling. Shorter related words
have reading choices but no longer-word writing proposals. Every related word
requires individual human review, including consistent spelling suggestions.
Batch checks use one combo snapshot from existing entries before the batch;
unwritten requests do not become evidence for later requests.

Before adding, include `sources` with original evidence, as documented in
`schema/README.md`. Do not supply an ID. Optional prose fields are accepted;
otherwise array fields default to empty and status defaults to `imported`.

For entries screened by a model against source context, explicitly include
`"review_status": "machine-reviewed"`. Record the model, review scope and evidence
in `editorial_rationale` and `sources`. Mechanical import or validation alone
leaves the status `imported`; reserve `reviewed` for explicit human review.
Authorizing a batch import does not imply individual human review. Review status
is preserved as provenance and does not change CSV inclusion or `rule_generated`.

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

## Standalone related-entry discovery and human review

Related discovery accepts a Hanji seed independently of import requests. Resolve
its readings from matching existing entries, or from the exact original MOE form
only when no existing seed entry is recorded. Missing/unalignable seed readings
do not permit a glyph-only fallback:

```sh
python3 tools/lexicon.py related 火車 \
  --out /path/to/fire-train.review.json \
  --markdown /path/to/fire-train.review.md
# Multiple seeds are allowed; related identities and relations are deduplicated.
python3 tools/lexicon.py related 火車 火車頭
# Restrict the source reading and identity to an existing entry.
python3 tools/lexicon.py related 中央 --entry-id 629
```

The JSON report contains original MOE evidence, all sourced reading choices,
combo writing suggestions for longer matches, existing-entry identity candidates,
matching seed-entry identities and shared Hanji/TL evidence,
and one `review` object per related entry. The optional Markdown report presents
the same evidence for a human to inspect, with distinct supporting-entry counts
for Hanji and romanization and at most three example preferred spellings per side.
The complete evidence remains in JSON. The new-only review index omits related
words with existing-entry candidates (shared recorded Hanji form or MOE source
identity) and shows the existing seed entries' preferred forms separately from
the proposed form of the new word. Such a candidate is an identity-review lead,
not proof of a duplicate. Output files must be outside the
repository or under ignored `.cache/related-moe/`. Discovery only reads entries;
it does not allocate IDs, approve words, or import entries.

Every `review.decision` starts as `pending`. After a human individually reviews
that word, edit only its `review` object, for example:

```json
{
  "decision": "approved",
  "preferred_form": "火車站",
  "canonical_tl": "hué-tshia-tsām",
  "alternate_readings": [],
  "identity_note": "",
  "editorial_rationale": ""
}
```

Use `rejected` to decline a word or retain `pending` for later review. Approval
must explicitly select the preferred spelling, canonical reading and any
alternates, including choices for conflicts and unknown positions. There is no
approve-all operation or automatic acceptance of consistent proposals. Readings
must belong to that same original MOE identity; alternate, colloquial, contracted
and dialect sources remain available. Human choices can adopt a different
spelling from a generated proposal. An existing-entry overlap needs explicit
identity resolution; this importer never updates or silently dismisses it.

```sh
python3 tools/lexicon.py import-related /path/to/fire-train.review.json
python3 tools/lexicon.py import-related /path/to/fire-train.review.json --apply
```

The first command previews, allocating nothing. `--apply` submits only individual
`approved` decisions to the ordinary batch writer, with `review_status: reviewed`
and original MOE citations. Human-adopted recommendations omit `rule_generated`.
Pending and rejected suggestions are excluded. The related word is dictionary
evidence, so the seed word's corpus context is not copied as an occurrence of the
longer word. Optional human rationale is preserved without inventing an explanation.
The writer repeats normal source/duplicate/ID checks and validates after import.

The report seals dictionary identity, source evidence, combo support, entry state
and seed-entry scope separately from editable human decisions. Changed evidence, entry data,
dictionary pins or implementation require regeneration and review of the updated
report. The writer rechecks the entry/dictionary state under its lock before any
IDs are reserved. After importing part of a report, regenerate for remaining
suggestions because the current entry/consistency evidence has changed.

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

## Batch imports

Put ordinary add requests in a nonempty JSON array, without IDs:

```json
[
  {
    "preferred_form": "a-lú-mih",
    "canonical_tl": "a-lú-mih",
    "sources": [{"snapshot": "moe-kautian-3e0b2023e0bd", "sheet": "詞目", "row": 24238}]
  }
]
```

```sh
python3 tools/lexicon.py add-batch /path/to/requests.json --dry-run
python3 tools/lexicon.py add-batch /path/to/requests.json
python3 tools/lexicon.py validate
python3 tools/lexicon.py format --check
```

The batch acquires one writer lock, reads and validates the existing TOML once,
and loads/checksums the original LKK and MOE inputs once. In-memory form/reading
indexes avoid scanning every dictionary record for every candidate. Every request
keeps the ordinary schema, source, duplicate and homograph checks, including
matches against earlier requests in the same batch. The result includes the usual
per-entry `checks` reports in request order. `add` uses this same path for one word
and retains its existing output shape.

The complete batch is checked before any IDs are reserved or entries are written.
Invalid requests and unresolved existing/intra-batch duplicates abort the batch;
there is no implicit skip, merge, spelling change or keep-existing decision. Resolve
identity conflicts explicitly before submitting the final batch. Status defaults
to `imported`, exactly as for ordinary adds.

`--dry-run` shows prospective paths, IDs and reports without reserving IDs or
writing entries. Those IDs are previews and may change before a later import.
It can populate the ignored original dictionary cache on first use. A real import
reserves the entire ID range once, then writes each canonical TOML atomically. A
disk failure can leave a partial import; the entire range stays reserved and gaps
must not be recycled. Inspect the entry files before retrying remaining requests.
This is full-batch preflight, not a filesystem transaction or rollback promise.

Local measurements on 2026-10-22 used scratch copies with 3,072 existing entries
and the already-downloaded pinned MOE source. Ten ordinary adds with the previous
tool took 91.1 seconds; the same ten requests took 6.2 seconds in one batch. The
complete 152-request loanword batch took 5.5 seconds. On the resulting 3,224-entry
checkout, median entry-query time across five fresh CLI processes was 0.65 seconds
for direct TOML reads and 0.16 seconds with a warm SQLite index. Setup/copy time
and network download were excluded; timings depend on the machine and cache state.

## Build CSV

```sh
python3 tools/lexicon.py build-csv
python3 tools/lexicon.py build-csv --include-pure-hanji
python3 tools/lexicon.py build-csv --canonical-only
python3 tools/lexicon.py build-csv --include-pure-hanji --canonical-only
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

Use `--canonical-only` to export only each included entry's `preferred_form` with
its `canonical_tl`, without generating any alternate-reading rows. It writes
`dist/lexicon-canonical.csv`, or `dist/lexicon-all-canonical.csv` when combined with
`--include-pure-hanji`, leaving the regular exports untouched. Sorting,
deduplication, source validation, and the pure-Hanji filter work the same way.
Alternate readings remain in the TOML records. Canonical-only builds do not try
to align alternate spellings, so an unalignable alternate does not block them.

Each included entry contributes its `preferred_form` with its `canonical_tl`.
Unless `--canonical-only` is set, each `alternate_readings` value also contributes:

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

## Han-Lo combo inventory

Build a read-only inventory from current entry TOML:

```sh
python3 tools/hanlo_combos.py
# For another checkout:
python3 tools/hanlo_combos.py --root /path/to/workspace
```

The command writes ignored local `.cache/hanlo-combos/inventory.json` and
`.cache/hanlo-combos/report.md`, then prints paths, counts, fingerprint and cache
hit status as JSON. No dictionary download, entry edit, allocation, approval or
import occurs. It uses the recursive maintenance reader and validates entry
structure; it does not independently verify whether citations support a spelling.
Use the ordinary `validate` command for repository/source validation.

A combo is a literal Hanji glyph paired with one canonical TL syllable. Tones
and neutral prefixes (`ê` versus `--ê`) stay distinct. Each complete reference
form must align one Hanji per canonical syllable; the preferred form must align
one Hanji or matching Roman syllable per canonical syllable. Implicit separators
next to Hanji are allowed; explicit neutral boundaries must agree. Unsupported
punctuation, iteration marks, count mismatches (including contractions), and
mismatched Roman syllables are audited rather than guessed. Glyph variation
selectors are retained. Only canonical readings contribute; alternate readings
and dictionary variants are not expanded automatically. Pure-Hanji preferred
forms contribute directly, including when they have no separate Hanji metadata.

The JSON records actual output tokens, supporting entry IDs, observed entry IDs,
entry paths, original source references, review status, identity notes and
editorial/usage notes. A
Hanji reference glyph can map to a different preferred Hanji glyph. Multiple
outputs are conflicts even when all outputs are Hanji. Repeated positions or
reference forms in one entry contribute once per combo/output. Conflicts retain
all supporting words and counts; no majority or minimum-support policy is applied.
Entries marked `rule_generated = true` can expose observed combos but never
contribute recommendation votes. See [entry semantics](../schema/README.md).

`unknown` means that an observed, safely aligned combo has no eligible preferred
output (for example, only generated evidence or an unalignable preferred form).
It does **not** enumerate every unobserved Hanji/reading pair in MOE. Roman-only
entries without Hanji metadata are listed as lacking aligned Hanji positions.
Consistency is distinct from support: one agreeing entry remains one observation,
and `imported` or `machine-reviewed` status is retained without implying human review.

The Markdown report includes all conflicts, unknown and consistent combos, a
skip audit, and provenance. Each combo has its own section with outputs followed
by one supporting word per line. Entry editorial notes appear beside the evidence;
long supporting-word lists and citations are not squeezed into table columns. It is regenerated on every invocation. The
inventory cache is invalidated by all entry contents and paths, the schema,
alignment/maintenance implementation, and an explicit derivation version. Entry
additions, deletions, source changes and generated flags therefore invalidate it.
Maintenance writers share a lock; a detected input change aborts publication.
Generated output stays ignored and entry TOML remains authoritative.

Focused tests are in `tests/test_hanlo_combos.py` and run with the maintenance
suite above. This implements inventory/reporting only. Provisional MOE review
suggestions and the pure-Hanji corpus discovery/review queue remain later phases;
whole-word recommendations must take precedence when suggestions are integrated.

## TSBP discovery and custom review

The reusable issue harvester, standalone review UI and approval importer live in
`tools/tsbp/`. See [the TSBP workflow](tsbp/README.md) for output-folder commands,
structured custom requests and tests. Generated corpus data, review exports and
local browser decisions remain outside the repository.

## Pure-Hanji corpus discovery

`harvest_hanji.py` makes a read-only report using the same checksum-pinned MOE
loader. It does not approve/import entries, change review statuses, or add corpus
observations to the recommendation inventory. It needs no converter or third-party
Python packages. Write reports outside the repository or in its ignored `.cache/`:

```sh
python3 tools/harvest_hanji.py \
  --corpus /path/to/tsbp.jsonl --issue 390 \
  --out .cache/hanji-harvest/tsbp-390
python3 tools/harvest_hanji.py \
  --corpus /path/to/corpus.jsonl --out /path/to/hanji-report
python3 tools/harvest_hanji.py \
  --corpus /path/to/article.txt --format text --out /path/to/hanji-report
```

The default input is UTF-8 JSONL with one object per line: required nonempty string
`id` and string `text`, and optional `metadata` containing `title`, `original_url`,
and string-array `tags`. Text-only corpus exports with `{id, text}` also work.
IDs must be unique within the selected documents. Text is never normalized or
rewritten; offsets count Unicode code points in the exact decoded `text`,
including supplementary Han characters, combining marks, and CR/LF. The corpus
file SHA-256 covers the entire input, including unselected records.

With no filters, all documents are processed. Repeat `--tag TAG` to require all
specified tags. `--issue N` additionally requires the exact `issue:N` tag and
omits TSBP catalog titles of the form `台文通訊BONG報 N 期`. These filters require
JSONL. `--radius N` controls literal context length (default 12 code points on each
side, extended to avoid splitting combining marks). `--lexicon PATH` selects an
entry/reference root; it defaults to this repository. `--exclude-contexts FILE`
accepts a JSON array of exact, case-sensitive literal phrases, omitting every match
that intersects one. Exclusions do not join text or create new word boundaries.

### Matching and uncertainty

- A trie finds all literal, contiguous canonical Hanji headwords from numbered
  MOE `詞目` records. Single characters, nested compounds, and crossing overlaps
  remain in the output. Alternate Hanji spellings, names/surnames, and comparison
  rows do not create candidates. An unmatched character is never assigned a
  reading by inference. Romanization, punctuation, and spaces are not traversed.
- Each candidate retains its distinct MOE identity, definitions for review, original
  sheet/row/column references, main readings in source order, and supported alternate,
  colloquial, contracted, and dialect readings. The first main reading supplies a
  canonical filing proposal; it does not establish the article's intended reading.
- Connected overlapping spans form groups. For each character position, the report
  compares **every covering dictionary identity and reading**. Agreement requires
  the same character and tone-preserving reading, including neutral `--` markers.
  A contraction or other unalignable alternative blocks positional agreement.
  This avoids enumerating possible segmentations; it deliberately favors caution
  over excluding interpretations using linguistic context.
- Agreement is **conditional dictionary evidence**. Unknown words remain possible
  even if every source character has dictionary coverage. The report never claims
  that a substring is an independently attested word or that a Han run has a certain
  segmentation. It also does not determine whether a source passage is Taiwanese;
  select the intended corpus/subset before accepting its evidence.

The current recommendation inventory uses only canonical TL, aligns each recorded
`moe_forms` / `hanji_forms` spelling with the preferred writing, and counts each entry
once per combo/output. A contiguous pure-Hanji preferred form can supply its own
Hanji alignment. Contractions and uncertain alignments are skipped with reasons.
Entries marked `rule_generated = true` or `disputed` do not supply recommendations;
`imported` and `machine-reviewed` are not reinterpreted as human review. Conflicting
recommendations retain all supporting entry IDs. Corpus observations never resolve
these conflicts.

### Outputs and review queues

| File | Contents |
| --- | --- |
| `report.md` | Top 50 candidates per review queue and unknown combos with conditional agreement |
| `candidates.json` | Matched MOE identities, readings, counts, reasons, existing-entry candidates, and up to three distinct-text contexts |
| `occurrences.jsonl` | Every literal match, source/context offsets, article link, group ID, and candidate identities |
| `overlap-groups.jsonl` | Isolated, same-span, containment, or crossing groups and position-level alternatives/agreement |
| `combo-inventory.json` | Existing recommendations with supporting entry IDs, conflicts, and skipped alignments |
| `combo-coverage.json` | Conditionally agreeing observed combos, corpus support, and comparison with the existing inventory |
| `summary.json` | Counts, selected article inventory, options/exclusions, corpus/dictionary/tool/entry fingerprints, and policy |

Candidates are ordered by the number of **new conditionally supported combos**,
then distinct text bodies and occurrences. `potential_new_combos` also lists
unknown combos from dictionary readings that may still be ambiguous; these do
not count toward `new_combo_count`. Whole-word readings stay separate from the
position-level inventory evidence.

- `batch_proposal`: at least one match spans an entire contiguous Han run, one MOE
  identity/reading, alignable combos, dictionary agreement at every occurrence,
  no crossing overlap group, and no existing-entry or recommendation conflict.
  Han-run boundaries are structural clues, not proof. This queue still needs
  explicit batch review and the ordinary maintenance checks before any import.
- `agreement_only`: some character/reading evidence agrees, while a whole-word
  proposal remains uncertain. Keep the evidence local rather than import a word
  from a substring match.
- `focused_review`: no usable positional agreement, or a recommendation conflict
  or existing-entry candidate requiring editorial identity review.

Counts describe the selected corpus, not general usage frequency. Raw occurrences
and distinct document IDs are reported separately from distinct text bodies.
Exact duplicate bodies contribute once at each text offset to distinct-text counts;
paraphrases and near-duplicates are not deduplicated. Overlapping matches cannot
multiply a character-position's combo support. Frequency does not choose a
segmentation or reading. Output is deterministic for identical inputs; invalid
input fails before replacing an existing report, and completed files are replaced
atomically one at a time. The corpus, entry data, and original snapshots are unchanged.

Run the behavioral fixture tests with the ordinary maintenance suite:

```sh
python3 -m unittest discover -s tests -v
```

For a contextual quick pass on the complete `batch_proposal` and `agreement_only`
queues, use the project-local [review-hanji skill](../.agents/skills/review-hanji/SKILL.md).
`tools/review_hanji.py prepare --harvest PATH --out PATH` creates sealed review
packets with wider literal contexts and source-line language labels. Lightweight
subagents return recommendations, combo-only evidence, holds, or rejections.
`tools/review_hanji.py collect --run PATH` verifies input freshness, exact candidate
coverage and cited evidence, then writes `review.json` and `review.md`. The quick
pass may relax Han-run boundaries and ignore irrelevant component readings when
context supports a compound. It never imports entries or marks them human-reviewed.
When an import is subsequently authorized, use `machine-reviewed` for its
contextually screened recommendations and retain model and source provenance.
