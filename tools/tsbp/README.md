# TSBP discovery and review

These scripts harvest mixed-script candidates from a local normalized TSBP JSONL
corpus and generate a standalone HTML review. The corpus is read-only. Generated
reviews, dictionary lookups, review exports and browser state stay in a separate
pilot output directory, outside version control.

## Harvest and review

From the repository root, supply your local corpus, converter checkout and output
folder. Reuse the same output folder to retain its exact context exclusions and
handled-request journal.

```sh
python3 tools/tsbp/harvest.py \
  --corpus /path/to/tsbp.jsonl --issue 390 \
  --lexicon . --known /path/to/ignored-forms.json --out /path/to/pilot
node tools/tsbp/normalize_anchors.mjs \
  /path/to/taigi-converter /path/to/pilot/roman-groups.json \
  /path/to/pilot/normalization.json
python3 tools/tsbp/harvest.py \
  --corpus /path/to/tsbp.jsonl --issue 390 --lexicon . \
  --known /path/to/ignored-forms.json \
  --normalization /path/to/pilot/normalization.json --moe --out /path/to/pilot
```

Open `/path/to/pilot/review.html`. All readings use the pinned original MOE data
loaded by the maintenance tool. POJ normalization validates complete Roman parts
with the supplied converter. Source offsets and literal contexts are preserved.
Nested and overlapping multi-syllable matches remain separate. A contained single
is suppressed only where a supported MOE or tracked compound covers it; standalone
occurrences remain eligible. Tracked custom mixed forms can provide coverage
without fabricating a MOE compound match.

The optional `excluded-contexts.json` in the output folder is a JSON array of
exact literal phrases; `--exclude-contexts` can select another file. This is
separate from final-anchor Ignore choices. An optional
`handled-custom-requests.json` records exact completed prompts, stable entry IDs,
preferred forms and filing readings. A resolution is embedded only while its
entry still has that preferred form and reading. For structured requests, include
`request_fields` with the exact `preferred_form`, optional `hanji` and `reading`
that were handled; this prevents a changed request from being cleared.

## Custom handling

The Custom handling section accepts:

- **Preferred form** and **Reading (TL)** together.
- **Hanji**, optionally, without claiming MOE inclusion.
- Optional additional instructions, or a free-text-only request as before.

For example, Export review.json records this structured request:

```json
{
  "anchor_key": "liô",
  "prompt": "",
  "anchor_present": true,
  "preferred_form": "liô心",
  "hanji": "𠞭心",
  "reading": "liô-sim"
}
```

The fields and instructions persist locally and survive file restore. Structured
custom requests pause ordinary automatic approval. They are proposals for source,
reading and identity review, including corrections that need an existing-entry
update. Hanji maps to optional `hanji_forms` in the entry proposal; it never
populates `moe_forms` by inference. An omitted Hanji input leaves the optional
entry field absent.

## Preview and import

```sh
python3 tools/tsbp/import_review.py /path/to/review.json \
  --pilot /path/to/pilot --root . --report /path/to/preview.json
python3 tools/tsbp/import_review.py /path/to/review.json \
  --pilot /path/to/pilot --root . --apply --report /path/to/import-result.json
```

The preview validates issue/corpus/candidate fingerprints and selected original
MOE references, then runs offline existing-entry/LKK/MOE checks. Structured custom
requests receive a separate `custom_previews` proposal and dictionary report.
`--apply` imports only explicit ordinary approvals, using the unchanged
maintenance writer, duplicate checks and ID allocation. It does not execute free
text or automatically add custom proposals. Resolve their sources and any
existing-entry identity first, then use `tools/lexicon.py` for the deliberate
addition or update. New entries remain `imported`.

## Tests

```sh
python3 -m unittest discover -s tools/tsbp -v
CONVERTER_ROOT=/path/to/taigi-converter \
  node --test tools/tsbp/test_written_forms.mjs tools/tsbp/test_normalize.mjs
```

Tests use temporary fixtures and mocked local browser state; they do not need a
corpus or a generated review. The Node normalization test needs the converter
checkout. Core maintenance tests remain `python3 -m unittest discover -s tests -v`.
