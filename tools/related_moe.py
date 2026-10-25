"""Combo-matched MOE discovery, writing evidence, and individual human review."""

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
    for index, position in enumerate(positions):
        choice, = position['choices']
        roman = choice['kind'] == 'romanized'
        token = choice['token']
        separator = choice.get('separator', '')
        if separator and (index or separator == '--'):
            result += separator
        elif roman and not token.startswith('--') and previous_roman:
            result += '-'
        result += token
        previous_roman = roman
    return result


def aligned_combos(form, reading):
    """One literal Hanji/TL pair per position; contractions cannot prove a match."""
    if not lex.hanji_glyphs(form):
        return None
    try:
        syllables = combos.reading_units(reading)
        units = combos.written_units(form, syllables)
    except combos.AlignmentError:
        return None
    return tuple((unit['text'], combos.tl_key(syllable)) for unit, syllable in zip(units, syllables))


class SeedComboIndex:
    """Keep complete sourced seed readings and identities, never a syllable pool."""

    def __init__(self, records=(), resolver=None):
        self.by_form = defaultdict(list)
        if resolver is not None:
            self.dictionary_forms, self.dictionary_sources = resolver.dictionary_forms, resolver.dictionary_sources
            return
        self.dictionary_forms, self.dictionary_sources = defaultdict(list), defaultdict(list)
        for record in records:
            for form in {record['headword'], *record['variant_forms']}:
                self.dictionary_forms[lex.annotation_key(form)].append(record)
            self.dictionary_sources[tuple(sorted(record['source'].items()))].append(record)

    def forms_for(self, entry):
        forms = {entry['preferred_form'], *entry.get('moe_forms', []), *entry.get('hanji_forms', [])}
        readings = {lex.key(entry['canonical_tl']), *(lex.key(value) for value in entry.get('alternate_readings', []))}
        records = [record for form in forms for record in self.dictionary_forms.get(lex.annotation_key(form), [])]
        records += [record for source in entry.get('sources', [])
                    for record in self.dictionary_sources.get(tuple(sorted(source.items())), [])]
        for record in records:
            if readings & lex.reading_keys(record['reading']):
                forms.update([record['headword'], *record['variant_forms']])
        return {''.join(glyphs) for form in forms if len(glyphs := lex.hanji_glyphs(form)) in (2, 3)}

    def add_entry(self, entry, forms=None):
        for form in self.forms_for(entry) if forms is None else forms:
            for reading in [entry['canonical_tl'], *entry.get('alternate_readings', [])]:
                sequence = aligned_combos(form, reading)
                if sequence is not None:
                    try:
                        written = lex.written_form(entry['preferred_form'], entry['canonical_tl'], reading)
                    except lex.Error:
                        written = None
                    item = {'entry_id': entry.get('id'), 'preferred_form': entry['preferred_form'],
                            'written_form': written,
                            'reading': reading, 'combos': sequence, 'sources': entry.get('sources', [])}
                    if item not in self.by_form[form]:
                        self.by_form[form].append(item)

    def match(self, relation, option):
        target = aligned_combos(relation['matched_form'], option['canonical_tl'])
        if target is None:
            return []
        seed_start, target_start = 0, 0
        pattern = relation['pattern']
        if pattern == 'BC':
            seed_start = 1
        elif pattern.startswith('X'):
            target_start = len(target) - len(lex.hanji_glyphs(relation['base_form']))
        length = min(len(target), len(lex.hanji_glyphs(relation['base_form'])))
        proofs = []
        for source in self.by_form.get(relation['base_form'], []):
            shared = source['combos'][seed_start:seed_start + length]
            if len(shared) == length and shared == target[target_start:target_start + length]:
                proof = {'seed_entry_id': source['entry_id'], 'seed_preferred_form': source['preferred_form'],
                         'seed_written_form': source['written_form'],
                         'seed_reading': source['reading'], 'related_reading': option['canonical_tl'],
                         'seed_sources': source['sources'],
                         'shared_combos': [{'hanji': hanji, 'canonical_tl': tl} for hanji, tl in shared]}
                if proof not in proofs:
                    proofs.append(proof)
        return proofs


