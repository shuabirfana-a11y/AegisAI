"""Empty corpus is observed in SQL; model failures never become safe answers."""
import pytest


def _index(db, seed):
    from app.db import models as m
    from app.knowledge.index import KnowledgeIndex
    from app.knowledge.embedding import MODEL
    doc=m.KnowledgeDocument(source_id=seed.sources[0].id,raw_document_id=seed.raws[0].id,
        external_id='SYNTHETIC_EMPTY_INDEX_CONTROL',edition='TEST',document_type='advisory',
        title='SYNTHETIC corpus',content='SYNTHETIC indexed input; not benchmark gold',
        url=seed.raws[0].source_url)
    db.add(doc);db.flush()
    class Embed:
        model=MODEL;dimension=2
        def passages(self,texts):return [[1.,0.] for _ in texts]
    KnowledgeIndex.index(db,doc,Embed())
    return doc


@pytest.mark.parametrize('corpus',['empty','stale','deleted'])
def test_unsearchable_corpus_returns_no_result_without_loading_model(db,seed,monkeypatch,corpus):
    from app.knowledge import embedding
    from app.tooling.adapters import execute_local
    calls=[]
    def unavailable():
        calls.append(True)
        raise ModuleNotFoundError('SYNTHETIC unavailable embedding dependency')
    monkeypatch.setattr(embedding,'local_embedding',unavailable)
    if corpus!='empty':
        doc=_index(db,seed)
        if corpus=='stale':doc.revision+=1
        else:
            from app.utils.time import utcnow
            doc.deleted_at=utcnow()
        db.flush()
    result=execute_local(db,'semantic_search',{'query':'SYNTHETIC lookup'},'test-analyst')
    assert result['status']=='no_result' and result['data']=={'items':[]}
    assert result['evidence_refs']==[] and not calls


def test_current_index_does_not_hide_embedding_load_failure(db,seed,monkeypatch):
    from app.knowledge import embedding
    from app.tooling.adapters import execute_local
    _index(db,seed);calls=[]
    def unavailable():
        calls.append(True)
        raise ModuleNotFoundError('SYNTHETIC unavailable embedding dependency')
    monkeypatch.setattr(embedding,'local_embedding',unavailable)
    with pytest.raises(ModuleNotFoundError):
        execute_local(db,'semantic_search',{'query':'SYNTHETIC lookup'},'test-analyst')
    assert calls==[True]
