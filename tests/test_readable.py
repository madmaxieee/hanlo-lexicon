"""Source joins and excerpts must preserve evidence rather than guess missing text."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import readable as reader


class ReaderTests(unittest.TestCase):
    def test_numeric_reading_preserves_neutral_boundaries_and_syllabic_tones(self):
        for source, expected in [('a-kīm', 'a1-kim7'), ('āu--ji̍t', 'au7--jit8'),
                                 ('nĝ', 'ng5'), ('ta̋nn', 'tann9'), ('--ah', '--ah4')]:
            self.assertEqual(reader.numeric_reading(source), expected)

    def test_excerpt_is_a_located_literal_substring(self):
        source = {'url': 'https://example.org/a', 'locator':
                  'Article text line 2; normalized source characters 3:6; written form beh'}
        text = '前文\nbeh食飯\n後文'
        excerpt, location, evidence = reader.cited_excerpt(source, {source['url']: {'id': 'a', 'text': text}})
        self.assertEqual(excerpt, 'beh食飯')
        self.assertEqual(text[slice(*evidence['excerpt_span'])], excerpt)
        self.assertIn('match 3:6', location)

    def test_stale_offsets_do_not_produce_an_example(self):
        source = {'url': 'https://example.org/a', 'locator':
                  'normalized source characters 0:3; written form beh'}
        with self.assertRaisesRegex(ValueError, 'no longer matches'):
            reader.cited_excerpt(source, {source['url']: {'id': 'a', 'text': '食飯beh'}})

    def test_legacy_locator_annotations_do_not_become_literal_text(self):
        for suffix in [' (in beh食飯)', '; preferred form corrected to beh']:
            source = {'url': 'https://example.org/a', 'locator':
                      'normalized source characters 0:3; source written form beh' + suffix}
            self.assertEqual(reader.cited_excerpt(source, {source['url']: {'id': 'a', 'text': 'beh食飯'}})[0], 'beh食飯')

    def test_derivation_joins_explicit_mandarin_mapping_and_suppresses_nested_match(self):
        pin = {'id': 'moe', 'sha256': 'fixture'}
        def entry(eid, form, reading, end):
            return {'id': eid, 'preferred_form': form, 'canonical_tl': reading,
                    'alternate_readings': [], 'moe_forms': ['欲食飯'], 'sources': [
                        {'url': 'https://example.org/a', 'locator':
                         f'normalized source characters 0:{end}; written form {form}'}]}
        entries = [(None, entry(1, 'beh', 'beh', 3)), (None, entry(2, 'beh食飯', 'beh-tsia̍h-pn̄g', 5))]
        sheets = {'詞彙比較': [(1, ['漢字', '羅馬字', '華語詞目']),
                             (2, ['欲食飯', 'beh-tsia̍h-pn̄g', '要吃飯']),
                             (3, ['同音異詞', 'beh-tsia̍h-pn̄g', 'wrong'])]}
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory) / 'corpus.jsonl'
            corpus.write_text(json.dumps({'id': 'a', 'text': 'beh食飯',
                              'metadata': {'original_url': 'https://example.org/a'}}))
            with patch.object(reader.lx, 'entries', return_value=entries), \
                 patch.object(reader.lx, 'lkk_data', return_value={}), \
                 patch.object(reader.lx, 'cached_moe', return_value=(pin, None, b'')), \
                 patch.object(reader.lx, 'decode_moe', return_value=(pin, sheets, [])):
                result = reader.derive(Path(directory), corpus)
        self.assertEqual([r[0] for r in result['rows']], ['2'])
        self.assertEqual(result['rows'][0][6:8], ['要吃飯', '【beh食飯】'])
        self.assertEqual(result['provenance'][0]['raw_example'], 'beh食飯')
        self.assertEqual(result['provenance'][0]['corpus_excerpt']['match_span'], [0, 5])
        self.assertNotIn('華語出處', result['headers'])
        self.assertEqual(len(result['rows'][0]), 11)
        self.assertEqual(result['headers'][-1], '用例來源')
        self.assertEqual(result['rows'][0][-1], 'https://example.org/a')
        self.assertIn('characters 0:5', result['provenance'][0]['example_source'])

    def test_example_source_is_one_native_link(self):
        ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
        rns = 'http://schemas.openxmlformats.org/package/2006/relationships'
        row = [''] * 11
        row[9] = 'https://example.org/moe'
        row[10] = 'https://example.org/article?a=1&b=2'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'plain.xlsx'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('xl/worksheets/sheet1.xml', f'<worksheet xmlns="{ns}"><sheetData/></worksheet>')
            reader.attach_links(path, [row])
            with zipfile.ZipFile(path) as archive:
                sheet = ET.fromstring(archive.read('xl/worksheets/sheet1.xml'))
                relationships = ET.fromstring(archive.read('xl/worksheets/_rels/sheet1.xml.rels'))
        self.assertEqual([link.get('ref') for link in sheet.find(f'{{{ns}}}hyperlinks')], ['J2', 'K2'])
        targets = {link.get('Id'): link.get('Target') for link in relationships}
        self.assertEqual(targets['readerLinkK2'], row[10])
        self.assertEqual(len(relationships.findall(f'{{{rns}}}Relationship')), 2)

    def test_mandarin_falls_back_to_definitions_of_cited_identity_only(self):
        pin = {'id': 'moe', 'sha256': 'fixture'}
        source = {'snapshot': 'moe', 'sheet': '詞目', 'row': 2}
        record = {'source': source, 'record_id': '10', 'headword': '欲', 'reading': 'beh'}
        item = {'id': 1, 'preferred_form': 'beh', 'canonical_tl': 'beh',
                'alternate_readings': [], 'moe_forms': ['欲'], 'sources': [source, {
                    'url': 'https://example.org/a', 'locator':
                    'normalized source characters 0:3; written form beh'}]}
        sheets = {'義項': [(1, ['詞目id', '義項id', '解說']),
                         (2, ['10', '1', '要、想要。']), (3, ['10', '2', '將要。']),
                         (4, ['11', '3', 'Unrelated homophone definition.'])]}
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory) / 'corpus.jsonl'
            corpus.write_text(json.dumps({'id': 'a', 'text': 'beh食飯',
                              'metadata': {'original_url': 'https://example.org/a'}}))
            with patch.object(reader.lx, 'entries', return_value=[(None, item)]), \
                 patch.object(reader.lx, 'lkk_data', return_value={}), \
                 patch.object(reader.lx, 'cached_moe', return_value=(pin, None, b'')), \
                 patch.object(reader.lx, 'decode_moe', return_value=(pin, sheets, [record])):
                result = reader.derive(Path(directory), corpus)
                sheets['詞彙比較'] = [(1, ['漢字', '羅馬字', '華語詞目']), (2, ['欲', 'beh', '要'])]
                explicit = reader.derive(Path(directory), corpus)
        self.assertEqual(result['rows'][0][6], '要、想要。 / 將要。')
        self.assertEqual(result['provenance'][0]['mandarin_sources'], ['moe:義項:2', 'moe:義項:3'])
        self.assertEqual(explicit['rows'][0][6], '要')
        self.assertEqual(explicit['provenance'][0]['mandarin_sources'], ['moe:詞彙比較:2'])

    def test_short_excerpt_preserves_tokens_and_only_display_has_brackets(self):
        from source_excerpts import short_bounds, display_excerpt
        text = '甲' * 80 + 'very-long-roman-word beh very-long-following-word' + '乙' * 80
        a = text.index('beh')
        b = a + 3
        left, right = short_bounds(text, a, b)
        raw = text[left:right]
        self.assertTrue(raw.startswith('very-long-roman-word'))
        self.assertTrue(raw.endswith('very-long-following-word'))
        decorated = display_excerpt(raw, {'excerpt_span': [left, right], 'match_span': [a, b]})
        self.assertIn('【beh】', decorated)
        self.assertNotIn('【', raw)


if __name__ == '__main__':
    unittest.main()
