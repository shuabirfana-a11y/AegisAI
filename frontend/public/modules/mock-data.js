/* 演示模拟数据层。
   用途：后端尚无对应接口的模块（Agent 编排、知识底座、运维监控、富化维度等）
   在前端展示标注清晰的演示数据；有真实 API 的字段一律以 API 为准。
   约定：所有模拟 CVE 使用真实公开编号或 CVE-2025-46xxx 演示区间，页面顶部以 mock-banner 提示。 */

export const AI_RISK_CLASSES = [
  { key: 'infra', label: 'AI 基础设施/推理框架', value: 34, color: '#22d3ee' },
  { key: 'model', label: '模型与数据层', value: 21, color: '#818cf8' },
  { key: 'app', label: 'AI 应用与智能体', value: 27, color: '#34d399' },
  { key: 'supply', label: '供应链风险', value: 15, color: '#fbbf24' },
  { key: 'other', label: '其他自分类', value: 9, color: '#fb923c' },
];

export const KPI_SPARKS = {
  vulns: [12, 18, 15, 22, 19, 28, 24, 31, 27, 35, 30, 38],
  ai: [4, 6, 5, 9, 7, 11, 8, 12, 10, 14, 11, 15],
  latency: [5.1, 4.6, 4.9, 4.2, 3.8, 4.0, 3.5, 3.3, 3.4, 3.1, 3.2, 3.2],
  enrich: [82, 84, 83, 86, 88, 87, 90, 91, 90, 92, 93, 93],
};

export const LATENCY_TREND = [
  { label: '10-12', value: 4.6 }, { label: '10-13', value: 4.1 }, { label: '10-14', value: 3.8 },
  { label: '10-15', value: 3.5 }, { label: '10-16', value: 3.7 }, { label: '10-17', value: 3.3 },
  { label: '10-18', value: 3.2 },
];
export const COLLECT_TREND = [
  { label: '10-12', value: 118 }, { label: '10-13', value: 132 }, { label: '10-14', value: 96 },
  { label: '10-15', value: 145 }, { label: '10-16', value: 128 }, { label: '10-17', value: 152 },
  { label: '10-18', value: 141 },
];

export const MOCK_FEED = [
  { cve: 'CVE-2025-46408', title: 'vLLM 推理框架远程代码执行漏洞', severity: 'critical', cvss: 9.8, source: 'NVD', published: '2026-10-18 06:12', collected: '2026-10-18 08:41', enrich: '已富化', cls: 'AI 基础设施' },
  { cve: 'CVE-2025-46321', title: 'LangChain 提示词注入导致敏感信息泄露', severity: 'high', cvss: 8.6, source: 'GitHub Advisory', published: '2026-10-18 03:47', collected: '2026-10-18 07:02', enrich: '富化中', cls: 'AI 应用与智能体' },
  { cve: 'CVE-2025-46190', title: 'Ray 集群未授权访问致模型权重泄露', severity: 'high', cvss: 8.1, source: '厂商公告', published: '2026-10-17 22:30', collected: '2026-10-18 01:15', enrich: '已富化', cls: 'AI 基础设施' },
  { cve: 'CVE-2025-46102', title: 'Ollama 模型文件解析越界写入', severity: 'high', cvss: 7.8, source: '安全社区', published: '2026-10-17 18:05', collected: '2026-10-17 21:44', enrich: '已富化', cls: '模型与数据层' },
  { cve: 'CVE-2025-46087', title: 'Transformers 反序列化恶意模型执行任意代码', severity: 'critical', cvss: 9.1, source: 'NVD', published: '2026-10-17 14:22', collected: '2026-10-17 17:09', enrich: '已富化', cls: '供应链风险' },
  { cve: 'CVE-2025-45964', title: 'LlamaIndex 检索插件 SSRF 漏洞', severity: 'medium', cvss: 6.5, source: '博客', published: '2026-10-17 09:31', collected: '2026-10-17 13:26', enrich: '待富化', cls: 'AI 应用与智能体' },
  { cve: 'CVE-2025-45933', title: 'MLflow 模型注册中心路径穿越', severity: 'medium', cvss: 6.1, source: 'NVD', published: '2026-10-17 02:14', collected: '2026-10-17 05:50', enrich: '已富化', cls: '模型与数据层' },
  { cve: 'CVE-2025-45871', title: 'Gradio 文件上传校验绕过致 RCE', severity: 'high', cvss: 8.3, source: '安全社区', published: '2026-10-16 20:41', collected: '2026-10-16 23:58', enrich: '已富化', cls: 'AI 应用与智能体' },
];

