# Han-Lo Lexicon

A community-curated collection of Taiwanese Han-Lo writing recommendations,
starting from the [LKK word list](sources/lkk-2024-05-10/word-list.tsv).
Editable vocabulary records preserve stable identities, verified readings, and
original evidence. CSV exports provide input/output mappings for TaigiKeyboard.

## Find the right document

- [Glossary](GLOSSARY.md): shared language for words, writing, evidence, and review.
- [Entry schema](schema/README.md): fields, source references, identity, and filing.
- [Maintenance guide](tools/README.md): lookup, editing, exports, and discovery commands.
- [Editorial decisions](decisions/README.md): standing decisions and historical import records.
- [Source rights](RIGHTS.md): reuse terms and distribution constraints.

## Maintain vocabulary

Use the [maintain-lexicon skill](.agents/skills/maintain-lexicon/SKILL.md) for entry
additions, corrections, homographs, and related-word review. It connects offline
LKK/MOE checks, evidence review, ID allocation, and validation. MOE's exact pinned
snapshot is downloaded on first use; later lookups work offline.

For corpus work, choose the workflow by writing system:

- [TSBP Roman and mixed-script review](.agents/skills/review-tsbp-roman/SKILL.md)
  covers harvesting, language screening, review exports, and authorized imports.
- [Pure-Hanji review](.agents/skills/review-hanji/SKILL.md) screens harvested
  candidates in context. Start with [discovery commands](tools/hanji-discovery.md)
  when no harvest exists.

## Build and check

With `just` installed, run `just` to list recipes. Common commands are:

```sh
just export       # Default TaigiKeyboard CSV, including alternate readings
just export-all   # Every CSV variant, including canonical and contractions only
just check        # Validate, check formatting, and run maintenance tests
```

Without `just`, use the Python commands in the [maintenance guide](tools/README.md).
See [CSV exports and releases](tools/csv.md) for headers, canonical-and-contractions exports,
alternate-spelling behavior, and GitHub build artifacts.

## Repository layout

- `entries/`: editable vocabulary TOML, filed by canonical TL initial and vowel prefix.
- `sources/` and `references/`: original snapshots, metadata, and dictionary pins.
- `schema/` and `decisions/`: record conventions and editorial decisions.
- `tools/` and `tests/`: maintenance commands, corpus tools, and their tests.
- `.agents/skills/`: project-specific editorial and jj workspace workflows.
- `docs/agents/`: engineering-skill configuration and documentation reading rules.
- `.github/workflows/`: CSV builds and tagged releases.

Generated caches and `dist/` are disposable local artifacts. TOML records remain
the editable source. See [agent instructions](AGENTS.md) before making changes.
