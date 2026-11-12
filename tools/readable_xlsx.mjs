// Optional workbook renderer. Source derivation stays in readable.py.
import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const require = createRequire(import.meta.url);
const { Workbook, SpreadsheetFile } = await import(pathToFileURL(require.resolve('@oai/artifact-tool')).href);
const output = path.resolve(process.argv[2] || 'dist/lkk-supplement');
const data = JSON.parse(await fs.readFile(path.join(output, 'lexicon-readable.json'), 'utf8'));
const values = [data.headers, ...data.rows.map(row => [...row])];
for (const row of values.slice(1)) {
  if (row[9]) row[9] = '教育部辭典';
  if (row[10]) row[10] = '用例來源';
}
const wb = Workbook.create();
const sh = wb.worksheets.add('字表');
const n = values.length;
sh.getRange(`A1:K${n}`).values = values;
// Preserve readings beginning with -- as text. Otherwise use spreadsheet defaults.
sh.getRange(`A1:K${n}`).setNumberFormat('@');
wb.recalculate();
console.log((await wb.inspect({ kind: 'table', range: '字表!A1:K4', tableMaxRows: 4,
  tableMaxCols: 11, maxChars: 1800 })).ndjson);
const preview = await wb.render({ sheetName: '字表', range: 'A1:K8', scale: 1, format: 'png' });
await fs.writeFile(path.join(output, 'preview.png'), new Uint8Array(await preview.arrayBuffer()));
const target = path.join(output, 'lexicon-readable.xlsx');
await (await SpreadsheetFile.exportXlsx(wb)).save(target);
execFileSync('python3', [fileURLToPath(new URL('./readable.py', import.meta.url)),
  '--out', output, '--link-xlsx', target], { stdio: 'inherit' });
console.log(target);
