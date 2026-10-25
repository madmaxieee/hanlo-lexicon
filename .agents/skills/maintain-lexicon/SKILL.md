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
   whether it is an existing lexeme or a distinct word. Search offline; do not
   guess a reading, convert POJ into TL, or use Mandarin text as a Taiwanese form.
2. Write a temporary JSON request with `preferred_form`, `canonical_tl`, and any
   known `alternate_readings` or `moe_forms`. Run `check REQUEST.json`. This checks
   existing entries, the full LKK snapshot, and the pinned original MOE ODS,
   including alternative/dialect readings and variant characters. On first use it
   downloads the pinned snapshot from TaigiKeyboard GitHub into the ignored cache.
   Download/checksum failures stop the operation; do not skip the MOE check.
3. Inspect matches by sense, etymology, and reading. The output includes MOE
   definitions and original snapshot/sheet/row references for review. A same-form
   or same-reading hit is not proof of lexical identity. MOE presence is useful
   evidence and does not prohibit an LKK writing recommendation.
   Treat check-time `related_moe_entries` as pre-import audit data. Complete
   the authorized import and resolve its conflicts first, then rerun the
   standalone related workflow against the current inventory, scoped to the
   imported entry IDs. Publish the new-only Markdown index with original MOE
   readings/definitions, matching patterns and source rows; do not copy stale
   per-request checks into the recommendation list. Existing-entry candidates
   and explicitly rejected words stay in JSON but are hidden from that index. Start from supplied Hanji
   (`preferred_form`, `moe_forms`, `hanji_forms`) or the explicitly cited MOE
   entry's Hanji, never by reading similarity or a homophone's Hanji. A relation
   requires every shared Hanji/TL combo to match exactly, including tone and
   neutral markers. Compare complete canonical or explicitly recorded alternate
   readings separately; never combine syllables across alternatives. Hanji-only
   overlap is insufficient: 中ng / tiong-ng cannot match 中央公園 /
   Tiong-iong Kong-hn̂g because 央/ng and 央/iong differ. Unalignable readings
   cannot prove a relation. For a
   two-Hanji form AB, suggest XAB, ABX, XYAB and ABXY; for three Hanji ABC,
   suggest AB, BC, XABC and ABCX. These are literal word-shape candidates, not
   claims of semantic relationship. Retain the matching current seed spelling
   at shared positions. For shorter AB/BC words, remove the extra aligned seed
   units; no new spelling decision is needed. For longer words, use the current
   combo inventory only for added positions. Repeated added combos can therefore
   reuse evidence from the freshly imported seed. Retain full inventory conflicts
   as audit evidence without reopening an adopted seed spelling. Unknown or
   conflicting added positions need human spelling decisions; never choose by
   majority. Keep canonical-headword proposals separate from dictionary-variant
   evidence so an unknown variant glyph does not demote the main spelling.
   Related entries normally require individual human review. The maintainer's
   standing exception permits batch-authorized consistent proposals to be
   screened against dictionary and combo evidence and imported as
   `machine-reviewed`, without claiming individual human review. Record the
   model/agent, scope and original evidence. Conflicting or incomplete added
   positions still need explicit resolution. Shorter words inherit their spelling
   but still need word-level adoption. The original entry's approval does not approve its
   related words. If the request has no verified Hanji, do not invent a seed.
4. For an existing word, edit the existing entry rather than creating another.
   For an unrelated homograph, supply a short `identity_note` explaining the
   distinction. Do not split a word merely because it has related senses or
   alternate pronunciations. If identity remains unclear, ask for the context
   needed to resolve it before adding.
5. Add original evidence to `sources`: cite an LKK snapshot/row, the checked MOE
   snapshot/sheet/row, or a published URL plus precise `locator`. Never cite a
   cleaned personal CSV as independent evidence or copy raw source cells into
   entries. Do not reintroduce removed meanings, example, or variant-spelling
   fields. Definitions shown during lookup remain external review evidence.
6. Run `add REQUEST.json`. It repeats the checks under a writer lock, allocates
   the next integer, and creates the canonical file. Default to `imported` for
   unreviewed records. After contextual model screening, explicitly request
   `review_status: "machine-reviewed"` and record the model, review scope, and
   evidence in `editorial_rationale` and `sources`. Mechanical checks alone do
   not qualify. Reserve `reviewed` for explicit human review; batch import
   authorization alone does not qualify as individual review. A request to add a
   word already authorizes this local addition; there is no separate blanket approval step.
7. Run `validate` and `format --check`. Report the resulting file/ID, relevant
   dictionary matches, and unresolved editorial issues. Keep the repository local
   and leave commit/publish actions to the user's instruction.

