# MOE single-character non-word exclusion (`單字不成詞者`) — 2026-11-15

Following [MOE appendix exclusion beyond 外來詞](moe-appendix-exclusion-2026-11-15.md), the maintainer directed that MOE `詞目類型 = 單字不成詞者` records also be excluded from lexicon discovery, matching the non-`外來詞` `附錄` policy. Many bound characters in MOE (including surnames such as `16497` 廖 and `16810` 蔡) appear both in `附錄－百家姓` and as `單字不成詞者` `詞目` rows without definitions.

## Workflow enforcement

- [`is_excluded_moe_discovery_entry`](../tools/lexicon.py) excludes both non-`外來詞` `附錄` rows and `單字不成詞者` rows in:
  - [`dictionary_index`](../tools/harvest_hanji.py) (pure-Hanji discovery), and
  - [`RelatedMoeIndex`](../tools/lexicon.py) (combo-matched related-word discovery).
- [`is_excluded_moe_entry`](../tools/tsbp/moe_context.py) applies the same exclusion in [`build_lookups`](../tools/tsbp/moe_context.py) (TSBP Roman/mixed-script discovery).
- Direct offline dictionary lookups (`query --moe`, `check`) retain full MOE records for auditability.

## Removed and retained entries

Per maintainer decision, the `27` pure-Hanji single-character entries previously imported from `單字不成詞者` rows were removed from `entries/`, keeping `id-sequence.toml` monotonic at `5392`:

- **Removed (`27`)**: `1514` 資, `1517` 怎, `1525` 續, `1552` 最, `1565` 詳, `1943` 姐, `1944` 盼, `1945` 慈, `1946` 碧, `1947` 稱, `1948` 儀, `1949` 遲, `2083` 雖, `2311` 候, `2312` 極, `2472` 蹤, `2588` 罈, `3282` 奉, `3329` 捐, `3364` 揮, `3380` 玄, `3785` 既, `3989` 祈, `4425` 餉, `4819` 冒, `5248` 閩, `5262` 刪.
- **Retained (`4`)**: the Romanized entries `435` `hah` (LKK + TSBP + MOE `哈`), `447` `phiàn`, `4916` `thut`, and `4941` `uâ`.
