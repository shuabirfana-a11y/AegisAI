"""Versioned type/query-specific time policy; all clocks are captured or injected."""
from datetime import timedelta
from app.integration.rules_common import check,finish,assessments
from app.integration.profiles import is_overview

def check_freshness(c):
    issues=[];o=c.objective;now=c.evaluation_time;overview=is_overview(c)
    if o is None:return (check('freshness','TIME_SCOPE_UNAVAILABLE','No original temporal acceptance scope','REPLAN'),)
    current=o.requires_current;claims=assessments(c);v=c.verification;r=c.analysis
    refs=v.supporting_evidence if v else ()
    for e in refs:
        assessed=claims.get(e.claim_id);kind=assessed.claim.claim_type if assessed else None
        dynamic=kind=='KNOWN_EXPLOITED'
        days=(1 if current else 7) if dynamic else (7 if current else 90 if overview else 30)
        blocking='NONE' if overview and not current and not o.window_days else 'REPLAN'
        def issue(code,msg):issues.append(check('freshness',code,msg,blocking,warning=blocking=='NONE',refs=(e.evidence_id,)))
        if e.retrieved_at is None:issue('EVIDENCE_TIME_MISSING','Source retrieval time absent; not assumed current')
        else:
            if e.retrieved_at>now+timedelta(minutes=5) or (e.published_at and e.published_at>e.retrieved_at+timedelta(minutes=5)):
                issue('SOURCE_TIME_INCONSISTENT','Publication/retrieval chronology is inconsistent')
            if e.retrieved_at<now-timedelta(days=days):issue('REQUIRED_EVIDENCE_STALE','Source exceeds its type/query freshness budget')
        if e.published_at and e.published_at>now+timedelta(minutes=5):issue('SOURCE_TIME_INCONSISTENT','Future publication timestamp')
    if o.window_days:
        publications=[e.published_at for e in refs if e.published_at]
        if not publications or not any(now-timedelta(days=o.window_days)<=t<=now+timedelta(minutes=5) for t in publications):
            issues.append(check('freshness','REQUEST_TIME_WINDOW_NOT_COVERED','No source publication/update in requested window','REPLAN'))
    if v:
        budget=timedelta(hours=24) if current else timedelta(days=7 if not overview else 90)
        if v.evaluation_time>now+timedelta(minutes=5):issues.append(check('freshness','VERIFICATION_TIME_INCONSISTENT','Verification time is in future','REPLAN'))
        elif v.evaluation_time<now-budget:issues.append(check('freshness','VERIFICATION_STALE','Verification snapshot needs renewed investigation','NONE' if overview else 'REPLAN',warning=overview))
    if c.asset_snapshot and not overview:
        t=c.asset_snapshot.captured_at;budget=timedelta(hours=24) if current else timedelta(days=7)
        if t>now+timedelta(minutes=5):issues.append(check('freshness','INVENTORY_TIME_INCONSISTENT','Inventory capture time in future','REPLAN'))
        elif t<now-budget:issues.append(check('freshness','INVENTORY_SNAPSHOT_STALE','Owned inventory snapshot needs refresh; no scan performed','REPLAN'))
    if r and r.unresolved_items:
        issues.append(check('freshness','UNRESOLVED_ANALYSIS','Unresolved analysis is disclosed','NONE' if overview else 'REPLAN',warning=overview,refs=r.unresolved_items[:128]))
    return finish('freshness',issues)
