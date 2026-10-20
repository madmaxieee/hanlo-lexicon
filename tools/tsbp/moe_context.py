"""MOE reading lookup and conservative mixed-form context matching."""

from collections import defaultdict
import hashlib
import importlib.util
import re
import unicodedata

from review_support import add_review_choices


def norm(text):
    return unicodedata.normalize('NFC', text).casefold()


def han(char):
    return '\u3400' <= char <= '\u9fff' or '\U00020000' <= char <= '\U000323af'


def parts(reading):
    tokens = re.split(r'-+|\s+', norm(reading))
    return tuple(token for token in tokens if token)


def strip_annotations(form):
    return re.sub(r'【[^】]*】', '', form).strip()


def syllable_segments(reading):
    return list(re.finditer(r'[^\s-]+', reading))


def fragment_start(reading, segments, index):
    start = segments[index].start()
    previous_end = segments[index - 1].end() if index else 0
    leading = re.search(r'-+$', reading[previous_end:start])
    if leading and (index == 0 or len(leading.group()) >= 2):
        start -= len(leading.group())
    return start


def reading_fragment(reading, segments, start, end):
    return reading[fragment_start(reading, segments, start):segments[end - 1].end()]


def build_lookups(groups, records):
    requests = defaultdict(list)
    for group in groups:
        reading = group.get('normalized_tl')
        if not reading:
            continue
        reading = norm(reading)
        segments, sequence = syllable_segments(reading), parts(reading)
        source_count = len(syllable_segments(group['key']))
        for start in range(len(sequence)):
            for end in range(start + 1, len(sequence) + 1):
                whole = start == 0 and end == len(sequence)
                if not whole and source_count != len(sequence):
                    continue  # Never guess source offsets after a syllable-count change.
                fragment = reading_fragment(reading, segments, start, end)
                requests[sequence[start]].append((group['key'], sequence[start:end],
                    fragment, start, end, whole))
    lookups = {g['key']: [] for g in groups}
    for record in records:
        for reading in sorted({strip_annotations(value) for value in re.split(r'[,，、/]', record['reading']) if value.strip()}):
            normalized = norm(reading)
            sequence, segments = parts(reading), syllable_segments(normalized)
            hits = defaultdict(list)
            for position, syllable in enumerate(sequence):
                for group_key, requested, anchor_reading, qs, qe, whole in requests.get(syllable, []):
                    count = len(requested)
                    if sequence[position:position + count] != requested:
                        continue
                    fragment = reading_fragment(normalized, segments, position, position + count)
                    if re.sub(r'\s+', '-', fragment) != re.sub(r'\s+', '-', anchor_reading):
                        continue
                    hits[(group_key, qs, qe, anchor_reading, whole)].append(position)
            forms = []
            for form in [record['headword'], *record['variant_forms']]:
                form = strip_annotations(form)
                if form and all(han(c) for c in form) and len(form) == len(sequence) and form not in forms:
                    forms.append(form)
            for (group_key, qs, qe, query, whole), positions in hits.items():
                lookups[group_key].append({**record, 'matched_reading': reading,
                    'syllables': list(sequence), 'alignment_positions': positions,
                    'aligned_forms': forms, 'query_syllable_start': qs,
                    'query_syllable_end': qe, 'query_reading': query, 'query_is_full': whole})
    return lookups


def source_units(groups, texts):
    """Align source Han characters and verified TL syllables without changing text."""
    anchors = defaultdict(dict)
    for group in groups:
        for row in group['occurrences']:
            anchors[row['document_id']][row['anchor_start']] = (row, group.get('normalized_tl'))
    result = {}
    for document, text in texts.items():
        units, i = [], 0
        while i < len(text):
            source = anchors[document].get(i)
            if source and source[1]:
                row, reading = source
                raw_segments = syllable_segments(row['anchor'])
                normalized = syllable_segments(reading)
                if len(raw_segments) == len(normalized):
                    for index, (raw, converted) in enumerate(zip(raw_segments, normalized)):
                        start = row['anchor_start'] + fragment_start(row['anchor'], raw_segments, index)
                        syllable_start = row['anchor_start'] + raw.start()
                        units.append({'start': start, 'syllable_start': syllable_start,
                                      'end': row['anchor_start'] + raw.end(), 'kind': 'roman',
                                      'reading': norm(converted.group()),
                                      'neutral': '--' in text[start:syllable_start]})
                    i = row['anchor_end']
                    continue
            units.append({'start': i, 'end': i + 1, 'kind': 'han' if han(text[i]) else 'boundary',
                          'char': text[i]})
            i += 1
        result[document] = {'units': units, 'starts': {u['start']: n for n, u in enumerate(units)},
                            'ends': {u['end']: n for n, u in enumerate(units)}}
    return result


