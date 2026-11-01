from copy import deepcopy
import unittest

from harvest import occurrences
from moe_context import build_lookups, regroup
from review_context import context_id
from review_filters import annotate_coverage, filter_occurrences
from import_review import article_source


def groups_for(text):
    doc = {'id': 'article', 'text': text,
           'metadata': {'title': 'Test', 'original_url': 'https://example.com'}}
    grouped = {}
    for row in occurrences(doc, 6):
        grouped.setdefault(row['key'], []).append(row)
    groups = [{'key': key, 'normalized_tl': key, 'occurrences': rows} for key, rows in grouped.items()]
    return regroup(groups, {'article': text}, build_lookups(groups, []))[0]


class ReviewFilterTests(unittest.TestCase):
    def test_new_neutral_compound_covers_only_its_own_occurrences_without_discovery(self):
        text = '割--tńg-去。--tńg。--tńg-來。--tńg -去。--tng-去。'
        groups = groups_for(text)
        original = deepcopy(groups)
        records = [{'id': 4741, 'preferred_form': '--tńg-去', 'canonical_tl': '--tńg-khì',
                    'multi_syllable_written_forms': ['--tńg-去']}]
        annotated = annotate_coverage(groups, records, {'article': text})
        neutral = next(g for g in annotated if g['key'] == '--tńg')
        self.assertEqual([bool(row['tracked_coverage']) for row in neutral['occurrences']], [True, False, False, False])
        self.assertEqual(neutral['occurrences'][0]['tracked_coverage'][0]['entries'][0]['id'], 4741)
        self.assertEqual(groups, original)
        eligible = next(g for g in filter_occurrences(annotated, []) if g['key'] == '--tńg')
        self.assertEqual(len(eligible['occurrences']), 3)
        self.assertNotIn('--tńg-去', article_source(eligible)['locator'])

    def test_segment_ignore_excludes_only_one_passage_and_import_uses_the_other(self):
        groups = groups_for('前hip。後hip。')
        group = groups[0]
        first, second = group['occurrences']
        ignored = [context_id('article', first['anchor_start'], first['anchor_end'])]
        filtered, = filter_occurrences(groups, ignored)
        self.assertEqual(filtered['occurrences'], [second])
        self.assertIn(f"{second['anchor_start']}:{second['anchor_end']}", article_source(filtered)['locator'])
        self.assertEqual(len(group['occurrences']), 2)
        all_ignored, = filter_occurrences(groups, ignored + [context_id('article', second['anchor_start'], second['anchor_end'])])
        with self.assertRaisesRegex(ValueError, 'All occurrences are ignored'):
            article_source(all_ignored)

    def test_segment_ignore_validates_membership_and_affects_all_triggered_candidates(self):
        groups = groups_for('hip相。')
        first = groups[0]['occurrences'][0]
        other = deepcopy(groups[0])
        other['key'] = 'hip相'
        other['occurrences'][0].update(anchor='hip相', anchor_end=first['anchor_end'] + 1)
        identity = context_id('article', first['anchor_start'], first['anchor_end'])
        result = filter_occurrences([groups[0], other], [identity])
        self.assertTrue(all(not g['occurrences'] for g in result))
        with self.assertRaisesRegex(ValueError, 'not in the sealed harvest'):
            filter_occurrences(groups, [context_id('other', 0, 3)])
        with self.assertRaises(ValueError):
            filter_occurrences(groups, 'all')
