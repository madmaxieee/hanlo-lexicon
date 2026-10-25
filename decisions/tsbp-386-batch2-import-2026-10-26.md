# TSBP issue 386 batch 2 import

The maintainer requested import of `review (11).json`, SHA-256
`8b312bff8a84c0e9d0db921a761f27684a49a3b159b52b6ccf59a9bdc88a6e9c`,
plus `lut官` / `lut-kuann`, Hanji 甪官, in the dismissal/removal-from-office
sense, and `--落-來` / `--lo̍h-lâi`. The export contains 97 ordinary approvals
and four structured custom requests. Its corpus, candidate, MOE and screening
fingerprints match the issue-386 pilot.

## Three-to-two-syllable contraction approval

The maintainer also identified a blocked `查某kán` approval after selecting
three MOE contractions. The saved decision contains the full filing reading
`tsa-bóo-kán` and alternates `tsőo-kán`, `tsa̋u-kán` and `tsa̋-kán`. The page's
alternate-spelling preview incorrectly required equal syllable counts, although
the maintenance writer already renders a shorter alternate as its complete
romanized reading. This made the approval checkbox disabled.

The page now follows the maintenance writer for shorter contractions, including
Hanji-only preferred spellings. Equal-length mixed-spelling alignment and
neutral-boundary checks remain in place. Regression tests compare browser and
writer outputs, exercise the actual approval/export logic with all three
contractions, and retain rejection of inconsistent longer/equal-length readings.
An isolated browser session restored the exported choices, clicked the enabled
approval checkbox and verified that all three alternate IDs were exported.

The original export remains unchanged. A derived export adds only the intended
`查某kán` approval from the saved decision, recording the maintainer's instruction
and the formerly blocked state. MOE word 5096, 詞目 row 5096 and 合音唸作 rows
18–20 support its readings. Entry 4373 preserves the full preferred `查某kán`
and exports all three contractions in full romanization.

## Imports and source preservation

The ordinary importer created 91 records, IDs 4283–4373, after the standard
offline existing-entry, LKK and pinned MOE checks. Seven initial overlaps were
separated from that automatic batch. Two concern distinct homophones rather
than existing lexical identities:

| New entry | Existing word | Evidence |
| --- | --- | --- |
| 4380 `tiām`, MOE 10411 墊, 詞目 row 10408 | 1255 恬 / tiām, LKK row 687, quiet/silent | The source says `tiām花子`, sowing flower seeds, matching the selected MOE planting sense. |
| 4381 `tàm`, alternate `tìm`, MOE 10914 頕, 詞目 row 10911 and 又唸作 row 834 | 310 抌 / tìm, LKK row 696, throwing; 1254 踮 / tiàm, alternate tàm, LKK row 686, location/residence | The source describes mango branches drooping under flowers. The selected MOE word describes drooping or nodding. |

Both new records preserve specific identity notes and original MOE/article
references. The standing homophone rule permits their addition without changing
the existing recommendations.

The normal batch writer also created these six custom records, with whole-phrase
article offsets rather than the shorter triggering anchor:

| ID | Preferred form | Reading | Recorded Hanji |
| --- | --- | --- | --- |
| 4374 | 黃huánn黃huánn | n̂g-huánn-n̂g-huánn | 黃幻黃幻 |
| 4375 | ōm-sà-sà | ōm-sà-sà | 茂嗄嗄 |
| 4376 | bē-tín-bē動 | bē-tín-bē-tāng | 袂振袂動 |
| 4377 | ûn境 | ûn-kíng | 勻境 |
| 4378 | lut官 | lut-kuann | 甪官 |
| 4379 | --落-來 | --lo̍h-lâi | --落-來 |

Custom Hanji is recorded in `hanji_forms`, without claiming MOE inclusion. The
maintainer's dismissal/removal meaning identifies `lut官`; it is not added as
a prohibited entry-definition field. Each custom request passed fresh offline
checks. All 100 new records remain `imported`. No preexisting entry or original
source snapshot was changed. The exact four exported custom requests are marked
handled in the pilot journal. Original Luna decisions are retained verbatim for
the 149 remaining occurrences, after verifying every packet row is unchanged.

Validation and canonical formatting pass. The ordinary CSV excludes pure-Hanji
preferred forms by repository policy; `--落-來` is verified in the all-forms CSV.
The contraction outputs are verified in both exports. Tests pass: 16 Node tests,
73 TSBP Python tests and 139 maintenance Python tests. No local commit or
publication was requested for this batch.

## Resolved existing-entry decisions

The maintainer explicitly kept `lām-sám` and approved the other four proposed
resolutions. The normal writer repeated offline checks and added separate entry
4382 `tsuat`, preserving entry 739. Entries 1334, 812, 1313 and 1273 stay
unchanged. Their declined alternative spellings join this issue's editable
Ignore list; this does not impose a global spelling policy. No approvals remain
pending from this export.

The harvester deliberately deduplicates complete output spellings, not MOE word
identities or inferred readings of Hanji. `lām摻` is therefore not mechanically
identical to entry 812's output `lām-sám`; the importer's broader identity check
instead raises the same-word conflict. After the explicit keep-existing decision,
the issue-specific Ignore list excludes `lām摻` without changing the entry or
globally hiding other proposed writing choices.

