"""Behavioral tests with tiny original-source fixtures; no network or user-data writes."""

import concurrent.futures
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest import mock
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('lexicon', ROOT / 'tools/lexicon.py')
lex = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lex)


def make_ods(path):
    office = ET.Element(lex.O + 'document-content')
    body = ET.SubElement(office, lex.O + 'body')
    spreadsheet = ET.SubElement(body, lex.O + 'spreadsheet')
    sheets = {
        '詞目': [['詞目id', '漢字', '羅馬字'], [7, '欲【替】', 'beh'], [8, '重', '【文】tîng']],
        '義項': [['詞目id', '義項id', '解說'], [7, 1, '要。'], [8, 1, 'Fixture definition.']],
        '又唸作': [['詞目id', '漢字', '羅馬字'], [7, '欲', 'bueh']],
        '語音差異': [['詞目id', '漢字', 'fixture dialect'], [7, '欲', 'bueh']],
        '異用字': [['詞目id', '漢字', '異用字'], [7, '欲', '卜']],
        '漢字羅馬字對應': [['漢字', '羅馬字', '來源'], ['arbitrary example token', 'beh', '例句']],
    }
    for name, rows in sheets.items():
        table = ET.SubElement(spreadsheet, lex.T + 'table', {lex.T + 'name': name})
        for values in rows:
            row = ET.SubElement(table, lex.T + 'table-row')
            for value in values:
                cell = ET.SubElement(row, lex.T + 'table-cell')
                if isinstance(value, int):
                    cell.set(lex.O + 'value', str(value))
                else:
                    ET.SubElement(cell, lex.X + 'p').text = value
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('content.xml', ET.tostring(office))


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'entries').mkdir()
        (self.root / 'schema').mkdir()
        shutil.copyfile(ROOT / 'schema/entry.schema.json', self.root / 'schema/entry.schema.json')
        (self.root / 'id-sequence.toml').write_text('next_id = 1\n')
        source = self.root / 'sources/lkk-fixture'
        source.mkdir(parents=True)
        raw = '\t建議用字\t音讀\t數字版音讀\t又音\t教育部推薦漢字\t對應華語\t用例\t異用字\n040\tbeh\t\tbeh4\tbueh\t欲\t要\tbeh食飯\t卜\n'.encode()
        (source / 'word-list.tsv').write_bytes(raw)
        (source / 'metadata.toml').write_text(f'id = "lkk-fixture"\nfile = "word-list.tsv"\nformat = "tsv"\nsheet = "字表"\nsha256 = "{hashlib.sha256(raw).hexdigest()}"\n')
        (self.root / 'references').mkdir()
        self.moe_path = self.root / 'moe.ods'
        make_ods(self.moe_path)
        digest = hashlib.sha256(self.moe_path.read_bytes()).hexdigest()
        revision = 'a' * 40
        url = f'https://raw.githubusercontent.com/taigikeyboard/taigikeyboard/{revision}/dictionary/kautian.ods'
        (self.root / 'references/moe.toml').write_text(f'id = "moe-fixture"\nsha256 = "{digest}"\nformat = "moe-ods"\nrevision = "{revision}"\nsource_path = "dictionary/kautian.ods"\ndownload_url = "{url}"\n')
        self.raw_moe = self.moe_path.read_bytes()
        cache = self.root / '.cache/dictionaries/moe' / digest / 'kautian.ods'
        cache.parent.mkdir(parents=True)
        self.moe_path.replace(cache)
        self.moe_path = cache

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args, expected=0):
        result = subprocess.run([sys.executable, str(ROOT / 'tools/lexicon.py'), '--root', str(self.root), *args], capture_output=True, text=True)
        self.assertEqual(result.returncode, expected, result.stderr + result.stdout)
        return json.loads(result.stdout) if result.stdout else result.stderr

    def request(self, form='beh', reading='beh', **extra):
        request = {'preferred_form': form, 'canonical_tl': reading, 'sources': [{'snapshot': 'lkk-fixture', 'row': 2}], **extra}
        path = self.root / 'request.json'
        path.write_text(json.dumps(request, ensure_ascii=False))
        return path

    def test_add_is_sorted_formatted_and_id_is_persistent_after_deletion(self):
        request = self.request(alternate_readings=['bueh'])
        self.assertEqual(self.run_cli('next-id')['next_id'], 1)
        result = self.run_cli('add', str(request))
        path = self.root / result['created']
        self.assertEqual(path.name, 'beh--000001.toml')
        data = tomllib.loads(path.read_text())
        self.assertIs(type(data['id']), int)
        self.assertEqual(path.read_text(), lex.render(data))
        keys = [line.split(' = ')[0] for line in path.read_text().split('\n\n')[0].splitlines()]
        self.assertEqual(keys, sorted(keys))
        before = path.read_bytes()
        self.run_cli('format')
        self.assertEqual(before, path.read_bytes())
        path.unlink()
        self.assertEqual(self.run_cli('next-id')['next_id'], 2)
        self.assertEqual(self.run_cli('add', str(request))['id'], 2)

    def test_optional_hanji_forms_round_trip_and_participate_in_checks(self):
        result = self.run_cli('add', str(self.request(form='liô心', reading='liô-sim',
                                                    hanji_forms=['𠞭心'])))
        entry = tomllib.loads((self.root / result['created']).read_text())
        self.assertEqual(entry['hanji_forms'], ['𠞭心'])
        self.assertEqual(entry['moe_forms'], [])
        found = self.run_cli('check', str(self.request(form='𠞭心', reading='other')))
        self.assertEqual(found['existing_entries'][0]['id'], result['id'])
        found = self.run_cli('check', str(self.request(form='other', reading='other', hanji_forms=['𠞭心'])))
        self.assertEqual(found['existing_entries'][0]['id'], result['id'])
        dictionary = self.run_cli('check', str(self.request(form='other', reading='other', hanji_forms=['欲'])))
        self.assertEqual(dictionary['lkk_matches'][0]['moe_form'], '欲')
        self.assertTrue(any(row['record_id'] == '7' for row in dictionary['moe_matches']))
        self.run_cli('format', '--check')
        self.run_cli('build-csv')
        self.assertEqual(self.csv_rows(), [['preferred_form', 'tl'], ['liô心', 'liô-sim']])

    def test_hanji_forms_are_optional_and_validate_script_and_nonempty_sets(self):
        for values in [[], ['liô心'], ['心\n心'], ['心', '心']]:
            with self.subTest(values=values):
                self.run_cli('add', str(self.request(hanji_forms=values)), expected=2)
        result = self.run_cli('add', str(self.request()))
        entry = tomllib.loads((self.root / result['created']).read_text())
        self.assertNotIn('hanji_forms', entry)

    def test_duplicate_and_alias_checks_do_not_consume_an_id(self):
        request = self.request(alternate_readings=['bueh'])
        self.run_cli('add', str(request))
        report = self.run_cli('check', str(request))
        self.assertEqual(report['existing_entries'][0]['match'], 'exact_pair')
        self.run_cli('add', str(request), expected=2)
        alias = self.request(reading='bueh')
        self.assertEqual(self.run_cli('check', str(alias))['existing_entries'][0]['match'], 'alias_pair')
        self.run_cli('add', str(alias), expected=2)
        self.assertEqual(self.run_cli('next-id')['next_id'], 2)

    def test_distinct_homograph_requires_and_preserves_identity_note(self):
        self.run_cli('add', str(self.request()))
        request = self.request(identity_note='A distinct lexeme with separate etymology.')
        result = self.run_cli('add', str(request))
        self.assertEqual(result['id'], 2)
        self.assertEqual(tomllib.loads((self.root / result['created']).read_text())['identity_note'], 'A distinct lexeme with separate etymology.')
        self.run_cli('add', str(request), expected=2)
        self.assertEqual(self.run_cli('validate')['entries'], 2)

    def test_moe_exact_reading_variant_and_source_ids(self):
        request = self.request(moe_forms=['欲'])
        report = self.run_cli('check', str(request))
        match = next(record for record in report['moe_matches'] if record['source']['sheet'] == '詞目')
        self.assertEqual(match['record_id'], '7')
        self.assertEqual(match['headword'], '欲【替】')
        self.assertEqual(match['source']['row'], 2)
        self.assertEqual(match['match'], 'form_and_reading')
        self.assertEqual(match['definitions'], ['要。'])
        self.assertFalse(any(record['source']['sheet'] == '漢字羅馬字對應' for record in report['moe_matches']))
        alias = self.run_cli('check', str(self.request(form='卜', reading='bueh')))
        self.assertTrue(any(record['match'] == 'same_form' for record in alias['moe_matches']))
        self.assertTrue(any(record['source']['sheet'] == '又唸作' for record in alias['moe_matches']))
        self.assertEqual(report['lkk_matches'][0]['source']['row'], 2)
        self.run_cli('add', str(request))  # MOE existence is evidence, not a veto.

    def test_moe_source_reference_is_validated(self):
        request = self.request(form='欲', sources=[{'snapshot': 'moe-fixture', 'sheet': '詞目', 'row': 2}])
        self.run_cli('add', str(request))
        self.run_cli('validate')
        invalid = self.request(form='重', reading='tîng', sources=[{'snapshot': 'moe-fixture', 'sheet': '詞目', 'row': 999}])
        self.run_cli('add', str(invalid), expected=2)

    def test_corrupt_moe_never_reports_success_or_allocates(self):
        request = self.request()
        self.moe_path.write_bytes(b'changed')
        self.run_cli('check', str(request), expected=2)
        self.run_cli('add', str(request), expected=2)
        self.assertEqual(self.run_cli('next-id')['next_id'], 1)

    def test_first_use_downloads_once_then_works_offline(self):
        self.moe_path.unlink()
        with mock.patch.object(lex, 'urlopen', return_value=io.BytesIO(self.raw_moe)) as download:
            _, path, raw = lex.cached_moe(self.root)
            self.assertEqual(raw, self.raw_moe)
            self.assertEqual(path, self.moe_path)
            self.assertEqual(path.read_bytes(), self.raw_moe)
            lex.cached_moe(self.root)
            self.assertEqual(download.call_count, 1)
        with mock.patch.object(lex, 'urlopen', side_effect=AssertionError('network must not be used')):
            lex.moe_data(self.root)

    def test_bad_download_is_not_cached(self):
        self.moe_path.unlink()
        with mock.patch.object(lex, 'urlopen', return_value=io.BytesIO(b'bad download')):
            with self.assertRaisesRegex(lex.Error, 'Downloaded MOE checksum mismatch'):
                lex.cached_moe(self.root)
        self.assertFalse(self.moe_path.exists())

    def test_failed_first_download_does_not_allocate(self):
        self.moe_path.unlink()
        args = ['lexicon.py', '--root', str(self.root), 'add', str(self.request())]
        with mock.patch.object(sys, 'argv', args), mock.patch.object(lex, 'urlopen', side_effect=OSError('offline')), mock.patch('sys.stderr'):
            with self.assertRaises(SystemExit) as error:
                lex.main()
        self.assertEqual(error.exception.code, 2)
        self.assertFalse(self.moe_path.exists())
        self.assertEqual(self.run_cli('next-id')['next_id'], 1)

    def test_unknown_fields_and_bad_citations_are_rejected(self):
        for extra in [{'examples': ['removed']}, {'sources': [{'snapshot': 'lkk-fixture', 'row': 999}]}, {'sources': [{'snapshot': 'lkk-fixture', 'row': 1}]}, {'sources': [{'url': 'file:///private/path', 'locator': 'word'}]}, {'sources': [{}]}, {'id': 9}]:
            with self.subTest(extra=extra):
                self.run_cli('add', str(self.request(**extra)), expected=2)
        self.assertEqual(self.run_cli('next-id')['next_id'], 1)

    def test_url_citation_and_unicode_search_keep_tones_and_boundaries(self):
        url = {'url': 'https://example.org/dictionary', 'locator': 'Entry 4'}
        self.run_cli('add', str(self.request(form='重', reading='tîng', sources=[url])))
        request = self.request(form='重', reading=unicodedata.normalize('NFD', 'tîng'))
        # Source strings are NFC on disk; lookup keys also normalize NFC.
        self.assertEqual(lex.key('TÎNG'), lex.key(unicodedata.normalize('NFD', 'tîng')))
        self.assertNotEqual(lex.key('bóng'), lex.key('bông'))
        self.assertNotEqual(lex.key('āu--ji̍t'), lex.key('āu-ji̍t'))
        self.assertEqual(self.run_cli('check', str(request))['existing_entries'][0]['match'], 'exact_pair')
        self.run_cli('add', str(request), expected=2)

    def test_lookup_without_a_citation_can_find_one_but_add_requires_evidence(self):
        request = self.root / 'query.json'
        request.write_text(json.dumps({'preferred_form': '欲', 'canonical_tl': 'beh'}))
        report = self.run_cli('check', str(request))
        self.assertTrue(report['moe_matches'])
        self.run_cli('add', str(request), expected=2)
        self.assertEqual(self.run_cli('next-id')['next_id'], 1)

    def test_bucket_and_portable_names(self):
        for reading, expected in [('tshì-môo-thâng', 'tsh'), ('khí', 'kh'), ('tsiah', 'ts'), ('phah', 'ph'), ('thâu', 'th'), ('m̄', 'zero'), ('n̂g', 'zero'), ('ńg', 'zero'), ('ngá', 'ng'), ('--ah', 'zero'), ('āu--ji̍t', 'zero')]:
            self.assertEqual(lex.bucket(reading), expected)
        self.assertEqual(lex.filename('漢/羅%字', 42), '漢%2F羅%25字--000042.toml')

    def test_format_renames_preserving_id_and_roundtrips_escaped_notes(self):
        result = self.run_cli('add', str(self.request(usage_notes='Quotes " and newline\nwith a backslash \\ remain.')))
        old = self.root / result['created']
        entry = tomllib.loads(old.read_text())
        entry['preferred_form'] = '欲'
        old.write_text(lex.render(entry))
        self.run_cli('format', '--check', expected=2)
        self.run_cli('format')
        new = self.root / 'entries/b/欲--000001.toml'
        self.assertFalse(old.exists())
        self.assertEqual(tomllib.loads(new.read_text())['usage_notes'], entry['usage_notes'])
        self.assertEqual(self.run_cli('next-id')['next_id'], 2)

    def test_concurrent_writers_never_allocate_the_same_id(self):
        request = self.request()
        def add():
            return subprocess.run([sys.executable, str(ROOT / 'tools/lexicon.py'), '--root', str(self.root), 'add', str(request)], capture_output=True, text=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: add(), range(2)))
        self.assertEqual(sum(result.returncode == 0 for result in results), 1)
        self.assertEqual(self.run_cli('validate')['entries'], 1)
        self.assertEqual(self.run_cli('next-id')['next_id'], 2)

    def test_checksum_and_counter_regressions_are_detected(self):
        self.run_cli('add', str(self.request()))
        (self.root / 'id-sequence.toml').write_text('next_id = 1\n')
        self.run_cli('validate', expected=2)
        (self.root / 'id-sequence.toml').write_text('next_id = 2\n')
        path = self.root / 'sources/lkk-fixture/word-list.tsv'
        path.write_bytes(path.read_bytes() + b'changed')
        self.run_cli('validate', expected=2)

    def test_failed_entry_write_reserves_a_gap_and_releases_lock(self):
        request = self.request()
        write = lex.atomic_write
        def fail_entry(path, content):
            if path.suffix == '.toml' and path.parent.name == 'b':
                raise OSError('simulated entry-write failure')
            write(path, content)
        args = ['lexicon.py', '--root', str(self.root), 'add', str(request)]
        with mock.patch.object(sys, 'argv', args), mock.patch.object(lex, 'atomic_write', side_effect=fail_entry), mock.patch('sys.stderr'):
            with self.assertRaises(SystemExit) as error:
                lex.main()
        self.assertEqual(error.exception.code, 2)
        self.assertFalse((self.root / '.lexicon.lock').exists())
        self.assertEqual(self.run_cli('next-id')['next_id'], 2)
        self.assertEqual(self.run_cli('add', str(request))['id'], 2)

    def csv_rows(self):
        with (self.root / 'dist/lexicon.csv').open(encoding='utf-8', newline='') as stream:
            return list(csv.reader(stream))

    def test_build_csv_romanized_aliases_map_to_themselves(self):
        self.run_cli('add', str(self.request(alternate_readings=['bueh'])))
        result = self.run_cli('build-csv')
        self.assertEqual(result, {'csv': 'dist/lexicon.csv', 'entries': 1, 'rows': 2})
        self.assertEqual(self.csv_rows(), [['preferred_form', 'tl'], ['beh', 'beh'], ['bueh', 'bueh']])

    def test_build_csv_hanji_keeps_form_and_mixed_alias_preserves_hanji(self):
        self.run_cli('add', str(self.request(form='欲', alternate_readings=['bueh'])))
        self.run_cli('add', str(self.request(form='beh食飯', reading='beh-tsiah-pn̄g', alternate_readings=['bueh-tsiah-pn̄g'])))
        self.run_cli('build-csv')
        self.assertEqual(self.csv_rows(), [
            ['preferred_form', 'tl'],
            ['beh食飯', 'beh-tsiah-pn̄g'],
            ['bueh食飯', 'bueh-tsiah-pn̄g'],
            ['欲', 'beh'], ['欲', 'bueh'],
        ])

    def test_mixed_alternates_change_only_romanized_syllables(self):
        cases = [
            ('想beh', 'siūnn-beh', 'siūnn-bueh', '想bueh'),
            ('hip相', 'hip-siòng', 'hip-siōng', 'hip相'),
            ('想beh食飯', 'siūnn-beh-tsiah-pn̄g', 'siūnn-bueh-tsiah-pn̄g', '想bueh食飯'),
            ('好--ah', 'hó--ah', 'hó--a', '好--a'),
            ('m̄知', 'm̄ tsai', 'm̄ chai', 'm̄知'),
        ]
        for form, canonical, alternate, expected in cases:
            with self.subTest(form=form):
                self.assertEqual(lex.written_form(form, canonical, alternate), expected)
        self.assertEqual(lex.written_form('想bèh', 'siūnn-bèh', 'siūnn-bueh'), '想bueh')

    def test_ambiguous_mixed_alternate_fails_before_csv_replacement(self):
        self.run_cli('add', str(self.request(form='想beh', reading='siūnn-beh')))
        self.run_cli('build-csv')
        before = (self.root / 'dist/lexicon.csv').read_bytes()
        path, entry = lex.entries(self.root)[0]
        entry['alternate_readings'] = ['sióng']
        path.write_text(lex.render(entry))
        self.run_cli('build-csv', expected=2)
        self.assertEqual((self.root / 'dist/lexicon.csv').read_bytes(), before)
        with self.assertRaisesRegex(lex.Error, 'romanized part'):
            lex.written_form('想beh', 'siūnn-bueh', 'siūnn-beh')
        with self.assertRaisesRegex(lex.Error, 'Neutral-tone'):
            lex.written_form('想beh', 'siūnn-beh', 'siūnn--beh')

    def test_build_csv_deduplicates_rows_without_merging_homographs(self):
        self.run_cli('add', str(self.request(alternate_readings=['bueh'])))
        self.run_cli('add', str(self.request(alternate_readings=['bueh'], identity_note='A separate fixture lexeme.')))
        self.run_cli('add', str(self.request(form='bueh', reading='bueh')))
        before = {path: path.read_bytes() for path, _ in lex.entries(self.root)}
        counter = (self.root / 'id-sequence.toml').read_bytes()
        self.assertEqual(self.run_cli('build-csv')['rows'], 2)
        self.assertEqual(self.csv_rows(), [['preferred_form', 'tl'], ['beh', 'beh'], ['bueh', 'bueh']])
        self.assertEqual({path: path.read_bytes() for path, _ in lex.entries(self.root)}, before)
        self.assertEqual((self.root / 'id-sequence.toml').read_bytes(), counter)
        self.assertEqual(self.run_cli('validate')['entries'], 3)

    def test_build_csv_preserves_unicode_quotes_and_neutral_markers(self):
        self.run_cli('add', str(self.request(form='後--日', reading='āu--ji̍t', alternate_readings=['āu--li̍t'])))
        self.run_cli('add', str(self.request(form='「欲,愛」', reading='bóng')))
        self.run_cli('build-csv')
        target = self.root / 'dist/lexicon.csv'
        before = target.read_bytes()
        self.assertNotIn(b'\r', before)
        self.assertEqual(self.csv_rows(), [
            ['preferred_form', 'tl'], ['「欲,愛」', 'bóng'],
            ['後--日', 'āu--ji̍t'], ['後--日', 'āu--li̍t'],
        ])
        self.run_cli('build-csv')
        self.assertEqual(target.read_bytes(), before)

    def test_build_csv_rejects_invalid_data_before_replacing_output(self):
        self.run_cli('add', str(self.request()))
        self.run_cli('build-csv')
        target = self.root / 'dist/lexicon.csv'
        before = target.read_bytes()
        source = self.root / 'sources/lkk-fixture/word-list.tsv'
        source.write_bytes(source.read_bytes() + b'changed')
        self.run_cli('build-csv', expected=2)
        self.assertEqual(target.read_bytes(), before)
        self.assertFalse((self.root / '.lexicon.lock').exists())

    def test_build_csv_empty_repository_and_writer_lock(self):
        (self.root / '.lexicon.lock').mkdir()
        self.run_cli('build-csv', expected=2)
        self.assertFalse((self.root / 'dist/lexicon.csv').exists())
        (self.root / '.lexicon.lock').rmdir()
        self.assertEqual(self.run_cli('build-csv')['rows'], 0)
        self.assertEqual(self.csv_rows(), [['preferred_form', 'tl']])


if __name__ == '__main__':
    unittest.main()
