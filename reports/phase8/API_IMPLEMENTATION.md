# 实际资产API

API仅loopback8000；全部资产接口需AEGIS_ASSET_TOKEN Bearer，owner由AEGIS_ASSET_OWNER服务端配置。未配置503，未认证401，越权/不存在404，非法422，超大SBOM413，幂等/旧revision409。没有body owner。演示服务启动时token仅内存，不写日志/报告；重启可由本地管理员安全配置。

GET/POST /api/v1/assets，GET /assets/overview，GET /assets/{id}，POST /assets/{id}/components，PATCH /assets/{id}/components/{component_id}，POST /assets/{id}/sbom（原JSON体+X-Request-Key），POST /assets/{id}/recompute，GET /assets/{id}/risks、/risks/{snapshot_id}、/risk-changes、/inventory-history、/reviews。列表offset>=0，limit1..100。

风险字段满足S01—S04：资产/组件/版本/范围/三态/PoC/KEV/Patch/fixed/证据/WhyNow/变化/unknown。S05问答仍BACKEND_GAP；8768原型仍Mock，本阶段未改前端。具体HTTP状态与耗时见api_validation.json。
