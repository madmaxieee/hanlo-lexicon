"""Occurrence-level review exclusions, retaining original harvest evidence."""
from collections import defaultdict
from copy import deepcopy

from moe_context import source_units, suppress_covered_singles, tracked_mixed_contexts
from review_context import context_id, source_triggers


def segment_ids(row):
    return [context_id(row['document_id'], t['anchor_start'], t['anchor_end'])
            for t in source_triggers(row)]


def annotate_coverage(groups, records, texts):
    """Reuse the harvester's exact compound coverage rule against current entries."""
    result = deepcopy(groups)
    if texts is None:
        return result
    originals = defaultdict(dict)
    buckets = defaultdict(dict)
    rows_by_id = {}
    for group in result:
        for row in group['occurrences']:
            document = row['document_id']
            row['tracked_coverage'] = []
            for trigger in source_triggers(row):
                start, end = trigger['anchor_start'], trigger['anchor_end']
                anchor = texts[document][start:end]
                reading = trigger.get('normalized_tl')
                if reading is None and (start, end) == (row.get('base_anchor_start'), row.get('base_anchor_end')):
                    reading = row.get('base_normalized_tl')
                if reading is None and (start, end) == (row['anchor_start'], row['anchor_end']):
                    reading = group.get('normalized_tl')
                originals[reading][(document, start, end)] = {
                    'document_id': document, 'anchor': anchor, 'anchor_start': start, 'anchor_end': end}
            identity = document, row['anchor_start'], row['anchor_end']
            candidate = {**row, 'key': group['key']}
            candidate.setdefault('moe_context_matches', [])
            candidate.setdefault('base_normalized_tl', group.get('normalized_tl'))
            candidate.setdefault('base_anchor_start', row['anchor_start'])
            candidate.setdefault('base_anchor_end', row['anchor_end'])
            buckets[group['key']][identity] = candidate
            rows_by_id[(group['key'], *identity)] = row
    originals = [{'normalized_tl': reading, 'occurrences': list(rows.values())}
                 for reading, rows in originals.items()]
    tracked = {form for r in records for form in r['multi_syllable_written_forms']}
    contexts = tracked_mixed_contexts(source_units(originals, texts), texts, tracked)
    audit = suppress_covered_singles(buckets, tracked, contexts)
    entries = defaultdict(list)
    for record in records:
        for form in record['multi_syllable_written_forms']:
            entries[form].append({k: record[k] for k in ('id', 'preferred_form', 'canonical_tl')})
    for row in audit:
        covers = []
        for cover in row['covered_by']:
            if cover['tracked_written_forms']:
                covers.append({**cover, 'entries': [entry for form in cover['tracked_written_forms']
                                                    for entry in entries[form]]})
        rows_by_id[(row['key'], row['document_id'], row['anchor_start'], row['anchor_end'])]['tracked_coverage'] = covers
    return result


def filter_occurrences(groups, ignored_segments, allow_absent=False):
    """Validate saved segment positions and select only eligible import evidence."""
    if not isinstance(ignored_segments, list) or any(not isinstance(s, str) for s in ignored_segments):
        raise ValueError('Ignored segments must be an array of source-position identities')
    known = {identity for g in groups for r in g['occurrences'] for identity in segment_ids(r)} if ignored_segments else set()
    ignored = set(ignored_segments)
    if not allow_absent and ignored - known:
        raise ValueError('Ignored segment is not in the sealed harvest; reload and export the review again')
    result = []
    for group in groups:
        rows = [row for row in group['occurrences']
                if not row.get('tracked_coverage') and (not ignored or not ignored.intersection(segment_ids(row)))]
        result.append({**group, 'occurrences': rows})
    return result
