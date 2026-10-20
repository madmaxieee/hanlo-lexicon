# TSBP issue 390 approved imports

On 2026-10-19 the maintainer exported four explicit review approvals and requested
that they be imported before changing alternate-reading handling. Offline LKK and
pinned MOE checks found no existing related entries for those four additions.

| ID | Preferred form | Filing reading | MOE evidence |
| --- | --- | --- | --- |
| 371 | lóng是 | lóng sī | 詞目 row 12776; headword 12782 攏是 |
| 372 | m̄是 | m̄ sī | 詞目 row 991; headword 990 毋是 |
| 373 | hit个 | hit ê | 詞目 row 3890; headword 3890 彼个 |
| 374 | tsit个 | tsit ê | 詞目 row 28548; headword 27296 這个 |
| 375 | 想beh | siūnn-beh | 詞目 row 14364; headword 14370 想欲 |

The maintainer additionally requested both `想beh` and `想bueh` for 想欲. Entry
375 keeps `siūnn-bueh` as an alternate supported by 又唸作 row 1115 of the same MOE
word. The CSV builder generates the paired output `想bueh,siūnn-bueh` while
retaining a single editorial word record. It preserves Han characters and varies
only corresponding romanized syllables. The review rescan indexes those generated
written forms as well as each primary preferred form.

Every entry cites the pinned original MOE snapshot `moe-kautian-3e0b2023e0bd` and
a published TSBP article with a precise source locator. All five records remain
`imported`; this batch does not change existing review statuses. The prior 56
records with alternate readings were audited; none required a mixed-form data
correction. The earlier CSV export policy discarded Han characters for mixed
alternates; the export tool now preserves them and the CSV was rebuilt.

No source snapshot was edited, and no commit or publication was requested.

## Second approved review batch

The next exported review has SHA-256
`62001bc75ddf4d95068c7e301d743792693b0b887d7450c013af5c1cf960a233`.
It contains 36 explicit approvals from the same corpus and MOE edition. All
selected readings were verified against original pinned MOE rows, and every new
candidate passed offline LKK/MOE and existing-entry checks.

The maintenance command allocated IDs 376–410 for 35 new word records. They
contribute 67 selected written-form/reading pairs before global CSV deduplication.
All remain `imported` and retain their original MOE and published article sources.

The approved `--neh` particle corresponds to existing entry 153, LKK row 435
(`呢、耶`). MOE word 3687, 詞目 row 3687, supports `--neh` for the same particle.
Add that sourced input reading and its original MOE/article citations to entry
153, preserving its primary `neh` spelling, filing reading and stable ID. The
export generates both `neh,neh` and `--neh,--neh`. Entry 159 `nih` denotes the
question particle (LKK row 445; MOE word 3686) and is unchanged. No unrelated
homograph or duplicate word was created to bypass the related-entry check.

All 36 approvals are resolved. Repository validation, canonical formatting and
CSV rebuilding follow the import. The corpus rescan indexes all 410 current
records and generated alternate outputs.

| ID | Preferred form | Filing TL |
| --- | --- | --- |
| 376 | m̄知 | m̄ tsai |
| 377 | 時tsūn | sî-tsūn |
| 378 | ka-tsua̍h | ka-tsua̍h |
| 379 | mā是 | mā sī |
| 380 | 牽--ê | khan--ê |
| 381 | iah是 | iah-sī |
| 382 | tsiânn做 | tsiânn-tsuè |
| 383 | hām | hām |
| 384 | khang-khuè | khang-khuè |
| 385 | tsit款 | tsit khuán |
| 386 | ǹg望 | ǹg-bāng |
| 387 | 啥mih | siánn-mih |
| 388 | 認bat | jīn-bat |
| 389 | hōo伊 | hōo i |
| 390 | 先--ê | sian--ê |
| 391 | bàng-gà | bàng-gà |
| 392 | bē輸 | bē-su |
| 393 | m̄-thang | m̄-thang |
| 394 | tng | tng |
| 395 | ē記得 | ē-kì--tit |
| 396 | iáu未 | iáu-buē |
| 397 | kah意 | kah-ì |
| 398 | kám有 | kám ū |
| 399 | ē-sái | ē-sái |
| 400 | buē到 | buē kàu |
| 401 | hit時 | hit-sî |
| 402 | iáu-koh | iáu-koh |
| 403 | iáu有 | iáu-ū |
| 404 | lim酒 | lim tsiú |
| 405 | m̄敢 | m̄ kánn |
| 406 | m̄知影 | m̄ tsai-iánn |
| 407 | tńg來 | tńg--lâi |
| 408 | 倒tńg | tò-tńg |
| 409 | hānn | hānn |
| 410 | iáu是 | iáu-sī |

