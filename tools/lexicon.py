#!/usr/bin/env python3
"""Han-Lo maintenance with a pinned first-use dictionary cache. Python 3.11+."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import tomllib
import unicodedata as ud
from urllib.parse import urlsplit
from urllib.request import urlopen
import xml.etree.ElementTree as ET
import zipfile


class Error(ValueError):
    """A failed check; commands report it without a traceback."""


INITIALS = ('tsh', 'ph', 'th', 'kh', 'ts', 'ng', 'p', 'm', 'b', 't', 'n', 'l', 'k', 'g', 's', 'j', 'h')
TONE_MARKS = set('\u0301\u0300\u0302\u030c\u0304\u030d\u030b')
T = '{urn:oasis:names:tc:opendocument:xmlns:table:1.0}'
X = '{urn:oasis:names:tc:opendocument:xmlns:text:1.0}'
O = '{urn:oasis:names:tc:opendocument:xmlns:office:1.0}'
HEADWORD_SHEETS = {'詞目', '又唸作', '合音唸作', '俗唸作', '語音差異', '詞彙比較', '名', '姓'}


def load_toml(path):
    try:
        return tomllib.loads(path.read_text(encoding='utf-8'))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise Error(f'{path}: {exc}') from exc


def key(text):
    """Search only: Unicode/case/whitespace normalization; retain tone and hyphens."""
    return ud.normalize('NFC', ' '.join(text.split())).casefold()


def bucket(reading):
    # Initial inventory and syllabic nasals: TaigiKeyboard phonetics reference
    # sections 2 and 9, and taigi-converter/src/tables.js. This files records;
    # it does not validate/convert pronunciation or infer a missing reading.
    first = re.split(r'[-\s]', reading.lstrip('-'), maxsplit=1)[0]
    bare = ''.join(c for c in ud.normalize('NFD', first.casefold()) if c not in TONE_MARKS)
    if bare in {'m', 'mh', 'ng', 'ngh'} or bare[:1] in 'aeiou' and bare:
        return 'zero'
    for initial in INITIALS:
        if bare.startswith(initial):
            return initial
    raise Error(f'Cannot file TL reading {reading!r}; supply a verified canonical TL reading.')


def subbucket(reading):
    """File by onset plus the full vowel sequence, excluding tones and codas."""
    initial = bucket(reading)
    first = re.split(r'[-\s]', reading.lstrip('-'), maxsplit=1)[0]
    bare = ''.join(c for c in ud.normalize('NFD', first.casefold()) if c not in TONE_MARKS)
    onset = '' if initial == 'zero' else initial
    nucleus = re.match(r'[aeiou]+|ng|m', bare[len(onset):])
    if nucleus is None:
        raise Error(f'Cannot file TL reading {reading!r}; supply a verified canonical TL reading.')
    return onset + nucleus.group()


def filename(form, entry_id):
    # Escape portability hazards, including the escape character itself.
    form = ud.normalize('NFC', form)
    unsafe = '<>:"/\\|?*%'
    escaped = ''.join(f'%{ord(c):02X}' if c in unsafe or ord(c) < 32 or ord(c) == 127 else c for c in form)
    return f'{escaped}--{entry_id:06d}.toml'


def entry_path(root, entry):
    reading = entry['canonical_tl']
    return root / 'entries' / bucket(reading) / subbucket(reading) / filename(entry['preferred_form'], entry['id'])


def entry_files(root):
    """Discover every record, including old paths awaiting format migration."""
    return sorted((root / 'entries').rglob('*.toml'))


def canonical_entry(entry):
    result = dict(entry)
    for field in ('alternate_readings', 'moe_forms', 'hanji_forms'):
        if field in result:
            result[field] = sorted(result[field], key=lambda text: (key(text), text))
    result['sources'] = sorted(result['sources'], key=lambda source: json.dumps(source, ensure_ascii=False, sort_keys=True))
    return result


def render(entry):
    """Emit the supported entry schema, never arbitrary TOML constructs."""
    entry = canonical_entry(entry)
    quote = lambda value: json.dumps(value, ensure_ascii=False, allow_nan=False)
    lines = [f'{name} = {quote(entry[name])}' for name in sorted(entry) if name != 'sources']
    for source in entry['sources']:
        lines.extend(['', '[[sources]]'])
        lines.extend(f'{name} = {quote(source[name])}' for name in sorted(source))
    return '\n'.join(lines) + '\n'


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text.encode('utf-8') if isinstance(text, str) else text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


@contextmanager
def writer_lock(root):
    lock = root / '.lexicon.lock'
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise Error('Another writer holds .lexicon.lock. If a process crashed, confirm it stopped before removing the lock.') from exc
    try:
        yield
    finally:
        lock.rmdir()


def validate_schema(value, rule, location='entry'):
    """Evaluate all assertion keywords used by our small JSON Schema."""
    supported = {'$schema', 'title', 'description', 'type', 'const', 'enum', 'minimum', 'minLength', 'pattern', 'minItems', 'uniqueItems', 'required', 'properties', 'additionalProperties', 'items', 'anyOf'}
    if set(rule) - supported:
        raise Error(f'Unsupported schema keywords: {sorted(set(rule) - supported)}')
    def require(condition, message):
        if not condition:
            raise Error(f'{location}: {message}')
    if 'anyOf' in rule:
        errors = []
        for choice in rule['anyOf']:
            try:
                validate_schema(value, choice, location)
                break
            except Error as exc:
                errors.append(str(exc))
        else:
            raise Error(f'{location}: no supported reference shape ({"; ".join(errors)})')
    if 'const' in rule:
        require(type(value) is type(rule['const']) and value == rule['const'], 'unexpected constant')
    if 'enum' in rule:
        require(value in rule['enum'], 'unexpected value')
    kind = rule.get('type')
    if kind:
        require(type(value) is {'object': dict, 'array': list, 'string': str, 'integer': int, 'boolean': bool}[kind], f'expected {kind}')
    if kind == 'object':
        require(set(rule.get('required', [])) <= value.keys(), 'missing required fields')
        properties = rule.get('properties', {})
        for name, item in value.items():
            if name in properties:
                validate_schema(item, properties[name], f'{location}.{name}')
            else:
                require(rule.get('additionalProperties', True) is not False, f'unexpected field {name}')
    elif kind == 'array':
        require(len(value) >= rule.get('minItems', 0), 'array too short')
        if rule.get('uniqueItems'):
            require(len({json.dumps(item, sort_keys=True) for item in value}) == len(value), 'duplicate array items')
        for i, item in enumerate(value):
            validate_schema(item, rule['items'], f'{location}[{i}]')
    elif kind == 'string':
        require(bool(value.strip()) and len(value) >= rule.get('minLength', 0), 'empty string')
        if 'pattern' in rule:
            require(re.search(rule['pattern'], value) is not None, 'invalid string pattern')
        require(ud.normalize('NFC', value) == value, 'use NFC Unicode')
    elif kind == 'integer':
        require(value >= rule.get('minimum', value), 'integer too small')


def verify_entry(root, entry, lookup_only=False):
    schema = json.loads((root / 'schema/entry.schema.json').read_text())
    if lookup_only:
        schema['required'].remove('sources')
    validate_schema(entry, schema)
    subbucket(entry['canonical_tl'])
    readings = [entry['canonical_tl'], *entry['alternate_readings']]
    if len({key(reading) for reading in readings}) != len(readings):
        raise Error('Duplicate primary/alternate readings after normalization.')
    if len({key(form) for form in entry['moe_forms']}) != len(entry['moe_forms']):
        raise Error('Duplicate MOE forms after normalization.')
    hanji = entry.get('hanji_forms', [])
    if len({key(form) for form in hanji}) != len(hanji):
        raise Error('Duplicate Hanji forms after normalization.')
    if any(not is_hanji(form) or '\n' in form or '\r' in form for form in hanji):
        raise Error('Hanji forms must contain only Hanji and separators on one line.')
    if any('\n' in entry[field] or '\r' in entry[field] for field in ('preferred_form', 'canonical_tl')):
        raise Error('Written forms and canonical readings must fit on one line.')
    if len(filename(entry['preferred_form'], entry['id']).encode('utf-8')) > 240:
        raise Error('Preferred form is too long for a portable filename.')
    for source in entry.get('sources', []):
        if ('url' in source) == ('snapshot' in source):
            raise Error('Cite either a snapshot/row or a URL/locator, not both.')
        if 'url' in source and urlsplit(source['url']).scheme not in ('http', 'https'):
            raise Error('External citations require an HTTP(S) source URL.')


def entries(root):
    result, ids, paths, senses = [], set(), set(), set()
    for path in entry_files(root):
        entry = load_toml(path)
        verify_entry(root, entry)
        if entry['id'] in ids:
            raise Error(f'Duplicate ID {entry["id"]}.')
        ids.add(entry['id'])
        identity = (key(entry['preferred_form']), key(entry['canonical_tl']), key(entry.get('identity_note', '')))
        if identity in senses:
            raise Error(f'Duplicate lexical identity at {path}.')
        senses.add(identity)
        target = key(str(entry_path(root, entry)))
        if target in paths:
            raise Error(f'Filename collision at {path}.')
        paths.add(target)
        result.append((path, entry))
    return result


def entry_keys(entry):
    return ({key(entry['preferred_form']), *(key(form) for form in entry['moe_forms']),
             *(key(form) for form in entry.get('hanji_forms', []))},
            {key(entry['canonical_tl']), *(key(reading) for reading in entry['alternate_readings'])})


class KeyIndex:
    """Ordered exact matches, retaining all homographs and original source rows."""

    def __init__(self):
        self.rows, self.forms, self.readings = [], {}, {}

    def add(self, row, forms, readings):
        number = len(self.rows)
        self.rows.append(row)
        for mapping, values in ((self.forms, forms), (self.readings, readings)):
            for value in values:
                mapping.setdefault(value, set()).add(number)

    def matching(self, forms, readings):
        numbers = set()
        for mapping, values in ((self.forms, forms), (self.readings, readings)):
            for value in values:
                numbers.update(mapping.get(value, ()))
        return [self.rows[number] for number in sorted(numbers)]


class LookupIndex:
    """Build once per batch; extend the entry index after each planned addition."""

    def __init__(self, current, evidence):
        self.current, self.lkk, self.moe = KeyIndex(), KeyIndex(), KeyIndex()
        for row in current:
            self.add_entry(*row)
        for snapshot, (_, rows) in evidence[0].items():
            for number, row in enumerate(rows[1:], 2):
                readings = reading_keys(row[2]) | reading_keys(row[4])
                if row[1]:
                    readings.add(key(row[1]))
                self.lkk.add((snapshot, number, row), {key(row[1]), key(row[5])}, readings)
        for record in evidence[1][2]:
            self.moe.add(record,
                         {annotation_key(record['headword']),
                          *(annotation_key(form) for form in record['variant_forms'])},
                         reading_keys(record['reading']))

    def add_entry(self, path, entry):
        self.current.add((path, entry), *entry_keys(entry))


def query_entries(root, forms=(), readings=(), entry_id=None, use_cache=True):
    """Disposable per-workspace SQLite index. TOML and full validation stay authoritative.

    Every query discovers files and stats them, including ctime and inode, so
    edits, replacements, renames and deletions invalidate their cached records.
    Cached records never participate in allocation or repository validation.
    """
    def matches(current):
        if entry_id is not None:
            return [(path, entry) for path, entry in current if entry['id'] == entry_id]
        return [(path, entry) for path, entry in current
                if set(forms) & entry_keys(entry)[0] or set(readings) & entry_keys(entry)[1]]

    if not use_cache:
        return matches(entries(root))
    database = root / '.cache/entries.sqlite3'
    connection = None
    try:
        database.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(database, timeout=0.2)
        connection.execute('PRAGMA foreign_keys = ON')
        connection.executescript('''
            CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS entries (
                path TEXT PRIMARY KEY, stamp TEXT NOT NULL, payload TEXT NOT NULL,
                id INTEGER NOT NULL, identity TEXT NOT NULL, target TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS keys (
                path TEXT NOT NULL REFERENCES entries(path) ON DELETE CASCADE,
                kind TEXT NOT NULL, value TEXT NOT NULL, PRIMARY KEY(path, kind, value));
            CREATE INDEX IF NOT EXISTS lookup_keys ON keys(kind, value);
            CREATE INDEX IF NOT EXISTS entry_ids ON entries(id);
            CREATE INDEX IF NOT EXISTS entry_identities ON entries(identity);
            CREATE INDEX IF NOT EXISTS entry_targets ON entries(target);
        ''')
        fingerprint = hashlib.sha256(
            b'entry-index-v1\0' + str(root.resolve()).encode() +
            (root / 'schema/entry.schema.json').read_bytes() + Path(__file__).read_bytes()).hexdigest()
        with connection:
            connection.execute('BEGIN IMMEDIATE')
            stored = connection.execute("SELECT value FROM metadata WHERE key = 'fingerprint'").fetchone()
            if stored != (fingerprint,):
                connection.execute('DELETE FROM entries')
                connection.execute("INSERT OR REPLACE INTO metadata VALUES ('fingerprint', ?)", (fingerprint,))
            previous = dict(connection.execute('SELECT path, stamp FROM entries'))
            present = set()
            for path in entry_files(root):
                relative = str(path.relative_to(root))
                present.add(relative)
                stat = path.stat()
                stamp = json.dumps([stat.st_dev, stat.st_ino, stat.st_size,
                                    stat.st_mtime_ns, stat.st_ctime_ns])
                if previous.get(relative) == stamp:
                    continue
                entry = load_toml(path)
                verify_entry(root, entry)
                identity = json.dumps([key(entry['preferred_form']), key(entry['canonical_tl']),
                                       key(entry.get('identity_note', ''))])
                connection.execute('DELETE FROM entries WHERE path = ?', (relative,))
                connection.execute('INSERT INTO entries VALUES (?, ?, ?, ?, ?, ?)',
                                   (relative, stamp, json.dumps(entry, ensure_ascii=False), entry['id'],
                                    identity, key(str(entry_path(root, entry)))))
                for kind, values in zip(('form', 'reading'), entry_keys(entry)):
                    connection.executemany('INSERT INTO keys VALUES (?, ?, ?)',
                                           [(relative, kind, value) for value in values])
            connection.executemany('DELETE FROM entries WHERE path = ?',
                                   [(path,) for path in previous.keys() - present])
            for column, message in (('id', 'Duplicate ID'), ('identity', 'Duplicate lexical identity'),
                                    ('target', 'Filename collision')):
                duplicate = connection.execute(
                    f'SELECT {column} FROM entries GROUP BY {column} HAVING count(*) > 1 LIMIT 1').fetchone()
                if duplicate:
                    raise Error(f'{message}: {duplicate[0]}.')
            if entry_id is not None:
                rows = connection.execute('SELECT path, payload FROM entries WHERE id = ? ORDER BY path',
                                          (entry_id,)).fetchall()
            else:
                values = [('form', value) for value in forms] + [('reading', value) for value in readings]
                if not values:
                    return []
                conditions = ' OR '.join('(kind = ? AND value = ?)' for _ in values)
                rows = connection.execute(
                    'SELECT path, payload FROM entries WHERE path IN '
                    f'(SELECT path FROM keys WHERE {conditions}) ORDER BY path',
                    [value for pair in values for value in pair]).fetchall()
            return sorted([(root / path, json.loads(payload)) for path, payload in rows],
                          key=lambda item: item[0])
    except Error:
        raise
    except (sqlite3.Error, OSError, ValueError):
        # An unavailable/corrupt cache must never hide TOML errors or block lookup.
        return matches(entries(root))
    finally:
        if connection is not None:
            connection.close()


def next_id(root, current):
    state = load_toml(root / 'id-sequence.toml')
    value = state.get('next_id')
    if type(value) is not int or value <= max((entry['id'] for _, entry in current), default=0):
        raise Error('id-sequence.toml must contain next_id greater than every allocated entry ID.')
    return value


def ods_sheets(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        doc = ET.fromstring(archive.read('content.xml'))
    sheets = {}
    for table in doc.iter(T + 'table'):
        rows, row_number = [], 1
        for row in table.iter(T + 'table-row'):
            cells = []
            for cell in row:
                if cell.tag not in (T + 'table-cell', T + 'covered-table-cell'):
                    continue
                text = '\n'.join(''.join(p.itertext()) for p in cell.findall(X + 'p'))
                text = text or cell.get(O + 'value', '')
                count = int(cell.get(T + 'number-columns-repeated', '1'))
                if len(cells) < 256:
                    cells.extend([text] * min(count, 256 - len(cells)))
            repeated = int(row.get(T + 'number-rows-repeated', '1'))
            if any(cells):
                if repeated > 100000:
                    raise Error('ODS repeats too many nonempty rows.')
                rows.extend((row_number + i, cells) for i in range(repeated))
            row_number += repeated
        sheets[table.get(T + 'name')] = rows
    return sheets


def annotation_key(text):
    # Strip explicit MOE annotations only for matching, preserving original output.
    return key(re.sub(r'【[^】]*】', '', text))


def reading_keys(text):
    return {annotation_key(part) for part in re.split(r'[,，、/]', text) if part.strip()}


def cached_moe(root):
    pin = load_toml(root / 'references/moe.toml')
    if not re.fullmatch('[0-9a-f]{64}', pin['sha256']):
        raise Error('Invalid MOE SHA-256 pin.')
    path = root / '.cache/dictionaries/moe' / pin['sha256'] / 'kautian.ods'
    if path.exists():
        raw = path.read_bytes()
    else:
        url = pin['download_url']
        revision = pin['revision']
        expected = f'https://raw.githubusercontent.com/taigikeyboard/taigikeyboard/{revision}/{pin["source_path"]}'
        if not re.fullmatch('[0-9a-f]{40}', revision) or url != expected:
            raise Error('MOE download must use the pinned TaigiKeyboard GitHub revision and source path.')
        try:
            with urlopen(url, timeout=30) as response:
                raw = response.read(64 * 1024 * 1024 + 1)
        except OSError as exc:
            raise Error(f'Cannot download pinned MOE dictionary; retry when GitHub is reachable: {exc}') from exc
        if len(raw) > 64 * 1024 * 1024:
            raise Error('MOE download exceeds the 64 MiB limit.')
        if hashlib.sha256(raw).hexdigest() != pin['sha256']:
            raise Error('Downloaded MOE checksum mismatch; no cache file was saved.')
        atomic_write(path, raw)
    if hashlib.sha256(raw).hexdigest() != pin['sha256']:
        raise Error('Cached MOE checksum mismatch. Remove the corrupt cache file to download the pinned copy again; do not change the pin.')
    return pin, path, raw


def moe_data(root):
    pin, _, raw = cached_moe(root)
    if pin['format'] != 'moe-ods':
        raise Error('Unsupported MOE source format.')
    sheets = ods_sheets(raw)
    if '詞目' not in sheets:
        raise Error('MOE ODS is missing the headword sheet.')
    records, definitions, variants = [], {}, {}
    for name, rows in sheets.items():
        if not rows:
            continue
        header = rows[0][1]
        for row_number, cells in rows[1:]:
            record = dict(zip(header, cells))
            if name == '義項':
                definitions.setdefault(record.get('詞目id', ''), []).append(record.get('解說', ''))
            elif name == '異用字':
                variants.setdefault(annotation_key(record.get('漢字', '')), []).append(record.get('異用字', ''))
            elif name in HEADWORD_SHEETS and '漢字' in record and ('羅馬字' in record or name == '語音差異'):
                columns = [column for column in header if column not in ('詞目id', '漢字')] if name == '語音差異' else ['羅馬字']
                for column in columns:
                    if record.get(column):
                        records.append({
                            'headword': record['漢字'], 'reading': record[column],
                            'record_id': record.get('詞目id', ''), 'column': column,
                            'source': {'snapshot': pin['id'], 'sheet': name, 'row': row_number},
                        })
    for record in records:
        record['definitions'] = definitions.get(record['record_id'], [])
        record['variant_forms'] = variants.get(annotation_key(record['headword']), [])
    return pin, sheets, records


def lkk_data(root):
    result = {}
    for path in sorted((root / 'sources').glob('*/metadata.toml')):
        meta = load_toml(path)
        relative = Path(meta['file'])
        if relative.is_absolute() or '..' in relative.parts:
            raise Error('Source files must remain inside their snapshot directory.')
        raw = (path.parent / relative).read_bytes()
        if hashlib.sha256(raw).hexdigest() != meta['sha256']:
            raise Error(f'Source checksum mismatch: {meta["id"]}.')
        if meta.get('format') != 'tsv':
            raise Error(f'Unsupported original source format: {meta.get("format")}.')
        rows = list(csv.reader(io.StringIO(raw.decode('utf-8-sig'), newline=''), delimiter='\t'))
        if not rows or rows[0][1:3] != ['建議用字', '音讀']:
            raise Error('Unrecognized LKK TSV columns.')
        if any(len(row) != 9 for row in rows):
            raise Error('LKK source must have exactly nine columns.')
        if meta['id'] in result:
            raise Error('Duplicate snapshot ID.')
        result[meta['id']] = (meta, rows)
    return result


def verify_sources(entry, lkk, moe):
    pin, sheets, _ = moe if moe else (None, None, None)
    for source in entry['sources']:
        if 'url' in source:
            continue
        if source['snapshot'] in lkk:
            meta, rows = lkk[source['snapshot']]
            if source['row'] <= 1 or source['row'] > len(rows) or not rows[source['row'] - 1][1].strip():
                raise Error('LKK citation does not identify a nonempty vocabulary row.')
            if 'sheet' in source and source['sheet'] != meta.get('sheet'):
                raise Error('Incorrect LKK sheet name.')
        elif pin and source['snapshot'] == pin['id']:
            if source.get('sheet') not in sheets:
                raise Error('MOE citation requires a valid sheet name.')
            rows = sheets[source['sheet']]
            if not any(number == source['row'] for number, _ in rows[1:]):
                raise Error('MOE citation does not identify a data row.')
        else:
            raise Error(f'Unknown or unavailable source snapshot: {source["snapshot"]}.')


def check(root, candidate, current=None, evidence=None, lookup=None):
    verify_entry(root, dict(candidate, id=candidate.get('id', 1)), lookup_only=True)
    lkk, moe = evidence if evidence else (lkk_data(root), moe_data(root))
    preferred = key(candidate['preferred_form'])
    forms = {preferred, *(key(form) for form in candidate['moe_forms']),
             *(key(form) for form in candidate.get('hanji_forms', []))}
    readings = {key(candidate['canonical_tl']), *(key(reading) for reading in candidate['alternate_readings'])}
    if lookup is not None:
        current = sorted(lookup.current.matching(forms, readings), key=lambda item: item[0])
    elif current is None:
        current = query_entries(root, forms, readings)
    existing = []
    for path, entry in current:
        same_form = key(entry['preferred_form']) == preferred
        shared_reading = bool(readings & {key(entry['canonical_tl']), *(key(reading) for reading in entry['alternate_readings'])})
        related_forms = {key(entry['preferred_form']), *(key(form) for form in entry['moe_forms']),
                         *(key(form) for form in entry.get('hanji_forms', []))}
        if same_form or shared_reading or forms & related_forms:
            exact = same_form and key(entry['canonical_tl']) == key(candidate['canonical_tl'])
            existing.append({'id': entry['id'], 'path': str(path.relative_to(root)), 'preferred_form': entry['preferred_form'], 'canonical_tl': entry['canonical_tl'], 'identity_note': entry.get('identity_note'), 'match': 'exact_pair' if exact else 'alias_pair' if same_form and shared_reading else 'same_form' if same_form else 'related_reading_or_form'})
    lkk_matches = []
    lkk_rows = lookup.lkk.matching(forms, readings) if lookup is not None else (
        (snapshot, number, row) for snapshot, (_, rows) in lkk.items()
        for number, row in enumerate(rows[1:], 2))
    for snapshot_id, row_number, row in lkk_rows:
        source_readings = reading_keys(row[2]) | reading_keys(row[4])
        if row[1]:
            source_readings.add(key(row[1]))
        if key(row[1]) in forms or key(row[5]) in forms or readings & source_readings:
            lkk_matches.append({'preferred_form': row[1], 'reading': row[2], 'alternate_readings': row[4], 'moe_form': row[5], 'context': row[6], 'source': {'snapshot': snapshot_id, 'row': row_number}})
    moe_matches = []
    for record in lookup.moe.matching(forms, readings) if lookup is not None else moe[2]:
        form_match = bool(forms & {annotation_key(record['headword']), *(annotation_key(form) for form in record['variant_forms'])})
        reading_match = bool(readings & reading_keys(record['reading']))
        if form_match or reading_match:
            moe_matches.append(dict(record, match='form_and_reading' if form_match and reading_match else 'same_form' if form_match else 'same_reading'))
    return {'existing_entries': existing, 'lkk_matches': lkk_matches, 'moe_matches': moe_matches, 'moe_checked': {'snapshot': moe[0]['id'], 'sha256': moe[0]['sha256']}}


def normalize_request(data):
    if not isinstance(data, dict) or 'id' in data:
        raise Error('Requests must be an object without an ID; add allocates it.')
    def nfc(value):
        if isinstance(value, str):
            return ud.normalize('NFC', value)
        if isinstance(value, list):
            return [nfc(item) for item in value]
        if isinstance(value, dict):
            return {name: nfc(item) for name, item in value.items()}
        return value
    data = nfc(data)
    return {'schema_version': 1, 'alternate_readings': [], 'moe_forms': [], 'review_status': 'imported', **data}


def request_data(path):
    return normalize_request(json.loads(path.read_text(encoding='utf-8')))


def batch_requests(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, list) or not data:
        raise Error('A batch must be a nonempty JSON array of requests without IDs.')
    return [normalize_request(item) for item in data]


def validate(root, formatting=True, current=None, evidence=None):
    current = entries(root) if current is None else current
    next_id(root, current)
    lkk = evidence[0] if evidence is not None else lkk_data(root)
    # Pure repository validation needs no MOE file unless an entry cites it.
    ids = {source['snapshot'] for _, entry in current for source in entry['sources'] if 'snapshot' in source}
    moe = (evidence[1] if evidence is not None else moe_data(root)) if ids - lkk.keys() else None
    for path, entry in current:
        verify_sources(entry, lkk, moe)
        if formatting and (path != entry_path(root, entry) or path.read_text() != render(entry)):
            raise Error(f'{path.relative_to(root)}: run format to canonicalize content and filename.')
    # Same-pair homographs require an explicit identity note on each additional word.
    groups = {}
    for _, entry in sorted(current, key=lambda item: item[1]['id']):
        pair = key(entry['preferred_form']), key(entry['canonical_tl'])
        if pair in groups and not entry.get('identity_note'):
            raise Error('Additional homographs need a distinct identity_note.')
        groups[pair] = True
    return {'entries': len(current), 'next_id': next_id(root, current), 'sources': len(lkk)}


def add_batch(root, candidates, dry_run=False):
    """Preflight the complete batch under one writer lock before reserving IDs.

    Existing data and checksum-verified dictionaries are loaded once. Every
    candidate is checked against existing entries and earlier batch candidates.
    I/O failures may leave a partial import, but all reserved IDs remain spent.
    """
    if not candidates:
        raise Error('A batch must contain at least one request.')
    with writer_lock(root):
        current = entries(root)
        evidence = lkk_data(root), moe_data(root)
        validate(root, current=current, evidence=evidence)
        lookup = LookupIndex(current, evidence)
        first_id = next_id(root, current)
        planned = []
        for number, candidate in enumerate(candidates, 1):
            try:
                entry = dict(candidate, id=first_id + len(planned))
                verify_entry(root, entry)
                report = check(root, candidate, current, evidence, lookup)
                for match in report['existing_entries']:
                    if match['match'] in ('exact_pair', 'alias_pair'):
                        note = key(candidate.get('identity_note', ''))
                        if not note or note == key(match.get('identity_note') or ''):
                            raise Error(f'Existing entry {match["id"]} already covers this form/reading. '
                                        'Edit it, or explain a distinct word in identity_note.')
                verify_sources(candidate, *evidence)
                target = entry_path(root, entry)
                if target.exists():
                    raise Error(f'Refusing to overwrite {target}.')
                planned.append((target, entry, report))
                current.append((target, entry))
                lookup.add_entry(target, entry)
            except (Error, KeyError, TypeError) as exc:
                raise Error(f'Batch request {number}: {exc}') from exc
        if not dry_run:
            atomic_write(root / 'id-sequence.toml', f'next_id = {first_id + len(planned)}\n')
            for target, entry, _ in planned:
                atomic_write(target, render(entry))
        results = [{'created': str(target.relative_to(root)), 'id': entry['id'], 'checks': report}
                   for target, entry, report in planned]
        return {'dry_run': dry_run, 'reserved': not dry_run, 'count': len(results),
                'first_id': first_id, 'last_id': first_id + len(results) - 1, 'results': results}


def is_hanji(form):
    """Ignore separators and marks, but require every remaining character to be Hanji."""
    characters = [char for char in form if ud.category(char)[0] not in {'P', 'Z', 'M'}]
    return bool(characters) and all(
        ud.name(char, '').startswith(('CJK UNIFIED IDEOGRAPH-', 'CJK COMPATIBILITY IDEOGRAPH-'))
        or char in '〇々〆'
        for char in characters
    )


def written_form(form, canonical, reading):
    """Render a sourced alternate in the same Han/romanized writing pattern.

    Mixed forms require one Han character or romanized syllable per reading
    syllable. Fail on contractions or mismatched romanization, rather than
    silently replacing the Han characters with a full romanized reading.
    """
    if is_hanji(form):
        return form
    if not any(is_hanji(char) for char in form):
        return form if key(canonical) == key(reading) else reading
    units = []
    i = 0
    while i < len(form):
        start = i
        char = form[i]
        if is_hanji(char):
            units.append((i, i + 1, True))
            i += 1
        elif 'LATIN' in ud.name(char, ''):
            i += 1
            while i < len(form) and ('LATIN' in ud.name(form[i], '')
                                    or ud.category(form[i]).startswith('M')
                                    or form[i].isdigit() or form[i] in "'’"):
                i += 1
            units.append((start, i, False))
        elif ud.category(char)[0] in {'P', 'Z', 'M'}:
            i += 1
        else:
            raise Error(f'Cannot align mixed written form {form!r}; review its spelling.')
    primary = list(re.finditer(r'[^\s-]+', canonical))
    alternate = list(re.finditer(r'[^\s-]+', reading))
    if len(units) != len(primary) or len(primary) != len(alternate):
        raise Error(f'Cannot align alternate {reading!r} to mixed form {form!r}; syllable counts differ.')
    output, cursor = [], 0
    for index, (start, end, hanji) in enumerate(units):
        if not hanji and key(form[start:end]) != key(primary[index].group()):
            raise Error(f'Cannot align romanized part of {form!r} with {canonical!r}.')
        # A changed neutral-tone boundary needs explicit spelling review.
        def neutral(tokens, value):
            previous = tokens[index - 1].end() if index else 0
            return '--' in value[previous:tokens[index].start()]
        if not hanji and neutral(primary, canonical) != neutral(alternate, reading):
            raise Error(f'Neutral-tone boundary changes in {form!r}; review the alternate spelling.')
        output.extend((form[cursor:start], form[start:end] if hanji else alternate[index].group()))
        cursor = end
    output.append(form[cursor:])
    return ''.join(output)


def spelling_readings(entry):
    """All recommended output pairs, retaining one editorial identity."""
    form, canonical = entry['preferred_form'], entry['canonical_tl']
    return [(written_form(form, canonical, reading), reading)
            for reading in [canonical, *entry['alternate_readings']]]


def build_csv(root, include_pure_hanji=False):
    """Build a flat spelling/reading CSV without changing editorial records."""
    with writer_lock(root):
        validate(root)
        current = entries(root)
        rows = set()
        for _, entry in current:
            if not include_pure_hanji and is_hanji(entry['preferred_form']):
                continue
            rows.update(spelling_readings(entry))
        stream = io.StringIO(newline='')
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(('preferred_form', 'tl'))
        writer.writerows(sorted(rows))
        target = root / 'dist' / ('lexicon-all.csv' if include_pure_hanji else 'lexicon.csv')
        atomic_write(target, stream.getvalue())
    return {'csv': str(target.relative_to(root)), 'entries': len(current), 'rows': len(rows)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('validate', 'next-id', 'fetch-moe'):
        sub.add_parser(name)
    csv_export = sub.add_parser('build-csv')
    csv_export.add_argument('--include-pure-hanji', action='store_true',
                            help='Include pure-Hanji preferred forms and write dist/lexicon-all.csv (default: exclude them in dist/lexicon.csv).')
    formatting = sub.add_parser('format')
    formatting.add_argument('--check', action='store_true')
    for name in ('check', 'add'):
        command = sub.add_parser(name)
        command.add_argument('request', type=Path)
    batch = sub.add_parser('add-batch', help='Preflight and import a JSON array with shared checks.')
    batch.add_argument('requests', type=Path)
    batch.add_argument('--dry-run', action='store_true', help='Show the checked plan without reserving IDs or writing entries.')
    query = sub.add_parser('query', help='Find existing entries by exact form, reading, or ID; no dictionary checks.')
    query.add_argument('text', nargs='?')
    query.add_argument('--id', type=int, dest='entry_id')
    query.add_argument('--no-cache', action='store_true', help='Read and validate all entry TOML directly.')
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.command == 'fetch-moe':
            pin, path, _ = cached_moe(root)
            result = {'snapshot': pin['id'], 'cache': str(path.relative_to(root)), 'sha256': pin['sha256']}
        elif args.command == 'next-id':
            result = {'next_id': next_id(root, entries(root)), 'reserved': False}
        elif args.command == 'build-csv':
            result = build_csv(root, include_pure_hanji=args.include_pure_hanji)
        elif args.command == 'validate' or args.command == 'format' and args.check:
            result = validate(root)
        elif args.command == 'format':
            with writer_lock(root):
                validate(root, formatting=False)
                for path, entry in entries(root):
                    target = entry_path(root, entry)
                    if target != path and target.exists():
                        raise Error(f'Refusing to overwrite {target}.')
                    atomic_write(target, render(entry))
                    if path != target:
                        path.unlink()
                        directory = path.parent
                        while directory != root / 'entries':
                            try:
                                directory.rmdir()
                            except OSError:
                                break
                            directory = directory.parent
                result = validate(root)
        elif args.command == 'check':
            result = check(root, request_data(args.request))
        elif args.command == 'query':
            if (args.text is None) == (args.entry_id is None):
                raise Error('Supply exactly one query text or --id.')
            forms = readings = {key(args.text)} if args.text is not None else set()
            matches = query_entries(root, forms, readings, args.entry_id, use_cache=not args.no_cache)
            result = {'count': len(matches), 'entries': [
                {'path': str(path.relative_to(root)), 'entry': entry} for path, entry in matches]}
        elif args.command == 'add-batch':
            result = add_batch(root, batch_requests(args.requests), dry_run=args.dry_run)
        elif args.command == 'add':
            candidate = request_data(args.request)
            result = add_batch(root, [candidate])['results'][0]
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    except (Error, OSError, ValueError, KeyError, zipfile.BadZipFile, ET.ParseError) as exc:
        parser.exit(2, f'error: {exc}\n')


if __name__ == '__main__':
    main()
