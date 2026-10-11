# Tool Contracts V1 — Phase7

这是后端服务封装契约；没有安装Dify或创建Agent。外部数据一律 UNTRUSTED_EXTERNAL_CONTENT，不能提升为系统指令。目标只能使用已有 vulnerability UUID/CVE。写操作由可信内部调用与事务控制，不能无鉴权公开成网络MCP。所有输出是结构化数据。

## investigate_vulnerability

- Purpose：通过 `EnrichmentService.run` 提供对应可追溯能力。
- Input：target_id / kind=all；offset≥0，分页limit为1..100；原始外部内容按数据接收。
- Output：EnrichmentResult[]；没有证据或数据不以零/false代替未知，状态区分 SUCCESS/PARTIAL/NO_RESULT/FAILED/CONFLICT 或标准Verification状态。
- Dependencies：当前目标、Phase6 observations；vendor→poc/patch/version。
- Evidence Produced：原始Source/Raw/Observation关联、locator/hash/stance/lineage；纯规则函数返回决策，由调用方持久化。
- Error Codes：TARGET_NOT_FOUND、PARSER_ERROR、SOURCE_HTTP_ERROR、SOURCE_TIMEOUT、RATE_LIMIT、REVISION_MISMATCH、EVIDENCE_INSUFFICIENT、OPEN_CONFLICT；只适用实际依赖，不把NO_RESULT当错误。
- Retryable：网络超时、429/403限流及部分5xx可重试；解析/标识/证据/修订错误需修正输入。只读查询可安全重试；写调用按claim/event/idempotency key防重复。
- Side Effects：可能追加原文、观察、候选、Claim/Evidence/Verification/Conflict/Review/Timeline/Job；网络读取无仓库代码执行；纯分类函数无副作用。
- Timeout：网络读30s，最多2次重试；GitHub搜索上限5/README3/Patch5；数据库statement30s。此为各请求/记录边界，不承诺整调查30秒完成；调度以小批次运行。
- Acceptance Criteria：目标/scope明确；输出结构可解析；检查来源/as_of可回查；关键结论有证据与原因；错误/未解决问题明确；只有IntegrationGate通过的结论可adopted；PoC usability未评估。

## find_vendor_advisories

- Purpose：通过 `VendorEnricher.investigate` 提供对应可追溯能力。
- Input：target_id + context；offset≥0，分页limit为1..100；原始外部内容按数据接收。
- Output：WorkOutcome / scoped Claims；没有证据或数据不以零/false代替未知，状态区分 SUCCESS/PARTIAL/NO_RESULT/FAILED/CONFLICT 或标准Verification状态。
- Dependencies：官方repo注册与CVE/GHSA。
- Evidence Produced：原始Source/Raw/Observation关联、locator/hash/stance/lineage；纯规则函数返回决策，由调用方持久化。
- Error Codes：TARGET_NOT_FOUND、PARSER_ERROR、SOURCE_HTTP_ERROR、SOURCE_TIMEOUT、RATE_LIMIT、REVISION_MISMATCH、EVIDENCE_INSUFFICIENT、OPEN_CONFLICT；只适用实际依赖，不把NO_RESULT当错误。
- Retryable：网络超时、429/403限流及部分5xx可重试；解析/标识/证据/修订错误需修正输入。只读查询可安全重试；写调用按claim/event/idempotency key防重复。
- Side Effects：可能追加原文、观察、候选、Claim/Evidence/Verification/Conflict/Review/Timeline/Job；网络读取无仓库代码执行；纯分类函数无副作用。
- Timeout：网络读30s，最多2次重试；GitHub搜索上限5/README3/Patch5；数据库statement30s。此为各请求/记录边界，不承诺整调查30秒完成；调度以小批次运行。
- Acceptance Criteria：目标/scope明确；输出结构可解析；检查来源/as_of可回查；关键结论有证据与原因；错误/未解决问题明确；只有IntegrationGate通过的结论可adopted；PoC usability未评估。

## find_poc_candidates

