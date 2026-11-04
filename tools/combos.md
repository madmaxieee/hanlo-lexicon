# Han-Lo combo inventory

[Maintenance guide](README.md) · [Terminology](../GLOSSARY.md)

Run commands from the repository root.

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
suite above. This command produces inventory/reporting only. For related-word suggestions,
see [related-word review](related-words.md); for corpus candidates, see
[pure-Hanji discovery](hanji-discovery.md). Whole-word recommendations take
precedence over component suggestions.
