# Hanji for 个 and 仔; sense-dependent 甲

The maintainer resolved these cases while reviewing the Han-Lo combo inventory
on 2026-10-21 (Asia/Taipei). The question was whether different outputs for the
same Hanji and canonical TL syllable were inconsistencies or deliberate choices.
This document records that discussion and the adopted decisions.

## 个 · ê and 仔 · á

Always use Hanji 个 and 仔 for these two components. The existing recommendations
in the inventory agreed except for the three entries below. Apply the decision
to those entries without changing their other components or canonical readings.

| Entry ID | Previous preferred form | Adopted preferred form | Canonical TL |
| --- | --- | --- | --- |
| 25 | ham-á | ham仔 | ham-á |
| 174 | phín-á | phín仔 | phín-á |
| 743 | 別ê | 別个 | pa̍t-ê |

Original LKK recommendations remain source evidence: snapshot `lkk-2024-05-10`,
row 117 for entry 25 and row 482 for entry 174. The pinned MOE snapshot
`moe-kautian-3e0b2023e0bd` supplies the whole-word spellings/readings:

- 蚶仔, `ham-á`, MOE word 7821, 詞目 row 7819.
- 𥰔仔, `phín-á`, MOE word 13504, 詞目 row 13498.
- 別个, `pa̍t-ê`, MOE word 2971, 詞目 row 2972.

The decision to use these mixed/Hanji preferred spellings is the maintainer's;
these citations do not imply that LKK recommended the revised forms. Entry 743's
article citation retains the original occurrence `別ê`. Entries 373 (`hit个`)
and 374 (`tsit个`), and the other 42 recommendations for 仔 · á, already use the
adopted Hanji and require no spelling changes.

## 甲 · kah

Retain the conflict. Its outputs depend on meaning, so it must not be collapsed
into one universal spelling or resolved by a majority vote.

The maintainer's general preference is romanization for an entry marked 【替】
in MOE. This is an editorial preference applied with lexical context, not an
automatic instruction to replace every occurrence of a matching glyph/reading.

- Entry 68 remains `kah`. The pinned MOE headword `甲【替】`, word 1848,
  詞目 row 1849, has reading `kah`. Add this original MOE citation alongside
  the existing LKK row 227 citation.
- Entry 905 remains `若kah` (`nā-kah`). The maintainer identifies the 甲
  component in 若甲 with the meaning of entry 68, so it also uses romanization.
  Whole-word MOE evidence is 若甲, word 29515, 詞目 row 15429.
- Entry 867 remains `tsíng甲` (`tsíng-kah`). It retains Hanji 甲 in the
  distinct 指甲 word; its MOE evidence is word 5007, 詞目 row 5007. The separate
  unmarked 甲 headword, MOE word 1847, 詞目 row 1848, is distinct from 甲【替】.

The inventory should continue to show both outputs and their supporting words.
The entry `editorial_rationale` fields carry these explicit decisions so they
remain visible with the evidence in the report.

## Record handling

Preserve all six entry IDs, canonical readings, existing original citations and
`imported` statuses. This review resolves the component spellings; it does not
perform a broader review-status migration. Add the verified whole-word MOE
citations to entries 25 and 174 and the 甲【替】 citation to entry 68. Source
snapshots remain byte-for-byte unchanged. The canonical formatter owns entry
renames; no new entries or IDs are allocated.

The read-only inventory command and report are documented in
[the maintenance commands](../tools/README.md#han-lo-combo-inventory).
