from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKeyConstraint, Integer, Numeric, String, Text, UniqueConstraint, Index, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from app.db.base import Base
from app.db.types import Record, Mutable, fk, timestamp, enum_check, VERIFY, CANDIDATE

class KnowledgeDocument(Record,Mutable,Base):
    __tablename__='knowledge_documents'
    __table_args__=(UniqueConstraint('source_id','external_id','edition'),enum_check('document_type','advisory blog paper analysis ai_event standard policy knowledge'),Index('ix_knowledge_type_date','document_type','published_at'),{'schema':'intel'})
    source_id=fk('raw.sources.id'); raw_document_id=fk('raw.raw_documents.id')
    external_id=mapped_column(Text,nullable=False)
    document_type=mapped_column(String(20),nullable=False)
    title=mapped_column(Text,nullable=False); content=mapped_column(Text)
    url=mapped_column(Text,nullable=False)
    edition=mapped_column(String(200),nullable=False)
    authors=mapped_column(JSONB); publisher=mapped_column(Text)
    language=mapped_column(String(20)); publication_status=mapped_column(String(30))
    published_at=timestamp(); modified_at=timestamp(); effective_at=timestamp()
    license_scope=mapped_column(Text,nullable=False,default='unknown',server_default='unknown')
    revision=mapped_column(Integer,nullable=False,default=1,server_default='1')
    deleted_at=timestamp()

class KnowledgeChunk(Record,Base):
    __tablename__='knowledge_chunks'
    __table_args__=(UniqueConstraint('document_id','document_revision','chunker_version','chunk_index'),CheckConstraint('chunk_index>=0 AND document_revision>0',name='position'),{'schema':'intel'})
    document_id=fk('intel.knowledge_documents.id'); raw_document_id=fk('raw.raw_documents.id')
    document_revision=mapped_column(Integer,nullable=False)
    chunk_index=mapped_column(Integer,nullable=False)
    chunker_version=mapped_column(String(60),nullable=False)
    content=mapped_column(Text,nullable=False); content_hash=mapped_column(String(64),nullable=False)
    locator=mapped_column(JSONB,nullable=False)

class PocCandidate(Record,Mutable,Base):
    __tablename__='poc_candidates'
    __table_args__=(UniqueConstraint('vulnerability_id','canonical_url'),UniqueConstraint('id','vulnerability_id'),enum_check('status',CANDIDATE),enum_check('usability_status','not_evaluated unknown verified_usable unusable'),Index('ix_poc_status','status'),{'schema':'intel'})
    vulnerability_id=fk('core.vulnerabilities.id'); source_id=fk('raw.sources.id'); observation_id=fk('raw.source_observations.id')
    url=mapped_column(Text,nullable=False); canonical_url=mapped_column(Text,nullable=False)
    repository=mapped_column(Text); commit=mapped_column(Text); author=mapped_column(Text)
    candidate_type=mapped_column(String(40),nullable=False)
    status=mapped_column(String(20),nullable=False,default='candidate',server_default='candidate')
    usability_status=mapped_column(String(30),nullable=False,default='not_evaluated',server_default='not_evaluated')
    first_seen_at=timestamp(False); last_seen_at=timestamp(False)

class PatchCandidate(Record,Mutable,Base):
    __tablename__='patch_candidates'
    __table_args__=(UniqueConstraint('vulnerability_id','product_id','branch','patch_type','identity_key'),UniqueConstraint('id','vulnerability_id'),enum_check('patch_type','commit pull_request release vendor_patch fixed_version'),enum_check('status',CANDIDATE),CheckConstraint("commit_sha IS NULL OR commit_sha ~ '^([0-9a-f]{40}|[0-9a-f]{64})$'",name='full_commit'),CheckConstraint("patch_type <> 'commit' OR commit_sha IS NOT NULL",name='commit_has_sha'),CheckConstraint("patch_type <> 'fixed_version' OR release_version IS NOT NULL",name='fixed_has_version'),{'schema':'intel'})
    vulnerability_id=fk('core.vulnerabilities.id'); product_id=fk('core.products.id')
    source_id=fk('raw.sources.id'); observation_id=fk('raw.source_observations.id')
    patch_type=mapped_column(String(30),nullable=False)
    identity_key=mapped_column(Text,nullable=False)
    url=mapped_column(Text); commit_sha=mapped_column(String(64)); release_version=mapped_column(Text)
    branch=mapped_column(Text,nullable=False,default='',server_default='')
    status=mapped_column(String(20),nullable=False,default='candidate',server_default='candidate')
    first_seen_at=timestamp(False)

