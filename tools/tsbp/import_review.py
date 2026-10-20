"""Preview or import explicit review approvals through the lexicon maintenance tool."""

import argparse
from contextlib import redirect_stdout, redirect_stderr
from functools import lru_cache
import io
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import tempfile
import unicodedata


def nfc(value):
    return unicodedata.normalize('NFC', value)


def pure_romanized(text):
    return isinstance(text, str) and any('LATIN' in unicodedata.name(c, '') for c in text) and all(
        'LATIN' in unicodedata.name(c, '') or unicodedata.category(c).startswith('M')
        or c.isdecimal() or c in "-'’ " for c in text)


def article_source(group):
    occurrence = group['occurrences'][0]
    return {'url': occurrence['url'], 'locator':
        f"Article text line {occurrence['line']}; normalized source characters "
        f"{occurrence['anchor_start']}:{occurrence['anchor_end']}; written form {occurrence['anchor']}"}


def source_anchor_request(approval, group):
    reading = group.get('normalized_tl')
    if (group.get('parser_compatible') is not True
            or not pure_romanized(group.get('display', group['key']))
            or not pure_romanized(reading)):
        raise ValueError('Article-only import requires a parser-compatible pure romanized anchor and TL reading')
    if approval.get('source_reading') != reading:
        raise ValueError('The approved article-anchor reading does not match the candidate’s normalized TL reading')
    if approval.get('word_id') or approval.get('canonical_choice_id') or approval.get('alternate_choice_ids'):
        raise ValueError('Article-only approval cannot include MOE reading choices')
    preferred = nfc(approval.get('preferred_form', '').strip())
    if not pure_romanized(preferred):
        raise ValueError('Article-only import requires a pure romanized preferred spelling')
    request = {'schema_version': 1, 'preferred_form': preferred, 'canonical_tl': nfc(reading),
               'alternate_readings': [], 'moe_forms': [], 'review_status': 'imported',
               'sources': [article_source(group)]}
    if approval.get('identity_note', '').strip():
        request['identity_note'] = nfc(approval['identity_note'].strip())
    return request


def build_request(approval, group, ignored, moe_records):
    if any(approval.get(field, '').strip() for field in (
            'custom_handling', 'custom_preferred_form', 'custom_hanji', 'custom_reading')):
        raise ValueError('Resolve this anchor’s custom handling request before automatic import')
    if approval.get('approved') is not True:
        raise ValueError('Only explicit Approve import decisions can become requests')
    if set(group['dedup_lookup_forms']) & set(ignored):
        raise ValueError('An ignored anchor cannot also be approved for import')
    if group.get('parser_compatible') is False:
        raise ValueError('Resolve the unrecognized reading before import')
    mode = approval.get('import_mode', 'moe')
    if mode == 'source_anchor':
        return source_anchor_request(approval, group)
    if mode != 'moe':
        raise ValueError('Unsupported import mode')
    word = next((word for word in group.get('review_words', []) if word['id'] == approval.get('word_id')), None)
    if word is None:
        raise ValueError('Select a MOE entry from this anchor’s supported matches')
    options = {reading['id']: reading for reading in word['readings']}
    primary_id = approval.get('canonical_choice_id')
    alternate_ids = approval.get('alternate_choice_ids', [])
    if primary_id not in options or not isinstance(alternate_ids, list):
        raise ValueError('A sourced filing reading is required')
    if primary_id in alternate_ids or len(set(alternate_ids)) != len(alternate_ids):
        raise ValueError('Filing and alternate reading choices must be distinct')
    if any(identity not in options for identity in alternate_ids):
        raise ValueError('Alternate readings must belong to the same selected MOE entry')
    preferred = nfc(approval.get('preferred_form', '').strip())
    if not preferred:
        raise ValueError('A preferred spelling is required')
    chosen = [options[primary_id], *(options[identity] for identity in alternate_ids)]
    sources = []
    for reading in chosen:
        if not reading['references']:
            raise ValueError('Selected reading has no original MOE evidence')
        for reference in reading['references']:
            source = reference['source']
            candidates = [record for record in moe_records
                          if record['source'] == source and record['column'] == reference['column']
                          and record['record_id'] == reference['record_id']]
            supported = {nfc(re.sub(r'【[^】]*】', '', value).strip()).casefold()
                         for record in candidates for value in re.split(r'[,，、/]', record['reading'])}
            if nfc(reading['reading']).casefold() not in supported:
                raise ValueError('Selected reading is not supported by the pinned MOE row')
            if source not in sources:
                sources.append(source)
    sources.append(article_source(group))
    request = {'schema_version': 1, 'preferred_form': preferred,
               'canonical_tl': nfc(chosen[0]['reading']),
               'alternate_readings': sorted({nfc(reading['reading']) for reading in chosen[1:]} - {nfc(chosen[0]['reading'])}),
               'moe_forms': sorted({re.sub(r'【[^】]*】', '', reading['headword']).strip() for reading in chosen} - {preferred}),
               'review_status': 'imported', 'sources': sources}
    if approval.get('identity_note', '').strip():
        request['identity_note'] = nfc(approval['identity_note'].strip())
    return request