- Purpose：通过 `PocDiscoveryService.search / PocEnricher.investigate` 提供对应可追溯能力。
- Input：target_id / bounded scope；offset≥0，分页limit为1..100；原始外部内容按数据接收。
- Output：搜索Raw + Candidate + WorkOutcome；没有证据或数据不以零/false代替未知，状态区分 SUCCESS/PARTIAL/NO_RESULT/FAILED/CONFLICT 或标准Verification状态。
- Dependencies：GitHub Search；现有products。
- Evidence Produced：原始Source/Raw/Observation关联、locator/hash/stance/lineage；纯规则函数返回决策，由调用方持久化。
- Error Codes：TARGET_NOT_FOUND、PARSER_ERROR、SOURCE_HTTP_ERROR、SOURCE_TIMEOUT、RATE_LIMIT、REVISION_MISMATCH、EVIDENCE_INSUFFICIENT、OPEN_CONFLICT；只适用实际依赖，不把NO_RESULT当错误。
- Retryable：网络超时、429/403限流及部分5xx可重试；解析/标识/证据/修订错误需修正输入。只读查询可安全重试；写调用按claim/event/idempotency key防重复。
- Side Effects：可能追加原文、观察、候选、Claim/Evidence/Verification/Conflict/Review/Timeline/Job；网络读取无仓库代码执行；纯分类函数无副作用。
- Timeout：网络读30s，最多2次重试；GitHub搜索上限5/README3/Patch5；数据库statement30s。此为各请求/记录边界，不承诺整调查30秒完成；调度以小批次运行。
- Acceptance Criteria：目标/scope明确；输出结构可解析；检查来源/as_of可回查；关键结论有证据与原因；错误/未解决问题明确；只有IntegrationGate通过的结论可adopted；PoC usability未评估。

## verify_poc_candidate

- Purpose：通过 `PocVerificationService.verify` 提供对应可追溯能力。
- Input：target、packages、repository、静态README、affected_ranges、explicit引用；offset≥0，分页limit为1..100；原始外部内容按数据接收。
- Output：status/features/reason/abstention/usability；没有证据或数据不以零/false代替未知，状态区分 SUCCESS/PARTIAL/NO_RESULT/FAILED/CONFLICT 或标准Verification状态。
- Dependencies：发现与原始README；version与vendor引用。
- Evidence Produced：原始Source/Raw/Observation关联、locator/hash/stance/lineage；纯规则函数返回决策，由调用方持久化。
- Error Codes：TARGET_NOT_FOUND、PARSER_ERROR、SOURCE_HTTP_ERROR、SOURCE_TIMEOUT、RATE_LIMIT、REVISION_MISMATCH、EVIDENCE_INSUFFICIENT、OPEN_CONFLICT；只适用实际依赖，不把NO_RESULT当错误。
- Retryable：网络超时、429/403限流及部分5xx可重试；解析/标识/证据/修订错误需修正输入。只读查询可安全重试；写调用按claim/event/idempotency key防重复。
- Side Effects：可能追加原文、观察、候选、Claim/Evidence/Verification/Conflict/Review/Timeline/Job；网络读取无仓库代码执行；纯分类函数无副作用。
- Timeout：网络读30s，最多2次重试；GitHub搜索上限5/README3/Patch5；数据库statement30s。此为各请求/记录边界，不承诺整调查30秒完成；调度以小批次运行。
- Acceptance Criteria：目标/scope明确；输出结构可解析；检查来源/as_of可回查；关键结论有证据与原因；错误/未解决问题明确；只有IntegrationGate通过的结论可adopted；PoC usability未评估。

## find_patch_candidates

