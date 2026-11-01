import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from review_context import context_id, reading_contexts
from render_review import render


class ReviewContextTests(unittest.TestCase):
    def test_context_spans_punctuation_and_preserves_unicode_and_source_evidence(self):
        text = '𠊎' * 105 + '前一句。這個hit陣，後一句有詳細說明。' + 'a\u0301' * 105
        start = text.index('hit')
        row = {'document_id': 'doc', 'anchor_start': start, 'anchor_end': start + 4,
               'snippet': 'hit陣', 'context_start': start, 'context_end': start + 4,
               'source_triggers': [{'anchor_start': start, 'anchor_end': start + 3}]}
        payload = {'groups': [{'occurrences': [row]}]}
        original = json.dumps(payload)
        contexts = reading_contexts(payload, {'doc': text})
        context = contexts[context_id('doc', start, start + 3)]
        self.assertIn('前一句。這個hit陣，後一句有詳細說明。', context['snippet'])
        self.assertEqual(context['snippet'], text[context['context_start']:context['context_end']])
        self.assertGreater(len(context['snippet']), 200)
        self.assertFalse(context['snippet'].startswith('\u0301'))
        self.assertEqual(json.dumps(payload), original)

    def test_refresh_changes_only_html_and_fails_before_writing_on_stale_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            pilot = Path(folder)
            text = '前一句。hit陣，後一句。'
            corpus = pilot / 'corpus.jsonl'
            corpus.write_text(json.dumps({'id': 'doc', 'text': text}) + '\n')
            start = text.index('hit')
            groups = [{'key': 'hit陣', 'occurrences': [{'document_id': 'doc', 'anchor_start': start,
                       'anchor_end': start + 4}]}]
            content = json.dumps(groups).encode()
            (pilot / 'groups.json').write_bytes(content)
            summary = {'corpus_path': str(corpus), 'corpus_sha256': hashlib.sha256(corpus.read_bytes()).hexdigest(),
                       'review_groups_sha256': hashlib.sha256(content).hexdigest()}
            (pilot / 'summary.json').write_text(json.dumps(summary))
            before = {p.name: p.read_bytes() for p in pilot.iterdir()}
            render(pilot)
            page = (pilot / 'review.html').read_text()
            self.assertIn(text, page)
            for name, data in before.items():
                self.assertEqual((pilot / name).read_bytes(), data)
            corpus.write_text('changed')
            with self.assertRaisesRegex(ValueError, 'Corpus changed'):
                render(pilot)
            self.assertEqual((pilot / 'review.html').read_text(), page)
            (pilot / 'groups.json').write_text('[]')
            with self.assertRaisesRegex(ValueError, 'Harvest groups changed'):
                render(pilot)
            self.assertEqual((pilot / 'review.html').read_text(), page)

    def test_refresh_uses_current_compound_coverage_and_leaves_sealed_files_unchanged(self):
        from unittest import mock
        with tempfile.TemporaryDirectory() as folder:
            pilot = Path(folder)
            corpus = pilot / 'corpus.jsonl'
            corpus.write_text(json.dumps({'id': 'doc', 'text': '--tńg-去'}, ensure_ascii=False) + '\n')
            groups = [{'key': '--tńg', 'normalized_tl': '--tńg', 'occurrences': [{
                'document_id': 'doc', 'anchor': '--tńg', 'anchor_start': 0, 'anchor_end': 5,
                'clause_start': 0, 'clause_end': 7}]}]
            content = json.dumps(groups).encode()
            (pilot / 'groups.json').write_bytes(content)
            summary = {'corpus_path': str(corpus), 'corpus_sha256': hashlib.sha256(corpus.read_bytes()).hexdigest(),
                       'review_groups_sha256': hashlib.sha256(content).hexdigest(), 'lexicon_root': str(pilot)}
            (pilot / 'summary.json').write_text(json.dumps(summary))
            before = {p.name: p.read_bytes() for p in pilot.iterdir()}
            records = [{'id': 4741, 'preferred_form': '--tńg-去', 'canonical_tl': '--tńg-khì',
                        'multi_syllable_written_forms': ['--tńg-去']}]
            with mock.patch('render_review.preferred_index', return_value=(records, {})):
                render(pilot)
            page = (pilot / 'review.html').read_text()
            payload = json.loads(page.split('const data=', 1)[1].split(';\n', 1)[0])
            self.assertEqual(payload['groups'][0]['occurrences'][0]['tracked_coverage'][0]['entries'][0]['id'], 4741)
            for name, data in before.items():
                self.assertEqual((pilot / name).read_bytes(), data)
