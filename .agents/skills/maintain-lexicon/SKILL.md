---
name: maintain-lexicon
description: Add or maintain Han-Lo vocabulary entries in this repository using offline LKK and MOE duplicate checks, stable integer IDs, and deterministic TOML formatting. Use for entry additions, spelling corrections, homograph handling, and repository data validation.
---

# Maintain the Han-Lo lexicon

Work from the repository root. Read [entry conventions](../../../schema/README.md)
and [maintenance commands](../../../tools/README.md) before changing data.
Use `python3 tools/lexicon.py`; do not invent an ID or hand-format generated TOML.

## Add a requested word

1. Establish the requested written form, a verified canonical TL reading, and
   whether the candidate is an existing lexeme or a distinct word (using offline
   dictionary lookups rather than guessing readings, converting POJ, or using
   Mandarin text as Taiwanese).
2. Write a temporary JSON request with `preferred_form`, `canonical_tl`, and any
   known `alternate_readings` or `moe_forms`. Run `check REQUEST.json` to check
   existing entries, LKK, and the pinned MOE ODS (populating the ignored cache on
   first use and stopping on download or checksum errors).
3. Inspect matches by sense, etymology, and reading (`query <text> --moe` shows
   MOE senses and examples). Treat shared spelling or reading as review evidence
   rather than proof of identity; keep check-time `related_moe_entries` as
   pre-import audit data and handle related words separately after import.
4. For an existing word, edit the existing entry. For an unrelated homograph,
   add a distinct `identity_note` (keep related senses and alternate readings
   in one entry). Add non-preferred valid output spellings to `accepted_forms`.
   Ask for context if lexical identity remains unclear.
5. Cite original evidence in `sources` (an LKK snapshot/row, checked MOE
   snapshot/sheet/row, or published HTTP(S) URL + `locator`), preserving source
   wording without inventing meanings, examples, or extra fields.
6. Run `add REQUEST.json` to recheck under the writer lock, allocate the next ID,
   and write the canonical TOML. Leave unreviewed additions as `imported`; use
   `machine-reviewed` after contextual model screening (recording model, scope,
   and evidence in `editorial_rationale` and `sources`), and reserve `reviewed`
   for explicit human review.
7. Run `validate` and `format --check`. Report the resulting file/ID, relevant
   dictionary matches, and any open editorial questions; keep the repository local
   unless asked to publish.

## Standalone related-word review

For standalone discovery or post-import related-word review, read
[related-word-review.md](references/related-word-review.md) and
[related-words.md](../../../tools/related-words.md).

## Import conflicts require maintainer review

When an import candidate overlaps an existing entry or hits a surname-appendix
or same-reading case, read [import-conflicts.md](references/import-conflicts.md).

## Corrections and IDs

Preserve IDs on spelling or reading edits. After manual edits, run `format`
(which sorts keys/sets and renames/moves files from preferred form and canonical
TL) and then `validate`. Cite evidence for added facts and omit unknown optional
fields.

`next-id` previews only; `add` owns allocation through `id-sequence.toml` and
keeps reserved/deleted IDs monotonic without recycling. Resolve cross-clone ID
collisions before merging without renumbering published entries.

MOE data lives in ignored `.cache/dictionaries/moe/<sha256>/kautian.ods`,
pinned in `references/moe.toml`. Keep the pin verified; on an explicit refresh,
inspect the new edition and terms before updating the pin.
