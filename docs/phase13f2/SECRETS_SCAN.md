# 敏感信息检查

实现暂存扫描：0 发现。结果扫描的 38 个 generic-api-key 告警逐条复核后均为：

- 评测 `idempotency_key`（bench + 随机请求 UUID）：去重标识，不能授予访问权限。
- `scope_key` 的 SHA256：原 ingestion 对 CVSS 作用域字符串的摘要（repositories/ingestion.py），不是服务凭据。

原始响应未为躲避扫描而删字段或改写。仅将准确提交、文件、行号和规则的 fingerprint 加入既有 `.gitleaksignore`；无目录、字段或规则级放行。逐项分类见 secrets-scan-identifiers.json。

私有 API Token 已与全部结果暂存文件逐字节检查，未出现；本轮模型服务使用原本机无 Key 配置。数据库连接、本机 Token、进程和服务日志仍保留于忽略的 work 目录，不进入 Git 或交付包。

完整 Git 历史扫描在精确误报登记后重跑；只有零剩余告警才允许推送。CI 的原全历史扫描规则不改。
