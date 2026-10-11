# 数据字典与实现规格

本字典从当前43个ORM表元数据生成，并经实际0001迁移的schema drift比较核验；字段不是API承诺。Record仅复用UUID/created/metadata三字段，Mutable复用updated，没有多层继承。metadata的Python属性名为details，避免覆盖Base.metadata。

NULL表示未知或未发生，不能改成0/false/[]；JSON空数组只用于来源明示空集。时间全部TIMESTAMP WITH TIME ZONE；BYTEA原文与JSON缓存分离。每张表的UNIQUE/FK/CHECK及索引见相邻文档。

## AgentRun `app.agent_runs`

用户请求与可审计摘要/状态/时延，尚未连接Agent

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `actor_principal` | VARCHAR(150) | 否 | `—` | 领域字段：actor_principal；按本模型语义保存原值/明确结果 |
| `user_request` | TEXT | 否 | `—` | 领域字段：user_request；按本模型语义保存原值/明确结果 |
| `agent_type` | VARCHAR(60) | 否 | `—` | 领域字段：agent_type；按本模型语义保存原值/明确结果 |
| `context` | JSONB | 是 | `—` | 领域字段：context；按本模型语义保存原值/明确结果 |
| `started_at` | TIMESTAMP WITH TIME ZONE | 否 | `—` | 领域字段：started_at；按本模型语义保存原值/明确结果 |
| `finished_at` | TIMESTAMP WITH TIME ZONE | 是 | `—` | 领域字段：finished_at；按本模型语义保存原值/明确结果 |
| `status` | VARCHAR(20) | 否 | `—` | 领域字段：status；按本模型语义保存原值/明确结果 |
| `duration_ms` | INTEGER | 是 | `—` | 领域字段：duration_ms；按本模型语义保存原值/明确结果 |
| `result_summary` | TEXT | 是 | `—` | 领域字段：result_summary；按本模型语义保存原值/明确结果 |
| `error_summary` | TEXT | 是 | `—` | 领域字段：error_summary；按本模型语义保存原值/明确结果 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |
| `updated_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 当前投影更新时间，ORM维护；直接SQL调用者必须显式更新 |

## Asset `app.assets`

授权资产的轻量身份、owner和演示标识，未实现扫描器

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `name` | TEXT | 否 | `—` | 领域字段：name；按本模型语义保存原值/明确结果 |
| `asset_type` | VARCHAR(40) | 否 | `—` | 领域字段：asset_type；按本模型语义保存原值/明确结果 |
| `owner_principal` | VARCHAR(150) | 否 | `—` | 领域字段：owner_principal；按本模型语义保存原值/明确结果 |
| `is_demo` | BOOLEAN | 否 | `false` | 领域字段：is_demo；按本模型语义保存原值/明确结果 |
| `deleted_at` | TIMESTAMP WITH TIME ZONE | 是 | `—` | 领域字段：deleted_at；按本模型语义保存原值/明确结果 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |
| `updated_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 当前投影更新时间，ORM维护；直接SQL调用者必须显式更新 |

## AiSecurityCategory `core.ai_security_categories`

解释性AI风险分类目录，无伪造分类评分

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `category_key` | VARCHAR(80) | 否 | `—` | 领域字段：category_key；按本模型语义保存原值/明确结果 |
| `name` | TEXT | 否 | `—` | 领域字段：name；按本模型语义保存原值/明确结果 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## Product `core.products`

面向用户的产品身份，与分发生态包分开

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `canonical_key` | VARCHAR(200) | 否 | `—` | 领域字段：canonical_key；按本模型语义保存原值/明确结果 |
| `canonical_name` | TEXT | 否 | `—` | 领域字段：canonical_name；按本模型语义保存原值/明确结果 |
| `vendor` | TEXT | 是 | `—` | 领域字段：vendor；按本模型语义保存原值/明确结果 |
| `product_type` | VARCHAR(40) | 否 | `software` | 领域字段：product_type；按本模型语义保存原值/明确结果 |
| `homepage` | TEXT | 是 | `—` | 领域字段：homepage；按本模型语义保存原值/明确结果 |
| `deleted_at` | TIMESTAMP WITH TIME ZONE | 是 | `—` | 领域字段：deleted_at；按本模型语义保存原值/明确结果 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |
| `updated_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 当前投影更新时间，ORM维护；直接SQL调用者必须显式更新 |

## Vulnerability `core.vulnerabilities`

去重后的问题主体，不承载全部富化字段

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `canonical_id` | VARCHAR(150) | 否 | `—` | 领域字段：canonical_id；按本模型语义保存原值/明确结果 |
| `title` | TEXT | 否 | `—` | 领域字段：title；按本模型语义保存原值/明确结果 |
| `description` | TEXT | 是 | `—` | 领域字段：description；按本模型语义保存原值/明确结果 |
| `published_at` | TIMESTAMP WITH TIME ZONE | 是 | `—` | 来源发布日期，可未知 |
| `modified_at` | TIMESTAMP WITH TIME ZONE | 是 | `—` | 来源修改时间，可未知 |
| `status` | VARCHAR(20) | 否 | `unknown` | 领域字段：status；按本模型语义保存原值/明确结果 |
| `primary_severity` | VARCHAR(20) | 否 | `unknown` | 领域字段：primary_severity；按本模型语义保存原值/明确结果 |
| `revision` | INTEGER | 否 | `1` | 领域字段：revision；按本模型语义保存原值/明确结果 |
| `deleted_at` | TIMESTAMP WITH TIME ZONE | 是 | `—` | 领域字段：deleted_at；按本模型语义保存原值/明确结果 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |
| `updated_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 当前投影更新时间，ORM维护；直接SQL调用者必须显式更新 |

## Weakness `core.weaknesses`

CWE身份；不猜缺失分类

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `cwe_id` | VARCHAR(30) | 否 | `—` | 领域字段：cwe_id；按本模型语义保存原值/明确结果 |
| `name` | TEXT | 否 | `—` | 领域字段：name；按本模型语义保存原值/明确结果 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## EvaluationDataset `evaluation.datasets`

隔离评测集合、split/as_of/rubric和冻结hash

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `dataset_key` | VARCHAR(120) | 否 | `—` | 领域字段：dataset_key；按本模型语义保存原值/明确结果 |
| `revision_hash` | VARCHAR(64) | 否 | `—` | 领域字段：revision_hash；按本模型语义保存原值/明确结果 |
| `task_type` | VARCHAR(40) | 否 | `—` | 领域字段：task_type；按本模型语义保存原值/明确结果 |
| `split` | VARCHAR(20) | 否 | `—` | 领域字段：split；按本模型语义保存原值/明确结果 |
| `as_of` | TIMESTAMP WITH TIME ZONE | 否 | `—` | 领域字段：as_of；按本模型语义保存原值/明确结果 |
| `frozen_at` | TIMESTAMP WITH TIME ZONE | 是 | `—` | 领域字段：frozen_at；按本模型语义保存原值/明确结果 |
| `rubric_version` | VARCHAR(100) | 否 | `—` | 领域字段：rubric_version；按本模型语义保存原值/明确结果 |
| `description` | TEXT | 否 | `—` | 领域字段：description；按本模型语义保存原值/明确结果 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## Source `raw.sources`

