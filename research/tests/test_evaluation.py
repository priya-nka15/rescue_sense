from research.evaluation import Sample, TfidfLogisticBaseline, grouped_split, metrics, validate_group_split


def test_groups_and_hashes_cannot_cross_splits():
    samples = [Sample("one", "true", "article-1", "a"), Sample("two", "miscaptioned", "article-1", "a")]
    assert validate_group_split(samples, {"one": "train", "two": "test"})
    assignments = grouped_split(samples)
    assert not validate_group_split(samples, assignments)


def test_metrics_shape():
    result = metrics(["true", "false"], ["true", "true"], ["true", "false"])
    assert "macro_f1" in result and len(result["confusion_matrix"]) == 2


def test_tfidf_baseline_requires_labels_and_predicts():
    baseline = TfidfLogisticBaseline().fit(["river flood warning", "sports result"], ["crisis", "other"])
    assert len(baseline.predict(["river flood"])) == 1
