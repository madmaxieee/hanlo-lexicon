"""LKK-only spelling coverage proofs for the supplemental reader export."""
from collections import defaultdict

import hanlo_combos as combos
import lexicon as lx


class LKKCoverage:
    def __init__(self, lkk, records):
        self.pairs = set()
        self.mappings = defaultdict(lambda: defaultdict(list))
        self.skipped = []
        dictionary = defaultdict(list)
        for record in records:
            for form in [record['headword'], *record.get('variant_forms', [])]:
                dictionary[lx.annotation_key(form)].append(record)
        for snapshot, (_, rows) in sorted(lkk.items()):
            for row, cells in enumerate(rows[1:], 2):
                form, reading = cells[1:3]
                if not form or not reading:
                    continue
                self.pairs.add((lx.key(form), lx.key(reading)))
                source = {'snapshot': snapshot, 'row': row}
                try:
                    syllables = combos.reading_units(reading)
                    preferred = combos.written_units(form, syllables)
                except combos.AlignmentError as error:
                    self.skipped.append({'source': source, 'reason': str(error)})
                    continue
                references = [(form, source)]
                if cells[5]:
                    references.append((cells[5], source))
                # Exact whole-word spelling AND reading only; never a homophone join.
                for record in dictionary[lx.annotation_key(form)]:
                    if lx.key(reading) in lx.reading_keys(record['reading']):
                        references.append((lx.annotation_key(record['headword']), record['source']))
                for reference, ref_source in references:
                    try:
                        units = combos.written_units(reference, syllables)
                    except combos.AlignmentError:
                        continue
                    for unit, output, syllable in zip(units, preferred, syllables):
                        if unit['kind'] != 'hanji':
                            continue
                        pair = (unit['text'], combos.tl_key(syllable))
                        choice = (output['kind'], lx.key(output['text']))
                        proof = {'lkk_source': source, 'hanji_source': ref_source}
                        if proof not in self.mappings[pair][choice]:
                            self.mappings[pair][choice].append(proof)

    def original(self, entry, lkk):
        return any(s.get('snapshot') in lkk for s in entry['sources']) or (
            lx.key(entry['preferred_form']), lx.key(entry['canonical_tl'])) in self.pairs

    def reconstructed(self, entry, references):
        """Every exported reading/spelling needs a complete, conflict-free proof."""
        proofs = []
        try:
            spellings = lx.spelling_readings(entry)
        except lx.Error:
            return None
        for form, reading in spellings:
            try:
                syllables = combos.reading_units(reading)
            except combos.AlignmentError:
                return None
            found = None
            for reference in sorted(set(references)):
                try:
                    units = combos.written_units(lx.annotation_key(reference), syllables)
                except combos.AlignmentError:
                    continue
                if any(u['kind'] != 'hanji' for u in units):
                    continue
                rendered, previous_roman, positions = '', False, []
                for unit, syllable in zip(units, syllables):
                    pair = (unit['text'], combos.tl_key(syllable))
                    outputs = self.mappings.get(pair, {})
                    if len(outputs) != 1:
                        break
                    (kind, token), sources = next(iter(outputs.items()))
                    roman = kind == 'romanized'
                    if syllable['neutral']:
                        rendered += '--'
                    elif roman and previous_roman:
                        rendered += '-'
                    rendered += token
                    previous_roman = roman
                    positions.append({'hanji': pair[0], 'canonical_tl': pair[1],
                                      'output': token, 'sources': sources})
                else:
                    if lx.key(rendered) == lx.key(form):
                        found = {'form': form, 'reading': reading, 'reference': reference,
                                 'positions': positions}
                        break
            if found is None:
                return None
            proofs.append(found)
        return proofs or None