class WritingIndex:
    def __init__(self, root, current, records):
        self.seed_resolver = SeedComboIndex(records)
        inventory = combos.derive([(path, entry) for path, entry in current
                                   if entry['review_status'] != 'disputed'])
        self.combos = {(item['hanji'], item['canonical_tl']): item for item in inventory['combos']}
        self.entries = {item['entry_id']: item for item in inventory['entries']}
        self.records = defaultdict(list)
        for record in records:
            self.records[record['record_id']].append(record)

    def proposal(self, form, option, relations=()):
        result = {'hanji_form': form, **option, 'requires_human_review': True,
                  'suggested_form': None, 'positions': []}
        try:
            reading = combos.reading_units(option['canonical_tl'])
            units = combos.written_units(form, reading)
        except combos.AlignmentError as error:
            return dict(result, status='unalignable', reason=str(error))
        inherited = defaultdict(dict)
        for relation in relations:
            for proof in relation['combo_matches']:
                identity = proof['seed_entry_id']
                if (identity not in self.entries or not proof.get('seed_written_form')
                        or self.entries[identity].get('rule_generated')
                        or lex.key(proof['related_reading']) != lex.key(option['canonical_tl'])):
                    continue
                try:
                    seed_units = combos.written_units(proof['seed_written_form'],
                                                     combos.reading_units(proof['seed_reading']))
                except combos.AlignmentError:
                    continue
                seed_start = 1 if relation['pattern'] == 'BC' else 0
                target_start = len(units) - len(seed_units) if relation['pattern'].startswith('X') else 0
                length = len(proof['shared_combos'])
                for offset in range(length):
                    unit = seed_units[seed_start + offset]
                    position = target_start + offset
                    separator = unit['separator'] if position or unit['separator'] == '--' else ''
                    key = unit['kind'], unit['text'], separator
                    choice = inherited[position].setdefault(key, {
                        'kind': unit['kind'], 'token': unit['text'], 'separator': separator,
                        'entry_ids': [], 'evidence': []})
                    if identity not in choice['entry_ids']:
                        choice['entry_ids'].append(identity)
                        choice['evidence'].append(self.entries[identity])
        for index, (unit, syllable) in enumerate(zip(units, reading)):
            tl = combos.tl_key(syllable)
            found = self.combos.get((unit['text'], tl))
            choices = [{**output, 'evidence': [self.entries[identity] for identity in output['entry_ids']]}
                       for output in found['outputs']] if found else []
            position = {'hanji': unit['text'], 'canonical_tl': tl,
                        'status': found['status'] if found else 'unknown', 'choices': choices}
            if inherited[index]:
                anchored = list(inherited[index].values())
                for choice in anchored:
                    choice['support_count'] = len(choice['entry_ids'])
                position.update(inventory_status=position['status'], inventory_choices=choices,
                                inherited_from_seed=True, choices=anchored,
                                status='conflicting' if len(anchored) > 1 else
                                       'consistent_' + anchored[0]['kind'])
            result['positions'].append(position)
        if any(len(position['choices']) > 1 for position in result['positions']):
            result['status'] = 'conflicting'
        elif any(not position['choices'] for position in result['positions']):
            result['status'] = 'incomplete'
        else:
            result['status'] = 'consistent'
            result['suggested_form'] = render_choices(result['positions'])
        return result

    def annotate(self, related, seeds):
        result = []
        for row in related:
            options = reading_options(self.records[row['record_id']])
            relations, matched = [], set()
            for relation in row['relations']:
                proofs = [proof for option in options for proof in seeds.match(relation, option)]
                if proofs:
                    relations.append({**relation, 'combo_matches': proofs})
                    matched.update(lex.key(proof['related_reading']) for proof in proofs)
            if not relations:
                continue
            options = [option for option in options if lex.key(option['canonical_tl']) in matched]
            forms = sorted({relation['matched_form'] for relation in relations
                            if len(lex.hanji_glyphs(relation['matched_form'])) >
                            len(lex.hanji_glyphs(relation['base_form']))
                            or any(proof['seed_entry_id'] is not None for proof in relation['combo_matches'])})
            proposals = [self.proposal(form, option, [relation for relation in relations
                         if relation['matched_form'] == form]) for form in forms for option in options
                         if any(relation['matched_form'] == form and seeds.match(relation, option)
                                for relation in relations)]
            main_form = re.sub(r'【[^】]*】', '', row['headword']).strip()
            result.append({**row, 'relations': relations, 'requires_human_review': True, 'reading_options': options,
                'writing_suggestions': [p for p in proposals if p['hanji_form'] == main_form],
                'variant_writing_suggestions': [p for p in proposals if p['hanji_form'] != main_form]})
        return result


