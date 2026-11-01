"""Persist review exclusions independently of the changing candidate queue."""
import argparse
import hashlib
import json
from pathlib import Path


def validate_segments(segments, summary):
    if not isinstance(segments, list) or any(not isinstance(s, str) for s in segments):
        raise ValueError('Ignored segments must be source-position identities')
    if not segments:
        return
    from harvest import spans
    content = Path(summary['corpus_path']).read_bytes()
    if hashlib.sha256(content).hexdigest() != summary['corpus_sha256']:
        raise ValueError('Corpus changed; cannot restore segment decisions')
    docs = {d['id']: d for d in map(json.loads, content.splitlines())}
    selected = {identity for identity, doc in docs.items()
                if 'tags' not in doc.get('metadata', {})
                or f"issue:{summary['issue']}" in doc['metadata']['tags']}
    for identity in segments:
        try:
            doc, start, end = json.loads(identity)
            if (not isinstance(doc, str) or type(start) is not int or type(end) is not int
                    or doc not in selected or (start, end) not in set(spans(docs[doc]['text']))):
                raise ValueError()
        except (ValueError, TypeError, KeyError):
            raise ValueError('Ignored segment is not a Roman-text position in this corpus') from None


def read_settings(pilot, summary):
    path = pilot / 'review-settings.json'
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    if (data.get('schema_version') != 1 or data.get('issue') != summary['issue']
            or data.get('corpus_sha256') != summary['corpus_sha256']):
        raise ValueError('Review settings belong to a different issue or corpus')
    validate_segments(data.get('ignored_segments', []), summary)
    return {**data, 'settings_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def save_settings(pilot, bundle, summary):
    if bundle.get('issue') != summary['issue'] or bundle.get('corpus_sha256') != summary['corpus_sha256']:
        raise ValueError('Review settings belong to a different issue or corpus')
    previous = read_settings(pilot, summary)
    segments = bundle.get('ignored_segments', previous.get('ignored_segments', []))
    validate_segments(segments, summary)
    forms = bundle.get('ignored_forms', [])
    if not isinstance(forms, list) or any(not isinstance(f, str) for f in forms):
        raise ValueError('Ignored forms must be an array of strings')
    data = {'schema_version': 1, 'issue': summary['issue'], 'corpus_sha256': summary['corpus_sha256'],
            'ignored_forms': sorted(set(forms)), 'ignored_segments': sorted(set(segments))}
    path = pilot / 'review-settings.json'
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--pilot', type=Path, required=True)
    args = parser.parse_args()
    data = save_settings(args.pilot, json.loads(args.review.read_text()),
                         json.loads((args.pilot / 'summary.json').read_text()))
    print(json.dumps({'ignored_forms': len(data['ignored_forms']), 'ignored_segments': len(data['ignored_segments'])}))


if __name__ == '__main__':
    main()
