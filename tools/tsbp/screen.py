"""Prepare contextual TSBP screening packets and collect occurrence-level decisions."""

import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def occurrence_id(group, row):
    return json.dumps([group['key'], row['document_id'], row['anchor_start'], row['anchor_end']],
                      ensure_ascii=False, separators=(',', ':'))


def visible_occurrences(groups):
    return {occurrence_id(group, row): (group, row)
            for group in groups if not group.get('exclusion_reason') for row in group['occurrences']}


def verify_inputs(pilot):
    summary = read(pilot / 'summary.json')
    if sha(pilot / 'groups.json') != summary['review_groups_sha256']:
        raise ValueError('Candidate fingerprint changed; rerun the harvest')
    if sha(Path(summary['corpus_path'])) != summary['corpus_sha256']:
        raise ValueError('Corpus fingerprint changed; rerun the harvest')
    return summary, read(pilot / 'groups.json')


def prepare(pilot, out, packet_size):
    if not 1 <= packet_size <= 150:
        raise ValueError('Packet size must be between 1 and 150 occurrences')
    if (out / 'manifest.json').exists():
        raise ValueError('Use a new screening run directory; existing packets must not be overwritten')
    summary, groups = verify_inputs(pilot)
    inventory = {a['id'] for a in summary['article_inventory']}
    docs = {d['id']: d for d in (json.loads(line) for line in Path(summary['corpus_path']).read_text().splitlines())
            if d['id'] in inventory}
    candidates = []
    for identity, (group, row) in visible_occurrences(groups).items():
        doc = docs[row['document_id']]
        text = doc['text']
        start, end = row['anchor_start'], row['anchor_end']
        if not 0 <= start < end <= len(text) or text[start:end] != row['anchor']:
            raise ValueError('Occurrence differs from its literal corpus span')
        left, right = max(0, start - 160), min(len(text), end + 160)
        options = [{'id': w['id'], 'headword': w['headword'],
                    'readings': [{'reading': r['reading'], 'definitions': r.get('definitions', [])}
                                 for r in w['readings']]} for w in group.get('review_words', [])]
        candidates.append({'occurrence_id': identity, 'anchor_key': group['key'],
                           'anchor': row['anchor'], 'normalized_tl': group.get('normalized_tl'),
                           'document_id': doc['id'], 'start': start, 'end': end,
                           'title': doc['metadata']['title'], 'url': doc['metadata']['original_url'],
                           'context_start': left, 'context_end': right,
                           'anchor_in_context': [start - left, end - left],
                           'context': text[left:right], 'dictionary_options': options})
    if not candidates:
        raise ValueError('No visible occurrences to screen')
    packets = []
    (out / 'packets').mkdir(parents=True)
    (out / 'reviews').mkdir()
    for offset in range(0, len(candidates), packet_size):
        rows = candidates[offset:offset + packet_size]
        name = f'packet-{len(packets) + 1:03d}.jsonl'
        path = out / 'packets' / name
        path.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows))
        packets.append({'file': name, 'sha256': sha(path),
                        'occurrence_ids': [r['occurrence_id'] for r in rows]})
    manifest = {'schema_version': 1, 'pilot': str(pilot), 'issue': summary['issue'],
                'corpus_sha256': summary['corpus_sha256'], 'groups_sha256': summary['review_groups_sha256'],
                'helper_sha256': sha(Path(__file__)), 'occurrences': len(candidates),
                'groups': len({r['anchor_key'] for r in candidates}), 'packets': packets,
                'scope': 'Contextual screening of every initially visible occurrence; no import approvals'}
    write(out / 'manifest.json', manifest)
    return {'run': str(out), 'groups': manifest['groups'], 'occurrences': len(candidates), 'packets': len(packets)}


