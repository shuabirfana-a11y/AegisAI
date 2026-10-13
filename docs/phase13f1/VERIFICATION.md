# Phase 13-F.1 验证记录

- 输入修复前：5个控制失败、1个通过，确认单对象asset版本遗漏、冲突未拒绝及overview请求语义错误。
- 无明确目标搜索的保留控制：先失败，再最小补回原行为；不改变3个已保存诊断题（均有明确目标），没有重新调用调查。
- 最终：AegisBench 115 passed；portable后端531 passed、1个真实Embedding检查明确deselected、1个既有Starlette/AnyIO deprecation warning。集合不相加，未重跑或借用历史1426项全量结果。
- OpenAPI/Pydantic：42个HTTP操作、5组Schema及40个合成对象一致，未连接数据库或改导出。
- 前端：23项既有测试通过、17文件语法通过、TypeScript契约检查通过；原生前端无build步骤。
- 实际诊断：新库持久化的本阶段Orchestrator调查数量正好3；12份来源哈希、519个受保护文件均未变。原金标、指标和实验归档没有回写。
- 独立自动审查无Critical/Important/Minor问题；人类语义审核未完成，不代签。

Gitleaks归档扫描55个generic-api-key候选，均逐项核对为51个随机幂等请求编号和4个领域scope_key哈希，不是身份凭据。原匹配值只在忽略的本机诊断目录核对；若历史扫描命中相同位置，仅追加准确提交/路径/规则/行号指纹，不排除目录或关闭规则。Token、数据库连接配置和私有模型原始输出不入Git/交付包。
