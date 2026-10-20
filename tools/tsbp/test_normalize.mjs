import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

test('converter wrapper validates complete parts and preserves originals', () => {
  const root = process.env.CONVERTER_ROOT;
  assert.ok(root, 'Set CONVERTER_ROOT to the local taigi-converter checkout');
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'tsbp-normalization-'));
  try {
    const forms = ['hō͘', 'chit', 'chiâⁿ', 'ē-tàng', 'm̄--koh', 'VnmQ5Y',
      'chit-FAKE', 'BONG', 'Hu-lí-liàn', 'goa2', 'sio̍ng', 'tī', '--ah', '--lah', 'ah', '--chit', '--', 'ah-'];
    const input = path.join(temp, 'groups.json');
    const output = path.join(temp, 'normalization.json');
    fs.writeFileSync(input, JSON.stringify(forms.map(key => ({key}))));
    const script = fileURLToPath(new URL('./normalize_anchors.mjs', import.meta.url));
    execFileSync(process.execPath, [script, root, input, output]);
    const payload = JSON.parse(fs.readFileSync(output));
    const rows = Object.fromEntries(payload.records.map(row => [row.anchor, row]));
    assert.equal(rows['hō͘'].normalized_tl, 'hōo');
    assert.equal(rows.chit.normalized_tl, 'tsit');
    assert.equal(rows['chiâⁿ'].normalized_tl, 'tsiânn');
    assert.equal(rows['goa2'].normalized_tl, 'guá');
    assert.equal(rows['ē-tàng'].normalized_tl, 'ē-tàng');
    assert.equal(rows['m̄--koh'].normalized_tl, 'm̄--koh');
    assert.equal(rows['--ah'].normalized_tl, '--ah');
    assert.equal(rows['--lah'].normalized_tl, '--lah');
    assert.equal(rows['--chit'].normalized_tl, '--tsit');
    assert.equal(rows.ah.normalized_tl, 'ah');
    assert.equal(rows['--'].parseable, false);
    assert.equal(rows['ah-'].parseable, false);
    assert.equal(rows.VnmQ5Y.parseable, false);
    assert.equal(rows.VnmQ5Y.normalized_tl, null);
    assert.equal(rows['chit-FAKE'].parseable, false);
    assert.equal(rows['chit-FAKE'].normalized_tl, null);
    assert.equal(rows.BONG.parseable, true); // Parsing cannot establish language or meaning.
    assert.equal(rows['Hu-lí-liàn'].parseable, true);
    assert.equal(rows['sio̍ng'].normalized_tl, 'sio̍ng');
    assert.equal(rows['tī'].normalized_tl, 'tī');
    assert.ok(payload.converter.source_files.every(file => file.sha256.length === 64));
    assert.deepEqual(JSON.parse(fs.readFileSync(input)), forms.map(key => ({key})));
  } finally {
    fs.rmSync(temp, {recursive: true, force: true});
  }
});