export const PIPELINE_NODES = [
  { name: '采集', state: 'ok', meta: ['最近 08:41:22', '本批 141 条', '成功率 99.2%'] },
  { name: '清洗去重', state: 'ok', meta: ['最近 08:41:40', '去重 23 条', '哈希+相似度'] },
  { name: 'AI 分类', state: 'running', meta: ['进行中…', '已分类 118/141', '准确率 96.4%'] },
  { name: '情报富化', state: 'running', meta: ['进行中…', '覆盖率 93.1%', '论文/POC/公告'] },
  { name: '入库', state: 'ok', meta: ['最近 08:42:05', '写入 118 条', '冲突 2 条待复核'] },
  { name: '索引', state: 'ok', meta: ['最近 08:42:31', '向量片段 +1,204', 'BM25+向量'] },
  { name: '问答可用', state: 'idle', meta: ['等待索引完成', '预计 08:43', '检索延迟 P95 1.8s'] },
];

export const MOCK_SOURCES = [
  { key: 'nvd-api', name: 'NVD API', type: 'CVE/NVD', enabled: true, mode: '实时监测中', freq: '5 分钟', last: '2026-10-18 08:41', failures: 0, cursor: 'pubDate≥2026-10-18T08:36Z', incr: true },
  { key: 'cve-org', name: 'CVE.org 官方', type: 'CVE/NVD', enabled: true, mode: '定时采集', freq: '30 分钟', last: '2026-10-18 08:30', failures: 0, cursor: 'offset 84,112', incr: true },
  { key: 'ghsa', name: 'GitHub Advisory', type: '厂商公告', enabled: true, mode: '实时监测中', freq: '10 分钟', last: '2026-10-18 08:38', failures: 1, cursor: 'cursor=MjAyNg…', incr: true },
  { key: 'vendor-rss', name: '厂商公告 RSS 聚合', type: '厂商公告', enabled: true, mode: '定时采集', freq: '1 小时', last: '2026-10-18 08:02', failures: 0, cursor: 'etag 9f2c…', incr: true },
  { key: 'sec-community', name: '安全社区（Seebug/奇安信）', type: '安全社区', enabled: true, mode: '定时采集', freq: '2 小时', last: '2026-10-18 07:30', failures: 2, cursor: 'page=1', incr: true },
  { key: 'blogs', name: '安全博客聚合', type: '博客', enabled: true, mode: '定时采集', freq: '4 小时', last: '2026-10-18 06:10', failures: 0, cursor: 'atom updated', incr: true },
  { key: 'arxiv', name: 'arXiv AI 安全论文', type: '论文', enabled: true, mode: '定时采集', freq: '6 小时', last: '2026-10-18 05:00', failures: 0, cursor: 'submittedDate≥20261017', incr: true },
  { key: 'standards', name: '标准政策站点', type: '标准政策', enabled: true, mode: '定时采集', freq: '12 小时', last: '2026-10-18 00:00', failures: 0, cursor: 'sitemap 全量', incr: false },
  { key: 'kev-cisa', name: 'CISA KEV', type: 'CVE/NVD', enabled: false, mode: '手动触发', freq: '—', last: '2026-10-16 12:00', failures: 0, cursor: '—', incr: false },
];

