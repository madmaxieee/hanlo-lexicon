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

    def test_existing_seed_spelling_is_retained_with_full_inventory_conflict_evidence(self):
        self.setup_dictionary()
        self.evidence_words()
        roman = self.word('kah', 'kah', '甲', review_status='reviewed')
        self.word('kah乙', 'kah-it', '甲乙', review_status='machine-reviewed')
        item = self.report()['items'][0]
        proposal, = item['writing_suggestions']
        self.assertEqual(proposal['suggested_form'], 'kah乙丁')
        self.assertEqual(proposal['status'], 'consistent')
        self.assertTrue(proposal['positions'][0]['inherited_from_seed'])
        self.assertEqual(proposal['positions'][0]['inventory_status'], 'conflicting')
        hanji, romanized = proposal['positions'][0]['inventory_choices']
        self.assertEqual((hanji['kind'], hanji['token']), ('hanji', '甲'))
        self.assertEqual((romanized['kind'], romanized['token']), ('romanized', 'kah'))
        self.assertIn(roman, romanized['entry_ids'])
        self.assertEqual(len(romanized['evidence']), 2)
        document = related.markdown(self.report())
        self.assertIn('romanized: **kah**', document)
        self.assertIn('https://example.org/source', document)
        self.assertIn('Retained from the matching existing seed', document)

    def test_added_positions_still_preserve_conflicts(self):
        self.setup_dictionary()
        self.word('kah乙', 'kah-it', '甲乙')
        self.word('丁', 'ting')
        self.word('ting', 'ting', '丁')
        proposal = self.report()['items'][0]['writing_suggestions'][0]
        self.assertEqual(proposal['status'], 'conflicting')
        self.assertIsNone(proposal['suggested_form'])
        self.assertEqual(len(proposal['positions'][2]['choices']), 2)

    def test_seed_preserves_ke_and_dictionary_variant_does_not_demote_main_spelling(self):
        self.dictionary([('頭家', 'thâu-ke'), ('厝頭家', 'tshù-thâu-ke')],
                        {'異用字': [['詞目id', '漢字', '異用字'], [11, '厝頭家', '茨頭家']]})
        identity = self.word('頭ke', 'thâu-ke', '頭家')
        self.word('家', 'ke')
        self.word('厝', 'tshù')
        item, = related.find(self.root, ['頭家'], [identity])['items']
        proposal, = item['writing_suggestions']
        self.assertEqual(proposal['hanji_form'], '厝頭家')
        self.assertEqual(proposal['suggested_form'], '厝頭ke')
        self.assertEqual(related.review_category(item), 'Consistent proposals')
        variant, = item['variant_writing_suggestions']
        self.assertEqual(variant['hanji_form'], '茨頭家')
        self.assertEqual(variant['positions'][0]['status'], 'unknown')

    def test_imported_seed_supplies_repeated_new_combo(self):
        self.dictionary([('平坦', 'pênn-thánn'), ('平坦坦', 'pênn-thánn-thánn')])
        identity = self.word('平thánn', 'pênn-thánn', '平坦')
        item, = related.find(self.root, ['平坦'], [identity])['items']
        proposal, = item['writing_suggestions']
        self.assertEqual(proposal['suggested_form'], '平thánn-thánn')
        self.assertEqual(proposal['positions'][2]['status'], 'consistent_romanized')

    def test_shorter_words_remove_the_extra_seed_units_without_new_writing_questions(self):
        self.dictionary([('塞喙空', 'that-tshuì-khang'), ('塞喙', 'that-tshuì'), ('喙空', 'tshuì-khang')])
        identity = self.word('that喙空', 'that-tshuì-khang', '塞喙空')
        report = related.find(self.root, ['塞喙空'], [identity])
        self.assertEqual({item['headword']: item['writing_suggestions'][0]['suggested_form']
                          for item in report['items']}, {'塞喙': 'that喙', '喙空': '喙空'})
        self.assertTrue(all(related.review_category(item) == 'Consistent proposals' for item in report['items']))

    def test_shorter_overlap_does_not_conflict_over_a_removed_leading_separator(self):
        self.dictionary([('甲乙丙', 'kah-it-ping'), ('乙丙丁', 'it-ping-ting'), ('乙丙', 'it-ping')])
        first = self.word('kah-it-ping', 'kah-it-ping', '甲乙丙')
        second = self.word('it-ping-ting', 'it-ping-ting', '乙丙丁')
        item = next(i for i in related.find(self.root, ['甲乙丙', '乙丙丁'], [first, second])['items']
                    if i['headword'] == '乙丙')
        self.assertEqual(item['writing_suggestions'][0]['suggested_form'], 'it-ping')
        self.assertEqual(item['writing_suggestions'][0]['status'], 'consistent')

    def test_generated_seed_does_not_supply_inherited_recommendation_evidence(self):
        self.setup_dictionary()
        identity = self.word('kah乙', 'kah-it', '甲乙', rule_generated=True)
        self.word('丁', 'ting')
        proposal = related.find(self.root, ['甲乙'], [identity])['items'][0]['writing_suggestions'][0]
        self.assertEqual(proposal['status'], 'incomplete')
        self.assertFalse(any(p.get('inherited_from_seed') for p in proposal['positions']))

    def test_unknown_generated_disputed_and_contracted_positions_require_manual_review(self):
        self.setup_dictionary('kah-it-ting, khah-it-ting, hó')
        self.word('甲', 'kah', alternate_readings=['khah'])
        self.word('it', 'it', '乙', rule_generated=True)
        self.word('丁', 'ting', review_status='disputed')
        proposals = self.report()['items'][0]['writing_suggestions']
        self.assertEqual([p['status'] for p in proposals], ['incomplete'])
        self.assertEqual(proposals[0]['positions'][1]['choices'], [])
        self.assertEqual(proposals[0]['positions'][2]['choices'], [])
        self.assertEqual([p['canonical_tl'] for p in proposals], ['kah-it-ting'])
        self.assertTrue(all(p['suggested_form'] is None for p in proposals))

    def test_conflict_counts_deduplicate_entries_and_limit_each_side_to_three_examples(self):
        def evidence(identity, form):
            return {'entry_id': identity, 'preferred_form': form}
        hanji = [evidence(number, f'甲例{number}') for number in range(1, 5)]
        roman = [evidence(number, f'kah例{number}') for number in range(5, 10)]
        position = {'hanji': '甲', 'canonical_tl': 'kah', 'status': 'conflicting', 'choices': [
            {'kind': 'hanji', 'token': '甲', 'evidence': hanji},
            {'kind': 'hanji', 'token': '另字', 'evidence': [hanji[0]]},
            {'kind': 'romanized', 'token': 'kah', 'evidence': roman}]}
        sides = related.support_sides(position)
        self.assertEqual([side['entry_count'] for side in sides], [4, 5])
        self.assertEqual([len(side['examples']) for side in sides], [3, 3])
        item = {'writing_suggestions': [{'positions': [position]}, {'positions': [position]}]}
        summary = related.conflict_summary(item)
        self.assertEqual(summary.count('甲/kah:'), 1)
        self.assertIn('Hanji 4 (甲例1, 甲例2, 甲例3)', summary)
        self.assertIn('Romanized 5 (kah例5, kah例6, kah例7)', summary)
        self.assertNotIn('甲例4', summary)
        self.assertNotIn('kah例8', summary)

    def test_new_only_index_shows_existing_seed_spellings_and_omits_related_overlaps(self):
        self.setup_dictionary()
        seed_id = self.word('甲it', 'kah-it', '甲乙')
        self.word('ping甲乙', 'ping-kah-it', '丙甲乙')
        report = self.report()
        seed = next(entry for _, entry in lex.entries(self.root) if entry['id'] == seed_id)
        document = related.index_markdown(report, {'甲乙': [seed]}, self.root / 'pages')
        self.assertIn(f'甲it (#{seed_id})', document)
        self.assertIn('[甲乙丁 — MOE 11]', document)
        self.assertNotIn('[丙甲乙 — MOE 12]', document)
        self.assertIn('**1 new candidates** shown; **1** rows', document)
        self.assertIn('Proposed form of new word', document)
        path = self.root / '.cache/related-moe/post-import.md'
        related.write_markdown(report, path)
        self.assertNotIn('[丙甲乙 — MOE 12]', path.read_text())
        self.assertFalse((path.with_name('post-import-entries') / 'moe-12-row-4.md').exists())
        page = path.with_name('post-import-entries') / 'moe-11-row-3.md'
        self.assertIn('Original definition 11', page.read_text())
        self.assertTrue(next(i for i in report['items'] if i['record_id'] == '12')['existing_entry_candidates'])

    def test_central_ng_seed_does_not_match_central_iong_in_larger_word(self):
        self.dictionary([('中央', 'tiong-ng'), ('中央公園', 'Tiong-iong Kong-hn̂g'),
                         ('中央路', 'tiong-ng-lōo')])
        seed_id = self.word('中ng', 'tiong-ng', '中央')
        report = related.find(self.root, ['中央'], [seed_id])
        self.assertEqual([item['headword'] for item in report['items']], ['中央路'])
        proof = report['items'][0]['relations'][0]['combo_matches'][0]
        self.assertEqual(proof['seed_entry_id'], seed_id)
        self.assertEqual(proof['shared_combos'], [{'hanji': '中', 'canonical_tl': 'tiong'},
                                                 {'hanji': '央', 'canonical_tl': 'ng'}])

    def test_combo_match_checks_every_position_tones_and_complete_reading_alternatives(self):
        self.dictionary([('甲乙', 'kah-it, khah-ít'), ('甲乙丁', 'kah-ít-ting'),
                         ('甲乙丙', 'khah-ít-ping'), ('丁甲乙', 'ting-kah-it')])
        seed_id = self.word('甲it', 'kah-it', '甲乙', alternate_readings=['khah-ít'])
        report = related.find(self.root, ['甲乙'], [seed_id])
        self.assertEqual([item['headword'] for item in report['items']], ['甲乙丙', '丁甲乙'])
        self.assertEqual(report['items'][0]['reading_options'][0]['canonical_tl'], 'khah-ít-ping')
        self.assertEqual(report['items'][0]['relations'][0]['combo_matches'][0]['seed_reading'], 'khah-ít')

    def test_neutral_markers_and_shorter_bc_use_the_shared_positions_exactly(self):
        self.dictionary([('甲乙丙', 'kah--it-ping'), ('甲乙', 'kah-it'),
                         ('乙丙', '--it-ping'), ('甲乙丙丁', 'kah-it-ping-ting')])
        seed_id = self.word('甲--it丙', 'kah--it-ping', '甲乙丙')
        report = related.find(self.root, ['甲乙丙'], [seed_id])
        self.assertEqual([item['headword'] for item in report['items']], ['乙丙'])
        self.assertEqual(report['items'][0]['relations'][0]['pattern'], 'BC')
        self.assertEqual(report['items'][0]['relations'][0]['combo_matches'][0]['shared_combos'],
                         [{'hanji': '乙', 'canonical_tl': '--it'}, {'hanji': '丙', 'canonical_tl': 'ping'}])

    def test_reading_options_and_seed_attribution_include_only_matching_combos(self):
        self.setup_dictionary('kah-it-ting, khah-it-ting, hó')
        first = self.word('甲it', 'kah-it', '甲乙')
        second = self.word('khah乙', 'khah-it', '甲乙')
        report = related.find(self.root, ['甲乙'], [first])
        item = report['items'][0]
        self.assertEqual([option['canonical_tl'] for option in item['reading_options']], ['kah-it-ting'])
        self.assertEqual({proof['seed_entry_id'] for relation in item['relations'] for proof in relation['combo_matches']}, {first})
        seed_entries = {'甲乙': [entry for _, entry in lex.entries(self.root)]}
        document = related.index_markdown(report, seed_entries, self.root / 'pages')
        self.assertIn(f'甲it (#{first})', document)
        self.assertNotIn(f'khah乙 (#{second})', document)
        self.assertNotIn('khah-it-ting', document)
        self.assertIn(f'甲it (#{first})', related.index_markdown(report, {}, self.root / 'pages'))
        # No explicit scope: each real source entry can establish its own match.
        both = related.find(self.root, ['甲乙'])['items'][0]
        self.assertEqual({proof['seed_entry_id'] for relation in both['relations'] for proof in relation['combo_matches']}, {first, second})

    def test_unalignable_seed_cannot_fall_back_to_a_different_dictionary_reading(self):
        self.setup_dictionary()
        seed_id = self.word('甲乙', 'hó')
        self.assertEqual(related.find(self.root, ['甲乙'], [seed_id])['items'], [])
        self.assertEqual(related.find(self.root, ['甲乙'])['items'], [])

    def test_entry_scoped_cli_records_the_seed_scope_and_revalidates_it_for_import(self):
        self.setup_dictionary()
        seed_id = self.word('甲it', 'kah-it', '甲乙')
        report = self.run_cli('related', '甲乙', '--entry-id', str(seed_id))
        self.assertEqual(report['seed_entry_ids'], [seed_id])
        path = self.root / 'scoped-review.json'
        path.write_text(json.dumps(report, ensure_ascii=False))
        preview = self.run_cli('import-related', str(path))
        self.assertEqual(preview['pending'], 2)
        self.run_cli('related', '甲乙', '--entry-id', '999', expected=2)

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

    def test_batch_adopted_consistent_proposals_preserve_machine_review_status(self):
        self.setup_dictionary()
        self.evidence_words()
        report = self.approve(self.report(), review_status='machine-reviewed')
        result = related.import_reviewed(self.root, report, apply=True)
        entry = lex.load_toml(self.root / result['results'][0]['created'])
        self.assertEqual(entry['review_status'], 'machine-reviewed')

    def test_machine_review_mode_does_not_approve_combo_conflicts(self):
        self.setup_dictionary()
        self.evidence_words()
        self.word('kah', 'kah', '甲')
        report = self.approve(self.report(), review_status='machine-reviewed')
        with self.assertRaisesRegex(lex.Error, 'consistent complete'):
            related.import_reviewed(self.root, report, apply=True)

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
        self.dictionary([('甲乙', 'kah-it, khah-it'), ('甲乙丁', 'kah-it-ting'), ('丙甲乙', 'ping-kah-it')],
                        {'又唸作': [['詞目id', '漢字', '羅馬字'], [11, '甲乙丁', 'khah-it-ting']]})
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
