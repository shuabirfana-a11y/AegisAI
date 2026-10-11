from uuid import uuid4

def request(chain,**changes):
    from app.integration.contracts import ArtifactRef,IntegrationRequest
    def ref(art):return ArtifactRef(run_id=art.run_id,task_id=art.task_id,artifact_id=art.artifact_id,schema_version=art.schema_version)
    data=dict(request_key='GATE-'+uuid4().hex,run_id=chain.investigation.run_id,planner_run_id=chain.planner.planner_run_id,
        investigation=ref(chain.investigation),verification=ref(chain.verification),analysis=ref(chain.analysis))
    data.update(changes)
    return IntegrationRequest(**data)