## Third approved review batch

The next exported review has SHA-256
`e2f04269326e36108360dbb5bf4179f044808515fb86c8a19821ed5205eace11`
and contains 116 explicit approvals from the same corpus and pinned MOE edition.
All selected readings and source references were verified against the original
dictionary. Offline LKK/MOE and existing-entry checks precede every addition.
The normal maintenance command allocated IDs 411–522 for 112 new records; all
remain `imported`.

Four pairs of approvals select the same MOE word, final spelling, filing reading
and alternates. They are represented once, with both approvals' source references
retained. No unrelated MOE word identities are merged.

| Duplicate anchor | Combined with anchor | Resulting ID |
| --- | --- | --- |
| chiâⁿ實 | tsiânn實 | 454 |
| hit-tang-chūn | hit-tang-tsūn | 436 |
| hōaⁿ | huānn | 497 |
| 順suà | 順sòa | 468 |

All 116 approvals are resolved. No existing entry or source snapshot was changed
by this batch. Repository validation and canonical formatting pass; the CSV and
review are rebuilt against all 522 entries and generated alternate written forms.


## Fourth review batch — 2026-10-20

The exported `review (2).json` has SHA-256
`4ee5b9f244c5d2c1d1bac1c1528c89c2e489836df40df68f0a4c477bdeb7c42c`.
Its issue, corpus, candidate fingerprint and pinned MOE edition match the saved
pilot. The original export is preserved byte-for-byte in the local pilot batch
folder `imports/review-4ee5b9f244c5/` alongside the preview, import results,
custom resolutions and before/after measurements.

Of 150 explicit approvals, 148 created new entries (IDs 523–670). The approvals
for `sia̋n-pái` and `siăn-pái` normalize to the same preferred form and reading;
ID 524 retains both published source references. The remaining approval,
`ē通`, MOE 19290 / `會通`, overlaps existing ID 341 (`ē-thang`, LKK row 86).
The actual source clause is `「我ē通知翁`, where this match cuts into `通知`.
The maintainer explicitly chose to skip this context match. The exact literal
context `我ē通知翁` is excluded from this pilot, preserving other `ē通` contexts
as eligible candidates. No edit to entry 341 was made; no approvals remain pending.

Five explicit custom requests were resolved as follows. All new requests passed
the same offline LKK/MOE duplicate checks and normal maintenance ID allocation.
No dictionary meaning or whole-compound MOE match is invented for these forms.

| Requested anchor handling | Result | Filing TL | Evidence |
| --- | --- | --- | --- |
| `liô` → `liô心` | New ID 671 | `liô-sim` | Literal article span; MOE 心, word 792, 詞目 row 793 supplies only the adjacent 心 reading |
| `sio-lām` | New ID 672 | `sio-lām` | Explicit requested reading and complete article anchor |
| `khoo` → `khoo狗螺` | New ID 673 | `khoo-káu-lê` | Literal source prefix khoo; 狗螺 matches the final two characters/readings of MOE 吹狗螺, word 2987, 詞目 row 2988 |
| `lê` → `lê-lê` | Resolved by approved ID 544 | `lê-lê` | Complete article anchor, already included among the 150 approvals |
| `ònn` → `gîn-ònn-ònn` | New ID 674 | `gîn-ònn-ònn` | Explicit requested reading and complete article anchor |

The batch adds 152 records and 179 unique written-form/reading pairs, retaining
all records as `imported`. All 522 pre-existing entry files and the source corpus
are byte-for-byte unchanged. Repository validation and `format --check` pass.
The rebuilt CSV contains 824 unique pairs across 674 entries; every resolved
approval and new custom pair is present.

The rescan also preserves the export's explicit Ignore choices, adding
`hu-lí-liàn` and `tuā-lián` to the four curated single forms in a separate local
`review-ignored-forms.json`. It leaves the original four-form file unchanged.
After skipping the rejected context, the visible review has 125 groups / 186
occurrences, with 1,894 compact snippet characters out of 29,571 source characters
(93.60% reduction). All-context coverage is 2,183 characters (92.62% reduction). Literal `liô` and `khoo` component
candidates can still appear: the current MOE anchoring does not synthesize a
compound dictionary match merely because a custom mixed form has been imported.

No source snapshot was edited, and no commit or publication was requested.