def build_custom_request(custom, group):
    """Build a proposal for offline review; never treat custom fields as approval."""
    preferred, reading = (custom.get(field, '') for field in ('preferred_form', 'reading'))
    hanji_form = custom.get('hanji', '')
    if not all(isinstance(value, str) for value in (preferred, reading, hanji_form)):
        raise ValueError('Custom preferred form, Hanji and reading must be text')
    preferred, reading, hanji_form = (nfc(value.strip()) for value in (preferred, reading, hanji_form))
    if not preferred or not reading:
        raise ValueError('A structured custom request needs both preferred form and reading; Hanji is optional')
    if not pure_romanized(reading) or any(c in preferred + reading + hanji_form for c in '\n\r'):
        raise ValueError('Use a single-line preferred form and a romanized TL reading')
    request = {'schema_version': 1, 'preferred_form': preferred, 'canonical_tl': reading,
               'alternate_readings': [], 'moe_forms': [], 'review_status': 'imported',
               'sources': [article_source(group)]}
    if hanji_form:
        request['hanji_forms'] = [hanji_form]
    return request


def load_bundle(path, groups_path, summary):
    bundle = json.loads(path.read_text())
    if bundle.get('schema_version') != 1:
        raise ValueError('Unsupported review export version')
    if bundle.get('issue') != summary['issue'] or bundle.get('corpus_sha256') != summary['corpus_sha256']:
        raise ValueError('The review belongs to another issue or corpus snapshot')
    actual = hashlib.sha256(groups_path.read_bytes()).hexdigest()
    if bundle.get('groups_sha256') != actual or summary['review_groups_sha256'] != actual:
        raise ValueError('The candidate file changed; load the saved review in the current page and export it again')
    if bundle.get('moe_snapshot') != summary['moe']['snapshot']:
        raise ValueError('The review uses a different MOE snapshot')
    return bundle


def coalesce_identical_approvals(plan):
    """Combine duplicate approvals only for the exact same MOE word and choices."""
    for item in plan:
        if item.get('status') != 'blocked' or not item.get('reason', '').startswith('Two approvals overlap'):
            continue
        signature = {k: v for k, v in item['request'].items() if k != 'sources'}
        target = next((other for other in plan if other['status'] == 'ready'
                       and other.get('word_id') == item.get('word_id')
                       and {k: v for k, v in other['request'].items() if k != 'sources'} == signature), None)
        if target is None:
            continue
        for source in item['request']['sources']:
            if source not in target['request']['sources']:
                target['request']['sources'].append(source)
        item.update(status='merged', merged_into_anchor=target['anchor_key'])
        item.pop('reason', None)


