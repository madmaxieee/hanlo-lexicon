# TSBP issue 385 batch 3 import

Imported the unchanged maintainer export `review (14).json`: 15 ordinary
nonconflicting approvals created entries 4837–4851. Applied imports persisted the
exported match and segment ignore settings. The explicit custom request added
`íng-tsūn / íng-tsūn` with source-backed Hanji metadata 往陣 as entry 4852.
No LKK/MOE matches were found for that custom request; its article evidence and
maintainer-selected spelling/reading are preserved without claiming MOE inclusion.

Contextual original-dictionary checks resolved two reading overlaps as distinct
words, creating entries with explicit identity notes:

- 4853 `ki`, MOE 吱, 詞目 row 2964: shrill crying/squeaking in
  `ki kah tsiok噪耳--ê`. Existing 枝 (1059, LKK row 303) and 支 (1060,
  LKK row 304) are measure words, not this lexical identity.
- 4854 `tsn̄g`, MOE 旋, 詞目 row 7428: hair whorl in
  `頷頸後壁ê頭毛tsn̄g`. Existing 舐 (1334, LKK row 846) means licking;
  its alternate reading tsn̄g does not establish lexical identity.

Keep existing LKK entry 1018 抓 / jiàu, alternate liàu, LKK row 204,
under the maintainer's standing preference to respect LKK spellings. Do not
create the romanized replacement from the repeated same-word proposal.

All 18 new entries retain imported status. Source snapshots and unrelated entries
are unchanged. Validation and formatting checks pass. No harvest or review-page
regeneration was run. Fresh related discovery, scoped to these 18 IDs and their
recorded two-/three-Hanji forms, is at `.cache/related-moe/tsbp-385-batch3.json`
and its Markdown index. Related suggestions remain pending and were not imported.
