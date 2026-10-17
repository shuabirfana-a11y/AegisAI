# 发布前敏感信息检查

已扫描实现暂存区、结果暂存区和全部 Git 历史。实现扫描为零发现；结果初扫有 67 个 generic-api-key 命中，逐项核验均为非凭据元数据。

类型：bench-UUID 幂等请求标识、CVSS scope 的 SHA256、Evidence locator 的 SHA256、受保护文件的 SHA256。locator 根据同一记录的 locator 字段重新计算并比对；文件摘要根据真实文件字节重新计算并比对。scope 的产生位置为 backend/app/repositories/ingestion.py，locator 为 backend/app/enrichment/evidence.py；这些值没有认证用途。

检查结果：没有真实模型 Key、API Token、数据库密码或连接串进入本阶段交付。单独比对本轮私有认证 Token 的字节，所有暂存文件均不含它。私有 token/database 配置和运行日志在 work/ 下，不在 Git 或文档包内。

只为已审查的结果提交登记精确 commit/file/line/rule fingerprint，保留原扫描规则，没有排除整个目录或关闭 generic-api-key。逐项位置见 secrets-scan-identifiers.json；原始模型/HTTP 记录没有为了躲避扫描删改。

执行命令：

```text
gitleaks git . --staged --redact --no-banner --report-format json --report-path <private-report>
gitleaks git . --redact --no-banner --log-opts="--all --full-history" --report-format json --report-path <private-report>
python scripts/ci/check_repository.py
git -c core.whitespace=cr-at-eol diff --cached --check
```

精确登记后全历史扫描为零未处理发现，Repository safety 为 PASS，空白检查通过。敏感信息扫描是发布检查，不能当成系统安全效果或 Benchmark 指标。
