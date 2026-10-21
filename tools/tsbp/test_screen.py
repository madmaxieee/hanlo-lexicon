import copy
import json
from pathlib import Path
import tempfile
import unittest

from import_review import article_source, load_bundle
from screen import apply_screening, collect, load_screening, occurrence_id, prepare, read, sha, write


def group(key, documents):
    return {'key': key, 'exclusion_reason': None, 'article_count': len(documents),
            'occurrences': [{'document_id': doc, 'anchor_start': 0, 'anchor_end': len(key),
                             'anchor': key, 'url': f'https://example.com/{doc}', 'line': 1}
                            for doc in documents]}


def report(groups):
    return {'schema_version': 1, 'issue': 388, 'corpus_sha256': 'corpus', 'groups_sha256': 'groups',
            'decisions': [{'occurrence_id': occurrence_id(g, r), 'decision': 'hold',
                           'reason': 'Context needs a human decision.', 'model': 'gpt-6-luna'}
                          for g in groups for r in g['occurrences']]}


class ScreeningTests(unittest.TestCase):
    def test_occurrence_rejection_preserves_taiwanese_homograph_and_import_evidence(self):
        groups = [group('the', ['english', 'taiwanese']), group('a', ['english']), group('foo', ['uncertain'])]
        original = copy.deepcopy(groups)
        review = report(groups)
        review['decisions'][0].update(decision='reject', reason='English article in The Mission.')
        review['decisions'][1].update(decision='keep', reason='Taiwanese usage in this occurrence.')
        review['decisions'][2].update(decision='reject', reason='English indefinite article.')
        screened = apply_screening(groups, review, 388, 'corpus', 'groups')
        self.assertEqual(groups, original)
        self.assertEqual([r['document_id'] for r in screened[0]['occurrences']], ['taiwanese'])
        self.assertEqual(screened[0]['article_count'], 1)
        self.assertEqual(screened[0]['machine_rejected_occurrences'][0]['document_id'], 'english')
        self.assertIsNone(screened[2]['exclusion_reason'])
        self.assertEqual(screened[2]['occurrences'][0]['machine_screening']['decision'], 'hold')
        self.assertEqual(article_source(screened[0])['url'], 'https://example.com/taiwanese')
        self.assertEqual(screened[1]['exclusion_reason'], 'machine_rejected')
        with self.assertRaisesRegex(ValueError, 'only machine-rejected'):
            article_source(screened[1])

    def test_incomplete_stale_duplicate_or_unattributed_screening_fails_closed(self):
        groups = [group('the', ['english'])]
        valid = report(groups)
        variants = []
        for field in ['issue', 'corpus_sha256', 'groups_sha256']:
            row = copy.deepcopy(valid)
            row[field] = 'stale'
            variants.append(row)
        for field, value in [('reason', ''), ('model', ''), ('decision', 'approve'), ('occurrence_id', 'unknown')]:
            row = copy.deepcopy(valid)
            row['decisions'][0][field] = value
            variants.append(row)
        variants.extend([dict(valid, decisions=[]), dict(valid, decisions=valid['decisions'] * 2)])
        for invalid in variants:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                apply_screening(groups, invalid, 388, 'corpus', 'groups')

    def test_packets_and_exports_bind_decisions_to_the_same_source_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            pilot = Path(folder)
            corpus = pilot / 'corpus.jsonl'
            docs = [{'id': identity, 'text': text,
                     'metadata': {'title': identity, 'original_url': f'https://example.com/{identity}'}}
                    for identity, text in [('english', 'the Mission'), ('taiwanese', 'the來')]]
            corpus.write_text(''.join(json.dumps(d) + '\n' for d in docs))
            groups = [group('the', ['english', 'taiwanese'])]
            write(pilot / 'groups.json', groups)
            summary = {'issue': 388, 'corpus_path': str(corpus), 'corpus_sha256': sha(corpus),
                       'review_groups_sha256': sha(pilot / 'groups.json'),
                       'article_inventory': [{'id': d['id']} for d in docs], 'moe': {'snapshot': 'moe'}}
            write(pilot / 'summary.json', summary)
            run = pilot / 'screening'
            self.assertEqual(prepare(pilot, run, 1)['occurrences'], 2)
            manifest = read(run / 'manifest.json')
            for index, packet in enumerate(manifest['packets']):
                path = run / 'reviews' / packet['file'].replace('.jsonl', '.review.jsonl')
                rows = [{'packet_file': packet['file'], 'packet_sha256': packet['sha256'], 'model': 'gpt-6-luna'},
                        {'occurrence_id': packet['occurrence_ids'][0], 'decision': 'reject' if index == 0 else 'keep',
                         'reason': 'English title.' if index == 0 else 'Taiwanese clause.'}]
                path.write_text(''.join(json.dumps(r) + '\n' for r in rows))
            output = pilot / 'machine-screen.json'
            self.assertEqual(collect(run, output)['decisions'], {'reject': 1, 'keep': 1})
            summary['machine_screening'] = {'sha256': sha(output)}
            self.assertEqual(load_screening(pilot, summary, groups)[0]['occurrences'][0]['document_id'], 'taiwanese')
            bundle = {'schema_version': 1, 'issue': 388, 'corpus_sha256': sha(corpus),
                      'groups_sha256': summary['review_groups_sha256'], 'moe_snapshot': 'moe'}
            write(pilot / 'review.json', bundle)
            with self.assertRaisesRegex(ValueError, 'Machine screening changed'):
                load_bundle(pilot / 'review.json', pilot / 'groups.json', summary)
            bundle['screening_sha256'] = sha(output)
            write(pilot / 'review.json', bundle)
            load_bundle(pilot / 'review.json', pilot / 'groups.json', summary)
            output.write_text(output.read_text() + '\n')
            with self.assertRaisesRegex(ValueError, 'artifact changed'):
                load_screening(pilot, summary, groups)
            packet = run / 'packets' / manifest['packets'][0]['file']
            packet.write_text(packet.read_text() + '\n')
            with self.assertRaisesRegex(ValueError, 'packet changed'):
                collect(run, output)


if __name__ == '__main__':
    unittest.main()
