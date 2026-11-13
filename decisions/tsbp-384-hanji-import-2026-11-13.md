# Issue 384 Hanji import decisions — 2026-11-13

The maintainer authorized importing the `gpt-6-luna` (medium reasoning) model-screened `recommend_import` set from the pure-Hanji harvest on TSBP issue 384 (`batch_proposal` and `agreement_only` queues; 359 screened candidates total, up to three sampled contexts per candidate).

All 145 `recommend_import` candidates (9 from `batch_proposal`, 136 from `agreement_only`) were imported as `machine-reviewed` entries with IDs 5246–5390 via `lexicon.py add-batch`:

- Screened by `gpt-6-luna` (`reasoningEffort = "medium"`), collected with `review_hanji.py collect` (model-review `review.json` SHA-256 `e447cfac6a01aac67d93825c505542c18ea15f6e831ccb1aef7b3899b2da8374`).
- Offline existing-entry, LKK, and pinned MOE checks cleared all 145 entries with zero existing-entry conflicts, zero LKK matches, and zero reading overlaps.
- All new records retain original MOE `詞目` snapshot/sheet/row references, only the designated supporting article offsets and URLs, and `review_status = "machine-reviewed"`. Batch authorization does not constitute individual human review.
- Remaining screened decisions (`148` `combo_only`, `47` `hold`, `19` `reject`) and the unscreened `focused_review` queue (`3,642` candidates) remain unimported.

Next ID advanced to 5391 in `id-sequence.toml`. All pre-existing entries and source snapshots remain unchanged. Validation, canonical formatting, and test suite checks passed.
