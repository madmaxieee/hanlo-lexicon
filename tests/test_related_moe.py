"""Hanji-only related-word suggestions with original dictionary provenance."""

import hashlib
import unittest
from unittest import mock

import test_lexicon as support

lex = support.lex


class RelatedMoeTests(unittest.TestCase):
    setUp = support.MaintenanceTests.setUp
    tearDown = support.MaintenanceTests.tearDown
    run_cli = support.MaintenanceTests.run_cli
    request = support.MaintenanceTests.request

    def dictionary(self, words, extra_sheets=None):
        sheets = {'詞目': [['詞目id', '漢字', '羅馬字'], *[
            [number, form, reading] for number, (form, reading) in enumerate(words, 10)]],
            '義項': [['詞目id', '義項id', '解說'], *[
                [number, 1, f'Original definition {number}。'] for number in range(10, 10 + len(words))]]}
        sheets.update(extra_sheets or {})
        path = self.root / 'related.ods'
        support.make_ods(path, sheets)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        pin = self.root / 'references/moe.toml'
        pin.write_text(pin.read_text().replace(lex.load_toml(pin)['sha256'], digest))
        self.moe_path = self.root / '.cache/dictionaries/moe' / digest / 'kautian.ods'
        self.moe_path.parent.mkdir(parents=True, exist_ok=True)
        path.replace(self.moe_path)

    def suggestions(self, form='甲乙', reading='kah-it', **extra):
        return self.run_cli('check', str(self.request(form, reading, **extra)))['related_moe_entries']

    def test_two_glyphs_match_only_the_four_requested_edge_shapes(self):
        positives = [('丁甲乙', 'XAB'), ('甲乙丁', 'ABX'), ('丁戊甲乙', 'XYAB'), ('甲乙丁戊', 'ABXY')]
        negatives = ['甲乙', '甲', '乙甲', '甲丁乙', '丁甲乙戊', '丁戊己甲乙', '甲乙丁戊己', '甲-乙丁']
        self.dictionary([(form, 'hó') for form, _ in positives] + [(form, 'hó') for form in negatives])
        result = self.suggestions()
        self.assertEqual([row['headword'] for row in result], [form for form, _ in positives])
        for row, (form, pattern) in zip(result, positives):
            self.assertEqual(row['relations'], [{'base_form': '甲乙', 'matched_form': form, 'pattern': pattern}])
        self.assertEqual(self.suggestions(reading='bóng'), result)

    def test_three_glyphs_match_two_components_and_one_glyph_extensions(self):
        positives = [('甲乙', 'AB'), ('乙丙', 'BC'), ('丁甲乙丙', 'XABC'), ('甲乙丙丁', 'ABCX')]
        negatives = ['甲乙丙', '甲丙', '甲', '丙', '丁戊甲乙丙', '甲乙丙丁戊', '甲丁乙丙', '乙丙丁']
        self.dictionary([(form, 'hó') for form, _ in positives] + [(form, 'hó') for form in negatives])
        result = self.suggestions('甲乙丙')
        self.assertEqual([row['headword'] for row in result], [form for form, _ in positives])
        self.assertEqual([row['relations'][0]['pattern'] for row in result], [pattern for _, pattern in positives])
        for form in ['甲', '甲乙丙丁', 'kah乙', 'kah-it', '甲-乙']:
            with self.subTest(form=form):
                self.assertEqual(self.suggestions(form), [])

    def test_mixed_and_romanized_forms_use_supplied_hanji_without_reading_search(self):
        self.dictionary([('甲乙', 'kah-it'), ('甲乙丁', 'other'), ('戊己', 'kah-it'), ('戊己丁', 'kah-it')])
        expected = self.suggestions()
        self.assertEqual([row['headword'] for row in expected], ['甲乙丁'])
        self.assertEqual(self.suggestions('kah乙', hanji_forms=['甲乙']), expected)
        self.assertEqual(self.suggestions('kah-it', moe_forms=['甲乙']), expected)
        self.assertEqual(self.suggestions('kah-it'), [])
        # An explicit MOE source selects its Hanji even with no reading match.
        source = {'snapshot': 'moe-fixture', 'sheet': '詞目', 'row': 2}
        self.assertEqual(self.suggestions('kah乙', 'other', sources=[source]), expected)

    def test_variants_annotations_homographs_and_source_payload_are_preserved(self):
        self.dictionary([('甲乙', 'kah-it'), ('丁甲乙【替】', '【文】hó, bái'),
                         ('丁甲乙', 'bóng'), ('戊己', 'hó')], {
            '異用字': [['詞目id', '漢字', '異用字'], [13, '戊己', '甲乙丁']]})
        result = self.suggestions()
        self.assertEqual([row['record_id'] for row in result], ['11', '12', '13'])
        self.assertEqual(result[0]['headword'], '丁甲乙【替】')
        self.assertEqual(result[0]['reading'], '【文】hó, bái')
        self.assertEqual(result[0]['definitions'], ['Original definition 11。'])
        self.assertEqual(result[0]['source'], {'snapshot': 'moe-fixture', 'sheet': '詞目', 'row': 3})
        self.assertEqual(result[0]['column'], '羅馬字')
        self.assertEqual(result[0]['relations'][0]['matched_form'], '丁甲乙')
        self.assertEqual(result[2]['relations'][0]['matched_form'], '甲乙丁')
        self.assertEqual(result[2]['variant_forms'], ['甲乙丁'])

    def test_only_numbered_headwords_are_suggested_without_appendix_duplicates(self):
        self.dictionary([('甲乙丁', 'hó')], {
            '詞彙比較': [['詞目id', '漢字', '羅馬字'], ['comparison', '丁甲乙', 'hó']],
            '姓': [['詞目id', '漢字', '羅馬字'], ['appendix', '甲乙丁', 'hó']],
            '又唸作': [['詞目id', '漢字', '羅馬字'], [10, '甲乙丁', 'bái']]})
        result = self.suggestions()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['source']['sheet'], '詞目')

    def test_repeated_edges_and_multiple_seeds_deduplicate_relations(self):
        self.dictionary([('甲甲甲', 'hó'), ('甲甲甲甲', 'hó')])
        result = self.suggestions('甲甲', hanji_forms=['甲甲'], moe_forms=['甲甲'])
        self.assertEqual(len(result), 2)
        self.assertEqual({relation['pattern'] for relation in result[0]['relations']}, {'XAB', 'ABX'})
        self.assertEqual(len(result[0]['relations']), 2)
        self.assertEqual({relation['pattern'] for relation in result[1]['relations']}, {'XYAB', 'ABXY'})

    def test_variation_selectors_and_supplementary_hanji_count_as_glyphs(self):
        base = '𠞭\U000e0100心'
        self.dictionary([(base + '丁', 'hó'), ('𠞭心丁', 'bái')])
        result = self.suggestions(base)
        self.assertEqual([row['headword'] for row in result], [base + '丁'])
        self.assertEqual(result[0]['relations'][0]['base_form'], base)

    def test_indexed_check_batch_preview_and_add_share_suggestions_without_extra_imports(self):
        self.dictionary([('甲乙', 'kah-it'), ('丁甲乙', 'hó'), ('甲乙丙', 'bái')])
        request = lex.request_data(self.request('kah乙', 'kah-it', hanji_forms=['甲乙'], review_status='reviewed'))
        evidence = lex.lkk_data(self.root), lex.moe_data(self.root)
        direct = lex.check(self.root, request, [], evidence)
        indexed = lex.check(self.root, request, [], evidence, lex.LookupIndex([], evidence))
        self.assertEqual(direct, indexed)
        self.assertEqual(len(direct['related_moe_entries']), 2)
        with mock.patch.object(lex, 'RelatedMoeIndex', wraps=lex.RelatedMoeIndex) as index:
            preview = lex.add_batch(self.root, [request], dry_run=True)
        self.assertEqual(index.call_count, 1)
        self.assertEqual(preview['results'][0]['checks'], direct)
        self.assertEqual(lex.entries(self.root), [])
        self.assertEqual(lex.next_id(self.root, []), 1)
        added = lex.add_batch(self.root, [request])
        self.assertEqual(added['results'][0]['checks'], direct)
        stored = lex.entries(self.root)
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0][1]['review_status'], 'reviewed')
        self.assertNotIn('related_moe_entries', stored[0][1])
        lex.validate(self.root)

    def test_related_lookup_still_rejects_a_corrupt_pinned_dictionary(self):
        self.dictionary([('甲乙丁', 'hó')])
        self.moe_path.write_bytes(b'changed')
        error = self.run_cli('check', str(self.request('甲乙', 'kah-it')), expected=2)
        self.assertIn('checksum mismatch', error)
        self.assertEqual(lex.entries(self.root), [])


if __name__ == '__main__':
    unittest.main()
