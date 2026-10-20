"""Extract romanized anchors and source-preserving contexts for human review."""

import argparse
import bisect
from collections import defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tomllib
import unicodedata

from moe_context import enrich


BOUNDARY = re.compile(r"[，,。！？!?；;：:、\n]+")


def key(text):
    return unicodedata.normalize("NFC", text).casefold()


def latin(char):
    return "LATIN" in unicodedata.name(char, "")


def preferred_index(root):
    spec = importlib.util.spec_from_file_location('preferred_form_lexicon', root / 'tools/lexicon.py')
    lexicon = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lexicon)
    records = []
    for path in lexicon.entry_files(root):
        raw = path.read_bytes()
        entry = tomllib.loads(raw.decode("utf-8"))
        pairs = lexicon.spelling_readings(entry)
        records.append({"id": entry["id"], "preferred_form": entry["preferred_form"],
                        **({'hanji_forms': entry['hanji_forms']} if entry.get('hanji_forms') else {}),
                        "written_forms": sorted({form for form, _ in pairs}),
                        "multi_syllable_written_forms": sorted({form for form, reading in pairs
                                                               if len(re.findall(r'[^\s-]+', reading)) >= 2}),
                        "path": str(path.relative_to(root)),
                        "sha256": hashlib.sha256(raw).hexdigest()})
    if not records:
        raise ValueError(f"No lexicon entries found under {root / 'entries'}")
    index = defaultdict(list)
    for record in records:
        for form in record['written_forms']:
            index[key(form)].append(record)
    return records, dict(index)


def apply_final_exclusions(groups, known, preferred):
    """Compare complete final spellings after MOE anchoring; never components."""
    categories = {name: set() for name in ('curated', 'tracked', 'unparseable')}
    for group in groups:
        candidates = {group['key'], *group.get('normalized_forms', [])}
        if group.get('normalized_tl'):
            candidates.add(key(group['normalized_tl']))
        matches = {}
        for candidate in sorted(candidates):
            for record in preferred.get(candidate, []):
                match = matches.setdefault(record['id'], {**record, 'matched_written_forms': []})
                if candidate not in match['matched_written_forms']:
                    match['matched_written_forms'].append(candidate)
        group['dedup_lookup_forms'] = sorted(candidates)
        group['preferred_matches'] = [matches[i] for i in sorted(matches)]
        # Exclusion sets overlap: editable ignores must not erase tracked status.
        if matches:
            categories['tracked'].add(group['key'])
        if group.get('parser_compatible') is False:
            reason, category = 'unparseable', 'unparseable'
        elif matches:
            reason, category = 'tracked_preferred_form', 'tracked'
        elif candidates & known:
            reason, category = 'curated_form', 'curated'
        else:
            reason, category = None, None
        group['exclusion_reason'] = reason
        if category:
            categories[category].add(group['key'])
    return categories['curated'], categories['tracked'], categories['unparseable']


def verified_custom_resolutions(path, records, root):
    """Publish handled requests only while the recorded entry still supports them."""
    if not path.exists() or root is None:
        return []
    resolutions = json.loads(path.read_text())
    if not isinstance(resolutions, list):
        raise ValueError('Handled custom requests must be a JSON array')
    by_id = {record['id']: record for record in records}
    result = []
    for row in resolutions:
        if not isinstance(row, dict) or not all(field in row for field in (
                'anchor_key', 'prompt', 'entry_id', 'preferred_form', 'canonical_tl')):
            raise ValueError('A handled custom request needs its exact prompt and entry identity')
        record = by_id.get(row['entry_id'])
        if record is None:
            continue
        entry = tomllib.loads((root / record['path']).read_text())
        if (entry['preferred_form'], entry['canonical_tl']) == (row['preferred_form'], row['canonical_tl']):
            result.append(row)
    return result


def spans(text):
    """Keep diacritics, numeric tones, nasalization and neutral-tone hyphens intact."""
    i = 0
    while i < len(text):
        neutral_prefix = (text.startswith("--", i) and i + 2 < len(text)
                          and latin(text[i + 2]) and (i == 0 or text[i - 1] != "-"))
        if not latin(text[i]) and not neutral_prefix:
            i += 1
            continue
        start = i
        i += 3 if neutral_prefix else 1
        while i < len(text):
            char = text[i]
            if latin(char) or unicodedata.category(char).startswith("M") or char in "0123456789":
                i += 1
            elif char == "-":
                after = i
                while after < len(text) and text[after] == "-":
                    after += 1
                if after < len(text) and latin(text[after]):
                    i = after
                else:
                    break
            elif char in "'’" and i + 1 < len(text) and latin(text[i + 1]):
                i += 1
            else:
                break
        yield start, i


