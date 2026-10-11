# Phase 13-A 工程维护报告

## Git 状态

沿用已有 Git 仓库，未重新初始化、未重写历史。基线提交为 d5bf67321fa9641d01260234c0f3c9691fed2ca3。实施在 Codex 管理的独立工作目录完成，工程改动位于 feature/backend；原本地 main 和业务运行文件未被替换。

## 分支状态

- main：已有稳定上传版本。
- feature/backend：本阶段工程文档、基础 CI 与契约类型兼容修正。
- feature/frontend：从稳定基线创建，供队友前端使用。
- 不覆盖远端已有队友修改、不 force push、不自动合并队友代码。

远端分支和最终提交状态将在推送/CI 后按实际回执补录。

## GitHub 状态

仓库：[shuabirfana-a11y/AegisAI](https://github.com/shuabirfana-a11y/AegisAI)，private，沿用当前认证连接。Actions 启用，workflow 默认 read，不能批准 PR。

## 当前 tag

v1.0-phase11D 的目标固定为初次上传提交 d5bf67321fa9641d01260234c0f3c9691fed2ca3，采用注释标签，远端发布结果待核对。标签表示 Phase 11-D 内部闭环和现有交接基线。

## 安全检查

Gitleaks v8.30.1 初扫约 28.91 MB 文本，84 候选项逐类复核，60 个准确历史指纹记录于 .gitleaksignore。复扫无未处理告警，未发现项目私密凭据；没有把整个目录设为扫描例外。依据见 docs/SECURITY_SCAN.md。

Git 索引路径门禁拒绝凭据、数据库、日志、node_modules、运行环境与临时 work。最终暂存内容及全历史扫描在推送前再次验收。

## CI 状态

已配置 PR、三条长期分支 push 与手动运行，三个 job：

1. Repository safety：敏感路径、6 个工程门禁测试、SHA256 校验的 Gitleaks 历史扫描。
2. Backend unit and contracts：Python 3.12，398 项无数据库测试，OpenAPI 和 5 组当前 Pydantic Schema 双副本比较；手工 ORM 列 Schema 仅检查合法性/镜像；40 个 Mock 请求/状态/Trace/答案验证。
3. Frontend tests and types：Node 24，17 个 JS 文件语法、21 项现有测试、TypeScript 7.0.2 契约编译和嵌套 JSON 的正负例。

本地执行均已通过。GitHub runner 运行结果待发布后核对，当前不能把“配置完成”写成“远端运行通过”。

单独排除真实缓存 embedding 测试 1 项，其他数据库/真实模型集成测试不在本 CI。没有重跑历史 1261 项，没有 Benchmark 成绩。当前应用无 build 脚本，明确 NOT_APPLICABLE；未伪造应用构建成功。

## 修改文件

新增贡献规范、GitHub/开发/发布/扫描文档、PR 模板、独立 CI 配置、四个工程检查脚本、工程门禁测试、本计划和报告；README 与团队指南新增入口/分支说明。

实际类型编译发现原 JsonValue 的 TS2456 循环引用。四份类型文档仅把递归 Record 改为等价索引签名，JSON Schema/wire 字段不变，交接 manifest/Validation 增补说明并同步 ZIP。冻结 v1.0-phase11D 保留原内容，原历史记录保留。

## 风险与限制

- 私有仓库 branch protection/rulesets 返回 403，当前套餐不能强制保护 main。本阶段未购买套餐、未改为公开；PR 审查规则依靠团队执行。
- CI 是基础单元/契约验收，不含数据库、真实模型、界面视觉和完整网站部署。
- Phase 12-B 仍待实施，Phase 11-D 新调查 HTTP 操作仍 API_NOT_EXPOSED。前端可继续按交接包和 Mock 开发。
- 冻结旧 API 的源码哈希门禁保留。未来需改动冻结文件时必须按相关阶段显式审查和更新证据，不能随意移除检查。

## 下一阶段建议

按单独指令推进 Phase 12-B 的公共调查 API/前后端联调；Phase 13-B 再建立 AegisBench、真实数据/模型对照与 Replay。当前没有开始这两阶段。
