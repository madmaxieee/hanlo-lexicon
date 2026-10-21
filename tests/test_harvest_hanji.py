"""Synthetic dictionary/corpus cases; no network and no real entry writes."""

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from test_lexicon import lex, make_ods


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('harvest_hanji', ROOT / 'tools/harvest_hanji.py')
harvest = importlib.util.module_from_spec(SPEC)
with mock.patch.dict(sys.modules, {'lexicon': lex}):
    SPEC.loader.exec_module(harvest)


def record(identity, form, reading, sheet='詞目', row=2):
    return {'record_id': str(identity), 'headword': form, 'reading': reading,
            'column': '羅馬字', 'definitions': ['Synthetic fixture.'], 'variant_forms': ['丁'],
            'source': {'snapshot': 'moe-fixture', 'sheet': sheet, 'row': row}}


def doc(text, identity='a'):
    return {'id': identity, 'text': text, 'metadata': {'title': identity, 'original_url': 'https://example.com/' + identity}}


def entry(identity, form, reading, hanji_forms=(), **extra):
    return (Path(f'entries/fixture-{identity}.toml'), {
        'id': identity, 'preferred_form': form, 'canonical_tl': reading,
        'moe_forms': list(hanji_forms), 'alternate_readings': [],
        'review_status': 'imported', **extra})


