"""Combo evidence behavior using local entry fixtures; no dictionary/network use."""

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
SPEC = importlib.util.spec_from_file_location('hanlo_combos', ROOT / 'tools/hanlo_combos.py')
combos = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(combos)
lex = combos.lexicon


def entry(entry_id, preferred, reading, forms=(), **extra):
    return {
        'schema_version': 1, 'id': entry_id, 'preferred_form': preferred,
        'canonical_tl': reading, 'moe_forms': list(forms), 'alternate_readings': [],
        'review_status': 'imported',
        'sources': [{'url': 'https://example.org/original', 'locator': f'word {entry_id}'}],
        **extra,
    }


def inventory(*entries):
    return combos.derive([(Path(f'entries/nested/{e["id"]}.toml'), e) for e in entries])


def lookup(report, hanji, reading):
    return next(c for c in report['combos'] if (c['hanji'], c['canonical_tl']) == (hanji, reading))


class EvidenceTests(unittest.TestCase):
    def test_mixed_alignment_and_provenance(self):
        e = entry(1, '引tshuā', 'ín-tshuā', ['引𤆬'])
        report = inventory(e)
        self.assertEqual(lookup(report, '引', 'ín')['outputs'][0]['token'], '引')
        self.assertEqual(lookup(report, '𤆬', 'tshuā')['outputs'][0]['token'], 'tshuā')
        self.assertEqual(report['entries'][0]['sources'], e['sources'])
        self.assertEqual(report['entries'][0]['path'], 'entries/nested/1.toml')
        self.assertEqual(report['entries'][0]['review_status'], 'imported')

    def test_contractions_are_skipped_without_inferred_mappings(self):
        report = inventory(entry(1, 'hông', 'hông', hanji_forms=['予人']),
                           entry(2, 'kâng', 'kâng', hanji_forms=['共人']))
        self.assertEqual(report['combos'], [])
        failed = [s for s in report['skipped_inputs'] if s['field'] == 'hanji_forms']
        self.assertEqual([s['value'] for s in failed], ['予人', '共人'])
        self.assertTrue(all('syllable count' in s['reason'] for s in failed))

    def test_tones_neutrality_and_alternate_readings_do_not_merge(self):
        report = inventory(entry(1, 'ê', 'ê', ['的'], alternate_readings=['ē']),
                           entry(2, '--ê', '--ê', ['的']), entry(3, 'ē', 'ē', ['的']))
        self.assertEqual({c['canonical_tl'] for c in report['combos']}, {'ê', '--ê', 'ē'})
        self.assertEqual(lookup(report, '的', 'ē')['outputs'][0]['entry_ids'], [3])
        self.assertEqual(lookup(report, '的', '--ê')['outputs'][0]['token'], '--ê')

    def test_implicit_hanji_neutral_boundary_is_safe_but_explicit_mismatch_skips(self):
        report = inventory(entry(1, 'tńg來', 'tńg--lâi', ['轉來']),
                           entry(2, 'tńg-lâi', 'tńg--lâi', ['轉來']))
        self.assertEqual(lookup(report, '來', '--lâi')['outputs'][0]['token'], '來')
        self.assertEqual(lookup(report, '來', '--lâi')['outputs'][0]['entry_ids'], [1])
        self.assertTrue(any(s['entry_id'] == 2 and 'neutral-tone' in s['reason'] for s in report['skipped_inputs']))

    def test_all_hanji_glyph_outputs_are_retained_as_conflicts(self):
        report = inventory(entry(1, '臺', 'tâi', ['台']), entry(2, '台', 'tâi', ['台']))
        c = lookup(report, '台', 'tâi')
        self.assertEqual(c['status'], 'conflicting')
        self.assertEqual({o['token'] for o in c['outputs']}, {'台', '臺'})
        self.assertEqual(c['support_count'], 2)
        self.assertEqual(lookup(report, '臺', 'tâi')['outputs'][0]['token'], '臺')

    def test_repeated_positions_and_reference_forms_count_once_per_output(self):
        report = inventory(entry(1, '人lâng', 'lâng-lâng', ['人人', '人人'], hanji_forms=['人人']),
                           entry(2, 'lâng', 'lâng', ['人']))
        c = lookup(report, '人', 'lâng')
        self.assertEqual(c['support_count'], 2)
        self.assertEqual(c['outputs'], [
            {'kind': 'hanji', 'token': '人', 'support_count': 1, 'entry_ids': [1]},
            {'kind': 'romanized', 'token': 'lâng', 'support_count': 2, 'entry_ids': [1, 2]},
        ])

    def test_one_support_is_consistent_but_not_a_confidence_policy(self):
        report = inventory(entry(1, 'tuì', 'tuì', ['對']), entry(2, '對', 'tuì', ['對']),
                           entry(3, 'tuì', 'tuì', ['對']), entry(4, 'suí', 'suí', ['水']))
        self.assertEqual(lookup(report, '對', 'tuì')['status'], 'conflicting')
        self.assertEqual(lookup(report, '水', 'suí')['status'], 'consistent_romanized')
        self.assertEqual(lookup(report, '水', 'suí')['support_count'], 1)

    def test_generated_entries_never_vote_or_overrule_curated_evidence(self):
        report = inventory(entry(1, '對', 'tuì', ['對']),
                           entry(2, 'tuì', 'tuì', ['對'], rule_generated=True),
                           entry(3, 'suí', 'suí', ['水'], rule_generated=True))
        self.assertEqual(lookup(report, '對', 'tuì')['status'], 'consistent_hanji')
        self.assertEqual(lookup(report, '對', 'tuì')['outputs'][0]['entry_ids'], [1])
        self.assertEqual(lookup(report, '水', 'suí')['status'], 'unknown')
        self.assertEqual(lookup(report, '水', 'suí')['support_count'], 0)
        self.assertEqual(report['excluded_generated_entry_ids'], [2, 3])

    def test_bad_preferred_alignment_gives_unknown_reference_combos(self):
        report = inventory(entry(1, 'wrong', 'ín-tshuā', ['引𤆬']))
        self.assertEqual(report['summary']['unknown'], 2)
        self.assertEqual(report['summary']['consistent_romanized'], 0)
        self.assertTrue(any(s['field'] == 'preferred_form' for s in report['skipped_inputs']))

    def test_bad_reference_does_not_erase_independent_valid_evidence(self):
        report = inventory(entry(1, '引tshuā', 'ín-tshuā', ['引𤆬', '引']))
        self.assertEqual(lookup(report, '𤆬', 'tshuā')['outputs'][0]['entry_ids'], [1])
        self.assertTrue(any(s['value'] == '引' for s in report['skipped_inputs']))

    def test_pure_hanji_and_mixed_preferred_forms_need_no_invented_reference(self):
        report = inventory(entry(1, '心', 'sim'), entry(2, '心sim', 'sim-sim'), entry(3, 'sim', 'sim'))
        self.assertEqual(len(report['combos']), 1)
        self.assertEqual(lookup(report, '心', 'sim')['outputs'][0]['entry_ids'], [1, 2])
        self.assertTrue(any(s['entry_id'] == 3 for s in report['skipped_inputs']))

    def test_punctuation_iteration_marks_and_wrong_romanization_are_audited(self):
        for preferred in ('人、人', '人々', '人lan'):
            with self.subTest(preferred=preferred):
                report = inventory(entry(1, preferred, 'lâng-lâng', ['人人']))
                self.assertEqual(lookup(report, '人', 'lâng')['status'], 'unknown')
                self.assertTrue(any(s['field'] == 'preferred_form' for s in report['skipped_inputs']))

    def test_variation_selectors_and_extended_hanji_preserve_glyphs(self):
        form = '𤆬\U000E0100'
        report = inventory(entry(1, form, 'tshuā', ['𤆬']))
        self.assertEqual(lookup(report, '𤆬', 'tshuā')['outputs'][0]['token'], form)
        self.assertEqual(lookup(report, form, 'tshuā')['outputs'][0]['token'], form)

    def test_markdown_exposes_supporting_words_and_original_sources(self):
        report = inventory(entry(1, '對', 'tuì', ['對'], editorial_rationale='Fixture maintainer decision.'),
                           entry(2, 'tuì', 'tuì', ['對']))
        self.assertEqual(report['entries'][0]['editorial_rationale'], 'Fixture maintainer decision.')
        report['fingerprint'] = 'fixture'
        text = combos.markdown(report)
        self.assertIn('## Conflicting', text)
        self.assertIn('#1 對 (tuì)', text)
        self.assertIn('#2 tuì (tuì)', text)
        self.assertIn('https://example.org/original', text)
        self.assertIn('majority vote', text)
        self.assertIn('Editorial decision: Fixture maintainer decision.', text)


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'schema').mkdir()
        shutil.copyfile(ROOT / 'schema/entry.schema.json', self.root / 'schema/entry.schema.json')
        self.path = self.root / 'entries/deep/prefix/entry.toml'
        self.path.parent.mkdir(parents=True)
        self.e = entry(1, 'tuì', 'tuì', ['對'])
        self.write_entry()

    def tearDown(self):
        self.temp.cleanup()

    def write_entry(self):
        self.path.write_text(lex.render(self.e), encoding='utf-8')

    def test_cli_uses_recursive_reader_and_does_not_change_authoritative_files(self):
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = subprocess.run([sys.executable, str(ROOT / 'tools/hanlo_combos.py'), '--root', str(self.root)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output['entries'], 1)
        self.assertEqual(output['consistent_romanized'], 1)
        self.assertTrue(Path(output['report']).is_file())
        self.assertEqual(before, {p: (self.root / p).read_bytes() for p in before})
        self.assertFalse((self.root / '.lexicon.lock').exists())

    def test_unchanged_inputs_hit_cache_and_report_can_be_regenerated(self):
        first = combos.build(self.root)
        Path(first['report']).unlink()
        with mock.patch.object(combos, 'derive', side_effect=AssertionError('should reuse cache')):
            second = combos.build(self.root)
        self.assertTrue(second['cache_hit'])
        self.assertEqual(first['fingerprint'], second['fingerprint'])
        self.assertTrue(Path(second['report']).is_file())

    def test_content_not_mtime_invalidates_cache_and_generated_flag_removes_vote(self):
        first = combos.build(self.root)
        self.e['rule_generated'] = True
        self.write_entry()
        second = combos.build(self.root)
        self.assertFalse(second['cache_hit'])
        self.assertNotEqual(first['fingerprint'], second['fingerprint'])
        self.assertEqual(second['unknown'], 1)
        self.assertEqual(second['consistent_romanized'], 0)

    def test_add_delete_rename_and_provenance_edits_invalidate(self):
        old = combos.build(self.root)
        for mutation in ('provenance', 'rename', 'add', 'delete'):
            with self.subTest(mutation=mutation):
                if mutation == 'provenance':
                    self.e['sources'][0]['locator'] = 'new source locator'
                    self.write_entry()
                elif mutation == 'rename':
                    self.path = self.path.rename(self.path.with_name('renamed.toml'))
                elif mutation == 'add':
                    second = self.path.with_name('second.toml')
                    second.write_text(lex.render(entry(2, 'suí', 'suí', ['水'])), encoding='utf-8')
                else:
                    second.unlink()
                new = combos.build(self.root)
                self.assertFalse(new['cache_hit'])
                self.assertNotEqual(new['fingerprint'], old['fingerprint'])
                old = new

    def test_schema_and_derivation_version_invalidate_cache(self):
        first = combos.build(self.root)
        with mock.patch.object(combos, 'DERIVATION_VERSION', combos.DERIVATION_VERSION + 1):
            version = combos.build(self.root)
        self.assertNotEqual(first['fingerprint'], version['fingerprint'])
        self.assertFalse(version['cache_hit'])
        schema = self.root / 'schema/entry.schema.json'
        schema.write_text(schema.read_text() + '\n')
        changed = combos.build(self.root)
        self.assertNotEqual(changed['fingerprint'], first['fingerprint'])

    def test_partial_invalid_cache_is_regenerated(self):
        first = combos.build(self.root)
        Path(first['inventory']).write_text('{unfinished')
        self.assertFalse(combos.build(self.root)['cache_hit'])

    def test_bad_entries_fail_without_overwriting_report_or_inventory(self):
        first = combos.build(self.root)
        saved = Path(first['inventory']).read_bytes(), Path(first['report']).read_bytes()
        self.path.write_text('invalid toml [')
        with self.assertRaises(lex.Error):
            combos.build(self.root)
        self.assertEqual(saved, (Path(first['inventory']).read_bytes(), Path(first['report']).read_bytes()))

    def test_concurrent_input_change_refuses_to_publish_mixed_snapshot(self):
        with mock.patch.object(combos, 'fingerprint', side_effect=['before', 'after']):
            with self.assertRaisesRegex(lex.Error, 'inputs changed'):
                combos.build(self.root)
        self.assertFalse((self.root / combos.CACHE_DIRECTORY / 'inventory.json').exists())
