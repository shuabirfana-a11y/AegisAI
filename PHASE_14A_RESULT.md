# Phase 14-A：AI安全情报监测与富化补强结果

实施范围已完成：新增原生NVD/GHSA/固定厂商公告接入、RSS/Atom知识同步、统一情报投影、原富化/证据桥接和既有问答链路。原Agent架构、Planner、Runtime、Gate、LLM、数据库结构和Benchmark保持。

## 1. 数据源与Collector

配置11个监测来源，覆盖6类；原CVE/OSV/KEV复用，新来源详见 [来源矩阵](docs/phase14a/SOURCE_MATRIX.md)。本次真实新演示库实际入库三类：漏洞数据库、安全博客、学术论文。记录2个漏洞、2篇博客、1篇论文及31个实际Embedding。

NVD/OSV有界批次PARTIAL不等于全部失败；GHSA/厂商公告监测请求、本次Google博客请求失败。arXiv更新排序请求遇到429，窄范围相关性请求成功；没有声明最新论文全覆盖。失败及Raw哈希均保留。

## 2. 统一情报模型与富化

复用原NormalizedIntelligenceRecord和数据库；新增SecurityIntelligenceObject为HTTP投影。展示CVSS/CWE、影响/修复版本、PoC/Patch候选、研究关联、来源证据及授权库存风险。

复用原富化服务并桥接原生事实后，库中合计15个Claim、15条Evidence、6个PoC候选及2个Patch候选（其中4条CVSS声明来自事实桥）。原富化作业结果含4 SUCCESS、8 NO_RESULT、4 FAILED、2 PARTIAL，未把失败改成成功。PoC未执行，不能显示为已验证利用；Patch候选不能解释为已证实修复。

文献关联保持候选语义。本次真实关联0条，精确ID/包名关联及XML出处用合成集成测试验证。没有企业库存输入，真实资产子接口为空；未虚构扫描数据或安全风险结论。

## 3. Agent与问答复用

原生CVSS事实先校验Raw中的JSON pointer，再经原ClaimStore/EvidenceService生成未采纳声明；桥本身不验证、不采纳、不调用模型。这样原调查工具可读取明确parsed观察，而不误把最新fetch观察当作核验事实。

真实TCP调查 `0588d3f6-6169-4ef1-9c72-66b6c608151d` 使用原本地Qwen、原v6 Planner与原八API：规划VALIDATED，3个Agent、3个Artifact、5次工具调用，Gate为PASS_WITH_WARNINGS，答案COMPLETE_WITH_WARNINGS。答案保留未知、候选及未核验警告，最终确认引用数0，不能宣称已证实企业风险。

论文问答 `4bd4b542-93bd-41ae-ae6a-65dd755cc645` 经原semantic_search完成，使用已缓存实际MiniLM模型。该旧问答入口为确定性流程，另一路专业调查Planner才调用真实Qwen，两者没有冒充同一种模型模式。

详细Run/Artifact/Gate/Answer IDs及原始来源摘要在 [真实验证记录](docs/phase14a/live-validation.json)。先前阻断调查也保留在本机，不删失败案例。

## 4. 前端接入

新增五个只读 `/api/v1/intelligence` 接口，实际HTTP均200；调查八接口保持。OpenAPI、TypeScript声明、客户端和队友包同步，共46路径/47操作。[接入说明](docs/phase14a/FRONTEND_ADAPTER_NOTES.md)列出状态、权限、分页和错误体。

公共详情过滤资产范围证据，资产子接口仅返回当前成员库存。历史文献可显式读取SUPERSEDED，当前列表/检索过滤归档版。

## 5. 修改文件与工程验证

新增文件及四个原代码适配点详见提交diff和 [源哈希例外](docs/phase14a/source_hash_exceptions.json)。共享旧来源目录恢复原字节，来源扩展放独立native目录；受保护652个文件0变更。

本阶段48项新增验证与相关旧测试合计70通过；前端23通过、工程18通过、类型及导出一致性通过。完整后端实跑1546通过/3失败；其中本阶段来源配置回归已用相关测试修复，另两项在基线同样失败。没有把全套报成全绿。便携CI最终数量见verification-summary.json。

[测试详情](docs/phase14a/TEST_RESULTS.md)和 [独立审查](docs/phase14a/REVIEW.md)保留命令、失败、跳过、修复依据及一项非阻塞归档副本优化。

## 6. 当前限制与停止

采集/检索均有界；不能宣称全球覆盖、长期无人值守、最新论文完备、实时情报准确率或比赛评分。精确搜索仍受已有1000向量容量限制。网络、厂商证据、文献关联、资产输入不足都显式保留，不改Gate标准。

没有运行正式Benchmark、修改金标、扩展新Agent或公网部署。实现、契约、真实来源记录与运行指南打包交付后停止；后续由团队决定前端展示与补充可用来源/实际资产。