注册来源/类别/权威范围/覆盖与checkpoint，研究检查时间不充当运行成功

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `source_key` | VARCHAR(100) | 否 | `—` | 领域字段：source_key；按本模型语义保存原值/明确结果 |
| `name` | TEXT | 否 | `—` | 领域字段：name；按本模型语义保存原值/明确结果 |
| `source_type` | VARCHAR(40) | 否 | `—` | 领域字段：source_type；按本模型语义保存原值/明确结果 |
| `category` | VARCHAR(60) | 否 | `—` | 领域字段：category；按本模型语义保存原值/明确结果 |
| `authority_level` | VARCHAR(20) | 否 | `—` | 领域字段：authority_level；按本模型语义保存原值/明确结果 |
| `authority_scope` | TEXT | 否 | `—` | 领域字段：authority_scope；按本模型语义保存原值/明确结果 |
| `acquisition_method` | VARCHAR(30) | 否 | `—` | 领域字段：acquisition_method；按本模型语义保存原值/明确结果 |
| `base_url` | TEXT | 否 | `—` | 领域字段：base_url；按本模型语义保存原值/明确结果 |
| `enabled` | BOOLEAN | 否 | `false` | 领域字段：enabled；按本模型语义保存原值/明确结果 |
| `update_interval` | INTEGER | 否 | `3600` | 领域字段：update_interval；按本模型语义保存原值/明确结果 |
| `last_sync_at` | TIMESTAMP WITH TIME ZONE | 是 | `—` | 领域字段：last_sync_at；按本模型语义保存原值/明确结果 |
| `last_success_at` | TIMESTAMP WITH TIME ZONE | 是 | `—` | 领域字段：last_success_at；按本模型语义保存原值/明确结果 |
| `status` | VARCHAR(20) | 否 | `planned` | 领域字段：status；按本模型语义保存原值/明确结果 |
| `license_scope` | TEXT | 否 | `unknown` | 领域字段：license_scope；按本模型语义保存原值/明确结果 |
| `checkpoint` | JSONB | 是 | `—` | 领域字段：checkpoint；按本模型语义保存原值/明确结果 |
| `coverage_scope` | JSONB | 是 | `—` | 领域字段：coverage_scope；按本模型语义保存原值/明确结果 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |
| `updated_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 当前投影更新时间，ORM维护；直接SQL调用者必须显式更新 |

## ToolCallRecord `app.tool_call_records`

完成/失败/timeout工具事件，结构化输入输出摘要，不保存私有思维

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `agent_run_id` | UUID | 否 | `—` | 领域字段：agent_run_id；按本模型语义保存原值/明确结果；FK app.agent_runs.id |
| `sequence_no` | INTEGER | 否 | `—` | 领域字段：sequence_no；按本模型语义保存原值/明确结果 |
| `attempt` | INTEGER | 否 | `1` | 领域字段：attempt；按本模型语义保存原值/明确结果 |
| `tool_name` | VARCHAR(100) | 否 | `—` | 领域字段：tool_name；按本模型语义保存原值/明确结果 |
| `input_summary` | JSONB | 是 | `—` | 领域字段：input_summary；按本模型语义保存原值/明确结果 |
| `output_summary` | JSONB | 是 | `—` | 领域字段：output_summary；按本模型语义保存原值/明确结果 |
| `started_at` | TIMESTAMP WITH TIME ZONE | 否 | `—` | 领域字段：started_at；按本模型语义保存原值/明确结果 |
| `finished_at` | TIMESTAMP WITH TIME ZONE | 是 | `—` | 领域字段：finished_at；按本模型语义保存原值/明确结果 |
| `duration_ms` | INTEGER | 是 | `—` | 领域字段：duration_ms；按本模型语义保存原值/明确结果 |
| `status` | VARCHAR(20) | 否 | `—` | 领域字段：status；按本模型语义保存原值/明确结果 |
| `error_summary` | TEXT | 是 | `—` | 领域字段：error_summary；按本模型语义保存原值/明确结果 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## ExternalIdentifier `core.external_identifiers`

命名空间内唯一的外部身份，公告身份不等于单一漏洞

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `namespace` | VARCHAR(120) | 否 | `global` | 领域字段：namespace；按本模型语义保存原值/明确结果 |
| `identifier_type` | VARCHAR(30) | 否 | `—` | 领域字段：identifier_type；按本模型语义保存原值/明确结果 |
| `identifier_value` | TEXT | 否 | `—` | 领域字段：identifier_value；按本模型语义保存原值/明确结果 |
| `normalized_value` | TEXT | 否 | `—` | 领域字段：normalized_value；按本模型语义保存原值/明确结果 |
| `source_id` | UUID | 否 | `—` | 注册Source外键，原publisher另存；FK raw.sources.id |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## PackageIdentifier `core.package_identifiers`

生态/namespace/包名/PURL的分发身份，CPE/repository作为补充

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `product_id` | UUID | 否 | `—` | 产品外键，生态包另分；FK core.products.id |
| `ecosystem` | VARCHAR(40) | 否 | `—` | 领域字段：ecosystem；按本模型语义保存原值/明确结果 |
| `namespace` | VARCHAR(200) | 否 | `` | 领域字段：namespace；按本模型语义保存原值/明确结果 |
| `package_name` | VARCHAR(300) | 否 | `—` | 领域字段：package_name；按本模型语义保存原值/明确结果 |
| `purl` | TEXT | 否 | `—` | 领域字段：purl；按本模型语义保存原值/明确结果 |
| `cpe` | TEXT | 是 | `—` | 领域字段：cpe；按本模型语义保存原值/明确结果 |
| `repository` | TEXT | 是 | `—` | 领域字段：repository；按本模型语义保存原值/明确结果 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## ProductAlias `core.product_aliases`

有来源的名称候选；重名可歧义，未审别名不授权自动合并

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `product_id` | UUID | 否 | `—` | 产品外键，生态包另分；FK core.products.id |
| `source_id` | UUID | 否 | `—` | 注册Source外键，原publisher另存；FK raw.sources.id |
| `alias` | TEXT | 否 | `—` | 领域字段：alias；按本模型语义保存原值/明确结果 |
| `normalized_alias` | TEXT | 否 | `—` | 领域字段：normalized_alias；按本模型语义保存原值/明确结果 |
| `alias_type` | VARCHAR(30) | 否 | `—` | 领域字段：alias_type；按本模型语义保存原值/明确结果 |
| `namespace` | VARCHAR(80) | 否 | `—` | 领域字段：namespace；按本模型语义保存原值/明确结果 |
| `verification_status` | VARCHAR(20) | 否 | `pending` | 四态当前投影/源候选态，严重度独立 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## Reference `core.references`

原始URL及经明确规则形成的canonical URL

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `url` | TEXT | 否 | `—` | 领域字段：url；按本模型语义保存原值/明确结果 |
| `canonical_url` | TEXT | 否 | `—` | 领域字段：canonical_url；按本模型语义保存原值/明确结果 |
| `title` | TEXT | 是 | `—` | 领域字段：title；按本模型语义保存原值/明确结果 |
| `reference_type` | VARCHAR(30) | 否 | `—` | 领域字段：reference_type；按本模型语义保存原值/明确结果 |
| `source_id` | UUID | 否 | `—` | 注册Source外键，原publisher另存；FK raw.sources.id |
| `published_at` | TIMESTAMP WITH TIME ZONE | 是 | `—` | 来源发布日期，可未知 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## EvaluationCase `evaluation.cases`

输入、真值状态、来源快照、lineage分组，draft不是gold

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `dataset_id` | UUID | 否 | `—` | 领域字段：dataset_id；按本模型语义保存原值/明确结果；FK evaluation.datasets.id |
| `case_key` | VARCHAR(150) | 否 | `—` | 领域字段：case_key；按本模型语义保存原值/明确结果 |
| `input_json` | JSONB | 否 | `—` | 领域字段：input_json；按本模型语义保存原值/明确结果 |
| `ground_truth` | JSONB | 是 | `—` | 人工确认真值，可unknown/null |
| `ground_truth_status` | VARCHAR(20) | 否 | `draft` | draft/validated/unknown；draft不得算gold |
| `adjudicator` | VARCHAR(150) | 是 | `—` | 领域字段：adjudicator；按本模型语义保存原值/明确结果 |
| `ground_truth_reason` | TEXT | 是 | `—` | 领域字段：ground_truth_reason；按本模型语义保存原值/明确结果 |
| `evidence_snapshot` | JSONB | 否 | `—` | 领域字段：evidence_snapshot；按本模型语义保存原值/明确结果 |
| `lineage_group` | VARCHAR(200) | 否 | `—` | 领域字段：lineage_group；按本模型语义保存原值/明确结果 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## EvaluationRun `evaluation.runs`

固定数据集/代码/模型/配置与环境的一次已结束评测

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `dataset_id` | UUID | 否 | `—` | 领域字段：dataset_id；按本模型语义保存原值/明确结果；FK evaluation.datasets.id |
| `started_at` | TIMESTAMP WITH TIME ZONE | 否 | `—` | 领域字段：started_at；按本模型语义保存原值/明确结果 |
| `finished_at` | TIMESTAMP WITH TIME ZONE | 否 | `—` | 领域字段：finished_at；按本模型语义保存原值/明确结果 |
| `status` | VARCHAR(20) | 否 | `—` | 领域字段：status；按本模型语义保存原值/明确结果 |
| `code_revision` | VARCHAR(100) | 否 | `—` | 领域字段：code_revision；按本模型语义保存原值/明确结果 |
| `model_version` | VARCHAR(150) | 是 | `—` | 领域字段：model_version；按本模型语义保存原值/明确结果 |
| `configuration` | JSONB | 否 | `—` | 领域字段：configuration；按本模型语义保存原值/明确结果 |
| `environment` | JSONB | 否 | `—` | 领域字段：environment；按本模型语义保存原值/明确结果 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## RawDocument `raw.raw_documents`

不可变源内容修订与准确字节hash，未知字段和原始出版时间并存

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `source_id` | UUID | 否 | `—` | 注册Source外键，原publisher另存；FK raw.sources.id |
| `external_id` | TEXT | 否 | `—` | 领域字段：external_id；按本模型语义保存原值/明确结果 |
| `source_url` | TEXT | 否 | `—` | 领域字段：source_url；按本模型语义保存原值/明确结果 |
| `published_at` | TIMESTAMP WITH TIME ZONE | 是 | `—` | 来源发布日期，可未知 |
| `modified_at` | TIMESTAMP WITH TIME ZONE | 是 | `—` | 来源修改时间，可未知 |
| `retrieved_at` | TIMESTAMP WITH TIME ZONE | 否 | `—` | 成功取得原文/当前观察UTC |
| `content_type` | VARCHAR(100) | 否 | `—` | 领域字段：content_type；按本模型语义保存原值/明确结果 |
| `raw_payload` | BYTEA | 否 | `—` | 准确entity字节BYTEA，最大16MiB；不执行内容 |
| `parsed_payload` | JSONB | 是 | `—` | 可选JSON解析缓存，不用于计算原文字节hash |
| `content_hash` | VARCHAR(64) | 否 | `—` | 准确raw字节SHA256；不证明发布者或事实真伪 |
| `completeness` | VARCHAR(20) | 否 | `unknown` | 领域字段：completeness；按本模型语义保存原值/明确结果 |
| `publisher` | TEXT | 否 | `—` | 领域字段：publisher；按本模型语义保存原值/明确结果 |
| `license_scope` | TEXT | 否 | `unknown` | 领域字段：license_scope；按本模型语义保存原值/明确结果 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## SyncRun `raw.sync_runs`

一次真实同步及分类计数/游标/缺口，失败不推进完整成功

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `source_id` | UUID | 否 | `—` | 注册Source外键，原publisher另存；FK raw.sources.id |
| `started_at` | TIMESTAMP WITH TIME ZONE | 否 | `—` | 领域字段：started_at；按本模型语义保存原值/明确结果 |
| `finished_at` | TIMESTAMP WITH TIME ZONE | 是 | `—` | 领域字段：finished_at；按本模型语义保存原值/明确结果 |
| `status` | VARCHAR(20) | 否 | `queued` | 领域字段：status；按本模型语义保存原值/明确结果 |
| `records_fetched` | INTEGER | 否 | `0` | 领域字段：records_fetched；按本模型语义保存原值/明确结果 |
| `records_created` | INTEGER | 否 | `0` | 领域字段：records_created；按本模型语义保存原值/明确结果 |
| `records_updated` | INTEGER | 否 | `0` | 领域字段：records_updated；按本模型语义保存原值/明确结果 |
| `records_skipped` | INTEGER | 否 | `0` | 领域字段：records_skipped；按本模型语义保存原值/明确结果 |
| `records_failed` | INTEGER | 否 | `0` | 领域字段：records_failed；按本模型语义保存原值/明确结果 |
| `cursor_before` | JSONB | 是 | `—` | 领域字段：cursor_before；按本模型语义保存原值/明确结果 |
| `cursor_after` | JSONB | 是 | `—` | 领域字段：cursor_after；按本模型语义保存原值/明确结果 |
| `mode` | VARCHAR(20) | 否 | `incremental` | 领域字段：mode；按本模型语义保存原值/明确结果 |
| `coverage_scope` | JSONB | 是 | `—` | 领域字段：coverage_scope；按本模型语义保存原值/明确结果 |
| `known_gaps` | JSONB | 是 | `—` | 领域字段：known_gaps；按本模型语义保存原值/明确结果 |
| `error_summary` | TEXT | 是 | `—` | 领域字段：error_summary；按本模型语义保存原值/明确结果 |
| `retry_of_id` | UUID | 是 | `—` | 领域字段：retry_of_id；按本模型语义保存原值/明确结果；FK raw.sync_runs.id |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## AssetComponent `app.asset_components`

精确/原始版本、包身份及库存修订；歧义可null

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `asset_id` | UUID | 否 | `—` | 领域字段：asset_id；按本模型语义保存原值/明确结果；FK app.assets.id |
| `product_id` | UUID | 是 | `—` | 产品外键，生态包另分；FK core.package_identifiers.product_id, core.products.id |
| `package_identifier_id` | UUID | 是 | `—` | 已解析生态包身份外键；FK core.package_identifiers.id |
| `version` | TEXT | 是 | `—` | 领域字段：version；按本模型语义保存原值/明确结果 |
| `raw_package_name` | TEXT | 是 | `—` | 领域字段：raw_package_name；按本模型语义保存原值/明确结果 |
| `source` | VARCHAR(20) | 否 | `manual` | 领域字段：source；按本模型语义保存原值/明确结果 |
| `inventory_revision` | INTEGER | 否 | `1` | 组件库存乐观修订 |
| `identity_status` | VARCHAR(20) | 否 | `unknown` | 领域字段：identity_status；按本模型语义保存原值/明确结果 |
| `deleted_at` | TIMESTAMP WITH TIME ZONE | 是 | `—` | 领域字段：deleted_at；按本模型语义保存原值/明确结果 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |
| `updated_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 当前投影更新时间，ORM维护；直接SQL调用者必须显式更新 |

