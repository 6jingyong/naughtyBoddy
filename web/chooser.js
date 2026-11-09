"use strict";
const $ = id => document.getElementById(id);
const facetTitles = {modality:"内容形式",task:"创作任务",deployment:"运行方式",type:"工具类别",evidence:"证据程度",capability:"具体能力（有来源）",link_health:"链接核查",integration:"连接方式（有来源）"};
const typeTitles = {model:"模型",tool:"工具",service:"在线服务",runtime:"推理后端",extension:"扩展",workflow:"工作流",component:"组件",utility:"辅助工具"};
const modalityTitles = {text:"文字",image:"图像",video:"视频",audio:"语音"};
const state = {rows:[],facets:{},selected:{},visible:30,sources:[],health:null,identity:null};
function n(tag,cls,value){const x=document.createElement(tag);if(cls)x.className=cls;if(value!==undefined)x.textContent=value;return x;}
async function load(){
  const response=await fetch("/api/catalog/text",{credentials:"same-origin",cache:"no-store"});
  if(!response.ok)throw Error("目录暂不可用（HTTP "+response.status+"）");
  const data=await response.json();if(!Array.isArray(data.items)||!data.facets)throw Error("目录数据格式有误");
  if(data.scope!=="text_first")throw Error("服务未返回文字专用目录");
  if(data.items.some(item=>item.modalities.length!==1 || item.modalities[0]!=="text"))throw Error("目录范围不一致");
  state.rows=data.items;state.facets=data.facets;state.sources=data.sources||[];
  state.health=data.health_summary||null;state.identity=data.identity_review||null;
  $("tool-count").textContent=String(data.items.length);
  $("source-count").textContent=String(state.sources.length);
}
function renderFilters(){
  const root=$("filters");root.replaceChildren();
  for(const [key,options] of Object.entries(state.facets)){
    state.selected[key]=new Set();
    const section=n("section","filter-section");
    section.append(n("div","filter-label",facetTitles[key]||key));
    const chips=n("div","tags");
    for(const option of options){
      const btn=n("button","tag",option.label);btn.type="button";btn.dataset.facet=key;btn.dataset.value=option.id;
      btn.setAttribute("aria-pressed","false");
      btn.addEventListener("click",()=>{
        const selected=state.selected[key];
        if(selected.has(option.id))selected.delete(option.id);else selected.add(option.id);
        btn.setAttribute("aria-pressed",String(selected.has(option.id)));
        state.visible=30;renderResults();
      });
      chips.append(btn);
    }
    section.append(chips);root.append(section);
  }
}
function selectedRows(){
  return state.rows.filter(item=>{
    for(const [facet,selected] of Object.entries(state.selected)){
      if(!selected.size)continue;
      let actual;
      if(facet==="modality")actual=item.modalities;
      else if(facet==="task")actual=item.tasks;
      else if(facet==="capability")actual=item.capabilities||[];
      else if(facet==="integration")actual=item.integration_tags||[];
      else actual=[item[facet]];
      if(!actual.some(value=>selected.has(value)))return false;
    }
    return true;
  });
}
function sourceLink(src){
  const a=n("a","","来源："+src.name);a.href=src.url;a.target="_blank";a.rel="noopener noreferrer";
  return a;
}
function createCard(item){
  const box=n("article","card");const heading=n("div","card-heading");const h3=n("h3");
  const a=n("a","",item.name);a.href=item.url;a.target="_blank";a.rel="noopener noreferrer";
  h3.append(a);heading.append(h3);
  const verified=item.evidence==="documentation_reviewed";
  heading.append(n("span","label"+(verified?"":" unverified"),verified?"文档已核查":"仅目录收录"));
  box.append(heading);
  const tags=n("div","chips");
  tags.append(n("span","chip",typeTitles[item.type]||item.type));
  for(const m of item.modalities)tags.append(n("span","chip",modalityTitles[m]||m));
  const dep={local:"目录称可本地运行",hosted:"目录标注在线",hybrid:"混合模式",unknown:"部署未知"}[item.deployment]||"部署未知";
  tags.append(n("span","chip",dep));box.append(tags);
  if(item.capability_evidence&&item.capability_evidence.length){
    const caps=n("div","chips evidence-preview");
    for(const detail of item.capability_evidence.slice(0,4))
      caps.append(n("span","chip evidence-chip",detail.label));
    if(item.capability_evidence.length>4)caps.append(n("span","chip","另有 "+(item.capability_evidence.length-4)+" 项能力"));
    box.append(caps);
    const evidence=n("details","capability-details");
    evidence.append(n("summary","","查看功能依据与适用条件（"+item.capability_evidence.length+"）"));
    const list=n("ul");
    for(const detail of item.capability_evidence){
      const li=n("li");
      const link=n("a","",detail.label+" · 官方来源");
      link.href=detail.source_url;link.target="_blank";link.rel="noopener noreferrer";
      li.append(link,n("span","cap-conditions"," — "+detail.conditions));
      list.append(li);
    }
    evidence.append(list);box.append(evidence);
  }
  if(item.connections&&item.connections.length){
    const details=n("details","compatibility-details");
    const direct=item.connections.filter(r=>r.evidence_status==="documented").length;
    const pending=item.connections.length-direct;
    details.append(n("summary","", "连接与依赖关系 · 文档 "+direct+" 条"+(pending?" / 待测 "+pending+" 条":"")));
    const list=n("div","compatibility-rows");
    const relLabels={
      client_backend:"应用 → 推理后端",extension_for:"扩展所属前端",
      needs_extension_for_isolation:"正确隔离所需扩展",runtime_format:"支持的模型文件格式",
      protocol_candidate:"可尝试的 API 协议候选"
    };
    for(const edge of item.connections){
      const row=n("article","compatibility-row");
      row.append(n("strong","",edge.other_name+" · "+(relLabels[edge.relation]||"关系")));
      row.append(n("span","compatibility-status"+(edge.evidence_status==="documented"?"":" proposed"),
        edge.evidence_status==="documented"?"上游文档支持；未实测":"仅协议推导；未验证"));
      if(edge.endpoint_hint&&edge.direction==="outgoing")
        row.append(n("code","",edge.endpoint_hint));
      row.append(n("p","",edge.limitations));
      if(edge.direction==="outgoing"&&edge.setup_steps.length){
        const steps=n("ol");
        for(const step of edge.setup_steps)steps.append(n("li","",step));
        row.append(steps);
      }
      const docs=n("div","sources-links");
      for(const url of edge.source_urls.slice(0,2)){
        const a=n("a","","查看连接依据");a.href=url;a.target="_blank";a.rel="noopener noreferrer";docs.append(a);
      }
      row.append(docs);list.append(row);
    }
    details.append(list);box.append(details);
  }
  const status=item.link_check||{state:"not_checked"};
  if(status.state==="repository_metadata_found"){
    const health=n("div","link-health checked","GitHub 仓库入口已核查 · "+status.checked_on);
    if(status.repo_archived)health.append(n("span","", " · 已归档"));
    box.append(health);
  }else if(status.state==="conflicting_evidence"){
    const health=n("div","link-health review","链接资料冲突 · 待人工复核");
    if(status.evidence_url){
      const proof=n("a",""," 查看 API 核查来源");
      proof.href=status.evidence_url;proof.target="_blank";proof.rel="noopener noreferrer";health.append(proof);
    }
    box.append(health);
  }else{
    box.append(n("div","link-health unchecked","当前链接状态尚未核查"));
  }
  box.append(n("p","",item.note));
  box.append(n("div","caveat","成人内容兼容：未测 · 模型质量：未测 · 隐私：未审计 · 显卡适配：未测"));
  const links=n("div","sources-links");
  const top=item.sources.slice(0,3);for(const s of top)links.append(sourceLink(s));
  if(item.sources.length>top.length)links.append(n("span","chip","另有 "+(item.sources.length-top.length)+" 个来源"));
  box.append(links);return box;
}
function renderResults(){
  const rows=selectedRows();$("result-count").textContent="("+rows.length+" 项)";
  $("empty").hidden=rows.length>0;
  const cards=$("cards");cards.replaceChildren();
  for(const item of rows.slice(0,state.visible))cards.append(createCard(item));
  $("more").hidden=rows.length<=state.visible;
  $("more").textContent="继续查看（已显示 "+Math.min(rows.length,state.visible)+" / "+rows.length+"）";
}
function renderSources(){
  const root=$("source-list");root.replaceChildren();
  for(const src of state.sources){
    const card=n("article","source-entry");
    const a=n("a","",src.name);a.href=src.url;a.target="_blank";a.rel="noopener noreferrer";
    card.append(a);card.append(n("small","",src.count+" 个来源条目 · "+src.license+" · README 版本："+src.commit.slice(0,9)));
    if(src.disclosure==="source_discloses_operator_interest")card.append(n("small","","来源声明其维护者具有商业利益关系"));
    root.append(card);
  }
}
function renderMaintenance(){
  const c=state.health?.counts;
  if(c){
    $("health-count").textContent="仓库已核查 "+(c.repository_metadata_found||0)+
      " · 状态待复核 "+(c.conflicting_evidence||0)+
      " · 未检查 "+(c.not_checked||0);
  }
  const list=$("identity-list");list.replaceChildren();
  const duplicates=state.identity?.shared_destinations||[];
  $("duplicate-count").textContent="共用链接的候选组："+duplicates.length+"；不自动合并不同模型变体。";
  for(const group of duplicates.slice(0,12)){
    const box=n("div","identity-entry");
    box.append(n("strong","",group.items.map(x=>x.name).join(" / ")));
    box.append(n("small","",group.destination_key));
    list.append(box);
  }
  const changes=$("migration-list");changes.replaceChildren();
  for(const move of state.health?.migrations||[]){
    const box=n("div","identity-entry");
    box.append(n("strong","","已核实地址迁移"));
    const a=n("a","",move.former_url+" → "+move.canonical_url);
    a.href=move.canonical_url;a.target="_blank";a.rel="noopener noreferrer";box.append(a);
    changes.append(box);
  }
}
function main(){
  $("more").addEventListener("click",()=>{state.visible+=30;renderResults();});
  $("clear").addEventListener("click",()=>{
    for(const selected of Object.values(state.selected))selected.clear();
    for(const btn of document.querySelectorAll(".tag[aria-pressed]"))btn.setAttribute("aria-pressed","false");
    state.visible=30;renderResults();
  });
  return load().then(()=>{
    renderFilters();renderResults();renderSources();renderMaintenance();
    $("status").textContent="目录内容来自本地快照；切换标签不会联网查询第三方或运行模型。";
  });
}
main().catch(err=>{$("status").textContent="无法加载目录："+err.message;});