class Claim(Record,Mutable,Base):
    __tablename__='claims'
    __table_args__=(UniqueConstraint('claim_key'),UniqueConstraint('id','scope_key'),UniqueConstraint('id','vulnerability_id'),CheckConstraint('num_nonnulls(vulnerability_id,knowledge_document_id)=1',name='one_root'),CheckConstraint('num_nonnulls(product_id,package_identifier_id,range_id,poc_candidate_id,patch_candidate_id,asset_component_id,cvss_assessment_id)<=1',name='one_subject'),enum_check('verification_status',VERIFY),CheckConstraint('revision>0',name='revision_positive'),ForeignKeyConstraint(['poc_candidate_id','vulnerability_id'],['intel.poc_candidates.id','intel.poc_candidates.vulnerability_id'],ondelete='RESTRICT',name='fk_claim_poc_root'),ForeignKeyConstraint(['patch_candidate_id','vulnerability_id'],['intel.patch_candidates.id','intel.patch_candidates.vulnerability_id'],ondelete='RESTRICT',name='fk_claim_patch_root'),ForeignKeyConstraint(['cvss_assessment_id','vulnerability_id'],['core.cvss_assessments.id','core.cvss_assessments.vulnerability_id'],ondelete='RESTRICT',name='fk_claim_cvss_root'),Index('ix_claims_root_status','vulnerability_id','verification_status'),Index('uq_claims_adopted_vuln_scope','vulnerability_id','predicate','scope_key',unique=True,postgresql_where=text('adopted AND vulnerability_id IS NOT NULL')),Index('uq_claims_adopted_knowledge_scope','knowledge_document_id','predicate','scope_key',unique=True,postgresql_where=text('adopted AND knowledge_document_id IS NOT NULL')),{'schema':'intel'})
    claim_key=mapped_column(String(200),nullable=False)
    vulnerability_id=fk('core.vulnerabilities.id',True); knowledge_document_id=fk('intel.knowledge_documents.id',True)
    product_id=fk('core.products.id',True); package_identifier_id=fk('core.package_identifiers.id',True)
    range_id=fk('core.affected_version_ranges.id',True); poc_candidate_id=fk('intel.poc_candidates.id',True)
    patch_candidate_id=fk('intel.patch_candidates.id',True); asset_component_id=fk('app.asset_components.id',True)
    cvss_assessment_id=fk('core.cvss_assessments.id',True)
    claim_type=mapped_column(String(50),nullable=False); predicate=mapped_column(String(80),nullable=False)
    value_json=mapped_column(JSONB,nullable=False)
    scope_key=mapped_column(String(128),nullable=False)
    branch=mapped_column(Text); cvss_version=mapped_column(String(10)); assessment_kind=mapped_column(String(40)); as_of_date=mapped_column(Date)
    verification_status=mapped_column(String(20),nullable=False,default='pending',server_default='pending')
    adopted=mapped_column(Boolean,nullable=False,default=False,server_default='false')
    revision=mapped_column(Integer,nullable=False,default=1,server_default='1')

class Evidence(Record,Base):
    __tablename__='evidence'
    __table_args__=(UniqueConstraint('id','claim_id'),UniqueConstraint('claim_id','observation_id','locator_key','stance'),ForeignKeyConstraint(['claim_id','scope_key'],['intel.claims.id','intel.claims.scope_key'],ondelete='RESTRICT',name='fk_evidence_claim_scope'),ForeignKeyConstraint(['raw_document_id','source_id'],['raw.raw_documents.id','raw.raw_documents.source_id'],ondelete='RESTRICT',name='fk_evidence_raw_source'),ForeignKeyConstraint(['observation_id','raw_document_id','source_id'],['raw.source_observations.id','raw.source_observations.raw_document_id','raw.source_observations.source_id'],ondelete='RESTRICT',name='fk_evidence_observation_raw'),enum_check('stance','support contradict neutral'),Index('ix_evidence_claim','claim_id'),{'schema':'intel'})
    claim_id=fk('intel.claims.id'); source_id=fk('raw.sources.id'); raw_document_id=fk('raw.raw_documents.id'); observation_id=fk('raw.source_observations.id')
    scope_key=mapped_column(String(128),nullable=False)
    evidence_type=mapped_column(String(40),nullable=False); stance=mapped_column(String(20),nullable=False)
    excerpt=mapped_column(Text,nullable=False); excerpt_hash=mapped_column(String(64),nullable=False)
    source_url=mapped_column(Text,nullable=False)
    published_at=timestamp(); retrieved_at=timestamp(False)
    locator=mapped_column(JSONB,nullable=False); locator_key=mapped_column(String(200),nullable=False)
    observed_value=mapped_column(JSONB)
    publisher=mapped_column(Text,nullable=False); lineage_key=mapped_column(Text,nullable=False)