- Purpose：通过 `PatchEnricher.investigate / PatchDiscoveryService.classify` 提供对应可追溯能力。
- Input：target_id / official references；offset≥0，分页limit为1..100；原始外部内容按数据接收。
- Output：PatchCandidate / scoped Claim / WorkOutcome；没有证据或数据不以零/false代替未知，状态区分 SUCCESS/PARTIAL/NO_RESULT/FAILED/CONFLICT 或标准Verification状态。
- Dependencies：Vendor/Phase6 reference 与官方metadata。
- Evidence Produced：原始Source/Raw/Observation关联、locator/hash/stance/lineage；纯规则函数返回决策，由调用方持久化。
- Error Codes：TARGET_NOT_FOUND、PARSER_ERROR、SOURCE_HTTP_ERROR、SOURCE_TIMEOUT、RATE_LIMIT、REVISION_MISMATCH、EVIDENCE_INSUFFICIENT、OPEN_CONFLICT；只适用实际依赖，不把NO_RESULT当错误。
- Retryable：网络超时、429/403限流及部分5xx可重试；解析/标识/证据/修订错误需修正输入。只读查询可安全重试；写调用按claim/event/idempotency key防重复。
- Side Effects：可能追加原文、观察、候选、Claim/Evidence/Verification/Conflict/Review/Timeline/Job；网络读取无仓库代码执行；纯分类函数无副作用。
- Timeout：网络读30s，最多2次重试；GitHub搜索上限5/README3/Patch5；数据库statement30s。此为各请求/记录边界，不承诺整调查30秒完成；调度以小批次运行。
- Acceptance Criteria：目标/scope明确；输出结构可解析；检查来源/as_of可回查；关键结论有证据与原因；错误/未解决问题明确；只有IntegrationGate通过的结论可adopted；PoC usability未评估。

## get_epss

- Purpose：通过 `EpssEnricher.investigate / queries.page(epss)` 提供对应可追溯能力。
- Input：target_id / offset / limit；输出包含所有已获取日期；offset≥0，分页limit为1..100；原始外部内容按数据接收。
- Output：EpssSnapshot / missing NO_RESULT；没有证据或数据不以零/false代替未知，状态区分 SUCCESS/PARTIAL/NO_RESULT/FAILED/CONFLICT 或标准Verification状态。
- Dependencies：FIRST API；dated immutable raw。
- Evidence Produced：原始Source/Raw/Observation关联、locator/hash/stance/lineage；纯规则函数返回决策，由调用方持久化。
- Error Codes：TARGET_NOT_FOUND、PARSER_ERROR、SOURCE_HTTP_ERROR、SOURCE_TIMEOUT、RATE_LIMIT、REVISION_MISMATCH、EVIDENCE_INSUFFICIENT、OPEN_CONFLICT；只适用实际依赖，不把NO_RESULT当错误。
- Retryable：网络超时、429/403限流及部分5xx可重试；解析/标识/证据/修订错误需修正输入。只读查询可安全重试；写调用按claim/event/idempotency key防重复。
- Side Effects：可能追加原文、观察、候选、Claim/Evidence/Verification/Conflict/Review/Timeline/Job；网络读取无仓库代码执行；纯分类函数无副作用。
- Timeout：网络读30s，最多2次重试；GitHub搜索上限5/README3/Patch5；数据库statement30s。此为各请求/记录边界，不承诺整调查30秒完成；调度以小批次运行。
- Acceptance Criteria：目标/scope明确；输出结构可解析；检查来源/as_of可回查；关键结论有证据与原因；错误/未解决问题明确；只有IntegrationGate通过的结论可adopted；PoC usability未评估。

## get_known_exploitation

- Purpose：通过 `KevEnricher.investigate / queries.page(known_exploitation)` 提供对应可追溯能力。
- Input：target_id；offset≥0，分页limit为1..100；原始外部内容按数据接收。
- Output：KnownExploitation / KNOWN_EXPLOITED Claim；没有证据或数据不以零/false代替未知，状态区分 SUCCESS/PARTIAL/NO_RESULT/FAILED/CONFLICT 或标准Verification状态。
- Dependencies：完整Phase6 CISA catalog。
- Evidence Produced：原始Source/Raw/Observation关联、locator/hash/stance/lineage；纯规则函数返回决策，由调用方持久化。
- Error Codes：TARGET_NOT_FOUND、PARSER_ERROR、SOURCE_HTTP_ERROR、SOURCE_TIMEOUT、RATE_LIMIT、REVISION_MISMATCH、EVIDENCE_INSUFFICIENT、OPEN_CONFLICT；只适用实际依赖，不把NO_RESULT当错误。
- Retryable：网络超时、429/403限流及部分5xx可重试；解析/标识/证据/修订错误需修正输入。只读查询可安全重试；写调用按claim/event/idempotency key防重复。
- Side Effects：可能追加原文、观察、候选、Claim/Evidence/Verification/Conflict/Review/Timeline/Job；网络读取无仓库代码执行；纯分类函数无副作用。
- Timeout：网络读30s，最多2次重试；GitHub搜索上限5/README3/Patch5；数据库statement30s。此为各请求/记录边界，不承诺整调查30秒完成；调度以小批次运行。
- Acceptance Criteria：目标/scope明确；输出结构可解析；检查来源/as_of可回查；关键结论有证据与原因；错误/未解决问题明确；只有IntegrationGate通过的结论可adopted；PoC usability未评估。

