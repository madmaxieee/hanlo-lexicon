# Dictionary and entry lookup

[Maintenance guide](README.md) · [Terminology](../GLOSSARY.md)

Run commands from the repository root.

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

Dictionary lookups also maintain `decoded-v1.json` beside the original ODS.
This disposable, compact UTF-8 JSON cache retains all decoded sheets, original
row numbers, lookup records and provenance. Every lookup still verifies the
original ODS checksum. Changes to the pin, cache version or maintenance
implementation invalidate the decoded cache; a payload checksum and shape checks
detect damaged cache data. Missing, stale or corrupt decoded data is rebuilt
from the verified ODS and saved atomically. If decoded cache storage is unavailable,
lookups use the original decoder. Deleting this JSON file is always safe.
The cache adds no dependencies and is never a source citation.

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
