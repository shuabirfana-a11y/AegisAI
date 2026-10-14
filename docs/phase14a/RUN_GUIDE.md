# 本机运行与团队复现

在项目 backend 目录使用现有 Python 环境、PostgreSQL与已完成的 Alembic版本。无需新增依赖或表结构。采集前设置本机 `AEGIS_DATABASE_URL`，使用自己明确指定的开发/演示库，不能指向正式评测隔离库。

## 一次采集

```powershell
python -m app.monitoring.cli --source NVD --source RSS_TRAIL_OF_BITS --source ARXIV --limit 2
```

默认只排队已有富化任务，不把 QUEUED 当作已完成。需要处理时：

```powershell
python -m app.monitoring.cli --source NVD --source OSV --source ARXIV --limit 2 --process-enrichment 6
```

复用原六种富化服务及依赖；一项失败保留已获取数据，失败类型写入来源/作业记录。输出明确 LIVE_PUBLIC_SOURCE_COLLECTION；测试不会使用这个标识冒充实时。

## 周期监测

```powershell
python -m app.monitoring.cli --all --limit 10 --cycles 1440 --interval 300 --process-enrichment 6
```

这是最多约五天的前台工作进程，需让进程与电脑保持运行。每轮检查各源独立的到期时间；原三源保持原获取限制。新源HTTP默认15秒、一次重试、每请求至少6秒、2MB上限。`--force` 是明确操作员刷新，不适合每轮强制重抓。错误独立报告；默认不会自动恢复长期遗留的 running 作业，以免重入覆盖。

NVD每次刷新声明的已知AI CVE，不做全量发现；CVE/OSV/GHSA承担既有或新增有界发现。GHSA/厂商公告只取有限窗口与记录数量。RSS最多解析100项；arXiv使用有界LLM/security相关性查询、摘要和元数据，明确不是最新论文全覆盖。

arXiv本次带更新排序的请求遇到429，窄范围相关性查询实际成功。上游失败时记录 FAILED，不能拿之前的成功冒充最新。HTTP不跟随任意跳转，也不抓正文链接。

## 使用已有调查链

已启动原FastAPI服务并配置本机 `AEGIS_ASSET_TOKEN` 后，可通过客户端使用原八调查API，或者：

```powershell
python -m app.monitoring.cli --source NVD --limit 1 --investigate CVE-2025-32434 --api-base-url http://127.0.0.1:8000
```

该选项只向原 HTTP Orchestrator 提交一次问题，不直接调用Agent或模型SDK。CLI要求精确、由操作员提供的CVE；不补造企业资产或版本。运行模型沿用已配置 Model Gateway，Mock/REAL与Planner审计仍由原系统记录。

## 配置与隐私

可选 `AEGIS_GITHUB_TOKEN`、`AEGIS_NVD_API_KEY` 只放本机环境；不写进参数、源码、日志或前端。没有这些Key仍支持限额内公开请求，受上游可用性影响。本次保持Qwen及Prompt不变，知识Embedding使用已有缓存CPU模型，不在请求中下载模型。

本次临时库、端口、授权令牌和原始Feed仅保存在机器私有工作目录；交付包只含受控元数据、哈希与引用位置。新增CLI、OpenAPI和TypeScript声明已通过针对性测试。前端布局仍由队友实现。
