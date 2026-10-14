# 监测与富化接口对接（Phase 14-A）

五个新增接口已存在，均为只读，不新增 UI。原八个 `/api/investigations` 调查接口及其权限保持。当前完整 OpenAPI 为 46 条路径、47 个操作；以生成文件为准。

| 接口 | 作用 | 权限 |
| --- | --- | --- |
| GET /api/v1/intelligence | 漏洞、论文、博客统一分页列表 | 公共来源信息 |
| GET /api/v1/intelligence/sources | 同步状态、失败、范围及来源类别 | 公共来源信息 |
| GET /api/v1/intelligence/vulnerabilities/{id} | UUID/CVE 对应的富化详情 | 公共来源信息 |
| GET /api/v1/intelligence/documents/{id} | 文献元数据与历史版本标识 | 公共来源信息 |
| GET /api/v1/intelligence/vulnerabilities/{id}/assets | 该漏洞关联的已计算库存风险 | Bearer，仅当前成员库存 |

列表支持 `type`、`q`、`offset>=0`、`limit=1..100`；q 最多150字符，通配字符按文本搜索处理。资产子接口同样分页，未计算的库存不会被假定安全。当前演示库没有企业库存，返回空资产列表是实际状态。

## 契约与调用

实际 Pydantic DTO：`backend/app/monitoring/schemas.py`。生成声明与 OpenAPI 在 `docs/frontend-contracts/intelligence-http.*`；客户端在 `frontend/contracts/intelligence.ts`，队友包有同步副本。生成器 `scripts/export_intelligence_api.py --check` 可检查漂移。

```typescript
import { IntelligenceApiClient } from './contracts/intelligence.js';
const client = new IntelligenceApiClient(apiOrigin, () => sessionToken);
const page = await client.list({ type: 'vulnerability', limit: 20 });
const detail = await client.vulnerability('CVE-2025-32434');
```

`apiOrigin` 与短期会话凭据由运行配置提供，模型密钥不进入浏览器。这里使用已有单成员 Bearer 协议，不宣称已经提供生产多租户身份系统。

## 展示语义

- `source` 为来源键数组，不是单字符串。不同来源、CVSS版本及历史版本并列保留；`is_current` 为前端判断当前性的依据。
- `SOURCE_ASSERTED` 表示来源声明，不等于全局核验通过。研究关联 `CANDIDATE` 表示线索，不能当作影响版本证据。
- `fixed_versions` 来自明确修复版本字段，含 package、source、observation、raw_document_id、locator；`< x` 不能被显示为“x 已发布修复”。
- `poc_status` 区分三类。`VERIFIED_EXPLOIT` 要求当前、未冲突的人工核验且可用性已验证；本阶段不执行利用代码。
- `NO_EVIDENCE` 仅指本地没有合格候选，应同时显示 `poc_search_status`。NOT_RUN、PARTIAL、FAILED均不能解释为“没有公开PoC”。
- 论文/博客有 `edition`、`modified_time`、`canonical_publication_id`、`is_current`。活跃列表与现有语义检索排除已归档版本；旧ID可读 `SUPERSEDED`，原正文、Raw、Chunk和Evidence保留。
- 来源页 `source_category_count` 是声明类别数，`collected_source_category_count` 是有解析记录的类别数；均不是评分承诺或全球完整覆盖率。
- 公共详情过滤资产关联证据，库存风险需要调用受保护子接口。

## 失败与刷新

401 缺少授权；404目标不存在；422参数或UUID非法。新增接口使用标准 FastAPI `detail` 错误体，不假定与调查接口 `ApiError` 完全同形。客户端保留未知错误体，页面显示受控错误信息。

建议列表/来源页30–60秒按需刷新，不让浏览器触发采集。调查进度继续使用原状态接口轮询；答案读取原 AnswerEnvelope，不在前端重生成事实。

`live-intelligence-example.json` 来自本次真实库投影，仅删去证据原文摘录，明确标记 REDACTED_LIVE_API_PROJECTION。自动测试 transport/embedding 是合成夹具，不能替代这些实时记录或正式准确率。
