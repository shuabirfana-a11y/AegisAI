from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKeyConstraint, Integer, Numeric, String, Text, UniqueConstraint, Index, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import mapped_column
from app.db.base import Base
from app.db.types import Record, Mutable, fk, timestamp, enum_check, VERIFY, SEVERITY

class Vulnerability(Record,Mutable,Base):
    __tablename__='vulnerabilities'
    __table_args__=(UniqueConstraint('canonical_id'),CheckConstraint("canonical_id !~* '^CVE-' OR canonical_id ~ '^CVE-[0-9]{4}-[0-9]{4,}$'",name='canonical_cve'),enum_check('status','published withdrawn rejected unknown'),enum_check('primary_severity',SEVERITY),Index('ix_vulnerabilities_published','published_at'),Index('ix_vulnerabilities_modified','modified_at'),Index('ix_vulnerabilities_severity','primary_severity'),{'schema':'core'})
    canonical_id=mapped_column(String(150),nullable=False)
    title=mapped_column(Text,nullable=False)
    description=mapped_column(Text)
    published_at=timestamp(); modified_at=timestamp()
    status=mapped_column(String(20),nullable=False,default='unknown',server_default='unknown')
    primary_severity=mapped_column(String(20),nullable=False,default='unknown',server_default='unknown')
    revision=mapped_column(Integer,nullable=False,default=1,server_default='1')
    deleted_at=timestamp()

class ExternalIdentifier(Record,Base):
    __tablename__='external_identifiers'
    __table_args__=(UniqueConstraint('namespace','identifier_type','normalized_value'),UniqueConstraint('id','identifier_type'),CheckConstraint('identifier_type=upper(identifier_type)',name='type_uppercase'),CheckConstraint("identifier_type<>'CVE' OR (namespace='global' AND normalized_value ~ '^CVE-[0-9]{4}-[0-9]{4,}$')",name='global_cve'),{'schema':'core'})
    namespace=mapped_column(String(120),nullable=False,default='global',server_default='global')
    identifier_type=mapped_column(String(30),nullable=False)
    identifier_value=mapped_column(Text,nullable=False)
    normalized_value=mapped_column(Text,nullable=False)
    source_id=fk('raw.sources.id')

class VulnerabilityIdentifier(Record,Base):
    __tablename__='vulnerability_identifiers'
    __table_args__=(UniqueConstraint('vulnerability_id','identifier_id'),ForeignKeyConstraint(['identifier_id','identifier_type'],['core.external_identifiers.id','core.external_identifiers.identifier_type'],ondelete='RESTRICT',name='fk_vi_identifier_type'),Index('uq_vi_one_cve_owner','identifier_id',unique=True,postgresql_where=text("identifier_type='CVE'")),{'schema':'core'})
    vulnerability_id=fk('core.vulnerabilities.id')
    identifier_id=fk('core.external_identifiers.id')
    identifier_type=mapped_column(String(30),nullable=False)
    observation_id=fk('raw.source_observations.id',True)

class Product(Record,Mutable,Base):
    __tablename__='products'
    __table_args__=(UniqueConstraint('canonical_key'),Index('ix_products_name','canonical_name'),{'schema':'core'})
    canonical_key=mapped_column(String(200),nullable=False)
    canonical_name=mapped_column(Text,nullable=False)
    vendor=mapped_column(Text)
    product_type=mapped_column(String(40),nullable=False,default='software',server_default='software')
    homepage=mapped_column(Text)
    deleted_at=timestamp()

class ProductAlias(Record,Base):
    __tablename__='product_aliases'
    __table_args__=(UniqueConstraint('product_id','namespace','alias_type','normalized_alias'),Index('ix_product_aliases_lookup','namespace','normalized_alias'),{'schema':'core'})
    product_id=fk('core.products.id')
    source_id=fk('raw.sources.id')
    alias=mapped_column(Text,nullable=False)
    normalized_alias=mapped_column(Text,nullable=False)
    alias_type=mapped_column(String(30),nullable=False)
    namespace=mapped_column(String(80),nullable=False)
    verification_status=mapped_column(String(20),nullable=False,default='pending',server_default='pending')

class PackageIdentifier(Record,Base):
    __tablename__='package_identifiers'
    __table_args__=(UniqueConstraint('purl'),UniqueConstraint('ecosystem','namespace','package_name'),UniqueConstraint('id','product_id'),{'schema':'core'})
    product_id=fk('core.products.id')
    ecosystem=mapped_column(String(40),nullable=False)
    namespace=mapped_column(String(200),nullable=False,default='',server_default='')
    package_name=mapped_column(String(300),nullable=False)
    purl=mapped_column(Text,nullable=False)
    cpe=mapped_column(Text)
    repository=mapped_column(Text)