def evidence_body(report):
    return {**{name: value for name, value in report.items() if name not in {'items', 'evidence_sha256'}},
            'items': [{name: value for name, value in item.items() if name != 'review'} for item in report['items']]}


def find(root, seeds, seed_entry_ids=None):
    """Standalone combo discovery from existing entries or exact MOE seed forms."""
    seeds = sorted({unicodedata.normalize('NFC', seed) for seed in seeds})
    if not seeds or any(len(lex.hanji_glyphs(seed)) not in (2, 3) for seed in seeds):
        raise lex.Error('Supply literal two- or three-Hanji forms, without romanization or separators.')
    current = [(path, entry) for path, entry, _ in lex.entry_snapshot(root)]
    evidence = lex.lkk_data(root), lex.moe_data(root)
    lookup = lex.LookupIndex(current, evidence)
    if seed_entry_ids is not None:
        if (not isinstance(seed_entry_ids, list) or any(type(identity) is not int for identity in seed_entry_ids)
                or set(seed_entry_ids) - {entry['id'] for _, entry in current}):
            raise lex.Error('Seed entry IDs must identify existing entries.')
        seed_entry_ids = sorted(set(seed_entry_ids))
    seed_combos, claimed, seed_forms = SeedComboIndex(evidence[1][2]), set(), set(seeds)
    selected_ids = set(seed_entry_ids) if seed_entry_ids is not None else None
    for _, entry in current:
        if selected_ids is not None and entry['id'] not in selected_ids:
            continue
        forms = seed_combos.forms_for(entry)
        if forms & seed_forms:
            claimed.update(forms)
            seed_combos.add_entry(entry, forms)
    if seed_entry_ids is None:
        for seed in set(seeds) - claimed:
            for option in reading_options(seed_combos.dictionary_forms.get(seed, [])):
                sources = []
                for reference in option['references']:
                    if reference['source'] not in sources:
                        sources.append(reference['source'])
                seed_combos.add_entry({'preferred_form': seed, 'canonical_tl': option['canonical_tl'], 'sources': sources}, {seed})
    candidate = {'preferred_form': seeds[0], 'moe_forms': seeds[1:]}
    matches = lookup.moe.matching({lex.key(seed) for seed in seeds}, set())
    related = lookup.related_moe.suggest(candidate, matches)
    related = WritingIndex(root, current, evidence[1][2]).annotate(related, seed_combos)
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
    report = {'schema_version': 1, 'kind': 'related-moe-human-review', 'seeds': seeds, 'seed_entry_ids': seed_entry_ids,
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
    status = review.get('review_status', 'reviewed')
    if status not in {'reviewed', 'machine-reviewed'}:
        raise lex.Error('Related review status must be reviewed or machine-reviewed.')
    if status == 'machine-reviewed' and review_category(item) != 'Consistent proposals':
        raise lex.Error('Batch machine-reviewed imports require consistent complete spelling proposals.')
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
        'sources': sources, 'review_status': status})
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
    fresh = find(root, report['seeds'], report.get('seed_entry_ids'))
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


