#!/usr/bin/env python3
"""Prepare sealed Hanji review packets and collect sourced subagent recommendations."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

import harvest_hanji as harvest
import lexicon as lex


DECISIONS = {'recommend_import', 'combo_only', 'hold', 'reject'}


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def read_lines(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def write_json(path, value):
    lex.atomic_write(path, json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')


def output_directory(path, root):
    path = path.resolve()
    if path.is_relative_to(root) and not path.is_relative_to(root / '.cache'):
        raise lex.Error('Write review artifacts outside the repository or under .cache/')
    return path


def verify_harvest(folder, root):
    summary = read_json(folder / 'summary.json')
    corpus = Path(summary['corpus_path'])
    if sha(corpus) != summary['corpus_sha256']:
        raise lex.Error('Corpus changed; rerun the harvest')
    old = {row['path']: row['sha256'] for row in summary['lexicon_entries']}
    now = {str(p.relative_to(root)): sha(p) for p in lex.entry_files(root)}
    if old != now:
        raise lex.Error('Lexicon entries changed; rerun the harvest')
    if sha(Path(harvest.__file__)) != summary['tool_sha256'] or sha(Path(lex.__file__)) != summary['maintenance_tool_sha256']:
        raise lex.Error('Harvest/maintenance tool changed; rerun the harvest')
    pin, _, records = lex.moe_data(root)
    if summary['dictionary'] != {'snapshot': pin['id'], 'sha256': pin['sha256']}:
        raise lex.Error('Pinned dictionary changed; rerun the harvest')
    return summary, corpus, harvest.dictionary_index(records)


def context(row, doc):
    text = doc['text']
    start, end = row['start'], row['end']
    if not (0 <= start < end <= len(text)) or text[start:end] != row['form']:
        raise lex.Error('Occurrence does not match its literal corpus span')
    line_start = text.rfind('\n', 0, start) + 1
    next_break = text.find('\n', end)
    line_end = len(text) if next_break == -1 else next_break
    left, right = max(line_start, start - 100), min(line_end, end + 100)
    return {'occurrence_id': f'{doc["id"]}:{start}:{end}',
            'document_id': doc['id'], 'start': start, 'end': end,
            'title': doc['metadata'].get('title', ''), 'url': doc['metadata'].get('original_url', ''),
            'context_start': left, 'context_end': right, 'text': text[left:right],
            'line_tail': text[max(line_start, line_end - 80):line_end],
            'boundary_aligned': row['boundary_aligned'], 'overlap_kind': row['overlap_kind'],
            'dictionary_combo_agreement': row['dictionary_combo_agreement']}


def prepare(folder, out, root, packet_size=50):
    if packet_size < 1 or packet_size > 200:
        raise lex.Error('packet-size must be between 1 and 200')
    summary, corpus, dictionary = verify_harvest(folder, root)
    out = output_directory(out, root)
    if out == folder:
        raise lex.Error('Use a separate review subdirectory, not the harvest directory itself')
    rows = read_json(folder / 'candidates.json')
    selected = [r for r in rows if r['queue'] in {'batch_proposal', 'agreement_only'}]
    ids = {r['candidate_id'] for r in selected}
    if len(ids) != len(selected) or not selected:
        raise lex.Error('Expected nonempty queues with unique candidate IDs')
    for row in selected:
        original = dictionary.get(row['candidate_id'])
        if original is None or any(row[key] != json.loads(json.dumps(original[key])) for key in original):
            raise lex.Error(f'Candidate {row["candidate_id"]} differs from the pinned dictionary')
    options = summary['options']
    docs = {d['id']: d for d in harvest.corpus_documents(corpus, options['format'], options['tags'], options['issue'])}
    occurrences = defaultdict(list)
    with (folder / 'occurrences.jsonl').open(encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            for identity in set(row['candidate_ids']) & ids:
                if row['form'] != dictionary[identity]['form']:
                    raise lex.Error('Occurrence/candidate spelling mismatch')
                occurrences[identity].append(row)
    packets = []
    input_files = [folder / n for n in ('summary.json', 'candidates.json', 'occurrences.jsonl')]
    if corpus in {(out / 'manifest.json').resolve(), (out / 'review.json').resolve()}:
        raise lex.Error('Review output would overwrite its corpus input')
    for offset in range(0, len(selected), packet_size):
        records = []
        for row in selected[offset:offset + packet_size]:
            ranked = sorted(occurrences[row['candidate_id']], key=lambda o: (
                not o['boundary_aligned'], not o['dictionary_combo_agreement'], o['document_id'], o['start']))
            if not ranked:
                raise lex.Error(f'No occurrences for {row["candidate_id"]}')
            examples, used, texts = [], set(), set()
            # Favor diverse bodies first, then fill with other literal contexts.
            for distinct_bodies in (True, False):
                for occurrence in ranked:
                    key = (occurrence['document_id'], occurrence['start'], occurrence['end'])
                    if key in used or distinct_bodies and occurrence['text_sha256'] in texts:
                        continue
                    examples.append(context(occurrence, docs[occurrence['document_id']]))
                    used.add(key)
                    texts.add(occurrence['text_sha256'])
                    if len(examples) == 3:
                        break
                if len(examples) == 3:
                    break
            records.append({k: row[k] for k in ('candidate_id', 'form', 'canonical_tl', 'queue',
                'definitions', 'review_reasons', 'existing_entry_candidates', 'new_combos')} | {
                'readings': [r['tl'] for r in row['readings']],
                'alignment_issues': [r['alignment_issue'] for r in row['readings'] if r['alignment_issue']],
                'contexts': examples})
        packet_file = f'packet-{len(packets) + 1:03d}.jsonl'
        path = out / 'packets' / packet_file
        if path.resolve() == corpus:
            raise lex.Error('Packet output would overwrite corpus input')
        content = ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in records)
        lex.atomic_write(path, content)
        packets.append({'file': packet_file, 'sha256': sha(path), 'candidate_ids': [r['candidate_id'] for r in records]})
    manifest = {'schema_version': 1, 'harvest': str(folder), 'lexicon': str(root),
                'corpus': str(corpus), 'corpus_sha256': summary['corpus_sha256'],
                'helper_sha256': sha(Path(__file__)),
                'inputs': [{'path': str(p), 'sha256': sha(p)} for p in input_files],
                'packets': packets, 'candidate_count': len(selected),
                'queues': dict(Counter(r['queue'] for r in selected)),
                'scope': 'Sampled subagent recommendations; no approvals, imports or inventory updates'}
    write_json(out / 'manifest.json', manifest)
    (out / 'reviews').mkdir(exist_ok=True)
    return {'run': str(out), 'candidates': len(selected), 'packets': len(packets), 'queues': manifest['queues']}


def validate_decision(row, candidate):
    if row.get('candidate_id') != candidate['candidate_id'] or row.get('decision') not in DECISIONS:
        raise lex.Error('Unknown candidate or review decision')
    if not isinstance(row.get('reason'), str) or not row['reason'].strip():
        raise lex.Error('Every decision needs a reason')
    known = {c['occurrence_id'] for c in candidate['contexts']}
    for field in ('reviewed_occurrence_ids', 'supporting_occurrence_ids'):
        values = row.get(field)
        if not isinstance(values, list) or any(not isinstance(v, str) for v in values) or len(values) != len(set(values)):
            raise lex.Error(f'{field} must be a list of unique occurrence IDs')
        if not set(values) <= known:
            raise lex.Error('Review cites an unknown occurrence ID')
    reviewed, supporting = set(row['reviewed_occurrence_ids']), set(row['supporting_occurrence_ids'])
    if not reviewed or not supporting <= reviewed:
        raise lex.Error('Supporting evidence must be reviewed, and every decision needs reviewed evidence')
    if row['decision'] == 'recommend_import':
        if not supporting:
            raise lex.Error('Import recommendation needs supporting evidence')
        if candidate['existing_entry_candidates'] or 'recommendation_conflict' in candidate['review_reasons']:
            raise lex.Error('Existing-entry/recommendation conflicts must remain held for maintainer resolution')
        if candidate['alignment_issues'] or not candidate['canonical_tl']:
            raise lex.Error('Unalignable/missing reading cannot be recommended by this quick pass')
    elif supporting:
        raise lex.Error('Only an import recommendation may designate supporting import evidence')


def collect(run, root):
    run = output_directory(run, root)
    manifest = read_json(run / 'manifest.json')
    if manifest['lexicon'] != str(root) or manifest['helper_sha256'] != sha(Path(__file__)):
        raise lex.Error('Review helper or lexicon root changed; prepare a fresh run')
    for source in manifest['inputs']:
        if sha(Path(source['path'])) != source['sha256']:
            raise lex.Error('Harvest artifacts changed; prepare a fresh review')
    verify_harvest(Path(manifest['harvest']), root)
    decisions, seen = [], set()
    for packet in manifest['packets']:
        path = run / 'packets' / packet['file']
        if sha(path) != packet['sha256']:
            raise lex.Error('Review packet changed')
        candidates = {r['candidate_id']: r for r in read_lines(path)}
        if set(candidates) != set(packet['candidate_ids']):
            raise lex.Error('Packet candidate inventory mismatch')
        result = read_lines(run / 'reviews' / packet['file'].replace('.jsonl', '.review.jsonl'))
        if not result or result[0] != {'packet_file': packet['file'], 'packet_sha256': packet['sha256']}:
            raise lex.Error('Review header does not match its packet fingerprint')
        packet_seen = set()
        for row in result[1:]:
            identity = row.get('candidate_id')
            if identity not in candidates or identity in packet_seen or identity in seen:
                raise lex.Error('Unknown or duplicate review candidate')
            validate_decision(row, candidates[identity])
            packet_seen.add(identity)
            seen.add(identity)
            decisions.append({**candidates[identity], **row})
        if packet_seen != set(candidates):
            raise lex.Error('Incomplete review packet')
    if len(seen) != manifest['candidate_count']:
        raise lex.Error('Incomplete review coverage')
    counts = dict(sorted(Counter(r['decision'] for r in decisions).items()))
    by_queue = {q: dict(sorted(Counter(r['decision'] for r in decisions if r['queue'] == q).items()))
                for q in manifest['queues']}
    report = {'scope': manifest['scope'], 'manifest_sha256': sha(run / 'manifest.json'),
              'decision_counts': counts, 'by_queue': by_queue, 'decisions': decisions}
    write_json(run / 'review.json', report)
    lines = ['# Hanji subagent review', '', manifest['scope'], '',
             f'Candidates screened: {len(decisions)}. Decisions: {json.dumps(counts)}.', '',
             'Full reasons and reviewed/supporting source IDs are in `review.json`.', '',
             '| MOE ID | Form | Filing TL | Original queue | Decision | Reason |',
             '| --- | --- | --- | --- | --- | --- |']
    for row in decisions:
        values = [row['candidate_id'], row['form'], row['canonical_tl'], row['queue'], row['decision'], row['reason']]
        lines.append('| ' + ' | '.join(str(v).replace('|', '&#124;').replace('\n', ' ') for v in values) + ' |')
    lex.atomic_write(run / 'review.md', '\n'.join(lines) + '\n')
    return {'run': str(run), 'candidates': len(decisions), 'decisions': counts, 'by_queue': by_queue}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lexicon', type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--harvest', type=Path, required=True)
    prep.add_argument('--out', type=Path, required=True)
    prep.add_argument('--packet-size', type=int, default=50)
    finish = sub.add_parser('collect')
    finish.add_argument('--run', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        root = args.lexicon.resolve()
        result = prepare(args.harvest.resolve(), args.out, root, args.packet_size) if args.command == 'prepare' else collect(args.run, root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (lex.Error, OSError, ValueError, KeyError, TypeError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
