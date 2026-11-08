# TSBP neutral-tone (`--`) corpus-wide import

The maintainer asked for neutral-tone (`--`) spellings across all TSBP articles to
be harvested for review. The normalized TSBP corpus has 2,265 articles; 2,092 of
them contain `--`. The maintainer gave three harvest criteria:

1. **MOE neutral word**: the source span matches an original MOE headword whose
   reading has `--` at the same syllable positions, such as `後--來` for MOE 後來
   `āu--lâi`.
2. **Romanized neutral form**: a leading `--` followed by a pure romanized run,
   such as `--lán`.
3. **MOE word with a leading `--`**: a leading `--` followed by a MOE headword,
   such as `--月` for MOE 月 `gue̍h`.

## Exact MOE matches imported

The first pass imports only criterion 1 words, through `import_review.py` from
`.cache/tsbp-neutral-review/moe-exact-review.json`. It created 109 entries, IDs
5029–5137, all with `imported` status. Each entry cites its MOE row and one TSBP
occurrence; the MOE headword is in `moe_forms`. Validation and formatting
checks pass.

An earlier batch had reserved IDs 5029–5246. It was backed out before any commit,
and the maintainer explicitly reset `next_id` to 5029. Those IDs were never
published, and this import reuses them.

Five more criterion 1 candidates are in the second review queue rather than
this import:

- `表--ê`, `友--ê`, `後--ê` and `穩--ê`: their corpus occurrences are cross-word
  spans, such as 發表 + ê, so they offer no valid article citation.
- `邊--á` / `pinn--á` (MOE 邊仔, 詞目 row 12870) conflicts with existing entry
  1156, `邊--a` / `pinn--a`.

## First maintainer review batch

The maintainer exported decisions for the second review queue as
`.cache/tsbp-neutral-review-2/review-21.json`. Only explicit approvals were
imported, all with `imported` status:

- 5138 `--m̄`, 5139 `--bē`, 5140 `--è`, 5141 `--pah` and 5142 `--niâ` were
  imported through `import_review.py`. Each cites one article.
- 5143 `--月` / `--gue̍h` comes from the maintainer's structured custom request.
  It cites MOE 月 (詞目 row 804) and one article, with `hanji_forms = ["--月"]`.

The maintainer's custom request for `厝--lìn` / `tshù--lìn` awaits a decision.
It is pending because entry 5029, `厝--裡` (MOE 厝裡; readings `tshù--lí`,
`tshù--nih`), may be the same word.

The maintainer also asked to omit articles whose text is over 80% romanized
syllables. The ratio is romanized syllables divided by romanized syllables plus
Han characters; 24 articles exceed it. Their IDs and ratios are in
`.cache/tsbp-neutral-2026-11-08/romanized-articles.json`.

Those articles are excluded as evidence for this batch and for later review
pages. The 34 passages the maintainer ignored in the review are excluded the same
way. The page tool records an ignored passage only when it starts with Roman text,
so these passages are removed from the regenerated review queue instead.

Seven candidates have no evidence left after these exclusions and leave the queue:
`--bô-tánn-kín`, `--khì-lâi`, `--khìr`, `--liáu-liáu`, `--sènn`, `--tshut-kuè`
and `--uè`.

None of the 109 exact-MOE entries imported earlier cites one of the omitted
articles.

## Second maintainer review batch

The maintainer's second export is `.cache/tsbp-neutral-review-3/review-1.json`.
It imported:

- 5144 `--mah` and 5145 `--nooh`, through `import_review.py` with article
  evidence.
- 5146 `--字` / `--jī`, with alternate `--lī` as the maintainer specified. It cites
  MOE 字 (詞目 row 2277) and one article.
- 5147 `--先-生` / `--sian-sinn`. It cites MOE 先生 (詞目 row 2060) and one article.

The maintainer ignored `--lìn` and `邊--á`. This drops the `厝--lìn` custom
request, so entry 5029 stays unchanged. Existing entry 1156, `邊--a`, also stays
unchanged.

The maintainer then changed entry 5029 to `厝--nih` / `tshù--nih`, with alternate
`tshù--lí` and Hanji `厝--裡`. Where the corpus spells out the reading, `nih` is
preferred: `厝--nih` and `tshù--nih` occur 29 times, plus 6 `tshù--ni̍h`, against
5 `tshù--lí`. The 381 Hanji `厝--裡` occurrences do not show the reading. The entry
now also cites an article that writes `厝--nih`.

The 84 passages ignored in this export are excluded from later queues together
with the earlier ones. Fourteen more candidates have no evidence left and leave
the queue.

## Harvest rules

- Romanized syllables were validated and converted from POJ to TL with the
  TaigiKeyboard converter. Preferred forms keep the source Hanji and use TL for
  the romanized syllables. The preferred form is the most frequent written form
  for the filing reading.
- MOE matching used the 詞目, 又唸作, 俗唸作 and 合音唸作 sheets. For all-Hanji spans,
  the main 詞目 reading was used. When several readings remained, a reading was
  accepted only if the corpus also spells it in Roman at a `--` position.
- A `--X` tail was dropped if a longer MOE `--` word covered it, such as `--月`
  in `正--月`. A span continuing into hyphenated Hanji was dropped as partial.
- Neutral-marked reading variants of one MOE word were merged as alternates, for
  example `厝--裡` `tshù--lí` with `tshù--nih`.
- 55 harvested groups were already covered by existing entries and were skipped.

## Pending review

`.cache/tsbp-neutral-review-2/review.html` holds the remaining 140 candidates,
with at most five sample passages per word:

- criterion 2 romanized forms;
- criterion 3 forms with a leading `--`, as structured custom requests;
- the five criterion 1 holdbacks above.

Preloaded agent screening decisions are in `prefilled-review.json` in the same
directory. Nothing in this queue is imported until the maintainer exports a review.

The scanner, candidate groups and screening plan are in the ignored audit
directory `.cache/tsbp-neutral-2026-11-08/`. Its `batch.json` and `apply.json`
record the backed-out first batch and are superseded.
