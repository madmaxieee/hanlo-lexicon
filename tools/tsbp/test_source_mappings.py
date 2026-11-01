import unittest
from source_mappings import apply_mappings, verified_mappings


class SourceMappingTests(unittest.TestCase):
    def test_whole_word_only_and_target_changes_reopen_review(self):
        row = {'source_form': 'hit陣', 'entry_id': 493,
               'preferred_form': 'hit-tsūn', 'canonical_tl': 'hit-tsūn'}
        records = [{'id': 493, 'preferred_form': 'hit-tsūn', 'canonical_tl': 'hit-tsūn'}]
        active, stale = verified_mappings([row], records)
        self.assertEqual(stale, [])
        groups = [{'key': form} for form in ['hit陣', 'HIT陣', 'hit', '陣', 'hit陣仔']]
        apply_mappings(groups, active)
        self.assertEqual([bool(g['source_mapping']) for g in groups], [True, True, False, False, False])
        records[0]['preferred_form'] = 'hit陣'
        self.assertEqual(verified_mappings([row], records), ([], [row]))
        self.assertEqual(verified_mappings([row], []), ([], [row]))

    def test_duplicate_or_incomplete_decisions_fail(self):
        row = {'source_form': 'hit陣', 'entry_id': 493,
               'preferred_form': 'hit-tsūn', 'canonical_tl': 'hit-tsūn'}
        with self.assertRaises(ValueError):
            verified_mappings([row, row], [])
        with self.assertRaises(ValueError):
            verified_mappings([{'source_form': 'hit陣'}], [])

    def test_export_persistence_removal_and_stale_review(self):
        import hashlib
        import json
        from pathlib import Path
        import tempfile
        from unittest.mock import patch
        from source_mappings import main
        with tempfile.TemporaryDirectory() as folder:
            pilot = Path(folder)
            groups = [{'key': 'hit陣', 'occurrences': [{'document_id': 'test', 'url': 'https://example.com',
                      'line': 1, 'anchor_start': 0, 'anchor_end': 4, 'anchor': 'hit陣'}]}]
            content = json.dumps(groups).encode()
            (pilot / 'groups.json').write_bytes(content)
            (pilot / 'summary.json').write_text(json.dumps({'issue': 385, 'corpus_sha256': 'corpus'}))
            target = {'id': 493, 'preferred_form': 'hit-tsūn', 'canonical_tl': 'hit-tsūn'}
            mapping = {'source_form': 'hit陣', 'entry_id': 493, **{k: target[k] for k in ('preferred_form', 'canonical_tl')}}
            bundle = {'schema_version': 1, 'issue': 385, 'corpus_sha256': 'corpus',
                      'groups_sha256': hashlib.sha256(content).hexdigest(), 'source_mappings': [mapping]}
            review = pilot / 'review.json'
            path = pilot / 'shared.json'
            command = ['source_mappings.py', '--root', str(pilot), '--pilot', str(pilot),
                       '--review', str(review), '--mappings', str(path)]
            review.write_text(json.dumps(bundle))
            with patch('harvest.preferred_index', return_value=([target], {})):
                with patch('sys.argv', command):
                    main()
                self.assertFalse(path.exists())
                with patch('sys.argv', command + ['--apply']):
                    main()
                saved = json.loads(path.read_text())
                self.assertEqual(saved[0]['sources'][0]['anchor'], 'hit陣')
                bundle['groups_sha256'] = 'stale'
                review.write_text(json.dumps(bundle))
                with patch('sys.argv', command + ['--apply']), self.assertRaises(ValueError):
                    main()
                self.assertEqual(json.loads(path.read_text()), saved)
                bundle['groups_sha256'] = hashlib.sha256(content).hexdigest()
                bundle['source_mappings'] = []
                bundle['source_mapping_removals'] = ['hit陣']
                review.write_text(json.dumps(bundle))
                with patch('sys.argv', command + ['--apply']):
                    main()
                self.assertEqual(json.loads(path.read_text()), [])
