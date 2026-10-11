# 技术栈冻结

| 项目 | 决定 | 理由/替代与成本 |
|---|---|---|
| Python | 3.12；本次验证运行3.12.14 | 现有运行时和库可用，避免新语言/版本迁移 |
| Web | FastAPI；当前官方release0.142.2作为安装候选 | 类型/OpenAPI复用；Flask需要更多接口schema工作，本期没有Django后台需求 |
| ORM | SQLAlchemy **2.0系列**，同步session | 官方2.0文档与稳定接口；不为刚发布2.1追新，不加异步DB复杂度 |
| DB/driver | PostgreSQL17当前安全minor；psycopg3 | 本次官方版本页17.11受支持；用事务/unique保证幂等，不用SQLite替生产约束。psycopg许可LGPL-3.0需保留通知，binary/libpq组件另登记 |
| Migration | Alembic1.x | 版本化schema，不手写启动时CREATE TABLE |
| 模型 | Pydantic2；本次已用2.13.5验证 | 自动schema/输入输出约束，unknown字段在metadata/raw留存 |
| HTTP | httpx0.28.1 | timeout/transport/连接池复用；首期并发有上限，不叠requests与多个HTTP栈 |
| Scheduler | 手动run-once＋OS任务计划/部署调度 | Windows任务计划或Linuxtimer执行短任务，PG advisory lock防重入；不把scheduler塞每个API worker；不用Celery/Redis/新scheduler服务 |
| Version | packaging26.3本次实测 | PyPI PEP440；OSV events用版本比较，禁止继承SpecifierSet默认预发布过滤；其他生态UNSUPPORTED |
| Product | packageurl-python＋明确生态的本地可审核映射 | PURL身份+规则，torch/pytorch不靠字符串自动等同 |
| Sources | CVE List V5＋OSV API＋CISA KEV，CISA ADP在CVE内解析 | 两源先跑通最小切片，再加入KEV；身份/状态+包语义+利用信号；NVD/GHSA/EPSS后续富化批次 |
| Evidence | PostgreSQL记录＋本地sha256地址raw blob | 不变字节与定位，可替换对象存储；首期不添MinIO服务 |
| Tests/Lint | pytest9.1系列；ruff0.16系列 | offline fixture为主；版本边界、事务/错误测试，不靠LLM自评 |
| Container | Docker Compose Specification，API/collector/DB | Windows需Docker Desktop/WSL2或远端Linux；本机未发现docker。Docker Desktop商业条款与Compose代码Apache许可分开 |

这是技术/兼容系列冻结，不是已经解析验证过的完整lockfile。下一编码阶段在隔离环境安装、锁精确补丁与镜像digest，执行迁移/端到端后才承诺组合可运行。没有安装产品依赖、初始化DB或创建正式服务。本轮只使用现有Pydantic/packaging做临时验证。

官方依据：[FastAPI](https://fastapi.tiangolo.com/)、[SQLAlchemy2.0](https://docs.sqlalchemy.org/en/20/)、[PostgreSQL支持表](https://www.postgresql.org/support/versioning/)、[HTTPX](https://github.com/encode/httpx)、[Pydantic](https://github.com/pydantic/pydantic)、[Psycopg](https://github.com/psycopg/psycopg)、[Docker安装](https://docs.docker.com/engine/install/)。新增基础依赖的实际仓库/许可/release记录见baseline_dependencies.json；代码许可不免除分发和服务条款。
