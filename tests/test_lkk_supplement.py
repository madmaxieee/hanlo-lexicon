"""Conservative LKK coverage must prove complete spellings, not majority votes."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from lkk_supplement import LKKCoverage


def lkk(*items):
    return {'lkk': ({}, [[''] * 9] + [['', form, reading, '', '', hanji, '', '', '']
                                  for form, reading, hanji in items])}


def entry(form='beh食', reading='beh-tsia̍h', alternates=()):
    return {'preferred_form': form, 'canonical_tl': reading, 'alternate_readings': list(alternates), 'sources': []}


class LKKSupplementTests(unittest.TestCase):
    def test_complete_reconstruction_records_original_row_proofs(self):
        coverage = LKKCoverage(lkk(('beh', 'beh', '欲'), ('食', 'tsia̍h', '食')), [])
        proof = coverage.reconstructed(entry(), ['欲食'])
        self.assertEqual(proof[0]['form'], 'beh食')
        self.assertEqual(proof[0]['positions'][0]['sources'][0]['lkk_source']['row'], 2)
        self.assertIsNone(coverage.reconstructed(entry(), ['欲飯']))

    def test_conflicts_are_retained_without_majority_resolution(self):
        coverage = LKKCoverage(lkk(('kah', 'kah', '甲'), ('甲', 'kah', '甲'), ('kah', 'kah', '甲')), [])
        self.assertIsNone(coverage.reconstructed(entry('kah', 'kah'), ['甲']))

    def test_extra_reading_or_nonstandard_separator_prevents_exclusion(self):
        coverage = LKKCoverage(lkk(('beh', 'beh', '欲'), ('食', 'tsia̍h', '食')), [])
        self.assertIsNone(coverage.reconstructed(entry(alternates=['bueh-tsia̍h']), ['欲食']))
        self.assertIsNone(coverage.reconstructed(entry('beh-食'), ['欲食']))

    def test_original_items_match_snapshot_pairs_or_explicit_source(self):
        original = lkk(('beh', 'beh', '欲'))
        coverage = LKKCoverage(original, [])
        self.assertTrue(coverage.original(entry('beh', 'beh'), original))
        changed = entry('new', 'new')
        changed['sources'] = [{'snapshot': 'lkk', 'row': 2}]
        self.assertTrue(coverage.original(changed, original))

    def test_same_reading_without_whole_word_spelling_is_not_hanji_evidence(self):
        records = [{'headword': '同音詞', 'reading': 'beh', 'source': {'snapshot': 'moe', 'row': 2}}]
        coverage = LKKCoverage(lkk(('beh', 'beh', '')), records)
        self.assertEqual(dict(coverage.mappings), {})
