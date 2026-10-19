# AegisAI 前端工作台

现有前端使用 JavaScript ES modules、History Router 和 Node 内置 HTTP 同源代理。调查页已实现提交、状态轮询、Trace、Artifact、Gate、结构化答案和证据引用；旧 Assistant 方法保留兼容用途。

## 启动

从仓库根目录运行 `node frontend/server.mjs`，打开 `http://127.0.0.1:8769/assistant`。默认代理到本地后端8000。完整依赖、数据库和模型准备见[Windows快速启动](../QUICKSTART_WINDOWS.md)。不要直接使用历史文档中的个人运行时绝对路径。

受保护接口使用后端配置的本机访问令牌；单独启动代理时在页面密码字段输入同一令牌。令牌不属于提交材料。显式本地演示模式可由原启动器在服务端注入令牌，但原启动器依赖开发机便携数据库缓存。

## 页面与数据

`/dashboard`、`/vulnerabilities`、`/assets`、`/reviews`、`/assistant`、`/system` 及已实现的详情路由。真实模式读取后端；Mock 模式只用于前端开发与协议回放。新数据库不会自动安装演示数据。

轮询在调查终态停止；缺上下文、证据冲突、需人工复核和服务错误按接口状态展示。现有界面仍有窄屏、高级字段和可读性限制，不能由接口测试推断全部GUI已验收。

## 测试

在 frontend 目录运行 `npm ci`，再运行 `npm test`。jsdom 是锁定的DOM测试开发依赖。测试使用协议或页面fixture，真实浏览器与后端调查记录应分别评价。本轮发布未重跑完整前后端测试或49题实验。
