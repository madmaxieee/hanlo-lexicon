"""Review packet provenance, completeness and evidence contracts."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from test_lexicon import lex, make_ods
from test_harvest_hanji import harvest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('review_hanji', ROOT / 'tools/review_hanji.py')
review = importlib.util.module_from_spec(SPEC)
with mock.patch.dict(sys.modules, {'lexicon': lex, 'harvest_hanji': harvest}):
    SPEC.loader.exec_module(review)


class ReviewContractTests(unittest.TestCase):
    def setUp(self):
        self.candidate = {'candidate_id': '7', 'canonical_tl': 'beh', 'alignment_issues': [],
                          'existing_entry_candidates': [], 'review_reasons': [],
                          'contexts': [{'occurrence_id': 'a:1:2'}]}
        self.decision = {'candidate_id': '7', 'decision': 'recommend_import',
                         'reason': 'Used as an independent word in the supplied Taiwanese sentence.',
                         'reviewed_occurrence_ids': ['a:1:2'], 'supporting_occurrence_ids': ['a:1:2']}

    def test_recommendation_requires_reviewed_known_support(self):
        review.validate_decision(self.decision, self.candidate)
        for fields in ({'supporting_occurrence_ids': []},
                       {'reviewed_occurrence_ids': []},
                       {'supporting_occurrence_ids': ['unknown']},
                       {'reviewed_occurrence_ids': ['a:1:2', 'a:1:2']},
                       {'reason': ''}, {'candidate_id': '8'}, {'decision': 'approved'}):
            with self.subTest(fields=fields), self.assertRaises(lex.Error):
                review.validate_decision(self.decision | fields, self.candidate)

    def test_conflicts_and_unalignable_readings_cannot_be_recommended(self):
        for fields in ({'existing_entry_candidates': [{'entry_id': 1}]},
                       {'review_reasons': ['recommendation_conflict']},
                       {'alignment_issues': ['character_syllable_count_mismatch']},
                       {'canonical_tl': None}):
            with self.subTest(fields=fields), self.assertRaises(lex.Error):
                review.validate_decision(self.decision, self.candidate | fields)

    def test_hold_combo_only_and_reject_do_not_designate_import_support(self):
        for decision in ('combo_only', 'hold', 'reject'):
            row = self.decision | {'decision': decision, 'supporting_occurrence_ids': []}
            review.validate_decision(row, self.candidate)
            with self.assertRaises(lex.Error):
                review.validate_decision(row | {'supporting_occurrence_ids': ['a:1:2']}, self.candidate)

    def test_line_language_label_survives_long_context(self):
        text = 'a' * 300 + '僕' + 'b' * 300 + '（日）'
        row = {'start': 300, 'end': 301, 'form': '僕', 'boundary_aligned': True,
               'overlap_kind': 'isolated', 'dictionary_combo_agreement': True}
        context = review.context(row, {'id': 'a', 'text': text, 'metadata': {}})
        self.assertNotIn('（日）', context['text'])
        self.assertTrue(context['line_tail'].endswith('（日）'))
        self.assertEqual(text[context['context_start']:context['context_end']], context['text'])
        with self.assertRaises(lex.Error):
            review.context(row | {'form': '甲'}, {'id': 'a', 'text': text, 'metadata': {}})


class ReviewWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root, self.folder, self.run = self.base / 'root', self.base / 'harvest', self.base / 'review'
        (self.root / 'entries').mkdir(parents=True)
        (self.root / 'references').mkdir()
        ods = self.base / 'fixture.ods'
        make_ods(ods)
        checksum = review.sha(ods)
        cached = self.root / '.cache/dictionaries/moe' / checksum / 'kautian.ods'
        cached.parent.mkdir(parents=True)
        cached.write_bytes(ods.read_bytes())
        (self.root / 'references/moe.toml').write_text(
            f'id = "fixture"\nsha256 = "{checksum}"\nformat = "moe-ods"\n', encoding='utf-8')
        self.corpus = self.base / 'corpus.jsonl'
        self.corpus.write_text(json.dumps({'id': 'a', 'text': '欲。重。', 'metadata': {}}) + '\n', encoding='utf-8')
        result = subprocess.run([sys.executable, str(ROOT / 'tools/harvest_hanji.py'),
            '--corpus', str(self.corpus), '--out', str(self.folder), '--lexicon', str(self.root)],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def prepare(self):
        return review.prepare(self.folder, self.run, self.root, packet_size=1)

    def write_reviews(self):
        for packet in review.read_json(self.run / 'manifest.json')['packets']:
            candidate = review.read_lines(self.run / 'packets' / packet['file'])[0]
            occurrence = candidate['contexts'][0]['occurrence_id']
            rows = [{'packet_file': packet['file'], 'packet_sha256': packet['sha256']},
                    {'candidate_id': candidate['candidate_id'], 'decision': 'hold',
                     'reason': 'Fixture awaiting contextual judgment.',
                     'reviewed_occurrence_ids': [occurrence], 'supporting_occurrence_ids': []}]
            path = self.run / 'reviews' / packet['file'].replace('.jsonl', '.review.jsonl')
            path.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')

    def test_prepare_and_collect_are_read_only_and_complete(self):
        before = self.corpus.read_bytes()
        result = self.prepare()
        self.assertEqual(result['candidates'], 1)
        self.assertEqual(result['packets'], 1)
        self.write_reviews()
        result = review.collect(self.run, self.root)
        self.assertEqual(result['decisions'], {'hold': 1})
        self.assertTrue((self.run / 'review.md').is_file())
        self.assertEqual(self.corpus.read_bytes(), before)
        self.assertEqual(list((self.root / 'entries').iterdir()), [])

    def test_collect_rejects_missing_duplicate_and_changed_packet(self):
        self.prepare()
        self.write_reviews()
        path = self.run / 'reviews/packet-001.review.jsonl'
        original = path.read_text(encoding='utf-8')
        header, decision = review.read_lines(path)
        for rows in ([header], [header, decision, decision]):
            path.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
            with self.assertRaisesRegex(lex.Error, 'Incomplete|duplicate'):
                review.collect(self.run, self.root)
        path.write_text(original, encoding='utf-8')
        with (self.run / 'packets/packet-001.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(' \n')
        with self.assertRaisesRegex(lex.Error, 'packet changed'):
            review.collect(self.run, self.root)

    def test_stale_corpus_and_harvest_are_rejected(self):
        self.prepare()
        self.write_reviews()
        self.corpus.write_text('{}\n', encoding='utf-8')
        with self.assertRaisesRegex(lex.Error, 'Corpus changed'):
            review.collect(self.run, self.root)
        with self.assertRaisesRegex(lex.Error, 'Corpus changed'):
            self.prepare()


if __name__ == '__main__':
    unittest.main()
