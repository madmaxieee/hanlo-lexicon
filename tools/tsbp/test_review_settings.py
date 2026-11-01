import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from review_settings import save_settings, read_settings
from review_context import context_id
from review_filters import filter_occurrences


class ReviewSettingsTests(unittest.TestCase):
    def test_settings_preserve_absent_segments_and_are_scoped_to_exact_corpus(self):
        with tempfile.TemporaryDirectory() as folder:
            pilot = Path(folder)
            corpus = pilot / 'corpus.jsonl'
            corpus.write_text(json.dumps({'id': 'doc', 'text': 'roman。roman',
                                         'metadata': {'tags': ['issue:385']}}))
            summary = {'issue': 385, 'corpus_path': str(corpus),
                       'corpus_sha256': hashlib.sha256(corpus.read_bytes()).hexdigest()}
            bundle = {**summary, 'ignored_segments': [context_id('doc', 0, 5)], 'ignored_forms': ['other']}
            save_settings(pilot, bundle, summary)
            settings = read_settings(pilot, summary)
            self.assertEqual(settings['ignored_segments'], bundle['ignored_segments'])
            self.assertEqual(filter_occurrences([], settings['ignored_segments'], allow_absent=True), [])
            with self.assertRaisesRegex(ValueError, 'different issue'):
                read_settings(pilot, {**summary, 'issue': 386})
            bundle['ignored_segments'] = [context_id('doc', 1, 5)]
            with self.assertRaisesRegex(ValueError, 'Roman-text position'):
                save_settings(pilot, bundle, summary)
            self.assertEqual(read_settings(pilot, summary)['ignored_segments'], settings['ignored_segments'])

    def test_harvest_reruns_embed_persisted_segments_without_rewriting_settings(self):
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as folder:
            pilot = Path(folder)
            corpus = pilot / 'corpus.jsonl'
            doc = {'id': 'doc', 'text': 'roman。roman', 'metadata': {'tags': ['issue:385'],
                   'title': 'Test', 'original_url': 'https://example.com'}}
            corpus.write_text(json.dumps(doc))
            summary = {'issue': 385, 'corpus_path': str(corpus),
                       'corpus_sha256': hashlib.sha256(corpus.read_bytes()).hexdigest()}
            bundle = {**summary, 'ignored_segments': [context_id('doc', 0, 5)], 'ignored_forms': []}
            save_settings(pilot, bundle, summary)
            original = (pilot / 'review-settings.json').read_bytes()
            command = [sys.executable, str(Path(__file__).with_name('harvest.py')),
                       '--corpus', str(corpus), '--issue', '385', '--out', str(pilot)]
            for _ in range(2):
                subprocess.run(command, check=True, capture_output=True)
                result = json.loads((pilot / 'summary.json').read_text())
                self.assertEqual(result['ignored_segments'], bundle['ignored_segments'])
                self.assertEqual((pilot / 'review-settings.json').read_bytes(), original)
            legacy = {**summary, 'ignored_forms': []}
            save_settings(pilot, legacy, summary)
            self.assertEqual(read_settings(pilot, summary)['ignored_segments'], bundle['ignored_segments'])
