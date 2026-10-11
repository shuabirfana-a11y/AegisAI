# 历史敏感信息扫描复核

工具：Gitleaks v8.30.1，[官方来源](https://github.com/gitleaks/gitleaks/releases/tag/v8.30.1)。本机 Windows 归档对照发布 checksums 验证；CI Linux 归档固定 SHA256，扫描完整 Git 历史，输出启用 100% redaction。

## 初始扫描

初始提交 d5bf67321fa9641d01260234c0f3c9691fed2ca3，约 28.91 MB 文本，84 个候选项对应 60 个不同 commit/path/rule/line 指纹。逐类复核后未发现 AegisAI 私密凭据：

| 类型 | 候选数 | 依据 |
|---|---:|---|
| 文件/接口 SHA256 | 7 | MANIFEST、manifest 与冻结源码基线中的校验值 |
| 合成幂等编号 | 30 | 三份固定 Mock 回执中的 ORCH 加随机 UUID；不是登录凭据 |
| 实现标识比较 | 1 | 测试代码比较 implementation_key；没有密钥值 |
| Zenodo 文件名 | 1 | 公共 files[].key 是 CVEfixes_v1.0.8.zip |
| NIST 网页公开 Mapbox 参数 | 3 | 原公开 HTML 中的 pk. 浏览器公开访问参数；不是项目私密服务 Key |
| SAMR/Google 公共链接参数 | 22 | 标准/文章访问标识；32 位链接 key 和新闻订阅链接 |
| GitHub curl 文档占位符 | 3 | YOUR_CLIENT_ID、YOUR_CLIENT_SECRET 官方示例 |
| GitHub JSON 示例临时 clone 字段 | 17 | HTML 的 code 样例属于 octocat/Hello-World 等公开示例，private=false；没有本项目账号令牌 |

复核未连接上述参数所代表的服务、未尝试使用任何第三方 token。原始匹配值与报告不提交；仅公开数量、位置指纹和判定依据。

## 例外边界

.gitleaksignore 只记录上述初始提交的 60 个准确历史指纹。没有 blanket 路径排除，没有关闭通用 API Key 规则，没有把整个 tests、docs、research 或 Mock 目录设为可信。未来提交即使改相同文件，也必须重新通过扫描。

忽略指纹复核后历史重扫为 0 个未处理告警。扫描发现新真实凭据时停止推送；先撤销/轮换凭据，再由负责人处理历史，不自动 force push、删除历史文件或重写共享仓库。发现疑似误报先核对来源，不能直接追加忽略。

## 双重检查

scripts/ci/check_repository.py 另检查 Git 索引，拒绝 .env、私钥、数据库/日志、虚拟环境、node_modules、临时 work 文件。唯一 work 例外是已冻结的纯文件哈希基线。该检查不读取或打印敏感值。配置模板 .env.example 可保留占位内容。

Gitleaks 的准确指纹忽略只适用于 Git 历史扫描；检查当前未提交文件时仍需避免把本机数据库/虚拟环境递归输入扫描器。临时导出 Git 索引进行本阶段补充扫描的副本放在忽略的 work 目录。

以上是工程扫描及复核结果，不是“绝对不存在任何敏感信息”的保证。当前仓库继续保持 private，禁止在文档或日志中输出真实模型凭据与私人资产数据。

## Phase 12-B 补充扫描

本轮新增代码阶段的暂存差异扫描为 0 个候选。更新 MANIFEST 后，差异扫描的 2 个命中分别是删除前的旧 current_openapi_sha256 与新增的当前字段；旧值与历史 MANIFEST 一致，当前值与实际导出 OpenAPI 字节的 SHA256 一致。两者都是文件校验摘要，不是 API 凭据。

历史扫描若再次命中当前摘要，仅加入经过复核的准确 commit/path/rule/line 指纹，不排除整个 MANIFEST、契约目录或规则。扫描启用完整脱敏，原始扫描报告保存在忽略的 work 目录，禁止推送发现的真实私密凭据。
