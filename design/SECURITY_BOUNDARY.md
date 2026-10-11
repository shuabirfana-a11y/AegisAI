# 安全边界

外部内容默认Untrusted；V0.1没有LLM，V0.2也不能把raw变成系统prompt或授权指令。采集host/路径仅CVE官方固定raw、api.osv.dev和CISA官方KEV镜像，reference不自动follow；拒绝私网/metadata/非HTTP、逐跳与出站约束。响应限字节、连接/读取/批次预算；JSON结构深度/长度限制，不运行CVE描述中的代码。

raw字节存固定sha256路径，无用户路径参与；HTML以后以octet-stream下载、禁内联执行/CSP，正文与提取内容另标parser，不覆盖raw。Unknown PoC、模型pickle、repo脚本禁止执行。本期没有第三方Plugin/MCP，数据库只API/collector/迁移专用角色，禁止superuser当应用角色。

secret用运行环境/受限secret文件，不写fixtures/metadata/git；数据库连接串/Authorization/key/query敏感字段从日志剔除。测试仅公开包/CVE数据；私有资产不发OSV/Jina/LLM。API读令牌与源API令牌分开；source scopes和环境变量不可由用户请求覆盖。

重复/修订保留lineage；事实模型支持反驳/冲突，不以源数量当置信度。网络和数据库错误不给假成功/覆盖旧可信记录。raw与DB同步备份/恢复验证；演示只localhost，后续外部部署再做TLS、角色和租户策略。

许可：源数据按上游授权和署名保存；当前CVE条款本轮提取不完整，公开再分发前补核对。fixtures是开发观察，不等于所有公告/代码获得无限发行权。Psycopg LGPL/Compose Apache/可能的Desktop条款分别记录。
