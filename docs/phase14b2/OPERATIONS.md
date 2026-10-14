# 多源监测自动流水线使用说明

## 启动方式

先按现有部署说明配置本机 `AEGIS_DATABASE_URL`。在 backend 目录执行：

```powershell
python -m app.monitoring.cli --source NVD --source GHSA --source VENDOR_VLLM --source RSS_TRAIL_OF_BITS --source ARXIV --pipeline --limit 1 --process-enrichment 2 --cycles 2 --interval 300 --cycle-seconds 300
```

这是两轮有界运行，结束后退出。每轮输出真实 JSON 回执，不安装后台服务，不自动启动模型。
未加 `--pipeline` 时保留原 CLI 行为；新模式处理选定来源及其积压，不处理全局无关队列。

`--force` 仅强制第一轮获取，后续按 Source.update_interval 判断；未到期可以继续富化旧批次。
默认每轮运行 6 个根富化任务；显式 `--process-enrichment 0` 只排队，不执行根任务。
原 EnrichmentService 可能增加 vendor 等依赖操作，根任务预算不是 HTTP 请求或所有依赖任务总量。
`--cycle-seconds` 是启动下一项工作前的截止时间，当前操作按原 HTTP/业务超时完成。

首次 CVE_LIST 需要已有 Git 缓存；自动模式默认返回 DEFERRED，避免意外下载大库。
确有需要时再显式使用 `--allow-cve-bootstrap`，沿用原过滤 Git 采集器。

## 来源范围

共复用 11 个注册来源：CVE_LIST、OSV、CISA_KEV、NVD、GHSA、三个固定官方仓库、两个安全博客和 arXiv。
GitHub 官方仓库与 GHSA 可能共享发布者，不能把它们当作独立证据投票。
NVD 按声明的 CVE 窗口读取；GHSA/厂商按既有公告和仓库窗口读取；RSS/论文只保留有限元数据、片段。
来源能力不是全量覆盖，本阶段也没有遍历所有历史漏洞或论文。

## 状态和失败

- 来源：SUCCESS、PARTIAL、FAILED、NOT_DUE、BUSY、DISABLED、DEFERRED。
- 流水线：SUCCESS、PARTIAL、FAILED、CANCELLED、BUSY；有待执行任务、依赖失败或未完扫描时不能报全部完成。
- 情报：DISCOVERED、NORMALIZED、ENRICHING、VERIFIED、AVAILABLE。
- 核验：CONFIRMED、PENDING、CONFLICT、INSUFFICIENT_EVIDENCE，沿用原规则。

AVAILABLE 表示数据可查，不能表示所有 Claim 已确认或 PoC 可以利用。
没有证据时保留未知；原失败、冲突、候选均保留。流水线不替代专业 Verification Agent 或 Gate。

根任务只处理当前批次及同来源、同模式的未完积压。历史扫描每轮最多 100 个源运行，游标轮转，
避免一个旧 RUNNING 任务长期阻塞后面的批次。已有无标识历史不自动改成 LIVE；Mock 不静默进入实时模式。
SyncRun 保留原采集时间、范围、模式和错误；最多保留最近 20 个流水线续跑回执，原数据库任务历史不删。

Ctrl+C 取消当前自动周期并落盘取消回执。若原领域任务已是 RUNNING，仍需按原恢复流程处理；
不能擅自覆盖成成功或重跑。两套 worker 不应同时操作同一范围：新流水线有 PostgreSQL 锁，旧全局 CLI 不使用该锁。

## 可选资产范围

只有本机明确配置 `AEGIS_ASSET_OWNER` 后，才对该用户已存在且组件匹配的库存调用原重算 worker。
默认不创建资产、不猜版本、不扫描企业系统。公共接口不返回该用户 ID 或库存内容。

## 数据真实性

LIVE 使用原注册远程来源；网络失败写入 FAILED，不切 Mock。
MOCK 仅允许专用 `aegis_phase5_test` 数据库中的显式测试注入，不提供伪实时来源。
本阶段的合成测试、真实网络采集和业务准确率完全分开；没有新增 Benchmark 或准确率结论。

## 只读接口

```text
GET /api/v1/intelligence/records?type=vulnerability&offset=0&limit=20
GET /api/v1/intelligence/monitoring/runs?source=NVD&offset=0&limit=20
```

使用实际 OpenAPI/TypeScript，不使用示例 `/api/intelligence` 作为实现 URL。
这两个 GET 不触发采集、模型、资产重算或新的调查。

本次实际网络回执见 `live-receipt.json`：部分来源失败是实际结果，不是全来源接入成功的证明。
