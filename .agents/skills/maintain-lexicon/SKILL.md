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
