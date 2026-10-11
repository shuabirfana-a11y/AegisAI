# Phase 10-A 完成报告

日期：2026-10-08。依据用户确认的 `PHASE10A_IMPLEMENTATION_PLAN.md` 实施。功能、独立只读审查要求的修正和最终完整回归已完成；本阶段停止开发。

## 实现内容

已实现统一 TaskContract、TaskArtifact、TaskTrace、ToolContract、不可变 DAG 快照、READY Scheduler、固定 Worker Executor 和任务进程树监管。

只有 SUCCESS 解锁依赖，失败/缺项分支停止下游，独立分支仍完成。并行最多 3 个任务，任务数、图深度、工具预算、执行期限和数据大小均有限制。

工具复用已有 Gateway；版本匹配、资产风险、检索、证据核验逻辑保持原样。规则模板不调用生成模型，保留 Model Gateway 注入位置。证据按真实工具收据保存，候选/未核验标记不提升，confidence 默认 null。

运行持久化复用 AgentRun、ToolCallRecord；actor/幂等键/运行类型隔离，行锁合并并行结果。真实测试已证明原 Assistant GET 接口可以读取新运行。

## 架构变化

新增独立 `backend/app/runtime/`：

```text
QueryRequest / TaskPlan
→ 原 Router 与规则模板
→ 协议、权限、预算和 DAG 校验
→ Scheduler → ProcessSupervisor → Worker / Executor
→ 原 Tool Gateway → 原业务 / Hybrid Retrieval
→ 收据与 Artifact → 原数据库表 → Trace 兼容投影
```

现有前端提问和 POST 接口仍走原 Agent。本阶段新运行通过显式 RuntimeService 启动，再用 Run ID 在原页面读取；没有悄悄替换旧运行链路。

## 新增文件

- `backend/app/runtime/`：13 个生产模块，职责清单见实现文档。
- `backend/tests/runtime/`：7 个测试模块及 fixture/helper，共 80 个 Runtime 测试。
- `docs/AGENT_RUNTIME_IMPLEMENTATION.md`：接口、权限、预算、状态、存储、真实测试和限制。
- `PHASE_10A_RESULT.md`：本报告。
- `work/runtime/`：199 文件哈希基线、执行账本、测试运行器、RED/GREEN 日志及全回归证据；保留测试审计历史。

## 修改文件

现有业务代码、Tool Gateway、Model Gateway、Hybrid Retrieval、旧 Agent、前端、数据库模型、迁移、依赖和配置文件：**无修改**。199 文件 SHA-256 基线核对：**零修改、零缺失**，证据为 `work/runtime/baseline_verified.json`。

## 测试结果

最终完整回归实际运行：**548 项通过，0 失败，0 错误，0 跳过**；pytest 用时 **61.34 秒**。包含 80 个新增 Runtime 测试、89 个既有 Model Gateway 测试及全部旧后端测试。存在一条已有 AnyIO 弃用警告。

最终证据：`work/runtime/reviewed_full_suite.json`、`reviewed_full_suite.xml`、`reviewed_full_suite.log`。此前 543 项通过的完整记录也保留。

| 要求 | 实际验证 |
| --- | --- |
| 单 CVE 查询 | 实际 Task、Gateway 收据、Artifact、数据库重读与幂等 |
| CVE→版本匹配→风险 | 调用现有三个工具，按依赖时间执行，保留 UNCERTAIN/WAITING_REVIEW |
| PoC/Patch 并行 | 调度 barrier 与真实 Worker 时间重叠双重证明 |
| 非法 DAG | 循环/缺依赖/重复/超预算拒绝；非法计划零工具、零新运行 |
| 失败恢复 | 工具异常正确 FAILED，下游 BLOCKED，独立分支 SUCCESS |
| 真正超时 | Windows Job 终止任务及子进程，无迟到文件/成功结果 |
| 可信来源 | 未核验 Evidence 保留 RawDocument、revision、locator 和 verified=false |
| 兼容与隔离 | 原认证 GET、所有者隔离、新旧幂等隔离、并行持久化 |

首次完整回归发现提交型 Runtime fixture 影响旧测试空库假设；已隔离两套测试库后全通过，未修改旧测试或取消审计保护。所有集成数据明确为合成测试样本，不能当作真实漏洞 Benchmark。

独立只读审查发现三个重要问题，全部修正并通过 RED→GREEN 复现：正常退出跨越截止时间、超大证据导致工具收据丢失、运行中旧任务视图显示 pending。超大证据完整保留在工具记录，以数量和摘要在 FAILED Artifact 中引用；父进程验证引用，篡改数量、摘要或 verified 标记会失败。审查记录见 `work/runtime/final_review.md`，没有未解决的重要问题。

## 当前限制

- 未切换网页提问入口，没有 SSE/新页面/动画。
- 没有 LLM Planner、多 Agent 协作或新 Integration Gate；模型生成调用为零。
- Windows 进程终止真实验证通过；Linux 进程组实现尚未在 Linux 主机验证。
- 同步运行，未实现服务重启后的任务恢复或自动人工复核续跑；持久化故障返回 STORE_FAILED。
- 显式写工具需服务端授权，已提交的写操作不会因后续超时自动撤销。
- 图表示依赖和执行次序；首期工具参数为常量，依赖引用为 Artifact ID，没有通用表达式或动态参数绑定。
- 一项审查小问题暂缓：旧 ToolCallRecord 时间由保存时间与耗时推算，不能当作精确执行时间；任务时间与耗时仍准确。后续只能改进新记录的首次写入，不修改已有审计记录。

实施取舍及代价已记录：无 Git 工作区使用文件哈希、保留证据，缺少 Git 回滚能力；测试审计记录保留，测试库会累积少量合成历史；完整旧回归另用一次性 PostgreSQL 测试集群，增加本地磁盘占用。未删除本机项目或审计历史。

对审查中暂不判断的两项已明确决策：Linux 分支保留但尚未实机验证，代价是部署到 Linux 前还需验收；服务重启和数据库故障后的自动续跑按批准范围不新增，代价是中断运行可能需要人工检查与新请求键。

## 下一阶段建议

**本阶段结束后停止开发。** 后续可按新指令决定 Phase 10-B 的 Model Gateway / Planner 接入，再决定专业 Agent、Integration Gate 和前端正式联调。已有 Gateway、检索、安全业务不重建。