The context-skip audit verifies that only the rejected `ē通` emitted span and its
previously suppressed `ē` source trigger are removed. All other emitted spans
and all 674 entry files are unchanged. Two existing context-exclusion tests pass.


## Fifth review batch and duplicate audit — 2026-10-20

The exported `review (3).json` has SHA-256
`ac4c3e2312be8cde9eb9b07aff98e41c5728f1bb1a15b5c6cf8c21b432c3dbb5`.
The candidate fingerprint, corpus and pinned dictionary match the pilot.
All 19 explicit approvals passed the offline existing-entry/LKK/MOE checks before
any import; none matched a current entry. The maintenance command allocated
IDs 675–693. All selected readings and alternatives retain original MOE and
published article references, and all new records remain `imported`.

The JSON also retains 325 approved decisions as review history. Of these, 305
already belong to tracked/excluded anchors, one belongs to the previously skipped
`ē通` anchor, and 19 are current active approvals. The import queue is the explicit
`approvals` array; the historical decisions do not authorize additional records.
Four of five custom requests repeat completed requests for IDs 671 (`liô心`),
672 (`sio-lām`), 544 (`lê-lê`) and 674 (`gîn-ònn-ònn`). They were not imported again.

The new custom request explicitly corrects source `包kuà` to preferred `包kuat`,
MOE form `包括`, reading `pau-kuat`. The original MOE snapshot supports that pair
at word 22115, 詞目 row 18780. Offline checks find no existing candidate; the
maintenance command allocated ID 694. The article citation preserves the literal
source spelling and exact span, and records the explicit reviewer correction.
The exact context `作品包kuà公共電視` is marked handled so the same source typo
will not return as an unreviewed `kuà` candidate. No global reading equivalence
or unsupported alternative reading is introduced.

The duplicate investigation identified a pilot matching gap. Tracked custom
mixed forms absent from MOE were not providing compound coverage, so single
`liô` and `khoo` candidates inside `liô心` and `khoo狗螺` remained visible. The
pilot now locates exact tracked mixed spellings using parsed, TL-normalized
source units, preserving literal Han, separators, neutral markers, tone and
original offsets. These lexicon spans supply containment evidence only; no MOE
match is invented. An audit comparing old and fixed code on the same current
inputs removes exactly three single-component occurrences (two `liô`, one
`khoo`), preserving every other emitted span. Standalone occurrences and nested
or overlapping multi-syllable matches remain eligible.

Handled custom requests now have a small local resolution journal. Resolutions
are embedded only while their stable entry ID, preferred form and filing reading
still match the current lexicon. The UI reconciles identical saved prompts on
reload and file restore, preserving a handled-history note; changed prompts
remain pending. A VM check using this exact exported state produces zero new
approvals and zero pending custom requests after the completed import.

The batch adds 20 entries / 24 unique written-form/reading pairs. All 674 previous
entry files and source snapshots remain unchanged. The rebuilt CSV contains
848 pairs across 694 entries. Validation and canonical formatting pass; 59 pilot
Python tests and seven Node tests pass. All 3,202 retained source triggers,
literal source offsets and the regenerated candidate fingerprint are verified.

The export's 18 explicit Ignore choices are retained. The refreshed review has
91 groups / 148 occurrences, with 1,404 compact snippet characters out of 29,571
source characters (95.25% reduction). All-context coverage is 1,660 characters
(94.39% reduction). The complete original export, checks, old-code ablation,
results and before/after files remain in the local pilot folder
`imports/review-ac4c3e2312be/`. No commit or publication was requested.


## Sixth review batch — 2026-10-20

The exported `review (4).json` has SHA-256
`ab0337eaf58444c49f7b4e450b25c11a03abd69ef0a7d9b89c6c2471637aca89`.
Its corpus, issue, candidate fingerprint and pinned MOE edition match the current
pilot. All five approvals passed offline existing-entry/LKK/MOE checks before
import; none matched an existing entry. There were no custom requests.
The normal maintenance command allocated IDs 696–700, retaining original MOE and
article citations and `imported` status.

| ID | Preferred form | Filing TL |
| --- | --- | --- |
| 696 | khah早 | khah-tsá |
| 697 | khuì力 | khuì-la̍t |
| 698 | làu-phâu | làu-phâu |
| 699 | nauh | nauh |
| 700 | ǹg | ǹg |

All 695 previous entry files and the source corpus remain byte-for-byte
unchanged. Validation and canonical formatting pass. The export and complete
preview/apply results remain in the local pilot folder
`imports/review-ab0337eaf584/`.