## EvaluationResult `evaluation.results`

每题prediction/correct/status/完整latency与rubric，失败不移除分母

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `dataset_id` | UUID | 否 | `—` | 领域字段：dataset_id；按本模型语义保存原值/明确结果；FK evaluation.cases.dataset_id, evaluation.datasets.id, evaluation.runs.dataset_id |
| `run_id` | UUID | 否 | `—` | 领域字段：run_id；按本模型语义保存原值/明确结果；FK evaluation.runs.id |
| `case_id` | UUID | 否 | `—` | 领域字段：case_id；按本模型语义保存原值/明确结果；FK evaluation.cases.id |
| `prediction` | JSONB | 是 | `—` | 领域字段：prediction；按本模型语义保存原值/明确结果 |
| `correct` | BOOLEAN | 是 | `—` | 逐题判定，可未知；不能把timeout默认为正确 |
| `status` | VARCHAR(20) | 否 | `—` | 领域字段：status；按本模型语义保存原值/明确结果 |
| `latency_ms` | INTEGER | 否 | `—` | 完整测量时延毫秒，非首token时间 |
| `rubric_score` | INTEGER | 是 | `—` | 领域字段：rubric_score；按本模型语义保存原值/明确结果 |
| `error_summary` | TEXT | 是 | `—` | 领域字段：error_summary；按本模型语义保存原值/明确结果 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## EpssSnapshot `intel.epss_snapshots`

