"""Display deduplication and sourced reading choices for human review."""

import hashlib
import json
import re
import unicodedata


def normalized(value):
    return unicodedata.normalize('NFC', value).casefold()


def word_key(record):
    if record['record_id']:
        return 'moe:' + record['record_id']
    source = record['source']
    return f"row:{source['snapshot']}:{source['sheet']}:{source['row']}:{record['column']}:{record['headword']}"


def collapse_cards(records):
    """Collapse visual duplicates without dropping senses, IDs or provenance."""
    cards = {}
    for record in records:
        reading = record.get('matched_reading', record['reading'])
        marker = (normalized(record['headword']), normalized(reading))
        card = cards.setdefault(marker, {'headword': record['headword'], 'reading': reading,
                                        'definitions': [], 'references': [], 'record_ids': []})
        for definition in record['definitions']:
            if definition and definition not in card['definitions']:
                card['definitions'].append(definition)
        reference = {'source': record['source'], 'column': record['column'],
                     'record_id': record['record_id'], 'definitions': record['definitions']}
        if reference not in card['references']:
            card['references'].append(reference)
        if record['record_id'] and record['record_id'] not in card['record_ids']:
            card['record_ids'].append(record['record_id'])
    return list(cards.values())


def reading_variants(record):
    # The original cell order distinguishes primary 1 from primary 2.
    return list(dict.fromkeys(re.sub(r'【[^】]*】', '', text).strip()
                              for text in re.split(r'[,，、/]', record['reading']) if text.strip()))


def add_review_choices(groups, records):
    index = {}
    for record in records:
        index.setdefault(word_key(record), []).extend({**record, 'reading': value} for value in reading_variants(record))
    for group in groups:
        matches = group.get('moe_matches', [])
        group['moe_cards'] = collapse_cards(matches)
        words = {}
        for match in matches:
            identity = word_key(match)
            if identity in words:
                continue
            candidates = index.get(identity, [match])
            cards = collapse_cards(candidates)
            primary_order = list(dict.fromkeys(normalized(record['reading']) for record in candidates
                                               if record['source']['sheet'] == '詞目'))
            matched = {(normalized(r['headword']), normalized(r['reading'])) for r in matches
                       if word_key(r) == identity}
            for card in cards:
                identity_text = json.dumps([identity, normalized(card['headword']), normalized(card['reading'])], ensure_ascii=False)
                card['id'] = hashlib.sha256(identity_text.encode()).hexdigest()[:24]
                card['detected'] = (normalized(card['headword']), normalized(card['reading'])) in matched
                if any(ref['source']['sheet'] == '詞目' for ref in card['references']):
                    card['primary_index'] = primary_order.index(normalized(card['reading'])) + 1
                    card['primary_count'] = len(primary_order)
            cards.sort(key=lambda card: card.get('primary_index', float('inf')))
            words[identity] = {'id': identity, 'headword': match['headword'],
                               'record_id': match['record_id'], 'readings': cards}
        group['review_words'] = list(words.values())