def support_sides(position):
    """Count distinct supporting entries per writing kind; show at most three."""
    result = []
    for kind in ('hanji', 'romanized'):
        entries, tokens = {}, []
        for choice in position['choices']:
            if choice['kind'] != kind:
                continue
            if choice['token'] not in tokens:
                tokens.append(choice['token'])
            for entry in choice['evidence']:
                entries[entry['entry_id']] = entry
        examples, spellings = [], set()
        for identity in sorted(entries):
            entry = entries[identity]
            if entry['preferred_form'] not in spellings:
                examples.append(entry)
                spellings.add(entry['preferred_form'])
            if len(examples) == 3:
                break
        result.append({'kind': kind, 'tokens': tokens, 'entry_count': len(entries), 'examples': examples})
    return result


def conflict_summary(item):
    """Show each tone-preserving conflict once, even across multiple readings."""
    conflicts = {}
    for proposal in item['writing_suggestions']:
        for position in proposal['positions']:
            if position['status'] == 'conflicting':
                conflicts.setdefault((position['hanji'], position['canonical_tl']), position)
    lines = []
    for (hanji, reading), position in conflicts.items():
        sides = []
        for side in support_sides(position):
            label = 'Hanji' if side['kind'] == 'hanji' else 'Romanized'
            examples = ', '.join(entry['preferred_form'] for entry in side['examples'])
            sides.append(f"{label} {side['entry_count']}" + (f" ({examples})" if examples else ''))
        lines.append(f"{hanji}/{reading}: " + '; '.join(sides))
    return ' / '.join(lines) or 'None'


def review_category(item):
    statuses = {proposal['status'] for proposal in item['writing_suggestions']}
    if 'conflicting' in statuses:
        return 'Combo conflict'
    if statuses & {'incomplete', 'unalignable'}:
        return 'Incomplete or unalignable'
    return 'Consistent proposals' if statuses else 'No canonical spelling proposal'


def index_markdown(report, seed_entries, pages):
    """New-only table; seed spellings explain why each related word was found."""
    def cell(value):
        return str(value).replace('|', '\\|').replace('\n', ' ')

    items = [item for item in report['items'] if not item['existing_entry_candidates']
             and item['review']['decision'] != 'rejected']
    hidden = sum(bool(item['existing_entry_candidates']) for item in report['items'])
    rejected = sum(not item['existing_entry_candidates'] and item['review']['decision'] == 'rejected'
                   for item in report['items'])
    lines = ['# New related MOE entries — human review', '',
             f"**{len(items)} new candidates** shown; **{hidden}** rows with existing-entry candidates hidden.", '',
             f"**{rejected}** explicitly rejected candidates omitted.", '',
             'The existing seed column shows only entries whose shared Hanji/TL combos actually matched the related reading. '
             'An existing-entry candidate for the related word means a shared Hanji form or MOE source identity; '
             'it is a possible identity match, not proof of a duplicate. Those rows are omitted from this table.', '',
             'Proposals retain the matching seed spelling, including shorter words obtained by removing its extra units. '
             'Only added positions need fresh writing choices. Dictionary variants have separate evidence sections. '
             'Conflict counts are distinct supporting entries for the exact Hanji/TL combo. '
             'Each side shows at most three example preferred spellings. Counts do not decide the writing; '
             'every row remains pending individual human review. Full original evidence remains in the JSON report.', '',
             '| Related MOE entry / evidence | Existing seed entries — preferred forms | Sourced readings | Proposed form of new word | Combo conflicts — support counts and examples | Review issue |',
             '| --- | --- | --- | --- | --- | --- |']
    for item in sorted(items, key=lambda row: (review_category(row), row['headword'], row['record_id'])):
        seeds = sorted({relation['base_form'] for relation in item['relations']})
        matched_ids = {proof['seed_entry_id'] for relation in item['relations'] for proof in relation.get('combo_matches', [])}
        existing = {entry['id']: entry for seed in seeds for entry in seed_entries.get(seed, [])
                    if entry['id'] in matched_ids}
        existing.update({proof['seed_entry_id']: {'preferred_form': proof['seed_preferred_form']}
                         for relation in item['relations'] for proof in relation.get('combo_matches', [])
                         if proof['seed_entry_id'] is not None})
        seed_forms = ' / '.join(f"{entry['preferred_form']} (#{identity})" for identity, entry in sorted(existing.items())) or ' / '.join(seeds)
        proposed = list(dict.fromkeys(proposal['suggested_form'] for proposal in item['writing_suggestions'] if proposal['suggested_form']))
        readings = list(dict.fromkeys(option['canonical_tl'] for option in item['reading_options']))
        path = Path(pages) / f"moe-{item['record_id']}-row-{item['source']['row']}.md"
        unknown = sorted({f"{position['hanji']}/{position['canonical_tl']}"
                          for proposal in item['writing_suggestions'] for position in proposal['positions']
                          if not position['choices']})
        issue = review_category(item) + (': ' + ', '.join(unknown) if unknown else '')
        values = [f"[{cell(item['headword'])} — MOE {item['record_id']}]({path})", cell(seed_forms),
                  cell(' / '.join(readings)), cell(' / '.join(proposed) or 'Human choice needed'),
                  cell(conflict_summary(item)), cell(issue)]
        lines.append('| ' + ' | '.join(values) + ' |')
    return '\n'.join(lines) + '\n'


