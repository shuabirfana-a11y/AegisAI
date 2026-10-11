# Tool Contracts V2 — Phase8 Asset Risk

继承V1的12个公开情报服务，不创建Agent/Dify/MCP服务器。下列10个资产工具均为实际Python服务。SQLAlchemy Session由调用方提供，写入在事务中完成；HTTP接口会提交事务。所有资产读取/写入需owner scope，actor由受控认证层提供，不能信任LLM/body传入的用户身份。库存内容为UNTRUSTED_EXTERNAL_CONTENT，不发送外部模型/数据源。

统一错误：AUTH_REQUIRED（401，不重试）、ACCESS_NOT_CONFIGURED（503，不自动重试）、NOT_FOUND（404）、INVALID_INPUT/SBOM_PARSE_ERROR/PACKAGE_ID_MISMATCH（422）、REVISION_CONFLICT/IDEMPOTENCY_CONFLICT（409，读新revision再人工决策）、TRANSIENT_DATABASE（可有限重试同request_key）。版本/身份UNKNOWN是有效业务结果，不是抛弃样本的错误。

## create_asset

Purpose：登记授权资产；路径app.assets.inventory.AssetService.create(session,value,actor,request_key)。
Input Schema：AssetInput{name:string1..200,asset_type:service/training/application/project/server/container,environment:production/staging/development/unknown,exposure:internet/internal/development/unknown,description:string|null,is_demo:boolean}，request_key1..150，server actor。
Output Schema：Asset{id,name,owner_principal,is_demo,environment,exposure,created_at}。
Dependencies：PostgreSQL、0003、server authentication。
Evidence References：库存是用户声明；不伪装厂商Evidence。
Error Codes：AUTH_REQUIRED/INVALID_INPUT/IDEMPOTENCY_CONFLICT。
Retryable：只有短暂数据库故障；必须原request_key和原body。
Side Effects：新增Asset；同key同body复用，异body409。
Acceptance Criteria：成功可GET；无owner body；不能查询他人资产。

## add_asset_component

Purpose：手工登记组件；AssetService.add_component(session,asset_id,value,actor,request_key)。
Input Schema：ComponentInput{name,package_name?,package_identifier_id?:UUID,ecosystem?,namespace?,purl?,version?,source_ref?}；版本<=200字，PURL<=2000字。
Output Schema：AssetComponent{id,asset_id,product_id?,package_identifier_id?,version?,normalized_version?,identity_status,source,inventory_revision,first_seen_at,last_seen_at}。
Dependencies：resolve_component、normalize_version、RiskService、owner Asset。
Evidence References：库存历史+公开匹配的range/Claim/Evidence链。
Error Codes：NOT_FOUND/PACKAGE_ID_MISMATCH/INVALID_INPUT/IDEMPOTENCY_CONFLICT。
Retryable：原body原key数据库瞬态。
Side Effects：组件、InventoryEvent、版本匹配、风险快照/变化，重要资产不确定可能Review。
Acceptance Criteria：未知可登记；PURL矛盾不得猜身份；重复key无重复组件。

## import_sbom

Purpose：同资产权威SBOM库存更新；AssetService.import_sbom(session,asset_id,payload:bytes,actor,request_key)。
Input Schema：原始JSON字节<=2MiB；CycloneDX1.6或SPDX2.3；<=1000组件；深度<=40，节点<=100000。HTTP X-Request-Key。
Output Schema：{format,sha256,added,updated,removed,added_ids,updated_ids,removed_ids,component_count,content_trust_level}。
Dependencies：本地官方JSON Schema/jsonschema、身份/版本/匹配/事务；不下载用户$schema/路径/PURL。
Evidence References：InventoryEvent保存SHA、完整文档及source_ref/locator；公开情报Evidence另存。
Error Codes：SBOM_PARSE_ERROR/PACKAGE_ID_MISMATCH/INVALID_INPUT/IDEMPOTENCY_CONFLICT；体积HTTP413。
Retryable：网络中断可同key原字节重试；输入错误不可自动重试。
Side Effects：新增/更新/软移除SBOM组件，保留manual组件；追加导入历史、风险变化；任一身份错误整批回滚。
Acceptance Criteria：官方schema验证；重复导入不制造库存修订；升级/移除保留历史；可明确空SBOM移除SBOM清单。

## resolve_component

Purpose：确定分发身份；app.assets.identity.resolve_component(session,value)。
Input Schema：ComponentInput。
Output Schema：{status:RESOLVED/AMBIGUOUS/UNRESOLVED,method,product_id?,package_identifier_id?,matched_product?,matched_identifier?,ecosystem,package_name,namespace,purl?,version?,reason_summary,candidates?}。
Dependencies：既有Product/PackageIdentifier/confirmed ProductAlias和显式AI注册表。
Evidence References：匹配包ID/PURL与规范产品；身份规则版本见COMPONENT_RESOLUTION报告。
Error Codes：PACKAGE_ID_MISMATCH/INVALID_INPUT。
Retryable：否（数据库瞬态除外）。
Side Effects：无写入/网络/模糊合并。
Acceptance Criteria：PURL精确→包ID→生态包名→明确别名；多候选歧义，不跨生态。

## normalize_version

Purpose：生态版本标准化；app.assets.versions.normalize_version(version,ecosystem)。
Input Schema：{version:string|null,ecosystem:string}。
Output Schema：{raw,ecosystem,status:NORMALIZED/UNKNOWN,normalized?,public_version?,reason,local_build?}。
Dependencies：packaging PEP440；仅PyPI支持确定比较，npm/Git等UNKNOWN。
Evidence References：原版本永久保留；无LLM生成值。
Error Codes：无（UNKNOWN是业务结果）。
Retryable：否。
Side Effects：无。
Acceptance Criteria：v前缀、dev/pre/post/local按PEP440；不把4.x/custom当精确版本。

