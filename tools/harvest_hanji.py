#!/usr/bin/env python3
"""Report pure-Hanji corpus matches and conditional combo evidence; never import."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import heapq
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import tomllib
import unicodedata as ud

import lexicon as lex


VERSION = 1
END = None


def han(char):
    return (ud.name(char, '').startswith(('CJK UNIFIED IDEOGRAPH-',
                                        'CJK COMPATIBILITY IDEOGRAPH-')) or char == '〇')


def pure(form):
    return bool(form) and all(han(char) for char in form)


def clean(value):
    return re.sub(r'【[^】]*】', '', value).strip()


def reading_choices(value):
    return list(dict.fromkeys(lex.key(clean(part)) for part in re.split(r'[,，、/]', value)
                              if clean(part)))


def syllables(reading):
    """Retain a leading/medial neutral marker on its syllable, including after spaces."""
    value = lex.key(reading)
    tokens = list(re.finditer(r'[^\s-]+', value))
    result = []
    for i, token in enumerate(tokens):
        gap = value[tokens[i - 1].end() if i else 0:token.start()]
        if gap.strip() not in ('', '-', '--'):
            return None
        part = token.group()
        if not all('LATIN' in ud.name(c, '') or ud.category(c).startswith('M')
                   or c in "'’" for c in part):
            return None
        result.append(('--' if '--' in gap else '') + part)
    if not tokens or value[tokens[-1].end():].strip():
        return None
    return result


def align(form, reading):
    parts = syllables(reading)
    if parts is None:
        return None, 'unsupported_reading'
    if not pure(form) or len(form) != len(parts):
        return None, 'character_syllable_count_mismatch'
    return list(zip(form, parts)), None


def dictionary_index(records):
    """One candidate per numbered main identity, canonical spelling only.

    All supported readings remain alternatives, including contractions that cannot
    supply positional evidence. Names, comparison rows and variant spellings do
    not create extra candidates or determine a default reading.
    """
    candidates = {}
    for record in records:
        if record['source']['sheet'] != '詞目' or not str(record['record_id']).isdigit():
            continue
        identity = str(record['record_id'])
        form = clean(record['headword'])
        if not pure(form):
            continue
        if identity in candidates and candidates[identity]['form'] != form:
            raise lex.Error(f'MOE identity {identity} has multiple canonical forms')
        candidate = candidates.setdefault(identity, {
            'candidate_id': identity, 'form': form, 'readings': [],
            'main_sources': [], 'definitions': record['definitions'],
        })
        if record['source'] not in candidate['main_sources']:
            candidate['main_sources'].append(record['source'])
    for record in records:
        candidate = candidates.get(str(record['record_id']))
        if candidate is None or record['source']['sheet'] not in {
                '詞目', '又唸作', '合音唸作', '俗唸作', '語音差異'}:
            continue
        for reading in reading_choices(record['reading']):
            option = next((r for r in candidate['readings'] if r['tl'] == reading), None)
            if option is None:
                combos, reason = align(candidate['form'], reading)
                option = {'tl': reading, 'combos': combos, 'alignment_issue': reason, 'sources': []}
                candidate['readings'].append(option)
            source = {**record['source'], 'column': record['column'],
                      'original_headword': record['headword'], 'original_reading': record['reading']}
            if source not in option['sources']:
                option['sources'].append(source)
    # Only the main sheet establishes the canonical filing default, in source order.
    for candidate in candidates.values():
        primary = [r for r in candidate['readings']
                   if any(s['sheet'] == '詞目' for s in r['sources'])]
        candidate['canonical_tl'] = primary[0]['tl'] if primary else None
    return dict(sorted(candidates.items(), key=lambda item: int(item[0])))


def preferred_units(form, reading):
    """Conservative canonical alignment, using the maintenance export's checks."""
    parts = syllables(reading)
    if parts is None:
        return None
    try:
        lex.written_form(form, reading, reading)
    except lex.Error:
        return None
    tokens, starts = [], []
    for match in re.finditer(r'[^\s-]+', form):
        chunk = match.group()
        i = 0
        while i < len(chunk):
            if han(chunk[i]):
                starts.append(match.start() + i)
                tokens.append(('hanji', chunk[i]))
                i += 1
            elif 'LATIN' in ud.name(chunk[i], ''):
                start = i
                starts.append(match.start() + i)
                i += 1
                while i < len(chunk) and ('LATIN' in ud.name(chunk[i], '')
                        or ud.category(chunk[i]).startswith('M') or chunk[i] in "'’"):
                    i += 1
                tokens.append(('romanized', lex.key(chunk[start:i])))
            else:
                return None
    if len(tokens) != len(parts):
        return None
    for index, (kind, value) in enumerate(tokens):
        if kind == 'romanized':
            if value != parts[index].removeprefix('--'):
                return None
            prefix = re.search(r'[-\s]*$', form[:starts[index]]).group()
            if ('--' in prefix) != parts[index].startswith('--'):
                return None
            tokens[index] = (kind, parts[index])
    return tokens


