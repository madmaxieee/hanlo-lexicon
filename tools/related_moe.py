"""Hanji-related MOE discovery, combo writing evidence, and individual human review."""

from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import unicodedata

import hanlo_combos as combos
import lexicon as lex


READING_SHEETS = {'詞目', '又唸作', '合音唸作', '俗唸作', '語音差異'}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def reading_options(records):
    """Keep original reading order and references, without inferring pronunciations."""
    options = {}
    for record in records:
        if record['source']['sheet'] not in READING_SHEETS:
            continue
        for part in re.split(r'[,，、/]', record['reading']):
            reading = unicodedata.normalize('NFC', re.sub(r'【[^】]*】', '', part).strip())
            if not reading:
                continue
            option = options.setdefault(lex.key(reading), {'canonical_tl': reading, 'references': []})
            reference = {field: record[field] for field in ('headword', 'reading', 'column', 'source')}
            if reference not in option['references']:
                option['references'].append(reference)
    return list(options.values())


def render_choices(positions):
    """Render one consistent choice per position; never resolve conflicts by count."""
    result, previous_roman = '', False
    for position in positions:
        choice, = position['choices']
        roman = choice['kind'] == 'romanized'
        token = choice['token']
        if roman and not token.startswith('--') and previous_roman:
            result += '-'
        result += token
        previous_roman = roman
    return result


class WritingIndex:
    def __init__(self, root, current, records):
        inventory = combos.derive([(path, entry) for path, entry in current
                                   if entry['review_status'] != 'disputed'])
        self.combos = {(item['hanji'], item['canonical_tl']): item for item in inventory['combos']}
        self.entries = {item['entry_id']: item for item in inventory['entries']}
        self.records = defaultdict(list)
        for record in records:
            self.records[record['record_id']].append(record)

    def proposal(self, form, option):
        result = {'hanji_form': form, **option, 'requires_human_review': True,
                  'suggested_form': None, 'positions': []}
        try:
            reading = combos.reading_units(option['canonical_tl'])
            units = combos.written_units(form, reading)
        except combos.AlignmentError as error:
            return dict(result, status='unalignable', reason=str(error))
        for unit, syllable in zip(units, reading):
            tl = combos.tl_key(syllable)
            found = self.combos.get((unit['text'], tl))
            choices = [{**output, 'evidence': [self.entries[identity] for identity in output['entry_ids']]}
                       for output in found['outputs']] if found else []
            result['positions'].append({'hanji': unit['text'], 'canonical_tl': tl,
                'status': found['status'] if found else 'unknown', 'choices': choices})
        if any(len(position['choices']) > 1 for position in result['positions']):
            result['status'] = 'conflicting'
        elif any(not position['choices'] for position in result['positions']):
            result['status'] = 'incomplete'
        else:
            result['status'] = 'consistent'
            result['suggested_form'] = render_choices(result['positions'])
        return result

    def annotate(self, related):
        result = []
        for row in related:
            options = reading_options(self.records[row['record_id']])
            longer_forms = sorted({relation['matched_form'] for relation in row['relations']
                                   if len(lex.hanji_glyphs(relation['matched_form'])) >
                                   len(lex.hanji_glyphs(relation['base_form']))})
            result.append({**row, 'requires_human_review': True, 'reading_options': options,
                'writing_suggestions': [self.proposal(form, option) for form in longer_forms for option in options]})
        return result


def evidence_body(report):
    return {**{name: value for name, value in report.items() if name not in {'items', 'evidence_sha256'}},
            'items': [{name: value for name, value in item.items() if name != 'review'} for item in report['items']]}


