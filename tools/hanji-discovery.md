# Pure-Hanji corpus discovery

[Maintenance guide](README.md) · [Terminology](../GLOSSARY.md)

Run commands from the repository root.

## Pure-Hanji corpus discovery

`harvest_hanji.py` makes a read-only report using the same checksum-pinned MOE
loader. It does not approve/import entries, change review statuses, or add corpus
observations to the recommendation inventory. It needs no converter or third-party
Python packages. Write reports outside the repository or in its ignored `.cache/`:

```sh
python3 tools/harvest_hanji.py \
  --corpus /path/to/tsbp.jsonl --issue 390 \
  --out .cache/hanji-harvest/tsbp-390
python3 tools/harvest_hanji.py \
  --corpus /path/to/corpus.jsonl --out /path/to/hanji-report
python3 tools/harvest_hanji.py \
  --corpus /path/to/article.txt --format text --out /path/to/hanji-report
```

The default input is UTF-8 JSONL with one object per line: required nonempty string
`id` and string `text`, and optional `metadata` containing `title`, `original_url`,
and string-array `tags`. Text-only corpus exports with `{id, text}` also work.
IDs must be unique within the selected documents. Text is never normalized or
rewritten; offsets count Unicode code points in the exact decoded `text`,
including supplementary Han characters, combining marks, and CR/LF. The corpus
file SHA-256 covers the entire input, including unselected records.

With no filters, all documents are processed. Repeat `--tag TAG` to require all
specified tags. `--issue N` additionally requires the exact `issue:N` tag and
omits TSBP catalog titles of the form `台文通訊BONG報 N 期`. These filters require
JSONL. `--radius N` controls literal context length (default 12 code points on each
side, extended to avoid splitting combining marks). `--lexicon PATH` selects an
entry/reference root; it defaults to this repository. `--exclude-contexts FILE`
accepts a JSON array of exact, case-sensitive literal phrases, omitting every match
that intersects one. Exclusions do not join text or create new word boundaries.

### Matching and uncertainty

- A trie finds all literal, contiguous canonical Hanji headwords from numbered
  MOE `詞目` records. Single characters, nested compounds, and crossing overlaps
  remain in the output. Alternate Hanji spellings, names/surnames, and comparison
  rows do not create candidates. An unmatched character is never assigned a
  reading by inference. Romanization, punctuation, and spaces are not traversed.
- Each candidate retains its distinct MOE identity, definitions for review, original
  sheet/row/column references, main readings in source order, and supported alternate,
  colloquial, contracted, and dialect readings. The first main reading supplies a
  canonical filing proposal; it does not establish the article's intended reading.
- Connected overlapping spans form groups. For each character position, the report
  compares **every covering dictionary identity and reading**. Agreement requires
  the same character and tone-preserving reading, including neutral `--` markers.
  A contraction or other unalignable alternative blocks positional agreement.
  This avoids enumerating possible segmentations; it deliberately favors caution
  over excluding interpretations using linguistic context.
- Agreement is **conditional dictionary evidence**. Unknown words remain possible
  even if every source character has dictionary coverage. The report never claims
  that a substring is an independently attested word or that a Han run has a certain
  segmentation. It also does not determine whether a source passage is Taiwanese;
  select the intended corpus/subset before accepting its evidence.

The current recommendation inventory uses only canonical TL, aligns each recorded
`moe_forms` / `hanji_forms` spelling with the preferred writing, and counts each entry
once per combo/output. A contiguous pure-Hanji preferred form can supply its own
Hanji alignment. Contractions and uncertain alignments are skipped with reasons.
Entries marked `rule_generated = true` or `disputed` do not supply recommendations;
`imported` and `machine-reviewed` are not reinterpreted as human review. Conflicting
recommendations retain all supporting entry IDs. Corpus observations never resolve
these conflicts.

### Outputs and review queues

| File | Contents |
| --- | --- |
| `report.md` | Top 50 candidates per review queue and unknown combos with conditional agreement |
| `candidates.json` | Matched MOE identities, readings, counts, reasons, existing-entry candidates, and up to three distinct-text contexts |
| `occurrences.jsonl` | Every literal match, source/context offsets, article link, group ID, and candidate identities |
| `overlap-groups.jsonl` | Isolated, same-span, containment, or crossing groups and position-level alternatives/agreement |
| `combo-inventory.json` | Existing recommendations with supporting entry IDs, conflicts, and skipped alignments |
| `combo-coverage.json` | Conditionally agreeing observed combos, corpus support, and comparison with the existing inventory |
| `summary.json` | Counts, selected article inventory, options/exclusions, corpus/dictionary/tool/entry fingerprints, and policy |

Candidates are ordered by the number of **new conditionally supported combos**,
then distinct text bodies and occurrences. `potential_new_combos` also lists
unknown combos from dictionary readings that may still be ambiguous; these do
not count toward `new_combo_count`. Whole-word readings stay separate from the
position-level inventory evidence.

- `batch_proposal`: at least one match spans an entire contiguous Han run, one MOE
  identity/reading, alignable combos, dictionary agreement at every occurrence,
  no crossing overlap group, and no existing-entry or recommendation conflict.
  Han-run boundaries are structural clues, not proof. This queue still needs
  explicit batch review and the ordinary maintenance checks before any import.
- `agreement_only`: some character/reading evidence agrees, while a whole-word
  proposal remains uncertain. Keep the evidence local rather than import a word
  from a substring match.
- `focused_review`: no usable positional agreement, or a recommendation conflict
  or existing-entry candidate requiring editorial identity review.

Counts describe the selected corpus, not general usage frequency. Raw occurrences
and distinct document IDs are reported separately from distinct text bodies.
Exact duplicate bodies contribute once at each text offset to distinct-text counts;
paraphrases and near-duplicates are not deduplicated. Overlapping matches cannot
multiply a character-position's combo support. Frequency does not choose a
segmentation or reading. Output is deterministic for identical inputs; invalid
input fails before replacing an existing report, and completed files are replaced
atomically one at a time. The corpus, entry data, and original snapshots are unchanged.

Run the behavioral fixture tests with the ordinary maintenance suite:

```sh
python3 -m unittest discover -s tests -v
```

For a contextual quick pass on the complete `batch_proposal` and `agreement_only`
queues, use the project-local [review-hanji skill](../.agents/skills/review-hanji/SKILL.md).
`tools/review_hanji.py prepare --harvest PATH --out PATH` creates sealed review
packets with wider literal contexts and source-line language labels. Lightweight
subagents return recommendations, combo-only evidence, holds, or rejections.
`tools/review_hanji.py collect --run PATH` verifies input freshness, exact candidate
coverage and cited evidence, then writes `review.json` and `review.md`. The quick
pass may relax Han-run boundaries and ignore irrelevant component readings when
context supports a compound. It never imports entries or marks them human-reviewed.
When an import is subsequently authorized, use `machine-reviewed` for its
contextually screened recommendations and retain model and source provenance.
