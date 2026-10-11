# 后端联调与演示稳定性结果

日期：2026-10-11，北京时间。范围为 AegisAI 本地联调、启动故障修复和运行说明；没有修改业务代码、HTTP/DTO 契约、数据库模型、Planner/Agent/Runtime/Gate、前端页面或 Ground Truth。

## 仓库与发布

仓库为 private `shuabirfana-a11y/AegisAI`。PR #6 已在负责人确认后合并，main 为 `0f2e7221b5e5a4765b6839ed54215c2c5dde9f0d`，main 三项 CI 通过：[run 38144161139](https://github.com/shuabirfana-a11y/AegisAI/actions/runs/38144161139)。本轮修改在 `feature/backend-integration-stability`，另提交 PR，不自动合并。固定标签 v1.0-phase11D 没有移动。

## 修复

开发库未运行，10 月 8 日遗留 postmaster.pid 中的 PID 已不存在，pg_ctl status 返回 3。旧脚本只检查文件存在，跳过启动后报 psycopg ConnectionTimeout。本轮使用实际 pg_ctl 状态并增加有限等待，原生 PostgreSQL 启动既有 cluster，实际恢复约 5.02 秒。保留 PG_VERSION、端口 55436、原库和采集数据，未手动删除 PID 文件或重建数据库。

新增生命周期测试覆盖失效 PID、运行中不重复启动、状态探测异常不启动/连接、连接超时限制、停止已退出库、仅停止所属 cluster。6 条新测试在修复前失败、修复后通过。

启动提示改为“HTTP services are ready”，并明确默认 Mock 规划限制；几份当前团队手册同步 42 个 API、35 个代理可用操作，历史报告和版本标签保持。

## 实际 HTTP 联调

运行现有 main 后端与代理，连接既有开发库，迁移 0004。health 200、client-config 200，现有漏洞列表总数 278。没有为本轮演示更新情报或写人工答案；只产生必要的调查/审计记录。

| 检查 | 观察 |
|---|---|
| 创建新调查 | 202，真实 Orchestrator 受理；model_provider=mock / is_mock=true |
| 幂等重试 | 同键同内容复用同 ID；同键改内容 409 IDEMPOTENCY_CONFLICT |
| 代理与认证 | 缺 Origin 的 POST 被 403 拒绝；无 Bearer 直接读受保护 API 为 401 |
| status/trace/artifacts/history | 200，响应通过实际 Pydantic Schema 验证；历史包含根调查 |
| 默认 Mock 业务结果 | CREATED → FAILED，Trace error_code=PLANNING_FAILED；agent_runs=0，三份 Artifact 均为 null |
| Integration GET | 409；未执行 Gate，不能把它算成集成成功 |
| Answer GET | 200；读取已保存失败 AnswerEnvelope，不是安全结论 |
| 终态取消 | 200；原失败终态未被倒转 |
| 旧确定性 Assistant | 一次实际数据库查询 COMPLETED，旧 Gate 为 PASS_WITH_WARNINGS，Trace 5 次工具调用；不使用 LLM Planner |

新调查记录：`e5a7f586-6e6d-48cf-9920-3d3b2a4581a0`，本地已入库目标 `CVE-2026-54183`。这是接口探测记录，不是对该漏洞事实的独立权威确认。旧 Assistant 记录：`a5478754-d333-4fb4-8213-5c90513ffe63`。脱敏摘要留在本机 ignored `work/backend_integration/`，未上传凭据或原始响应。

默认 Mock 的 structured_fixtures 只有 VulnerabilityAnalysis，没有 PlannerPlan，返回 CAPABILITY_UNSUPPORTED；现有 Planner 正确结束为 PLANNING_FAILED。本轮没有绕过验证或给任意问题添加固定计划。

## 实际执行的验证

修改位于现有隔离工作树；实际 Python 复用了本机主目录的 `backend/.venv/Scripts/python.exe`。下表命令以该解释器为 `$Python`，工作目录分别列明；没有把旧历史 1261/1288 项说成本轮重跑。

