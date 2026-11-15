# MOE appendix exclusion beyond 外來詞 — 2026-11-15

The maintainer confirmed that only the MOE `外來詞` appendix (`詞目類型 = 附錄`, `分類 = 外來詞`) belongs in lexicon discovery and imports. All other `詞目類型 = 附錄` categories are excluded:

- Place, station, and landmark appendices (`山脈`, `文教處所`, railway/MRT/light-rail stations including three empty-`分類` Kaohsiung MRT rows, administrative divisions, `海港`, `河川`, `廟宇`, `舊地名`).
- `節氣` (24 solar terms).
- `百家姓` (`全部,<strokes>`) and `俗諺` (`全部,首字<strokes>`).

## Workflow enforcement

- [`decode_moe`](../tools/lexicon.py) and `read_decoded_moe` now preserve `entry_type` (`詞目類型`) and `category` (`分類`) on decoded MOE records across `詞目` and reading sheets linked by `詞目id`.
- `is_excluded_moe_appendix` filters out non-`外來詞` `附錄` entries in:
  - [`dictionary_index`](../tools/harvest_hanji.py) (pure-Hanji discovery),
  - [`RelatedMoeIndex`](../tools/lexicon.py) (combo-matched related-word discovery), and
  - [`build_lookups`](../tools/tsbp/moe_context.py) (TSBP Roman/mixed-script discovery).
- Direct offline dictionary lookups (`query --moe`, `check`) retain full MOE records for auditability.

## Removed entries

Thirty-eight previously imported `machine-reviewed` entries sourced from non-`外來詞` `附錄` rows were removed from `entries/`, keeping `id-sequence.toml` monotonic at `5392`:

- **Railway / MRT stations (9)**: `2433` 蘆洲, `2473` 宜蘭, `2485` 長榮大學, `2506` 沙崙, `2616` 沙崙線, `2953` 十字路, `5353` 新竹, `5354` 嘉義, `5355` 路竹.
- **Administrative divisions (8)**: `3561` 光復鄉, `3796` 高雄市, `3994` 路竹區, `4169` 後壁區, `4395` 嘉義縣, `4467` 新北市, `4638` 民雄鄉, `5283` 宜蘭縣.
- **Old place names `舊地名` (8)**: `3277` 艋舺, `3298` 五股坑, `3299` 洄瀾, `3562` 三角湧, `4170` 田中ng, `4171` 後壁厝, `4172` ka-lé關, `4173` kap仔難.
- **Landmarks / geography (5)**: `2589` 阿里山 (`山脈`), `3560` 觀音山 (`山脈`), `3993` 美術館 (`文教處所`), `2954` 曾文溪 (`河川`), `2955` 代天府 (`廟宇`).
- **Surnames `百家姓` (6)**: `3723` 邱, `3724` 秦, `3725` 郝, `3726` 廖, `3727` 蔡, `3728` 蘇.
- **Solar terms `節氣` (2)**: `5246` 驚蟄, `5352` 穀雨.

The 171 committed `外來詞` entries ([MOE loanword appendix, 2026-10-22](moe-loanword-appendix-import-2026-10-22.md)) remain unchanged.
