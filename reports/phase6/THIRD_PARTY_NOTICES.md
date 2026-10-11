# 实际依赖与第三方许可

Python 3.12.14；requirements.txt 为实际 pip freeze，requirements.in 为直接依赖升级范围。pip check 无损坏依赖。许可证取自安装分发 metadata，原始 LICENSE/NOTICE 复制到 licenses/，不自行改写授权条款。

| 依赖 | 版本 | 用途 | 分发声明许可 |
|---|---|---|---|
| alembic | 1.20.0 | 版本化迁移 | MIT |
| annotated-doc | 0.0.5 | 传递依赖/运行与测试支撑 | MIT |
| annotated-types | 0.8.0 | 传递依赖/运行与测试支撑 | MIT |
| anyio | 4.15.1 | ASGI/HTTP 并发运行基础 | MIT |
| certifi | 2026.7.22 | TLS CA 证书库 | License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0) |
| click | 8.5.0 | 传递依赖/运行与测试支撑 | BSD-3-Clause |
| colorama | 0.4.6 | 传递依赖/运行与测试支撑 | License :: OSI Approved :: BSD License |
| cvss | 3.6 | CVSS 2/3/4 向量评分 | License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+) |
| fastapi | 0.142.2 | 五条只读 API | MIT |
| greenlet | 3.5.6 | 传递依赖/运行与测试支撑 | MIT AND PSF-2.0 |
| h11 | 0.16.0 | 传递依赖/运行与测试支撑 | License :: OSI Approved :: MIT License |
| httpcore | 1.0.9 | HTTPX 连接与协议层 | BSD-3-Clause |
| httpx | 0.28.1 | 统一 HTTP 客户端 | License :: OSI Approved :: BSD License |
| idna | 3.20 | 传递依赖/运行与测试支撑 | BSD-3-Clause |
| iniconfig | 2.3.0 | 传递依赖/运行与测试支撑 | MIT |
| Mako | 1.4.3 | 传递依赖/运行与测试支撑 | MIT |
| MarkupSafe | 3.0.4 | 传递依赖/运行与测试支撑 | BSD-3-Clause |
| opentelemetry-api | 1.45.0 | 依赖提供的 tracing 接口；本阶段未配置遥测导出 | Apache-2.0 |
| packageurl-python | 0.17.6 | 规范 Package URL | License :: OSI Approved :: MIT License |
| packaging | 26.3 | PEP440 版本/PEP503 包名 | Apache-2.0 OR BSD-2-Clause |
| pip | 25.0.1 | 环境包安装工具 | License :: OSI Approved :: MIT License |
| pluggy | 1.6.0 | 传递依赖/运行与测试支撑 | License :: OSI Approved :: MIT License |
| psycopg | 3.3.6 | PostgreSQL 驱动 | LGPL-3.0-only |
| psycopg-binary | 3.3.6 | PostgreSQL 驱动平台实现 | LGPL-3.0-only |
| pydantic | 2.13.5 | 统一中间记录校验 | MIT |
| pydantic_core | 2.46.5 | Pydantic 原生校验实现 | MIT |
| Pygments | 2.21.0 | 传递依赖/运行与测试支撑 | BSD-2-Clause |
| pytest | 9.1.1 | 工程测试 | MIT |
| SQLAlchemy | 2.0.54 | ORM、参数化查询和事务 | MIT |
| starlette | 0.52.1 | FastAPI 的 ASGI/测试基础 | BSD-3-Clause |
| typing-inspection | 0.4.4 | 传递依赖/运行与测试支撑 | MIT |
| typing_extensions | 4.16.0 | 传递依赖/运行与测试支撑 | PSF-2.0 |
| tzdata | 2026.4 | 传递依赖/运行与测试支撑 | Apache-2.0 |
| uvicorn | 0.54.0 | 本机 ASGI 服务 | BSD-3-Clause |

cvss 3.6 分发声明 LGPLv3+，此项目以外部未修改 Python 依赖引用，原许可在 licenses/cvss/LICENSE；发布打包时保留许可与相应来源获取方式。没有移植第三方大型 CTI 项目实现。其他完整元数据见 dependencies.json。

来源数据许可沿用 Phase 2 冻结 source_catalog；条目 publisher/许可 scope 随 Raw 保存。来源页面及转引内容的授权范围不能由数据库去重扩大。测试/实测 raw 示例仅用于开发回查，未做对外数据再发布。