def combo_inventory(current):
    evidence = defaultdict(lambda: defaultdict(set))
    skipped = []
    for path, entry in current:
        reason = ('rule_generated' if entry.get('rule_generated') else
                  'disputed' if entry['review_status'] == 'disputed' else None)
        units = preferred_units(entry['preferred_form'], entry['canonical_tl']) if not reason else None
        if not reason and units is None:
            reason = 'unalignable_preferred_form'
        if reason:
            skipped.append({'entry_id': entry['id'], 'reason': reason})
            continue
        forms = list(dict.fromkeys([*entry['moe_forms'], *entry.get('hanji_forms', []),
                                    *([entry['preferred_form']] if pure(entry['preferred_form']) else [])]))
        if not forms:
            skipped.append({'entry_id': entry['id'], 'reason': 'no_hanji_form'})
        for form in forms:
            combos, issue = align(clean(form), entry['canonical_tl'])
            if issue:
                skipped.append({'entry_id': entry['id'], 'form': form, 'reason': issue})
                continue
            for combo, output in zip(combos, units):
                evidence[tuple(combo)][output].add(entry['id'])
    inventory = {}
    for combo, outputs in sorted(evidence.items()):
        recommendations = [{'kind': kind, 'output': output, 'entry_ids': sorted(ids)}
                           for (kind, output), ids in sorted(outputs.items())]
        inventory[combo] = {'hanji': combo[0], 'tl': combo[1],
                            'status': 'consistent' if len(outputs) == 1 else 'conflicting',
                            'recommendations': recommendations}
    return inventory, skipped


def trie_for(candidates):
    trie = {}
    for identity, candidate in candidates.items():
        node = trie
        for char in candidate['form']:
            node = node.setdefault(char, {})
        node.setdefault(END, []).append(identity)
    return trie


def han_runs(text):
    start = None
    for index, char in enumerate(text):
        if han(char) or start is not None and ud.category(char).startswith('M'):
            if start is None:
                start = index
        elif start is not None:
            yield start, index
            start = None
    if start is not None:
        yield start, len(text)


def blocked_spans(text, phrases):
    spans = []
    for phrase in phrases:
        start = text.find(phrase)
        while start >= 0:
            spans.append((start, start + len(phrase)))
            start = text.find(phrase, start + 1)
    return spans


def match_document(doc, trie, radius, exclusions):
    text = doc['text']
    blocked = blocked_spans(text, exclusions)
    matches = []
    for run_start, run_end in han_runs(text):
        for start in range(run_start, run_end):
            node = trie
            end = start
            while end < run_end and text[end] in node:
                node = node[text[end]]
                end += 1
                if END not in node or end < len(text) and ud.category(text[end]).startswith('M'):
                    continue
                if any(start < b and a < end for a, b in blocked):
                    continue
                left, right = max(0, start - radius), min(len(text), end + radius)
                while left > 0 and ud.category(text[left]).startswith('M'):
                    left -= 1
                while right < len(text) and ud.category(text[right]).startswith('M'):
                    right += 1
                matches.append({'start': start, 'end': end, 'form': text[start:end],
                    'candidate_ids': node[END][:], 'run_start': run_start, 'run_end': run_end,
                    'boundary_aligned': (start, end) == (run_start, run_end),
                    'context_start': left, 'context_end': right, 'snippet': text[left:right]})
    return sorted(matches, key=lambda row: (row['start'], row['end']))


