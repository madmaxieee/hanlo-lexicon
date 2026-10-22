"""Batch preflight/allocation and disposable entry-index behavior."""

import json
import hashlib
import os
import sqlite3
import unittest
from unittest import mock

import test_lexicon as support

lex = support.lex


class BatchAndCacheTests(unittest.TestCase):
    setUp = support.MaintenanceTests.setUp
    tearDown = support.MaintenanceTests.tearDown
    run_cli = support.MaintenanceTests.run_cli
    request = support.MaintenanceTests.request

    def candidate(self, form='beh', reading='beh', **extra):
        return lex.request_data(self.request(form, reading, **extra))

    def batch(self, rows):
        path = self.root / 'batch.json'
        path.write_text(json.dumps(rows, ensure_ascii=False))
        return path

    def test_batch_matches_sequential_adds_and_loads_inputs_once(self):
        rows = [self.candidate(alternate_readings=['bueh']), self.candidate('重', 'tîng')]
        expected = []
        for row in rows:
            path = self.root / 'single.json'
            path.write_text(json.dumps(row, ensure_ascii=False))
            expected.append(self.run_cli('add', str(path)))
        expected_bytes = {p.relative_to(self.root): p.read_bytes() for p, _ in lex.entries(self.root)}
        for path, _ in lex.entries(self.root):
            path.unlink()
        (self.root / 'id-sequence.toml').write_text('next_id = 1\n')
        with mock.patch.object(lex, 'entries', wraps=lex.entries) as entries, \
             mock.patch.object(lex, 'moe_data', wraps=lex.moe_data) as moe, \
             mock.patch.object(lex, 'lkk_data', wraps=lex.lkk_data) as lkk:
            actual = lex.add_batch(self.root, rows)
        self.assertEqual(actual['results'], expected)
        self.assertEqual(entries.call_count, 1)
        self.assertEqual(moe.call_count, 1)
        self.assertEqual(lkk.call_count, 1)
        self.assertEqual({p.relative_to(self.root): p.read_bytes() for p, _ in lex.entries(self.root)}, expected_bytes)
        self.assertEqual(self.run_cli('validate')['entries'], 2)
        self.run_cli('format', '--check')

    def test_dry_run_checks_plan_without_reserving_or_writing(self):
        path = self.batch([self.candidate(), self.candidate('重', 'tîng')])
        counter = (self.root / 'id-sequence.toml').read_bytes()
        plan = self.run_cli('add-batch', str(path), '--dry-run')
        self.assertTrue(plan['dry_run'])
        self.assertFalse(plan['reserved'])
        self.assertEqual([r['id'] for r in plan['results']], [1, 2])
        self.assertEqual(lex.entries(self.root), [])
        self.assertEqual((self.root / 'id-sequence.toml').read_bytes(), counter)
        actual = self.run_cli('add-batch', str(path))
        self.assertEqual(actual['results'], plan['results'])
        self.assertTrue(actual['reserved'])

    def test_invalid_later_request_leaves_all_ids_and_entries_untouched(self):
        rows = [self.candidate(), self.candidate('重', 'tîng', sources=[{'snapshot': 'lkk-fixture', 'row': 999}])]
        message = self.run_cli('add-batch', str(self.batch(rows)), expected=2)
        self.assertIn('Batch request 2', message)
        self.assertEqual(self.run_cli('next-id')['next_id'], 1)
        self.assertFalse(lex.entry_files(self.root))
        self.assertFalse((self.root / '.lexicon.lock').exists())

    def test_existing_and_intra_batch_alias_conflicts_are_not_skipped(self):
        first = self.candidate(alternate_readings=['bueh'])
        alias = self.candidate(reading='bueh')
        self.run_cli('add-batch', str(self.batch([first, alias])), expected=2)
        self.assertEqual(self.run_cli('next-id')['next_id'], 1)
        self.run_cli('add', str(self.request()))
        self.run_cli('add-batch', str(self.batch([self.candidate('new'), first])), expected=2)
        self.assertEqual(self.run_cli('next-id')['next_id'], 2)
        self.assertEqual(len(lex.entries(self.root)), 1)

    def test_distinct_homographs_and_shared_readings_remain_separate(self):
        rows = [self.candidate(), self.candidate(identity_note='A separate fixture word.'),
                self.candidate('another', 'beh')]
        result = self.run_cli('add-batch', str(self.batch(rows)))
        self.assertEqual(result['count'], 3)
        self.assertEqual(self.run_cli('validate')['entries'], 3)
        self.run_cli('add-batch', str(self.batch([rows[1]])), expected=2)
        self.assertEqual(self.run_cli('next-id')['next_id'], 4)
        found = self.run_cli('query', 'beh')
        self.assertEqual(found['count'], 3)
        self.assertEqual(found, self.run_cli('query', 'beh', '--no-cache'))

    def test_batch_reports_follow_sequential_path_order(self):
        rows = [self.candidate('zzz'), self.candidate('aaa'), self.candidate('middle')]
        actual = lex.add_batch(self.root, rows)['results']
        self.assertEqual([m['id'] for m in actual[2]['checks']['existing_entries']], [2, 1])
        self.assertEqual(actual[2]['checks'], lex.check(
            self.root, rows[2], lex.entries(self.root)[:1] + lex.entries(self.root)[2:]))

    def test_bad_batch_shapes_unknown_fields_and_manual_ids_fail_before_allocation(self):
        for rows in [[], {}, [None], [{'id': 9}], [dict(self.candidate(), examples=['removed'])]]:
            with self.subTest(rows=rows):
                self.run_cli('add-batch', str(self.batch(rows)), expected=2)
                self.assertEqual(self.run_cli('next-id')['next_id'], 1)

    def test_source_corruption_blocks_batch_even_after_entry_cache_is_warm(self):
        self.run_cli('add', str(self.request()))
        self.run_cli('query', 'beh')
        self.moe_path.write_bytes(b'corrupt')
        self.run_cli('add-batch', str(self.batch([self.candidate('another')])), expected=2)
        self.assertEqual(self.run_cli('next-id')['next_id'], 2)
        self.assertEqual(len(lex.entries(self.root)), 1)

    def test_partial_write_failure_reserves_the_entire_range_and_releases_lock(self):
        rows = [self.candidate(), self.candidate('重', 'tîng')]
        write = lex.atomic_write
        calls = 0
        def fail_second(path, text):
            nonlocal calls
            if path.is_relative_to(self.root / 'entries'):
                calls += 1
                if calls == 2:
                    raise OSError('simulated disk failure')
            write(path, text)
        with mock.patch.object(lex, 'atomic_write', side_effect=fail_second):
            with self.assertRaisesRegex(OSError, 'simulated disk failure'):
                lex.add_batch(self.root, rows)
        self.assertFalse((self.root / '.lexicon.lock').exists())
        self.assertEqual(self.run_cli('next-id')['next_id'], 3)
        self.assertEqual(self.run_cli('validate')['entries'], 1)
        self.assertEqual(self.run_cli('add', str(self.request('重', 'tîng')))['id'], 3)

    def test_batch_respects_writer_lock(self):
        (self.root / '.lexicon.lock').mkdir()
        self.run_cli('add-batch', str(self.batch([self.candidate()])), expected=2)
        self.assertEqual(self.run_cli('next-id')['next_id'], 1)

    def test_indexed_checks_equal_full_scans_including_annotations_and_hanji(self):
        lex.add_batch(self.root, [self.candidate(alternate_readings=['bueh'], hanji_forms=['欲']),
                                  self.candidate(identity_note='Separate word.'), self.candidate('重', 'tîng')])
        current = lex.entries(self.root)
        evidence = lex.lkk_data(self.root), lex.moe_data(self.root)
        index = lex.LookupIndex(current, evidence)
        for candidate in [self.candidate(), self.candidate('卜', 'bueh'),
                          self.candidate('other', 'other', hanji_forms=['欲']),
                          self.candidate('重', 'tîng'), self.candidate('not-present', 'bóng')]:
            expected = lex.check(self.root, candidate, current, evidence)
            self.assertEqual(lex.check(self.root, candidate, current, evidence, index), expected)
            self.assertEqual(lex.check(self.root, candidate, evidence=evidence), expected)

    def test_warm_entry_cache_avoids_toml_parsing_and_preserves_provenance(self):
        lex.add_batch(self.root, [self.candidate(alternate_readings=['bueh'], hanji_forms=['欲'])])
        expected = lex.query_entries(self.root, {'欲'}, {'bueh'})
        with mock.patch.object(lex, 'load_toml', side_effect=AssertionError('unchanged TOML must not be parsed')):
            self.assertEqual(lex.query_entries(self.root, {'欲'}, {'bueh'}), expected)
        self.assertEqual(expected[0][1]['sources'], [{'snapshot': 'lkk-fixture', 'row': 2}])
        self.assertEqual(self.run_cli('query', '--id', '1')['entries'][0]['entry'], expected[0][1])

    def test_complete_snapshot_reuses_cached_entries_and_original_byte_hashes(self):
        lex.add_batch(self.root, [self.candidate(), self.candidate('重', 'tîng')])
        expected = lex.entry_snapshot(self.root, use_cache=False)
        self.assertEqual(lex.entry_snapshot(self.root), expected)
        with mock.patch.object(lex, 'load_toml', side_effect=AssertionError('Warm snapshot must not parse TOML')):
            self.assertEqual(lex.entry_snapshot(self.root), expected)
        path, entry, digest = expected[0]
        self.assertEqual(digest, hashlib.sha256(path.read_bytes()).hexdigest())
        path.write_text(path.read_text() + '\n# Byte provenance changed\n')
        updated = lex.entry_snapshot(self.root)
        self.assertEqual(updated[0][1], entry)
        self.assertNotEqual(updated[0][2], digest)
        self.assertEqual(updated[0][2], hashlib.sha256(path.read_bytes()).hexdigest())
        path.unlink()
        self.assertEqual(len(lex.entry_snapshot(self.root)), 1)

    def test_existing_v1_database_is_upgraded_to_supply_snapshot_hashes(self):
        lex.add_batch(self.root, [self.candidate()])
        database = self.root / '.cache/entries.sqlite3'
        with sqlite3.connect(database) as connection:
            connection.execute('CREATE TABLE entries (path TEXT PRIMARY KEY, stamp TEXT NOT NULL, '
                               'payload TEXT NOT NULL, id INTEGER NOT NULL, identity TEXT NOT NULL, target TEXT NOT NULL)')
        snapshot = lex.entry_snapshot(self.root)
        self.assertEqual(len(snapshot), 1)
        self.assertEqual(snapshot[0][2], hashlib.sha256(snapshot[0][0].read_bytes()).hexdigest())
        with mock.patch.object(lex, 'load_toml', side_effect=AssertionError('Upgraded cache must be reusable')):
            self.assertEqual(lex.entry_snapshot(self.root), snapshot)

    def test_cache_tracks_same_size_edits_restored_mtime_renames_and_deletions(self):
        lex.add_batch(self.root, [self.candidate()])
        self.assertEqual(len(lex.query_entries(self.root, {'beh'})), 1)
        path, entry = lex.entries(self.root)[0]
        before = path.stat()
        entry['preferred_form'] = 'bah'
        path.write_text(lex.render(entry))
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.assertEqual(path.stat().st_size, before.st_size)
        self.assertEqual(lex.query_entries(self.root, {'beh'}), [])
        self.assertEqual(len(lex.query_entries(self.root, {'bah'})), 1)
        moved = path.with_name('renamed.toml')
        path.rename(moved)
        self.assertEqual(lex.query_entries(self.root, {'bah'})[0][0], moved)
        moved.unlink()
        self.assertEqual(lex.query_entries(self.root, {'bah'}), [])
        self.run_cli('add', str(self.request('new')))
        self.assertEqual(lex.query_entries(self.root, {'new'})[0][1]['id'], 2)

    def test_schema_change_invalidates_the_entry_cache(self):
        lex.add_batch(self.root, [self.candidate()])
        lex.query_entries(self.root, {'beh'})
        path = self.root / 'schema/entry.schema.json'
        schema = json.loads(path.read_text())
        schema['properties']['preferred_form']['const'] = 'different'
        path.write_text(json.dumps(schema))
        with self.assertRaises(lex.Error):
            lex.query_entries(self.root, {'beh'})

    def test_corrupt_or_unavailable_sqlite_falls_back_to_toml(self):
        lex.add_batch(self.root, [self.candidate()])
        expected = lex.query_entries(self.root, {'beh'})
        database = self.root / '.cache/entries.sqlite3'
        database.write_bytes(b'broken sqlite')
        self.assertEqual(lex.query_entries(self.root, {'beh'}), expected)
        with mock.patch.object(sqlite3, 'connect', side_effect=sqlite3.OperationalError('locked')):
            self.assertEqual(lex.query_entries(self.root, {'beh'}), expected)
        lex.entry_files(self.root)[0].write_text('invalid toml =')
        with self.assertRaises(lex.Error):
            lex.query_entries(self.root, {'beh'})

    def test_cache_does_not_hide_duplicate_ids_or_invalid_entries(self):
        lex.add_batch(self.root, [self.candidate()])
        lex.query_entries(self.root, {'beh'})
        path, entry = lex.entries(self.root)[0]
        entry['preferred_form'] = 'another'
        (path.parent / 'duplicate.toml').write_text(lex.render(entry))
        with self.assertRaisesRegex(lex.Error, 'Duplicate ID'):
            lex.query_entries(self.root, {'beh'})
        self.run_cli('validate', expected=2)

    def test_query_is_offline_and_rejects_ambiguous_arguments(self):
        lex.add_batch(self.root, [self.candidate()])
        self.moe_path.unlink()
        self.assertEqual(self.run_cli('query', 'BEH')['count'], 1)
        self.assertEqual(self.run_cli('query', '--id', '1')['count'], 1)
        self.assertEqual(self.run_cli('query', 'bèh')['count'], 0)
        self.run_cli('query', expected=2)
        self.run_cli('query', 'beh', '--id', '1', expected=2)


if __name__ == '__main__':
    unittest.main()