每日分数/percentile/model及更正raw修订，缺失不填0

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `vulnerability_id` | UUID | 否 | `—` | 问题主体外键，非一份源记录；FK core.vulnerabilities.id |
| `source_id` | UUID | 否 | `—` | 注册Source外键，原publisher另存；FK raw.sources.id |
| `raw_document_id` | UUID | 否 | `—` | 不可变原文版本外键；FK raw.raw_documents.id |
| `score` | NUMERIC(9, 8) | 否 | `—` | 领域字段：score；按本模型语义保存原值/明确结果 |
| `percentile` | NUMERIC(9, 8) | 是 | `—` | 领域字段：percentile；按本模型语义保存原值/明确结果 |
| `score_date` | DATE | 否 | `—` | 领域字段：score_date；按本模型语义保存原值/明确结果 |
| `observed_at` | TIMESTAMP WITH TIME ZONE | 否 | `—` | 源声明的观察/模型日期上下文，UTC |
| `model_version` | VARCHAR(60) | 否 | `—` | 领域字段：model_version；按本模型语义保存原值/明确结果 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## KnowledgeDocument `intel.knowledge_documents`

论文/公告/分析/事件/标准/政策，保留类型/版次/发布机关/许可

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `source_id` | UUID | 否 | `—` | 注册Source外键，原publisher另存；FK raw.sources.id |
| `raw_document_id` | UUID | 否 | `—` | 不可变原文版本外键；FK raw.raw_documents.id |
| `external_id` | TEXT | 否 | `—` | 领域字段：external_id；按本模型语义保存原值/明确结果 |
| `document_type` | VARCHAR(20) | 否 | `—` | 领域字段：document_type；按本模型语义保存原值/明确结果 |
| `title` | TEXT | 否 | `—` | 领域字段：title；按本模型语义保存原值/明确结果 |
| `content` | TEXT | 是 | `—` | 领域字段：content；按本模型语义保存原值/明确结果 |
| `url` | TEXT | 否 | `—` | 领域字段：url；按本模型语义保存原值/明确结果 |
| `edition` | VARCHAR(200) | 否 | `—` | 领域字段：edition；按本模型语义保存原值/明确结果 |
| `authors` | JSONB | 是 | `—` | 领域字段：authors；按本模型语义保存原值/明确结果 |
| `publisher` | TEXT | 是 | `—` | 领域字段：publisher；按本模型语义保存原值/明确结果 |
| `language` | VARCHAR(20) | 是 | `—` | 领域字段：language；按本模型语义保存原值/明确结果 |
| `publication_status` | VARCHAR(30) | 是 | `—` | 领域字段：publication_status；按本模型语义保存原值/明确结果 |
| `published_at` | TIMESTAMP WITH TIME ZONE | 是 | `—` | 来源发布日期，可未知 |
| `modified_at` | TIMESTAMP WITH TIME ZONE | 是 | `—` | 来源修改时间，可未知 |
| `effective_at` | TIMESTAMP WITH TIME ZONE | 是 | `—` | 领域字段：effective_at；按本模型语义保存原值/明确结果 |
| `license_scope` | TEXT | 否 | `unknown` | 领域字段：license_scope；按本模型语义保存原值/明确结果 |
| `revision` | INTEGER | 否 | `1` | 领域字段：revision；按本模型语义保存原值/明确结果 |
| `deleted_at` | TIMESTAMP WITH TIME ZONE | 是 | `—` | 领域字段：deleted_at；按本模型语义保存原值/明确结果 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |
| `updated_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 当前投影更新时间，ORM维护；直接SQL调用者必须显式更新 |

## KnownExploitation `intel.known_exploitation`

完整目录下的收录/未在该次目录/未知，不以false宣告没被利用

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `vulnerability_id` | UUID | 否 | `—` | 问题主体外键，非一份源记录；FK core.vulnerabilities.id |
| `source_id` | UUID | 否 | `—` | 注册Source外键，原publisher另存；FK raw.sources.id |
| `raw_document_id` | UUID | 否 | `—` | 不可变原文版本外键；FK raw.raw_documents.id |
| `known_exploited` | BOOLEAN | 是 | `—` | 领域字段：known_exploited；按本模型语义保存原值/明确结果 |
| `catalog_status` | VARCHAR(30) | 否 | `—` | 领域字段：catalog_status；按本模型语义保存原值/明确结果 |
| `catalog_complete` | BOOLEAN | 否 | `false` | 领域字段：catalog_complete；按本模型语义保存原值/明确结果 |
| `catalog_version` | TEXT | 否 | `—` | 领域字段：catalog_version；按本模型语义保存原值/明确结果 |
| `observed_at` | TIMESTAMP WITH TIME ZONE | 否 | `—` | 源声明的观察/模型日期上下文，UTC |
| `date_added` | DATE | 是 | `—` | 领域字段：date_added；按本模型语义保存原值/明确结果 |
| `due_date` | DATE | 是 | `—` | 领域字段：due_date；按本模型语义保存原值/明确结果 |
| `required_action` | TEXT | 是 | `—` | 领域字段：required_action；按本模型语义保存原值/明确结果 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## SourceObservation `raw.source_observations`

某次获取或标准化完成观察，源/原文/locator/lineage/normalizer独立保留

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `source_id` | UUID | 否 | `—` | 注册Source外键，原publisher另存；FK raw.raw_documents.source_id, raw.sources.id, raw.sync_runs.source_id |
| `raw_document_id` | UUID | 是 | `—` | 不可变原文版本外键；FK raw.raw_documents.id |
| `sync_run_id` | UUID | 是 | `—` | 领域字段：sync_run_id；按本模型语义保存原值/明确结果；FK raw.sync_runs.id |
| `external_id` | TEXT | 否 | `—` | 领域字段：external_id；按本模型语义保存原值/明确结果 |
| `record_type` | VARCHAR(30) | 否 | `—` | 领域字段：record_type；按本模型语义保存原值/明确结果 |
| `retrieved_at` | TIMESTAMP WITH TIME ZONE | 否 | `—` | 成功取得原文/当前观察UTC |
| `http_status` | INTEGER | 是 | `—` | 领域字段：http_status；按本模型语义保存原值/明确结果 |
| `raw_locator` | JSONB | 是 | `—` | 领域字段：raw_locator；按本模型语义保存原值/明确结果 |
| `lineage_key` | TEXT | 否 | `—` | 原发布依赖组，镜像/转载不能增加独立票 |
| `publisher` | TEXT | 否 | `—` | 领域字段：publisher；按本模型语义保存原值/明确结果 |
| `upstream_observation_id` | UUID | 是 | `—` | 领域字段：upstream_observation_id；按本模型语义保存原值/明确结果；FK raw.source_observations.id |
| `normalizer_version` | VARCHAR(60) | 是 | `—` | 领域字段：normalizer_version；按本模型语义保存原值/明确结果 |
| `normalized_payload` | JSONB | 是 | `—` | 领域字段：normalized_payload；按本模型语义保存原值/明确结果 |
| `parse_status` | VARCHAR(20) | 否 | `pending` | parsed/unsupported/failed，非确定性猜测 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## AffectedVersionRange `core.affected_version_ranges`

某源/包/分支的原范围和机器表示，失败/unsupported保持原文

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `vulnerability_id` | UUID | 否 | `—` | 问题主体外键，非一份源记录；FK core.vulnerabilities.id |
| `product_id` | UUID | 否 | `—` | 产品外键，生态包另分；FK core.package_identifiers.product_id, core.products.id |
| `package_identifier_id` | UUID | 否 | `—` | 已解析生态包身份外键；FK core.package_identifiers.id |
| `source_id` | UUID | 否 | `—` | 注册Source外键，原publisher另存；FK raw.sources.id |
| `observation_id` | UUID | 否 | `—` | 当前字段来源/标准化观察外键；FK raw.source_observations.id |
| `introduced` | TEXT | 是 | `—` | 起点；OSV 0为无已知下界标记，不是软件0.0.0 |
| `fixed` | TEXT | 是 | `—` | 明确修复边界，不从last_affected推断 |
| `last_affected` | TEXT | 是 | `—` | 最后受影响，包含上界，与fixed不同 |
| `limit_version` | TEXT | 是 | `—` | limit排他边界，与已修复断言不同 |
| `range_type` | VARCHAR(30) | 否 | `—` | 领域字段：range_type；按本模型语义保存原值/明确结果 |
| `raw_expression` | TEXT | 否 | `—` | 完整原始版本表达，不因解析失败丢弃 |
| `events` | JSONB | 是 | `—` | 规范事件序列；introduced=0等原始语义保留 |
| `explicit_versions` | JSONB | 是 | `—` | 源明确列举版本；null未知，[]只用于观测空集 |
| `branch` | TEXT | 是 | `—` | 领域字段：branch；按本模型语义保存原值/明确结果 |
| `scope_key` | VARCHAR(128) | 否 | `—` | 确定性范围标识，比较前核对生态包/分支/评分版本/日期 |
| `parse_status` | VARCHAR(20) | 否 | `—` | parsed/unsupported/failed，非确定性猜测 |
| `parse_reason` | TEXT | 是 | `—` | 领域字段：parse_reason；按本模型语义保存原值/明确结果 |
| `parser_version` | VARCHAR(60) | 否 | `—` | 领域字段：parser_version；按本模型语义保存原值/明确结果 |
| `verification_status` | VARCHAR(20) | 否 | `pending` | 四态当前投影/源候选态，严重度独立 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## AiRelevanceAssessment `core.ai_relevance_assessments`

relevant/irrelevant/uncertain、方法/版本/理由及时间

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `vulnerability_id` | UUID | 是 | `—` | 问题主体外键，非一份源记录；FK core.vulnerabilities.id |
| `knowledge_document_id` | UUID | 是 | `—` | 领域字段：knowledge_document_id；按本模型语义保存原值/明确结果；FK intel.knowledge_documents.id |
| `method` | VARCHAR(20) | 否 | `—` | 领域字段：method；按本模型语义保存原值/明确结果 |
| `result` | VARCHAR(20) | 否 | `—` | 领域字段：result；按本模型语义保存原值/明确结果 |
| `reason_summary` | TEXT | 否 | `—` | 可审计结论理由，不是模型私有Chain-of-Thought |
| `model_version` | VARCHAR(100) | 是 | `—` | 领域字段：model_version；按本模型语义保存原值/明确结果 |
| `evaluated_at` | TIMESTAMP WITH TIME ZONE | 否 | `—` | 领域字段：evaluated_at；按本模型语义保存原值/明确结果 |
| `observation_id` | UUID | 是 | `—` | 当前字段来源/标准化观察外键；FK raw.source_observations.id |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## CvssAssessment `core.cvss_assessments`

来源/评估版本/范围独立评分，选择由typed Claim表达

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `vulnerability_id` | UUID | 否 | `—` | 问题主体外键，非一份源记录；FK core.vulnerabilities.id |
| `source_id` | UUID | 否 | `—` | 注册Source外键，原publisher另存；FK raw.sources.id |
| `observation_id` | UUID | 否 | `—` | 当前字段来源/标准化观察外键；FK raw.source_observations.id |
| `version` | VARCHAR(10) | 否 | `—` | 领域字段：version；按本模型语义保存原值/明确结果 |
| `vector` | TEXT | 是 | `—` | 领域字段：vector；按本模型语义保存原值/明确结果 |
| `base_score` | NUMERIC(3, 1) | 否 | `—` | 领域字段：base_score；按本模型语义保存原值/明确结果 |
| `severity` | VARCHAR(20) | 否 | `—` | 领域字段：severity；按本模型语义保存原值/明确结果 |
| `provider` | TEXT | 否 | `—` | 领域字段：provider；按本模型语义保存原值/明确结果 |
| `assessment_kind` | VARCHAR(40) | 否 | `base` | 领域字段：assessment_kind；按本模型语义保存原值/明确结果 |
| `scope_key` | VARCHAR(128) | 否 | `—` | 确定性范围标识，比较前核对生态包/分支/评分版本/日期 |
| `published_at` | TIMESTAMP WITH TIME ZONE | 是 | `—` | 来源发布日期，可未知 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## VulnerabilityIdentifier `core.vulnerability_identifiers`

精确身份关联；CVE单一归属，公告可连接多个漏洞

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `vulnerability_id` | UUID | 否 | `—` | 问题主体外键，非一份源记录；FK core.vulnerabilities.id |
| `identifier_id` | UUID | 否 | `—` | 领域字段：identifier_id；按本模型语义保存原值/明确结果；FK core.external_identifiers.id |
| `identifier_type` | VARCHAR(30) | 否 | `—` | 领域字段：identifier_type；按本模型语义保存原值/明确结果；FK core.external_identifiers.identifier_type |
| `observation_id` | UUID | 是 | `—` | 当前字段来源/标准化观察外键；FK raw.source_observations.id |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## VulnerabilityReference `core.vulnerability_references`

公告/引用对多漏洞的关联和原始观察

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `vulnerability_id` | UUID | 否 | `—` | 问题主体外键，非一份源记录；FK core.vulnerabilities.id |
| `reference_id` | UUID | 否 | `—` | 领域字段：reference_id；按本模型语义保存原值/明确结果；FK core.references.id |
| `observation_id` | UUID | 否 | `—` | 当前字段来源/标准化观察外键；FK raw.source_observations.id |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## VulnerabilityWeakness `core.vulnerability_weaknesses`

多CWE及各自来源观察

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `vulnerability_id` | UUID | 否 | `—` | 问题主体外键，非一份源记录；FK core.vulnerabilities.id |
| `weakness_id` | UUID | 否 | `—` | 领域字段：weakness_id；按本模型语义保存原值/明确结果；FK core.weaknesses.id |
| `observation_id` | UUID | 否 | `—` | 当前字段来源/标准化观察外键；FK raw.source_observations.id |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## KnowledgeChunk `intel.knowledge_chunks`

冻结文档revision/chunker/index与原文定位，尚未切块或生成向量

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `document_id` | UUID | 否 | `—` | 领域字段：document_id；按本模型语义保存原值/明确结果；FK intel.knowledge_documents.id |
| `raw_document_id` | UUID | 否 | `—` | 不可变原文版本外键；FK raw.raw_documents.id |
| `document_revision` | INTEGER | 否 | `—` | 领域字段：document_revision；按本模型语义保存原值/明确结果 |
| `chunk_index` | INTEGER | 否 | `—` | 领域字段：chunk_index；按本模型语义保存原值/明确结果 |
| `chunker_version` | VARCHAR(60) | 否 | `—` | 领域字段：chunker_version；按本模型语义保存原值/明确结果 |
| `content` | TEXT | 否 | `—` | 领域字段：content；按本模型语义保存原值/明确结果 |
| `content_hash` | VARCHAR(64) | 否 | `—` | 准确raw字节SHA256；不证明发布者或事实真伪 |
| `locator` | JSONB | 否 | `—` | 对当前raw版本有效的JSON Pointer/page/span等结构化定位 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## PatchCandidate `intel.patch_candidates`

完整commit/PR/release/fixed候选及包/分支适用关系

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `vulnerability_id` | UUID | 否 | `—` | 问题主体外键，非一份源记录；FK core.vulnerabilities.id |
| `product_id` | UUID | 否 | `—` | 产品外键，生态包另分；FK core.products.id |
| `source_id` | UUID | 否 | `—` | 注册Source外键，原publisher另存；FK raw.sources.id |
| `observation_id` | UUID | 否 | `—` | 当前字段来源/标准化观察外键；FK raw.source_observations.id |
| `patch_type` | VARCHAR(30) | 否 | `—` | 领域字段：patch_type；按本模型语义保存原值/明确结果 |
| `identity_key` | TEXT | 否 | `—` | 领域字段：identity_key；按本模型语义保存原值/明确结果 |
| `url` | TEXT | 是 | `—` | 领域字段：url；按本模型语义保存原值/明确结果 |
| `commit_sha` | VARCHAR(64) | 是 | `—` | 领域字段：commit_sha；按本模型语义保存原值/明确结果 |
| `release_version` | TEXT | 是 | `—` | 领域字段：release_version；按本模型语义保存原值/明确结果 |
| `branch` | TEXT | 否 | `` | 领域字段：branch；按本模型语义保存原值/明确结果 |
| `status` | VARCHAR(20) | 否 | `candidate` | 领域字段：status；按本模型语义保存原值/明确结果 |
| `first_seen_at` | TIMESTAMP WITH TIME ZONE | 否 | `—` | 领域字段：first_seen_at；按本模型语义保存原值/明确结果 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |
| `updated_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 当前投影更新时间，ORM维护；直接SQL调用者必须显式更新 |

