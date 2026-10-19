# 前后端整合记录

本分支整合当前后端交付候选与团队调查工作台，保留已有业务规则和接口适配。

|来源|版本|
|---|---|
|后端与当前整合基线|`a8140fc21b7b25299a38e9a81762e07a498d4ab6`|
|团队前端|`frontend/wang-investigation-workbench`，`e982b400e374318399f77d7a06bbcfe53fc3b80f`|

## 合并处置

队友的看板、路由、资产/复核详情、全局搜索和调查工作台已通过早期整合补丁进入当前候选，Git 历史未记录两个前端提交的直接合并关系。本次建立正式双亲合并记录，不以较早前端覆盖后续接口适配。

四处冲突分别保留了现有修正：

- `investigation-client.js`：结果版本参数与非法版本拒绝。
- `pages/assistant.js`：调查身份及 Gate 引用绑定、旧异步回执隔离、缺上下文与终态处理。
- `pages/vulnerabilities.js`：详情加载、空值、冲突和错误状态。
- `tests/investigations.test.mjs`：结果版本接口回归。

合并后的后端289个 Python 文件和前端 public 下23个文件与正在运行的交付候选哈希一致。此次合并未修改模型、Planner、Verification、Gate、Gold 或评分规则。

## 实际验证

2026年10月19日在独立工作区执行：

```text
node --test frontend/tests/*.test.mjs
72 passed, 0 failed, 0 skipped

python -m pytest tests/investigation_api/test_contract.py tests/integration/test_contracts.py -q --tb=short
20 passed, 1 deprecation warning
```

前端DOM测试使用现有锁定的开发依赖 jsdom 26.1.0。测试中的合成夹具用于契约和交互验证，真实业务证据另行保存。

从本分支启动独立前端代理，连接已有正式后端8066：健康、历史、状态、Trace、Artifact、Gate、答案7个只读检查均返回200。真实浏览器打开总览及调查工作台，读取既有调查 `2196641f-b655-4d56-8cba-d6c540bd53f5`，调查根标识和 Trace/Answer 对 Gate 的引用一致，仍显示 `PASS_WITH_WARNINGS` 与 `COMPLETE_WITH_WARNINGS`。没有新建调查、调用模型或运行49题。

首次诊断脚本误用 AnswerEnvelope 的字段名 `investigation_id`，已按正式契约改查 `logical_investigation_id`；原诊断记录保留，未修改生产实现。

## 使用方式与范围

新机器按根目录 `QUICKSTART_WINDOWS.md` 配置数据库与真实模型，使用 `node frontend/server.mjs` 启动前端；默认8769代理至后端8000。当前开发机的8066与临时前端端口是既有运行配置，不应直接替代新机器启动配置。

本次验证复用已有健康后端，并不构成冷启动、全部GUI、并发或长期可靠性验收。Windows Worker 组合执行的已知限制保留，C25源码与数据库备份未改动。

本地完整检查日志、源码哈希和截图保存在 `outputs/final-frontend-backend-integration/`。本次仅本地整合，不自动推送或合并远程PR。
