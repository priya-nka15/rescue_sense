import json
import pytest
from research.evaluation import Sample, grouped_split, validate_group_split, metrics, TfidfLogisticBaseline
from research.run import evaluate


def test_transitive_duplicate_groups_stay_together():
    samples = [Sample('a','yes','g1','hash1'), Sample('b','no','g2','hash1'), Sample('c','yes','g2','hash2'), Sample('d','no','g3','hash2')]
    assignments = grouped_split(samples)
    assert len(set(assignments.values())) == 1
    assert not validate_group_split(samples,assignments)


def test_duplicate_ids_and_event_leakage():
    samples = [Sample('a','yes','g1',event_id='event'),Sample('b','no','g2',event_id='event')]
    assert validate_group_split(samples,{'a':'train','b':'test'})
    assert validate_group_split([samples[0],samples[0]],{'a':'train'})


def test_abstention_and_invalid_metrics():
    result = metrics(['SUPPORTED','CONTRADICTED'],['SUPPORTED','INSUFFICIENT_EVIDENCE'],['SUPPORTED','CONTRADICTED','INSUFFICIENT_EVIDENCE'])
    assert result['coverage'] == .5 and result['selective_accuracy'] == 1
    assert metrics(['SUPPORTED'],['INSUFFICIENT_EVIDENCE'],['SUPPORTED','INSUFFICIENT_EVIDENCE'])['selective_accuracy'] is None
    with pytest.raises(ValueError): metrics(['true'], ['invented'], ['true','false'])


def test_test_vocabulary_does_not_enter_fitted_preprocessor():
    baseline = TfidfLogisticBaseline().fit(['bridge closed', 'bridge open'],['closed','open'])
    baseline.predict(['never_before_seen_token'])
    assert 'never_before_seen_token' not in baseline.vectorizer.vocabulary_


def test_reproducible_manifest_runner(tmp_path):
    rows = [dict(sample_id=str(i), group_id=str(i), text=text, label=label, split=split)
            for i,(text,label,split) in enumerate([('bridge open','open','train'),('bridge closed','closed','train'),('open road','open','validation'),('closed road','closed','test')])]
    path = tmp_path/'manifest.json'
    path.write_text(json.dumps(dict(dataset='synthetic unit fixture only', version='1', source='unit test', license='test',task='classification fixture', labels=['open','closed'],samples=rows)))
    config, result = evaluate(path)
    assert result['predictions'] == evaluate(path)[1]['predictions']
    assert config['split_counts'] == {'train':2,'validation':1,'test':1}
