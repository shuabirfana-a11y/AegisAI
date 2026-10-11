# 真实协议离线参考

- openapi.json：当前 FastAPI 导出；34 个实际操作，无建议路由。
- http-apis.json / HTTP_API_REFERENCE.md：逐项请求/返回、权限、错误和源码定位；示例请求均标 Mock。
- *.schemas.json / *.d.ts：当前 Pydantic 或现有 HTTP 行/序列化结构的映射，保留原字段及枚举。internal 仅内部协议。
- tools.registry.json：37 个工具的真实注册定义；外部 invoke 权限仍受只读限制。
- examples/：Phase 12-A.5 的原始脱敏导出。生产数据=false；测试合成/Schema Mock 区分标注。

HTTP 成功响应未声明 response_model，不能依靠 OpenAPI 的空对象生成业务返回类型；配合 contracts/generated/http-responses.ts 使用。源文件定位指完整项目，源码不随包附带。

本包实际核对结果与哈希见 [VALIDATION](../../VALIDATION.json) 和 [MANIFEST](../../MANIFEST.json)。
