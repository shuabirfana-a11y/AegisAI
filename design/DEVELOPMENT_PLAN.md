# 开发顺序与阶段验收

最新主路线见 [PROJECT_ROADMAP.md](../PROJECT_ROADMAP.md)：已完成源调研与真实数据准备，下一主步骤先做产品功能规划、UX、UI，再复核数据模型和后端。以下四项是之后进入第8—9步的编码顺序，当前不直接跳入业务工程。

1. 基础与输入契约：下一编码阶段建立最小项目、隔离依赖lock、12fixture回归、Pydantic模型、package/版本服务与规则测试。先只offline跑通。
2. 持久化：PostgreSQL17/Alembic、14表与索引、raw写入/哈希、claim/evidence关系、单记录事务/幂等、回补和source状态。真实DB测重复/并发/错误，再加采集runner。
3. 首批闭环：CVE List/OSV先跑通，再加KEV snapshot和CVE内CISA ADP解析；固定scope和批次预算、规范化/AI规则/来源化claims、run-once和OS定时。由本批真实种子及目录契约验收每项可回查。
4. 只读API与容器：detail/list/evidence/timeline、令牌/错误/health、Compose与备份恢复；fixture模式不依赖互联网，opt-in真实API测试。

每阶段只在有实际验证证据时称完成。当前通过的是设计schema与公开响应，不是阶段2—4的运行服务。下一阶段不能拿work/design_probe.py直接当生产Normalizer：它是临时映射试验，来源raw/locator/事务/并发/错误边界须正式实现和测试。

后续富化：NVD/GHSA独立增量/EPSS、更多生态。V0.2：Dify只读工具/检索、人工写审核/冲突、PoC/Patch候选审核、资产/SBOM、队列/订阅和对象存储。决赛：有来源攻击防御映射、模型供应链、Replay/RiskChange、企业权限/恢复与AegisBench；完整比赛范围包含这些后续步骤。
