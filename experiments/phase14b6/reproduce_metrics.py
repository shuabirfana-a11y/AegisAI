"""Recompute saved Phase 14-B6 scores offline; no HTTP or model access."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from evaluation.bench.data import load_benchmark
from evaluation.bench.schema import Prediction
from evaluation.bench.quality import score_variant
OUT=ROOT/'evaluation/reports/phase14b6-human49-20261016'
receipt=json.loads((OUT/'receipt-hashes.json').read_text(encoding='utf-8'))
for name,h in receipt.items():
 assert hashlib.sha256((OUT/name).read_bytes()).hexdigest()==h,'Frozen receipt changed: '+name
experiment=json.loads((OUT/'experiment.json').read_text(encoding='utf-8'))
data=load_benchmark(ROOT/experiment['dataset']['manifest'])
assert hashlib.sha256((ROOT/experiment['dataset']['manifest']).read_bytes()).hexdigest()==experiment['dataset']['manifest_sha256']
all_predictions=[Prediction.model_validate_json(x) for x in (OUT/'predictions.jsonl').read_text(encoding='utf-8').splitlines()]
predictions=[p for p in all_predictions if p.baseline=='aegisai']
actual=score_variant(data['questions'],data['annotations'],predictions,[],data['sources'])
assert actual==json.loads((OUT/'metrics.json').read_text(encoding='utf-8')),'Scoring does not reproduce'
assert actual['scored_count']==actual['eligible_gold_count']==len(predictions)==49
assert actual['field_accuracy']['risk_level']['n']==10
print(json.dumps({'offline_reproduction':'PASS','samples':49,'accuracy':actual['accuracy'],
 'risk_accuracy':actual['risk_accuracy'],'evidence_coverage':actual['evidence_coverage'],
 'hallucination_rate':actual['hallucination_rate'],'new_model_calls':0}))