def clauses(text):
    start = 0
    for match in BOUNDARY.finditer(text):
        if match.start() > start:
            yield start, match.start()
        start = match.end()
    if start < len(text):
        yield start, len(text)


def cluster_edges(text, start, end):
    return [start] + [i for i in range(start + 1, end)
                      if not unicodedata.category(text[i]).startswith("M")] + [end]


def excluded_context_spans(text, phrases):
    found = []
    for phrase in phrases:
        if not phrase:
            raise ValueError('Context exclusions must not contain an empty phrase')
        start = text.find(phrase)
        while start >= 0:
            found.append({'phrase': phrase, 'start': start, 'end': start + len(phrase)})
            start = text.find(phrase, start + 1)
    return sorted(found, key=lambda row: (row['start'], row['end'], row['phrase']))


def review_regions(text, blocked):
    ranges = merged((row['start'], row['end']) for row in blocked)
    for cs, ce in clauses(text):
        cursor = cs
        for start, end in ranges:
            if end <= cs:
                continue
            if start >= ce:
                break
            if cursor < start:
                yield cursor, min(start, ce)
            cursor = max(cursor, end)
        if cursor < ce:
            yield cursor, ce


def occurrences(doc, radius, excluded_contexts=()):
    text = doc["text"]
    blocked = excluded_context_spans(text, excluded_contexts)
    source_anchors = list(spans(text))
    for cs, ce in review_regions(text, blocked):
        clause = text[cs:ce]
        edges = cluster_edges(text, cs, ce)
        anchors = [(a, b) for a, b in source_anchors if cs <= a < b <= ce]
        for a, b in anchors:
            left = edges[max(0, bisect.bisect_left(edges, a) - radius)]
            right = edges[min(len(edges) - 1, bisect.bisect_left(edges, b) + radius)]
            for neighbor_start, neighbor_end in anchors:
                if neighbor_start < left < neighbor_end:
                    left = neighbor_start
                if neighbor_start < right < neighbor_end:
                    right = neighbor_end
            while left < a and text[left].isspace():
                left += 1
            while right > b and text[right - 1].isspace():
                right -= 1
            anchor = text[a:b]
            yield {
                "anchor": anchor, "key": key(anchor), "document_id": doc["id"],
                "title": doc["metadata"]["title"], "url": doc["metadata"]["original_url"],
                "anchor_start": a, "anchor_end": b,
                "context_start": left, "context_end": right,
                "snippet": text[left:right], "clause": clause,
                "clause_start": cs, "clause_end": ce,
                "line": text.count("\n", 0, a) + 1,
                "offset_unit": "Unicode code points in normalized corpus text",
                "mixed_clause": any("\u3400" <= c <= "\u9fff" or "\U00020000" <= c <= "\U000323af" for c in clause),
                "has_tone_mark": any(unicodedata.category(c).startswith("M")
                                     for c in unicodedata.normalize("NFD", anchor))
                                 or any(c in "123456789" for c in anchor),
            }


def merged(intervals):
    result = []
    for start, end in sorted(intervals):
        if result and start <= result[-1][1]:
            result[-1][1] = max(result[-1][1], end)
        else:
            result.append([start, end])
    return result


def coverage(rows, texts, field):
    intervals = defaultdict(list)
    for row in rows:
        intervals[row["document_id"]].append((row[f"{field}_start"], row[f"{field}_end"]))
    return sum(len(texts[doc][start:end]) for doc, ranges in intervals.items()
               for start, end in merged(ranges))


def metrics(groups, texts, known):
    groups = [g for g in groups if g["key"] not in known]
    rows = [row for g in groups for row in g["occurrences"]]
    total = sum(map(len, texts.values()))
    compact = sum(len(g["occurrences"][0]["snippet"]) for g in groups)
    context = coverage(rows, texts, "context")
    clause = coverage(rows, texts, "clause")
    return {"article_count": len(texts), "source_characters": total,
            "candidate_groups": len(groups), "anchor_occurrences": len(rows),
            "compact_review_characters": compact,
            "compact_review_retained_pct": round(100 * compact / total, 2),
            "compact_review_reduction_pct": round(100 * (1 - compact / total), 2),
            "all_contexts_union_characters": context,
            "all_contexts_union_retained_pct": round(100 * context / total, 2),
            "all_contexts_union_reduction_pct": round(100 * (1 - context / total), 2),
            "full_clauses_union_characters": clause,
            "full_clauses_union_retained_pct": round(100 * clause / total, 2)}