def validate_report(report, groups, issue, corpus_sha256, groups_sha256):
    if (report.get('schema_version'), report.get('issue'), report.get('corpus_sha256'), report.get('groups_sha256')) != (
            1, issue, corpus_sha256, groups_sha256):
        raise ValueError('Screening belongs to another issue, corpus or candidate fingerprint; prepare a fresh run')
    expected = visible_occurrences(groups)
    decisions = report.get('decisions')
    if not isinstance(decisions, list):
        raise ValueError('Screening decisions must be an array')
    seen = set()
    for row in decisions:
        identity = row.get('occurrence_id')
        if identity not in expected or identity in seen:
            raise ValueError('Unknown or duplicate screened occurrence')
        if row.get('decision') not in {'keep', 'hold', 'reject'}:
            raise ValueError('Unknown screening decision')
        if any(not isinstance(row.get(field), str) or not row[field].strip() for field in ('reason', 'model')):
            raise ValueError('Every screened occurrence needs its reason and reviewer model')
        seen.add(identity)
    if seen != set(expected):
        raise ValueError('Screening must cover every initially visible occurrence')
    return {row['occurrence_id']: row for row in decisions}


def apply_screening(groups, report, issue, corpus_sha256, groups_sha256):
    decisions = validate_report(report, groups, issue, corpus_sha256, groups_sha256)
    result = copy.deepcopy(groups)
    for group in result:
        if group.get('exclusion_reason'):
            continue
        kept, rejected = [], []
        for row in group['occurrences']:
            verdict = decisions[occurrence_id(group, row)]
            row['machine_screening'] = {k: verdict[k] for k in ('decision', 'reason', 'model')}
            (rejected if verdict['decision'] == 'reject' else kept).append(row)
        if not kept:
            group['exclusion_reason'] = 'machine_rejected'
        else:
            group['occurrences'] = kept
            group['article_count'] = len({r['document_id'] for r in kept})
            if rejected:
                group['machine_rejected_occurrences'] = rejected
    return result


def load_screening(pilot, summary, groups):
    info = summary.get('machine_screening')
    if not info:
        return groups
    path = pilot / 'machine-screen.json'
    if sha(path) != info['sha256']:
        raise ValueError('Screening artifact changed; regenerate the review')
    return apply_screening(groups, read(path), summary['issue'], summary['corpus_sha256'], summary['review_groups_sha256'])


def collect(run, output):
    manifest = read(run / 'manifest.json')
    if sha(Path(__file__)) != manifest['helper_sha256']:
        raise ValueError('Screening helper changed; prepare a fresh run')
    summary, groups = verify_inputs(Path(manifest['pilot']))
    decisions = []
    for packet in manifest['packets']:
        if sha(run / 'packets' / packet['file']) != packet['sha256']:
            raise ValueError('Screening packet changed')
        path = run / 'reviews' / packet['file'].replace('.jsonl', '.review.jsonl')
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        header = rows[0] if rows else {}
        if (header.get('packet_file'), header.get('packet_sha256')) != (packet['file'], packet['sha256']):
            raise ValueError('Review header does not match its sealed packet')
        if not isinstance(header.get('model'), str) or not header['model'].strip():
            raise ValueError('Packet reviewer model is required')
        if {r.get('occurrence_id') for r in rows[1:]} != set(packet['occurrence_ids']):
            raise ValueError('Incomplete or wrong packet decisions')
        decisions.extend({**r, 'model': header['model']} for r in rows[1:])
    report = {k: manifest[k] for k in ('schema_version', 'issue', 'corpus_sha256', 'groups_sha256', 'scope')}
    report.update(manifest_sha256=sha(run / 'manifest.json'), decisions=decisions)
    validate_report(report, groups, summary['issue'], summary['corpus_sha256'], summary['review_groups_sha256'])
    write(output, report)
    return {'output': str(output), 'decisions': dict(Counter(r['decision'] for r in decisions))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--pilot', type=Path, required=True)
    prep.add_argument('--out', type=Path, required=True)
    prep.add_argument('--packet-size', type=int, default=75)
    finish = sub.add_parser('collect')
    finish.add_argument('--run', type=Path, required=True)
    finish.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = (prepare(args.pilot.resolve(), args.out.resolve(), args.packet_size) if args.command == 'prepare'
              else collect(args.run.resolve(), args.out.resolve()))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