def aligned_source_match(row, record, form, position, a, b, context, text):
    """Match a complete dictionary word through any mix of Han and romanized units."""
    units = context['units']
    first, last = context['starts'].get(a), context['ends'].get(b)
    if first is None or last is None:
        return None
    start_index = first - position
    end_index = last + len(record['syllables']) - position - (last - first + 1)
    if start_index < 0 or end_index >= len(units):
        return None
    selected = units[start_index:end_index + 1]
    if len(selected) != len(record['syllables']):
        return None
    start, end = selected[0]['start'], selected[-1]['end']
    if start < row['clause_start'] or end > row['clause_end']:
        return None
    reading = norm(record['matched_reading'])
    segments = syllable_segments(reading)
    output, cursor = [], start
    for index, unit in enumerate(selected):
        if unit['kind'] == 'han':
            if unit['char'] != form[index]:
                return None
        elif unit['kind'] == 'roman':
            prefix = reading[fragment_start(reading, segments, index):segments[index].start()]
            if unit['reading'] != record['syllables'][index] or unit['neutral'] != ('--' in prefix):
                return None
            if index and selected[index - 1]['kind'] == 'roman':
                actual = text[selected[index - 1]['end']:unit['syllable_start']]
                expected = reading[segments[index - 1].end():segments[index].start()]
                if re.sub(r'\s+', '-', actual) != re.sub(r'\s+', '-', expected):
                    return None
            output.extend((text[cursor:unit['syllable_start']], unit['reading']))
            cursor = unit['end']
        else:
            return None
    output.append(text[cursor:end])
    return start, end, ''.join(output)


def context_matches(row, related, text, anchor_reading, context=None):
    """Return every supported source span, including syllable-boundary substrings."""
    matches = []
    raw_segments = syllable_segments(row['anchor'])
    for record in related:
        qs, qe = record.get('query_syllable_start', 0), record.get('query_syllable_end', len(raw_segments))
        query = record.get('query_reading', anchor_reading)
        whole = record.get('query_is_full', True)
        if whole:
            a, b = row['anchor_start'], row['anchor_end']
        else:
            if qe > len(raw_segments):
                continue
            a = row['anchor_start'] + fragment_start(row['anchor'], raw_segments, qs)
            b = row['anchor_start'] + raw_segments[qe - 1].end()
        count = len(parts(query))
        base = {'query_anchor': text[a:b], 'query_anchor_start': a, 'query_anchor_end': b,
                'query_reading': query, 'query_is_full': whole}
        for position in record['alignment_positions']:
            evidence = {**base, 'reading': record['matched_reading'], 'record_id': record['record_id'],
                        'source': record['source'], 'column': record['column'],
                        'headword': record['headword'], 'definitions': record['definitions']}
            if position == 0 and count == len(record['syllables']):
                matches.append({**evidence, 'form': strip_annotations(record['headword']),
                                'start': a, 'end': b, 'match_type': 'full_reading'})
            for form in record['aligned_forms']:
                if context is not None:
                    candidate = aligned_source_match(row, record, form, position, a, b, context, text)
                    if candidate is None:
                        continue
                    start, end, normalized_form = candidate
                    if (start, end) == (a, b) and count == len(record['syllables']):
                        continue  # The full-reading path already retained this evidence.
                else:
                    prefix, suffix = form[:position], form[position + count:]
                    if not prefix and not suffix:
                        continue
                    start, end = a - len(prefix), b + len(suffix)
                    if start < row['clause_start'] or end > row['clause_end']:
                        continue
                    if text[start:a] != prefix or text[b:end] != suffix:
                        continue
                    normalized_form = text[start:a] + query + text[b:end]
                matches.append({**evidence, 'form': form, 'start': start, 'end': end,
                                'normalized_form': normalized_form,
                                'match_type': 'han_context' if any(han(c) for c in text[start:end]) else 'full_reading'})
    return matches