def review_page(payload):
    data = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    return '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TSBP issue review</title>
<style>
body{font:16px/1.6 system-ui,sans-serif;max-width:1250px;margin:auto;padding:32px;color:#202833;background:#f6f7f9}
h1{font-size:28px;margin:0}p{max-width:1000px}.muted{color:#626d7c;font-size:14px}
.cards{display:flex;flex-wrap:wrap;gap:12px;margin:20px 0}.card{background:white;border:1px solid #dce1e7;border-radius:8px;padding:14px 20px;min-width:170px}.number{font-size:25px;font-weight:650}
input[type=text],textarea{font:inherit;border:1px solid #bfc8d2;border-radius:5px;padding:8px;box-sizing:border-box}textarea{width:100%;min-height:65px}button{font:inherit;padding:7px 12px;cursor:pointer}#search{width:100%;margin:12px 0}
.custom-handling-editor label{display:block;margin:10px 0}.custom-handling-editor input[type=text],.custom-handling-editor textarea{display:block;width:100%;min-width:0;margin-top:4px}
table{width:100%;border-collapse:collapse;background:white}th,td{text-align:left;vertical-align:top;border-bottom:1px solid #e1e5ea;padding:12px}th{background:#e9eef3;position:sticky;top:0}td:nth-child(2){min-width:130px}mark{background:#ffdf89;border-radius:3px;padding:1px 0}a{color:#165ab0}details{margin-top:6px}summary{cursor:pointer;color:#36638b;font-size:14px}.snippet{font-size:18px;white-space:pre-wrap}.occurrence{padding:12px 0;border-top:1px solid #eee}.known{opacity:.5}.tag{font-size:12px;color:#777}.import-editor{border:1px solid #dce1e7;padding:10px;border-radius:6px;margin:12px 0}.import-editor label{display:block;margin:8px 0}.import-editor input[type=text],.import-editor select{font:inherit;width:100%;padding:6px;box-sizing:border-box}.approve-label{display:block;margin-top:12px}.approval-good{color:#167344}.reading-alt{display:block}button{margin:3px}
</style>
<h1 id="title"></h1>
<p>Review 漢羅合用 candidates with source context and MOE evidence where available. Approve pure romanized anchors using the displayed TL reading and article, or choose an MOE entry and readings.</p>
<div class="cards" id="stats"></div>
<p><strong>Ignore</strong> skips a candidate. <strong>Approve import</strong> approves your chosen spelling and readings. Use <strong>Export review.json</strong> to pass approvals to the import script.</p>
<button id="export-review">Export review.json</button> <button id="load-review">Load review.json</button><input id="review-file" type="file" accept="application/json" hidden>
<p id="review-status" class="muted" role="status"></p>
<details><summary>Extraction method and filters</summary>
<p class="muted">Compact review counts one displayed snippet per retained group. Coverage counts the union of all retained snippet positions across articles, so overlaps count once. Percentages use Unicode code points including whitespace in the 24 normalized article bodies. Titles, controls and source labels are excluded from the reading-size measure. Opening more occurrences adds reading; these figures do not measure vocabulary recall or noise rate.</p>
<p class="muted" id="policy"></p>
<p class="muted" id="normalization"></p>
<p class="muted" id="moe-policy"></p>
<p class="muted" id="context-policy"></p>
</details>
<details id="ignored-settings"><summary>Edit ignored forms</summary>
<label for="known">Exact final anchors, comma or newline separated. Case is ignored; tones and hyphens stay distinct.</label>
<textarea id="known" placeholder="Add ignored forms after reviewing the batch"></textarea>
<button id="apply">Apply ignored forms</button> <button id="download">Download ignored forms</button>
</details>
<label><input id="showKnown" type="checkbox"> Show excluded rows</label>
<input id="search" type="text" placeholder="Search an anchor, snippet, or article title">
<p class="muted" id="count"></p>
<table><thead><tr><th>Ignore</th><th>Anchor / import</th><th>Source context and MOE</th></tr></thead><tbody id="rows"></tbody></table>
<p class="muted">All processing is local. Every romanized span uses the same MOE lookup and anchoring process. Deduplication compares complete final spellings, including normalized TL spellings with Han characters preserved, against tracked preferred forms. Romanized components, inferred Han readings, MOE headwords, canonical readings and aliases do not trigger deduplication. Source files and lexicon entries were not modified.</p>
<script>
const data=PAYLOAD;
WRITTEN_FORM_SCRIPT
REVIEW_SCRIPT
</script></html>'''.replace("WRITTEN_FORM_SCRIPT", Path(__file__).with_name('written_forms.js').read_text()).replace("REVIEW_SCRIPT", Path(__file__).with_name('review.js').read_text()).replace("PAYLOAD", data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--issue", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--known", type=Path)
    parser.add_argument("--exclude-contexts", type=Path, default=None,
                        help="Exact literal context phrases to ignore in every source document")
    parser.add_argument("--lexicon", type=Path, help="Read tracked preferred forms recursively from entries/")
    parser.add_argument("--normalization", type=Path, help="Output from normalize_anchors.mjs")
    parser.add_argument("--moe", action="store_true", help="Look up the pinned MOE dictionary and match mixed-form contexts")
    parser.add_argument("--radius", type=int, default=6)
    args = parser.parse_args()
    if args.moe and not (args.lexicon and args.normalization):
        raise ValueError("MOE lookup requires --lexicon and --normalization")
    if args.exclude_contexts is None:
        args.exclude_contexts = args.out / 'excluded-contexts.json'
    known = {key(s) for s in json.loads(args.known.read_text())} if args.known else set()
    excluded_contexts = json.loads(args.exclude_contexts.read_text()) if args.exclude_contexts.exists() else []
    if not isinstance(excluded_contexts, list) or any(not isinstance(s, str) or not s for s in excluded_contexts):
        raise ValueError('Context exclusions must be a JSON array of nonempty exact phrases')
    records, preferred = preferred_index(args.lexicon) if args.lexicon else ([], {})
    custom_resolutions = verified_custom_resolutions(
        args.out / 'handled-custom-requests.json', records, args.lexicon)
    normalization = json.loads(args.normalization.read_text()) if args.normalization else None
    normalized = {row["anchor"]: row for row in normalization["records"]} if normalization else {}
    content = args.corpus.read_bytes()
    tagged = [json.loads(line) for line in content.splitlines()
              if f'issue:{args.issue}'.encode() in line]
    tagged = [d for d in tagged if f"issue:{args.issue}" in d["metadata"]["tags"]]
    catalog = [d for d in tagged if re.fullmatch(r"台文通訊BONG報\s*\d+\s*期", d["metadata"]["title"])]
    docs = [d for d in tagged if d not in catalog]
    if not docs:
        raise SystemExit("No articles found for this issue")
    texts = {d["id"]: d["text"] for d in docs}
    groups = defaultdict(list)
    blocked_records, skipped_anchors = [], []
    for doc in docs:
        blocked = excluded_context_spans(doc['text'], excluded_contexts)
        blocked_records.extend({**row, 'document_id': doc['id'], 'url': doc['metadata']['original_url']} for row in blocked)
        rows = list(occurrences(doc, args.radius, excluded_contexts))
        retained_positions = {(row['anchor_start'], row['anchor_end']) for row in rows}
        if blocked:
            skipped_anchors.extend(row for row in occurrences(doc, args.radius)
                                   if (row['anchor_start'], row['anchor_end']) not in retained_positions)
        for row in rows:
            groups[row["key"]].append(row)
    grouped = [{"key": k, "display": rows[0]["anchor"], "occurrences": rows,
                "article_count": len({o["document_id"] for o in rows})}
               for k, rows in groups.items()]
    for group in grouped:
        # Prefer a representative with Han context, preserving corpus order on ties.
        group["occurrences"].sort(key=lambda row: -sum("\u3400" <= c <= "\u9fff" for c in row["snippet"]))
    grouped.sort(key=lambda g: (-len(g["occurrences"]), g["key"]))
    baseline = metrics(grouped, texts, set())
    if normalization and set(normalized) != {g["key"] for g in grouped}:
        raise ValueError("Normalization input does not cover exactly the current anchors; rerun normalize_anchors.mjs")
    for group in grouped:
        source_key = group["key"]
        norm = normalized.get(source_key, {})
        group["normalized_tl"] = norm.get("normalized_tl")
        group["parser_compatible"] = norm.get("parseable")
        group["normalization_errors"] = norm.get("errors", [])
        group['preferred_matches'] = []
        group['exclusion_reason'] = None
    roman_grouped = grouped
    moe, moe_lookups = None, None
    covered_singles = []
    if args.moe:
        tracked_multi = {key(form) for record in records for form in record['multi_syllable_written_forms']}
        grouped, moe, moe_lookups = enrich(grouped, texts, args.lexicon, tracked_multi)
        covered_singles = moe.pop('covered_single_syllable_audit', [])
    curated, tracked, unparseable = apply_final_exclusions(grouped, known, preferred)
    effective = curated | tracked | unparseable
    def excluded_counts(forms):
        matches = [g for g in grouped if g["key"] in forms]
        return {"matched_groups": len(matches), "occurrences": sum(len(g["occurrences"]) for g in matches)}
    summary = {"issue": args.issue, "radius_base_characters": args.radius,
               "corpus_path": str(args.corpus.resolve()),
               "corpus_sha256": hashlib.sha256(content).hexdigest(),
               "excluded_catalog_ids": [d["id"] for d in catalog],
               "known_forms": sorted(known), "baseline": baseline,
               "handled_custom_requests": custom_resolutions,
               "context_exclusions": {'phrases': excluded_contexts, 'source_matches': len(blocked_records),
                                      'skipped_anchor_occurrences': len(skipped_anchors),
                                      'matching': 'exact literal, case-sensitive; before extraction and MOE lookup',
                                      'configuration': str(args.exclude_contexts.resolve())},
               "tracked_preferred_forms": sorted(tracked),
               "unparseable_forms": sorted(unparseable),
               "normalization": {**normalization["converter"],
                                 "changed_groups": sum(g["normalized_tl"] is not None and g["normalized_tl"] != g["key"] for g in roman_grouped)} if normalization else None,
               "moe": moe, "dedup_stage": "after_moe_all_supported_anchors",
               "regrouped_baseline": metrics(grouped, texts, set()),
               "lexicon_root": str(args.lexicon.resolve()) if args.lexicon else None,
               "lexicon_entry_count": len(records), "lexicon_inventory": records,
               "exclusions": {"curated_form": {**excluded_counts(curated), "forms": sorted(known)},
                              "tracked_preferred_form": {**excluded_counts(tracked),
                                  "eligible_preferred_forms": len(preferred), "forms": sorted(tracked)},
                              "unparseable": {**excluded_counts(unparseable), "forms": sorted(unparseable)}},
               "curated_only": metrics(grouped, texts, curated),
               "filtered": metrics(grouped, texts, effective),
               "article_inventory": [{"id": d["id"], "title": d["metadata"]["title"],
                                      "url": d["metadata"]["original_url"],
                                      "characters": len(d["text"])} for d in docs]}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'covered-single-audit.json').write_text(json.dumps(covered_singles, ensure_ascii=False, indent=2) + '\n')
    (args.out / "context-exclusion-audit.json").write_text(json.dumps({'source_spans': blocked_records, 'skipped_anchors': skipped_anchors}, ensure_ascii=False, indent=2) + '\n')
    with (args.out / "occurrences.jsonl").open("w") as out:
        for group in grouped:
            for row in group["occurrences"]:
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
    group_text = json.dumps(grouped, ensure_ascii=False, indent=2) + "\n"
    (args.out / "groups.json").write_text(group_text)
    summary["review_groups_sha256"] = hashlib.sha256(group_text.encode()).hexdigest()
    (args.out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    (args.out / "roman-groups.json").write_text(json.dumps(roman_grouped, ensure_ascii=False, indent=2) + "\n")
    if moe_lookups is not None:
        (args.out / "moe-lookup.json").write_text(json.dumps(moe_lookups, ensure_ascii=False, indent=2) + "\n")
    exclusions = [{"anchor": g["key"], "reason": g["exclusion_reason"],
                   "occurrences": len(g["occurrences"]), "article_count": g["article_count"],
                   "preferred_matches": g["preferred_matches"]}
                  for g in grouped if g["exclusion_reason"]]
    (args.out / "exclusions.json").write_text(json.dumps(exclusions, ensure_ascii=False, indent=2) + "\n")
    (args.out / "known-forms.json").write_text(json.dumps(sorted(known), ensure_ascii=False, indent=2) + "\n")
    (args.out / "review.html").write_text(review_page({**summary, "groups": grouped}))
    print(json.dumps({k: summary[k] for k in ("issue", "known_forms", "exclusions", "moe", "baseline", "curated_only", "filtered")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
