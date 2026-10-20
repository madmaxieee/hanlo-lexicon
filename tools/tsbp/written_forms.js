// Match tools/lexicon.py written_form: preserve Han characters, vary romanized syllables.
function writtenForm(form, canonical, reading) {
  const han = char => /^[\p{Script=Han}〇々〆]$/u.test(char);
  const clean = text => text.normalize('NFC').trim().replace(/\s+/gu, ' ').toLowerCase();
  const significant = Array.from(form).filter(char => !/[\p{P}\p{Z}\p{M}]/u.test(char));
  if (significant.length && significant.every(han)) return form;
  if (!Array.from(form).some(han)) return clean(canonical) === clean(reading) ? form : reading;
  const units = [...form.matchAll(/[\p{Script=Han}〇々〆]|[\p{Script=Latin}][\p{Script=Latin}\p{M}\d'’]*/gu)];
  let rest = '', cursor = 0;
  for (const unit of units) {rest += form.slice(cursor, unit.index); cursor = unit.index + unit[0].length;}
  rest += form.slice(cursor);
  if (Array.from(rest).some(char => !/[\p{P}\p{Z}\p{M}]/u.test(char))) throw Error('Cannot align this mixed spelling; review it.');
  const primary = [...canonical.matchAll(/[^\s-]+/gu)], alternate = [...reading.matchAll(/[^\s-]+/gu)];
  if (units.length !== primary.length || primary.length !== alternate.length) throw Error('Syllable counts differ; review the alternate spelling.');
  let output = ''; cursor = 0;
  units.forEach((unit, index) => {
    const isHan = han(unit[0]);
    if (!isHan && clean(unit[0]) !== clean(primary[index][0])) throw Error('Romanized spelling does not match the filing reading.');
    const neutral = (tokens, text) => text.slice(index ? tokens[index-1].index + tokens[index-1][0].length : 0, tokens[index].index).includes('--');
    if (!isHan && neutral(primary, canonical) !== neutral(alternate, reading)) throw Error('Neutral-tone boundary changes; review the alternate spelling.');
    output += form.slice(cursor, unit.index) + (isHan ? unit[0] : alternate[index][0]);
    cursor = unit.index + unit[0].length;
  });
  return output + form.slice(cursor);
}