## PocCandidate `intel.poc_candidates`

PoC线索；关联可信度与可用性分别保存，不执行代码

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `vulnerability_id` | UUID | 否 | `—` | 问题主体外键，非一份源记录；FK core.vulnerabilities.id |
| `source_id` | UUID | 否 | `—` | 注册Source外键，原publisher另存；FK raw.sources.id |
| `observation_id` | UUID | 否 | `—` | 当前字段来源/标准化观察外键；FK raw.source_observations.id |
| `url` | TEXT | 否 | `—` | 领域字段：url；按本模型语义保存原值/明确结果 |
| `canonical_url` | TEXT | 否 | `—` | 领域字段：canonical_url；按本模型语义保存原值/明确结果 |
| `repository` | TEXT | 是 | `—` | 领域字段：repository；按本模型语义保存原值/明确结果 |
| `commit` | TEXT | 是 | `—` | 领域字段：commit；按本模型语义保存原值/明确结果 |
| `author` | TEXT | 是 | `—` | 领域字段：author；按本模型语义保存原值/明确结果 |
| `candidate_type` | VARCHAR(40) | 否 | `—` | 领域字段：candidate_type；按本模型语义保存原值/明确结果 |
| `status` | VARCHAR(20) | 否 | `candidate` | 领域字段：status；按本模型语义保存原值/明确结果 |
| `usability_status` | VARCHAR(30) | 否 | `not_evaluated` | 领域字段：usability_status；按本模型语义保存原值/明确结果 |
| `first_seen_at` | TIMESTAMP WITH TIME ZONE | 否 | `—` | 领域字段：first_seen_at；按本模型语义保存原值/明确结果 |
| `last_seen_at` | TIMESTAMP WITH TIME ZONE | 否 | `—` | 领域字段：last_seen_at；按本模型语义保存原值/明确结果 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |
| `updated_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 当前投影更新时间，ORM维护；直接SQL调用者必须显式更新 |

## VulnerabilityAiCategory `core.vulnerability_ai_categories`

多类别关系及评估依据

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `vulnerability_id` | UUID | 否 | `—` | 问题主体外键，非一份源记录；FK core.vulnerabilities.id |
| `category_id` | UUID | 否 | `—` | 领域字段：category_id；按本模型语义保存原值/明确结果；FK core.ai_security_categories.id |
| `assessment_id` | UUID | 否 | `—` | 领域字段：assessment_id；按本模型语义保存原值/明确结果；FK core.ai_relevance_assessments.id |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## Claim `intel.claims`

带scope的结构化候选/采用结论，当前投影与历史核验分开

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `claim_key` | VARCHAR(200) | 否 | `—` | 领域字段：claim_key；按本模型语义保存原值/明确结果 |
| `vulnerability_id` | UUID | 是 | `—` | 问题主体外键，非一份源记录；FK core.cvss_assessments.vulnerability_id, core.vulnerabilities.id, intel.patch_candidates.vulnerability_id, intel.poc_candidates.vulnerability_id |
| `knowledge_document_id` | UUID | 是 | `—` | 领域字段：knowledge_document_id；按本模型语义保存原值/明确结果；FK intel.knowledge_documents.id |
| `product_id` | UUID | 是 | `—` | 产品外键，生态包另分；FK core.products.id |
| `package_identifier_id` | UUID | 是 | `—` | 已解析生态包身份外键；FK core.package_identifiers.id |
| `range_id` | UUID | 是 | `—` | 领域字段：range_id；按本模型语义保存原值/明确结果；FK core.affected_version_ranges.id |
| `poc_candidate_id` | UUID | 是 | `—` | 领域字段：poc_candidate_id；按本模型语义保存原值/明确结果；FK intel.poc_candidates.id |
| `patch_candidate_id` | UUID | 是 | `—` | 领域字段：patch_candidate_id；按本模型语义保存原值/明确结果；FK intel.patch_candidates.id |
| `asset_component_id` | UUID | 是 | `—` | 领域字段：asset_component_id；按本模型语义保存原值/明确结果；FK app.asset_components.id |
| `cvss_assessment_id` | UUID | 是 | `—` | 领域字段：cvss_assessment_id；按本模型语义保存原值/明确结果；FK core.cvss_assessments.id |
| `claim_type` | VARCHAR(50) | 否 | `—` | 领域字段：claim_type；按本模型语义保存原值/明确结果 |
| `predicate` | VARCHAR(80) | 否 | `—` | 领域字段：predicate；按本模型语义保存原值/明确结果 |
| `value_json` | JSONB | 否 | `—` | 结构化命题值；不得由LLM补未知事实 |
| `scope_key` | VARCHAR(128) | 否 | `—` | 确定性范围标识，比较前核对生态包/分支/评分版本/日期 |
| `branch` | TEXT | 是 | `—` | 领域字段：branch；按本模型语义保存原值/明确结果 |
| `cvss_version` | VARCHAR(10) | 是 | `—` | 领域字段：cvss_version；按本模型语义保存原值/明确结果 |
| `assessment_kind` | VARCHAR(40) | 是 | `—` | 领域字段：assessment_kind；按本模型语义保存原值/明确结果 |
| `as_of_date` | DATE | 是 | `—` | 领域字段：as_of_date；按本模型语义保存原值/明确结果 |
| `verification_status` | VARCHAR(20) | 否 | `pending` | 四态当前投影/源候选态，严重度独立 |
| `adopted` | BOOLEAN | 否 | `false` | 当前展示选择，非删除其他来源 |
| `revision` | INTEGER | 否 | `1` | 领域字段：revision；按本模型语义保存原值/明确结果 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |
| `updated_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 当前投影更新时间，ORM维护；直接SQL调用者必须显式更新 |