def find(root, seeds):
    """Standalone read-only discovery; no import request or pronunciation needed."""
    seeds = sorted({unicodedata.normalize('NFC', seed) for seed in seeds})
    if not seeds or any(len(lex.hanji_glyphs(seed)) not in (2, 3) for seed in seeds):
        raise lex.Error('Supply literal two- or three-Hanji forms, without romanization or separators.')
    current = [(path, entry) for path, entry, _ in lex.entry_snapshot(root)]
    evidence = lex.lkk_data(root), lex.moe_data(root)
    lookup = lex.LookupIndex(current, evidence)
    candidate = {'preferred_form': seeds[0], 'moe_forms': seeds[1:]}
    matches = lookup.moe.matching({lex.key(seed) for seed in seeds}, set())
    related = lookup.related_moe.suggest(candidate, matches)
    related = WritingIndex(root, current, evidence[1][2]).annotate(related)
    items = []
    for row in related:
        forms = {lex.annotation_key(form) for form in [row['headword'], *row['variant_forms']]}
        sources = {tuple(sorted(record['source'].items())) for record in evidence[1][2]
                   if record['record_id'] == row['record_id']}
        existing = [{'path': str(path.relative_to(root)), **entry} for path, entry in current
                    if forms & lex.entry_keys(entry)[0]
                    or any(tuple(sorted(source.items())) in sources for source in entry['sources'])]
        items.append({**row, 'existing_entry_candidates': existing,
                      'review': {'decision': 'pending', 'preferred_form': '', 'canonical_tl': '',
                                 'alternate_readings': [], 'identity_note': '', 'editorial_rationale': ''}})
    report = {'schema_version': 1, 'kind': 'related-moe-human-review', 'seeds': seeds,
              'state': {'entries_sha256': lex.entry_state(root, current), 'moe_sha256': evidence[1][0]['sha256']},
              'moe_snapshot': evidence[1][0]['id'],
              'implementation_sha256': digest([Path(path).read_text() for path in
                  (__file__, lex.__file__, combos.__file__)]), 'items': items}
    report['evidence_sha256'] = digest(evidence_body(report))
    # Refuse a report combining two repository snapshots.
    after = [(path, entry) for path, entry, _ in lex.entry_snapshot(root)]
    if lex.entry_state(root, after) != report['state']['entries_sha256']:
        raise lex.Error('Entries changed during discovery; rerun related.')
    return report


def reviewed_request(item):
    review = item['review']
    preferred, reading = review.get('preferred_form'), review.get('canonical_tl')
    if not isinstance(preferred, str) or not preferred.strip() or not isinstance(reading, str):
        raise lex.Error('Each approved related entry needs its human-selected preferred form and reading.')
    options = {lex.key(option['canonical_tl']): option for option in item['reading_options']}
    alternates = review.get('alternate_readings', [])
    if (not isinstance(alternates, list) or any(not isinstance(value, str) for value in alternates)
            or lex.key(reading) not in options or any(lex.key(value) not in options for value in alternates)):
        raise lex.Error('Choose canonical and alternate readings from this related MOE entry’s sourced reading options.')
    chosen = [reading, *alternates]
    if len({lex.key(value) for value in chosen}) != len(chosen):
        raise lex.Error('Canonical and alternate readings must be distinct.')
    note = review.get('identity_note', '')
    rationale = review.get('editorial_rationale', '')
    if not isinstance(note, str) or not isinstance(rationale, str):
        raise lex.Error('Review identity notes and rationale must be text.')
    if item['existing_entry_candidates'] and not note.strip():
        raise lex.Error('Related entry overlaps existing entries; resolve identity explicitly before importing a separate word.')
    sources = [item['source']]
    for value in chosen:
        for reference in options[lex.key(value)]['references']:
            if reference['source'] not in sources:
                sources.append(reference['source'])
    form = preferred.strip()
    request = lex.normalize_request({'preferred_form': form, 'canonical_tl': reading,
        'alternate_readings': alternates,
        'moe_forms': sorted({re.sub(r'【[^】]*】', '', item['headword']).strip()} - {form}),
        'sources': sources, 'review_status': 'reviewed'})
    if note.strip():
        request['identity_note'] = unicodedata.normalize('NFC', note.strip())
    if rationale.strip():
        request['editorial_rationale'] = unicodedata.normalize('NFC', rationale.strip())
    return request


