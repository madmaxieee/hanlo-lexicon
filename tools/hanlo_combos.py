#!/usr/bin/env python3
"""Read-only Hanji/canonical-TL evidence inventory. No spelling generation/import."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata as ud

import lexicon

# Bump when alignment, evidence, or report semantics change. The code fingerprint
# also invalidates local edits before a version bump reaches a commit.
DERIVATION_VERSION = 1
CACHE_DIRECTORY = Path('.cache/hanlo-combos')


class AlignmentError(ValueError):
    pass


def hanji(char):
    # Iteration marks (々/〆) are not independent Hanji/readings. Do not expand them.
    return ud.name(char, '').startswith(('CJK UNIFIED IDEOGRAPH-', 'CJK COMPATIBILITY IDEOGRAPH-')) or char == '〇'


def latin(char):
    return 'LATIN' in ud.name(char, '')


def reading_units(reading):
    """Retain tones and the neutral prefix; never convert or infer readings."""
    matches = list(re.finditer(r'[^\s-]+', reading))
    if not matches:
        raise AlignmentError('empty canonical reading')
    units = []
    previous = 0
    for match in matches:
        separator = reading[previous:match.start()]
        if separator not in ('', '-', '--') and not separator.isspace():
            raise AlignmentError('unsupported canonical separator')
        if previous == 0 and not units and separator == '-':
            raise AlignmentError('single leading canonical hyphen')
        token = match.group()
        if not latin(token[0]) or any(not (latin(c) or ud.category(c).startswith('M')) for c in token):
            raise AlignmentError('unsupported canonical syllable')
        units.append({'text': token, 'neutral': separator == '--'})
        previous = match.end()
    if reading[previous:]:
        raise AlignmentError('trailing canonical separator')
    return units


def written_units(form, reading):
    """Accept one literal Hanji or matching Roman syllable per canonical unit.

    Ordinary Hanji adjacency can leave separators implicit. Explicit -- must
    match canonical neutral tone. Adjacent Roman syllables need a separator;
    punctuation, contractions, iteration marks and nonliteral mappings skip.
    """
    units, cursor, separator = [], 0, ''
    while cursor < len(form):
        char = form[cursor]
        if char == '-' or char.isspace():
            separator += char
            cursor += 1
            continue
        start = cursor
        if hanji(char):
            cursor += 1
            # Variation selectors are glyph data, not ignorable punctuation.
            while cursor < len(form) and (0xFE00 <= ord(form[cursor]) <= 0xFE0F or 0xE0100 <= ord(form[cursor]) <= 0xE01EF):
                cursor += 1
            kind = 'hanji'
        elif latin(char):
            cursor += 1
            while cursor < len(form) and (latin(form[cursor]) or ud.category(form[cursor]).startswith('M')):
                cursor += 1
            kind = 'romanized'
        else:
            raise AlignmentError('unsupported written character')
        if separator not in ('', '-', '--') and not separator.isspace():
            raise AlignmentError('unsupported written separator')
        if not units and separator == '-':
            raise AlignmentError('single leading written hyphen')
        units.append({'text': form[start:cursor], 'kind': kind, 'separator': separator})
        separator = ''
    if separator:
        raise AlignmentError('trailing written separator')
    if len(units) != len(reading):
        raise AlignmentError('syllable count mismatch (possible contraction)')
    for index, (unit, syllable) in enumerate(zip(units, reading)):
        sep = unit['separator']
        explicit_neutral = sep == '--'
        if explicit_neutral and not syllable['neutral']:
            raise AlignmentError('neutral-tone boundary mismatch')
        # A written separator, or a leading Roman syllable, explicitly chooses
        # its tone boundary. Hanji adjacency otherwise leaves it implicit.
        explicit = bool(sep) or (index == 0 and unit['kind'] == 'romanized')
        if explicit and explicit_neutral != syllable['neutral']:
            raise AlignmentError('neutral-tone boundary mismatch')
        if unit['kind'] == 'romanized' and lexicon.key(unit['text']) != lexicon.key(syllable['text']):
            raise AlignmentError('Roman syllable differs from canonical reading')
    return units


def tl_key(syllable):
    return ('--' if syllable['neutral'] else '') + lexicon.key(syllable['text'])


def derive(current):
    """Derive from parsed authoritative entries; each entry gets one vote/output."""
    combos, audit, excluded, words = {}, [], [], {}

    def skip(entry, field, value, reason):
        audit.append({'entry_id': entry['id'], 'field': field, 'value': value, 'reason': reason})

    def combo(glyph, syllable):
        pair = glyph, tl_key(syllable)
        return combos.setdefault(pair, {'hanji': pair[0], 'canonical_tl': pair[1], 'observed': set(), 'outputs': {}})

    for path, entry in sorted(current, key=lambda item: item[1]['id']):
        entry_id = entry['id']
        words[entry_id] = {
            'entry_id': entry_id, 'path': path.as_posix(),
            **{name: entry[name] for name in ('preferred_form', 'canonical_tl', 'review_status', 'sources')},
            **{name: entry[name] for name in ('identity_note', 'rule_generated', 'editorial_rationale', 'usage_notes') if name in entry},
        }
        generated = entry.get('rule_generated') is True
        if generated:
            excluded.append(entry_id)
        try:
            reading = reading_units(entry['canonical_tl'])
        except AlignmentError as exc:
            skip(entry, 'canonical_tl', entry['canonical_tl'], str(exc))
            continue
        try:
            preferred = written_units(entry['preferred_form'], reading)
        except AlignmentError as exc:
            preferred = None
            skip(entry, 'preferred_form', entry['preferred_form'], str(exc))
        references = []
        for field in ('moe_forms', 'hanji_forms'):
            for form in sorted(set(entry.get(field, []))):
                try:
                    units = written_units(form, reading)
                    if any(unit['kind'] != 'hanji' for unit in units):
                        raise AlignmentError('reference form is not entirely Hanji')
                    references.append(units)
                except AlignmentError as exc:
                    skip(entry, field, form, str(exc))
        # The preferred form itself supplies only its literally Han-written
        # positions. No Hanji is invented for Roman positions lacking metadata.
        if preferred is not None:
            references.append(preferred)
        found = False
        for units in references:
            for index, unit in enumerate(units):
                if unit['kind'] != 'hanji':
                    continue
                found = True
                item = combo(unit['text'], reading[index])
                item['observed'].add(entry_id)
                if preferred is None or generated:
                    continue
                output = preferred[index]
                # Neutrality belongs to canonical TL, also retained in Roman
                # output even when adjacent Hanji leave its boundary implicit.
                token = ('--' if reading[index]['neutral'] and output['kind'] == 'romanized' else '') + output['text']
                choice = item['outputs'].setdefault((output['kind'], token), set())
                choice.add(entry_id)
        if not found:
            skip(entry, 'hanji_reference', '', 'no safely aligned Hanji positions')

    results = []
    for _, item in sorted(combos.items()):
        outputs = [
            {'kind': kind, 'token': token, 'support_count': len(ids), 'entry_ids': sorted(ids)}
            for (kind, token), ids in sorted(item['outputs'].items())
        ]
        status = ('unknown' if not outputs else 'conflicting' if len(outputs) > 1 else 'consistent_' + outputs[0]['kind'])
        supporting = set().union(*(set(output['entry_ids']) for output in outputs))
        results.append({
            'hanji': item['hanji'], 'canonical_tl': item['canonical_tl'],
            'status': status, 'support_count': len(supporting),
            'observed_entry_ids': sorted(item['observed']), 'outputs': outputs,
        })
    counts = Counter(item['status'] for item in results)
    return {
        'derivation_version': DERIVATION_VERSION,
        'summary': {
            'entries': len(current), 'combos': len(results),
            **{status: counts[status] for status in ('consistent_romanized', 'consistent_hanji', 'conflicting', 'unknown')},
            'single_support_combos': sum(item['support_count'] == 1 for item in results),
            'skipped_inputs': len(audit), 'entries_with_skips': len({item['entry_id'] for item in audit}),
            'excluded_generated_entries': len(excluded),
        },
        'combos': results, 'skipped_inputs': audit,
        'excluded_generated_entry_ids': excluded, 'entries': list(words.values()),
    }


def json_text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n'


def fingerprint(root):
    """Hash every byte/path of real inputs, including alignment/schema code."""
    digest = hashlib.sha256(f'hanlo-combos:{DERIVATION_VERSION}\n'.encode())
    for name, path in sorted([
        *((path.relative_to(root).as_posix(), path) for path in lexicon.entry_files(root)),
        ('schema/entry.schema.json', root / 'schema/entry.schema.json'),
        ('implementation/hanlo_combos.py', Path(__file__)),
        ('implementation/lexicon.py', Path(lexicon.__file__)),
    ]):
        data = path.read_bytes()
        digest.update(json_text([name, len(data)]).encode())
        digest.update(data)
    return digest.hexdigest()


def markdown(inventory):
    """Use full-width sections and one supporting word per line for narrow panes."""
    summary = inventory['summary']
    words = {entry['entry_id']: entry for entry in inventory['entries']}

    def inline(value):
        text = str(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', ' ')
        return re.sub(r'([\\`*_{}\[\]#|])', r'\\\1', text)

    def word(entry_id):
        entry = words[entry_id]
        return f"#{entry_id} {inline(entry['preferred_form'])} ({inline(entry['canonical_tl'])})"

    def support(ids):
        for entry_id in ids:
            entry = words[entry_id]
            lines.extend([f'- {word(entry_id)}', ''])
            for field, label in (('editorial_rationale', 'Editorial decision'), ('identity_note', 'Identity'), ('usage_notes', 'Usage')):
                if field in entry:
                    lines.extend([f'  {label}: {inline(entry[field])}', ''])

    def count(value, noun):
        plural = noun[:-1] + 'ies' if noun.endswith('entry') else noun + 's'
        return f'{value} {noun if value == 1 else plural}'

    lines = [
        '# Han-Lo combo inventory', '',
        'Derived local evidence. Generating this report does not approve or import spellings. Entry TOML remains authoritative.', '',
        f"Derivation version: {inventory['derivation_version']}.", '',
        'Only canonical readings contribute. Each entry contributes once per combo/output. '
        'Rule-generated entries supply no recommendation votes. Support is separate from consistency; '
        'a conflict may reflect different meanings and must not be settled by majority vote. '
        'Whole-word recommendations take precedence over any future composed suggestion.', '',
        '| Measure | Count |', '| --- | ---: |',
        *[f'| {name.replace("_", " ")} | {value} |' for name, value in summary.items()], '',
    ]
    for status in ('conflicting', 'unknown', 'consistent_romanized', 'consistent_hanji'):
        items = [item for item in inventory['combos'] if item['status'] == status]
        lines.extend([f'## {status.replace("_", " ").title()}', '', f'{count(len(items), "combo")}.', ''])
        for item in items:
            lines.extend([
                f"### {inline(item['hanji'])} · {inline(item['canonical_tl'])}", '',
                f"{count(item['support_count'], 'supporting entry')} · {count(len(item['outputs']), 'output')}", '',
            ])
            for output in item['outputs']:
                kind = 'Hanji' if output['kind'] == 'hanji' else 'Romanized'
                lines.extend([f"**Output: {inline(output['token'])}** — {kind}; {count(output['support_count'], 'supporting entry')}.", ''])
                support(output['entry_ids'])
            if not item['outputs']:
                lines.extend(['Observed only; no eligible recommendation evidence.', ''])
                support(item['observed_entry_ids'])
    lines.extend(['## Skipped inputs', ''])
    skipped = {}
    for item in inventory['skipped_inputs']:
        skipped.setdefault(item['entry_id'], []).append(item)
    for entry_id, items in skipped.items():
        lines.extend([f'### {word(entry_id)}', ''])
        for item in items:
            value = inline(item['value']) or '(no Hanji reference)'
            lines.extend([f"- **{inline(item['field'])}: {value}** — {inline(item['reason'])}.", ''])
    lines.extend([
        '## Provenance', '',
        'Source references establish provenance; they do not by themselves endorse a spelling. Full entry metadata is also retained in inventory.json.', '',
    ])
    for entry in inventory['entries']:
        lines.extend([
            f"### {word(entry['entry_id'])}", '',
            f"Path: {inline(entry['path'])}", '',
            f"Review status: {inline(entry['review_status'])}.", '',
        ])
        for field, label in (('editorial_rationale', 'Editorial decision'), ('identity_note', 'Identity'), ('usage_notes', 'Usage')):
            if field in entry:
                lines.extend([f'{label}: {inline(entry[field])}', ''])
        for source in entry['sources']:
            if 'url' in source:
                # Entry schema/source checks restrict citations to HTTP(S).
                url = source['url'].replace('(', '%28').replace(')', '%29')
                citation = f"[Original source]({url}) — {inline(source['locator'])}"
            else:
                parts = [source['snapshot']]
                if 'sheet' in source:
                    parts.append(source['sheet'])
                parts.append(f"row {source['row']}")
                citation = ' · '.join(inline(part) for part in parts)
            lines.extend([f'- {citation}', ''])
    lines.extend([
        'Excluded rule-generated entry IDs: ' + (', '.join(map(str, inventory['excluded_generated_entry_ids'])) or 'none') + '.', '',
        f"Input fingerprint: {inventory['fingerprint']}", '',
    ])
    return '\n'.join(lines)


def build(root):
    """Publish a cache from a coherent input snapshot; never touch entry data."""
    root = root.resolve()
    if not (root / 'entries').is_dir():
        raise lexicon.Error(f'No entries directory under {root}')
    cache = root / CACHE_DIRECTORY
    # Coordinate with maintenance add/format writers; readers need a stable view.
    with lexicon.writer_lock(root):
        content_fingerprint = fingerprint(root)
        target = cache / 'inventory.json'
        inventory = None
        try:
            candidate = json.loads(target.read_text(encoding='utf-8'))
            if (candidate.get('fingerprint') == content_fingerprint
                    and candidate.get('derivation_version') == DERIVATION_VERSION):
                inventory = candidate
        except (OSError, ValueError, AttributeError):
            pass
        hit = inventory is not None
        if inventory is None:
            current = [(path.relative_to(root), entry) for path, entry in lexicon.entries(root)]
            inventory = derive(current)
            inventory['fingerprint'] = content_fingerprint
        if fingerprint(root) != content_fingerprint:
            raise lexicon.Error('Derivation inputs changed while building; rerun the inventory command.')
        # Each complete file is replaced atomically, JSON last as the cache key.
        lexicon.atomic_write(cache / 'report.md', markdown(inventory))
        lexicon.atomic_write(target, json_text(inventory))
    return {'cache_hit': hit, 'fingerprint': content_fingerprint,
            'inventory': str(target), 'report': str(cache / 'report.md'), **inventory['summary']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        print(json_text(build(args.root)), end='')
    except (lexicon.Error, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
