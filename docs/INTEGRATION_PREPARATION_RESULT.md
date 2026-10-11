# AegisAI 已有成果集成准备

日期：2026-10-11。仓库为 `shuabirfana-a11y/AegisAI`；集成分支为 `chore/aegisai-integration`。这是主分支合并前的审查材料，不表示 main 已发布。

## 集成范围

- 调查 API：`feature/investigation-api`，提交 `4bf2f906807bd76dd878957c7d859d0b71040823`。
- 评测与标注准备：`feature/ground-truth-dataset`，提交 `57d5704ca613c599154f833e3acef7f66403f928`，包含原PR #2、#3、#4。
- 解决唯一的CI文件冲突，同时保留调查HTTP契约检查、评测框架测试和既有离线烟雾检查。
- PR检查覆盖所有目标分支，修复原先堆叠PR没有自动触发CI的问题。安全扫描失败时只输出规则、文件、行号和提交指纹，便于定位；不打印密钥值。
- README、贡献规范和GitHub流程说明更新为实际实现状态；旧API计划保留并标明已被替代。新增 `CURRENT_STATUS.md` 统一记录未完成事项。

对比两个来源提交：`backend/`、`frontend/`、API导出脚本、前端契约与交接包没有额外改动；`evaluation/`、`tests/aegisbench/`、`evaluate.py` 与标注来源提交一致。未修改Agent、Planner、Runtime、风险逻辑或Gate规则。

## 本次实际运行

下列命令在合并候选工作区执行，使用已有Python虚拟环境；未连接业务数据库或真实模型。

| 命令 | 结果 |
|---|---|
| `python scripts/ci/run_backend_tests.py` | 423通过、1明确排除；1条已有弃用警告 |
| `python -m pytest tests/aegisbench -q` | 48通过 |
| `python -m unittest discover -s tests/engineering -v` | 6通过 |
| `node --test frontend/tests/*.test.mjs` | 23通过、0失败、0跳过 |
| `node .github/node_modules/typescript/bin/tsc -p .github/tsconfig.contracts.json` | 退出0 |
| `node scripts/ci/check_frontend.mjs` | 17个JavaScript文件语法检查通过；当前应用未配置构建脚本 |
| `python scripts/ci/check_contracts.py` | 42个HTTP操作、5组Schema、40个合成对象通过 |
| `python scripts/export_investigation_api.py --check` | 10个导出文件与代码一致 |
| `python scripts/ci/check_repository.py` | 索引安全检查通过；不读取或输出密钥值 |
| Gitleaks 8.30.1完整Git历史扫描，启用100%脱敏 | 本地未处理告警0；精确历史例外沿用已有复核记录 |

没有把历史1288项数据库回归算成本次重跑；本次针对已有代码集成与CI契约检查。GitHub CI结果以集成PR当前提交的Checks为准。CI中的离线评测烟雾检查只检验框架运行，不构成正式准确率或模型对比实验。

## 标注材料核对

新版有49个不同问题ID、49张DRAFT任务卡，三批分别10/20/19题，分配覆盖49题且不重复。问题文件SHA-256为 `f1f4be86e202ec263c6ebac66782b74d265840d706b559d913ab0c8c5f45e6f1`，与冻结来源一致。旧v0.1的24题继续保留。

人工完成和批准记录仍为0。没有填写答案、编造标注人或把候选资料升级为标准答案。新版题目覆盖5个公告簇，不能描述成49个独立漏洞。

## 仍待完成

负责人审查并确认集成PR后，才将成果发布到main。人工标注及独立复核、队友调查工作台联调、真实模型配置、正式评测和公网部署继续按各自阶段推进，不能仅因本次集成而宣称完成。
