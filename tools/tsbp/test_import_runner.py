"""Exercise real CLI allocation and checksum rejection with tiny dictionary fixtures."""
import importlib.util
from functools import lru_cache
import json
from pathlib import Path
import sys
import unittest
import hashlib
import io
import shutil
from contextlib import redirect_stdout
from import_review import run_maintenance, coalesce_identical_approvals, main as review_main

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('maintenance_fixtures', ROOT / 'tests/test_lexicon.py')
fixtures = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixtures)


class RunnerTests(unittest.TestCase):
    def test_structured_custom_fields_get_offline_preview_without_automatic_import(self):
        fixture = fixtures.MaintenanceTests()
        fixture.setUp()
        previous = sys.argv
        try:
            (fixture.root / 'tools').mkdir()
            shutil.copy2(ROOT / 'tools/lexicon.py', fixture.root / 'tools/lexicon.py')
            pilot = fixture.root / 'pilot'
            pilot.mkdir()
            group = {'key': 'liô', 'occurrences': [{'url': 'https://example.com/article',
                     'line': 1, 'anchor_start': 0, 'anchor_end': 3, 'anchor': 'liô'}]}
            raw = json.dumps([group], ensure_ascii=False)
            digest = hashlib.sha256(raw.encode()).hexdigest()
            (pilot / 'groups.json').write_text(raw)
            pin = fixtures.lex.moe_data(fixture.root)[0]
            summary = {'issue': 390, 'corpus_sha256': 'fixture', 'review_groups_sha256': digest,
                       'lexicon_root': str(fixture.root), 'moe': {'snapshot': pin['id'], 'sha256': pin['sha256']}}
            (pilot / 'summary.json').write_text(json.dumps(summary))
            bundle = {'schema_version': 1, 'issue': 390, 'corpus_sha256': 'fixture',
                      'groups_sha256': digest, 'moe_snapshot': pin['id'], 'approvals': [],
                      'custom_requests': [{'anchor_key': 'liô', 'prompt': '', 'preferred_form': 'liô心',
                                           'hanji': '𠞭心', 'reading': 'liô-sim'}]}
            review = pilot / 'review.json'
            review.write_text(json.dumps(bundle, ensure_ascii=False))
            sys.argv = ['import_review.py', str(review), '--pilot', str(pilot), '--apply']
            output = io.StringIO()
            with redirect_stdout(output):
                review_main()
            result = json.loads(output.getvalue())
            self.assertEqual(result['created'], [])
            self.assertEqual(result['custom_previews'][0]['status'], 'needs_review')
            self.assertEqual(result['custom_previews'][0]['request']['hanji_forms'], ['𠞭心'])
            self.assertEqual(result['custom_previews'][0]['checks']['moe_checked']['snapshot'], pin['id'])
            self.assertEqual(fixtures.lex.entries(fixture.root), [])
            self.assertEqual(fixtures.lex.next_id(fixture.root, []), 1)
        finally:
            sys.argv = previous
            fixture.tearDown()

    def test_duplicate_approvals_merge_sources_only_for_same_word_and_choices(self):
        def item(anchor, word, source, status):
            return {'anchor_key':anchor,'word_id':word,'status':status,
                    'reason':'Two approvals overlap; combine this word’s readings into one approval',
                    'request':{'preferred_form':'huānn','canonical_tl':'huānn','alternate_readings':[],
                               'sources':[{'url':source,'locator':'fixture'}]}}
        first=item('huānn','moe:2430','https://example.com/one','ready')
        duplicate=item('hōaⁿ','moe:2430','https://example.com/two','blocked')
        unrelated=item('other','moe:999','https://example.com/three','blocked')
        different=item('alias','moe:2430','https://example.com/four','blocked')
        different['request']['alternate_readings']=['other']
        coalesce_identical_approvals([first,duplicate,unrelated,different])
        self.assertEqual(duplicate['status'],'merged')
        self.assertEqual(len(first['request']['sources']),2)
        self.assertEqual(duplicate['merged_into_anchor'],'huānn')
        self.assertEqual(unrelated['status'],'blocked')
        self.assertEqual(different['status'],'blocked')

    def test_real_cli_allocates_and_checks_duplicates_without_changing_argv(self):
        fixture = fixtures.MaintenanceTests()
        fixture.setUp()
        try:
            argv = sys.argv
            request = fixture.request(alternate_readings=['bueh'])
            code, output, errors = run_maintenance(fixtures.lex, fixture.root, ['add', str(request)])
            self.assertEqual((code, errors), (0, ''))
            self.assertEqual(json.loads(output)['id'], 1)
            code, _, errors = run_maintenance(fixtures.lex, fixture.root, ['add', str(request)])
            self.assertEqual(code, 2)
            self.assertIn('Existing entry', errors)
            self.assertIs(sys.argv, argv)
            self.assertEqual(fixtures.lex.next_id(fixture.root, fixtures.lex.entries(fixture.root)), 2)
        finally:
            fixture.tearDown()

    def test_decoder_cache_never_skips_original_dictionary_checksum(self):
        fixture = fixtures.MaintenanceTests()
        fixture.setUp()
        original = fixtures.lex.ods_sheets
        try:
            fixtures.lex.ods_sheets = lru_cache(maxsize=1)(original)
            fixture.run_cli('fetch-moe')
            first = fixtures.lex.moe_data(fixture.root)
            second = fixtures.lex.moe_data(fixture.root)
            self.assertEqual(first, second)
            self.assertEqual(fixtures.lex.ods_sheets.cache_info().misses, 1)
            fixture.moe_path.write_bytes(b'corrupt cached dictionary')
            code, _, errors = run_maintenance(fixtures.lex, fixture.root, ['add', str(fixture.request())])
            self.assertEqual(code, 2)
            self.assertIn('checksum mismatch', errors)
            self.assertEqual(fixtures.lex.entries(fixture.root), [])
            self.assertEqual(fixtures.lex.next_id(fixture.root, []), 1)
        finally:
            fixtures.lex.ods_sheets = original
            fixture.tearDown()
