# Entry maintenance

[Maintenance guide](README.md) · [Terminology](../GLOSSARY.md)

Run commands from the repository root.

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

`check`, `add`, and per-request `add-batch` reports also expose
`related_moe_entries` as pre-import audit data. They do not authorize or import
related words. After the authorized import and conflict resolutions, follow the
[related-word editorial procedure](../.agents/skills/maintain-lexicon/SKILL.md#standalone-related-word-review)
to generate current recommendations. See the
[related-word reference](related-words.md) for matching and report mechanics.

Before adding, include `sources` with original evidence, as documented in
[entry schema](../schema/README.md). Do not supply an ID. Optional prose fields are accepted;
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

## Existing entries and IDs

```sh
python3 tools/lexicon.py next-id
python3 tools/lexicon.py format
python3 tools/lexicon.py validate
```

`next-id` only previews. `format` retains IDs, sorts keys and set-like arrays, and
renames/moves entries to the canonical path after deliberate spelling edits.
It skips writes when an entry is already at its canonical path with exactly the
canonical bytes. Full validation still runs before and after formatting. Source
row lookups are rebuilt within each validation pass from freshly loaded,
checksum-verified dictionaries; they are never saved or reused between passes.
`validate` checks the full entry schema, source checksums and locators, ID uniqueness,
homograph distinctions, counter bounds, and canonical formatting/filing. It does
not infer whether a cited source supports an editorial choice.

Entry paths are `entries/<initial>/<prefix>/<preferred-form>--<id>.toml`. The
prefix uses the complete vowel sequence, excluding tones and final consonants:
`beh` files under `b/be/`, while `bu` and `bueh` use `b/bu/` and `b/bue/`.
See [entry schema](../schema/README.md) for zero-initial and syllabic-nasal cases. Readers scan
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
