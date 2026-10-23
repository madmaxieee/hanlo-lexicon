import unittest

from harvest import apply_final_exclusions, occurrences
from moe_context import build_lookups, regroup


def record(form, reading, entry_id='8913', variants=()):
    return {'headword': form, 'reading': reading, 'record_id': entry_id,
            'column': '羅馬字', 'source': {'snapshot': 'test', 'sheet': '詞目', 'row': int(entry_id)},
            'definitions': ['fixture'], 'variant_forms': list(variants)}


def groups_for(text, lookup=None):
    doc = {'id': 'test:1', 'text': text, 'metadata': {'title': 'Fixture', 'original_url': 'https://example.com'}}
    buckets = {}
    for row in occurrences(doc, 6):
        buckets.setdefault(row['key'], []).append(row)
    return [{'key': key, 'normalized_tl': (lookup or {}).get(key, key), 'occurrences': rows,
             'display': rows[0]['anchor'], 'exclusion_reason': None, 'preferred_matches': []}
            for key, rows in buckets.items()]


class MoeContextTests(unittest.TestCase):
    def test_hip_query_includes_compounds_without_substring_or_tone_matching(self):
        groups = groups_for('hip')
        related = build_lookups(groups, [record('翕相', 'hip-siòng'), record('吸石', 'khip-tsio̍h', '2'), record('別', 'híp', '3')])
        self.assertEqual([r['headword'] for r in related['hip']], ['翕相'])

    def test_compound_and_standalone_are_separate_and_occurrences_not_duplicated(self):
        text = '我hip相。毋通hip。'
        groups = groups_for(text)
        related = build_lookups(groups, [record('翕相', 'hip-siòng')])
        result, stats = regroup(groups, {'test:1': text}, related)
        by_key = {g['key']: g for g in result}
        self.assertEqual(set(by_key), {'hip', 'hip相'})
        self.assertEqual(stats['promoted_occurrences'], 1)
        self.assertEqual(sum(len(g['occurrences']) for g in result), 2)
        self.assertEqual(by_key['hip相']['moe_matches'][0]['record_id'], '8913')

    def test_nested_compounds_variants_and_all_readings_are_listed(self):
        text = '伊hip像機。'
        groups = groups_for(text)
        records = [record('翕相', 'hip-siòng', variants=['翕像']),
                   record('翕相機', 'hip-siòng-ki', '8914', ['翕像機']),
                   record('翕相機', 'hip-siōng-ki', '8915', ['翕像機'])]
        result, stats = regroup(groups, {'test:1': text}, build_lookups(groups, records))
        by_key = {g['key']: g for g in result}
        self.assertEqual(set(by_key), {'hip像', 'hip像機'})
        self.assertEqual({r['reading'] for r in by_key['hip像機']['moe_matches']}, {'hip-siòng-ki', 'hip-siōng-ki'})
        self.assertEqual(len(by_key['hip像機']['occurrences']), 1)
        self.assertEqual(stats['additional_anchor_occurrences'], 1)

    def test_equal_length_overlapping_ab_and_bc_are_both_listed(self):
        text = '相ki器'
        groups = groups_for(text)
        records = [record('相機', 'siòng-ki', '1'), record('機器', 'ki-khì', '2')]
        result, _ = regroup(groups, {'test:1': text}, build_lookups(groups, records))
        self.assertEqual({g['key'] for g in result}, {'相ki', 'ki器'})
        self.assertEqual({(g['occurrences'][0]['anchor_start'], g['occurrences'][0]['anchor_end'])
                          for g in result}, {(0, 3), (1, 4)})

    def test_romanized_abc_keeps_ab_bc_and_abc(self):
        text = 'hip-siòng-ki'
        groups = groups_for(text)
        records = [record('翕相', 'hip-siòng', '1'), record('相機', 'siòng-ki', '2'),
                   record('翕相機', 'hip-siòng-ki', '3')]
        result, stats = regroup(groups, {'test:1': text}, build_lookups(groups, records))
        self.assertEqual({g['key'] for g in result}, {'hip-siòng', 'siòng-ki', 'hip-siòng-ki'})
        self.assertEqual(stats['source_anchor_occurrences'], 1)
        self.assertEqual(stats['emitted_anchor_occurrences'], 3)

    def test_unknown_full_romanized_run_stays_when_subwords_match(self):
        text = 'hip-siòng-ki'
        groups = groups_for(text)
        records = [record('翕相', 'hip-siòng', '1'), record('相機', 'siòng-ki', '2')]
        result, _ = regroup(groups, {'test:1': text}, build_lookups(groups, records))
        by_key = {g['key']: g for g in result}
        self.assertEqual(set(by_key), {'hip-siòng', 'siòng-ki', 'hip-siòng-ki'})
        self.assertEqual(by_key['hip-siòng-ki']['kind'], 'romanized')

    def test_subwords_keep_poj_offsets_combining_marks_and_neutral_prefix(self):
        text = '甲khì--chit乙'
        groups = groups_for(text, {'khì--chit':'khì--tsit'})
        records = [record('去', 'khì', '1'), record('這', '--tsit', '2'), record('別', 'tsit', '3')]
        result, _ = regroup(groups, {'test:1': text}, build_lookups(groups, records))
        by_key = {g['key']: g for g in result}
        self.assertEqual(by_key['--chit']['normalized_forms'], ['--tsit'])
        self.assertEqual({m['record_id'] for m in by_key['--chit']['moe_matches']}, {'2'})
        for group in result:
            for row in group['occurrences']:
                self.assertEqual(text[row['anchor_start']:row['anchor_end']], row['anchor'])
                self.assertEqual(text[row['context_start']:row['context_end']], row['snippet'])

    def test_duplicate_dictionary_evidence_does_not_duplicate_occurrence(self):
        text = 'hip相機'
        groups = groups_for(text)
        records = [record('翕相', 'hip-siòng', '1'), record('翕相', 'hip-siòng', '2'),
                   record('翕相機', 'hip-siòng-ki', '3')]
        result, _ = regroup(groups, {'test:1': text}, build_lookups(groups, records))
        by_key = {g['key']: g for g in result}
        self.assertEqual(len(by_key['hip相']['occurrences']), 1)
        self.assertEqual(len(by_key['hip相']['moe_matches']), 2)
        self.assertEqual(len(by_key['hip相機']['occurrences']), 1)

    def test_related_entries_use_the_complete_final_romanized_query(self):
        whole = 'hip-siòng-ki'
        text = whole + '。hip。'
        groups = groups_for(text)
        records = [record('翕相機','hip-siòng-ki','1'), record('翕','hip','2')]
        result, _ = regroup(groups, {'test:1':text}, build_lookups(groups, records))
        by_key = {g['key']:g for g in result}
        self.assertEqual({r['record_id'] for r in by_key[whole]['moe_related']}, {'1'})
        self.assertEqual({r['record_id'] for r in by_key['hip']['moe_related']}, {'1','2'})

    def test_singles_are_suppressed_per_occurrence_inside_supported_compound(self):
        text = 'ē-tàng，tàng。'
        groups = groups_for(text)
        records = [record('會當','ē-tàng','1'), record('當','tàng','2')]
        result, stats = regroup(groups, {'test:1':text}, build_lookups(groups, records))
        by_key = {g['key']:g for g in result}
        self.assertEqual(set(by_key), {'ē-tàng','tàng'})
        self.assertEqual(len(by_key['tàng']['occurrences']),1)
        self.assertEqual(by_key['tàng']['occurrences'][0]['anchor_start'],7)
        self.assertEqual(stats['suppressed_single_syllable_occurrences'],1)
        self.assertEqual(stats['covered_single_syllable_audit'][0]['covered_by'][0]['anchor'],'ē-tàng')

    def test_single_inside_mixed_compound_is_hidden_but_two_and_three_syllables_remain(self):
        text = 'hip相機'
        groups = groups_for(text)
        records = [record('翕','hip','1'), record('翕相','hip-siòng','2'),
                   record('翕相機','hip-siòng-ki','3')]
        result, stats = regroup(groups, {'test:1':text}, build_lookups(groups, records))
        self.assertEqual({g['key'] for g in result},{'hip相','hip相機'})
        self.assertEqual(stats['suppressed_single_syllable_occurrences'],1)

    def test_single_inside_overlapping_ab_bc_is_hidden_without_dropping_either_word(self):
        text = '相ki器'
        groups = groups_for(text)
        records = [record('機','ki','1'), record('相機','siòng-ki','2'), record('機器','ki-khì','3')]
        result, stats = regroup(groups, {'test:1':text}, build_lookups(groups, records))
        self.assertEqual({g['key'] for g in result},{'相ki','ki器'})
        self.assertEqual(len(stats['covered_single_syllable_audit'][0]['covered_by']),2)

    def test_unknown_multisyllable_fallback_does_not_suppress_a_single(self):
        text = 'ē-tàng'
        groups = groups_for(text)
        records = [record('當','tàng','1')]
        result, stats = regroup(groups, {'test:1':text}, build_lookups(groups, records))
        self.assertEqual({g['key'] for g in result},{'ē-tàng','tàng'})
        self.assertEqual(stats['suppressed_single_syllable_occurrences'],0)

    def test_tracked_compound_still_suppresses_its_single_before_deduplication(self):
        text = 'ē-tàng'
        groups = groups_for(text)
        records = [record('會當','ē-tàng','1'), record('當','tàng','2')]
        result, _ = regroup(groups, {'test:1':text}, build_lookups(groups, records))
        apply_final_exclusions(result,set(),{'ē-tàng':[{'id':1,'preferred_form':'ē-tàng'}]})
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['exclusion_reason'],'tracked_preferred_form')

    def test_tracked_poj_compound_suppresses_singles_without_any_moe_compound_match(self):
        text = '會chit个chhui-sak台語文ê好所。chhui。'
        groups = groups_for(text, {'chit':'tsit','chhui-sak':'tshui-sak','chhui':'tshui'})
        records = [record('吹','tshui','1'), record('塞','sak','2')]
        result, stats = regroup(groups, {'test:1':text}, build_lookups(groups, records), {'tshui-sak'})
        by_key = {g['key']:g for g in result}
        self.assertEqual(len(by_key['chhui']['occurrences']),1)
        self.assertEqual(by_key['chhui']['occurrences'][0]['clause'],'chhui')
        self.assertNotIn('sak',by_key)
        self.assertEqual(by_key['chhui-sak']['moe_matches'],[])
        self.assertEqual(stats['suppressed_single_syllable_occurrences'],2)
        for item in stats['covered_single_syllable_audit']:
            self.assertEqual(item['covered_by'][0]['tracked_written_forms'],['tshui-sak'])
            self.assertFalse(item['covered_by'][0]['moe_match'])

    def test_tracked_multisyllable_component_cannot_cover_a_larger_unknown_fallback(self):
        text = 'chhui-sak-ki'
        groups = groups_for(text, {'chhui-sak-ki':'tshui-sak-ki'})
        records = [record('吹','tshui','1')]
        result, stats = regroup(groups, {'test:1':text}, build_lookups(groups, records), {'tshui-sak'})
        self.assertIn('chhui',{g['key'] for g in result})
        self.assertEqual(stats['suppressed_single_syllable_occurrences'],0)

    def test_a_compound_in_another_document_does_not_hide_a_standalone_single(self):
        groups = groups_for('ē-tàng') + groups_for('tàng')
        for row in groups[-1]['occurrences']:
            row['document_id']='test:2'
        records = [record('會當','ē-tàng','1'), record('當','tàng','2')]
        result, _ = regroup(groups, {'test:1':'ē-tàng','test:2':'tàng'}, build_lookups(groups, records))
        by_key = {g['key']:g for g in result}
        self.assertEqual(len(by_key['tàng']['occurrences']),1)
        self.assertEqual(by_key['tàng']['occurrences'][0]['document_id'],'test:2')

    def test_tracked_custom_mixed_form_covers_only_its_component_occurrences(self):
        text = 'liô心。liô。khoo狗螺。khoo。'
        groups = groups_for(text)
        records = [record('𠞭', 'liô', '1'), record('呼', 'khoo', '2')]
        result, stats = regroup(groups, {'test:1': text}, build_lookups(groups, records),
                                {'liô心', 'khoo狗螺'})
        by_key = {g['key']: g for g in result}
        self.assertEqual({k: len(g['occurrences']) for k, g in by_key.items()}, {'liô': 1, 'khoo': 1})
        self.assertEqual({g['occurrences'][0]['clause'] for g in result}, {'liô', 'khoo'})
        self.assertEqual(stats['suppressed_single_syllable_occurrences'], 2)
        self.assertEqual({r['covered_by'][0]['tracked_written_forms'][0]
                          for r in stats['covered_single_syllable_audit']}, {'liô心', 'khoo狗螺'})
        self.assertTrue(all(not r['covered_by'][0]['moe_match']
                            for r in stats['covered_single_syllable_audit']))

    def test_tracked_mixed_cover_uses_poj_offsets_and_exact_unit_boundaries(self):
        text = 'chhiu̍h心。chhiu̍h。chhiu̍h人。achhiu̍h心。'
        groups = groups_for(text, {'chhiu̍h': 'tshiu̍h', 'achhiu̍h': 'atshiu̍h'})
        records = [record('手', 'tshiu̍h', '1')]
        result, stats = regroup(groups, {'test:1': text}, build_lookups(groups, records), {'tshiu̍h心'})
        audit = stats['covered_single_syllable_audit']
        self.assertEqual(len(audit), 1)
        self.assertEqual(audit[0]['clause'], 'chhiu̍h心')
        cover = audit[0]['covered_by'][0]
        self.assertEqual(text[cover['anchor_start']:cover['anchor_end']], 'chhiu̍h心')
        self.assertEqual(len(next(g for g in result if g['key'] == 'chhiu̍h')['occurrences']), 2)

    def test_tracked_mixed_cover_does_not_cross_boundaries_or_change_tones(self):
        text = 'liô 心。liô，心。lió心。liô--心。'
        groups = groups_for(text)
        records = [record('𠞭', 'liô', '1'), record('別', 'lió', '2')]
        _, stats = regroup(groups, {'test:1': text}, build_lookups(groups, records), {'liô心'})
        self.assertEqual(stats['suppressed_single_syllable_occurrences'], 0)

    def test_tracked_hyphenated_mixed_form_covers_unknown_neutral_single(self):
        text = '無飛--tńg-來。趕--tńg-來。--tńg。--tńg-去。--tńg -來。'
        groups = groups_for(text)
        result, stats = regroup(groups, {'test:1': text}, build_lookups(groups, []),
                                {'--tńg-來'})
        by_key = {g['key']: g for g in result}
        self.assertCountEqual([r['clause'] for r in by_key['--tńg']['occurrences']],
                              ['--tńg', '--tńg-去', '--tńg -來'])
        audit = stats['covered_single_syllable_audit']
        self.assertEqual(len(audit), 2)
        self.assertTrue(all(r['covered_by'][0]['tracked_written_forms'] == ['--tńg-來']
                            for r in audit))
        self.assertTrue(all(not r['covered_by'][0]['moe_match'] for r in audit))

    def test_tracked_hyphenated_mixed_form_covers_moe_single(self):
        text = 'liô-心。liô。'
        groups = groups_for(text)
        records = [record('𠞭', 'liô', '1')]
        result, stats = regroup(groups, {'test:1': text}, build_lookups(groups, records),
                                {'liô-心'})
        self.assertEqual([r['clause'] for r in result[0]['occurrences']], ['liô'])
        self.assertEqual(stats['suppressed_single_syllable_occurrences'], 1)

    def test_tracking_ab_does_not_hide_abc_or_overlapping_bc(self):
        text = '相ki器'
        groups = groups_for(text)
        records = [record('相機', 'siòng-ki', '1'), record('機器', 'ki-khì', '2'),
                   record('相機器', 'siòng-ki-khì', '3')]
        result, _ = regroup(groups, {'test:1':text}, build_lookups(groups, records))
        apply_final_exclusions(result, set(), {'相ki':[{'id':1,'preferred_form':'相ki'}]})
        by_key = {g['key']:g for g in result}
        self.assertEqual(by_key['相ki']['exclusion_reason'], 'tracked_preferred_form')
        self.assertIsNone(by_key['ki器']['exclusion_reason'])
        self.assertIsNone(by_key['相ki器']['exclusion_reason'])

    def test_multiple_romanized_pieces_match_full_word_and_overlap_once(self):
        text = 'hip相ki'
        groups = groups_for(text)
        records = [record('翕相', 'hip-siòng', '1'), record('相機', 'siòng-ki', '2'),
                   record('翕相機', 'hip-siòng-ki', '3')]
        result, stats = regroup(groups, {'test:1':text}, build_lookups(groups, records))
        by_key = {g['key']:g for g in result}
        self.assertEqual(set(by_key), {'hip相', '相ki', 'hip相ki'})
        self.assertEqual(len(by_key['hip相ki']['occurrences']), 1)
        self.assertEqual(len(by_key['hip相ki']['occurrences'][0]['source_triggers']), 2)
        self.assertGreater(stats['merged_trigger_emissions'], 0)

    def test_all_romanized_pieces_are_normalized_for_final_dedup(self):
        text = 'chiah甲chit'
        groups = groups_for(text, {'chiah':'tsiah','chit':'tsit'})
        records = [record('隻甲這', 'tsiah-kah-tsit', '1')]
        result, _ = regroup(groups, {'test:1':text}, build_lookups(groups, records))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['normalized_forms'], ['tsiah甲tsit'])
        apply_final_exclusions(result, set(), {'tsiah甲tsit':[{'id':1,'preferred_form':'tsiah甲tsit'}]})
        self.assertEqual(result[0]['exclusion_reason'],'tracked_preferred_form')

    def test_component_reading_cannot_hide_a_full_romanized_match(self):
        text = 'hip-siòng-ki'
        groups = groups_for(text)
        records = [record('翕相機', 'hip-siòng-ki', '1')]
        result, _ = regroup(groups, {'test:1':text}, build_lookups(groups, records))
        self.assertEqual(result[0]['normalized_tl'], 'hip-siòng-ki')
        apply_final_exclusions(result, set(), {'hip':[{'id':1,'preferred_form':'hip'}]})
        self.assertIsNone(result[0]['exclusion_reason'])

    def test_multi_piece_matches_do_not_cross_punctuation_or_excluded_context(self):
        records = [record('翕相機','hip-siòng-ki','1')]
        for text in ['hip相，ki', 'hip 相ki', 'hip相\nki']:
            groups = groups_for(text)
            result, _ = regroup(groups, {'test:1':text}, build_lookups(groups, records))
            self.assertNotIn(text, {g['key'] for g in result})
            self.assertFalse(any(g['moe_matches'] for g in result))
        text = 'hip相台文通訊BONG報ki'
        from harvest import occurrences
        doc = {'id':'test:1','text':text,'metadata':{'title':'fixture','original_url':'https://example.com'}}
        rows = list(occurrences(doc,6,['台文通訊BONG報']))
        groups = [{'key':r['key'],'normalized_tl':r['key'],'occurrences':[r]} for r in rows]
        result, _ = regroup(groups, {'test:1':text}, build_lookups(groups, records))
        self.assertFalse(any(g['moe_matches'] for g in result))

    def test_prefix_han_context_and_poj_lookup_keep_literal_source(self):
        text = '相ki。跤chiah。'
        groups = groups_for(text, {'chiah': 'tsiah'})
        related = build_lookups(groups, [record('相機', 'siòng-ki'), record('跤脊', 'kha-tsiah', '2')])
        result, _ = regroup(groups, {'test:1': text}, related)
        self.assertEqual({g['key'] for g in result}, {'相ki', '跤chiah'})

    def test_context_must_be_adjacent_and_alignment_must_be_unambiguous(self):
        for text in ['hip別相', 'hip，相', 'hip 相']:
            groups = groups_for(text)
            result, stats = regroup(groups, {'test:1': text}, build_lookups(groups, [record('翕相', 'hip-siòng')]))
            self.assertEqual(stats['promoted_occurrences'], 0)
        groups = groups_for('hip相')
        result, stats = regroup(groups, {'test:1': 'hip相'}, build_lookups(groups, [record('翕相', 'hip')]))
        self.assertEqual(stats['promoted_occurrences'], 0)

    def test_neutral_separator_is_not_folded_for_multisyllable_lookup(self):
        groups = groups_for('tsia--ê')
        lookups = build_lookups(groups, [record('這个', 'tsia-ê')])
        self.assertFalse(any(r['query_is_full'] for r in lookups['tsia--ê']))

    def test_neutral_prefix_matches_exactly_and_dedups_without_hiding_plain_ah(self):
        text = '好--ah。ah。--lah。'
        groups = groups_for(text)
        records = [record('矣', '--ah', '1'), record('啊', 'ah', '2'),
                   record('啦', '--lah', '3'), record('甲矣', 'kah--ah', '4')]
        lookups = build_lookups(groups, records)
        self.assertEqual({r['record_id'] for r in lookups['--ah']}, {'1', '4'})
        self.assertEqual({r['record_id'] for r in lookups['ah']}, {'2'})
        result, _ = regroup(groups, {'test:1': text}, lookups)
        apply_final_exclusions(result, set(), {'--ah': [{'id': 365, 'preferred_form': '--ah'}]})
        by_key = {g['key']: g for g in result}
        self.assertEqual(by_key['--ah']['exclusion_reason'], 'tracked_preferred_form')
        self.assertEqual(by_key['--ah']['moe_matches'][0]['reading'], '--ah')
        self.assertIsNone(by_key['ah']['exclusion_reason'])

    def test_curated_component_does_not_hide_a_new_mixed_expression(self):
        text = 'hip相'
        groups = groups_for(text)
        groups[0]['exclusion_reason'] = 'curated_single'
        related = build_lookups(groups, [record('翕相', 'hip-siòng')])
        result, _ = regroup(groups, {'test:1': text}, related)
        self.assertIsNone(result[0]['exclusion_reason'])

    def test_full_romanized_anchors_use_the_same_moe_match_for_all_lengths(self):
        text = 'hip。hip-siòng。'
        groups = groups_for(text)
        related = build_lookups(groups, [record('翕', 'hip'), record('翕相', 'hip-siòng', '2')])
        result, stats = regroup(groups, {'test:1': text}, related)
        self.assertEqual({g['kind'] for g in result}, {'moe_romanized'})
        self.assertEqual(stats['promoted_occurrences'], 0)
        self.assertEqual(stats['full_romanized_groups'], 2)
        self.assertTrue(all(g['moe_matches'] for g in result))

    def test_dedup_runs_on_final_mixed_anchor_not_known_romanized_component(self):
        text = 'pùn-sò桶。pùn-sò。'
        groups = groups_for(text)
        related = build_lookups(groups, [record('糞埽', 'pùn-sò'), record('糞埽桶', 'pùn-sò-tháng', '2')])
        result, _ = regroup(groups, {'test:1': text}, related)
        index = {'pùn-sò': [{'id': 1, 'preferred_form': 'pùn-sò'}]}
        apply_final_exclusions(result, set(), index)
        by_key = {g['key']: g for g in result}
        self.assertEqual(by_key['pùn-sò']['exclusion_reason'], 'tracked_preferred_form')
        self.assertIsNone(by_key['pùn-sò桶']['exclusion_reason'])
        index['pùn-sò桶'] = [{'id': 2, 'preferred_form': 'pùn-sò桶'}]
        apply_final_exclusions(result, set(), index)
        self.assertEqual(by_key['pùn-sò桶']['preferred_matches'][0]['id'], 2)

    def test_single_forms_dedup_normally_and_tones_remain_distinct(self):
        groups = groups_for('hip。híp。')
        apply_final_exclusions(groups, set(), {'hip': [{'id': 1, 'preferred_form': 'hip'}]})
        by_key = {g['key']: g for g in groups}
        self.assertEqual(by_key['hip']['exclusion_reason'], 'tracked_preferred_form')
        self.assertIsNone(by_key['híp']['exclusion_reason'])

    def test_mixed_tl_lookup_preserves_han_and_does_not_dedup_by_moe_headword(self):
        text = '跤chiah'
        groups = groups_for(text, {'chiah': 'tsiah'})
        related = build_lookups(groups, [record('跤脊', 'kha-tsiah')])
        result, _ = regroup(groups, {'test:1': text}, related)
        apply_final_exclusions(result, set(), {'跤脊': [{'id': 1, 'preferred_form': '跤脊'}]})
        self.assertIsNone(result[0]['exclusion_reason'])
        apply_final_exclusions(result, set(), {'跤tsiah': [{'id': 2, 'preferred_form': '跤tsiah'}]})
        self.assertEqual(result[0]['preferred_matches'][0]['id'], 2)


if __name__ == '__main__':
    unittest.main()
