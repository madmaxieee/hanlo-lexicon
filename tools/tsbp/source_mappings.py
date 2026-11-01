"""Persist explicit whole-word source-spelling decisions; never infer component rules."""
import argparse
import json
from pathlib import Path
import unicodedata


def key(value):
    return unicodedata.normalize('NFC', value).casefold()


def verified_mappings(rows, records):
    by_id = {r['id']: r for r in records}
    active, stale = [], []
    seen = set()
    for row in rows:
        if (not isinstance(row, dict) or not isinstance(row.get('source_form'), str)
                or not row['source_form'].strip() or type(row.get('entry_id')) is not int
                or not all(isinstance(row.get(f), str) and row[f] for f in ('preferred_form', 'canonical_tl'))):
            raise ValueError('Source mappings require a whole source form and explicit target identity')
        form = key(row['source_form'])
        if form in seen:
            raise ValueError(f'Duplicate source mapping: {form}')
        seen.add(form)
        target = by_id.get(row['entry_id'])
        valid = target and all(target.get(f) == row[f] for f in ('preferred_form', 'canonical_tl'))
        (active if valid else stale).append(row)
    return active, stale


def apply_mappings(groups, rows):
    by_form = {key(r['source_form']): r for r in rows}
    for group in groups:
        # Exact whole anchor only: no substring, reading-only, or component matching.
        group['source_mapping'] = by_form.get(key(group['key']))
        if group['source_mapping'] and not group.get('exclusion_reason'):
            group['exclusion_reason'] = 'mapped_source_form'


def main():
    from harvest import preferred_index
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--pilot', type=Path, required=True)
    parser.add_argument('--mappings', type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    path = args.mappings or args.root / 'decisions/tsbp-source-mappings.json'
    rows = json.loads(path.read_text()) if path.exists() else []
    bundle = json.loads(args.review.read_text())
    summary = json.loads((args.pilot / 'summary.json').read_text())
    import hashlib
    content = (args.pilot / 'groups.json').read_bytes()
    if (bundle.get('schema_version') != 1 or bundle.get('issue') != summary['issue']
            or bundle.get('corpus_sha256') != summary['corpus_sha256']
            or bundle.get('groups_sha256') != hashlib.sha256(content).hexdigest()):
        raise ValueError('Review does not match this pilot; regenerate and review again')
    groups = {g['key']: g for g in json.loads(content)}
    removals = {key(form) for form in bundle.get('source_mapping_removals', [])}
    if removals - groups.keys():
        raise ValueError('Removed mapping must be a whole anchor in this pilot')
    rows = [r for r in rows if key(r['source_form']) not in removals]
    additions = bundle.get('source_mappings', [])
    for row in additions:
        group = groups.get(key(row['source_form']))
        if group is None:
            raise ValueError('Mapped source form is not a whole anchor in this pilot')
        previous = next((r for r in rows if key(r['source_form']) == key(row['source_form'])), None)
        if previous and any(previous[f] != row[f] for f in ('entry_id', 'preferred_form', 'canonical_tl')):
            raise ValueError('Conflicting saved mapping; resolve the existing decision explicitly')
        if not previous:
            rows.append({**row, 'issue': summary['issue'], 'corpus_sha256': summary['corpus_sha256'],
                         'sources': [{k: o[k] for k in ('document_id', 'url', 'line', 'anchor_start', 'anchor_end', 'anchor')}
                                     for o in group['occurrences']]})
    records, _ = preferred_index(args.root)
    _, stale = verified_mappings(rows, records)
    if stale:
        raise ValueError('Mapping target changed or disappeared; review the saved decisions')
    print(json.dumps({'mapping_count': len(rows), 'path': str(path), 'applied': args.apply}, indent=2))
    if args.apply:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(sorted(rows, key=lambda r: key(r['source_form'])), ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