export const MOCK_COLLECT_TASKS = [
  { time: '08:41', source: 'NVD API', dur: '6.2s', added: 14, dedup: 3, result: 'success', note: '增量游标推进至 08:36Z' },
  { time: '08:38', source: 'GitHub Advisory', dur: '3.8s', added: 5, dedup: 1, result: 'success', note: 'GraphQL 分页 2 页' },
  { time: '08:30', source: 'CVE.org', dur: '11.4s', added: 22, dedup: 6, result: 'success', note: '全量校验一致' },
  { time: '08:02', source: '厂商 RSS', dur: '8.7s', added: 9, dedup: 2, result: 'success', note: 'etag 命中 304' },
  { time: '07:30', source: '安全社区', dur: '24.1s', added: 7, dedup: 4, result: 'warning', note: '1 页解析字段缺失，已降级' },
  { time: '07:12', source: '安全社区', dur: '—', added: 0, dedup: 0, result: 'failed', note: 'HTTP 429 限流，自动重试成功' },
  { time: '06:10', source: '博客聚合', dur: '15.3s', added: 11, dedup: 5, result: 'success', note: '内容哈希去重 5 条' },
  { time: '05:00', source: 'arXiv', dur: '31.6s', added: 18, dedup: 2, result: 'success', note: 'AI 安全关键词命中 18/64' },
];

export const DEDUP_STATS = { raw: 864, afterDedup: 631, incremental: 141, byCveId: 142, byTitleSim: 51, byUrl: 28, byHash: 12 };

export const MOCK_INTEL_LIST = MOCK_FEED.map((f, i) => ({
  id: 'INT-2026' + String(1018_000 + i).slice(1),
  title: f.title, cve: f.cve, srcType: f.source, published: f.published, collected: f.collected,
  severity: f.severity, cvss: f.cvss, cls: f.cls, enrich: f.enrich, dedup: i % 3 === 2 ? '已合并' : '唯一',
}));

