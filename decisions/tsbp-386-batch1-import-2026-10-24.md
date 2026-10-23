# TSBP issue 386 batch 1 import

The maintainer requested import of `review (10).json`, SHA-256
`fea928d8f831037ad337638851208064e70c1e51b43897bf6a5476d8d0213337`,
and explicitly directed that `uân-nā` be added as an alternate reading of
existing entry 326 `uân-á`. The export contains 57 ordinary approvals and one
structured custom request. Its issue, corpus, candidate, MOE and contextual
screening fingerprints match the issue-386 pilot after the poem exclusion.

The ordinary importer added 53 nonconflicting records, IDs 4224–4276, after
offline existing-entry, LKK and pinned MOE checks. The source-anchor approval
`uân-nā` was removed from the derived automatic-import export to implement the
maintainer's explicit alternate-reading instruction instead of creating a word.
Entry 326 retains its ID, preferred form, canonical reading and `imported`
status, with alternate `uân-nā` and the precise issue-386 article citation added.
LKK row 881 supports the existing word in the “still/as before” sense. The MOE
reading-only hit for 丸仔 is an unrelated word and is not cited for this update.

The initial importer also flagged `khoo` because entry 1056 箍 has the same
reading. The selected MOE word 3692 呼, 詞目 row 3692, describes calling or
summoning. The source says `khoo人客tsiūnn車koh起行`. This is distinct from the
ring/measure-word identity supported by LKK row 296 for entry 1056. Under the
standing homophone rule, the checked maintenance writer added separate entry
4277 `khoo`, retaining the original dictionary/article references and a sourced
identity note. Entry 1056 is unchanged.

The structured custom request supplies `kàn古`, reading `kàn-kóo`, and Hanji
`姦古`. The article literally contains the complete `kàn古` at Unicode code
points 2751:2755, line 64. Offline LKK and MOE checks found no whole-word match.
The normal writer added entry 4278 with `hanji_forms`, without claiming MOE
inclusion. The exact custom request and stable ID are recorded in the pilot's
handled-request journal.

The 56 ordinary/custom batch imports remain `imported`; the language/noise screening does not
establish editorial review of spelling or dictionary sense. All original source
snapshots and preexisting entries except entries 165 and 326 are byte-for-byte unchanged.
The earlier harvester fix in the working copy is preserved unchanged. Validation,
canonical formatting and CSV export pass. The maintainer subsequently requested a local commit; no publication was requested.

## Approved follow-up resolutions

The maintainer explicitly approved both proposed resolutions. The normal writer
repeated the offline checks before creating entry 4279 `lia̍p`. The checked update
to entry 165 adds `--ooh` and its MOE/article references while retaining the ID,
preferred/canonical `ooh`, and `imported` status. No batch approvals remain pending.

| Approval | Existing entry | Evidence and proposed resolution |
| --- | --- | --- |
| `--ooh` / `--ooh`, selected MOE 8172 喔, 詞目 row 8170 | 165 `ooh` / `ooh`, LKK row 460 喔 | Both concern the sentence-final particle. Added `--ooh` as an alternate reading, retaining preferred/canonical `ooh`. |
| `lia̍p` / `lia̍p`, selected MOE 5995 捏, 詞目 row 5994 | 313 `tēnn`, alternate `tīnn`, LKK row 644 捏; separately 3358 粒 / `lia̍p`, MOE 7713 | MOE 5995 describes molding soft material; MOE 5996 describes pinching/squeezing. The source describes shaping a bird's nest with mud. Added separate entry 4279 for MOE 5995 with an explicit identity note; both existing entries remain unchanged. |

The original export, before-import harvest, preview, derived ordinary-import
export, maintenance requests, import results and integrity audit are retained
outside the repository in the issue-386 pilot's
`imports/review-fea928d8f831/` folder. Its `related-suggestions.md` and JSON record
12 additional MOE candidates, including original readings, definitions, source
rows, matching patterns and spelling evidence. They remain separate suggestions;
the ordinary batch did not authorize their import.

## Three individually approved related words

The maintainer subsequently selected `sio連suà`, `止喙ta`, and `kha-sau間仔`.
A fresh related-word report was generated from seed entries 4239 `sio連`, 4240
`喙ta`, and 4255 `kha-sau間`. Only the three corresponding review objects were
approved; other candidates remained pending. The sealed report evidence was not
rewritten. The `import-related` preview repeated offline existing-entry, LKK and
pinned MOE checks; apply allocated these records with `review_status = "reviewed"`
because the maintainer individually selected the complete spellings:

| ID | Preferred form | Dictionary filing reading | Original MOE evidence |
| --- | --- | --- | --- |
| 4280 | 止喙ta | tsí tshuì-ta | Word 1068 止喙焦, 詞目 row 1069 |
| 4281 | sio連suà | sio-liân-suà | Word 5274 相連紲, 詞目 row 5274 |
| 4282 | kha-sau間仔 | kha-sau-king-á | Word 10105 跤梢間仔, 詞目 row 10102 |

The earlier summary's “unresolved” label for 跤梢間仔 concerned missing
間 · king evidence in the pre-import inventory, not the added 仔 · á. The
added component was consistently Hanji already. The current inventory supports
間 · king through entry 4255. Its 跤 · kha position now has both Hanji and
romanized evidence; the maintainer explicitly retains the seed spelling
`kha-sau間` and appends `仔`, resolving that component choice. The readable
summary now identifies the original missing component and the adopted spelling;
the original JSON evidence remains unchanged.

The fresh review, preview and apply reports are retained beside the original
batch artifacts as `related-approved-three.json`, `related-three-preview.json`
and `related-three-import.json`. Validation, canonical formatting and CSV export
pass. These approvals do not authorize the remaining related suggestions.
