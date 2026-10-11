# Phase 13-A 实施计划

目标：在现有私有仓库建立三分支协作、不可移动的 Phase 11-D 标签、可运行的基础 CI 与团队规范。依据用户提供的 Phase 13-A 指令，本次直接执行工程维护，不修改业务代码。

## 范围与文件

- 保留 main；创建 feature/backend、feature/frontend；v1.0-phase11D 指向 d5bf67321fa9641d01260234c0f3c9691fed2ca3。
- 新增 CONTRIBUTING.md、docs/GITHUB_WORKFLOW.md、docs/DEVELOPMENT_GUIDE.md、docs/RELEASE_NOTES.md、docs/SECURITY_SCAN.md、PHASE_13A_RESULT.md。
- 新增 .github/workflows/ci.yml、PR 模板、独立的 CI Python/TypeScript 配置、scripts/ci/ 检查脚本和 tests/engineering/。
- README 与已有团队指南只补充工程文档链接和分支说明；全部历史业务文件保留原字节。
- 实际 TypeScript 检查发现旧 JsonValue 声明 TS2456；仅将四份类型文档中的递归 Record 改为等价索引签名，同步交接校验元数据与 ZIP。JSON Schema、wire 字段和业务代码不改变。

## 实施步骤

1. [x] 确认已有仓库、分支、远端与干净状态；不初始化或覆盖远端。
2. [x] 在 Codex 管理的独立工作目录创建 feature/backend，并建立 feature/frontend。
3. [x] 核对实际测试依赖；398 项无数据库后端测试与 21 项前端测试作为本次 CI 基础。单独排除需要本机缓存模型的真实 embedding 测试；没有重跑历史 1261 项。
4. [x] Gitleaks 扫描全部 Git 历史；复核候选，仅记录准确历史指纹。新增未知告警阻止推送。
5. [x] 先验证工程检查能拒绝敏感路径和 Schema 漂移，再实现检查脚本。
6. [x] 配置三条长期分支目标 PR、main push 与手动基础 CI：仓库安全检查、Python 单元测试与契约一致性、JavaScript 检查/测试与独立契约 TypeScript 检查。
7. [x] 实际运行本地检查、扫描和文件差异核对；完成文档。
8. [x] 推送分支和注释标签，创建本阶段自己的 PR，实际检查 GitHub CI。当前 main 不包含队友的未审查修改；不自动合并队友代码。
9. [x] 核对已发布的远端标签、分支与 run 38113508882 的执行结果，输出验收报告。

发布收尾遵循以下顺序：核对 PR 最新 head 的三项 CI → 显式合入本阶段自己的已审查工程 PR → 安全同步共享分支 → 核对 main 最新 CI 与远端引用。完成后停止。

## 已确认的适配与风险

- 当前前端没有 TypeScript 应用、npm 依赖或 build 脚本：不重写前端。只在 .github/ 安装契约检查用 TypeScript；构建应用暂为 NOT_APPLICABLE。
- 当前套餐对私有仓库的 branch protection/rulesets 返回 403：不付费升级、不改公开；采用文档化 PR 审查，明确尚无服务器强制保护。
- 本阶段不连接或修改数据库，不调用真实模型，不部署网站。CI 不使用真实 API Key，不下载模型。
- 每次 PR 仍须人工确认业务/API 变化及数据真实性。基础 CI 不等于数据库集成验收、Benchmark 或准确率。

## 验收重点

历史业务文件未变；交接包只有等价类型声明/校验元数据更新；敏感路径不能纳入 Git；现有 Pydantic/OpenAPI 与交接 Schema 一致；CI 失败须明确报告；分支已有队友提交时禁止强制更新或覆盖。
