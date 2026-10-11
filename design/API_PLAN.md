# API 计划

V0.1只读，开发时绑定localhost；HTTP bearer读令牌由服务端验证，不来自外部文档/模型。无public写入、任意fetch、自由SQL、PoC执行和模型endpoint。

| 操作 | 约定 |
|---|---|
| GET /health/live | 进程状态，不暴露secret |
| GET /health/ready | DB/必要blob访问可用才200，否则503 |
| GET /v1/vulnerabilities | product/package/AI/review/state/page limit；上限100；游标稳定排序first_seen+id |
| GET /v1/vulnerabilities/{cve_id} | source-qualified cvss/cwe/ranges/fixed/refs、claims、review_status、更新时间/coverage |
| GET /v1/vulnerabilities/{cve_id}/evidence | evidence ID、source、locator、excerpt/hash/时间和支持/反驳关系 |
| GET /v1/evidence/{uuid} | 限权定位结果；raw下载单独控制，不render HTML |
| GET /v1/vulnerabilities/{cve_id}/timeline | 修订/撤销/审核事件；未知将来类型保留 |

list/detail默认显示来源状态和PENDING_HUMAN，不将结构核验叫verified；verified_only过滤可选。版本影响查询先由内部Version Service测试，若V0.1公开则GET /v1/packages/impact?ecosystem=PyPI&name=&version=，返回affected/not_affected/unknown和range/evidence依据；UNKNOWN不是空列表。限包名/版本长度，不在GET中同步外查。

响应 envelope：schema_version/data/as_of/coverage/warnings；标准error code/message/request_id/retryable/details（无凭证）。坏参数422，权限401/403，不存在404，依赖不可用503。timestamps ISO8601+UTC，客户端不靠title作为ID。

V0.2预留语义Agent Tool：lookup_vulnerability/get_evidence/explain_conflict；可OpenAPI→Dify，不强制MCP。Candidate/Verification/Conflict/Asset/SBOM/RiskChange另设版本化资源，先保持claims/polarity/events，不提前写空端点或假的API响应。