def overlap_groups(matches):
    """Connected intervals; touching spans belong to separate groups."""
    group, end = [], -1
    for row in matches:
        if group and row['start'] >= end:
            yield group
            group = []
        group.append(row)
        end = max(end, row['end']) if len(group) > 1 else row['end']
    if group:
        yield group


def group_analysis(rows, candidates, text):
    """Per-position agreement over ALL covering dictionary alternatives.

    This does not assert a tokenization. Unknown-word alternatives always remain
    possible, even if the dictionary covers every character. Unalignable reading
    alternatives block agreement rather than silently disappearing.
    """
    start, end = rows[0]['start'], max(row['end'] for row in rows)
    options = defaultdict(set)
    blocked = set()
    for row in rows:
        for identity in row['candidate_ids']:
            readings = candidates[identity]['readings']
            if not readings:
                blocked.update(range(row['start'], row['end']))
            for reading in readings:
                if reading['combos'] is None:
                    blocked.update(range(row['start'], row['end']))
                    continue
                for offset, (_, tl) in enumerate(reading['combos']):
                    options[row['start'] + offset].add(tl)
    positions = []
    for index in range(start, end):
        readings = sorted(options[index])
        positions.append({'offset': index, 'hanji': text[index], 'readings': readings,
                          'unalignable_alternative': index in blocked,
                          'dictionary_agreement': len(readings) == 1 and index not in blocked})
    # Do not enumerate the quadratic set of overlap pairs in long Han paragraphs.
    active, pending, previous_start, crossing = [], [], None, False
    for row in rows:
        if row['start'] != previous_start:
            for previous_end in pending:
                heapq.heappush(active, previous_end)
            pending = []
            previous_start = row['start']
            while active and active[0] <= row['start']:
                heapq.heappop(active)
        if active and active[0] < row['end']:
            crossing = True
            break
        pending.append(row['end'])
    return {'start': start, 'end': end, 'text': text[start:end],
            'overlap_kind': 'crossing' if crossing else 'containment' if len(rows) > 1
                            else 'same_span_identities' if len(rows[0]['candidate_ids']) > 1 else 'isolated',
            'unknown_word_possible': True, 'positions': positions,
            'dictionary_combo_agreement': all(p['dictionary_agreement'] for p in positions)}


def corpus_documents(path, input_format, tags, issue):
    """Stream JSONL; preserve decoded source text and Unicode code-point offsets."""
    digest = hashlib.sha256()
    seen = set()
    if input_format == 'text':
        raw = path.read_bytes()
        digest.update(raw)
        yield {'id': path.name, 'text': raw.decode('utf-8'), 'metadata': {}}
    else:
        with path.open('rb') as stream:
            for line_number, raw in enumerate(stream, 1):
                digest.update(raw)
                if not raw.strip():
                    continue
                try:
                    doc = json.loads(raw)
                    if not isinstance(doc, dict) or not isinstance(doc.get('text'), str):
                        raise ValueError('expected an object with a text string')
                    if not isinstance(doc.get('id'), str) or not doc['id']:
                        raise ValueError('expected a nonempty string id')
                    metadata = doc.get('metadata', {})
                    if not isinstance(metadata, dict):
                        raise ValueError('metadata must be an object')
                    doc_tags = metadata.get('tags', [])
                    if not isinstance(doc_tags, list) or any(not isinstance(t, str) for t in doc_tags):
                        raise ValueError('metadata.tags must be an array of strings')
                    if not all(tag in doc_tags for tag in tags):
                        continue
                    if issue is not None and re.fullmatch(r'台文通訊BONG報\s*\d+\s*期', metadata.get('title', '')):
                        continue
                    if doc['id'] in seen:
                        raise ValueError(f'duplicate document id {doc["id"]!r}')
                    seen.add(doc['id'])
                    yield {**doc, 'metadata': metadata}
                except (ValueError, TypeError) as exc:
                    raise lex.Error(f'{path}:{line_number}: {exc}') from exc
    return digest.hexdigest()