## Standalone related-word review

Related discovery is independently available through `tools/lexicon.py related
HANJI [HANJI ...] --out /path/to/review.json --markdown /path/to/review.md`.
No import request is required. Seed readings come from matching existing entries;
use `--entry-id ID` (repeatable) to restrict the source identities. Only when no
existing seed entry is recorded can the exact MOE seed form supply readings.
Do not substitute other dictionary readings for an unalignable existing entry.
Use only matched reading options and the recorded `combo_matches` proofs; the
existing-seed column must not attribute a suggestion to a glyph-only match.
When following a batch import, generate this report only after that batch and
its conflict resolutions are complete. Use the resulting entry IDs as the scope.
The Markdown output must hide related words already represented by existing
entries and explicit rejections, while preserving those identities in JSON.
Shared writing comes from the exact matching seed; shorten it by aligned unit
removal or extend it using fresh combo evidence only at added positions.
Use the readable report to present
each dictionary identity, reading choices, proposed writing and both sides of
combo conflicts. All decisions initially remain `pending`, regardless of combo
consistency. Record a human's explicit entry-by-entry decisions only in each
item's `review` object; approval must select the whole preferred form, canonical
reading and any alternates, resolving conflicts and unknown positions.

For a batch-authorized consistent proposal, set its review object's
`review_status` to `machine-reviewed`, retain the selected spelling/readings,
record contextual dictionary/combo screening provenance, and mark the batch
decision approved. This is import authorization, not individual human review;
do not upgrade these entries to `reviewed`. Existing-entry overlaps stay pending.

After human review, `import-related /path/to/review.json` previews only individual
`approved` decisions; add `--apply` when their local import is authorized. These
entries are imported as `reviewed`, preserving original MOE sources, without a
`rule_generated` flag. Pending/rejected items are never imported. An overall
request to import suggestions does not establish individual human review.
Do not rewrite sealed report evidence. If entries, dictionary or implementation
change, regenerate the report and review the updated evidence before import.
Existing-entry conflicts still follow the resolution rules below.

## Import conflicts require maintainer review

For the same written form and canonical reading, always prefer a substantive MOE
entry with actual definitions over an `附錄－百家姓` surname appendix duplicate.
Use the substantive entry's original source row and retain the appendix identity
only in the import audit as excluded. This is the maintainer's standing resolution;
do not ask again for this duplicate pattern or invent a definition when none exists.
The preference selects dictionary identity; it does not establish that a corpus
span uses any particular sense or is an independent word.

Sharing a canonical reading alone is not an import conflict. When written forms
and dictionary identities differ, inspect the source context and continue if it
supports both proposals. Do not create a human-review hold solely for homophones.
Questions about a matched span occurring only inside a compound are separate
from duplicate identity and must state that actual evidence concern.

Present import conflicts directly in the conversation as a readable table or
short list, not through a structured question tool.

When an import approval overlaps an existing entry, show the maintainer the
approved form/reading, existing ID and form/readings, relevant source identities,
and the proposed resolution. Prompt for an explicit decision before changing the
existing preferred form, adding or merging readings, treating the approval as
already handled, or creating a separate word. A general request to import, or an
ordinary approval in a review export, does not resolve a conflict with an existing
entry. Continue nonconflicting imports while the conflicting cases await review.

Apply a resolution already explicitly given by the maintainer in the current
conversation without asking again. Preserve existing IDs and forms when the
maintainer chooses to keep them. Shared Hanji alone does not establish lexical
identity: compare the original MOE entry IDs and evidence, and retain separate
romanized recommendations when the maintainer explicitly chooses distinct words.
Record an evidence-backed `identity_note` for a deliberate separate entry.

## Corrections and IDs

Preserve IDs on spelling or reading corrections. After a deliberate edit, run
`format` to sort keys/sets and rename the file from its preferred form and canonical
TL initial; then run `validate`. Cite evidence for added facts and leave unknown
optional notes absent.

`next-id` is only a preview. `add` owns allocation through `id-sequence.toml`.
Never decrement the counter or recycle a deleted/reserved ID. Local writers are
serialized, but independent clones can allocate the same number: resolve such
collisions before merging, update affected references, and advance the counter.
Do not silently renumber already published entries.

The MOE copy lives in ignored `.cache/dictionaries/moe/<sha256>/kautian.ods`. Its
GitHub revision, download URL, checksum, and source description are tracked in
`references/moe.toml`. First use fetches that exact pin; later lookups stay offline.
Never repin or substitute a dictionary after a checksum mismatch. On an explicit
source refresh, inspect the new edition and terms before changing the pin.
