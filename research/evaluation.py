from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import json
import random
from typing import Iterable

from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression


@dataclass(frozen=True)
class Sample:
    sample_id: str
    label: str
    group_id: str
    image_hash: str | None = None
    event_id: str | None = None
    source_id: str | None = None
    claim_hash: str | None = None
    image_cluster: str | None = None


def validate_group_split(samples: Iterable[Sample], assignments: dict[str, str]) -> list[str]:
    samples = list(samples)
    errors: list[str] = []
    if len({s.sample_id for s in samples}) != len(samples):
        errors.append('Duplicate sample IDs.')
    if any(not s.sample_id or not s.label or not s.group_id for s in samples):
        errors.append('Samples require non-empty ID, label and group.')
    groups: dict[str, set[str]] = defaultdict(set)
    hashes: dict[str, set[str]] = defaultdict(set)
    for sample in samples:
        split = assignments.get(sample.sample_id)
        if split not in {"train", "validation", "test"}: errors.append(f"{sample.sample_id}: missing or invalid split")
        elif split: groups[sample.group_id].add(split)
        if sample.image_hash and split: hashes[sample.image_hash].add(split)
        for field in ('event_id', 'source_id', 'claim_hash', 'image_cluster'):
            value = getattr(sample, field)
            if value and split:
                groups[f'{field}:{value}'].add(split)
    errors.extend(f"group {group} crosses {sorted(splits)}" for group, splits in groups.items() if len(splits) > 1)
    errors.extend(f"image hash {digest} crosses {sorted(splits)}" for digest, splits in hashes.items() if len(splits) > 1)
    return errors


def grouped_split(samples: list[Sample], seed: int = 42) -> dict[str, str]:
    # Connected components keep duplicate images and linked sources together.
    parent = {sample.group_id: sample.group_id for sample in samples}
    def root(group):
        while parent[group] != group:
            parent[group] = parent[parent[group]]
            group = parent[group]
        return group
    seen = {}
    for sample in samples:
        for field in ('image_hash', 'event_id', 'source_id', 'claim_hash', 'image_cluster'):
            value = getattr(sample, field)
            if value:
                key = (field, value)
                if key in seen:
                    parent[root(sample.group_id)] = root(seen[key])
                seen[key] = sample.group_id
    groups = sorted({root(sample.group_id) for sample in samples})
    random.Random(seed).shuffle(groups)
    cut_one, cut_two = int(len(groups) * .6), int(len(groups) * .8)
    group_assignments = {group: "train" if index < cut_one else "validation" if index < cut_two else "test" for index, group in enumerate(groups)}
    return {sample.sample_id: group_assignments[root(sample.group_id)] for sample in samples}


def metrics(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict:
    if not y_true or len(y_true) != len(y_pred) or len(set(labels)) != len(labels) or not set(y_true + y_pred) <= set(labels):
        raise ValueError('Metrics require non-empty aligned predictions and valid declared labels.')
    decided = [(a,b) for a,b in zip(y_true,y_pred) if b != 'INSUFFICIENT_EVIDENCE']
    selected_accuracy = sum(a == b for a,b in decided) / len(decided) if decided else None
    return {"accuracy": sum(a == b for a,b in zip(y_true,y_pred))/len(y_true), "coverage": len(decided)/len(y_true), "selective_accuracy": selected_accuracy, "selective_error": None if selected_accuracy is None else 1-selected_accuracy, "macro_f1": f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0), "per_class": classification_report(y_true, y_pred, labels=labels, output_dict=True, zero_division=0), "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(), "labels": labels}


def majority_predictions(train_labels: list[str], count: int) -> list[str]:
    if not train_labels:
        raise ValueError('Majority baseline needs training labels.')
    from collections import Counter
    label = sorted(Counter(train_labels).items(), key=lambda x: (-x[1], x[0]))[0][0]
    return [label] * count


def write_report(output: Path, config: dict, results: dict) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"config": config, "results": results}, indent=2), encoding="utf-8")


class TfidfLogisticBaseline:
    """A train-only research baseline; callers must provide valid labelled splits."""

    def __init__(self) -> None:
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=20000)
        self.classifier = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)

    def fit(self, texts: list[str], labels: list[str]) -> "TfidfLogisticBaseline":
        if len(texts) != len(labels) or len(set(labels)) < 2:
            raise ValueError("Training requires equally sized text/label lists with at least two classes.")
        self.classifier.fit(self.vectorizer.fit_transform(texts), labels)
        return self

    def predict(self, texts: list[str]) -> list[str]:
        return self.classifier.predict(self.vectorizer.transform(texts)).tolist()