| 工作目录与命令 | 实际结果 |
|---|---|
| 根目录：`$Python -m unittest discover -s tests/engineering -v` | 12 passed，0.283 秒；6 条新测试 + 6 条既有门禁测试；无真实数据库副作用 |
| 根目录：`$Python scripts/ci/run_backend_tests.py` | 423 passed，1 deselected，9.80 秒；明确排除真实缓存 embedding 测试 |
| backend：`$Python -m pytest tests/investigation_api/test_live_chain.py -q` | 2 passed，20.08 秒；专用 aegis_phase5_test/55435，显式合成 Planner 回执，实际执行完整链/取消 |
| 根目录：`$Python scripts/ci/check_contracts.py` | PASS；42 HTTP 操作、5 Schema 组、40 合成对象；不连接数据库 |
| 根目录：`$Python scripts/export_investigation_api.py --check` | PASS；10 份导出与实际实现一致；不连接数据库 |
| 根目录：`node scripts/ci/check_frontend.mjs` | 17 个 JS 文件语法通过；应用没有 build 脚本 |
| 根目录：`npm --prefix frontend test` | 23 passed，0 failed/0 skipped |
| 根目录：`node .github/node_modules/typescript/bin/tsc -p .github/tsconfig.contracts.json` | exit 0；契约类型检查 |
| PowerShell Parser 解析 scripts/start-local-demo.ps1 | 无语法错误；未将语法检查当作全新机器安装验收 |
| 根目录：`$Python scripts/ci/check_repository.py` | PASS；1703 个索引文件，无敏感路径；不读取密钥值 |
| 根目录：`gitleaks git --pre-commit --staged --redact=100` / `gitleaks git --log-opts='--all' --redact=100` | 未发现泄漏；扫描暂存内容约 27 KB、16 个历史提交约 34.57 MB，沿用精确历史误报排除规则 |

后端两组 pytest 各有 1 条既有 anyio BlockingPortal 弃用警告，无失败；本轮不升级依赖。合成专用库完整链证明 HTTP → Planner Validation → 三 Agent → Gate PASS → 冻结答案/引用检查；不代表真实模型质量或 Ground Truth。

独立只读审查未发现 P0/P1/P2 问题，另行复跑新增 6 条启动测试通过。检查了目录归属、Windows 原生状态码、超时与文档数据模式；未触及实际数据库。新 PR 的 GitHub 检查和合并状态以其最新 Checks 为准。

## 修改文件

- `backend/scripts/local_database.py`：运行状态探测、启动与连接时限。
- `tests/engineering/test_local_database.py`：6 条生命周期回归。
- `scripts/start-local-demo.ps1`：服务就绪与 Mock 限制提示。
- `backend/README.md`、`frontend/README.md`：当前运行入口与代理范围。
- `CURRENT_STATUS.md`、`docs/TEAM_COLLABORATION.md`、`docs/DEVELOPMENT_GUIDE.md`、`docs/GITHUB_WORKFLOW.md`、`docs/RELEASE_NOTES.md`：发布、API 和真实进度。
- `docs/PHASE12B_INVESTIGATION_API.md`：默认 Mock 失败语义。
- 本报告与 `docs/BACKEND_DEMO_STABILITY.md`：演示/联调步骤和实际验收。

## 保留的限制

本机应用当前运行已发布 main；新启动修复还需本轮 PR 合并才会进入 main，不能声称已发布。便携数据库启动器依赖开发者本机缓存，不是队友新机器通用安装方案。

默认 Mock 不能规划任意调查，真实模型仍未配置；产品化 Replay、公开比赛网址和前端新工作台尚未完成。当前单 worker、进程内队列和协作式取消的既有部署边界没有改变。

新版 49 题 SHA-256 保持 `f1f4be86e202ec263c6ebac66782b74d265840d706b559d913ab0c8c5f45e6f1`；人工 APPROVED=0，本轮没有修改 Evaluation Runner 或运行最终业务评测。

下一步：审查本轮启动修复；团队选定规划模型后进行真实新调查闭环验收，队友继续新工作台联调，标注人员完成独立人工复核。
