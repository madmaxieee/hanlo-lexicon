# TSBP issue 385 batch 2 import

Imported the 57 nonconflicting approvals from the unchanged `review (13).json`
export through the normal offline review importer. Added `傷khî / siong-khî`
as entry 4799 using the article occurrence and MOE component-reading evidence;
no whole-word MOE match or invented Hanji metadata is claimed.

Imported six reviewed custom requests as entries 4800–4805: `--heh` with alternate
`--hennh`, `iap-phiah`, `ka-tsuē`, `lok-sōng`, `lè-táu`, and `mê-mê角角`.
Original source contexts were inspected; custom Hanji metadata is retained without
asserting MOE inclusion. The first has original MOE reading citations.

The maintainer explicitly requested `tsa̋`, `tsa̋u`, `tsőo` as alternate contractions
of entry 1274 `查某 / tsa-bóo`. Added those readings and the issue 385 `tsa̋`
article citation, preserving the existing ID, preferred form and canonical reading.
MOE supplies the canonical reading; the adopted contractions are attributed to
the maintainer rather than falsely claimed as dictionary matches.

Previously imported approvals remain represented by their existing entries;
prior explicit identity resolutions remain in force. Preserve the LKK entry
4334 `ōm` rather than creating another entry from the repeated exact-pair approval.

Conflict resolutions and remaining decision:

- Resolved: add `--looh` and its approved MOE alternate `--loh` to entry 130,
  preserving preferred/canonical `looh` and the LKK source.
- Resolved: replace entry 834's preferred form with `sio疊`, preserving canonical
  `sio-tha̍h` and adopting the approved alternate `sio-thia̍p`. Replace its sources
  with the approved MOE/article evidence, removing the original 2016/08/bong-ue
  article citation as explicitly requested.
- Resolved: add `tng-teh` as another alternate to entry 242, preserving canonical
  `tng-leh`, existing alternate `tng-tih`, preferred spelling and LKK source.
- The new `--lueh` prompt names 落來, while the previous explicit resolution and
  recorded `lueh` contraction belong to entry 808 落--去. That entry already has
  `--lueh`. Do not silently attach the contraction to a different word.

No harvest or review page regeneration was run. Fresh related discovery remains
deferred until these import conflicts are resolved; pre-import checks stay audit
artifacts under `.cache/tsbp-385/`.
