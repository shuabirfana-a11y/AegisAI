# 独立审查记录

审查对象：Phase 14-B1 分支相对 Phase 14-A 基线的 PoC 标准化、富化快照、只读 HTTP 与契约。
审查人员：Codex 独立只读代码审查 Agent；未修改文件、索引、HEAD 或数据库，未运行攻击或扫描。

## 已解决问题

- 异常 README/Locator 的读取异常：明确判为无效证据；README 失败保留较弱搜索证据与 PARTIAL。
- 尾点内部域名、签名参数、Token 查询/片段：拒绝包含凭据的引用。
- 超过 128 条历史证据：保留当前与真正验证依据，明确裁剪计数。
- 未来/过期核验及旧修订：不用于当前有效利用状态。
- 旧验证证据不能借用另一条新鲜关联证据；只有具体有效验证证据本身满足条件才可采用。
- Candidate 的 Source 必须对应原 Observation/Raw，防止错误归因。
- 人工核验不能提前确认随后才获取的证据；投影与 DTO 同时检查时间顺序。
- 原列表/详情 PoC 汇总和新查询采用同一规则；旧原始字段保持兼容。

新增测试先复现缺陷，再验证修复；最终专项 186 项通过。

## 最终意见

Ready within Phase 14-B1 scope. No open critical or important findings.

纯读取探针确认：当前链接人工依据能确认；核验后才获取的依据保持候选；DTO 拒绝不一致时序。
契约导出一致，无空白格式问题，无新增写/攻击接口，无 Agent/Planner/Runtime/Gate 业务修改。

## GitHub CI 同期远程数据误报

GitHub 全历史扫描包含队友刚上传的 frontend/public/mock/investigation-demo.json，10 个合成 request_key 被识别为 generic-api-key。
该文件的 JSON 与原交接包完全相同，标记为 DEMO、production_data=false、合成种子执行结果。
仅添加 10 个精确 commit:path:rule:line 排除；没有修改队友前端文件或扩大路径排除。
使用 --all --full-history（含同期提交与 CI merge audit ref），扫描器报告扫描 69 个提交、0 发现。
扫描器计数不等于可达 Git 提交总数。独立审查确认仅增加 10 处精确例外、未移除既有规则，
request_key 为 actor 范围内的幂等标识，HTTP 鉴权是另一个机制。依据见 CI_SCAN_PROOF.json。

## 未评判事项

- 实际利用与扫描：本阶段明确禁止。
- Ground Truth、评分和历史实验：本阶段保护且未修改。
- 生产压力性能：未进行压测。
- 两项已知 Unknown Context 全量失败：不属于 PoC 范围，未通过修改核心逻辑绕过。
