import unittest
from pathlib import Path
import tempfile
import shutil

from harvest import coverage, key, merged, occurrences, preferred_index, spans, verified_custom_resolutions
import json


def doc(text):
    return {"id": "test:1", "text": text,
            "metadata": {"title": "Test", "original_url": "https://example.com"}}


class ExtractionTests(unittest.TestCase):
    def test_handled_custom_requests_require_the_recorded_entry_and_pair(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            entry = root / 'entry.toml'
            entry.write_text('id = 671\npreferred_form = "liô心"\ncanonical_tl = "liô-sim"\n')
            resolution = {'anchor_key': 'liô', 'prompt': 'use "liô心"', 'entry_id': 671,
                          'preferred_form': 'liô心', 'canonical_tl': 'liô-sim'}
            path = root / 'handled.json'
            path.write_text(json.dumps([resolution]))
            records = [{'id': 671, 'path': 'entry.toml'}]
            self.assertEqual(verified_custom_resolutions(path, records, root), [resolution])
            self.assertEqual(verified_custom_resolutions(path, [], root), [])
            entry.write_text('id = 671\npreferred_form = "liô"\ncanonical_tl = "liô"\n')
            self.assertEqual(verified_custom_resolutions(path, records, root), [])

    def test_preserves_marks_hyphens_nasalization_and_numeric_tones(self):
        text = "M̄驚Kho̍k-kho̍k-tsông，chiâⁿ kap goa2 siuN7"
        self.assertEqual([text[a:b] for a, b in spans(text)],
                         ["M̄", "Kho̍k-kho̍k-tsông", "chiâⁿ", "kap", "goa2", "siuN7"])

    def test_leading_neutral_marker_is_part_of_anchor_and_offsets(self):
        text = "好--ah。ah。來--lah。m̄--koh。你甘願--ah--。-ah"
        rows = list(occurrences(doc(text), 6))
        self.assertEqual([r['anchor'] for r in rows],
                         ['--ah', 'ah', '--lah', 'm̄--koh', '--ah', 'ah'])
        for row in rows:
            self.assertEqual(text[row['anchor_start']:row['anchor_end']], row['anchor'])

    def test_common_form_does_not_remove_a_compound(self):
        rows = list(occurrences(doc("伊m̄驚m̄-koh走"), 6))
        self.assertEqual([r["anchor"] for r in rows if r["key"] != key("m̄")], ["m̄-koh"])

    def test_offsets_and_source_are_unchanged(self):
        source = doc("甲乙丙丁戊己庚辛M̄驚露水，穿tsat仔。")
        for row in occurrences(source, 6):
            self.assertEqual(row["anchor"], source["text"][row["anchor_start"]:row["anchor_end"]])
            self.assertEqual(row["snippet"], source["text"][row["context_start"]:row["context_end"]])
            self.assertNotIn("，", row["snippet"])
        self.assertEqual(source["text"], "甲乙丙丁戊己庚辛M̄驚露水，穿tsat仔。")

    def test_combining_mark_is_not_cut_at_context_edge(self):
        rows = list(occurrences(doc("甲M̄ê乙"), 1))
        self.assertEqual(rows[0]["snippet"], "甲M̄ê乙")

    def test_union_avoids_double_counting_overlaps(self):
        self.assertEqual(merged([(0, 5), (3, 7), (9, 10)]), [[0, 7], [9, 10]])
        rows = [{"document_id": "a", "context_start": 0, "context_end": 5},
                {"document_id": "a", "context_start": 3, "context_end": 7}]
        self.assertEqual(coverage(rows, {"a": "0123456789"}, "context"), 7)

    def test_retains_unaccented_anchors_and_pure_romanized_lines(self):
        rows = list(occurrences(doc("拍暗bong。thang kap。穿tsat仔"), 6))
        self.assertEqual([r["anchor"] for r in rows], ["bong", "thang", "kap", "tsat"])

    def test_double_hyphen_has_no_dangling_separator(self):
        text = "khok--一下 m̄--koh"
        self.assertEqual([text[a:b] for a, b in spans(text)], ["khok", "m̄--koh"])

    def test_context_does_not_cut_a_neighboring_romanized_span(self):
        row = list(occurrences(doc("伊kap kho̍k-kho̍k-tsông做伙"), 3))[0]
        self.assertIn("kho̍k-kho̍k-tsông", row["snippet"])

    def test_preferred_index_covers_every_written_form_without_reading_aliases(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'tools').mkdir()
            shutil.copy2(Path(__file__).resolve().parents[1] / 'lexicon.py', root / 'tools/lexicon.py')
            entries = root / "entries" / "zero"
            entries.mkdir(parents=True)
            (entries / "one.toml").write_text('id = 1\npreferred_form = "ē-tàng"\ncanonical_tl = "ē-tàng"\n')
            (entries / "two.toml").write_text('id = 2\npreferred_form = "ē"\ncanonical_tl = "ē"\n')
            (entries / "three.toml").write_text('id = 3\npreferred_form = "會曉"\ncanonical_tl = "ē-hiáu"\nalternate_readings = ["ē-sái"]\n')
            for entry_path in entries.glob('*.toml'):
                if 'alternate_readings' not in entry_path.read_text():
                    entry_path.write_text(entry_path.read_text() + 'alternate_readings = []\n')
            (entries / 'four.toml').write_text('id = 4\npreferred_form = "想beh"\ncanonical_tl = "siūnn-beh"\nalternate_readings = ["siūnn-bueh"]\n')
            records, index = preferred_index(root)
            self.assertEqual(len(records), 4)
            self.assertEqual(set(index), {"ē-tàng", "ē", "會曉", "想beh", "想bueh"})
            self.assertIn(key("Ē-tàng"), index)
            for form in ["ē-hiáu", "ē-sái", "e-tang", "ē--tàng"]:
                self.assertNotIn(key(form), index)
            self.assertEqual(index["ē-tàng"][0]["id"], 1)
            self.assertEqual(index["想bueh"][0]["id"], 4)
            self.assertEqual(index['想bueh'][0]['multi_syllable_written_forms'], ['想beh','想bueh'])
            self.assertEqual(index['ē'][0]['multi_syllable_written_forms'], [])

    def test_magazine_context_does_not_exclude_other_bong_occurrences(self):
        text = '《台文通訊BONG報》kap拍暗bong。台文通訊BONG報'
        rows = list(occurrences(doc(text), 6, ['台文通訊BONG報']))
        self.assertEqual([r['anchor'] for r in rows], ['kap', 'bong'])
        for row in rows:
            self.assertNotIn('台文通訊BONG報', row['snippet'])
            self.assertEqual(text[row['anchor_start']:row['anchor_end']], row['anchor'])

    def test_context_exclusion_does_not_remove_a_whole_clause_or_create_fragments(self):
        text = 'hip相台文通訊BONG報kā伊拍暗bong'
        rows = list(occurrences(doc(text), 6, ['台文通訊BONG報']))
        self.assertEqual([r['anchor'] for r in rows], ['hip', 'kā', 'bong'])
        self.assertTrue(all('台文通訊BONG報' not in r['clause'] for r in rows))
        self.assertEqual(list(occurrences(doc('foobar'), 6, ['foo'])), [])


if __name__ == "__main__":
    unittest.main()
