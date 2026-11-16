# Issue 382 Hanji import decisions — 2026-11-17

The maintainer authorized importing the `gpt-6-luna` (medium reasoning) model-screened `recommend_import` set from the refreshed pure-Hanji harvest on TSBP issue 382 (`batch_proposal` and `agreement_only` queues; 721 screened candidates total, up to three sampled contexts per candidate, after excluding non-`外來詞` `附錄` and `單字不成詞者` MOE entries).

All 449 `recommend_import` candidates (54 from `batch_proposal`, 395 from `agreement_only`) were imported as `machine-reviewed` entries with IDs 5392–5840 via `lexicon.py add-batch`:

- Screened by `gpt-6-luna` (`reasoningEffort = "medium"`), collected with `review_hanji.py collect` in `review-v3` (model-review `review.json` SHA-256 `80df80ec36cd0f865b9554a898c627be64a06aa71744db767727ca433f57bf71`).
- Offline existing-entry, LKK, and pinned MOE checks cleared all 449 entries with zero existing-entry conflicts, zero LKK matches, and zero reading overlaps.
- All new records retain original MOE `詞目` snapshot/sheet/row references, only the designated supporting article offsets and URLs, and `review_status = "machine-reviewed"`. Batch authorization does not constitute individual human review.
- Remaining screened decisions (`211` `combo_only`, `27` `hold`, `34` `reject`) and the unscreened `focused_review` queue (`2,737` candidates) remain unimported.

Next ID advanced to 5841 in `id-sequence.toml`. All pre-existing entries and source snapshots remain unchanged. Validation (`5,775` entries), canonical formatting, and test suite checks passed.
