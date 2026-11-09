"use strict";
const $ = id => document.getElementById(id);
const facetTitles = {modality:"内容形式",task:"创作任务",deployment:"运行方式",type:"工具类别",evidence:"证据程度",capability:"具体能力（有来源）"};
const typeTitles = {model:"模型",tool:"工具",service:"在线服务",runtime:"推理后端",extension:"扩展",workflow:"工作流",component:"组件",utility:"辅助工具"};
const modalityTitles = {text:"文字",image:"图像",video:"视频",audio:"语音"};
const state = {rows:[],facets:{},selected:{},visible:30,sources:[]};
function n(tag,cls,value){const x=document.createElement(tag);if(cls)x.className=cls;if(value!==undefined)x.textContent=value;return x;}
async function load(){
  const response=await fetch("/api/catalog",{credentials:"same-origin",cache:"no-store"});
  if(!response.ok)throw Error("目录暂不可用（HTTP "+response.status+"）");
  const data=await response.json();if(!Array.isArray(data.items)||!data.facets)throw Error("目录数据格式有误");
  state.rows=data.items;state.facets=data.facets;state.sources=data.sources||[];
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
function main(){
  $("more").addEventListener("click",()=>{state.visible+=30;renderResults();});
  $("clear").addEventListener("click",()=>{
    for(const selected of Object.values(state.selected))selected.clear();
    for(const btn of document.querySelectorAll(".tag[aria-pressed]"))btn.setAttribute("aria-pressed","false");
    state.visible=30;renderResults();
  });
  return load().then(()=>{
    renderFilters();renderResults();renderSources();
    $("status").textContent="目录内容来自本地快照；切换标签不会联网查询第三方或运行模型。";
  });
}
main().catch(err=>{$("status").textContent="无法加载目录："+err.message;});
