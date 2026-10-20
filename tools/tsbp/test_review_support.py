import unittest

from review_support import add_review_choices, collapse_cards, reading_variants
from import_review import build_request, build_custom_request


def record(headword, reading, identity='8913', sheet='詞目', row=8911):
    return {'headword': headword, 'reading': reading, 'record_id': identity,
            'definitions': ['fixture'], 'variant_forms': [], 'column': '羅馬字',
            'source': {'snapshot': 'moe-test', 'sheet': sheet, 'row': row}}


class ReviewTests(unittest.TestCase):
    def test_primary_readings_keep_original_order_and_stable_choice_ids(self):
        primary = record('物件', 'mn̍gh-kiānn/mi̍h-kiānn', '4343')
        alternate = record('物件', 'mih-kiānn', '4343', sheet='又唸作', row=30)
        self.assertEqual(reading_variants(primary), ['mn̍gh-kiānn', 'mi̍h-kiānn'])
        match = {**primary, 'reading': 'mi̍h-kiānn'}
        group = {'moe_matches': [match]}
        add_review_choices([group], [alternate, primary])
        choices = group['review_words'][0]['readings']
        self.assertEqual([r['reading'] for r in choices], ['mn̍gh-kiānn', 'mi̍h-kiānn', 'mih-kiānn'])
        self.assertEqual([(r['primary_index'],r['primary_count']) for r in choices[:2]], [(1,2),(2,2)])
        self.assertEqual([r['detected'] for r in choices], [False,True,False])
        self.assertNotIn('primary_index', choices[2])
        ids = {r['reading']:r['id'] for r in choices}
        add_review_choices([group], [primary,alternate])
        self.assertEqual({r['reading']:r['id'] for r in group['review_words'][0]['readings']}, ids)

    def test_structured_custom_request_preserves_optional_hanji_without_moe_claim(self):
        _, group, _ = self.fixture()
        request = build_custom_request({'preferred_form': 'liô心', 'hanji': '𠞭心',
                                        'reading': 'liô-sim'}, group)
        self.assertEqual(request['preferred_form'], 'liô心')
        self.assertEqual(request['canonical_tl'], 'liô-sim')
        self.assertEqual(request['hanji_forms'], ['𠞭心'])
        self.assertEqual(request['moe_forms'], [])
        self.assertEqual(request['review_status'], 'imported')
        self.assertEqual(request['sources'][0]['url'], 'https://example.com/article')
        request = build_custom_request({'preferred_form': 'liô心', 'reading': 'liô-sim'}, group)
        self.assertNotIn('hanji_forms', request)
        for bad in [{'preferred_form': 'liô心'}, {'reading': 'liô-sim'},
                    {'preferred_form': 'liô心', 'reading': 'wrong!'},
                    {'preferred_form': 'liô\n心', 'reading': 'liô-sim'}]:
            with self.assertRaises(ValueError):
                build_custom_request(bad, group)

    def fixture(self):
        records = [record('翕相', 'hip-siòng'), record('翕相', 'hip-siōng', sheet='又唸作', row=725)]
        group = {'key': 'hip相', 'dedup_lookup_forms': ['hip相'], 'parser_compatible': True,
                 'moe_matches': [records[0], dict(records[0])],
                 'occurrences': [{'url': 'https://example.com/article', 'line': 3,
                                  'anchor_start': 20, 'anchor_end': 24, 'anchor': 'hip相'}]}
        add_review_choices([group], records)
        word = group['review_words'][0]
        approval = {'approved': True, 'word_id': word['id'], 'preferred_form': 'hip相',
                    'canonical_choice_id': word['readings'][0]['id'],
                    'alternate_choice_ids': [word['readings'][1]['id']]}
        return records, group, approval

    def test_duplicate_cards_keep_all_references_and_senses(self):
        one = record('毋知', 'm̄ tsai', '976', row=977)
        two = record('毋知', 'm̄ tsai', '976', '詞彙比較', 12)
        two['definitions'] = ['another source definition']
        cards = collapse_cards([one, one, two])
        self.assertEqual(len(cards), 1)
        self.assertEqual(len(cards[0]['references']), 2)
        self.assertEqual(len(cards[0]['definitions']), 2)

    def test_additional_readings_come_from_same_word_even_when_not_detected(self):
        records, group, approval = self.fixture()
        self.assertEqual(len(group['moe_cards']), 1)
        choices = group['review_words'][0]['readings']
        self.assertEqual({choice['reading'] for choice in choices}, {'hip-siòng', 'hip-siōng'})
        self.assertEqual(sum(choice['detected'] for choice in choices), 1)
        self.assertEqual(len({choice['id'] for choice in choices}), 2)

    def test_approved_request_keeps_aliases_sources_and_schema_fields(self):
        records, group, approval = self.fixture()
        request = build_request(approval, group, [], records)
        self.assertEqual(request['preferred_form'], 'hip相')
        self.assertEqual(request['canonical_tl'], 'hip-siòng')
        self.assertEqual(request['alternate_readings'], ['hip-siōng'])
        self.assertEqual(request['moe_forms'], ['翕相'])
        self.assertEqual(request['review_status'], 'imported')
        self.assertEqual(len(request['sources']), 3)
        self.assertNotIn('definitions', request)
        self.assertNotIn('id', request)

    def source_fixture(self):
        group = {'key':'chhiū-lo̍h','display':'Chhiū-lo̍h','normalized_tl':'tshiū-lo̍h',
                 'normalized_forms':['tshiū-lo̍h'],'dedup_lookup_forms':['chhiū-lo̍h','tshiū-lo̍h'],
                 'parser_compatible':True,'review_words':[],
                 'occurrences':[{'url':'https://example.com/article','line':3,
                                 'anchor_start':20,'anchor_end':29,'anchor':'Chhiū-lo̍h'}]}
        approval = {'approved':True,'import_mode':'source_anchor','preferred_form':'tshiū-lo̍h',
                    'source_reading':'tshiū-lo̍h','word_id':'','canonical_choice_id':'',
                    'alternate_choice_ids':[]}
        return group, approval

    def test_source_only_romanized_import_has_article_provenance_and_no_invented_moe_data(self):
        group, approval = self.source_fixture()
        request = build_request(approval,group,[],[])
        self.assertEqual(request['preferred_form'],'tshiū-lo̍h')
        self.assertEqual(request['canonical_tl'],'tshiū-lo̍h')
        self.assertEqual(request['moe_forms'],[])
        self.assertEqual(request['alternate_readings'],[])
        self.assertEqual(request['review_status'],'imported')
        self.assertEqual(len(request['sources']),1)
        self.assertIn('Chhiū-lo̍h',request['sources'][0]['locator'])

    def test_source_only_approval_cannot_replace_its_reading_or_smuggle_moe_choices(self):
        group, approval = self.source_fixture()
        for changes in [{'source_reading':'other'}, {'word_id':'moe:1'},
                        {'canonical_choice_id':'foreign'}, {'alternate_choice_ids':['foreign']}]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                build_request({**approval,**changes},group,[],[])

    def test_source_only_import_keeps_mixed_invalid_ignored_and_unapproved_guards(self):
        group, approval = self.source_fixture()
        for changes in [{'parser_compatible':False},{'normalized_tl':None},
                        {'display':'hip相'},{'normalized_tl':'翕相'}]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                build_request(approval,{**group,**changes},[],[])
        for changes in [{'preferred_form':'hip相'},{'approved':False},{'custom_handling':'check this'}]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                build_request({**approval,**changes},group,[],[])
        with self.assertRaises(ValueError):
            build_request(approval,group,['tshiū-lo̍h'],[])

    def test_custom_handling_blocks_automatic_import(self):
        records, group, approval = self.fixture()
        for field, value in [('custom_handling', 'Use a different preferred spelling after review.'),
                             ('custom_preferred_form', 'liô心'), ('custom_hanji', '𠞭心'),
                             ('custom_reading', 'liô-sim')]:
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'custom handling'):
                build_request({**approval, field: value}, group, [], records)

    def test_ignore_never_becomes_import_approval(self):
        records, group, approval = self.fixture()
        with self.assertRaisesRegex(ValueError, 'ignored'):
            build_request(approval, group, ['hip相'], records)
        approval['approved'] = False
        with self.assertRaisesRegex(ValueError, 'explicit'):
            build_request(approval, group, [], records)

    def test_foreign_reading_choice_and_tampered_reference_are_rejected(self):
        records, group, approval = self.fixture()
        approval['alternate_choice_ids'] = ['another-word-choice']
        with self.assertRaisesRegex(ValueError, 'same selected'):
            build_request(approval, group, [], records)
        approval['alternate_choice_ids'] = []
        with self.assertRaisesRegex(ValueError, 'pinned MOE row'):
            build_request(approval, group, [], [record('翕相', 'unrelated')])


if __name__ == '__main__':
    unittest.main()
