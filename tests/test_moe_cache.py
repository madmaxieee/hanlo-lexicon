"""Decoded MOE caches retain evidence and recover without weakening source checks."""

import concurrent.futures
import hashlib
import json
import unittest
from unittest import mock

import test_lexicon as support

lex = support.lex


class MoeCacheTests(unittest.TestCase):
    setUp = support.MaintenanceTests.setUp
    tearDown = support.MaintenanceTests.tearDown

    def cache_path(self):
        return self.moe_path.with_name('decoded-v1.json')

    def test_warm_cache_matches_original_decoder_without_parsing_ods(self):
        pin, _, raw = lex.cached_moe(self.root)
        expected = lex.decode_moe(pin, raw)
        self.assertEqual(lex.moe_data(self.root), expected)
        with mock.patch.object(lex, 'ods_sheets', side_effect=AssertionError('warm cache must skip XML')):
            actual = lex.moe_data(self.root)
        self.assertEqual(actual, expected)
        self.assertIsInstance(actual[1]['詞目'][1], tuple)
        self.assertEqual(actual[2][0]['source']['row'], 2)
        actual[2][0]['definitions'].append('caller mutation')
        self.assertEqual(lex.moe_data(self.root), expected)

    def test_missing_corrupt_and_stale_caches_rebuild(self):
        expected = lex.moe_data(self.root)
        for damage in ('missing', 'syntax', 'version', 'decoder', 'pin', 'payload'):
            with self.subTest(damage=damage):
                path = self.cache_path()
                cache = json.loads(path.read_bytes())
                if damage == 'missing':
                    path.unlink()
                elif damage == 'syntax':
                    path.write_text('{broken')
                else:
                    if damage == 'version':
                        cache['version'] += 1
                    elif damage == 'decoder':
                        cache['decoder_sha256'] = '0' * 64
                    elif damage == 'pin':
                        cache['pin']['id'] = 'stale'
                    else:
                        cache['data']['records'][0]['definitions'].append('damaged wording')
                    path.write_text(json.dumps(cache))
                with mock.patch.object(lex, 'decode_moe', wraps=lex.decode_moe) as decode:
                    self.assertEqual(lex.moe_data(self.root), expected)
                self.assertEqual(decode.call_count, 1)
                with mock.patch.object(lex, 'ods_sheets', side_effect=AssertionError('rebuilt cache must be usable')):
                    self.assertEqual(lex.moe_data(self.root), expected)

    def test_invalid_shapes_rebuild_even_with_matching_payload_checksum(self):
        expected = lex.moe_data(self.root)
        for field, value in (('sheets', []), ('records', [None])):
            with self.subTest(field=field):
                cache = json.loads(self.cache_path().read_bytes())
                cache['data'][field] = value
                cache['data_sha256'] = hashlib.sha256(lex.moe_payload_bytes(cache['data'])).hexdigest()
                self.cache_path().write_bytes(lex.moe_payload_bytes(cache))
                self.assertEqual(lex.moe_data(self.root), expected)

    def test_changed_pin_metadata_refreshes_original_source_identities(self):
        lex.moe_data(self.root)
        path = self.root / 'references/moe.toml'
        path.write_text(path.read_text().replace('moe-fixture', 'moe-new-fixture'))
        result = lex.moe_data(self.root)
        self.assertEqual(result[0]['id'], 'moe-new-fixture')
        self.assertTrue(all(r['source']['snapshot'] == 'moe-new-fixture' for r in result[2]))

    def test_warm_cache_never_bypasses_original_checksum_or_format(self):
        lex.moe_data(self.root)
        self.moe_path.write_bytes(b'corrupt original')
        with self.assertRaisesRegex(lex.Error, 'Cached MOE checksum mismatch'):
            lex.moe_data(self.root)
        self.moe_path.write_bytes(self.raw_moe)
        pin_path = self.root / 'references/moe.toml'
        pin_path.write_text(pin_path.read_text().replace('moe-ods', 'unsupported'))
        with self.assertRaisesRegex(lex.Error, 'Unsupported MOE source format'):
            lex.moe_data(self.root)

    def test_unavailable_cache_storage_falls_back_to_original_decoder(self):
        expected = lex.moe_data(self.root)
        self.cache_path().unlink()
        with mock.patch.object(lex, 'atomic_write', side_effect=OSError('read-only')):
            self.assertEqual(lex.moe_data(self.root), expected)
        self.assertFalse(self.cache_path().exists())
        self.cache_path().mkdir()  # An unreadable cache path must also recover.
        self.assertEqual(lex.moe_data(self.root), expected)

    def test_concurrent_cold_writers_publish_complete_cache(self):
        pin, _, raw = lex.cached_moe(self.root)
        expected = lex.decode_moe(pin, raw)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: lex.moe_data(self.root), range(4)))
        self.assertTrue(all(result == expected for result in results))
        with mock.patch.object(lex, 'ods_sheets', side_effect=AssertionError('cache must be complete')):
            self.assertEqual(lex.moe_data(self.root), expected)

    def test_decoded_cache_preserves_appendix_metadata_across_reading_sheets(self):
        path = self.root / 'appendix.ods'
        support.make_ods(path, {
            '詞目': [['詞目id', '詞目類型', '漢字', '羅馬字', '分類'],
                     [10, '附錄', '甲', 'kah', '外來詞'],
                     [11, '附錄', '乙', 'it', '節氣'],
                     [12, '附錄', '丙', 'ping', '山脈'],
                     [13, '單字不成詞者', '戊', 'boo', '']],
            '又唸作': [['詞目id', '漢字', '羅馬字'], [11, '乙', 'i̍t'], [13, '戊', 'bōo']],
            '姓': [['漢字', '羅馬字'], ['丁', 'Ting']],
        })
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        pin = self.root / 'references/moe.toml'
        pin.write_text(pin.read_text().replace(lex.load_toml(pin)['sha256'], digest))
        target = self.root / '.cache/dictionaries/moe' / digest / 'kautian.ods'
        target.parent.mkdir(parents=True, exist_ok=True)
        path.replace(target)
        expected = lex.moe_data(self.root)
        by_key = {(r['source']['sheet'], r['record_id']): r for r in expected[2]}
        self.assertEqual((by_key[('詞目', '10')]['entry_type'], by_key[('詞目', '10')]['category']), ('附錄', '外來詞'))
        self.assertEqual((by_key[('詞目', '11')]['entry_type'], by_key[('詞目', '11')]['category']), ('附錄', '節氣'))
        self.assertEqual((by_key[('又唸作', '11')]['entry_type'], by_key[('又唸作', '11')]['category']), ('附錄', '節氣'))
        self.assertEqual((by_key[('詞目', '13')]['entry_type'], by_key[('詞目', '13')]['category']), ('單字不成詞者', ''))
        self.assertEqual((by_key[('又唸作', '13')]['entry_type'], by_key[('又唸作', '13')]['category']), ('單字不成詞者', ''))
        self.assertEqual((by_key[('姓', '')]['entry_type'], by_key[('姓', '')]['category']), ('', ''))
        with mock.patch.object(lex, 'ods_sheets', side_effect=AssertionError('warm cache must skip XML')):
            self.assertEqual(lex.moe_data(self.root), expected)