class VerificationResult(Record,Base):
    __tablename__='verification_results'
    __table_args__=(UniqueConstraint('id','claim_id'),UniqueConstraint('claim_id','claim_revision'),UniqueConstraint('claim_id','claim_revision','decision_key'),enum_check('status',VERIFY),enum_check('verified_by_type','system human'),CheckConstraint('claim_revision>0',name='positive_revision'),{'schema':'intel'})
    claim_id=fk('intel.claims.id')
    claim_revision=mapped_column(Integer,nullable=False)
    status=mapped_column(String(20),nullable=False)
    verification_method=mapped_column(String(80),nullable=False)
    reason_summary=mapped_column(Text,nullable=False)
    verified_at=timestamp(False)
    verified_by_type=mapped_column(String(20),nullable=False); verified_by_id=mapped_column(String(150),nullable=False)
    decision_key=mapped_column(String(200),nullable=False)
    adopted_value=mapped_column(JSONB)

class VerificationEvidence(Record,Base):
    __tablename__='verification_evidence'
    __table_args__=(UniqueConstraint('verification_result_id','evidence_id'),ForeignKeyConstraint(['verification_result_id','claim_id'],['intel.verification_results.id','intel.verification_results.claim_id'],ondelete='RESTRICT',name='fk_ve_result_claim'),ForeignKeyConstraint(['evidence_id','claim_id'],['intel.evidence.id','intel.evidence.claim_id'],ondelete='RESTRICT',name='fk_ve_evidence_claim'),{'schema':'intel'})
    claim_id=fk('intel.claims.id'); verification_result_id=fk('intel.verification_results.id'); evidence_id=fk('intel.evidence.id')

class EpssSnapshot(Record,Base):
    __tablename__='epss_snapshots'
    __table_args__=(UniqueConstraint('vulnerability_id','source_id','score_date','model_version','raw_document_id'),CheckConstraint('score BETWEEN 0 AND 1 AND (percentile IS NULL OR percentile BETWEEN 0 AND 1)',name='probability_bounds'),Index('ix_epss_vuln_date','vulnerability_id','score_date'),{'schema':'intel'})
    vulnerability_id=fk('core.vulnerabilities.id'); source_id=fk('raw.sources.id'); raw_document_id=fk('raw.raw_documents.id')
    score=mapped_column(Numeric(9,8),nullable=False); percentile=mapped_column(Numeric(9,8))
    score_date=mapped_column(Date,nullable=False); observed_at=timestamp(False)
    model_version=mapped_column(String(60),nullable=False)

class KnownExploitation(Record,Base):
    __tablename__='known_exploitation'
    __table_args__=(UniqueConstraint('vulnerability_id','source_id','raw_document_id'),enum_check('catalog_status','listed not_listed_as_of unknown'),CheckConstraint("(catalog_status='listed' AND known_exploited IS TRUE) OR (catalog_status<>'listed' AND known_exploited IS NULL)",name='no_false_negative'),CheckConstraint("catalog_status<>'not_listed_as_of' OR catalog_complete IS TRUE",name='absence_requires_complete'),Index('ix_kev_status','catalog_status'),{'schema':'intel'})
    vulnerability_id=fk('core.vulnerabilities.id'); source_id=fk('raw.sources.id'); raw_document_id=fk('raw.raw_documents.id')
    known_exploited=mapped_column(Boolean,nullable=True)
    catalog_status=mapped_column(String(30),nullable=False)
    catalog_complete=mapped_column(Boolean,nullable=False,default=False,server_default='false')
    catalog_version=mapped_column(Text,nullable=False); observed_at=timestamp(False)
    date_added=mapped_column(Date); due_date=mapped_column(Date); required_action=mapped_column(Text)

class IntelligenceEvent(Record,Base):
    __tablename__='intelligence_events'
    __table_args__=(UniqueConstraint('event_key'),CheckConstraint('num_nonnulls(vulnerability_id,knowledge_document_id)=1',name='one_root'),Index('ix_events_vuln_detected','vulnerability_id','detected_at'),{'schema':'intel'})
    event_key=mapped_column(String(200),nullable=False)
    vulnerability_id=fk('core.vulnerabilities.id',True); knowledge_document_id=fk('intel.knowledge_documents.id',True)
    claim_id=fk('intel.claims.id',True); evidence_id=fk('intel.evidence.id',True); source_id=fk('raw.sources.id',True)
    event_type=mapped_column(String(50),nullable=False)
    occurred_at=timestamp(); detected_at=timestamp(False)
    summary=mapped_column(Text,nullable=False); payload=mapped_column(JSONB)

class KnowledgeVulnerabilityRelation(Record,Base):
    __tablename__='knowledge_vulnerability_relations'
    __table_args__=(UniqueConstraint('knowledge_document_id','vulnerability_id','relation_type','claim_id'),{'schema':'intel'})
    knowledge_document_id=fk('intel.knowledge_documents.id'); vulnerability_id=fk('core.vulnerabilities.id'); claim_id=fk('intel.claims.id')
    relation_type=mapped_column(String(50),nullable=False)
