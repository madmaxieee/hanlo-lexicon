"""Derive an LKK supplement from original sources; never write vocabulary records."""

import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
import unicodedata as ud
import xml.etree.ElementTree as ET
import zipfile

import lexicon as lx
from source_excerpts import SPAN, cited_excerpt, display_excerpt
from lkk_supplement import LKKCoverage


HEADERS = ['詞條ID', '建議用字', '音讀', '數字版音讀', '又音', '教育部推薦漢字',
           '對應華語', '用例', '異用字', '教育部辭典', '來源文章', '華語出處', '用例出處']
TONES = dict(zip('\u0301\u0300\u0302\u030c\u0304\u030d\u030b', '2356789'))


def numeric_reading(reading):
    def convert(match):
        text = ud.normalize('NFD', match.group())
        tones = [TONES[c] for c in text if c in TONES]
        if len(tones) > 1:
            raise lx.Error(f'Multiple tone marks in syllable: {match.group()}')
        bare = ud.normalize('NFC', ''.join(c for c in text if c not in TONES)).replace('ı', 'i')
        tone = tones[0] if tones else ('4' if bare.lower().endswith(('p', 't', 'k', 'h')) else '1')
        return bare + tone
    return re.sub(r'[^\s-]+', convert, reading)


def sheet_records(sheets, name):
    rows = sheets.get(name, [])
    return [(number, dict(zip(rows[0][1], cells))) for number, cells in rows[1:]] if rows else []


