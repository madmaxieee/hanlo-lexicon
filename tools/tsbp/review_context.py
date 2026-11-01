"""Longer literal excerpts for presentation, without changing harvest evidence."""
import hashlib
import json
from pathlib import Path
import unicodedata


def context_id(document, start, end):
    return json.dumps([document, start, end], ensure_ascii=False, separators=(',', ':'))


def source_triggers(row):
    return row.get('source_triggers') or [{
        'anchor_start': row.get('base_anchor_start', row['anchor_start']),
        'anchor_end': row.get('base_anchor_end', row['anchor_end']),
    }]


def corpus_texts(payload):
    path = payload.get('corpus_path')
    if not path:
        return None
    content = Path(path).read_bytes()
    if hashlib.sha256(content).hexdigest() != payload['corpus_sha256']:
        raise ValueError('Corpus changed; cannot refresh literal review contexts')
    wanted = {row['document_id'] for group in payload['groups'] for row in group['occurrences']}
    texts = {}
    for line in content.splitlines():
        doc = json.loads(line)
        if doc['id'] in wanted:
            texts[doc['id']] = doc['text']
    return texts


def reading_contexts(payload, texts=None, radius=100):
    groups = payload['groups']
    if texts is None:
        texts = corpus_texts(payload)
    if texts is None:
        return {}  # Older standalone fixtures can still show their literal clauses.
    bounds = {}
    for group in groups:
        for row in group['occurrences']:
            document = row['document_id']
            for trigger in source_triggers(row):
                start, end = trigger['anchor_start'], trigger['anchor_end']
                identity = context_id(document, start, end)
                left, right = min(start, row['anchor_start']), max(end, row['anchor_end'])
                if identity in bounds:
                    _, a, b = bounds[identity]
                    left, right = min(left, a), max(right, b)
                bounds[identity] = document, left, right
    result = {}
    for identity, (document, start, end) in bounds.items():
        text = texts[document]
        left, right = max(0, start - radius), min(len(text), end + radius)
        while left and unicodedata.category(text[left]).startswith('M'):
            left -= 1
        while right < len(text) and unicodedata.category(text[right]).startswith('M'):
            right += 1
        result[identity] = {'snippet': text[left:right], 'context_start': left, 'context_end': right,
                            'clipped_left': left > 0, 'clipped_right': right < len(text)}
    return result