def run_maintenance(module, root, command):
    """Run the unchanged maintenance CLI in-process; retain its writer/check logic."""
    output, errors = io.StringIO(), io.StringIO()
    previous = sys.argv
    code = 0
    try:
        sys.argv = [str(root / 'tools/lexicon.py'), '--root', str(root), *command]
        with redirect_stdout(output), redirect_stderr(errors):
            try:
                module.main()
            except SystemExit as error:
                code = error.code if isinstance(error.code, int) else 1
    finally:
        sys.argv = previous
    return code, output.getvalue(), errors.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('review', type=Path)
    parser.add_argument('--root', type=Path)
    parser.add_argument('--pilot', type=Path, default=Path.cwd(), help='Pilot output folder containing summary.json and groups.json')
    parser.add_argument('--apply', action='store_true', help='Add ready approved entries; otherwise preview only')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    summary = json.loads((args.pilot / 'summary.json').read_text())
    groups_path = args.pilot / 'groups.json'
    bundle = load_bundle(args.review, groups_path, summary)
    root = args.root or Path(summary['lexicon_root'])
    module_path = root / 'tools/lexicon.py'
    spec = importlib.util.spec_from_file_location('review_lexicon', module_path)
    lexicon = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lexicon)
    # Cache only the pure ODS decoder for identical bytes. Every maintenance call
    # still loads the pin and verifies the original ODS checksum before decoding.
    lexicon.ods_sheets = lru_cache(maxsize=1)(lexicon.ods_sheets)
    # These are the same offline checks and verified original MOE loader used by add.
    evidence = lexicon.lkk_data(root), lexicon.moe_data(root)
    if evidence[1][0]['sha256'] != summary['moe']['sha256']:
        raise ValueError('The pinned MOE dictionary changed; regenerate and review the candidates')
    custom_requests = bundle.get('custom_requests', [])
    if not isinstance(custom_requests, list) or any(not isinstance(item, dict)
            or not isinstance(item.get('anchor_key'), str) or not isinstance(item.get('prompt'), str)
            for item in custom_requests):
        raise ValueError('Custom requests must contain an anchor key and text prompt')
    pending_custom = {item['anchor_key'] for item in custom_requests
                      if any(item.get(field) for field in ('prompt', 'preferred_form', 'hanji', 'reading'))}
    current = lexicon.entries(root)
    groups = {group['key']: group for group in json.loads(groups_path.read_text())}
    custom_previews = []
    for custom in custom_requests:
        if not any(field in custom for field in ('preferred_form', 'hanji', 'reading')):
            continue
        item = {'anchor_key': custom['anchor_key'], 'status': 'needs_review'}
        try:
            request = build_custom_request(custom, groups[custom['anchor_key']])
            item.update(request=request, checks=lexicon.check(root, request, current, evidence))
            lexicon.verify_sources(request, *evidence)
        except (ValueError, KeyError, TypeError, lexicon.Error) as error:
            item.update(status='needs_resolution', reason=str(error))
        custom_previews.append(item)
    plan, batch_readings = [], []
    for approval in bundle.get('approvals', []):
        if approval.get('approved') is not True:
            continue
        item = {'anchor_key': approval.get('anchor_key'), 'word_id': approval.get('word_id'), 'status': 'blocked'}
        try:
            if approval.get('anchor_key') in pending_custom:
                raise ValueError('Resolve this anchor’s custom handling request before automatic import')
            group = groups[approval['anchor_key']]
            request = build_request(approval, group, bundle.get('ignored_forms', []), evidence[1][2])
            report = lexicon.check(root, request, current, evidence)
            lexicon.verify_sources(request, *evidence)
            item['written_forms'] = [{'preferred_form': form, 'tl': reading}
                                     for form, reading in lexicon.spelling_readings(request)]
            item.update(request=request, checks={'existing_entries': report['existing_entries'],
                'lkk_matches': len(report['lkk_matches']), 'moe_matches': len(report['moe_matches']),
                'moe_checked': report['moe_checked']})
            note = lexicon.key(request.get('identity_note', ''))
            existing = report['existing_entries']
            if existing and (not note or any(note == lexicon.key(match.get('identity_note') or '') for match in existing)):
                raise ValueError('Existing related entry needs review: update that word, or explicitly distinguish an unrelated homograph')
            readings = {lexicon.key(request['canonical_tl']), *(lexicon.key(value) for value in request['alternate_readings'])}
            form = lexicon.key(request['preferred_form'])
            if any(form == old_form and readings & old_readings and note == old_note for old_form, old_readings, old_note in batch_readings):
                raise ValueError('Two approvals overlap; combine this word’s readings into one approval')
            batch_readings.append((form, readings, note))
            item['status'] = 'ready'
        except (ValueError, KeyError, TypeError) as error:
            item['reason'] = str(error)
        plan.append(item)
    coalesce_identical_approvals(plan)
    created = []
    if args.apply:
        with tempfile.TemporaryDirectory(prefix='hanlo-approved-import-') as folder:
            for index, item in enumerate(plan):
                if item['status'] != 'ready':
                    continue
                request_path = Path(folder) / f'{index}.json'
                request_path.write_text(json.dumps(item['request'], ensure_ascii=False))
                code, output, errors = run_maintenance(lexicon, root, ['add', str(request_path)])
                if code:
                    item.update(status='blocked', reason=errors.strip())
                else:
                    added = json.loads(output)
                    item.update(status='created', id=added['id'], path=added['created'])
                    created.append({'id': added['id'], 'path': added['created']})
        by_anchor = {item['anchor_key']: item for item in plan}
        for item in plan:
            if item['status'] == 'merged':
                target = by_anchor[item['merged_into_anchor']]
                if target['status'] == 'created':
                    item.update(id=target['id'], path=target['path'])
                else:
                    item.update(status='blocked', reason='The matching approval could not be imported')
        for command in (['validate'], ['format', '--check']):
            code, output, errors = run_maintenance(lexicon, root, command)
            if code:
                raise ValueError('Post-import validation failed: ' + errors.strip())
    output = {'mode': 'apply' if args.apply else 'preview', 'approved': len(plan),
              'ready': sum(item['status'] == 'ready' for item in plan), 'created': created,
              'merged': sum(item['status'] == 'merged' for item in plan),
              'custom_requests': custom_requests,
              'custom_previews': custom_previews,
              'blocked': sum(item['status'] == 'blocked' for item in plan), 'items': plan}
    text = json.dumps(output, ensure_ascii=False, indent=2) + '\n'
    if args.report:
        args.report.write_text(text)
    print(text, end='')


if __name__ == '__main__':
    main()