def tracked_mixed_contexts(contexts, texts, tracked_multi_forms):
    """Locate exact tracked mixed spellings on verified source-unit boundaries.

    These are lexicon coverage spans, not new MOE matches. Normalize only the
    already parsed Roman units, retaining literal Han, separators and offsets.
    """
    forms = sorted({norm(form) for form in tracked_multi_forms
                    if any(han(c) for c in form)
                    and any('LATIN' in unicodedata.name(c, '') for c in form)})
    result = []
    for document, context in contexts.items():
        text, units = texts[document], context['units']
        chunks, starts, ends, cursor, length = [], {}, {}, 0, 0
        for index, unit in enumerate(units):
            gap = norm(text[cursor:unit['start']])
            chunks.append(gap)
            length += len(gap)
            starts[length] = index
            value = (norm(text[unit['start']:unit['syllable_start']]) + unit['reading']
                     if unit['kind'] == 'roman' else norm(text[unit['start']:unit['end']]))
            chunks.append(value)
            length += len(value)
            ends[length] = index
            cursor = unit['end']
        surface = ''.join(chunks)
        for form in forms:
            position = surface.find(form)
            while position >= 0:
                first, last = starts.get(position), ends.get(position + len(form))
                if first is not None and last is not None:
                    selected = units[first:last + 1]
                    if all(u['kind'] in ('roman', 'han') for u in selected):
                        start, end = selected[0]['start'], selected[-1]['end']
                        result.append({'document_id': document, 'anchor': text[start:end],
                                       'key': norm(text[start:end]), 'anchor_start': start,
                                       'anchor_end': end, 'tracked_written_form': form})
                position = surface.find(form, position + 1)
    return result


def suppress_covered_singles(buckets, tracked_multi_forms=(), tracked_contexts=()):
    """Suppress only one-syllable occurrences contained in a supported longer word."""
    multi = defaultdict(dict)
    support = {}
    tracked_multi_forms = {norm(form) for form in tracked_multi_forms}
    for locations in buckets.values():
        for row in locations.values():
            candidates = {row['key']}
            if row.get('normalized_form'):
                candidates.add(norm(row['normalized_form']))
            elif row.get('base_normalized_tl'):
                a = row['base_anchor_start'] - row['anchor_start']
                b = row['base_anchor_end'] - row['anchor_start']
                candidates.add(norm(row['anchor'][:a] + row['base_normalized_tl'] + row['anchor'][b:]))
            tracked = sorted(candidates & tracked_multi_forms)
            moe = any(len(parts(match['reading'])) >= 2 for match in row['moe_context_matches'])
            if moe or tracked:
                multi[row['document_id']][(row['anchor_start'], row['anchor_end'])] = row
                support[(row['document_id'], row['anchor_start'], row['anchor_end'])] = {
                    'moe_match': moe, 'tracked_written_forms': tracked}
    for row in tracked_contexts:
        span = (row['anchor_start'], row['anchor_end'])
        multi[row['document_id']].setdefault(span, row)
        evidence = support.setdefault((row['document_id'], *span),
                                      {'moe_match': False, 'tracked_written_forms': []})
        if row['tracked_written_form'] not in evidence['tracked_written_forms']:
            evidence['tracked_written_forms'].append(row['tracked_written_form'])
            evidence['tracked_written_forms'].sort()
    audit = []
    for group_key, locations in list(buckets.items()):
        for identity, row in list(locations.items()):
            matches = row['moe_context_matches']
            if not matches or not all(len(parts(match['reading'])) == 1 for match in matches):
                continue
            covering = [other for other in multi[row['document_id']].values()
                        if other['anchor_start'] <= row['anchor_start']
                        and row['anchor_end'] <= other['anchor_end']
                        and row['clause_start'] <= other['anchor_start']
                        and other['anchor_end'] <= row['clause_end']
                        and (other['anchor_start'], other['anchor_end']) != (row['anchor_start'], row['anchor_end'])]
            if not covering:
                continue
            audit.append({**row, 'suppression_reason': 'covered_single_syllable',
                          'covered_by': [{'anchor': other['anchor'], 'key': other['key'],
                                          'anchor_start': other['anchor_start'], 'anchor_end': other['anchor_end'],
                                          **support[(other['document_id'], other['anchor_start'], other['anchor_end'])]}
                                         for other in sorted(covering, key=lambda r: (r['anchor_start'], r['anchor_end']))]})
            del locations[identity]
        if not locations:
            del buckets[group_key]
    return audit


