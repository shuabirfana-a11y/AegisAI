# Phase 14-C.1 实施范围

用户已授权修复三个前端联调问题，不进入冻结、合并或新功能。

- 后端基线：4f6722800fa60a0264356b0c4ce6ade69cd36073。
- UI 基线：PR #23 / e982b400e374318399f77d7a06bbcfe53fc3b80f；保留最新后端生成的前端契约，不用旧分支覆盖。
- 修复分支：codex/phase14c1-frontend-integration-fixes；队友分支和 PR 保持不变。

实施：先新增真实页面模块的 DOM 回归，复现 details、NEED_CONTEXT 和延迟响应竞态；再修页面防御式加载、创建联合响应及请求 generation/AbortController；运行全部前端测试、类型/Schema/工程检查；用现有官方公告快照和明确标为 Demo 的资产库存跑真实模型 HTTP 调查，并检查缺版本与调查切换。最后独立审查、交付结果及可审查分支。

边界：不修改 backend/app、数据库结构、模型、Agent、Planner、Verification、Risk、Gate、评测或人工答案。工程 Hash 保护保留原始基线，若需适配，仅记录已授权前端文件的精确前后 Hash；不关闭保护、不放行后端变化。DOM 测试使用锁定的 jsdom 开发依赖，不进入浏览器生产代码；CI 安装该测试依赖。