/* ---------- 漏洞详情富化演示数据 ---------- */
export const MOCK_ENRICH = {
  papers: [
    { title: 'Efficient LLM Serving with PagedAttention：内存管理攻击面分析', rel: 0.93, src: 'arXiv 2309.06180', time: '2026-10-18 08:55', reviewed: true },
    { title: 'Remote Code Execution in Distributed Inference Frameworks', rel: 0.87, src: 'USENIX Security 2026', time: '2026-10-18 08:56', reviewed: false },
    { title: 'vLLM 调度器竞争条件分析与利用链构造', rel: 0.81, src: '安全博客 · 深度解读', time: '2026-10-18 09:02', reviewed: false },
  ],
  poc: { source: 'GitHub 安全研究仓', availability: '可复现', verified: '沙箱验证通过', risk: '仅限授权环境演示', conf: 0.88 },
  assets: { type: '推理服务', product: 'vLLM', versions: '>=0.4.0, <0.6.3', exposure: '公网暴露约 2.1k 实例（第三方测绘引用）', compliance: '未主动扫描，引用公开测绘数据' },
  cvss: { vector: 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H', score: 9.8, explain: '网络可达、无鉴权、三性影响均为高，评分为严重' },
  fix: { patch: '升级至 vLLM 0.6.3+', measures: '临时：关闭 /v1/internal 调试端点；启用 API Key 鉴权；网络侧限制管理面访问', advisory: 'GHSA-2026-vllm-rce' },
  attackChain: [
    { tech: 'T1190 利用面向公网的应用', stage: '初始访问' },
    { tech: 'T1059 命令与脚本解释执行', stage: '执行' },
    { tech: 'T1552 不安全凭证获取（模型权重/密钥）', stage: '凭证访问' },
  ],
  related: [
    { cve: 'CVE-2025-46190', rel: '同组件（Ray 调度链）' },
    { cve: 'CVE-2025-45871', rel: '同利用面（文件上传）' },
  ],
  policy: { name: '《生成式人工智能服务安全基本要求》', org: 'TC260', link: '标准政策库 #STD-014' },
};

export const MOCK_EVIDENCE_CHAIN = [
  { title: '原始漏洞入库', desc: 'NVD API 增量采集 CVE 记录，提取标题/描述/CVSS', time: '08:41:22', state: 'done' },
  { title: '关键词/实体抽取', desc: '识别实体：vLLM、推理框架、RCE；判定 AI 基础设施风险', time: '08:41:47', state: 'done' },
  { title: '检索论文/文章/POC', desc: '向量检索命中论文 3 篇（相关度>0.8）、分析文章 2 篇、POC 1 个', time: '08:42:10', state: 'done' },
  { title: '相关性判断', desc: 'LLM 复核相关性，POC 来源可信度 0.88，通过阈值 0.75', time: '08:42:38', state: 'done' },
  { title: '富化结果写回', desc: '8 个维度富化完成，2 条字段冲突转入人工复核队列', time: '08:43:05', state: 'done' },
];

/* ---------- Agent 编排演示数据 ---------- */
export const MOCK_AGENTS = [
  { name: '采集 Agent', role: '多源轮询与增量游标管理', icon: 'radar', state: '运行中', success: 99.2, runs: 1284, avgDur: '8.4s', tools: ['NVD API', 'RSS 解析', 'arXiv 检索'] },
  { name: '分类 Agent', role: 'AI 安全风险类目判定', icon: 'tag', state: '运行中', success: 96.4, runs: 1086, avgDur: '2.1s', tools: ['LLM 分类', '规则引擎'] },
  { name: '富化 Agent', role: '论文/POC/公告关联富化', icon: 'spark', state: '运行中', success: 93.1, runs: 954, avgDur: '21.7s', tools: ['向量检索', '论文搜索', 'POC 搜索', 'CVSS 解析'] },
  { name: '检索 Agent', role: '混合检索与重排', icon: 'search', state: '运行中', success: 98.7, runs: 2301, avgDur: '0.9s', tools: ['BM25', '向量检索', 'Reranker'] },
  { name: '问答 Agent', role: '多跳推理与答案合成', icon: 'chat', state: '运行中', success: 95.8, runs: 640, avgDur: '4.6s', tools: ['LLM 网关', '引用校验'] },
  { name: '质量校验 Agent', role: '富化准确性与冲突复核', icon: 'check', state: '运行中', success: 97.5, runs: 886, avgDur: '5.3s', tools: ['规则校验', 'LLM 复核'] },
  { name: '告警 Agent', role: '高危情报实时推送', icon: 'bell', state: '待机', success: 100, runs: 96, avgDur: '0.4s', tools: ['Webhook', '邮件'] },
];

export const MOCK_ORCH = [
  { id: 'monitor', name: '监测 Agent', sub: '发现新 CVE · 8.4s', x: 20, y: 40, state: 'done' },
  { id: 'classify', name: '分类 Agent', sub: '判定 AI 相关 · 2.1s', x: 190, y: 40, state: 'done' },
  { id: 'enrich', name: '富化 Agent', sub: '论文/POC/CVSS · 21.7s', x: 360, y: 40, state: 'running' },
  { id: 'verify', name: '校验 Agent', sub: '质量复核 · 5.3s', x: 530, y: 40, state: 'idle' },
  { id: 'store', name: '入库索引', sub: '写库 + 向量索引', x: 700, y: 40, state: 'idle' },
  { id: 'qa', name: '问答 Agent', sub: '情报可检索', x: 700, y: 160, state: 'idle' },
];
export const MOCK_ORCH_EDGES = [
  ['monitor', 'classify'], ['classify', 'enrich'], ['enrich', 'verify'], ['verify', 'store'], ['store', 'qa'],
];

export const MOCK_TOOL_LOGS = [
  { time: '08:42:31', tool: 'nvd.api.search', io: 'pubDate≥08:36Z → 14 条 CVE 记录', dur: '1.9s', ok: true },
  { time: '08:42:12', tool: 'vector.search', io: 'query="vLLM RCE" top_k=8 → 命中 3 篇论文', dur: '0.4s', ok: true },
  { time: '08:41:58', tool: 'poc.search', io: 'CVE-2025-46408 → GitHub 1 个候选 POC', dur: '2.7s', ok: true },
  { time: '08:41:52', tool: 'cvss.parse', io: 'CVSS:3.1/AV:N/AC:L/… → 9.8 Critical', dur: '0.1s', ok: true },
  { time: '08:41:40', tool: 'rss.parse', io: 'vendor-rss 24 项 → 9 条有效公告', dur: '1.2s', ok: true },
  { time: '08:41:20', tool: 'llm.classify', io: '标题+摘要 → AI 基础设施（置信 0.94）', dur: '1.6s', ok: true },
  { time: '08:40:55', tool: 'paper.search', io: 'arXiv "PagedAttention attack" → 相关度 0.93', dur: '3.1s', ok: true },
  { time: '08:40:12', tool: 'vector.search', io: 'query="prompt injection defense" → 0 命中', dur: '0.3s', ok: false },
];

export const MOCK_DECISIONS = [
  { text: '该漏洞涉及 vLLM 推理框架核心调度器，判定为「AI 基础设施风险」，置信度 0.94', agent: '分类 Agent', time: '08:41:20' },
  { text: '检索到 3 篇相关论文，相关性均 > 0.8，纳入富化结果并标记引用来源', agent: '富化 Agent', time: '08:42:10' },
  { text: 'POC 来源为个人仓库（star<50），可信度偏低，标记「待人工复核」而非直接采信', agent: '质量校验 Agent', time: '08:42:38' },
  { text: '受影响版本范围与厂商公告存在冲突（>=0.4.0 vs >=0.3.9），保留双断言并生成复核任务', agent: '质量校验 Agent', time: '08:42:41' },
  { text: 'CVSS 9.8 且属 KEV 目录同类利用面，触发高危告警推送', agent: '告警 Agent', time: '08:43:02' },
];

export const MOCK_HEALING = [
  { err: '安全社区源 HTTP 429 限流', act: '指数退避自动重试（1m/5m/15m）', ok: '第 2 次重试成功，已恢复采集', time: '07:12 → 07:30' },
  { err: '富化 Agent 调用 POC 搜索超时', act: '降级为仅论文+公告富化，标记维度缺失', ok: '任务完成，缺失维度进入补跑队列', time: '06:58 → 07:01' },
  { err: '质量校验不通过（版本范围冲突）', act: '自动回退富化结果，生成人工复核单', ok: '复核单 #RV-1024 已创建', time: '05:44' },
];

/* ---------- 知识底座演示数据 ---------- */
export const MOCK_PAPERS = [
  { id: 'P-2309.06180', title: 'Efficient Memory Management for LLM Serving with PagedAttention', authors: 'Kwon et al.', org: 'UC Berkeley', date: '2023-09', abs: '提出 PagedAttention 注意力内存管理算法，是 vLLM 核心；本文分析其调度面的安全边界。', linked: ['CVE-2025-46408'], tags: ['推理框架', '内存管理'] },
  { id: 'P-2402.05196', title: 'Prompt Injection Attacks and Defenses in LLM-Integrated Applications', authors: 'Liu et al.', org: 'arXiv', date: '2024-02', abs: '系统化梳理提示词注入攻击面与防御框架，覆盖 36 种攻击变体。', linked: ['CVE-2025-46321'], tags: ['提示词注入', '防御'] },
  { id: 'P-2510.11223', title: 'Supply Chain Risks in Open-Weight Model Distribution', authors: 'Zhang et al.', org: 'USENIX', date: '2026-08', abs: '分析开源权重模型分发链中的篡改与后门植入风险，提出签名验证方案。', linked: ['CVE-2025-46087'], tags: ['供应链', '模型分发'] },
  { id: 'P-2510.09871', title: 'Agentic RAG 系统的越权访问模式研究', authors: 'Chen et al.', org: 'NDSS', date: '2026-09', abs: '研究智能体 RAG 架构下的工具越权调用模式，给出最小权限设计准则。', linked: ['CVE-2025-45964'], tags: ['智能体', 'RAG'] },
  { id: 'P-2510.07632', title: 'Adversarial Robustness Evaluation of Safety Alignment', authors: 'Wang et al.', org: 'ICLR', date: '2026-06', abs: '对主流安全对齐方法进行对抗鲁棒性评测，发现系统性绕过模式。', linked: [], tags: ['对齐安全', '评测'] },
];

export const MOCK_STANDARDS = [
  { id: 'STD-014', name: '生成式人工智能服务安全基本要求', org: 'TC260', date: '2024-03', scope: '生成式 AI 服务上线安全评估', linked: 'AI 应用与智能体' },
  { id: 'STD-021', name: 'AI 安全治理框架 1.0', org: '全国网安标委', date: '2024-09', scope: 'AI 全生命周期风险治理', linked: '模型与数据层' },
  { id: 'STD-032', name: 'NIST AI RMF 1.0', org: 'NIST', date: '2023-01', scope: 'AI 风险管理（治理/映射/测量/管理）', linked: '治理框架' },
  { id: 'STD-047', name: 'ISO/IEC 42001 人工智能管理体系', org: 'ISO/IEC', date: '2023-12', scope: '组织级 AI 管理体系认证', linked: '治理框架' },
  { id: 'STD-055', name: '人工智能生成合成内容标识办法', org: '网信办等四部门', date: '2025-03', scope: 'AI 合成内容标识与溯源', linked: '合规要求' },
  { id: 'STD-061', name: 'OWASP LLM Top 10 (2025)', org: 'OWASP', date: '2025-01', scope: '大模型应用十大风险清单', linked: 'AI 应用与智能体' },
];

export const KB_STATS = { docs: 2847, chunks: 46_213, papers: 612, standards: 89, updateFreq: '6 小时' };

/* ---------- 系统运维演示数据 ---------- */
export const MOCK_SERVICES = [
  { name: '采集服务', sub: 'collector-01 · docker', state: 'on', note: 'UP 36d · 8 源在线' },
  { name: '富化服务', sub: 'enricher-01 · docker', state: 'on', note: '队列深度 12' },
  { name: '问答服务', sub: 'qa-01 · docker', state: 'on', note: 'P95 1.8s' },
  { name: '向量库', sub: 'qdrant · 6 collections', state: 'on', note: '46k 片段' },
  { name: '关系数据库', sub: 'postgres-16', state: 'on', note: '连接 23/100' },
  { name: 'LLM 网关', sub: 'model-gateway', state: 'warn', note: '1 个上游降级' },
];

export const MOCK_ALERTS = [
  { level: 'warning', time: '10-18 08:12', text: 'LLM 网关上游 deepseek-chat 超时率 4.2%，已自动切换备用模型' },
  { level: 'critical', time: '10-18 07:12', text: '安全社区源连续 2 次采集失败（HTTP 429），退避重试后恢复' },
  { level: 'info', time: '10-18 05:00', text: 'arXiv 采集窗口命中率 28%，低于 7 日均值 35%' },
  { level: 'info', time: '10-17 22:40', text: '向量库完成例行快照（46,213 片段，耗时 42s）' },
];

export const MOCK_DEPLOYS = [
  { ver: 'v0.14.2', time: '2026-10-17 21:00', note: '富化准确率反馈闭环上线', by: 'ci-bot' },
  { ver: 'v0.14.1', time: '2026-10-15 18:30', note: '新增标准政策源采集器', by: 'ci-bot' },
  { ver: 'v0.14.0', time: '2026-10-12 10:12', note: 'Agent 编排引擎重构（任务图调度）', by: 'wang.zhang' },
];

export const MOCK_LOGS = [
  { t: '08:42:38', lv: 'ok', msg: '[verify-agent] CVE-2025-46408 富化校验通过（8/8 维度）' },
  { t: '08:42:12', lv: 'info', msg: '[enrich-agent] vector.search 命中 3 篇论文，rel>0.8' },
  { t: '08:41:47', lv: 'info', msg: '[classify-agent] CVE-2025-46408 → AI基础设施（conf 0.94）' },
  { t: '08:41:22', lv: 'ok', msg: '[collector] nvd-api 增量 14 条，游标推进 08:36Z' },
  { t: '08:12:03', lv: 'warn', msg: '[llm-gateway] deepseek-chat 超时率 4.2% > 阈值 3%，切换 qwen-plus' },
  { t: '07:30:11', lv: 'ok', msg: '[collector] sec-community 重试成功（第 2 次，退避 5m）' },
  { t: '07:12:55', lv: 'err', msg: '[collector] sec-community HTTP 429，进入指数退避' },
  { t: '06:58:40', lv: 'warn', msg: '[enrich-agent] poc.search 超时（30s），维度降级标记' },
];

export const OPS_METRICS = {
  collectLatencyP50: '2.8h', collectLatencyP95: '6.1h',
  enrichPrecision: '93.1%', enrichRecall: '88.4%',
  qaAccuracy: '91.7%', qaP95: '1.8s',
  agentSuccess: '96.8%', uptime: '99.95%',
};

export const QA_EVAL = { accuracy: 91.7, multiHop: 86.2, avgResp: '3.4s', cases: 120 };

export function mockFeedToVuln(f) {
  return {
    canonical_id: f.cve, title: f.title, primary_severity: f.severity,
    published_at: f.published, modified_at: f.collected, status: f.enrich,
  };
}
