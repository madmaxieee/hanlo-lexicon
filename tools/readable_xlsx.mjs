// Optional workbook renderer. Source derivation stays in readable.py.
import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const require = createRequire(import.meta.url);
const { Workbook, SpreadsheetFile } = await import(pathToFileURL(require.resolve('@oai/artifact-tool')).href);
const output = path.resolve(process.argv[2] || 'dist/readable');
const data = JSON.parse(await fs.readFile(path.join(output, 'lexicon-readable.json'), 'utf8'));
const values = [data.headers, ...data.rows.map(row => [...row])];
for (const row of values.slice(1)) {
  if (row[9]) row[9] = '教育部辭典';
  if (row[10]) row[10] = '來源文章';
}
const wb = Workbook.create();
const sh = wb.worksheets.add('字表');
const n = values.length;
sh.getRange(`A1:M${n}`).values = values;
sh.getRange(`A1:M${n}`).setNumberFormat('@');
sh.getRange(`A1:M${n}`).format.font = { name: 'Arial', size: 11 };
sh.getRange(`A1:M${n}`).format.wrapText = true;
sh.getRange(`A1:M${n}`).format.verticalAlignment = 'top';
const widths = [10, 24, 24, 24, 24, 24, 30, 72, 24, 16, 16, 42, 60];
widths.forEach((width, col) => sh.getRangeByIndexes(0, col, n, 1).format.columnWidth = width);
sh.getRange(`A2:M${n}`).format.autofitRows();
sh.getRange('A1:M1').format = { fill: '#354F52', font: { bold: true, color: '#FFFFFF' }, rowHeight: 32 };
sh.getRange(`J2:K${n}`).format.font = { color: '#1765A1', underline: 'single' };
sh.freezePanes.freezeRows(1);
sh.freezePanes.freezeColumns(2);
sh.tables.add(`A1:M${n}`, true, 'LexiconTable');
sh.showGridLines = false;
wb.recalculate();
console.log((await wb.inspect({ kind: 'table', range: '字表!A1:M4', tableMaxRows: 4,
  tableMaxCols: 13, maxChars: 1800 })).ndjson);
const preview = await wb.render({ sheetName: '字表', range: 'A1:M8', scale: 1, format: 'png' });
await fs.writeFile(path.join(output, 'preview.png'), new Uint8Array(await preview.arrayBuffer()));
const target = path.join(output, 'lexicon-readable.xlsx');
await (await SpreadsheetFile.exportXlsx(wb)).save(target);
execFileSync('python3', [fileURLToPath(new URL('./readable.py', import.meta.url)),
  '--out', output, '--link-xlsx', target], { stdio: 'inherit' });
console.log(target);
