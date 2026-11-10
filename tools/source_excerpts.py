"""Resolve literal source excerpts from recorded corpus coordinates."""

import hashlib
import re
import unicodedata as ud

SPAN = re.compile(r'(?:normalized source characters|corpus Unicode code points) (\d+):(\d+)')


def short_bounds(text, a, b, limit=64):
    """Keep a short clause, or a small window without splitting Roman tokens."""
    boundaries = '，,。！？!?；;：:\n'
    left = max((i + 1 for i in range(a) if text[i] in boundaries), default=0)
    right = next((i for i in range(b, len(text)) if text[i] in boundaries), len(text))
    if right - left > limit:
        left, right = max(left, a - 16), min(right, b + 20)
        def roman(c):
            return 'LATIN' in ud.name(c, '') or ud.category(c).startswith('M') or c in "-'’" or c.isdecimal()
        while 0 < left < a and roman(text[left - 1]) and roman(text[left]):
            left -= 1
        while b < right < len(text) and roman(text[right - 1]) and roman(text[right]):
            right += 1
    while left < a and text[left].isspace():
        left += 1
    while right > b and text[right - 1].isspace():
        right -= 1
    return left, right


def display_excerpt(excerpt, evidence):
    """Output decoration only; source excerpts and locators remain literal."""
    left = evidence['excerpt_span'][0]
    a, b = (position - left for position in evidence['match_span'])
    return (('…' if evidence.get('clipped_left') else '') + excerpt[:a] + '【' +
            excerpt[a:b] + '】' + excerpt[b:] + ('…' if evidence.get('clipped_right') else ''))


def cited_excerpt(source, documents, limit=64):
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
    left, right = short_bounds(text, a, b, limit)
    excerpt = text[left:right]
    # Retain exact substring and coordinates, without rewriting POJ/TL or Hanji.
    evidence = {'url': source['url'], 'locator': source['locator'],
                'document_id': document['id'], 'excerpt_span': [left, right],
                'clipped_left': left > 0 and text[left - 1] not in '，,。！？!?；;：:\n',
                'clipped_right': right < len(text) and text[right] not in '，,。！？!?；;：:\n',
                'match_span': [a, b], 'coordinate_text_sha256': hashlib.sha256(text.encode()).hexdigest()}
    location = f"{source['url']} | characters {left}:{right}; match {a}:{b}"
    return excerpt, location, evidence