class AffectedVersionRange(Record,Base):
    __tablename__='affected_version_ranges'
    __table_args__=(ForeignKeyConstraint(['package_identifier_id','product_id'],['core.package_identifiers.id','core.package_identifiers.product_id'],ondelete='RESTRICT',name='fk_range_package_product'),UniqueConstraint('id','vulnerability_id','package_identifier_id'),enum_check('parse_status','parsed unsupported failed'),enum_check('verification_status',VERIFY),CheckConstraint("length(raw_expression)>0",name='raw_expression_present'),CheckConstraint("parse_status <> 'parsed' OR events IS NOT NULL OR explicit_versions IS NOT NULL OR introduced IS NOT NULL OR fixed IS NOT NULL OR last_affected IS NOT NULL OR limit_version IS NOT NULL",name='parsed_has_machine_value'),Index('ix_ranges_vuln_package','vulnerability_id','package_identifier_id'),{'schema':'core'})
    vulnerability_id=fk('core.vulnerabilities.id')
    product_id=fk('core.products.id')
    package_identifier_id=fk('core.package_identifiers.id')
    source_id=fk('raw.sources.id'); observation_id=fk('raw.source_observations.id')
    introduced=mapped_column(Text); fixed=mapped_column(Text); last_affected=mapped_column(Text); limit_version=mapped_column(Text)
    range_type=mapped_column(String(30),nullable=False)
    raw_expression=mapped_column(Text,nullable=False)
    events=mapped_column(JSONB); explicit_versions=mapped_column(JSONB)
    branch=mapped_column(Text)
    scope_key=mapped_column(String(128),nullable=False)
    parse_status=mapped_column(String(20),nullable=False)
    parse_reason=mapped_column(Text)
    parser_version=mapped_column(String(60),nullable=False)
    verification_status=mapped_column(String(20),nullable=False,default='pending',server_default='pending')

class CvssAssessment(Record,Base):
    __tablename__='cvss_assessments'
    __table_args__=(UniqueConstraint('id','vulnerability_id'),CheckConstraint('base_score BETWEEN 0 AND 10',name='score_bounds'),enum_check('version','2.0 3.0 3.1 4.0'),enum_check('severity',SEVERITY),Index('ix_cvss_vuln_version','vulnerability_id','version'),{'schema':'core'})
    vulnerability_id=fk('core.vulnerabilities.id'); source_id=fk('raw.sources.id'); observation_id=fk('raw.source_observations.id')
    version=mapped_column(String(10),nullable=False)
    vector=mapped_column(Text)
    base_score=mapped_column(Numeric(3,1),nullable=False)
    severity=mapped_column(String(20),nullable=False)
    provider=mapped_column(Text,nullable=False)
    assessment_kind=mapped_column(String(40),nullable=False,default='base',server_default='base')
    scope_key=mapped_column(String(128),nullable=False)
    published_at=timestamp()

class Weakness(Record,Base):
    __tablename__='weaknesses'
    __table_args__=(UniqueConstraint('cwe_id'),{'schema':'core'})
    cwe_id=mapped_column(String(30),nullable=False)
    name=mapped_column(Text,nullable=False)

class VulnerabilityWeakness(Record,Base):
    __tablename__='vulnerability_weaknesses'
    __table_args__=(UniqueConstraint('vulnerability_id','weakness_id','observation_id'),{'schema':'core'})
    vulnerability_id=fk('core.vulnerabilities.id'); weakness_id=fk('core.weaknesses.id'); observation_id=fk('raw.source_observations.id')

class Reference(Record,Base):
    __tablename__='references'
    __table_args__=(UniqueConstraint('canonical_url'),{'schema':'core'})
    url=mapped_column(Text,nullable=False); canonical_url=mapped_column(Text,nullable=False)
    title=mapped_column(Text); reference_type=mapped_column(String(30),nullable=False)
    source_id=fk('raw.sources.id'); published_at=timestamp()

class VulnerabilityReference(Record,Base):
    __tablename__='vulnerability_references'
    __table_args__=(UniqueConstraint('vulnerability_id','reference_id','observation_id'),{'schema':'core'})
    vulnerability_id=fk('core.vulnerabilities.id'); reference_id=fk('core.references.id'); observation_id=fk('raw.source_observations.id')

class AiSecurityCategory(Record,Base):
    __tablename__='ai_security_categories'
    __table_args__=(UniqueConstraint('category_key'),{'schema':'core'})
    category_key=mapped_column(String(80),nullable=False); name=mapped_column(Text,nullable=False)

class VulnerabilityAiCategory(Record,Base):
    __tablename__='vulnerability_ai_categories'
    __table_args__=(UniqueConstraint('vulnerability_id','category_id','assessment_id'),{'schema':'core'})
    vulnerability_id=fk('core.vulnerabilities.id'); category_id=fk('core.ai_security_categories.id'); assessment_id=fk('core.ai_relevance_assessments.id')

class AiRelevanceAssessment(Record,Base):
    __tablename__='ai_relevance_assessments'
    __table_args__=(CheckConstraint('num_nonnulls(vulnerability_id,knowledge_document_id)=1',name='one_subject'),enum_check('method','rule product package llm human'),enum_check('result','relevant irrelevant uncertain'),{'schema':'core'})
    vulnerability_id=fk('core.vulnerabilities.id',True); knowledge_document_id=fk('intel.knowledge_documents.id',True)
    method=mapped_column(String(20),nullable=False); result=mapped_column(String(20),nullable=False)
    reason_summary=mapped_column(Text,nullable=False); model_version=mapped_column(String(100))
    evaluated_at=timestamp(False); observation_id=fk('raw.source_observations.id',True)
