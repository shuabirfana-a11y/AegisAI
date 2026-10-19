const make=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
const jsonText=v=>JSON.stringify(v,null,2);
const shown=v=>v===null||v===undefined?'未提供':String(v);
const stamp=value=>new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',dateStyle:'medium',timeStyle:'medium',hour12:false}).format(new Date(value));
const safeLink=url=>{try{const u=new URL(url);return ['https:','http:'].includes(u.protocol)?u.href:null;}catch{return null;}};
function details(parent,title,value){const d=make('details');d.append(make('summary',title),make('pre',jsonText(value)));parent.append(d);}
function table(parent,heads,rows){const box=make('div',undefined,'table-wrap'),t=make('table'),head=make('thead'),tr=make('tr');heads.forEach(s=>tr.append(make('th',s)));head.append(tr);t.append(head);const b=make('tbody');rows.forEach(cells=>{const row=make('tr');cells.forEach(v=>{const c=make('td');if(v instanceof Node)c.append(v);else c.textContent=shown(v);row.append(c);});b.append(row);});t.append(b);box.append(t);parent.append(box);}
async function renderCase(section){
  const target=section.querySelector('.case-content');
  try{
    const r=await fetch(`data/${section.dataset.case}.json`,{cache:'no-store'});if(!r.ok)throw Error(`HTTP ${r.status}`);
    const data=await r.json(),a=data.answer;target.replaceChildren();
    const meta=make('div',undefined,'record-meta');meta.append(make('span',`原运行时间：${stamp(data.started_at_utc)}（北京时间）`),make('span',`调查 ID：${data.investigation_id}`));target.append(meta);
    const facts=make('div',undefined,'facts');
    const fixes=[...new Set(a.recommended_actions.map(x=>x.fixed_version).filter(Boolean))];
    const risk=a.risk_assessment;
    const values=[['目标组件',`${data.request.asset_scope.component.name} ${data.request.asset_scope.component.version}`],['历史答案状态',a.answer_status],['历史 Gate 状态',a.integration_status],['该资产修复建议',fixes.join(' / ')||'未给出确定版本'],['补丁是否已落地',risk.patch_applied],['规划重试记录',`retry_count = ${data.planner.retry_count}`]];
    values.forEach(([label,value])=>{const f=make('div',undefined,'fact');f.append(make('b',label),make('span',shown(value)));facts.append(f);});target.append(facts);
    target.append(make('h3','核验后的版本事实'));
    const claims=a.verified_claims.filter(c=>['AFFECTS_VERSION','FIXED_VERSION'].includes(c.claim_type));
    table(target,['事实类型','结构化要点（完整字段见下载记录）','核验状态'],claims.map(c=>{const value={...c.value};delete value.impact_scope;if(Array.isArray(value.ranges))value.ranges=value.ranges.map(r=>{const concise={...r};delete concise.raw_expression;return concise;});const n=make('div',jsonText(value),'claim-value');return[c.claim_type,n,c.verification_status];}));
    target.append(make('h3','保留的警告与不确定性'));
    const warnings=make('ul',undefined,'warning-list');
    for(const w of [...new Set([...(a.warnings||[]),...(data.integration.warnings||[])].map(x=>typeof x==='string'?x:JSON.stringify(x)))])warnings.append(make('li',w));
    warnings.append(make('li',`实际利用状态：${shown(risk.exploitation_status)}；补丁应用状态：${shown(risk.patch_applied)}。`));target.append(warnings);
    details(target,'原始问题、目标组件与选项',data.request);
    details(target,'规划状态与真实阶段事件',{planner:data.planner,events:data.events});
    const sourceDetails=make('details');sourceDetails.append(make('summary',`查看 ${a.citations.length} 条原始证据定位`));
    table(sourceDetails,['证据与事实关联','来源与定位'],a.citations.map(c=>{const refs=make('div');const url=safeLink(c.reference?.url);if(url){const l=make('a',url);l.href=url;l.target='_blank';l.rel='noopener';refs.append(l);}refs.append(make('small',jsonText(c.reference?.locator||{})));const ids=make('div',c.evidence_id);ids.append(make('small',`Claim：${c.claim_id}`));return[ids,refs];}));target.append(sourceDetails);
    details(target,'历史风险输出与对应 Gate 检查',{risk_assessment:risk,integration:data.integration});
  }catch(e){target.replaceChildren(make('p',`记录读取失败：${e.message}。可使用下方链接直接下载原记录。`));}
}
document.querySelectorAll('[data-case]').forEach(renderCase);
fetch('data/manifest.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error(r.status);return r.json();}).then(d=>{document.querySelector('#manifest').textContent=jsonText(d);}).catch(()=>{document.querySelector('#manifest').textContent='发布清单暂时未能载入，请直接下载清单文件。';});
