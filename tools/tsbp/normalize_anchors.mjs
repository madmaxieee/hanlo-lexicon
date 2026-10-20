import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';

const [converterRoot, groupsPath, outputPath] = process.argv.slice(2);
if (!converterRoot || !groupsPath || !outputPath) {
  throw new Error('Usage: node normalize_anchors.mjs CONVERTER_ROOT GROUPS_JSON OUTPUT_JSON');
}
const {parseSyllable} = await import(pathToFileURL(path.join(converterRoot, 'src/phonetics.js')));
const {convert} = await import(pathToFileURL(path.join(converterRoot, 'src/index.js')));

export function analyze(anchor) {
  const errors = [];
  // Validate every whole hyphen-separated part, never a regex-matched substring.
  // A leading -- marks neutral tone; it is part of the written form.
  const body = anchor.startsWith('--') ? anchor.slice(2) : anchor;
  for (const syllable of body.split(/-+/)) {
    try { parseSyllable(syllable); }
    catch (error) { errors.push({syllable, error: error.message}); }
  }
  return {anchor, parseable: errors.length === 0,
    normalized_tl: errors.length ? null : convert(anchor, 'poj', 'tl').normalize('NFC').toLowerCase(),
    errors};
}

const groups = JSON.parse(fs.readFileSync(groupsPath, 'utf8'));
const records = groups.map(group => analyze(group.key));
const sourceFiles = ['package.json', ...fs.readdirSync(path.join(converterRoot, 'src'))
  .filter(name => name.endsWith('.js')).sort().map(name => 'src/' + name)];
const payload = {
  converter: {repository: 'https://github.com/taigikeyboard/taigi-converter',
    local_path: path.resolve(converterRoot),
    version: JSON.parse(fs.readFileSync(path.join(converterRoot, 'package.json'), 'utf8')).version,
    source_files: sourceFiles.map(file => ({file,
      sha256: createHash('sha256').update(fs.readFileSync(path.join(converterRoot, file))).digest('hex')})),
    policy: 'Whole-part parseSyllable gate, then convert(anchor, "poj", "tl"). Original anchors and groups retained. Parser compatibility is not lexical or semantic validation.'},
  records,
};
fs.writeFileSync(outputPath, JSON.stringify(payload, null, 2) + '\n');
console.log(JSON.stringify({groups: records.length,
  parseable: records.filter(row => row.parseable).length,
  unparseable: records.filter(row => !row.parseable).length,
  changed: records.filter(row => row.normalized_tl !== null && row.normalized_tl !== row.anchor).length}));
