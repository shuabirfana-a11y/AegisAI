"""Export/check real HTTP-evaluation schemas without connecting to a service."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'backend'))


def main(argv=None):
    from app.investigation_api.schemas import (
        InvestigationCreateRequest, TraceResponse, ArtifactResponse,
        IntegrationResponse, AnswerResponse,
    )
    from evaluation.bench.schema import Question, Annotation, Prediction, OutcomeAudit

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    models = (Question, Annotation, Prediction, OutcomeAudit, InvestigationCreateRequest,
              TraceResponse, ArtifactResponse, IntegrationResponse, AnswerResponse)
    schemas = {model.__name__: model.model_json_schema() for model in models}
    target = ROOT / 'evaluation/contracts/investigation-http-eval-v1.schema.json'
    if args.check:
        if not target.is_file() or json.loads(target.read_text(encoding='utf-8')) != schemas:
            raise SystemExit('HTTP-evaluation schema differs from current Pydantic definitions')
    else:
        target.write_text(json.dumps(schemas, ensure_ascii=False, indent=2) + '\n',
                          encoding='utf-8', newline='\n')
    print(json.dumps({'status': 'PASS', 'mode': 'check' if args.check else 'export',
                      'schema_groups': len(schemas), 'database_connected': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