## AssetVulnerabilityMatch `app.asset_vulnerability_matches`

三态影响、版本/库存/Claim/范围快照与理由，旧结果不可覆盖

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `asset_component_id` | UUID | 否 | `—` | 领域字段：asset_component_id；按本模型语义保存原值/明确结果；FK app.asset_components.id |
| `vulnerability_id` | UUID | 否 | `—` | 问题主体外键，非一份源记录；FK core.affected_version_ranges.vulnerability_id, core.vulnerabilities.id |
| `package_identifier_id` | UUID | 是 | `—` | 已解析生态包身份外键；FK app.asset_components.package_identifier_id, core.affected_version_ranges.package_identifier_id, core.package_identifiers.id |
| `matched_range_id` | UUID | 是 | `—` | 领域字段：matched_range_id；按本模型语义保存原值/明确结果；FK core.affected_version_ranges.id |
| `claim_id` | UUID | 是 | `—` | 带范围的命题外键；FK intel.claims.id |
| `match_status` | VARCHAR(20) | 否 | `—` | 领域字段：match_status；按本模型语义保存原值/明确结果 |
| `version_at_evaluation` | TEXT | 是 | `—` | 当时组件版本快照，非当前版本自动替换 |
| `component_revision` | INTEGER | 否 | `—` | 计算时库存修订，变化后旧match须标陈旧 |
| `claim_revision` | INTEGER | 否 | `—` | 被核验/回答/匹配采用的结论修订 |
| `matcher_version` | VARCHAR(60) | 否 | `—` | 领域字段：matcher_version；按本模型语义保存原值/明确结果 |
| `reason_summary` | TEXT | 否 | `—` | 可审计结论理由，不是模型私有Chain-of-Thought |
| `detected_at` | TIMESTAMP WITH TIME ZONE | 否 | `—` | 系统首次发现本事件时间，历史回补单列 |
| `last_evaluated_at` | TIMESTAMP WITH TIME ZONE | 否 | `—` | 领域字段：last_evaluated_at；按本模型语义保存原值/明确结果 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## ReviewTask `app.review_tasks`