def existing_index(current):
    forms, readings, entries = defaultdict(set), defaultdict(set), {}
    for _, entry in current:
        identity = entry['id']
        entries[identity] = entry
        for form in [entry['preferred_form'], *entry['moe_forms'], *entry.get('hanji_forms', [])]:
            forms[lex.annotation_key(form)].add(identity)
        for reading in [entry['canonical_tl'], *entry['alternate_readings']]:
            readings[lex.key(reading)].add(identity)
    return forms, readings, entries


def existing_links(candidate, index):
    forms, index_readings, entries = index
    form = lex.key(candidate['form'])
    readings = {lex.key(r['tl']) for r in candidate['readings']}
    form_ids = forms.get(form, set())
    reading_ids = set().union(*(index_readings.get(r, set()) for r in readings))
    links = []
    for identity in sorted(form_ids | reading_ids):
        entry = entries[identity]
        links.append({'entry_id': identity, 'preferred_form': entry['preferred_form'],
                      'canonical_tl': entry['canonical_tl'], 'shared_form': identity in form_ids,
                      'shared_reading': identity in reading_ids})
    return links


def combo_status(combo, inventory):
    row = inventory.get(tuple(combo))
    if row is None:
        return 'unknown'
    if row['status'] == 'conflicting':
        return 'conflicting'
    output = row['recommendations'][0]
    return 'hanji' if output['kind'] == 'hanji' and output['output'] == combo[0] else 'different_recommendation'


