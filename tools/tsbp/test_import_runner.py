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
from unittest import mock
from import_review import run_maintenance, coalesce_identical_approvals, apply_ready, main as review_main
from review_support import add_review_choices

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('maintenance_fixtures', ROOT / 'tests/test_lexicon.py')
fixtures = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixtures)


class RunnerTests(unittest.TestCase):
    def fixture(self):
        fixture = fixtures.MaintenanceTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        return fixture

    def make_pilot(self, fixture, words):
        (fixture.root / 'tools').mkdir()
        shutil.copyfile(ROOT / 'tools/lexicon.py', fixture.root / 'tools/lexicon.py')
        pilot = fixture.root / 'pilot'
        pilot.mkdir()
        groups = [{'key': word, 'display': word, 'normalized_tl': word,
                   'parser_compatible': True, 'dedup_lookup_forms': [word],
                   'occurrences': [{'url': 'https://example.com/article', 'line': n,
                                    'anchor_start': 0, 'anchor_end': len(word), 'anchor': word}]}
                  for n, word in enumerate(words, 1)]
        raw = json.dumps(groups, ensure_ascii=False)
        digest = hashlib.sha256(raw.encode()).hexdigest()
        (pilot / 'groups.json').write_text(raw)
        pin = fixtures.lex.moe_data(fixture.root)[0]
        (pilot / 'summary.json').write_text(json.dumps({
            'issue': 390, 'corpus_sha256': 'fixture', 'review_groups_sha256': digest,
            'lexicon_root': str(fixture.root), 'moe': {'snapshot': pin['id'], 'sha256': pin['sha256']}}))
        bundle = {'schema_version': 1, 'issue': 390, 'corpus_sha256': 'fixture',
                  'groups_sha256': digest, 'moe_snapshot': pin['id'],
                  'approvals': [{'anchor_key': word, 'approved': True, 'preferred_form': word,
                                 'import_mode': 'source_anchor', 'source_reading': word} for word in words]}
        review = pilot / 'review.json'
        review.write_text(json.dumps(bundle, ensure_ascii=False))
        return pilot, review

    def test_review_preview_uses_warm_entry_cache_and_apply_imports_only_ready_words(self):
        fixture = self.fixture()
        fixtures.lex.add_batch(fixture.root, [fixtures.lex.request_data(fixture.request())])
        pilot, review = self.make_pilot(fixture, ['beh', 'tîng', 'bueh'])
        fixtures.lex.entry_snapshot(fixture.root)
        args = ['import_review.py', str(review), '--pilot', str(pilot)]
        read = Path.read_bytes
        def reject_entry_read(path):
            if path.is_relative_to(fixture.root / 'entries'):
                raise AssertionError('Preview must reuse cached entry fields')
            return read(path)
        output = io.StringIO()
        with mock.patch.object(sys, 'argv', args), mock.patch.object(Path, 'read_bytes', reject_entry_read), redirect_stdout(output):
            review_main()
        preview = json.loads(output.getvalue())
        self.assertEqual([item['status'] for item in preview['items']], ['blocked', 'ready', 'ready'])
        self.assertEqual(preview['created'], [])
        output = io.StringIO()
        with mock.patch.object(sys, 'argv', args + ['--apply']), redirect_stdout(output):
            review_main()
        result = json.loads(output.getvalue())
        self.assertEqual([item['status'] for item in result['items']], ['blocked', 'created', 'created'])
        self.assertEqual([item['id'] for item in result['created']], [2, 3])
        for path, entry in fixtures.lex.entries(fixture.root):
            self.assertEqual(entry['review_status'], 'imported')
            if entry['id'] > 1:
                self.assertEqual(entry['sources'][0]['url'], 'https://example.com/article')
        self.assertEqual(fixtures.lex.validate(fixture.root)['entries'], 3)

    def test_ready_approvals_use_one_batch_and_merged_sources_share_the_result(self):
        fixture = self.fixture()
        request = fixtures.lex.request_data(fixture.request())
        other = fixtures.lex.request_data(fixture.request('重', 'tîng'))
        plan = [{'anchor_key': 'beh', 'word_id': '7', 'status': 'ready', 'request': request},
                {'anchor_key': 'other-anchor', 'word_id': '7', 'status': 'blocked',
                 'reason': 'Two approvals overlap', 'request': {**request, 'sources': [
                     {'url': 'https://example.com/second', 'locator': 'Second occurrence'}]}},
                {'anchor_key': 'blocked', 'status': 'blocked', 'reason': 'Needs review'},
                {'anchor_key': '重', 'status': 'ready', 'request': other}]
        coalesce_identical_approvals(plan)
        with mock.patch.object(fixtures.lex, 'add_batch', wraps=fixtures.lex.add_batch) as batch:
            created = apply_ready(fixtures.lex, fixture.root, plan)
        self.assertEqual(batch.call_count, 1)
        self.assertEqual(len(created), 2)
        self.assertEqual(plan[0]['id'], plan[1]['id'])
        self.assertEqual(plan[0]['path'], plan[1]['path'])
        self.assertEqual(plan[2]['status'], 'blocked')
        first = fixtures.lex.load_toml(fixture.root / plan[0]['path'])
        self.assertEqual(len(first['sources']), 2)

    def test_approved_moe_word_reports_hanji_suggestions_without_importing_them(self):
        fixture = self.fixture()
        # Install an original-source fixture with a two-Hanji word and extension.
        old_digest = fixtures.lex.load_toml(fixture.root / 'references/moe.toml')['sha256']
        fixtures.make_ods(fixture.moe_path, {
            '詞目': [['詞目id', '漢字', '羅馬字'], [7, '欲食', 'beh-tsia̍h'], [8, '欲食飯', 'beh-tsia̍h-pn̄g']]})
        digest = hashlib.sha256(fixture.moe_path.read_bytes()).hexdigest()
        pin = fixture.root / 'references/moe.toml'
        pin.write_text(pin.read_text().replace(old_digest, digest))
        cache = fixture.root / '.cache/dictionaries/moe' / digest / 'kautian.ods'
        cache.parent.mkdir(parents=True)
        fixture.moe_path.replace(cache)
        pilot, review = self.make_pilot(fixture, ['beh-tsia̍h'])
        records = fixtures.lex.moe_data(fixture.root)[2]
        groups = json.loads((pilot / 'groups.json').read_text())
        groups[0]['moe_matches'] = [records[0]]
        add_review_choices(groups, records)
        (pilot / 'groups.json').write_text(json.dumps(groups, ensure_ascii=False))
        groups_digest = hashlib.sha256((pilot / 'groups.json').read_bytes()).hexdigest()
        summary = json.loads((pilot / 'summary.json').read_text())
        summary['review_groups_sha256'] = groups_digest
        (pilot / 'summary.json').write_text(json.dumps(summary))
        bundle = json.loads(review.read_text())
        bundle['groups_sha256'] = groups_digest
        word = groups[0]['review_words'][0]
        bundle['approvals'][0].update(import_mode='moe', word_id=word['id'],
                                      canonical_choice_id=word['readings'][0]['id'])
        review.write_text(json.dumps(bundle))
        args = ['import_review.py', str(review), '--pilot', str(pilot)]
        for flags, expected_status in (([], 'ready'), (['--apply'], 'created')):
            output = io.StringIO()
            with mock.patch.object(sys, 'argv', args + flags), redirect_stdout(output):
                review_main()
            result = json.loads(output.getvalue())
            item = result['items'][0]
            self.assertEqual(item['status'], expected_status)
            suggestion, = item['checks']['related_moe_entries']
            self.assertEqual(suggestion['headword'], '欲食飯')
            self.assertEqual(suggestion['relations'], [{'base_form': '欲食', 'matched_form': '欲食飯', 'pattern': 'ABX'}])
            if not flags:
                self.assertEqual(fixtures.lex.entries(fixture.root), [])
        entry, = fixtures.lex.entries(fixture.root)
        self.assertEqual(entry[1]['preferred_form'], 'beh-tsia̍h')
        self.assertEqual(entry[1]['moe_forms'], ['欲食'])
        self.assertEqual(entry[1]['review_status'], 'imported')
        self.assertEqual(fixtures.lex.next_id(fixture.root, [entry]), 2)

    def test_writer_recheck_blocks_stale_plan_without_allocating_or_individual_retries(self):
        fixture = self.fixture()
        request = fixtures.lex.request_data(fixture.request())
        plan = [{'anchor_key': 'new', 'status': 'ready',
                 'request': fixtures.lex.request_data(fixture.request('重', 'tîng'))},
                {'anchor_key': 'beh', 'status': 'ready', 'request': request}]
        fixtures.lex.add_batch(fixture.root, [request])
        with mock.patch.object(fixtures.lex, 'add_batch', wraps=fixtures.lex.add_batch) as batch:
            self.assertEqual(apply_ready(fixtures.lex, fixture.root, plan), [])
        self.assertEqual(batch.call_count, 1)
        self.assertTrue(all(item['status'] == 'blocked' for item in plan))
        self.assertEqual(fixtures.lex.next_id(fixture.root, fixtures.lex.entries(fixture.root)), 2)
        self.assertEqual(len(fixtures.lex.entries(fixture.root)), 1)

    def test_structured_custom_fields_get_offline_preview_without_automatic_import(self):
        fixture = fixtures.MaintenanceTests()
        fixture.setUp()
        previous = sys.argv
        try:
            (fixture.root / 'tools').mkdir()
            shutil.copyfile(ROOT / 'tools/lexicon.py', fixture.root / 'tools/lexicon.py')
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
