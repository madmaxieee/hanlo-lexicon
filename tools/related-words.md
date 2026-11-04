# Related-word discovery and review

[Maintenance guide](README.md) · [Terminology](../GLOSSARY.md)

Run commands from the repository root. Follow the maintenance skill's
[related-word editorial procedure](../.agents/skills/maintain-lexicon/SKILL.md#standalone-related-word-review)
for report timing, spelling adoption, review authority, and provenance.
This reference describes matching, report fields, and command behavior.

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

`--entry-id` is repeatable. Output files must be outside the repository or under
ignored `.cache/related-moe/`. Discovery does not allocate IDs, approve words,
or import entries.

### Matching and spelling evidence

The search uses literal contiguous Hanji and exact shared Hanji/TL combos:
for two Hanji AB, it finds XAB, ABX, XYAB and ABXY; for three Hanji ABC, it finds
AB, BC, XABC and ABCX. Every shared glyph and aligned syllable must agree,
including tones and neutral markers. Each canonical or explicitly recorded
alternate reading is compared as a complete sequence; syllables are never mixed
across alternatives. For example, 中ng / tiong-ng cannot match 中央公園 /
Tiong-iong Kong-hn̂g because 央/ng and 央/iong differ. Contractions and other
unalignable readings cannot prove a shared combo match.

Check-time seeds come from supplied `preferred_form`, `moe_forms`, `hanji_forms`,
or an explicitly cited MOE headword/reading. Reading similarity alone supplies no
Hanji. Glyph variation selectors remain attached; explicit MOE annotations are
ignored for matching and preserved in the evidence.

Suggestions cover numbered MOE `詞目` identities and their recorded variants,
without comparison/name/surname-sheet duplicates. They retain dictionary order,
original headwords, readings, definitions, source rows, and `relations` recording
`base_form`, `matched_form`, `pattern`, and `combo_matches`. Only reading choices
with a shared combo match are offered. Homographs remain separate, the requested
word is omitted, and suggestions do not recursively seed further suggestions.
The word shapes do not establish semantic kinship.

`writing_suggestions` preserves the matching existing seed's spelling at shared
positions. Shorter words remove extra aligned units; longer words use the current
combo inventory at added positions. Generated and disputed entries supply no
recommendations. Each position retains Hanji, TL, supported outputs, supporting
entry IDs, preferred forms, readings, sources, and review status. Shared positions
also retain full inventory choices as audit evidence.

A complete inherited spelling, or one completed with a single supported output
at every added position, is `consistent`. Conflicting added outputs produce
`conflicting` suggestions; unknown positions are `incomplete`, and unsupported
alignments are `unalignable`. `variant_writing_suggestions` is separate from canonical
proposals, so uncertain dictionary variants do not demote the canonical proposal.
Batch checks use one pre-batch combo snapshot; unwritten requests do not supply
evidence for later requests.

### Reports and editable decisions

The JSON report contains original MOE evidence, sourced reading choices,
writing suggestions, existing-entry candidates, seed identities, shared Hanji/TL
proofs, and one `review` object per related entry. The Markdown index links to
per-word evidence pages, shows seed preferred forms separately from new proposals,
and omits existing-entry candidates and explicit rejections. The complete
evidence remains in JSON. An existing-entry candidate means a shared recorded
Hanji form or MOE source identity; it is an identity-review lead rather than proof
of a duplicate. Supporting-entry counts distinguish Hanji and romanization, with
at most three example preferred spellings per side in the readable report.

Every `review.decision` starts as `pending`. Edit only the `review` object to
record an authorized decision, for example:

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

`rejected` excludes a word; `pending` leaves it for later review. Omitted
`review_status` defaults to `reviewed` for individually human-reviewed decisions.
Explicit `"review_status": "machine-reviewed"` selects the authorized model-review
mode. The importer accepts this mode only for `Consistent proposals`: complete,
consistent canonical spelling suggestions, including shorter words with inherited
spellings. Conflicting, incomplete, or unalignable proposals are ineligible.
See the editorial procedure for authorization and required review provenance.

An approval must select the preferred spelling and canonical/alternate readings.
Readings must belong to the same MOE identity, including its sourced alternate,
colloquial, contracted, or dialect readings. Human choices can adopt a spelling
other than the generated proposal. There is no approve-all operation or automatic
acceptance of consistent suggestions; existing-entry overlaps require explicit
identity resolution and are never silently updated or dismissed.

### Preview and apply

```sh
python3 tools/lexicon.py import-related /path/to/fire-train.review.json
python3 tools/lexicon.py import-related /path/to/fire-train.review.json --apply
```

The first command previews without allocating IDs. `--apply` submits only
`approved` decisions to the ordinary batch writer, preserving their selected
review status and original MOE citations. Pending and rejected suggestions are
excluded. The seed's corpus context is not copied as an occurrence of a related
word. Optional review rationale is preserved without inventing an explanation.
The writer repeats normal source, duplicate, and ID checks and validates after
import.

The report seals dictionary identity, source evidence, combo support, entry state,
and seed scope separately from editable decisions. Changes to evidence, entries,
dictionary pins, or implementation require regeneration and review of the updated
report. The writer rechecks entry/dictionary state under its lock before reserving
IDs. After importing part of a report, regenerate for remaining suggestions
because the entry and consistency evidence has changed.
