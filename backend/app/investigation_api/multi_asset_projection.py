"""Deterministic summary only. Never derives impact from a graph path."""
from app.investigation_api.multi_asset_schemas import BatchSummary


def summarize(items):
    counts={key:0 for key in ('total','processed','running','failed','not_executed','need_context',
                              'AFFECTED','NOT_AFFECTED','UNKNOWN')}
    counts['total']=len(items)
    actionable=[];unresolved=[];unaffected=[]
    for item in items:
        state=item.execution_status
        counts['processed']+=state in ('COMPLETED','FAILED','NEED_CONTEXT')
        counts['running']+=state=='RUNNING'
        counts['failed']+=state=='FAILED'
        counts['not_executed']+=state in ('NOT_STARTED','NOT_EXECUTED')
        counts['need_context']+=state=='NEED_CONTEXT'
        counts[item.impact]+=1
        accepted=(state=='COMPLETED' and item.snapshot_valid and item.gate_status in ('PASS','PASS_WITH_WARNINGS')
                  and item.verification_status=='CONFIRMED' and bool(item.evidence_ids))
        if accepted and item.impact=='AFFECTED' and item.risk_level in ('CRITICAL','HIGH','MEDIUM','LOW') and item.priority in ('P0','P1','P2','P3'):
            actionable.append(item)
        elif accepted and item.impact=='NOT_AFFECTED':unaffected.append(item.snapshot.asset_id)
        else:unresolved.append(item.snapshot.asset_id)
    actionable.sort(key=lambda x:(('P0','P1','P2','P3').index(x.priority),str(x.snapshot.asset_id)))
    return BatchSummary(counts=counts,actionable_asset_ids=tuple(x.snapshot.asset_id for x in actionable),
        unresolved_asset_ids=tuple(sorted(unresolved,key=str)),unaffected_asset_ids=tuple(sorted(unaffected,key=str)))
