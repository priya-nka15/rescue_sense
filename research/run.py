"""Evaluate an authorized, labelled JSON manifest. No data acquisition."""
import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

from .evaluation import Sample, TfidfLogisticBaseline, majority_predictions, metrics, validate_group_split, write_report


def evaluate(path: Path) -> tuple[dict, dict]:
    data = json.loads(path.read_text())
    for key in ('dataset', 'version', 'source', 'license', 'task', 'labels', 'samples'):
        if not data.get(key):
            raise ValueError(f'Manifest requires {key}.')
    rows = data['samples']
    samples = [Sample(**{k: row.get(k) for k in Sample.__dataclass_fields__}) for row in rows]
    errors = validate_group_split(samples, {r['sample_id']: r['split'] for r in rows})
    if errors:
        raise ValueError('; '.join(errors))
    subsets = {split: [r for r in rows if r['split'] == split] for split in ('train','validation','test')}
    if not all(subsets.values()):
        raise ValueError('Train, validation and test must all be nonempty.')
    if any(not isinstance(r.get('text'), str) or not r['text'].strip() or r['label'] not in data['labels'] for r in rows):
        raise ValueError('All rows need valid text and declared labels.')
    train, test = subsets['train'], subsets['test']
    started = perf_counter()
    baseline = TfidfLogisticBaseline().fit([r['text'] for r in train], [r['label'] for r in train])
    predictions = baseline.predict([r['text'] for r in test])
    results = {'tfidf_logistic': metrics([r['label'] for r in test], predictions, data['labels']),
               'majority': metrics([r['label'] for r in test], majority_predictions([r['label'] for r in train], len(test)), data['labels']),
               'predictions': [{'sample_id': r['sample_id'], 'truth': r['label'], 'prediction': p} for r,p in zip(test,predictions)],
               'elapsed_seconds': perf_counter()-started}
    config = {k: data[k] for k in ('dataset','version','source','license','task','labels')}
    config.update(manifest_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), seed=42, split_counts={k:len(v) for k,v in subsets.items()})
    return config, results


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    config, results = evaluate(args.manifest)
    write_report(args.output, config, results)