def import_reviewed(root, report, apply=False):
    if not isinstance(report, dict) or report.get('schema_version') != 1 or report.get('kind') != 'related-moe-human-review':
        raise lex.Error('Unsupported related-entry human review file.')
    if (not isinstance(report.get('items'), list) or any(not isinstance(item, dict) for item in report['items'])
            or not isinstance(report.get('seeds'), list) or any(not isinstance(seed, str) for seed in report['seeds'])):
        raise lex.Error('Related-entry review needs a list of Hanji seeds and entry objects.')
    if report.get('evidence_sha256') != digest(evidence_body(report)):
        raise lex.Error('Related-entry evidence changed; edit only each item’s review fields.')
    fresh = find(root, report['seeds'])
    if fresh['evidence_sha256'] != report['evidence_sha256']:
        raise lex.Error('Related-entry evidence is stale; regenerate and human-review the updated report.')
    requests, counts = [], defaultdict(int)
    for item in report['items']:
        review = item.get('review')
        if (not isinstance(review, dict) or not isinstance(review.get('decision'), str)
                or review['decision'] not in {'pending', 'approved', 'rejected'}):
            raise lex.Error('Every related entry needs an individual pending, approved or rejected human decision.')
        counts[review['decision']] += 1
        if review['decision'] == 'approved':
            requests.append(reviewed_request(item))
    result = {'mode': 'apply' if apply else 'preview', 'approved': counts['approved'],
              'pending': counts['pending'], 'rejected': counts['rejected'], 'results': []}
    if requests:
        batch = lex.add_batch(root, requests, dry_run=not apply, expected_state=report['state'])
        result['results'] = batch['results']
        if apply:
            lex.validate(root)
    return result


def markdown(report):
    def inline(value):
        return str(value).replace('`', '\\`').replace('\n', ' ')

    lines = ['# Related MOE entries — individual human review required', '',
             'Hanji seeds: ' + ', '.join(report['seeds']), '']
    for item in report['items']:
        lines += [f"## {inline(item['headword'])} — MOE {item['record_id']}", '',
                  f"Human decision: **{item['review']['decision']}**", '',
                  'Patterns: ' + '; '.join(f"{r['base_form']} → {r['matched_form']} ({r['pattern']})" for r in item['relations']), '',
                  'MOE definition: ' + inline(' / '.join(item['definitions'])), '',
                  'MOE readings: ' + ', '.join(inline(option['canonical_tl']) for option in item['reading_options']), '',
                  'MOE source: ' + inline(json.dumps(item['source'], ensure_ascii=False)), '']
        if item['existing_entry_candidates']:
            lines += ['Existing entries require identity review: ' + ', '.join(
                f"#{entry['id']} {inline(entry['preferred_form'])}" for entry in item['existing_entry_candidates']), '']
        for proposal in item['writing_suggestions']:
            lines += [f"### {inline(proposal['hanji_form'])} ({inline(proposal['canonical_tl'])})", '',
                      'Suggested form: ' + (f"**{inline(proposal['suggested_form'])}**" if proposal['suggested_form'] else
                                            f"manual review ({proposal['status']})"), '']
            for position in proposal['positions']:
                lines += [f"- {inline(position['hanji'])} / {inline(position['canonical_tl'])}: {position['status']}"]
                for choice in position['choices']:
                    lines += [f"  - {choice['kind']}: **{inline(choice['token'])}**"]
                    for entry in choice['evidence']:
                        lines += [f"    - [#{entry['entry_id']} {inline(entry['preferred_form'])}]({entry['path']}) "
                                  f"({inline(entry['canonical_tl'])}); {entry['review_status']}; original sources: " +
                                  inline(json.dumps(entry['sources'], ensure_ascii=False))]
            lines += ['']
        if not item['writing_suggestions']:
            lines += ['Shorter related word: choose its spelling and readings during human review.', '']
    return '\n'.join(lines) + '\n'