def build_report(documents, candidates, current, *, radius=12,
                 exclusions=(), occurrence_sink=None, group_sink=None):
    inventory, skipped = combo_inventory(current)
    trie = trie_for(candidates)
    tracked = existing_index(current)
    identities_per_form = Counter(c['form'] for c in candidates.values())
    stats = defaultdict(Counter)
    candidate_docs, candidate_texts = defaultdict(set), defaultdict(set)
    span_keys = defaultdict(set)
    samples = defaultdict(list)
    supported_combos = defaultdict(set)
    coverage = defaultdict(lambda: {'occurrences': set(), 'documents': set(), 'texts': set(),
                                    'candidate_ids': set()})
    article_inventory = []
    totals = Counter()
    seen_texts = set()
    for doc in documents:
        text = doc['text']
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        totals['duplicate_text_documents'] += text_hash in seen_texts
        seen_texts.add(text_hash)
        meta = doc.get('metadata', {})
        article = {'id': doc['id'], 'title': meta.get('title', ''),
                   'url': meta.get('original_url', ''), 'text_sha256': text_hash,
                   'characters': len(text)}
        article_inventory.append(article)
        matches = match_document(doc, trie, radius, exclusions)
        totals.update(documents=1, source_characters=len(text), matched_spans=len(matches))
        for group_number, rows in enumerate(overlap_groups(matches), 1):
            analysis = group_analysis(rows, candidates, text)
            group_id = f'{doc["id"]}#{group_number}'
            totals['overlap_groups'] += 1
            totals[analysis['overlap_kind'] + '_groups'] += 1
            if group_sink:
                group_sink({'group_id': group_id, 'document_id': doc['id'], **analysis,
                            'matches': [{'start': r['start'], 'end': r['end'],
                                         'candidate_ids': r['candidate_ids']} for r in rows]})
            for position in analysis['positions']:
                if not position['dictionary_agreement']:
                    continue
                combo = position['hanji'], position['readings'][0]
                item = coverage[combo]
                item['occurrences'].add((text_hash, position['offset']))
                item['documents'].add(doc['id'])
                item['texts'].add(text_hash)
                item['candidate_ids'].update(identity for row in rows
                    if row['start'] <= position['offset'] < row['end'] for identity in row['candidate_ids'])
            for row in rows:
                positions = analysis['positions'][row['start'] - analysis['start']:row['end'] - analysis['start']]
                agreement = all(p['dictionary_agreement'] for p in positions)
                for identity in row['candidate_ids']:
                    stats[identity]['occurrences'] += 1
                    stats[identity]['boundary_aligned_occurrences'] += row['boundary_aligned']
                    stats[identity]['crossing_group_occurrences'] += analysis['overlap_kind'] == 'crossing'
                    stats[identity]['dictionary_agreement_occurrences'] += agreement
                    supported_combos[identity].update((p['hanji'], p['readings'][0]) for p in positions
                                                      if p['dictionary_agreement'])
                    candidate_docs[identity].add(doc['id'])
                    candidate_texts[identity].add(text_hash)
                    span_keys[identity].add((text_hash, row['start'], row['end']))
                occurrence = {**row, 'document_id': doc['id'], 'title': article['title'],
                              'url': article['url'], 'text_sha256': text_hash,
                              'group_id': group_id, 'overlap_kind': analysis['overlap_kind'],
                              'dictionary_combo_agreement': agreement}
                if occurrence_sink:
                    occurrence_sink(occurrence)
                for identity in row['candidate_ids']:
                    # At most three distinct-text contexts; duplicates cannot crowd them out.
                    if len(samples[identity]) < 3 and not any(s['text_sha256'] == text_hash for s in samples[identity]):
                        samples[identity].append(occurrence)
    output = []
    for identity in sorted(stats, key=int):
        candidate = candidates[identity]
        canonical = next((r for r in candidate['readings'] if r['tl'] == candidate['canonical_tl']), None)
        combos = canonical['combos'] if canonical and canonical['combos'] is not None else []
        possible_combos = {tuple(c) for reading in candidate['readings'] for c in (reading['combos'] or [])}
        statuses = [dict(hanji=c[0], tl=c[1], status=combo_status(c, inventory)) for c in sorted(possible_combos)]
        novel = sorted(c for c in supported_combos[identity] if combo_status(c, inventory) == 'unknown')
        links = existing_links(candidate, tracked)
        reasons = []
        if len(candidate['readings']) != 1:
            reasons.append('multiple_or_missing_readings')
        if not combos:
            reasons.append('unalignable_canonical_reading')
        if identities_per_form[candidate['form']] > 1:
            reasons.append('same_form_multiple_identities')
        if any(s['status'] in {'different_recommendation', 'conflicting'} for s in statuses):
            reasons.append('recommendation_conflict')
        if links:
            reasons.append('existing_entry_candidates')
        if stats[identity]['crossing_group_occurrences']:
            reasons.append('crossing_overlap')
        if not stats[identity]['boundary_aligned_occurrences']:
            reasons.append('no_boundary_aligned_occurrence')
        if stats[identity]['dictionary_agreement_occurrences'] != stats[identity]['occurrences']:
            reasons.append('dictionary_reading_disagreement')
        queue = 'batch_proposal' if not reasons else 'agreement_only' if (
            supported_combos[identity] and
            not any(r in reasons for r in ('recommendation_conflict', 'existing_entry_candidates'))
        ) else 'focused_review'
        output.append({**candidate, **stats[identity], 'article_count': len(candidate_docs[identity]),
                       'distinct_text_count': len(candidate_texts[identity]),
                       'distinct_text_occurrences': len(span_keys[identity]),
                       'combo_statuses': statuses, 'new_combos': novel,
                       'potential_new_combos': sorted(c for c in possible_combos if combo_status(c, inventory) == 'unknown'),
                       'new_combo_count': len(novel), 'existing_entry_candidates': links,
                       'queue': queue, 'review_reasons': reasons, 'sample_contexts': samples[identity]})
    output.sort(key=lambda row: (-row['new_combo_count'], -row['distinct_text_count'],
                                -row['distinct_text_occurrences'], int(row['candidate_id'])))
    combo_rows = []
    for combo, evidence in sorted(coverage.items()):
        combo_rows.append({'hanji': combo[0], 'tl': combo[1], 'status': combo_status(combo, inventory),
                           'distinct_text_occurrences': len(evidence['occurrences']),
                           'article_count': len(evidence['documents']), 'distinct_text_count': len(evidence['texts']),
                           'candidate_ids': sorted(evidence['candidate_ids'], key=int)})
    totals.update(candidates=len(output), dictionary_candidates=len(candidates),
                  conditional_agreement_combos=len(combo_rows),
                  new_conditional_agreement_combos=sum(r['status'] == 'unknown' for r in combo_rows))
    return {'candidates': output, 'combo_coverage': combo_rows,
            'combo_inventory': list(inventory.values()), 'inventory_skipped': skipped,
            'summary': {'counts': dict(sorted(totals.items())),
                        'queues': dict(sorted(Counter(r['queue'] for r in output).items())),
                        'articles': article_inventory}}


