"use strict";
const $ = id => document.getElementById(id);
const state = {step:0,questions:[],answers:{}};
const roleLabel = {workflow:"完整创作工具",extension:"现有软件扩展",component:"本地推理组件",utility:"配套工具"};
const localLabel = {documented_option:"文档提供本地模式（未审计）",requires_local_host:"可连接本地服务（取决于配置）",unknown:"本地能力尚未确认"};
function node(tag,cls,text){
  const e=document.createElement(tag);if(cls)e.className=cls;
  if(text!==undefined)e.textContent=text;
  return e;
}
async function get(path){
  const res=await fetch(path,{credentials:"same-origin",cache:"no-store"});
  const data=await res.json();
  if(!res.ok)throw Error(data.error||"目录读取失败");
  return data;
}
function renderQuestion(){
  const q=state.questions[state.step];
  $("progress-label").textContent="选择 "+(state.step+1)+" / "+state.questions.length;
  $("progress-fill").style.width=String((state.step+1)*100/state.questions.length)+"%";
  $("question-title").textContent=q.title;
  const host=$("answers");host.replaceChildren();
  for(const option of q.options){
    const btn=node("button","choice",option.label);
    btn.type="button";btn.setAttribute("aria-pressed",String(state.answers[q.id]===option.id));
    btn.addEventListener("click",()=>{state.answers[q.id]=option.id;renderQuestion();});
    host.append(btn);
  }
  $("prev").disabled=state.step===0;
  $("next").disabled=!state.answers[q.id];
  $("next").textContent=state.step===state.questions.length-1?"查看候选工具":"下一步";
}
function card(info){
  const box=node("article","card");
  const title=node("h3");
  const link=node("a","",info.name);link.href=info.url;link.target="_blank";link.rel="noopener noreferrer";
  title.append(link);box.append(title);
  box.append(node("span","chip",roleLabel[info.role]||"工具"));
  box.append(node("span","chip",localLabel[info.local_mode]||"能力未知"));
  box.append(node("p","",info.summary));box.append(node("p","",info.note));
  if(info.frictions&&info.frictions.length){
    const ul=node("ul");
    for(const f of info.frictions){
      const status=f.mitigation_status==="documented"?"已有文档方案":"尚需验证";
      const li=node("li","",f.title+"（"+status+"）");
      const a=node("a",""," 查看来源");a.href=f.source;a.target="_blank";a.rel="noopener noreferrer";
      li.append(a);ul.append(li);
    }
    box.append(ul);
  }
  box.append(node("small","","实际质量：未测试 · 显卡适配：未测试 · 隐私：未审计"));
  const docs=node("a","source","查看上游文档与安装说明");
  docs.href=info.documentation_url;docs.target="_blank";docs.rel="noopener noreferrer";
  box.append(docs);return box;
}
async function showResults(){
  $("status").textContent="正在读取本地目录…";
  const params=new URLSearchParams(state.answers);
  try{
    const result=await get("/api/chooser/match?"+params.toString());
    $("status").textContent="";
    $("results").hidden=false;
    $("results").scrollIntoView({behavior:"smooth",block:"start"});
    const warnings=$("warnings");warnings.replaceChildren();
    for(const message of result.warnings)warnings.append(node("div","warning","• "+message));
    const host=$("candidates");host.replaceChildren();
    if(!result.candidates.length){
      host.append(node("p","","暂无符合当前严格本地要求的文档候选；不会把未知项强行推荐给你。"));
    }
    for(const item of result.candidates)host.append(card(item));
    $("unknown-wrap").hidden=!result.unconfirmed_local.length;
    const extra=$("unknown");extra.replaceChildren();
    for(const item of result.unconfirmed_local)extra.append(card(item));
  }catch(err){$("status").textContent=err.message;}
}
async function main(){
  const data=await get("/api/chooser/options");
  state.questions=data.questions;renderQuestion();
  $("prev").addEventListener("click",()=>{state.step=Math.max(0,state.step-1);renderQuestion();});
  $("next").addEventListener("click",()=>{
    if(!state.answers[state.questions[state.step].id])return;
    if(state.step===state.questions.length-1)void showResults();
    else{state.step++;renderQuestion();}
  });
  $("restart").addEventListener("click",()=>{
    state.answers={};state.step=0;$("results").hidden=true;renderQuestion();
    $("question-title").scrollIntoView({behavior:"smooth",block:"start"});
  });
}
main().catch(err=>$("status").textContent="目录暂时不可用："+err.message);
