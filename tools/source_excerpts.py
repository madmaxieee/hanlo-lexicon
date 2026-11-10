"""Resolve literal source excerpts from recorded corpus coordinates."""

import hashlib
import re
import unicodedata as ud

SPAN = re.compile(r'(?:normalized source characters|corpus Unicode code points) (\d+):(\d+)')


def cited_excerpt(source, documents, limit=240):
    """Resolve the recorded occurrence, failing closed on stale/mismatched offsets."""
    match = SPAN.search(source.get('locator', ''))
    document = documents.get(source.get('url'))
    if not match or document is None:
        raise ValueError('Missing corpus document or character span')
    a, b = map(int, match.groups())
    literal = re.search(r'(?:written form |literal form )(.+?)(?:;| \(in |$)', source['locator'])
    if literal is None:
        raise ValueError('Missing recorded literal form')
    # Harvest sources use NFC; some older citations count the original code points.
    candidates = [ud.normalize('NFC', document['text']), document['text']]
    text = next((t for t in candidates if 0 <= a < b <= len(t)
                 and ud.normalize('NFC', t[a:b]) == ud.normalize('NFC', literal[1])), None)
    if text is None:
        raise ValueError('Corpus span no longer matches recorded literal form')
    left = text.rfind('\n', 0, a) + 1
    right = text.find('\n', b)
    if right < 0:
        right = len(text)
    if right - left > limit:
        left = max(left, a - max(0, (limit - (b - a)) // 2))
        right = min(right, max(b, left + limit))
    excerpt = text[left:right]
    # Retain exact substring and coordinates, without rewriting POJ/TL or Hanji.
    evidence = {'url': source['url'], 'locator': source['locator'],
                'document_id': document['id'], 'excerpt_span': [left, right],
                'match_span': [a, b], 'coordinate_text_sha256': hashlib.sha256(text.encode()).hexdigest()}
    location = f"{source['url']} | characters {left}:{right}; match {a}:{b}"
    return excerpt, location, evidence

