/* Entire dataset is fictional UI material. It is not intelligence, an asset inventory, or a benchmark. */
window.AEGIS_MOCK = {
  schema_version:'aegis-ui-mock/1.0', is_mock:true, as_of:'2026-10-03T09:30:00+08:00',
  vulnerabilities:[
    {id:'CVE-XXXX-A001',title:'推理服务请求边界校验不足',product:'vLLM',package:'vllm',ecosystem:'PyPI',range:'>= 0.8.0, < 0.8.4',fixed:'0.8.4',severity:'critical',cvss:9.1,cvss_version:'3.1',poc:'related',usability:'not_verified',kev:'listed',patch:'candidate',verification:'conflict',published:'2026-10-01',modified:'2026-10-03',description:'特定配置下，请求参数缺少边界检查，可能影响服务进程。此条目、范围及评分仅用于UI布局演示，均为虚构。',claim:'CL-MOCK-A001',source:'VENDOR_VLLM',is_mock:true},
    {id:'CVE-XXXX-A002',title:'模型反序列化路径检查不完整',product:'PyTorch',package:'torch',ecosystem:'PyPI',range:'>= 2.5.0, < 2.5.2',fixed:'2.5.2',severity:'high',cvss:8.4,cvss_version:'3.1',poc:'related',usability:'not_verified',kev:'not_listed_as_of',patch:'related',verification:'confirmed',published:'2026-10-01',modified:'2026-10-02',claim:'CL-MOCK-A002',source:'VENDOR_PYTORCH',is_mock:true},
    {id:'CVE-XXXX-A003',title:'模型工件访问权限校验缺口',product:'MLflow',package:'mlflow',ecosystem:'PyPI',range:'>= 2.10.0, < 2.10.3',fixed:null,severity:'high',cvss:7.8,cvss_version:'3.1',poc:'candidate',usability:'not_verified',kev:'unknown',patch:'not_fetched',verification:'insufficient',published:'2026-09-30',modified:'2026-10-02',claim:'CL-MOCK-A003',source:'VENDOR_MLFLOW',is_mock:true},
    {id:'CVE-XXXX-A004',title:'上传文件名称处理不完整',product:'Gradio',package:'gradio',ecosystem:'PyPI',range:'>= 4.0.0, < 4.2.1',fixed:'4.2.1',severity:'medium',cvss:6.2,cvss_version:'3.1',poc:'not_found',usability:'unknown',kev:'not_listed_as_of',patch:'not_found',verification:'pending',published:'2026-09-29',modified:'2026-10-01',claim:'CL-MOCK-A004',source:'OSV',is_mock:true},
    {id:'CVE-XXXX-A005',title:'组件配置读取缺少范围限制',product:'Transformers',package:'transformers',ecosystem:'PyPI',range:'< 4.40.2',fixed:'4.40.2',severity:'medium',cvss:5.9,cvss_version:'3.1',poc:'related',usability:'not_verified',kev:'not_listed_as_of',patch:'candidate',verification:'confirmed',published:'2026-09-28',modified:'2026-09-30',claim:'CL-MOCK-A005',source:'CVE_LIST',is_mock:true},
    {id:'CVE-XXXX-A006',title:'任务元数据暴露范围待确认',product:'Ray',package:'ray',ecosystem:'PyPI',range:null,fixed:null,severity:'low',cvss:3.7,cvss_version:'3.1',poc:'not_fetched',usability:'unknown',kev:'unknown',patch:'not_fetched',verification:'insufficient',published:'2026-09-28',modified:'2026-09-29',claim:'CL-MOCK-A006',source:'OSV',is_mock:true},
    {id:'CVE-XXXX-A007',title:'输入资源限制绕过候选',product:'vLLM',package:'vllm',ecosystem:'PyPI',range:'< 0.8.1',fixed:'0.8.1',severity:'medium',cvss:6.5,cvss_version:'3.1',poc:'candidate',usability:'not_verified',kev:'unknown',patch:'not_found',verification:'pending',published:'2026-09-27',modified:'2026-09-28',claim:'CL-MOCK-A007',source:'CVE_LIST',is_mock:true},
    {id:'CVE-XXXX-A008',title:'示例插件加载路径需补证',product:'MLflow',package:'mlflow',ecosystem:'PyPI',range:null,fixed:null,severity:'medium',cvss:5.4,cvss_version:'3.1',poc:'not_found',usability:'unknown',kev:'not_listed_as_of',patch:'not_fetched',verification:'pending',published:'2026-09-26',modified:'2026-09-27',claim:'CL-MOCK-A008',source:'OSV',is_mock:true}
  ],
  knowledge:[
    {id:'PAPER-MOCK-01',type:'paper',title:'推理服务安全边界研究（模拟论文）',publisher:'示例研究团队',version:'v2',status:'预印本',published:'2026-10-02',source:'ARXIV',is_mock:true},
    {id:'STD-MOCK-01',type:'standard',title:'AI安全组件核验规范（模拟标准）',publisher:'示例标准发布机构',version:'示例版次',status:'正式文本示例',published:'2026-10-01',source:'SAMR_AI_STANDARD',is_mock:true},
    {id:'POLICY-MOCK-01',type:'policy',title:'AI服务安全管理要求（模拟政策）',publisher:'示例发布机关',version:'示例版次',status:'生效状态未提供',published:'2026-09-30',source:'CAC_POLICY',is_mock:true},
    {id:'EVENT-MOCK-01',type:'event',title:'模型供应链信任边界分析（模拟文章）',publisher:'示例研究团队',version:'初版',status:'研究分析',published:'2026-09-29',source:'TOB_BLOG',is_mock:true}
  ],
  assets:[
    {id:'ASSET-MOCK-01',name:'推理服务 · 演示组件',package:'vllm',product:'vLLM',ecosystem:'PyPI',version:'0.8.2',impact:'affected',vulns:['CVE-XXXX-A001'],is_mock:true},
    {id:'ASSET-MOCK-02',name:'训练作业 · 演示组件',package:'torch',product:'PyTorch',ecosystem:'PyPI',version:'2.5.0',impact:'affected',vulns:['CVE-XXXX-A002'],is_mock:true},
    {id:'ASSET-MOCK-04',name:'已升级 · 演示组件',package:'torch',product:'PyTorch',ecosystem:'PyPI',version:'2.5.2',impact:'not_affected',vulns:['CVE-XXXX-A002'],is_mock:true},
    {id:'ASSET-MOCK-03',name:'实验跟踪 · 待补版本',package:'mlflow',product:'MLflow',ecosystem:'PyPI',version:null,impact:'unknown',vulns:['CVE-XXXX-A003'],is_mock:true}
  ],
  sources:[
    {id:'CVE_LIST',name:'CVE List',category:'漏洞目录',status:'success',last_success:'09:12',count:8,latency:'样本不足',is_mock:true},
    {id:'OSV',name:'OSV',category:'漏洞目录',status:'success',last_success:'09:10',count:6,latency:'样本不足',is_mock:true},
    {id:'CISA_KEV',name:'CISA KEV',category:'漏洞目录',status:'success',last_success:'08:30',count:1,latency:'不适用',is_mock:true},
    {id:'VENDOR_VLLM',name:'vLLM公告',category:'厂商公告',status:'partial',last_success:'08:15',count:2,latency:'样本不足',is_mock:true},
    {id:'GITHUB_CODE',name:'GitHub引用',category:'代码引用',status:'failed',last_success:'昨日 21:00',count:null,latency:'未知',is_mock:true},
    {id:'ARXIV',name:'arXiv',category:'论文',status:'success',last_success:'09:00',count:1,latency:'样本不足',is_mock:true},
    {id:'SAMR_AI_STANDARD',name:'标准元数据',category:'技术标准',status:'planned',last_success:null,count:null,latency:'未知',is_mock:true}
  ],
  runs:[
    {id:'RUN-MOCK-01',source:'GitHub引用',source_id:'GITHUB_CODE',time:'09:20',status:'failed',fetched:null,updated:null,error:'模拟速率限制：本次引用更新未完成',is_mock:true},
    {id:'RUN-MOCK-02',source:'vLLM公告',source_id:'VENDOR_VLLM',time:'09:15',status:'partial',fetched:2,updated:1,error:'模拟单条公告解析缺少范围',is_mock:true},
    {id:'RUN-MOCK-03',source:'CVE List',source_id:'CVE_LIST',time:'09:12',status:'success',fetched:8,updated:2,error:null,is_mock:true}
  ],
  reviews:[
    {id:'REVIEW-MOCK-01',vuln:'CVE-XXXX-A001',kind:'版本范围冲突',reason:'同生态/包/分支下，两条示例范围不一致',status:'open',is_mock:true},
    {id:'REVIEW-MOCK-02',vuln:'CVE-XXXX-A003',kind:'修复版本证据不足',reason:'模拟公告未提供明确fixed',status:'open',is_mock:true}
  ],
  trend:[2,4,3,5,4,6,8],
  tool_trace:[
    {tool:'查询结构化情报',scope:'PyPI · 原published最近90天',count:8},
    {tool:'匹配演示组件',scope:'4个模拟组件 · 清单示例版本',count:2},
    {tool:'检查PoC关联',scope:'related与可用性分开',count:2},
    {tool:'检查KEV目录',scope:'模拟完整目录快照',count:1},
    {tool:'回查Evidence',scope:'范围/评分/关联原文',count:4}
  ]
};
