# TSBP Roman review controls and refresh

Use these controls in the pilot's `review.html`. Run commands from the repository root.

## MOE selection defaults

The entry/meaning selector lists regular numbered entries with original 詞目
references first. When exactly one such entry matches an anchor, it is selected
by default, even if matching 詞彙比較 rows are also present. Readings in the
original 詞目 cell retain source order. Multiple primary readings are labeled
**MOE primary 1**, **MOE primary 2**, and so on; primary 1 is the default filing
reading. If no primary reading exists, a sole detected reading is the fallback.
Multiple regular entry matches do not get an entry default. An untouched default
preferred spelling follows the selected filing reading when its Roman syllables
can be aligned; ambiguous spellings remain for manual review.
Comparison entries remain available and show their original sheet and row.
Saved entry/reading choices are preserved. Defaults never approve an import.
Selected MOE contractions with fewer syllables remain approvable. Their output
uses the complete contracted romanization, matching the maintenance writer;
the full reading retains the preferred mixed spelling. For example, `查某kán`
with `tsa-bóo-kán` can also export `tsőo-kán`, `tsa̋u-kán` and `tsa̋-kán`.

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

## Review layout and presentation-only refresh

The page groups matches by the original Roman-text **position in an article**.
All candidates triggered by that segment appear together, longest span first;
sections follow the article inventory and source offsets rather than frequency.
A match triggered by two segments joins those local segments into one section.
Repeated spellings in other passages do not join unrelated sections. A word can
appear in several sections, but its decisions remain shared by anchor key and
are exported once. Approving one candidate does not approve its overlapping
alternatives. Search retains the other candidates in any matching section.

Each section shows a literal passage extending about 100 Unicode code points
on either side of the matched area, including punctuation and nearby sentences.
The original Roman segments are highlighted in that passage; each candidate
also highlights its own exact span in a shorter excerpt. Article links, full
clauses, all occurrences and dictionary references remain available.

Each candidate has the same three handling panels: **Import word** (article or
MOE evidence), **Custom handling**, and **Use existing entry**. **Ignore match**
and **Copy note** sit beside its status. For a pending MOE-backed import, its
spelling/reading controls and dictionary evidence open by default. Explicitly
saved fold choices take precedence. Custom fields save while typing;
**Save request and fold** closes that panel. Approving an import folds its
editor. Manually opened or folded panels retain their state when another word
changes, when searching, and across browser reloads. Panel state also travels
in `review.json` as optional `ui_state`; old exports remain loadable.

To update only the HTML presentation after changing these tools:

```sh
python3 tools/tsbp/render_review.py --pilot /path/to/pilot
```

This verifies the existing groups and corpus checksums, reapplies any sealed
language screen, and reads longer literal contexts from that same corpus.
It writes only `review.html`: no extraction, normalization, dictionary lookup,
entry edits, approvals, or fingerprint changes occur. It refreshes short-fragment
coverage from current entries, while retaining the harvest's candidate inventory
and other deduplication decisions. Use a normal harvest separately for new discovery.

### Ignore a whole Roman-text segment

**Ignore this segment** hides every candidate occurrence in that source section.
It applies to those article positions, leaving other occurrences of the same
word available for review. It also clears approvals for the affected words.
Custom request drafts are retained; fully ignored words do not export active
custom requests or approvals. Enable **Show excluded rows** and use **Restore
segment** to undo it. The decision saves locally and travels in the optional
`ignored_segments` array in `review.json`. Import previews validate these positions
against the sealed harvest and exclude them from article evidence. If every
occurrence is ignored or covered by an existing word, import is blocked.

### Refresh compound coverage after an import

Every HTML refresh rechecks short fragments against current compound spellings:

```sh
python3 tools/tsbp/render_review.py --pilot /path/to/pilot
```

This reads current entry recommendations and reuses the harvester's exact
compound-coverage rule with recorded, normalized Roman triggers. It performs no
new extraction or dictionary matching and writes only `review.html`. The corpus,
`groups.json`, summary, source offsets and export fingerprints remain unchanged.
Covered fragments stay inspectable under **Show excluded rows**, with the covering
spelling and entry ID. For example, entry 4741 `--tńg-去` covers `--tńg` only inside
that exact compound; a standalone `--tńg` or `--tńg-來` is not hidden by that entry.
The importer independently rechecks coverage against current entries before
choosing source evidence, so old approvals cannot bypass new compound coverage.

### Remember exclusions across reruns

Applied review imports save both match and segment ignores to the pilot's
`review-settings.json`, scoped to the issue and exact corpus checksum. Rerunning
harvest or refreshing HTML loads this file automatically. Segment decisions are
retained even when their candidates disappear from the queue, so they still apply
if those candidates return. Browser-local edits and restores remain effective.

To recover exclusions from an earlier export without reimporting its approvals:

```sh
python3 tools/tsbp/review_settings.py --review /path/to/review.json --pilot /path/to/pilot
python3 tools/tsbp/render_review.py --pilot /path/to/pilot
```

The settings command accepts exports from an older candidate queue for the same
issue/corpus. It validates segment positions against original Roman spans in that
corpus, rather than requiring those spans to still have pending candidates.
It writes no entries or approvals. Export the review to carry recent browser
choices back into local workflow settings; a static HTML page cannot write that
file directly. An export predating segment ignores preserves the saved segment
settings; an explicit empty `ignored_segments` array clears them.

### Approved words fold in later passages

A word keeps one decision across its passages. After the first passage in review
order, later passages of an approved word collapse to a single row showing the word
and its green **Approved import** status. Select the row to expand that passage,
and **Fold** to collapse it again. Expansion is not saved and changes no decision.

### Browse excluded candidates without loading the entire queue

**Show excluded rows** reveals candidates hidden by match/segment ignores,
tracked preferred spellings or source mappings, longer tracked-word coverage,
parser incompatibility, and language-screen rejection. This changes visibility;
it does not restore, approve, or import anything by itself.

**Ignored segments only** is the default filter when excluded rows are enabled,
so **Restore segment** is easy to find. Select **All rows, including excluded**
to inspect the other exclusion categories.
Both normal and excluded views show 20 Roman-text segments per page. Search
examines the full result set and resets to its first page. Occurrence histories
are built only when opened and initially show 25 rows, with an explicit button
to load more. This prevents common words from duplicating thousands of hidden
source rows across every section.
