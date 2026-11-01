# TSBP issue 385 batch 1 import

Imported from the maintainer's `review (12).json` export, issue 385, corpus SHA-256
`a161a8e8a4ce678ea6848a8204fafc4659590a4089b027ce5ecf4ddf837202e5`, review-group
SHA-256 `343231590ae049afc595b1105578b0480d6bce7db9c708d7497a0439cea65cd0`.
The original export is unchanged. No harvest or review-page regeneration was run.

Thirty ordinary approvals created entries 4707–4736 through the review importer.
Three further approved words created entries 4737–4739 through `lexicon.py add-batch`,
after original dictionary and article checks established distinct identities:

- `ànn`: MOE 2120, 詞目 row 2121, bending down, in `頭ànn-ànn`;
  distinct from existing 700, `ǹg`, MOE 2123, row 2124, facing/tending toward.
- `tshia`: MOE 6000, 詞目 row 5999, overturning, in `chhia龜弄甕`;
  distinct from existing 1299, `車`, LKK row 767, vehicle/machine.
- `tshok`: MOE 11104, 詞目 row 11101, small-quantity measure applied to salt;
  distinct from existing 1313, `簇`, LKK row 794 and MOE 14509, row 14503,
  a group or heap of people or things.

All 33 new entries retain `imported` status. Source references and explicit identity
notes are recorded in the entries. The review's explicit custom instruction added
`--lueh` as another alternate of entry 808, preserving its ID, preferred `落--去`,
canonical `lo̍h--khì`, existing `lueh`, status and sources. Three literal issue 385
`--lueh` occurrences were added as provenance.

Subsequent maintainer resolutions:

- Preserve LKK recommendations as the standing preference: keep entry 1334
  `舐 / tsīnn` and its readings, and entry 1043 `磕 / kha̍p`. Do not import the
  romanized replacements from this batch.
- Correct custom POJ `má-chih` to preferred form and TL reading `má-tsih`.
  Offline LKK/MOE and existing-entry checks found no matches. Imported as entry
  4740 with article evidence and explicit maintainer review.
- Confirm custom `--tńg-去` has reading `--tńg-khì`. Checks revealed existing entry
  619, `tńg去 / tńg--khì`, MOE 詞目 row 12619. Its neutral marker differs from
  the new request. The maintainer explicitly chose a separate entry: imported
  `--tńg-去 / --tńg-khì` as entry 4741 with a distinguishing identity note and
  literal article evidence. Preserve entry 619 unchanged.

The existing `hit陣` → entry 493 mapping is retained. Pre-import related-word
checks remain audit evidence in the ignored output directory. After resolving
the remaining import conflicts, fresh related discovery was generated for the
new entries (4707–4741), using their recorded two-/three-Hanji forms, at
`.cache/related-moe/tsbp-385-batch1.json` and its Markdown index. These suggestions
remain pending and were not imported. No corpus harvest or review page was rerun.