## match_component_vulnerabilities

Purpose：精确版本影响；AssetVulnerabilityMatcher.match(session,component)。
Input Schema：已授权AssetComponent实体，匹配之前调用方必须确认owner。
Output Schema：list{component_id,vulnerability_id,canonical_id,installed_version,match_status:AFFECTED/NOT_AFFECTED/UNCERTAIN/NOT_EVALUATED,version_result,verification_status,claim_ids,claim_revisions,affected_ranges,comparisons,evidence_refs,conflict_ids,fingerprint,reason_summary}。
Dependencies：现有范围/Phase7 Claim/Evidence/Conflict和PEP440 interval engine。
Evidence References：Component→Package→Range→Claim→Evidence→Source/Raw/locator。
Error Codes：TRANSIENT_DATABASE；不支持版本返回UNCERTAIN。
Retryable：瞬态数据库可重试。
Side Effects：缺失Phase6范围Claim时追加pending源陈述/Evidence；可将既有Vendor Claim的原范围持久化为新Range，绝不假确认。
Acceptance Criteria：精确包、不仅产品名；所有当前范围合并；确认/采用/新鲜证据无冲突才输出确定结论。

## get_asset_risks

Purpose：优先处置当前投影；app.assets.queries.get_asset_risks(session,asset_id,actor,offset=0,limit=20)。
Input Schema：{asset_id:UUID,server actor,offset>=0,limit1..100}。
Output Schema：{items:[RiskPayload],total,offset,limit,coverage}。RiskPayload含完整资产/组件/漏洞/版本/范围/核验/KEV/EPSS/PoC/修复/优先级/factors/WhyNow/Evidence/快照时间/陈旧状态。
Dependencies：RiskSnapshot/Match，owner scope。
Evidence References：公开Evidence引用+本地库存revision。
Error Codes：NOT_FOUND/AUTH_REQUIRED。
Retryable：只读瞬态可重试。
Side Effects：无；不在GET偷偷重算。
Acceptance Criteria：不显示过期确定安全结论；NOT_AFFECTED仅该漏洞scope；真实SQL统计，不隐藏unknown。

## explain_asset_risk

Purpose：解释固定历史快照；app.assets.queries.explain_asset_risk(session,asset_id,snapshot_id,actor)。
Input Schema：{asset_id:UUID,snapshot_id:UUID,server actor}。
Output Schema：冻结RiskPayload+evaluated_at+historical=true。
Dependencies：AssetRiskSnapshot与owner鉴权。
Evidence References：固定版本/revision/Claim/Evidence，不把历史当现在。
Error Codes：NOT_FOUND/AUTH_REQUIRED。
Retryable：只读瞬态可重试。
Side Effects：无。
Acceptance Criteria：与当时快照一致；不能通过另一资产ID读取快照。

## get_remediation

Purpose：展示确有证据的处置选项；app.assets.remediation.get_remediation(session,vulnerability_id,package_id)。
Input Schema：{vulnerability_id:UUID,package_id:UUID}，调用方先校验范围。
Output Schema：{statuses:[PATCH_AVAILABLE/FIXED_VERSION_AVAILABLE/VENDOR_GUIDANCE_AVAILABLE/NO_PUBLIC_FIX_FOUND/UNKNOWN],fixed_versions,patches,related_patches,vendor_guidance,recommended_action,search_scope,absence_is_not_no_patch:true}。
Dependencies：当前confirmed/adopted/fresh Claim、当前revision的VerificationResult及对应Evidence、PatchCandidate、最近任务范围；新反驳/未审新证据/open conflict阻断确定处置。
Evidence References：每个fixed/Patch给Claim与EvidenceID/branch。
Error Codes：INVALID_INPUT/NOT_FOUND。
Retryable：只读瞬态可重试。
Side Effects：无网络、无自动升级。
Acceptance Criteria：fixed不从上界猜；candidate不说confirmed；产品相关Patch只作为related_patches/applicability UNKNOWN；只有精确包且无未核验分支限制才进入PATCH_AVAILABLE；无结果不说“No Patch Exists”。

## get_asset_risk_changes

Purpose：回看风险为何变化；app.assets.queries.get_asset_risk_changes(session,asset_id,actor,offset=0,limit=20)，HTTP GET /api/v1/assets/{id}/risk-changes。
Input Schema：{asset_id:UUID,server actor,offset>=0,limit1..100}。
Output Schema：{items:[{event_type,previous_snapshot_id,snapshot_id,before_state,after_state,occurred_at}],total,offset,limit}。
Dependencies：不可变风险变化和owner Asset。
Evidence References：前后Snapshot与各自版本/Claim/Evidence。
Error Codes：NOT_FOUND/AUTH_REQUIRED。
Retryable：只读瞬态可重试。
Side Effects：无。
Acceptance Criteria：PoC/KEV/EPSS/Patch/版本/核验/库存移除变化有结构化历史；重复重算不重复事件；A→B→A保存三次观察。

运行：scripts/assets.py dispatch按range和package-scoped Claim建立受影响asset/event对；无Phase7事件的Phase6源更新用依赖指纹差量补排程，元数据检查只读、不在dispatch中全量重算。已排队资产不重复排source任务，稳定指纹幂等。due使用FOR UPDATE SKIP LOCKED运行，失败30s后可重试，最多3次。管理员CLIrecompute局部资产。GET比较库存、当前源/证据/范围依赖与新鲜度，不把历史确定结论当现状。没有常驻daemon/Kafka，多进程租约/服务部署在后续工程阶段验证。
