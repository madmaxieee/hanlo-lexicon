# Personal curated batch, 2026-10-19

## Scope and inputs

Import both personal lists from 2026-10-18. These files determine batch membership
and requested mappings; entries cite the original dictionaries as evidence.
The personal CSVs are not independent source citations or new source snapshots.

| Input | Headerless pairs | SHA-256 |
| --- | ---: | --- |
| `LKK-romanized-personal-2026-10-18.csv` | 397 | `ecf15b3b7c328102dc3bdf4c227d0192b275b09736a710783cac28ba99e9639d` |
| `LKK-hanji-personal-2026-10-18.csv` | 25 | `d2df2a136834227def99a8cf109a31ba35742d6fa35e32edfb6622c1a8e831b1` |

The result is 362 records with 350 distinct preferred forms. IDs 1 through 10 are
the unchanged pilot; IDs 11 through 362 cover the remaining batch. All records
remain `imported`. There are 420 distinct input/output mappings after the explicit
resolutions below. Homographs can share a mapping without sharing an identity.

## Maintainer resolutions

- Use `leh` (ID 120) as preferred form, with `teh` as an alternate reading. Both source-list
  spellings refer to LKK row 376, which writes `leh/teh`.
- Use `kánn-ná` (ID 112) as preferred form, with `ká-ná` and `kán-ná` as alternate readings.
  Both source-list spellings refer to LKK row 223, which writes `kánn-ná/ká-ná`.
- Use `tshì-môo-thâng` for `刺毛蟲` (ID 362), replacing the CSV's `tshì-môo--thâng`.
  LKK row 766 shows `tshì-môo- thâng`; the pinned MOE `詞目` sheet, row 3617,
  explicitly gives `tshì-môo-thâng`. Cite both sources on the entry.

These choices were confirmed by the maintainer during this import. The first two
consolidations remove two repeated mappings; the reading correction replaces one
mapping. No other input reading or requested output was dropped.

## Source interpretation

Use the requested romanized output as canonical TL when it is also an input
reading. Otherwise use the first reading in the corresponding personal-list
group. This selects a filing reference, not a superior dialect. Preserve all
remaining selected readings as aliases, subject to the resolutions above.

Expand only the source notation needed for the selected list forms:

| Selected forms | LKK row | Original notation |
| --- | ---: | --- |
| `khah-thîng`, `khah-thîng-á` | 257 | `khah-thîng(-á)` |
| `m̄ bat` | 422 | `m̄ bat(無連字符)`; alternate `m̄ pat` |
| `四秀` | 580 | `四秀(仔)`; reading `sì-siù(-á)` |
| `小可` | 577 | `小可(仔)`; reading `sió-khuá(-á)` |
| `敏豆仔` | 61 | `敏豆(仔)`; reading `bín-tāu(-á)` |
| `花眉仔` | 163 | `花眉(仔)`; reading `hue-bî(-á)` |

The selected input readings use hyphens for source reading spaces in `hia ê`,
`tsia ê`, `ah nā`, `kè sī`, and `m̄ bat`/`m̄ pat`. The written output `m̄ bat`
retains its space. Source abbreviation expansions include `liam-mi/pinn`,
`m̄-kò/kù`, and `sih/sinnh-nà`; their full selected readings remain in the entries.
The original snapshot is unchanged.

## Homographs and dictionary checks

Keep the separate source words under `ha̍h`, `kah`, `khau`, `lak`, `thuh`,
`thàng`, `tshuah`, `tsiah`, `tsiânn`, and `tīng` as distinct records. Their
identity notes name the corresponding LKK row and Hanji from its MOE column.
The alias `kap` belongs only to the `kah` record corresponding to `佮` (row 226).

Keep `tiānn-tiānn` (ID 241) as one record citing LKK rows 691 and 692. The pinned MOE
dictionary groups both source senses under record 3837, `定定` / `tiānn-tiānn`.
Different senses or alternate readings alone do not establish unrelated words.

Check every candidate against existing entries, the complete original LKK TSV,
and the checksum-pinned MOE ODS. MOE matches are review evidence and do not veto
an LKK recommendation. Keep dictionary definitions outside entry records.

Populate `moe_forms` from simple LKK MOE-column spellings also found in the pinned
dictionary. Unexpanded optional-suffix notation stays in the source snapshot.
The labels `咦`, `咳啾`, `嗯`, `打合`, and `原仔` were not found by the offline lookup
for the seven corresponding records (`i̋`, `kha-tshiùnn`, `mh`, `m̀`, `ngh`,
`tánn-ha̍p`, and `uân-á`), so their `moe_forms` arrays remain empty. Their LKK
citations still preserve access to the original wording.