## get_claims

- Purpose：通过 `queries.page(claims)` 提供对应可追溯能力。
- Input：target_id / offset / limit；offset≥0，分页limit为1..100；原始外部内容按数据接收。
- Output：items/total/verification/adopted；没有证据或数据不以零/false代替未知，状态区分 SUCCESS/PARTIAL/NO_RESULT/FAILED/CONFLICT 或标准Verification状态。
- Dependencies：PostgreSQL Claim。
- Evidence Produced：已有Evidence/Raw引用；不生成新证据。
- Error Codes：TARGET_NOT_FOUND、PARSER_ERROR、SOURCE_HTTP_ERROR、SOURCE_TIMEOUT、RATE_LIMIT、REVISION_MISMATCH、EVIDENCE_INSUFFICIENT、OPEN_CONFLICT；只适用实际依赖，不把NO_RESULT当错误。
- Retryable：网络超时、429/403限流及部分5xx可重试；解析/标识/证据/修订错误需修正输入。只读查询可安全重试；写调用按claim/event/idempotency key防重复。
- Side Effects：无。
- Timeout：网络读30s，最多2次重试；GitHub搜索上限5/README3/Patch5；数据库statement30s。此为各请求/记录边界，不承诺整调查30秒完成；调度以小批次运行。
- Acceptance Criteria：目标/scope明确；输出结构可解析；检查来源/as_of可回查；关键结论有证据与原因；错误/未解决问题明确；只有IntegrationGate通过的结论可adopted；PoC usability未评估。

## get_evidence

- Purpose：通过 `queries.page(evidence) / GET evidence/{id}` 提供对应可追溯能力。
- Input：target_id or evidence_id；offset≥0，分页limit为1..100；原始外部内容按数据接收。
- Output：source/raw/URL/excerpt/hash/stance/locator/time；没有证据或数据不以零/false代替未知，状态区分 SUCCESS/PARTIAL/NO_RESULT/FAILED/CONFLICT 或标准Verification状态。
- Dependencies：Evidence与原始观察。
- Evidence Produced：已有Evidence/Raw引用；不生成新证据。
- Error Codes：TARGET_NOT_FOUND、PARSER_ERROR、SOURCE_HTTP_ERROR、SOURCE_TIMEOUT、RATE_LIMIT、REVISION_MISMATCH、EVIDENCE_INSUFFICIENT、OPEN_CONFLICT；只适用实际依赖，不把NO_RESULT当错误。
- Retryable：网络超时、429/403限流及部分5xx可重试；解析/标识/证据/修订错误需修正输入。只读查询可安全重试；写调用按claim/event/idempotency key防重复。
- Side Effects：无。
- Timeout：网络读30s，最多2次重试；GitHub搜索上限5/README3/Patch5；数据库statement30s。此为各请求/记录边界，不承诺整调查30秒完成；调度以小批次运行。
- Acceptance Criteria：目标/scope明确；输出结构可解析；检查来源/as_of可回查；关键结论有证据与原因；错误/未解决问题明确；只有IntegrationGate通过的结论可adopted；PoC usability未评估。

## verify_claim

