# Maintenance commands

Run from the repository root with Python 3.11 or newer. The Python maintenance
tool has no third-party dependencies. See the [glossary](../GLOSSARY.md) for
terminology and the [entry schema](../schema/README.md) for record conventions.

For vocabulary changes, follow the [maintain-lexicon skill](../.agents/skills/maintain-lexicon/SKILL.md).
This guide indexes command reference; the skill owns the editorial workflow.

## Dictionary cache

Populate and verify the checksum-pinned MOE source and disposable decoded cache.
See the [command reference](dictionaries.md#dictionary-cache).

## Existing-entry queries and SQLite index

Find current records by text or stable ID and understand the disposable entry index.
See the [command reference](dictionaries.md#existing-entry-queries-and-sqlite-index).

## Check and add

Prepare a request, inspect offline duplicate evidence, and add an authorized entry.
See the [command reference](entries.md#check-and-add).

## Standalone related-entry discovery and human review

Generate fresh related-word evidence and import separately authorized decisions.
See the [command reference](related-words.md#standalone-related-entry-discovery-and-human-review).

## Existing entries and IDs

Correct and format records while preserving stable IDs.
See the [command reference](entries.md#existing-entries-and-ids).

## Batch imports

Preflight a complete batch, allocate IDs, and handle interrupted writes.
See the [command reference](entries.md#batch-imports).

## Build CSV

Export default and canonical-and-contractions CSVs with alternate-reading rules.
See the [command reference](csv.md#build-csv).

## CSV releases

Build artifacts and explicitly publish tagged releases.
See the [command reference](csv.md#csv-releases).

## Tests

```sh
python3 -m unittest discover -s tests -v
```

Tests use small temporary ODS/TSV fixtures and cover duplicate/alias behavior,
homographs, source verification, ID allocation, concurrency, formatting, Unicode,
and the CSV output rules above.

## Han-Lo combo inventory

Inspect component outputs, conflicts, unknowns, and evidence without editing entries.
See the [command reference](combos.md#han-lo-combo-inventory).

## TSBP discovery and custom review

The reusable issue harvester, standalone review UI and approval importer live in
`tools/tsbp/`. See [the TSBP workflow](tsbp/README.md) for output-folder commands,
structured custom requests and tests. Generated corpus data, review exports and
local browser decisions remain outside the repository.

## Pure-Hanji corpus discovery

Harvest literal matches and inspect overlap, conditional agreement, and review queues.
See the [command reference](hanji-discovery.md#pure-hanji-corpus-discovery).
