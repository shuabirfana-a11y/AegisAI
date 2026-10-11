# AegisAI 团队开发规范

本规范用于已有私有仓库。当前业务基线是 Phase 11-D，前端协议基线是 Phase 12-A.5；新调查 HTTP 接口仍待 Phase 12-B 实施。

## 分支

| 分支 | 用途 | 合并要求 |
|---|---|---|
| main | 已审查的稳定成果、可复现交接 | PR、检查通过、负责人确认 |
| feature/backend | 后端 API、评测和优化协作 | 后端负责人维护 |
| feature/frontend | 队友前端协作 | 前端负责人维护 |
| backend/姓名-任务、frontend/姓名-任务、chore/任务 | 个人短期任务 | PR 到对应协作分支 |

长期协作分支不是稳定发布。两条线进入 main 前，分别提交 PR，确认契约和对方兼容性。直接共用协作分支时只指定一位提交负责人；多人使用个人分支。禁止 force push、删除已发布标签、覆盖队友工作或自动合并队友 PR。

开始工作前，确认自己的工作区干净并同步目标分支。未提交工作先提交到自己的分支或自行保存，不使用强制重置。只用普通 fast-forward 同步稳定分支。

## Commit

格式：类型(范围): 简要说明。类型包括 feat、fix、test、docs、chore、ci；一次提交只处理一个目的。

~~~text
feat(api): expose investigation status DTO
fix(frontend): preserve conflict state
docs(handoff): clarify cancellation semantics
ci: add portable unit and contract checks
~~~

说明用户可见行为和原因；不提交生成日志、数据库、安装依赖目录或个人凭据。凭据配置到各自环境。保持现有文件字节和冻结基线，不批量转换换行符。

## PR 与审查

1. 写明问题、变更范围、接口/Schema 影响和明确未实现项。
2. 提供实际测试命令、结果；界面改动附脱敏截图。
3. CI 的三个检查全部通过。失败不得改成跳过或伪造通过。
4. 由另一位队员或负责人审查边界、权限、证据引用、状态和兼容性；作者逐项回应。
5. 负责人确认后显式合并。未审查的同学代码不能自动合并。

当前私有仓库套餐不支持强制 branch protection/rulesets（服务返回 403）。这些要求目前依靠团队执行，**没有服务器强制门禁**；不得写成已经保护。CI 结果会显示在 PR 中。

## 验证要求

- 所有 PR：敏感路径检查、Gitleaks、工程检查、现有前端测试及契约类型检查。
- 后端：portable unit baseline 和当前 Pydantic/OpenAPI 契约比较。
- API/数据库/Runtime 行为改动：除基础 CI 外，还须在专用测试库完成相应集成验收，明确测试库和实际结果。不能把开发或比赛演示数据库用于测试。
- Schema 变更同步 OpenAPI、JSON Schema、TypeScript、接口清单和文档；旧响应缺 response_model 的限制必须保留。
- Mock、合成测试、真实模型运行和业务 Benchmark 分开标识。工程测试数量不是准确率。

具体命令见 [开发指南](docs/DEVELOPMENT_GUIDE.md)，分支流程见 [GitHub 流程](docs/GITHUB_WORKFLOW.md)，历史扫描复核见 [安全扫描说明](docs/SECURITY_SCAN.md)。
