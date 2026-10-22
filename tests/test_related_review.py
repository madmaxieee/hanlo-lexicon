"""Standalone combo-backed proposals and individual human-reviewed import behavior."""

import copy
import json
import unittest
from unittest import mock

import test_lexicon as support
import test_related_moe as related_fixtures
import related_moe as related

lex = related.lex


class RelatedReviewTests(unittest.TestCase):
    setUp = support.MaintenanceTests.setUp
    tearDown = support.MaintenanceTests.tearDown
    run_cli = support.MaintenanceTests.run_cli
    request = support.MaintenanceTests.request
    dictionary = related_fixtures.RelatedMoeTests.dictionary

    def setup_dictionary(self, readings='kah-it-ting', extra_sheets=None):
        self.dictionary([('甲乙', 'kah-it'), ('甲乙丁', readings), ('丙甲乙', 'ping-kah-it')], extra_sheets)

    def word(self, preferred, reading, hanji=None, **extra):
        request = lex.normalize_request({'preferred_form': preferred, 'canonical_tl': reading,
            'sources': [{'url': 'https://example.org/source', 'locator': f'Original word: {preferred}'}],
            **({'hanji_forms': [hanji]} if hanji else {}), **extra})
        return lex.add_batch(self.root, [request])['results'][0]['id']

    def evidence_words(self):
        return [self.word('甲', 'kah'), self.word('it', 'it', '乙'), self.word('丁', 'ting')]

    def report(self):
        return related.find(self.root, ['甲乙'])

    def approve(self, report, index=0, preferred='甲it丁', reading='kah-it-ting', **extra):
        report['items'][index]['review'].update(decision='approved', preferred_form=preferred,
                                               canonical_tl=reading, **extra)
        return report

    def test_consistent_longer_spelling_uses_tone_exact_canonical_combos_and_original_evidence(self):
        self.setup_dictionary()
        ids = self.evidence_words()
        report = self.report()
        proposal = report['items'][0]['writing_suggestions'][0]
        self.assertEqual(proposal['suggested_form'], '甲it丁')
        self.assertEqual(proposal['status'], 'consistent')
        for position, identity in zip(proposal['positions'], ids):
            evidence, = position['choices'][0]['evidence']
            self.assertEqual(evidence['entry_id'], identity)
            self.assertTrue(evidence['path'].startswith(str(self.root)))
            self.assertEqual(evidence['sources'][0]['url'], 'https://example.org/source')
            self.assertEqual(evidence['review_status'], 'imported')
        self.assertTrue(all(row['requires_human_review'] for row in report['items']))
        self.assertTrue(all(row['review']['decision'] == 'pending' for row in report['items']))
        request = lex.normalize_request({'preferred_form': 'kah-it', 'canonical_tl': 'kah-it', 'hanji_forms': ['甲乙']})
        self.assertEqual(lex.check(self.root, request)['related_moe_entries'][0]['writing_suggestions'],
                         report['items'][0]['writing_suggestions'])

    def test_conflicts_attach_all_hanji_and_romanization_evidence_without_majority_choice(self):
        self.setup_dictionary()
        self.evidence_words()
        roman = self.word('kah', 'kah', '甲', review_status='reviewed')
        self.word('kah乙', 'kah-it', '甲乙', review_status='machine-reviewed')
        item = self.report()['items'][0]
        proposal, = item['writing_suggestions']
        self.assertIsNone(proposal['suggested_form'])
        self.assertEqual(proposal['status'], 'conflicting')
        hanji, romanized = proposal['positions'][0]['choices']
        self.assertEqual((hanji['kind'], hanji['token']), ('hanji', '甲'))
        self.assertEqual((romanized['kind'], romanized['token']), ('romanized', 'kah'))
        self.assertIn(roman, romanized['entry_ids'])
        self.assertEqual(len(romanized['evidence']), 2)
        document = related.markdown(self.report())
        self.assertIn('hanji: **甲**', document)
        self.assertIn('romanized: **kah**', document)
        self.assertIn('https://example.org/source', document)
        self.assertIn('manual review (conflicting)', document)

    def test_unknown_generated_disputed_and_contracted_positions_require_manual_review(self):
        self.setup_dictionary('kah-it-ting, khah-it-ting, hó')
        self.word('甲', 'kah', alternate_readings=['khah'])
        self.word('it', 'it', '乙', rule_generated=True)
        self.word('丁', 'ting', review_status='disputed')
        proposals = self.report()['items'][0]['writing_suggestions']
        self.assertEqual([p['status'] for p in proposals], ['incomplete', 'incomplete', 'unalignable'])
        self.assertEqual(proposals[0]['positions'][1]['choices'], [])
        self.assertEqual(proposals[0]['positions'][2]['choices'], [])
        self.assertEqual(proposals[1]['positions'][0]['choices'], [])
        self.assertTrue(all(p['suggested_form'] is None for p in proposals))

    def test_neutral_tone_and_adjacent_roman_syllables_render_without_changing_boundaries(self):
        self.setup_dictionary('kah-it--ê')
        self.word('kah', 'kah', '甲')
        self.word('it', 'it', '乙')
        self.word('--ê', '--ê', '丁')
        proposal = self.report()['items'][0]['writing_suggestions'][0]
        self.assertEqual(proposal['suggested_form'], 'kah-it--ê')
        self.assertEqual(proposal['positions'][2]['canonical_tl'], '--ê')

    def test_shorter_entries_still_need_human_review_but_do_not_get_longer_word_proposals(self):
        self.setup_dictionary()
        report = related.find(self.root, ['甲乙丁'])
        self.assertEqual([item['headword'] for item in report['items']], ['甲乙'])
        self.assertEqual(report['items'][0]['writing_suggestions'], [])
        self.assertEqual(report['items'][0]['review']['decision'], 'pending')
        self.assertTrue(report['items'][0]['reading_options'])

    def test_standalone_cli_has_no_import_or_reading_input_and_outputs_readable_evidence(self):
        self.setup_dictionary()
        self.evidence_words()
        before = (self.root / 'id-sequence.toml').read_bytes()
        output, document = self.root / '.cache/related-moe/review.json', self.root / '.cache/related-moe/review.md'
        report = self.run_cli('related', '甲乙', '--out', str(output), '--markdown', str(document))
        self.assertEqual(json.loads(output.read_text()), report)
        self.assertIn('甲it丁', document.read_text())
        self.assertEqual((self.root / 'id-sequence.toml').read_bytes(), before)
        self.assertEqual(len(lex.entries(self.root)), 3)
        for form in ['kah-it', 'kah乙', '甲', '甲乙丁戊']:
            self.run_cli('related', form, expected=2)
        self.run_cli('related', '甲乙', '--out', str(self.root / 'id-sequence.toml'), expected=2)
        self.assertEqual((self.root / 'id-sequence.toml').read_bytes(), before)

    def test_pending_is_never_imported_and_individual_approval_imports_as_reviewed(self):
        self.setup_dictionary()
        self.evidence_words()
        report = self.report()
        result = related.import_reviewed(self.root, report, apply=True)
        self.assertEqual((result['approved'], result['pending'], result['results']), (0, 2, []))
        self.approve(report, editorial_rationale='Human chose the consistent mixed form after individual review.')
        report['items'][1]['review']['decision'] = 'rejected'
        preview = related.import_reviewed(self.root, report)
        self.assertEqual(preview['mode'], 'preview')
        self.assertEqual(len(lex.entries(self.root)), 3)
        result = related.import_reviewed(self.root, report, apply=True)
        entry = lex.load_toml(self.root / result['results'][0]['created'])
        self.assertEqual(entry['preferred_form'], '甲it丁')
        self.assertEqual(entry['review_status'], 'reviewed')
        self.assertNotIn('rule_generated', entry)
        self.assertEqual(entry['sources'], [{'snapshot': 'moe-fixture', 'sheet': '詞目', 'row': 3}])
        self.assertIn('Human chose', entry['editorial_rationale'])
        self.assertEqual(len(lex.entries(self.root)), 4)
        self.run_cli('validate')
        self.run_cli('format', '--check')

    def test_human_can_resolve_a_conflict_by_selecting_the_whole_spelling(self):
        self.setup_dictionary()
        self.evidence_words()
        self.word('kah', 'kah', '甲')
        report = self.approve(self.report(), preferred='kah-it丁')
        result = related.import_reviewed(self.root, report, apply=True)
        entry = lex.load_toml(self.root / result['results'][0]['created'])
        self.assertEqual((entry['preferred_form'], entry['review_status']), ('kah-it丁', 'reviewed'))

    def test_import_cli_applies_only_the_individually_approved_word_and_leaves_pending_out(self):
        self.setup_dictionary()
        report = self.run_cli('related', '甲乙')
        self.approve(report, preferred='甲乙丁')
        path = self.root / 'human-review.json'
        path.write_text(json.dumps(report, ensure_ascii=False))
        preview = self.run_cli('import-related', str(path))
        self.assertEqual((preview['approved'], preview['pending']), (1, 1))
        self.assertEqual(lex.entries(self.root), [])
        result = self.run_cli('import-related', str(path), '--apply')
        self.assertEqual(len(result['results']), 1)
        entry = lex.load_toml(self.root / result['results'][0]['created'])
        self.assertEqual((entry['preferred_form'], entry['review_status']), ('甲乙丁', 'reviewed'))
        self.assertEqual(len(lex.entries(self.root)), 1)

    def test_bad_or_incomplete_decisions_and_unsupported_readings_do_not_allocate(self):
        self.setup_dictionary()
        original = self.report()
        for edit in [{'decision': True}, {'decision': []}, {'decision': 'approved'},
                     {'decision': 'approved', 'preferred_form': '甲乙丁', 'canonical_tl': 'bóng'},
                     {'decision': 'approved', 'preferred_form': '甲乙丁', 'canonical_tl': 'kah-it-ting',
                      'alternate_readings': ['kah-it-ting']}]:
            report = copy.deepcopy(original)
            report['items'][0]['review'].update(edit)
            with self.subTest(edit=edit), self.assertRaises(lex.Error):
                related.import_reviewed(self.root, report, apply=True)
            self.assertEqual(lex.next_id(self.root, []), 1)
            self.assertEqual(lex.entries(self.root), [])

    def test_sourced_alternate_readings_stay_in_one_human_reviewed_entry(self):
        self.setup_dictionary(extra_sheets={'又唸作': [['詞目id', '漢字', '羅馬字'], [11, '甲乙丁', 'khah-it-ting']]})
        report = self.approve(self.report(), preferred='甲乙丁', alternate_readings=['khah-it-ting'])
        result = related.import_reviewed(self.root, report, apply=True)
        entry = lex.load_toml(self.root / result['results'][0]['created'])
        self.assertEqual(entry['alternate_readings'], ['khah-it-ting'])
        self.assertEqual(entry['review_status'], 'reviewed')
        self.assertTrue(any(source['sheet'] == '又唸作' for source in entry['sources']))

    def test_tampered_evidence_and_stale_entry_or_dictionary_state_are_rejected(self):
        self.setup_dictionary()
        report = self.approve(self.report())
        tampered = copy.deepcopy(report)
        tampered['items'][0]['definitions'] = ['Changed evidence']
        with self.assertRaisesRegex(lex.Error, 'evidence changed'):
            related.import_reviewed(self.root, tampered, apply=True)
        self.word('hó', 'hó')
        with self.assertRaisesRegex(lex.Error, 'stale'):
            related.import_reviewed(self.root, report, apply=True)
        report = self.approve(self.report())
        self.setup_dictionary('kah-it-ting, khah-it-ting')
        with self.assertRaisesRegex(lex.Error, 'stale'):
            related.import_reviewed(self.root, report, apply=True)
        self.assertEqual(len(lex.entries(self.root)), 1)

    def test_writer_rechecks_the_review_snapshot_before_reserving_ids(self):
        self.setup_dictionary()
        report = self.approve(self.report(), preferred='甲乙丁')
        add = lex.add_batch
        def changed_before_lock(root, requests, **kwargs):
            with mock.patch.object(lex, 'add_batch', add):
                self.word('hó', 'hó')
            return add(root, requests, **kwargs)
        with mock.patch.object(lex, 'add_batch', side_effect=changed_before_lock), self.assertRaisesRegex(lex.Error, 'changed before import'):
            related.import_reviewed(self.root, report, apply=True)
        self.assertEqual(len(lex.entries(self.root)), 1)
        self.assertEqual(lex.next_id(self.root, lex.entries(self.root)), 2)

    def test_existing_dictionary_identity_requires_explicit_distinct_word_resolution(self):
        self.setup_dictionary()
        self.word('kah-it-ting', 'kah-it-ting', '甲乙丁')
        report = self.approve(self.report(), preferred='甲乙丁')
        self.assertEqual(len(report['items'][0]['existing_entry_candidates']), 1)
        with self.assertRaisesRegex(lex.Error, 'resolve identity explicitly'):
            related.import_reviewed(self.root, report, apply=True)
        self.assertEqual(len(lex.entries(self.root)), 1)


if __name__ == '__main__':
    unittest.main()