def markdown_report(summary, candidates, combos):
    counts = summary['counts']
    lines = ['# Hanji harvest report', '',
             'Read-only proposals. Dictionary agreement is conditional on dictionary interpretations;',
             'unknown words and incorrect word boundaries remain possible. No entry is approved or imported.', '',
             f"Documents: {counts.get('documents', 0)}; matched spans: {counts.get('matched_spans', 0)}; "
             f"candidate identities: {len(candidates)}; new conditional combos: "
             f"{counts.get('new_conditional_agreement_combos', 0)}.", '',
             'Counts describe this corpus, not general language frequency. Distinct-text counts collapse exact duplicate bodies.', '',
             'The tables show up to 50 candidates per queue in priority order; `candidates.json` contains every candidate,',
             'its review reasons, and literal source contexts. `occurrences.jsonl` retains every match.', '']
    def cell(value):
        return str(value).replace('|', '&#124;').replace('\n', ' ')
    for queue in ('batch_proposal', 'agreement_only', 'focused_review'):
        selected = [r for r in candidates if r['queue'] == queue]
        lines += [f'## {queue} ({len(selected)})', '',
                  '| MOE ID | Form | Canonical filing TL | New combos | Articles / distinct texts |',
                  '| --- | --- | --- | --- | --- |']
        for row in selected[:50]:
            lines.append('| ' + ' | '.join(map(cell, [row['candidate_id'], row['form'], row['canonical_tl'] or '',
                         row['new_combo_count'], f"{row['article_count']} / {row['distinct_text_count']}"])) + ' |')
        lines.append('')
    lines += ['', '## New combos with conditional dictionary agreement', '',
              '| Hanji | TL | Distinct texts | Candidate IDs |', '| --- | --- | --- | --- |']
    for row in combos:
        if row['status'] == 'unknown':
            lines.append('| ' + ' | '.join(map(cell, [row['hanji'], row['tl'], row['distinct_text_count'],
                                                      ', '.join(row['candidate_ids'])])) + ' |')
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--lexicon', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--format', choices=('jsonl', 'text'), default='jsonl', dest='input_format')
    parser.add_argument('--tag', action='append', default=[], help='Require this metadata tag; repeat for AND')
    parser.add_argument('--issue', type=int, help='Require issue:N tag and omit TSBP catalog titles')
    parser.add_argument('--radius', type=int, default=12)
    parser.add_argument('--exclude-contexts', type=Path, help='JSON array of exact literal phrases; omit intersecting matches')
    args = parser.parse_args(argv)
    try:
        root, out, corpus = args.lexicon.resolve(), args.out.resolve(), args.corpus.resolve()
        if args.radius < 0:
            raise lex.Error('radius must be nonnegative')
        if args.input_format == 'text' and (args.tag or args.issue is not None):
            raise lex.Error('tag/issue filters require JSONL input')
        if out.is_relative_to(root) and not out.is_relative_to(root / '.cache'):
            raise lex.Error('Write reports outside the repository or under its ignored .cache/')
        names = ('occurrences.jsonl', 'overlap-groups.jsonl', 'candidates.json', 'combo-inventory.json',
                 'combo-coverage.json', 'summary.json', 'report.md')
        inputs = {corpus, *( [args.exclude_contexts.resolve()] if args.exclude_contexts else [])}
        if any((out / name).resolve() in inputs for name in names):
            raise lex.Error('Output files would overwrite an input')
        exclusions = json.loads(args.exclude_contexts.read_text(encoding='utf-8')) if args.exclude_contexts else []
        if not isinstance(exclusions, list) or any(not isinstance(p, str) or not p for p in exclusions):
            raise lex.Error('Context exclusions must be an array of nonempty strings')
        pin, _, records = lex.moe_data(root)
        current = lex.entries(root)
        candidates = dictionary_index(records)
        tags = list(dict.fromkeys([*args.tag, *([f'issue:{args.issue}'] if args.issue is not None else [])]))
        documents = corpus_documents(corpus, args.input_format, tags, args.issue)
        # Stage the report so invalid corpus input cannot leave a partially replaced report.
        with tempfile.TemporaryDirectory(prefix='hanji-harvest-') as folder:
            stage = Path(folder)
            with (stage / 'occurrences.jsonl').open('w', encoding='utf-8') as occurrences, \
                    (stage / 'overlap-groups.jsonl').open('w', encoding='utf-8') as groups:
                def sink(stream):
                    return lambda row: stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')
                # Capture the generator's final corpus digest without rereading the input.
                corpus_digest = []
                def selected_documents():
                    corpus_digest.append((yield from documents))
                report = build_report(selected_documents(), candidates, current, radius=args.radius,
                                      exclusions=exclusions,
                                      occurrence_sink=sink(occurrences), group_sink=sink(groups))
            if not report['summary']['counts'].get('documents'):
                raise lex.Error('No documents selected; check the input and tag/issue filters')
            if lex.entry_files(root) != [path for path, _ in current]:
                raise lex.Error('Entry files changed during harvesting; rerun for a consistent report')
            manifest = []
            for path, entry in current:
                raw = path.read_bytes()
                if tomllib.loads(raw.decode('utf-8')) != entry:
                    raise lex.Error(f'{path}: entry changed during harvesting; rerun')
                manifest.append({'path': str(path.relative_to(root)), 'sha256': hashlib.sha256(raw).hexdigest()})
            summary = report['summary']
            summary.update(schema_version=VERSION, corpus_path=str(corpus), corpus_sha256=corpus_digest[0],
                           dictionary={'snapshot': pin['id'], 'sha256': pin['sha256']},
                           lexicon_entries=manifest,
                           tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                           maintenance_tool_sha256=hashlib.sha256(Path(lex.__file__).read_bytes()).hexdigest(),
                           options={'format': args.input_format, 'tags': tags, 'issue': args.issue,
                                    'radius': args.radius,
                                    'excluded_contexts': exclusions},
                           offset_unit='Unicode code points in the exact decoded corpus text',
                           policy='Canonical MOE Hanji forms only; all supported readings; no inferred tokenization. '
                                  'Agreement is conditional dictionary evidence, never approval or lexical attestation. '
                                  'No corpus observation updates the recommendation inventory.')
            for name, data in [('candidates.json', report['candidates']),
                               ('combo-inventory.json', {'combos': report['combo_inventory'], 'skipped': report['inventory_skipped']}),
                               ('combo-coverage.json', report['combo_coverage']), ('summary.json', summary)]:
                (stage / name).write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
            (stage / 'report.md').write_text(markdown_report(summary, report['candidates'], report['combo_coverage']), encoding='utf-8')
            for name in names:
                lex.atomic_write(out / name, (stage / name).read_bytes())
        print(json.dumps({'out': str(out), 'counts': summary['counts'], 'queues': summary['queues']}, ensure_ascii=False, indent=2))
        return 0
    except (lex.Error, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
