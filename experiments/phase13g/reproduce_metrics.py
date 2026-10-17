"""Offline verification of recorded scoring; never calls HTTP, models or agents."""
import json,sys,hashlib
from pathlib import Path
r=Path(__file__).resolve().parents[2];sys.path.insert(0,str(r))
from evaluation.bench.data import load_benchmark
from evaluation.bench.schema import Prediction
from evaluation.bench.quality import score_variant
root=r/'evaluation/reports/phase13g-human49-20261014'
data=load_benchmark(r/'evaluation/datasets/AegisBench-v0.4-human49-20261014/manifest.json')
receipt=json.loads((root/'collection/experiment.json').read_text(encoding='utf-8'))
for name,key in [('report.json','report_sha256'),('predictions.jsonl','predictions_sha256'),('native-http-records.json','native_records_sha256')]:
    assert hashlib.sha256((root/'collection'/name).read_bytes()).hexdigest()==receipt[key],'Frozen result hash mismatch'
report=json.loads((root/'collection/report.json').read_text(encoding='utf-8'))
variant=report['variants']['aegisai']
actual=score_variant(data['questions'],data['annotations'],[Prediction.model_validate(p) for p in variant['predictions']],[],data['sources'])
assert actual==variant['metrics'],'Recorded scores do not reproduce'
assert actual['eligible_gold_count']==actual['scored_count']==49
print(json.dumps({'offline_reproduction':'PASS','samples':49,'accuracy':actual['accuracy'],'risk_accuracy':actual['risk_accuracy'],'evidence_coverage':actual['evidence_coverage'],'hallucination_rate':actual['hallucination_rate'],'new_model_calls':0},ensure_ascii=False))
