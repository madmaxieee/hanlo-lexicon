# TSBP discovery and review

These scripts harvest Roman and mixed-script candidates from a local normalized
TSBP JSONL corpus and generate a standalone HTML review. The corpus is read-only;
generated artifacts stay in a separate local pilot output directory outside
version control.

Use the project-local [review-tsbp-roman skill](../../.agents/skills/review-tsbp-roman/SKILL.md)
for harvesting, contextual model screening, review exports, source mappings and
authorized imports. Its [review controls reference](../../.agents/skills/review-tsbp-roman/references/review-interface.md)
covers MOE selection, custom handling, exclusions and presentation refreshes.
For command-line options, run the relevant Python script with `--help`.

## Tests

```sh
python3 -m unittest discover -s tools/tsbp -v
CONVERTER_ROOT=/path/to/taigi-converter \
  node --test tools/tsbp/test_written_forms.mjs tools/tsbp/test_normalize.mjs
```

Tests use temporary fixtures and mocked local browser state; they do not need a
corpus or a generated review. The Node normalization test needs the converter
checkout. Core maintenance tests remain `python3 -m unittest discover -s tests -v`.

Run the UI, layout and screening regression tests without a converter checkout:

```sh
node --test tools/tsbp/test_written_forms.mjs tools/tsbp/test_review_layout.mjs tools/tsbp/test_screen.mjs
```
