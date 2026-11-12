# Reader-facing export

Generate an LKK-shaped supplement from the entries and original sources:

```sh
python3 tools/readable.py --corpus /path/to/normalized/tsbp.jsonl
```

The default `dist/lkk-supplement/` directory contains CSV and JSON. JSON retains field
provenance, corpus/dictionary checksums, coverage and excluded/unresolved rows.
Entry TOML and source snapshots are read-only. CSV contains literal text; when
importing into a spreadsheet, disable conversion of text to formulas/numbers.

The export lists only preferred forms; accepted forms stay in the keyboard CSV.
It excludes pure Hanji using the keyboard export's hyphen rule. It excludes
original LKK items, identified by an LKK source citation or an exact original
preferred-form/canonical-reading pair. Remaining entries need a recorded corpus span not
strictly contained in another entry's cited span in the same article. This is an
initial overlap filter, not a complete word-boundary or semantic review. Homographs
retain their IDs. Dictionary-only related recommendations stay in the repository.

It also excludes spellings fully reconstructed from unambiguous original LKK
component mappings using the [documented combo alignment rules](combos.md).
Mappings come from literal snapshot recommendations, not later entry spellings
or votes from the supplement itself. Hanji references come from the snapshot's
MOE-Hanji column or exact whole-word spelling/reading dictionary matches. A
homophone alone supplies no mapping. Each component needs exactly one supported
output; conflicts and unknowns retain the word. Every canonical/alternate output
must reconstruct exactly, including neutral markers and standard separators.
An exclusion proof records each component, output, original LKK row and supporting
Hanji source in the JSON audit. Unalignable original rows are separately audited.
This is output filtering, not deletion or a new editorial identity decision.

## Derived fields

- Numeric readings are generated from canonical TL, retaining separators and
  neutral `--` markers. Tone numbers describe the written reading, not tone sandhi.
- Mandarin comes from MOE `詞彙比較` rows matching
  verified Hanji and a canonical/alternate reading. Multiple explicit mappings
  are retained. Where no explicit mapping exists, the column contains the full
  original `義項.解說` definitions linked to the entry's cited MOE headword ID.
  These fallback cells are dictionary explanations rather than concise Mandarin
  equivalents; they are copied without summarization or sense selection. Both
  kinds retain their original sheet/row references in JSON provenance.
- Examples prefer a verifiable, uncontained cited corpus occurrence. The excerpt
  is an unchanged punctuation-bounded clause when at most 64 code points long.
  Longer clauses use 16 code points before the match and 20 after, expanded to
  preserve Roman words and combining marks; a long token can exceed this budget.
  Original spelling, including POJ, is preserved. Examples linked to cited MOE
  headword IDs are fallbacks. MOE examples are
  dictionary examples; no corpus-specific sense selection is implied.
- `用例來源` links to the article or dictionary supplying the example. Exact
  locations and Mandarin source references remain in JSON provenance rather than
  visible columns.
  Corpus provenance additionally retains the original locator, document ID,
  excerpt/match spans, and coordinate-text SHA-256 in JSON. Offsets are zero-based,
  end-exclusive Unicode code points. NFC text is tried first, then original text
  for legacy citations. A mismatch is reported and never silently relocated.
- Only output display cells add `【】` around the cited occurrence and `…` at
  clipped ends. JSON provenance retains `raw_example` without added decorations.
  Shared excerpt extraction, import reports, source locators and entry TOML stay
  literal. Existing source punctuation is preserved.

Missing evidence leaves a blank. Rebuilding does not generate translations,
rewrite examples, or change review statuses. An excerpt is not a new review.

## Optional shareable workbook

With Node and `@oai/artifact-tool` installed in the execution environment:

```sh
node tools/readable_xlsx.mjs dist/lkk-supplement
```

`NODE_PATH` can point to an external dependency directory. No package installation
or repository-local dependencies are required by the Python exporter. The renderer
writes a plain `lexicon-readable.xlsx` with text cells and native hyperlinks for
the MOE page and example source, plus a preview PNG. It uses default
spreadsheet formatting without colors, tables or frozen panes. Native links are attached with the
standard-library OOXML helper because Artifact Tool lacks native link authoring.
The example source column appears at the right of the original LKK columns.

Source reuse notices remain in [RIGHTS.md](../RIGHTS.md); generating local output
does not publish it or change source terms.