class HanjiHarvestTests(unittest.TestCase):
    def run_report(self, records, docs, current=(), **kwargs):
        occurrences, groups = [], []
        candidates = harvest.dictionary_index(records)
        report = harvest.build_report(docs, candidates, current, occurrence_sink=occurrences.append,
                                      group_sink=groups.append, **kwargs)
        return report, occurrences, groups

    def test_canonical_spelling_and_reading_order_preserve_original_references(self):
        records = [record(1, '甲【替】', '【文】ká, kah', row=8),
                   record(1, '甲', 'kà', '又唸作', row=9),
                   record(1, '甲', 'kà', '語音差異', row=10),
                   record('', '乙', 'it', '詞彙比較'), record('', '丁', 'ting', '姓')]
        index = harvest.dictionary_index(records)
        self.assertEqual(list(index), ['1'])
        self.assertEqual(index['1']['form'], '甲')
        self.assertEqual(index['1']['canonical_tl'], 'ká')
        self.assertEqual([r['tl'] for r in index['1']['readings']], ['ká', 'kah', 'kà'])
        self.assertEqual(len(index['1']['readings'][-1]['sources']), 2)
        self.assertEqual(index['1']['readings'][0]['sources'][0]['original_reading'], '【文】ká, kah')
        self.assertEqual(list(harvest.trie_for(index)), ['甲'])

    def test_nested_and_crossing_matches_are_preserved_without_selecting_a_segmentation(self):
        records = [record(1, '甲乙', 'a-it'), record(2, '乙丙', 'it-píng'),
                   record(3, '甲', 'a'), record(4, '乙', 'it'), record(5, '丙', 'píng')]
        report, rows, groups = self.run_report(records, [doc('甲乙丙')])
        self.assertEqual([(r['start'], r['end']) for r in rows], [(0, 1), (0, 2), (1, 2), (1, 3), (2, 3)])
        self.assertEqual(groups[0]['overlap_kind'], 'crossing')
        self.assertTrue(groups[0]['dictionary_combo_agreement'])
        self.assertTrue(groups[0]['unknown_word_possible'])
        self.assertEqual({r['queue'] for r in report['candidates']}, {'agreement_only'})
        self.assertEqual(len(report['combo_coverage']), 3)

    def test_compound_and_components_can_agree_without_importing_the_component(self):
        report, _, groups = self.run_report(
            [record(1, '甲乙', 'a-it'), record(2, '甲', 'a'), record(3, '乙', 'it')], [doc('甲乙。')])
        self.assertEqual(groups[0]['overlap_kind'], 'containment')
        by_id = {r['candidate_id']: r for r in report['candidates']}
        self.assertEqual(by_id['1']['queue'], 'batch_proposal')
        self.assertEqual(by_id['2']['queue'], 'agreement_only')
        self.assertIn('no_boundary_aligned_occurrence', by_id['2']['review_reasons'])

    def test_disagreement_blocks_only_the_affected_position(self):
        report, _, groups = self.run_report([record(1, '甲乙', 'a-it'), record(2, '乙', 'jī')], [doc('甲乙')])
        self.assertTrue(groups[0]['positions'][0]['dictionary_agreement'])
        self.assertFalse(groups[0]['positions'][1]['dictionary_agreement'])
        compound = next(c for c in report['candidates'] if c['candidate_id'] == '1')
        self.assertEqual(compound['new_combos'], [('甲', 'a')])
        self.assertEqual(compound['potential_new_combos'], [('乙', 'it'), ('甲', 'a')])
        self.assertIn('dictionary_reading_disagreement', compound['review_reasons'])

    def test_homographs_retain_distinct_dictionary_identities(self):
        report, rows, groups = self.run_report([record(1, '甲', 'a'), record(2, '甲', 'a')], [doc('甲')])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['candidate_ids'], ['1', '2'])
        self.assertEqual(groups[0]['overlap_kind'], 'same_span_identities')
        self.assertEqual(len(report['candidates']), 2)
        self.assertTrue(all('same_form_multiple_identities' in c['review_reasons'] for c in report['candidates']))
        self.assertFalse(any(c['queue'] == 'batch_proposal' for c in report['candidates']))

    def test_contraction_alternative_is_retained_and_blocks_positional_evidence(self):
        report, _, groups = self.run_report([record(1, '予人', 'hōo-lâng'),
                                            record(1, '予人', 'hông', '合音唸作')], [doc('予人')])
        self.assertEqual(report['candidates'][0]['readings'][1]['alignment_issue'], 'character_syllable_count_mismatch')
        self.assertTrue(all(p['unalignable_alternative'] for p in groups[0]['positions']))
        self.assertEqual(report['combo_coverage'], [])
        self.assertEqual(report['candidates'][0]['new_combo_count'], 0)

    def test_unknown_word_alternatives_remain_even_with_sole_dictionary_match(self):
        report, _, groups = self.run_report([record(1, '甲乙', 'a-it')], [doc('甲乙丁')])
        self.assertTrue(groups[0]['unknown_word_possible'])
        self.assertTrue(groups[0]['dictionary_combo_agreement'])
        self.assertEqual(report['candidates'][0]['queue'], 'agreement_only')
        self.assertEqual(report['candidates'][0]['boundary_aligned_occurrences'], 0)

    def test_literal_unicode_offsets_and_roman_boundaries(self):
        source = 'M\u0304甲乙，𠞭心kap甲 乙'
        report, rows, _ = self.run_report([record(1, '甲乙', 'a-it'), record(2, '𠞭心', 'liô-sim')], [doc(source)])
        self.assertEqual([r['form'] for r in rows], ['甲乙', '𠞭心'])
        self.assertEqual(rows[0]['start'], 2)
        for row in rows:
            self.assertEqual(source[row['start']:row['end']], row['form'])
            self.assertEqual(source[row['context_start']:row['context_end']], row['snippet'])
        self.assertEqual(report['summary']['counts']['matched_spans'], 2)

    def test_variant_selector_and_exclusions_do_not_create_false_boundaries(self):
        records = [record(1, '甲', 'a'), record(2, '甲乙', 'a-it')]
        _, rows, _ = self.run_report(records, [doc('甲\ufe00。甲乙丙。甲')], exclusions=['乙丙'])
        self.assertEqual([(r['start'], r['end']) for r in rows], [(3, 4), (7, 8)])
        self.assertFalse(rows[0]['boundary_aligned'])
        self.assertTrue(rows[1]['boundary_aligned'])

    def test_duplicate_bodies_do_not_inflate_distinct_text_support(self):
        report, rows, _ = self.run_report([record(1, '甲乙', 'a-it')],
                                          [doc('甲乙', 'a'), doc('甲乙', 'b'), doc('甲乙甲乙', 'c')])
        candidate = report['candidates'][0]
        self.assertEqual(candidate['occurrences'], 4)
        self.assertEqual(candidate['article_count'], 3)
        self.assertEqual(candidate['distinct_text_count'], 2)
        self.assertEqual(candidate['distinct_text_occurrences'], 3)
        self.assertEqual(len(candidate['sample_contexts']), 2)
        self.assertEqual(report['summary']['counts']['duplicate_text_documents'], 1)
        self.assertEqual(report['combo_coverage'][0]['distinct_text_occurrences'], 3)

    def test_inventory_excludes_generated_disputed_and_contracted_entries(self):
        current = [entry(1, '引tshuā', 'ín-tshuā', ['引𤆬']),
                   entry(2, '引tshuā', 'ín-tshuā', ['引𤆬'], rule_generated=True),
                   entry(3, '引𤆬', 'ín-tshuā', ['引𤆬'], review_status='disputed'),
                   entry(4, 'hông', 'hông', ['予人'])]
        inventory, skipped = harvest.combo_inventory(current)
        self.assertEqual(inventory[('𤆬', 'tshuā')]['recommendations'],
                         [{'kind': 'romanized', 'output': 'tshuā', 'entry_ids': [1]}])
        self.assertEqual(inventory[('引', 'ín')]['recommendations'][0]['entry_ids'], [1])
        self.assertEqual({s['reason'] for s in skipped},
                         {'rule_generated', 'disputed', 'character_syllable_count_mismatch'})

    def test_conflicts_and_existing_word_candidates_cannot_enter_batch_proposals(self):
        current = [entry(1, 'a', 'a', ['甲']), entry(2, '甲', 'a', ['甲'])]
        report, _, _ = self.run_report([record(1, '甲乙', 'a-it')], [doc('甲乙')], current)
        self.assertEqual(report['combo_inventory'][0]['status'], 'conflicting')
        self.assertEqual(report['candidates'][0]['queue'], 'focused_review')
        self.assertIn('recommendation_conflict', report['candidates'][0]['review_reasons'])
        report, _, _ = self.run_report([record(1, '甲', 'a')], [doc('甲')], current)
        self.assertEqual([r['entry_id'] for r in report['candidates'][0]['existing_entry_candidates']], [1, 2])
        self.assertIn('existing_entry_candidates', report['candidates'][0]['review_reasons'])

    def test_inventory_counts_each_word_once_and_only_its_canonical_reading(self):
        inventory, _ = harvest.combo_inventory([
            entry(1, '甲甲', 'a-a', ['甲甲', '甲甲'], alternate_readings=['á-á'])])
        self.assertEqual(set(inventory), {('甲', 'a')})
        self.assertEqual(inventory[('甲', 'a')]['recommendations'][0]['entry_ids'], [1])

    def test_neutral_tones_and_tone_marks_stay_distinct(self):
        self.assertEqual(harvest.syllables('ā--a'), ['ā', '--a'])
        self.assertEqual(harvest.syllables('--ê'), ['--ê'])
        self.assertEqual(harvest.preferred_units('甲--a', 'ā--a'), [('hanji', '甲'), ('romanized', '--a')])
        self.assertIsNone(harvest.preferred_units('甲a', 'ā--a'))
        self.assertIsNone(harvest.syllables('a---a'))
        self.assertIsNone(harvest.syllables('a2'))
        _, _, groups = self.run_report([record(1, '甲', 'a'), record(2, '甲', 'á')], [doc('甲')])
        self.assertFalse(groups[0]['dictionary_combo_agreement'])

    def test_crossing_detection_does_not_confuse_equal_starts_or_touching_spans(self):
        records = [record(1, '甲乙丙', 'a-it-píng'), record(2, '甲乙', 'a-it'), record(3, '丙', 'píng')]
        _, _, groups = self.run_report(records, [doc('甲乙丙')])
        self.assertEqual(groups[0]['overlap_kind'], 'containment')
        _, _, groups = self.run_report(records[1:], [doc('甲乙丙')])
        self.assertEqual(len(groups), 2)

    def test_input_filters_validate_json_and_document_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'corpus.jsonl'
            docs = [doc('甲', 'a'), doc('乙', 'b'), doc('丙', 'c')]
            for item in docs:
                item['metadata']['tags'] = ['issue:390']
            docs[1]['metadata']['title'] = '台文通訊BONG報 390 期'
            docs[2]['metadata']['tags'] = ['issue:3900']
            path.write_text('\n'.join(json.dumps(d) for d in docs) + '\n', encoding='utf-8')
            self.assertEqual([d['id'] for d in harvest.corpus_documents(path, 'jsonl', ['issue:390'], 390)], ['a'])
            path.write_text(json.dumps(docs[0]) + '\n' + json.dumps(docs[0]) + '\n', encoding='utf-8')
            with self.assertRaisesRegex(lex.Error, ':2:.*duplicate document id'):
                list(harvest.corpus_documents(path, 'jsonl', [], None))
            path.write_text('{invalid}\n', encoding='utf-8')
            with self.assertRaisesRegex(lex.Error, ':1:'):
                list(harvest.corpus_documents(path, 'jsonl', [], None))

    def test_cli_reports_are_repeatable_and_corpus_entries_and_snapshot_are_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            root, out = base / 'lexicon', base / 'report'
            (root / 'entries').mkdir(parents=True)
            (root / 'references').mkdir()
            ods = base / 'fixture.ods'
            make_ods(ods)
            sha = hashlib.sha256(ods.read_bytes()).hexdigest()
            cached = root / '.cache/dictionaries/moe' / sha / 'kautian.ods'
            cached.parent.mkdir(parents=True)
            cached.write_bytes(ods.read_bytes())
            (root / 'references/moe.toml').write_text(
                f'id = "moe-fixture"\nsha256 = "{sha}"\nformat = "moe-ods"\n', encoding='utf-8')
            corpus = base / 'corpus.jsonl'
            corpus.write_text(json.dumps(doc('欲。重。')) + '\n', encoding='utf-8')
            before = {p: p.read_bytes() for p in [corpus, cached, root / 'references/moe.toml']}
            command = [sys.executable, str(ROOT / 'tools/harvest_hanji.py'), '--corpus', str(corpus),
                       '--out', str(out), '--lexicon', str(root)]
            result = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            files = {p.name: p.read_bytes() for p in out.iterdir()}
            self.assertEqual(len(files), 7)
            summary = json.loads(files['summary.json'])
            self.assertEqual(summary['corpus_sha256'], hashlib.sha256(corpus.read_bytes()).hexdigest())
            self.assertEqual(summary['counts']['candidates'], 2)
            result = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(files, {p.name: p.read_bytes() for p in out.iterdir()})
            self.assertTrue(all(p.read_bytes() == content for p, content in before.items()))
            self.assertEqual(list((root / 'entries').iterdir()), [])
            corpus.write_text(corpus.read_text(encoding='utf-8') + 'bad-json\n', encoding='utf-8')
            result = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(files, {p.name: p.read_bytes() for p in out.iterdir()})

    def test_cli_rejects_output_in_tracked_tree_and_input_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            corpus = base / 'occurrences.jsonl'
            corpus.write_text('{}\n', encoding='utf-8')
            for out in [ROOT / 'entries', base]:
                with mock.patch('sys.stderr'):
                    result = harvest.main(['--corpus', str(corpus), '--out', str(out)])
                self.assertEqual(result, 1)
            self.assertEqual(corpus.read_text(encoding='utf-8'), '{}\n')

    def test_plain_text_input_has_literal_offsets(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'prose.txt'
            path.write_text('甲\r\n乙', encoding='utf-8', newline='')
            documents = list(harvest.corpus_documents(path, 'text', [], None))
            self.assertEqual(documents[0]['text'], '甲\r\n乙')


if __name__ == '__main__':
    unittest.main()