| Approval | Existing entry and evidence | Adopted resolution |
| --- | --- | --- |
| `chn̄g`, filing `tsīnn`, selected MOE 6533 舐, 詞目 row 6532 | 1334 舐 / tsīnn, alternates tsn̄g and tsī, LKK row 846 | Keep the existing 舐 recommendation and supported readings rather than adding another spelling for the same word. |
| `lām摻` / lām-sám, selected MOE 12224 濫糝, 詞目 row 12219 | 812 lām-sám / lām-sám, same MOE identity | Keep entry 812's lām-sám unchanged, as explicitly selected by the maintainer. |
| `tshok` / tshok, selected MOE 11104 撮, 詞目 row 11101 | 1313 簇 / tshok, LKK row 794; MOE 14509 簇 is also a measure word for piled/grouped objects | Keep the existing 簇 recommendation unless the maintainer distinguishes a separate lexical identity or adopts the romanized spelling. |
| `tsuat` / tsuat, selected MOE 4261 泏, 詞目 row 4261 | 739 tsuh / tsuh, selected MOE 4259 泏, 詞目 row 4259 | Added separate entry 4382 tsuat for splashing out with an explicit identity note; retain tsuh for seeping/dripping through small openings. |
| `tōng` / tōng, selected MOE 11061 撞, 詞目 row 11058 | 1273 撞 / tōng, LKK row 727 | Keep the existing 撞 recommendation for the same collision/striking word. |

The batch archive is the pilot's `imports/review-8b312bff8a84/` directory.
It retains the original and derived exports, initial inventory fingerprints,
full conflict checks, custom requests, preview/apply reports and integrity audit.
The original 29-row pre-import suggestion list is retained as
`related-suggestions-pre-import.md` and `related-suggestions-pre-import.json`.
It is superseded by the post-import workflow below; its unknown components and
existing-word duplicates must not be presented as current recommendations.

## Post-import related recommendation workflow

The maintainer corrected the timing and spelling scope of the related report.
Run discovery after all authorized batch imports and conflict resolutions, using
the resulting entry IDs and current inventory. Pre-import checks remain audit
data. The project maintenance skill and tool documentation now require this
order. The default Markdown output is a new-only index, with separate linked
evidence pages. Existing-entry candidates remain in JSON for identity audit;
they are omitted from the new recommendation table. This removes already-present
words such as 查某, 雞nuā仔 and the two 棉tsioh forms.

Writing proposals retain the matching current seed at shared positions. Only
added positions need new combo choices. Shorter AB/BC words remove the extra
aligned seed units; they do not require an invented replacement spelling.
Full inventory conflicts remain attached as audit evidence. Generated/disputed
entries do not supply inherited recommendation evidence. Canonical proposals
and dictionary variants are separate, so 茨頭家 does not make 厝頭家 unresolved.
The original MOE snapshot and variant evidence are unchanged.

The maintainer explicitly excludes 頭家厝 and retains romanized 家 · ke in the
remaining 頭家-related proposals. The fresh report therefore proposes 店頭ke,
厝頭ke and 頭ke娘, as well as 平thánn-thánn from the imported 平thánn seed.
It contains 17 new candidates, hides six existing-entry candidate rows, and
omits the explicitly rejected station-name row. Shorter new proposals such as
生驚 and 李仔 have complete inherited spellings. These are recommendations,
not new import approvals.

The fresh sealed report is `related-post-import.json`; the updated user-facing
index remains `related-suggestions.md`, with per-word pages in
`related-suggestions-entries/`. `related-post-import-audit.json` records the
scope, exclusions and unchanged entry/source inventories. All vocabulary entries
are unchanged by this workflow repair and recommendation rerun.

## Three individually resolved related imports

The maintainer subsequently approved these three words and resolved their
writing/reading choices. MOE 6693 initially lacked a complete proposed spelling;
the maintainer explicitly clarified the preference as `khí-moo-giang`.
Only these three review objects were approved. The maintenance preview repeated
offline existing-entry, LKK and pinned MOE checks, and `import-related --apply`
created them as individually `reviewed` records:

| ID | Preferred form | Canonical filing reading | Alternates | Original MOE reference |
| --- | --- | --- | --- | --- |
| 4383 | khí-moo-giang | khí-moo giang | None | Word 6693 起毛婸, 詞目 row 6692 |
| 4384 | suà喙尾 | suà-tshuì-bué | suà-tshuì-bé | Word 7762 紲喙尾, 詞目 row 7760 |
| 4385 | 戶tīng跤 | hōo-tīng-kha | None | Word 28380 戶橂跤, 詞目 row 29041 |

For 28380, the maintainer selects Hanji 跤 at the added kha position while
retaining the 戶tīng seed. For 7762, the maintainer approves the complete form
and both sourced readings, with bué canonical in line with other 尾 entries;
the Hanji output remains 尾 for both readings. This is a resolved word-level
choice, not a remaining spelling conflict.

The sealed approval file, preview, apply report and integrity check are retained
as `related-three-resolved.json`, `related-three-resolved-preview.json`,
`related-three-resolved-import.json` and `related-three-resolved-integrity.json`
in the batch archive. All preexisting entries and original snapshots remain
unchanged. Validation, formatting and both CSV exports pass. Related discovery
was rerun after import using the original batch seed scope, removing these three
from the new-only report and leaving 14 new candidates for separate review.