- Purpose：通过 `VerificationService.verify` 提供对应可追溯能力。
- Input：claim_id / now；offset≥0，分页limit为1..100；原始外部内容按数据接收。
- Output：VerificationResult / evidence IDs / reasons；没有证据或数据不以零/false代替未知，状态区分 SUCCESS/PARTIAL/NO_RESULT/FAILED/CONFLICT 或标准Verification状态。
- Dependencies：Claim+Evidence 当前修订。
- Evidence Produced：原始Source/Raw/Observation关联、locator/hash/stance/lineage；纯规则函数返回决策，由调用方持久化。
- Error Codes：TARGET_NOT_FOUND、PARSER_ERROR、SOURCE_HTTP_ERROR、SOURCE_TIMEOUT、RATE_LIMIT、REVISION_MISMATCH、EVIDENCE_INSUFFICIENT、OPEN_CONFLICT；只适用实际依赖，不把NO_RESULT当错误。
- Retryable：网络超时、429/403限流及部分5xx可重试；解析/标识/证据/修订错误需修正输入。只读查询可安全重试；写调用按claim/event/idempotency key防重复。
- Side Effects：可能追加原文、观察、候选、Claim/Evidence/Verification/Conflict/Review/Timeline/Job；网络读取无仓库代码执行；纯分类函数无副作用。
- Timeout：网络读30s，最多2次重试；GitHub搜索上限5/README3/Patch5；数据库statement30s。此为各请求/记录边界，不承诺整调查30秒完成；调度以小批次运行。
- Acceptance Criteria：目标/scope明确；输出结构可解析；检查来源/as_of可回查；关键结论有证据与原因；错误/未解决问题明确；只有IntegrationGate通过的结论可adopted；PoC usability未评估。

## detect_conflicts

- Purpose：通过 `ConflictDetectionService.detect` 提供对应可追溯能力。
- Input：target_id / now；offset≥0，分页limit为1..100；原始外部内容按数据接收。
- Output：ConflictRecord[] / ReviewTask；没有证据或数据不以零/false代替未知，状态区分 SUCCESS/PARTIAL/NO_RESULT/FAILED/CONFLICT 或标准Verification状态。
- Dependencies：同scope当前Claim/Evidence。
- Evidence Produced：原始Source/Raw/Observation关联、locator/hash/stance/lineage；纯规则函数返回决策，由调用方持久化。
- Error Codes：TARGET_NOT_FOUND、PARSER_ERROR、SOURCE_HTTP_ERROR、SOURCE_TIMEOUT、RATE_LIMIT、REVISION_MISMATCH、EVIDENCE_INSUFFICIENT、OPEN_CONFLICT；只适用实际依赖，不把NO_RESULT当错误。
- Retryable：网络超时、429/403限流及部分5xx可重试；解析/标识/证据/修订错误需修正输入。只读查询可安全重试；写调用按claim/event/idempotency key防重复。
- Side Effects：可能追加原文、观察、候选、Claim/Evidence/Verification/Conflict/Review/Timeline/Job；网络读取无仓库代码执行；纯分类函数无副作用。
- Timeout：网络读30s，最多2次重试；GitHub搜索上限5/README3/Patch5；数据库statement30s。此为各请求/记录边界，不承诺整调查30秒完成；调度以小批次运行。
- Acceptance Criteria：目标/scope明确；输出结构可解析；检查来源/as_of可回查；关键结论有证据与原因；错误/未解决问题明确；只有IntegrationGate通过的结论可adopted；PoC usability未评估。

## get_vulnerability_timeline

- Purpose：通过 `queries.page(timeline)` 提供对应可追溯能力。
- Input：target_id / offset / limit；offset≥0，分页limit为1..100；原始外部内容按数据接收。
- Output：IntelligenceEvent[]；没有证据或数据不以零/false代替未知，状态区分 SUCCESS/PARTIAL/NO_RESULT/FAILED/CONFLICT 或标准Verification状态。
- Dependencies：持久化事件。
- Evidence Produced：已有Evidence/Raw引用；不生成新证据。
- Error Codes：TARGET_NOT_FOUND、PARSER_ERROR、SOURCE_HTTP_ERROR、SOURCE_TIMEOUT、RATE_LIMIT、REVISION_MISMATCH、EVIDENCE_INSUFFICIENT、OPEN_CONFLICT；只适用实际依赖，不把NO_RESULT当错误。
- Retryable：网络超时、429/403限流及部分5xx可重试；解析/标识/证据/修订错误需修正输入。只读查询可安全重试；写调用按claim/event/idempotency key防重复。
- Side Effects：无。
- Timeout：网络读30s，最多2次重试；GitHub搜索上限5/README3/Patch5；数据库statement30s。此为各请求/记录边界，不承诺整调查30秒完成；调度以小批次运行。
- Acceptance Criteria：目标/scope明确；输出结构可解析；检查来源/as_of可回查；关键结论有证据与原因；错误/未解决问题明确；只有IntegrationGate通过的结论可adopted；PoC usability未评估。