def derive(root, corpus):
    current = lx.entries(root)
    lkk = lx.lkk_data(root)
    pin, _, raw = lx.cached_moe(root)
    _, sheets, records = lx.decode_moe(pin, raw)
    moe = {(r['source']['sheet'], r['source']['row']): r for r in records}
    coverage = LKKCoverage(lkk, records)
    comparisons = defaultdict(list)
    for number, record in sheet_records(sheets, '詞彙比較'):
        for reading in lx.reading_keys(record.get('羅馬字', '')):
            comparisons[(lx.annotation_key(record.get('漢字', '')), reading)].append(
                (record.get('華語詞目', ''), f"{pin['id']}:詞彙比較:{number}"))
    examples = defaultdict(list)
    for number, record in sheet_records(sheets, '例句'):
        if record.get('漢字'):
            examples[record['詞目id']].append((record['漢字'],
                f"{pin['id']}:例句:{number}; sense {record.get('義項id', '')}"))
    documents = {}
    corpus_bytes = corpus.read_bytes()
    for line in corpus_bytes.decode('utf-8').splitlines():
        record = json.loads(line)
        url = record.get('metadata', {}).get('original_url')
        if url:
            if url in documents and documents[url]['text'] != record['text']:
                raise lx.Error(f'Conflicting corpus documents for {url}')
            documents[url] = record
    spans = defaultdict(list)
    for _, entry in current:
        for source in entry['sources']:
            match = SPAN.search(source.get('locator', ''))
            if 'url' in source and match:
                a, b = map(int, match.groups())
                spans[source['url']].append((a, b, entry['id']))
    rows, audit, provenance = [], [], []
    for _, entry in current:
        form, eid = entry['preferred_form'], entry['id']
        if lx.is_hanji(form) and '-' not in form:
            continue
        if coverage.original(entry, lkk):
            audit.append({'id': eid, 'reason': 'Original LKK item'})
            continue
        cited_moe = [moe[(s['sheet'], s['row'])] for s in entry['sources']
                     if s.get('snapshot') == pin['id'] and (s.get('sheet'), s['row']) in moe]
        references = [*entry['moe_forms'], *entry.get('hanji_forms', []),
                      *(r['headword'] for r in cited_moe)]
        proof = coverage.reconstructed(entry, references)
        if proof:
            audit.append({'id': eid, 'reason': 'Reconstructed from unambiguous original LKK combos', 'proof': proof})
            continue
        independent = []
        for source in entry['sources']:
            match = SPAN.search(source.get('locator', ''))
            if 'url' not in source or not match:
                continue
            a, b = map(int, match.groups())
            if not any(x <= a and b <= y and (x < a or b < y)
                       for x, y, _ in spans[source['url']]):
                independent.append(source)
        if not independent:
            audit.append({'id': eid, 'reason': 'No uncontained corpus citation'})
            continue
        mandarin, mandarin_sources, example, example_source = [], [], '', ''
        evidence = None
        if not mandarin:
            readings = {lx.key(r) for r in [entry['canonical_tl'], *entry['alternate_readings']]}
            forms = {lx.annotation_key(f) for f in entry['moe_forms']}
            forms.update(lx.annotation_key(r['headword']) for r in cited_moe)
            for headword in sorted(forms):
                for reading in sorted(readings):
                    for value, location in comparisons.get((headword, reading), []):
                        if value:
                            mandarin.append(value); mandarin_sources.append(location)
        # Prefer an actual cited occurrence to dictionary examples.
        for source in independent:
            try:
                example, example_source, evidence = cited_excerpt(source, documents)
                break
            except ValueError as error:
                audit.append({'id': eid, 'reason': str(error), 'source': source})
        if not example:
            for record in cited_moe:
                candidates = examples.get(record['record_id'], [])
                if candidates:
                    example, example_source = candidates[0]
                    break
        urls = list(dict.fromkeys(s['url'] for s in independent))
        moe_links = [f"https://sutian.moe.edu.tw/zh-hant/su/{r['record_id']}/"
                     for r in cited_moe if r['record_id']]
        row = [str(eid), form, entry['canonical_tl'], numeric_reading(entry['canonical_tl']),
               ', '.join(entry['alternate_readings']), ', '.join(entry['moe_forms']),
               ' / '.join(dict.fromkeys(mandarin)), display_excerpt(example, evidence) if evidence else example, ', '.join(entry.get('hanji_forms', [])),
               next(iter(moe_links), ''), evidence['url'] if evidence else next(iter(urls), ''),
               '; '.join(dict.fromkeys(mandarin_sources)), example_source]
        rows.append(row)
        provenance.append({'id': eid, 'mandarin_sources': list(dict.fromkeys(mandarin_sources)),
                           'example_source': example_source, 'raw_example': example, 'corpus_excerpt': evidence})
    rows.sort(key=lambda row: (lx.key(row[2]), int(row[0])))
    return {'headers': HEADERS, 'rows': rows, 'provenance': provenance, 'audit': audit,
            'lkk_combo_alignment_skips': coverage.skipped,
            'corpus_sha256': hashlib.sha256(corpus_bytes).hexdigest(), 'moe_sha256': pin['sha256'],
            'coverage': {'entries': len(rows), 'mandarin': sum(bool(r[6]) for r in rows),
                         'examples': sum(bool(r[7]) for r in rows)}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--corpus', type=Path, help='Read-only normalized TSBP JSONL')
    parser.add_argument('--out', type=Path, default=Path('dist/lkk-supplement'))
    parser.add_argument('--link-xlsx', type=Path, help='Attach native hyperlinks to the rendered workbook')
    args = parser.parse_args()
    if args.link_xlsx:
        result = json.loads((args.out / 'lexicon-readable.json').read_text())
        attach_links(args.link_xlsx, result['rows'])
        return
    if not args.corpus:
        parser.error('--corpus is required for source derivation')
    result = derive(args.root, args.corpus)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'lexicon-readable.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    with (args.out / 'lexicon-readable.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(result['headers'])
        writer.writerows(result['rows'])
    print(json.dumps(result['coverage']))


def attach_links(path, rows):
    """Artifact Tool lacks native hyperlink authoring; add OOXML external links."""
    ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    rns = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    relns = 'http://schemas.openxmlformats.org/package/2006/relationships'
    with zipfile.ZipFile(path) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    sheet = ET.fromstring(files['xl/worksheets/sheet1.xml'])
    relpath = 'xl/worksheets/_rels/sheet1.xml.rels'
    rels = ET.fromstring(files[relpath]) if relpath in files else ET.Element(f'{{{relns}}}Relationships')
    links = ET.Element(f'{{{ns}}}hyperlinks')
    used = {r.get('Id') for r in rels}
    for i, row in enumerate(rows, 2):
        for j, col in [(9, 'J'), (10, 'K')]:
            if not row[j]:
                continue
            identity = f'readerLink{col}{i}'
            if identity in used:
                raise ValueError('Workbook already contains reader links; render it again first')
            ET.SubElement(links, f'{{{ns}}}hyperlink', {'ref': f'{col}{i}', f'{{{rns}}}id': identity})
            ET.SubElement(rels, f'{{{relns}}}Relationship', {
                'Id': identity, 'Type': rns + '/hyperlink', 'Target': row[j], 'TargetMode': 'External'})
    index = next((i for i, child in enumerate(sheet) if child.tag.split('}')[-1] in
                  ['pageMargins', 'pageSetup', 'drawing', 'tableParts']), len(sheet))
    sheet.insert(index, links)
    files['xl/worksheets/sheet1.xml'] = ET.tostring(sheet, encoding='utf-8', xml_declaration=True)
    files[relpath] = ET.tostring(rels, encoding='utf-8', xml_declaration=True)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)


if __name__ == '__main__':
    main()
