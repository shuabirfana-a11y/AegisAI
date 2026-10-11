# 当前离线契约

- openapi.json：当前FastAPI原样导出，42个HTTP操作、41条路径。
- investigation-http.openapi.json：八个调查操作及实际公共Schema。
- investigation-http.d.ts / investigation-client.ts：队友优先使用的公共类型和Client，放在同一目录。
- http-apis.json：真实路径、权限、浏览器代理限制及响应边界。
- http-input / tool-input / internal-input / internal-output / legacy-output：已有Schema和内部/旧协议映射；内部输出不是新的浏览器响应。
- HTTP_API_REFERENCE.md：旧34操作的逐项参数与错误参考，新增八操作见 [调查规范](../INVESTIGATION_API.md)。

旧操作OpenAPI描述不替代兼容返回逻辑；新调查严格Pydantic。原始历史fixture、验证时间和内部字段均保留来源说明。
