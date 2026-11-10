# Reader-facing export

Generate an LKK-shaped table from the entries and original sources:

```sh
python3 tools/readable.py --corpus /path/to/normalized/tsbp.jsonl
```

The default `dist/readable/` directory contains CSV and JSON. JSON retains field
provenance, corpus/dictionary checksums, coverage and excluded/unresolved rows.
Entry TOML and source snapshots are read-only. CSV contains literal text; when
importing into a spreadsheet, disable conversion of text to formulas/numbers.

The export excludes pure Hanji using the keyboard export's hyphen rule. It keeps
LKK recommendations and entries with at least one recorded corpus span not
strictly contained in another entry's cited span in the same article. This is an
initial overlap filter, not a complete word-boundary or semantic review. Homographs
retain their IDs. Dictionary-only related recommendations stay in the repository.

## Derived fields

- Numeric readings are generated from canonical TL, retaining separators and
  neutral `--` markers. Tone numbers describe the written reading, not tone sandhi.
- Mandarin comes from referenced LKK cells, then MOE `詞彙比較` rows matching
  verified Hanji and a canonical/alternate reading. Multiple explicit mappings
  are retained. Dictionary definitions are not converted into Mandarin glosses.
- Examples prefer a verifiable, uncontained cited corpus occurrence. The excerpt
  is an unchanged line, or a window of up to 240 code points around a longer
  occurrence. Original spelling, including POJ, is preserved. LKK examples and
  examples linked to cited MOE headword IDs are fallbacks. MOE examples are
  dictionary examples; no corpus-specific sense selection is implied.
- `華語出處` and `用例出處` retain snapshot/sheet/row or URL/character coordinates.
  Corpus provenance additionally retains the original locator, document ID,
  excerpt/match spans, and coordinate-text SHA-256 in JSON. Offsets are zero-based,
  end-exclusive Unicode code points. NFC text is tried first, then original text
  for legacy citations. A mismatch is reported and never silently relocated.

Missing evidence leaves a blank. Rebuilding does not generate translations,
rewrite examples, or change review statuses. An excerpt is not a new review.

## Optional shareable workbook

With Node and `@oai/artifact-tool` installed in the execution environment:

```sh
node tools/readable_xlsx.mjs dist/readable
```

`NODE_PATH` can point to an external dependency directory. No package installation
or repository-local dependencies are required by the Python exporter. The renderer
writes `lexicon-readable.xlsx` with text cells, filters, frozen headers and native
MOE/article hyperlinks, plus a preview PNG. Native links are attached with the
standard-library OOXML helper because Artifact Tool lacks native link authoring.
The two source columns appear at the right of the original LKK columns.

Source reuse notices remain in [RIGHTS.md](../RIGHTS.md); generating local output
does not publish it or change source terms.