围绕Claim的人工复核，P1工作状态、乐观revision和前后决定

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `claim_id` | UUID | 否 | `—` | 带范围的命题外键；FK intel.claims.id |
| `review_type` | VARCHAR(40) | 否 | `—` | 领域字段：review_type；按本模型语义保存原值/明确结果 |
| `priority` | INTEGER | 否 | `2` | 领域字段：priority；按本模型语义保存原值/明确结果 |
| `status` | VARCHAR(20) | 否 | `open` | 领域字段：status；按本模型语义保存原值/明确结果 |
| `reason` | TEXT | 否 | `—` | 领域字段：reason；按本模型语义保存原值/明确结果 |
| `assigned_to` | VARCHAR(150) | 是 | `—` | 领域字段：assigned_to；按本模型语义保存原值/明确结果 |
| `resolved_at` | TIMESTAMP WITH TIME ZONE | 是 | `—` | 领域字段：resolved_at；按本模型语义保存原值/明确结果 |
| `resolution` | VARCHAR(30) | 是 | `—` | 领域字段：resolution；按本模型语义保存原值/明确结果 |
| `resolution_note` | TEXT | 是 | `—` | 领域字段：resolution_note；按本模型语义保存原值/明确结果 |
| `before_state` | JSONB | 是 | `—` | 领域字段：before_state；按本模型语义保存原值/明确结果 |
| `after_state` | JSONB | 是 | `—` | 领域字段：after_state；按本模型语义保存原值/明确结果 |
| `revision` | INTEGER | 否 | `1` | 领域字段：revision；按本模型语义保存原值/明确结果 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |
| `updated_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 当前投影更新时间，ORM维护；直接SQL调用者必须显式更新 |

## Evidence `intel.evidence`

Claim支持/反驳/中立原文、immutable raw/observation、定位和lineage

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `claim_id` | UUID | 否 | `—` | 带范围的命题外键；FK intel.claims.id |
| `source_id` | UUID | 否 | `—` | 注册Source外键，原publisher另存；FK raw.raw_documents.source_id, raw.source_observations.source_id, raw.sources.id |
| `raw_document_id` | UUID | 否 | `—` | 不可变原文版本外键；FK raw.raw_documents.id, raw.source_observations.raw_document_id |
| `observation_id` | UUID | 否 | `—` | 当前字段来源/标准化观察外键；FK raw.source_observations.id |
| `scope_key` | VARCHAR(128) | 否 | `—` | 确定性范围标识，比较前核对生态包/分支/评分版本/日期；FK intel.claims.scope_key |
| `evidence_type` | VARCHAR(40) | 否 | `—` | 领域字段：evidence_type；按本模型语义保存原值/明确结果 |
| `stance` | VARCHAR(20) | 否 | `—` | support/contradict/neutral；范围不同不能填contradict |
| `excerpt` | TEXT | 否 | `—` | 源原文允许片段，不能由摘要替换 |
| `excerpt_hash` | VARCHAR(64) | 否 | `—` | 领域字段：excerpt_hash；按本模型语义保存原值/明确结果 |
| `source_url` | TEXT | 否 | `—` | 领域字段：source_url；按本模型语义保存原值/明确结果 |
| `published_at` | TIMESTAMP WITH TIME ZONE | 是 | `—` | 来源发布日期，可未知 |
| `retrieved_at` | TIMESTAMP WITH TIME ZONE | 否 | `—` | 成功取得原文/当前观察UTC |
| `locator` | JSONB | 否 | `—` | 对当前raw版本有效的JSON Pointer/page/span等结构化定位 |
| `locator_key` | VARCHAR(200) | 否 | `—` | 定位幂等键，应由canonical locator构造 |
| `observed_value` | JSONB | 是 | `—` | 该Evidence原生候选值，不覆盖Claim采用层 |
| `publisher` | TEXT | 否 | `—` | 领域字段：publisher；按本模型语义保存原值/明确结果 |
| `lineage_key` | TEXT | 否 | `—` | 原发布依赖组，镜像/转载不能增加独立票 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## KnowledgeVulnerabilityRelation `intel.knowledge_vulnerability_relations`

知识到漏洞的typed关系及Claim，不以相似度直接确认

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `knowledge_document_id` | UUID | 否 | `—` | 领域字段：knowledge_document_id；按本模型语义保存原值/明确结果；FK intel.knowledge_documents.id |
| `vulnerability_id` | UUID | 否 | `—` | 问题主体外键，非一份源记录；FK core.vulnerabilities.id |
| `claim_id` | UUID | 否 | `—` | 带范围的命题外键；FK intel.claims.id |
| `relation_type` | VARCHAR(50) | 否 | `—` | 领域字段：relation_type；按本模型语义保存原值/明确结果 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## VerificationResult `intel.verification_results`

不可变核验修订，记录四态、理由、执行者和采用值

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `claim_id` | UUID | 否 | `—` | 带范围的命题外键；FK intel.claims.id |
| `claim_revision` | INTEGER | 否 | `—` | 被核验/回答/匹配采用的结论修订 |
| `status` | VARCHAR(20) | 否 | `—` | 领域字段：status；按本模型语义保存原值/明确结果 |
| `verification_method` | VARCHAR(80) | 否 | `—` | 领域字段：verification_method；按本模型语义保存原值/明确结果 |
| `reason_summary` | TEXT | 否 | `—` | 可审计结论理由，不是模型私有Chain-of-Thought |
| `verified_at` | TIMESTAMP WITH TIME ZONE | 否 | `—` | 领域字段：verified_at；按本模型语义保存原值/明确结果 |
| `verified_by_type` | VARCHAR(20) | 否 | `—` | 领域字段：verified_by_type；按本模型语义保存原值/明确结果 |
| `verified_by_id` | VARCHAR(150) | 否 | `—` | 领域字段：verified_by_id；按本模型语义保存原值/明确结果 |
| `decision_key` | VARCHAR(200) | 否 | `—` | 领域字段：decision_key；按本模型语义保存原值/明确结果 |
| `adopted_value` | JSONB | 是 | `—` | 领域字段：adopted_value；按本模型语义保存原值/明确结果 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## AgentCitation `app.agent_citations`

回答断言对应Evidence及真实Claim核验revision，旧引用不漂移

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `agent_run_id` | UUID | 否 | `—` | 领域字段：agent_run_id；按本模型语义保存原值/明确结果；FK app.agent_runs.id |
| `evidence_id` | UUID | 否 | `—` | 领域字段：evidence_id；按本模型语义保存原值/明确结果；FK intel.evidence.id |
| `claim_id` | UUID | 否 | `—` | 带范围的命题外键；FK intel.claims.id, intel.evidence.claim_id, intel.verification_results.claim_id |
| `citation_index` | INTEGER | 否 | `—` | 领域字段：citation_index；按本模型语义保存原值/明确结果 |
| `claim_revision` | INTEGER | 否 | `—` | 被核验/回答/匹配采用的结论修订；FK intel.verification_results.claim_revision |
| `assertion_summary` | TEXT | 否 | `—` | 领域字段：assertion_summary；按本模型语义保存原值/明确结果 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## AuditLog `app.audit_logs`

actor/action/before/after/reason/request指纹的追加审计

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `actor` | VARCHAR(150) | 否 | `—` | 领域字段：actor；按本模型语义保存原值/明确结果 |
| `action` | VARCHAR(60) | 否 | `—` | 领域字段：action；按本模型语义保存原值/明确结果 |
| `claim_id` | UUID | 否 | `—` | 带范围的命题外键；FK intel.claims.id |
| `review_task_id` | UUID | 是 | `—` | 领域字段：review_task_id；按本模型语义保存原值/明确结果；FK app.review_tasks.id |
| `verification_result_id` | UUID | 是 | `—` | 领域字段：verification_result_id；按本模型语义保存原值/明确结果；FK intel.verification_results.id |
| `before_state` | JSONB | 否 | `—` | 领域字段：before_state；按本模型语义保存原值/明确结果 |
| `after_state` | JSONB | 否 | `—` | 领域字段：after_state；按本模型语义保存原值/明确结果 |
| `reason` | TEXT | 否 | `—` | 领域字段：reason；按本模型语义保存原值/明确结果 |
| `occurred_at` | TIMESTAMP WITH TIME ZONE | 否 | `—` | 业务发生/审计时间，原事件未知可null |
| `request_key` | VARCHAR(150) | 否 | `—` | actor范围幂等键 |
| `request_hash` | VARCHAR(64) | 否 | `—` | 同键完整请求指纹，不同载荷拒绝 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## IntelligenceEvent `intel.intelligence_events`

有主体与证据的业务变化，源发生时间与系统发现时间分开

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `event_key` | VARCHAR(200) | 否 | `—` | 领域字段：event_key；按本模型语义保存原值/明确结果 |
| `vulnerability_id` | UUID | 是 | `—` | 问题主体外键，非一份源记录；FK core.vulnerabilities.id |
| `knowledge_document_id` | UUID | 是 | `—` | 领域字段：knowledge_document_id；按本模型语义保存原值/明确结果；FK intel.knowledge_documents.id |
| `claim_id` | UUID | 是 | `—` | 带范围的命题外键；FK intel.claims.id |
| `evidence_id` | UUID | 是 | `—` | 领域字段：evidence_id；按本模型语义保存原值/明确结果；FK intel.evidence.id |
| `source_id` | UUID | 是 | `—` | 注册Source外键，原publisher另存；FK raw.sources.id |
| `event_type` | VARCHAR(50) | 否 | `—` | 领域字段：event_type；按本模型语义保存原值/明确结果 |
| `occurred_at` | TIMESTAMP WITH TIME ZONE | 是 | `—` | 业务发生/审计时间，原事件未知可null |
| `detected_at` | TIMESTAMP WITH TIME ZONE | 否 | `—` | 系统首次发现本事件时间，历史回补单列 |
| `summary` | TEXT | 否 | `—` | 领域字段：summary；按本模型语义保存原值/明确结果 |
| `payload` | JSONB | 是 | `—` | 领域字段：payload；按本模型语义保存原值/明确结果 |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |

## VerificationEvidence `intel.verification_evidence`

某次核验确实使用哪些同Claim Evidence，FK防串证据

| 字段 | PostgreSQL类型 | 可null | DB默认 | 语义/FK |
|---|---|---|---|---|
| `claim_id` | UUID | 否 | `—` | 带范围的命题外键；FK intel.claims.id, intel.evidence.claim_id, intel.verification_results.claim_id |
| `verification_result_id` | UUID | 否 | `—` | 领域字段：verification_result_id；按本模型语义保存原值/明确结果；FK intel.verification_results.id |
| `evidence_id` | UUID | 否 | `—` | 领域字段：evidence_id；按本模型语义保存原值/明确结果；FK intel.evidence.id |
| `id` | UUID | 否 | `gen_random_uuid()` | UUID主键，客户端/数据库均可生成；不代表来源原生ID |
| `created_at` | TIMESTAMP WITH TIME ZONE | 否 | `now()` | 本系统入库时间UTC，不能冒充发布 |
| `metadata` | JSONB | 否 | `'{}'::jsonb` | 非核心扩展；不得存Secret或模型隐藏思维 |
