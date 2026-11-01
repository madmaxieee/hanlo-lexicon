"""Refresh only review.html from sealed harvest files; never run discovery."""
import argparse
import hashlib
import json
from pathlib import Path

from harvest import review_page, preferred_index
from review_context import corpus_texts
from review_filters import annotate_coverage
from screen import load_screening


def render(pilot):
    summary = json.loads((pilot / 'summary.json').read_text())
    content = (pilot / 'groups.json').read_bytes()
    if hashlib.sha256(content).hexdigest() != summary['review_groups_sha256']:
        raise ValueError('Harvest groups changed; cannot refresh this review')
    groups = load_screening(pilot, summary, json.loads(content))
    payload = {**summary, 'groups': groups}
    texts = corpus_texts(payload)
    if summary.get('lexicon_root'):
        records, _ = preferred_index(Path(summary['lexicon_root']))
        payload.update(groups=annotate_coverage(groups, records, texts), lexicon_inventory=records,
                       coverage_refreshed=True)
    page = review_page(payload, texts)
    (pilot / 'review.html').write_text(page)
    return pilot / 'review.html'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pilot', type=Path, required=True)
    args = parser.parse_args()
    print(render(args.pilot))


if __name__ == '__main__':
    main()