def regroup(groups, texts, lookups, tracked_multi_forms=()):
    buckets = defaultdict(dict)
    templates = {g['key']: g for g in groups}
    source_count = matched_count = emitted_before_merge = 0
    contexts = source_units(groups, texts)
    for group in groups:
        for original in group['occurrences']:
            source_count += 1
            text = texts[original['document_id']]
            reading = group.get('normalized_tl')
            matches = context_matches(original, lookups[group['key']], text, reading, contexts[original['document_id']]) if reading else []
            matched_count += bool(matches)
            by_span = defaultdict(list)
            for match in matches:
                by_span[(match['start'], match['end'])].append(match)
            # Preserve the original unknown span unless a full-trigger match covers it.
            if not any(match['query_is_full'] for match in matches):
                by_span.setdefault((original['anchor_start'], original['anchor_end']), [])
            trigger = {'anchor': original['anchor'], 'key': group['key'], 'normalized_tl': reading,
                       'anchor_start': original['anchor_start'], 'anchor_end': original['anchor_end']}
            for (start, end), evidence in sorted(by_span.items()):
                emitted_before_merge += 1
                row = dict(original)
                representative = max(evidence, key=lambda m: m['query_anchor_end'] - m['query_anchor_start']) if evidence else {
                    'query_anchor': original['anchor'], 'query_anchor_start': original['anchor_start'],
                    'query_anchor_end': original['anchor_end'], 'query_reading': reading}
                row.update(anchor=text[start:end], key=norm(text[start:end]), anchor_start=start, anchor_end=end,
                           context_start=min(original['context_start'], start),
                           context_end=max(original['context_end'], end),
                           base_anchor=representative['query_anchor'],
                           base_key=norm(representative['query_anchor']),
                           base_normalized_tl=representative['query_reading'],
                           base_anchor_start=representative['query_anchor_start'],
                           base_anchor_end=representative['query_anchor_end'],
                           source_triggers=[trigger], moe_context_matches=[],
                           normalized_form=next((m['normalized_form'] for m in evidence if m.get('normalized_form')), None))
                row['snippet'] = text[row['context_start']:row['context_end']]
                identity = (row['document_id'], start, end)
                existing = buckets[row['key']].get(identity)
                if existing is None:
                    existing = buckets[row['key']][identity] = row
                elif trigger not in existing['source_triggers']:
                    existing['source_triggers'].append(trigger)
                for match in evidence:
                    if match not in existing['moe_context_matches']:
                        existing['moe_context_matches'].append(match)
    before_suppression = sum(len(locations) for locations in buckets.values())
    tracked_contexts = tracked_mixed_contexts(contexts, texts, tracked_multi_forms)
    suppressed = suppress_covered_singles(buckets, tracked_multi_forms, tracked_contexts)
    result = []
    for group_key, locations in buckets.items():
        rows = list(locations.values())
        mixed = any(any(m['match_type'] == 'han_context' for m in row['moe_context_matches']) for row in rows)
        template = templates.get(group_key, {})
        group = {k: v for k, v in template.items() if k != 'occurrences'}
        group.update(key=group_key, normalized_tl=None if mixed else template.get('normalized_tl', rows[0]['base_normalized_tl']),
                     parser_compatible=True if mixed or not template else template.get('parser_compatible', True),
                     normalization_errors=template.get('normalization_errors', []),
                     preferred_matches=[], exclusion_reason=None)
        related, matches = {}, {}
        for row in rows:
            queries = {(m['query_anchor_start'], m['query_anchor_end'], m['query_reading'])
                       for m in row['moe_context_matches']}
            if not queries:
                queries.add((row['base_anchor_start'], row['base_anchor_end'], row['base_normalized_tl']))
            maximal_queries = {query for query in queries if not any(
                other[0] <= query[0] and query[1] <= other[1] and other[:2] != query[:2]
                for other in queries)}
            for trigger in row['source_triggers']:
                raw_segments = syllable_segments(trigger['anchor'])
                for record in lookups[trigger['key']]:
                    if record['query_is_full']:
                        a, b = trigger['anchor_start'], trigger['anchor_end']
                    else:
                        a = trigger['anchor_start'] + fragment_start(trigger['anchor'], raw_segments, record['query_syllable_start'])
                        b = trigger['anchor_start'] + raw_segments[record['query_syllable_end'] - 1].end()
                    if (a, b, record['query_reading']) not in maximal_queries:
                        continue
                    marker = (record['source']['sheet'], record['source']['row'], record['column'], record['matched_reading'])
                    related[marker] = record
            for record in row['moe_context_matches']:
                marker = (record['source']['sheet'], record['source']['row'], record['column'], record['reading'], record['form'])
                matches[marker] = record
        rows.sort(key=lambda row: -sum(han(c) for c in row['snippet']))
        normalized_forms = set()
        for row in rows:
            if row.get('normalized_form'):
                normalized_forms.add(norm(row['normalized_form']))
            elif row['base_normalized_tl']:
                a = row['base_anchor_start'] - row['anchor_start']
                b = row['base_anchor_end'] - row['anchor_start']
                normalized_forms.add(norm(row['anchor'][:a] + row['base_normalized_tl'] + row['anchor'][b:]))
        if not mixed:
            group['normalized_tl'] = next(iter(normalized_forms)) if len(normalized_forms) == 1 else template.get('normalized_tl')
        group.update(display=rows[0]['anchor'], occurrences=rows,
                     article_count=len({row['document_id'] for row in rows}),
                     kind='moe_context' if mixed else 'moe_romanized' if matches else 'romanized',
                     normalized_forms=sorted(normalized_forms),
                     moe_related=list(related.values()), moe_matches=list(matches.values()))
        result.append(group)
    result.sort(key=lambda group: (-len(group['occurrences']), group['key']))
    emitted = sum(len(g['occurrences']) for g in result)
    return result, {'source_anchor_occurrences': source_count,
                    'matched_source_anchor_occurrences': matched_count,
                    'unmatched_source_anchor_occurrences': source_count - matched_count,
                    'emitted_anchor_occurrences': emitted,
                    'supported_anchor_occurrences_before_single_suppression': before_suppression,
                    'suppressed_single_syllable_occurrences': len(suppressed),
                    'covered_single_syllable_audit': suppressed,
                    'additional_anchor_occurrences': max(0, emitted - source_count),
                    'anchor_occurrence_delta': emitted - source_count,
                    'merged_trigger_emissions': emitted_before_merge - before_suppression,
                    'promoted_occurrences': sum(any(m['match_type'] == 'han_context' for m in row['moe_context_matches'])
                                                for g in result for row in g['occurrences']),
                    'mixed_groups': sum(g['kind'] == 'moe_context' for g in result),
                    'full_romanized_groups': sum(g['kind'] == 'moe_romanized' for g in result),
                    'groups_with_related_entries': sum(bool(g['moe_related']) for g in result)}


def enrich(groups, texts, lexicon_root, tracked_multi_forms=()):
    module_path = lexicon_root / 'tools/lexicon.py'
    spec = importlib.util.spec_from_file_location('pinned_lexicon_lookup', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    pin, sheets, records = module.moe_data(lexicon_root)
    lookups = build_lookups(groups, records)
    enriched, stats = regroup(groups, texts, lookups, tracked_multi_forms)
    add_review_choices(enriched, records)
    metadata = {**stats, 'snapshot': pin['id'], 'sha256': pin['sha256'],
                'dictionary_records': len(records), 'download_url': pin['download_url'],
                'lookup_tool': str(module_path),
                'lookup_tool_sha256': hashlib.sha256(module_path.read_bytes()).hexdigest(),
                'lookup_policy': 'Exact tone-preserving whole-syllable sequence; aligned Han context; all nested and overlapping supported spans, including romanized subspans. Identical source spans are merged; contained single-syllable matches are suppressed by MOE or tracked multi-syllable written forms before tracked/curated exclusions. No semantic identity inferred.'}
    return enriched, metadata, lookups