def write_markdown(report, path):
    """Publish a new-only index with separate, sourced pages per candidate."""
    path = Path(path)
    pages = path.with_name(path.stem + '-entries')
    for item in report['items']:
        if item['existing_entry_candidates'] or item['review']['decision'] == 'rejected':
            continue
        target = pages / f"moe-{item['record_id']}-row-{item['source']['row']}.md"
        lex.atomic_write(target, markdown(dict(report, items=[item])))
    lex.atomic_write(path, index_markdown(report, {}, pages))


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
        proofs = [proof for relation in item['relations'] for proof in relation.get('combo_matches', [])]
        if proofs:
            lines += ['Matching seed combos:', '']
            for proof in proofs:
                identity = f" (#{proof['seed_entry_id']})" if proof['seed_entry_id'] is not None else ''
                pairs = ', '.join(f"{pair['hanji']}/{pair['canonical_tl']}" for pair in proof['shared_combos'])
                lines += [f"- {inline(proof['seed_preferred_form'])}{identity} ({inline(proof['seed_reading'])}) "
                          f"→ {inline(proof['related_reading'])}: {inline(pairs)}"]
            lines += ['']
        if item['existing_entry_candidates']:
            lines += ['Existing entries require identity review: ' + ', '.join(
                f"#{entry['id']} {inline(entry['preferred_form'])}" for entry in item['existing_entry_candidates']), '']
        for proposal, variant in ([(p, False) for p in item['writing_suggestions']] +
                                  [(p, True) for p in item.get('variant_writing_suggestions', [])]):
            label = 'Dictionary variant: ' if variant else ''
            lines += [f"### {label}{inline(proposal['hanji_form'])} ({inline(proposal['canonical_tl'])})", '',
                      'Suggested form: ' + (f"**{inline(proposal['suggested_form'])}**" if proposal['suggested_form'] else
                                            f"manual review ({proposal['status']})"), '']
            if variant:
                lines += ['Separate variant evidence; this does not change the main headword proposal.', '']
            for position in proposal['positions']:
                lines += [f"- {inline(position['hanji'])} / {inline(position['canonical_tl'])}: {position['status']}"]
                if position.get('inherited_from_seed'):
                    lines += ['  - Retained from the matching existing seed spelling; full inventory evidence remains in JSON.']
                for side in support_sides(position):
                    if not side['entry_count'] and position['status'] != 'conflicting':
                        continue
                    lines += [f"  - {side['kind']}: **{inline(' / '.join(side['tokens']) or 'none')}** — "
                              f"**{side['entry_count']} supporting entries**; up to 3 example preferred forms:"]
                    for entry in side['examples']:
                        lines += [f"    - [#{entry['entry_id']} {inline(entry['preferred_form'])}]({entry['path']}) "
                                  f"({inline(entry['canonical_tl'])}); {entry['review_status']}; original sources: " +
                                  inline(json.dumps(entry['sources'], ensure_ascii=False))]
            lines += ['']
        if not item['writing_suggestions']:
            lines += ['No aligned canonical-headword spelling is available; inspect the separate variant/seed evidence.', '']
    return '\n'.join(lines) + '\n'
