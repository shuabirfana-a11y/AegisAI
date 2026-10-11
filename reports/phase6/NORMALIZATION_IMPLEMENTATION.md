# 标准化实现

NormalizedIntelligenceRecord 是 Pydantic 中间契约，含 source/external_id/external_ids、raw UUID、retrieved/published/modified、状态、标题/描述/语言、product/package、原始范围与显式 fixed、CVSS/CWE/reference、exploitation、upstream_lineage、field_provenance 与 extensions。时间必须带时区；空缺用 null，保留来源原字段，不补估计值。

| 字段 | CVE_LIST | OSV | CISA_KEV |
|---|---|---|---|
| 主标识 | cveMetadata.cveId | id + 明确 aliases | 条目 cveID |
| 发布/更新 | datePublished/dateUpdated | published/modified | dateAdded；目录 dateReleased 在目录上下文 |
| 描述 | 优先英语 CNA 原文 | summary/details | vulnerabilityName/shortDescription |
| 产品/版本 | CNA affected，未知生态保留 | affected.package + 原生 events/versions | vendorProject/product；没有版本就不生成范围 |
| CVSS | CNA 和 ADP 内所有支持版本/提供者 | source severity vector | 缺失保持 null |
| 状态 | published/rejected/unknown | published/withdrawn | 条目存在与完整目录时间上下文 |

支持 CVE schema 5.x、OSV 1.x；未来主版本显式报错并保留 raw。CVE Program/其他 ADP 原容器完整保留在 extensions，不覆盖 CNA。CWE 仅接明确 CWE-ID；引用保存原 URL/locator，不下载和执行所指内容。

CVE 显式 baseScore 保留；OSV 仅给 vector 时由 cvss 库计算评分，score_method=computed_from_source_vector。CVSS 2/3.0/3.1/4.0 各自保存 version/provider/scope；不把计算分当作新增官方声明。来源 absence 不等于否定；KEV 条目移除写 not_listed_as_of + unknown，不能推出未被利用。

RawDocument 在解析前提交且不可改，published_at/modified_at 当时未知保持 null。原文解析得到的来源原生时间保存在不可变 normalized observation；API 另给 source_published_at/source_modified_at，与原始 retrieved_at 区分。重查不改第一份 raw 的取回时间，另有本次 fetch observation/SyncRun。

基础产品依人工维护注册表和显式 PyPI 包名，不用 LLM。未知生态按来源与供应商范围隔离；未知 vendor 与已知 vendor 不偷偷合并。归属历史与 FK 一致。PEP440/事件解析范围见 VERSION_PARSER.md；相关性 V0 见 AI_RELEVANCE_V0.md。
