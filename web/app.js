"use strict";
const $ = (id) => document.getElementById(id);
const state = { token: "", selected: null, chapters: [], chapter: 1, offset: 0, job: null };
const perPage = 80;

async function api(path, method="GET", body=null) {
  const headers = { "Accept": "application/json" };
  if (method !== "GET") { headers["Content-Type"] = "application/json"; headers["X-NB-Token"] = state.token; }
  const r = await fetch(path, {method, headers, body: body === null ? undefined : JSON.stringify(body), cache:"no-store"});
  let data; try { data = await r.json(); } catch { throw new Error("服务器返回了非 JSON 数据"); }
  if (!r.ok) throw new Error(data.error || `HTTP ${r.status}`);
  return data;
}
function notify(message) { const el=$('toast'); el.textContent=message; el.classList.remove('hidden'); clearTimeout(notify.timer); notify.timer=setTimeout(()=>el.classList.add('hidden'),3500); }
function showResult(value) { $('action-result').textContent=typeof value==='string'?value:JSON.stringify(value,null,2); }
function reportError(e) { showResult(`错误：${e.message}`); notify(e.message); }
function el(tag, cls='', text='') { const node=document.createElement(tag); if(cls)node.className=cls; node.textContent=text; return node; }
function toggle(id, on) { $(id).classList.toggle('hidden',!on); }
function fmt(n) { return Number(n||0).toLocaleString(); }

async function loadProjects() {
  const result=await api('/api/projects'); const list=$('project-list'); list.replaceChildren();
  $('project-count').textContent=result.projects.length;
  if (!result.projects.length) { list.append(el('p','hint','还没有作品。先导入一本 TXT 或 EPUB。')); return; }
  for(const p of result.projects) {
    const b=el('button',`project-btn${state.selected===p.id?' active':''}`);
    b.type='button'; b.append(el('span','name',p.title), el('span','meta',`${fmt(p.done)} / ${fmt(p.segments)} 已完成`));
    b.addEventListener('click',()=>openProject(p.id).catch(reportError)); list.append(b);
  }
}
async function openProject(id) {
  state.selected=id; state.offset=0;
  const data=await api(`/api/projects/${id}`); state.chapters=data.chapter_list;
  $('current-name').textContent=data.title; $('book-title').textContent=data.title;
  $('book-subtitle').textContent=`${fmt(data.chapters)} 章 · ${fmt(data.segments)} 个片段 · ${data.target_language}`;
  $('progress-text').textContent=`${fmt(data.done)} / ${fmt(data.segments)} · ${Math.floor((data.done/Math.max(1,data.segments))*100)}%`;
  $('progress-bar').style.width=`${(data.done/Math.max(1,data.segments))*100}%`;
  const ch=$('chapter-select'); ch.replaceChildren();
  for(const item of data.chapter_list){const opt=el('option','',`${item.chapter_no}. ${item.translated_title||item.title} (${item.done}/${item.total})`); opt.value=String(item.chapter_no); ch.append(opt);}
  if(!data.chapter_list.some(x=>x.chapter_no===state.chapter))state.chapter=data.chapter_list[0]?.chapter_no||1;
  ch.value=String(state.chapter);
  toggle('welcome', false);toggle('editor', true);toggle('import-card',false);
  await loadSegments(); await loadProjects();
}
async function loadSegments() {
  if(!state.selected)return;
  const data=await api(`/api/projects/${state.selected}/segments?chapter=${state.chapter}&offset=${state.offset}`);
  $('page-label').textContent=`${data.total?data.offset+1:0}–${data.offset+data.rows.length} / ${fmt(data.total)}`;
  $('prev-page').disabled=state.offset===0; $('next-page').disabled=!data.has_more;
  const host=$('segments'); host.replaceChildren();
  if(!data.rows.length) host.append(el('p','hint','此章节暂无片段。'));
  for(const item of data.rows){
    const row=el('article','segment-row');
    const left=el('div','source-cell'); const leftMeta=el('div','segment-meta');
    leftMeta.append(el('span','',item.paragraph_no===0?'章节标题':`段落 ${item.paragraph_no} · 片段 ${item.chunk_no}`));
    left.append(leftMeta,el('div','source-text',item.source));
    const right=el('div','target-cell'); const rightMeta=el('div','segment-meta');
    rightMeta.append(el('span','',item.simulated?'演示内容':item.target?'译文已保存':'等待翻译'),el('span','',item.provider||'—'));
    const input=el('textarea');input.setAttribute('aria-label',`译文 ${item.id}`);input.value=item.target||'';input.placeholder='可直接编辑译文，保存后会覆盖当前片段的机器翻译。';
    const actions=el('div','row-actions');const status=el('span','',item.flags?.join(' · ')||'手动修改后可保存');
    const save=el('button','btn subtle','保存修改');save.type='button';save.disabled=true;
    input.addEventListener('input',()=>save.disabled=input.value===(item.target||''));
    save.addEventListener('click',async()=>{
      try{save.disabled=true; const result=await api(`/api/projects/${state.selected}/segments/${item.id}`,'PATCH',{target:input.value});
      item.target=result.target; item.simulated=0; status.textContent='已保存 · 可在本地继续修改';notify('译文修改已保存');
      await refreshSummary();}catch(e){save.disabled=false;reportError(e);}
    });
    actions.append(status,save);right.append(rightMeta,input,actions);row.append(left,right);host.append(row);
  }
}
async function refreshSummary() {
  if(!state.selected) return;
  const data=await api(`/api/projects/${state.selected}`);state.chapters=data.chapter_list;
  $('progress-text').textContent=`${fmt(data.done)} / ${fmt(data.segments)} · ${Math.floor((data.done/Math.max(1,data.segments))*100)}%`;
  $('progress-bar').style.width=`${(data.done/Math.max(1,data.segments))*100}%`;
  for(const item of data.chapter_list){const opt=$('chapter-select').querySelector(`option[value="${item.chapter_no}"]`);if(opt)opt.textContent=`${item.chapter_no}. ${item.translated_title||item.title} (${item.done}/${item.total})`;}
  await loadProjects();
}

async function importBook(e) {
  e.preventDefault(); const file=$('book-file').files[0];if(!file)return;
  if(file.size>12*1024*1024)throw new Error('当前最大支持 12 MiB 文件');
  const submit=$('import-form').querySelector('button[type="submit"]');submit.disabled=true;submit.textContent='正在导入…';
  try{
    const bytes=new Uint8Array(await file.arrayBuffer()); const chunks=[];
    for(let i=0;i<bytes.length;i+=8192) chunks.push(String.fromCharCode(...bytes.subarray(i,i+8192)));
    const base64=btoa(chunks.join(''));
    const project=await api('/api/projects','POST',{filename:file.name,base64,target_language:$('target-language').value,rights_confirmed:$('rights-confirmed').checked});
    state.chapter=1;await openProject(project.id);notify(`作品导入成功：${project.title}`);
  }finally{submit.disabled=false;submit.innerHTML='创建项目 <span>↗</span>';}
}
function providerChanged(){
  const provider=$('provider').value;
  toggle('base-url-wrap',provider==='compatible');
  const remote=provider==='openrouter'||(provider==='compatible'&&!isLocal($('base-url').value));
  toggle('remote-wrap',remote);if(!remote)$('remote-accept').checked=false;
  if(provider==='mock')$('model-id').placeholder='演示模式不需要模型';
  else $('model-id').placeholder='填写或从上方模型候选中选择';
}
function isLocal(url){try{return ['localhost','127.0.0.1','::1'].includes(new URL(url).hostname);}catch{return false;}}
async function discover() {
  const source=$('model-source').value, query=$('model-query').value.trim(), list=$('model-results');
  list.replaceChildren(el('p','hint','正在查询模型元数据…'));
  try{
    const data=await api(`/api/models?source=${encodeURIComponent(source)}&query=${encodeURIComponent(query)}&limit=12`);
    list.replaceChildren();
    if(!data.models.length){list.append(el('p','hint','未找到匹配模型。请更换关键词或来源。'));return;}
    for(const model of data.models){
      const card=el('button','model-item');card.type='button';card.append(el('strong','',model.id||'未命名模型'));
      card.append(el('small','',model.local===true?'本地可用':`${model.source} · 兼容性未测`));
      card.addEventListener('click',()=>{
        $('provider').value=source==='ollama'?'ollama':source==='openrouter'?'openrouter':'compatible';
        $('model-id').value=model.id;providerChanged();
        if(source==='huggingface') notify('Hugging Face 只提供候选信息，需先下载并通过本地推理服务运行。');
        else notify('已填入模型 ID。请确认服务和调用条件。');
      });
      list.append(card);
    }
  }catch(e){list.replaceChildren(el('p','hint',e.message));reportError(e);}
}
async function translate() {
  if(!state.selected)throw new Error('请先导入或选择作品');
  const provider=$('provider').value;
  const btn=$('translate');btn.disabled=true;
  try{
    const result=await api(`/api/projects/${state.selected}/translate`,'POST',{
      provider,model:$('model-id').value.trim(),base_url:$('base-url').value.trim(),
      max_segments:Number($('batch-size').value),accept_remote:$('remote-accept').checked});
    state.job=result.job_id;showResult(result);$('job-state').textContent='◉ 翻译批次执行中';pollJob();
  }catch(e){btn.disabled=false;throw e;}
}
async function pollJob(){
  if(!state.job)return;
  try{
    const job=await api(`/api/jobs/${state.job}`);showResult(job);
    if(['done','failed'].includes(job.state)){
      $('job-state').textContent=job.state==='done'?'● 本批完成':'● 执行失败';
      $('translate').disabled=false;state.job=null;
      if(state.selected){await refreshSummary();await loadSegments();}
      notify(job.state==='done'?'本批已完成，可继续下一批。':`执行失败：${job.error||'请查看结果'}`);
    }else setTimeout(pollJob,1200);
  }catch(e){$('translate').disabled=false;state.job=null;reportError(e);}
}
async function openGlossary(){
  if(!state.selected)throw new Error('请先选择作品');
  const data=await api(`/api/projects/${state.selected}/glossary`);
  $('glossary-json').value=JSON.stringify(data.terms,null,2);
  $('glossary-dialog').showModal();
}
async function saveGlossary(){
  if(!state.selected)throw new Error('请先选择作品');
  let terms;try{terms=JSON.parse($('glossary-json').value);}catch{throw new Error('术语表 JSON 语法有误');}
  const result=await api(`/api/projects/${state.selected}/glossary`,'PATCH',{terms});
  $('glossary-dialog').close();notify(`已保存 ${result.count} 条术语`);
}
async function audit() { if(!state.selected)throw new Error('尚未选择作品');const data=await api(`/api/projects/${state.selected}/audit`);showResult(data);notify(`${data.pending} 个未翻译片段；${data.flagged_total} 个待检查标记`); }
async function doExport() {
  if(!state.selected)throw new Error('尚未选择作品');
  const result=await api(`/api/projects/${state.selected}/export`,'POST',{format:$('export-format').value,allow_demo:$('allow-demo').checked});
  showResult(result);const a=document.createElement('a');a.href=result.download_url;a.download=result.filename;document.body.append(a);a.click();a.remove();notify('作品已生成，下载已开始');
}
function bind(id,event,callback){$(id).addEventListener(event,(e)=>{Promise.resolve().then(()=>callback(e)).catch(reportError);});}

// P3.1: local model lifecycle is opt-in and independent from active projects.
let inspectedCatalog = null;
function localLog(info) {
  $('local-job-result').textContent = typeof info === 'string' ? info : JSON.stringify(info, null, 2);
}
function byteSize(n) { return Number.isFinite(n) && n > 0 ? `${(n / 1073741824).toFixed(2)} GiB` : '大小未知'; }
function fitText(fit) {
  if (!fit) return '显存适配性未知（缺少权重大小）';
  const names = {gpu_plausible:'GPU 可能可运行', cpu_or_partial_offload_plausible:'CPU/混合卸载可能可运行', unknown_or_insufficient:'配置未知或可能不足'};
  return `${names[fit.assessment] || '未评估'} · 粗估 ${byteSize(fit.estimated_total_bytes)}，实际以运行测试为准`;
}
async function loadLocal() {
  $('hardware-status').textContent = '正在检测硬件与 Ollama（可能需要几秒）…';
  try {
    const data = await api('/api/local/status');
    const hardware = data.hardware;
    const ram = byteSize(hardware.system_ram_bytes);
    const gpu = hardware.gpus.length ? hardware.gpus.map(x=>`${x.name} · ${x.vram_free_mib} MiB 空闲`).join('；') : '未识别 NVIDIA GPU；其他显卡可能可用';
    $('hardware-status').textContent = `${hardware.platform} / ${hardware.machine} · 内存 ${ram} · ${gpu}\nOllama：${data.ollama.available?'已连接':'未连接'}`;
    const host=$('local-inventory'); host.replaceChildren();
    for (const model of data.ollama.models) {
      const row=el('div','inventory-item');
      row.append(el('div','',`Ollama · ${model.id}`));
      const select=el('button','btn subtle','用于翻译');select.type='button';
      select.addEventListener('click',()=>{$('provider').value='ollama';$('model-id').value=model.id;providerChanged();notify('已选中已安装的 Ollama 模型');});
      row.append(select);host.append(row);
    }
    for (const model of data.gguf) {
      const row=el('div','inventory-item');
      row.append(el('div','',`${model.name} · ${byteSize(model.size_bytes)}\n${fitText(model.fit)}`));
      const start=el('button','btn subtle','启动');start.type='button';
      start.addEventListener('click',()=>launchGGUF(model.name).catch(reportError));
      row.append(start);host.append(row);
    }
    if(!host.childElementCount)host.append(el('p','hint','还没有发现本地模型。'));
    $('engine-status').textContent = data.engine.state === 'stopped' ?
      `托管服务未运行 · llama-server ${data.engine.llama_server_available?'已找到':'未安装或未加入 PATH'}` :
      `${data.engine.state==='ready'?'已就绪':'正在加载'} · ${data.engine.name} · ${data.engine.base_url}（推理质量未验证）`;
    return data;
  } catch(e) { $('hardware-status').textContent=`设备检测失败：${e.message}`; throw e; }
}
async function inspectGGUF() {
  inspectedCatalog = null;
  const repo=$('gguf-repo').value.trim();
  $('gguf-license').textContent='正在查询模型资料…';
  const data=await api(`/api/local/catalog?repo=${encodeURIComponent(repo)}`);
  inspectedCatalog=data;
  $('gguf-license').replaceChildren(el('span','',`许可证：${data.license||'未标注'} · ${data.gated?'需要授权':''} ${data.private?'私有仓库':''} · 修订：${data.revision||'未知'}`));
  const a=el('a','hf-link','查看 Hugging Face 模型卡');a.href=`https://huggingface.co/${encodeURIComponent(repo.split('/')[0])}/${encodeURIComponent(repo.split('/')[1])}`;
  a.rel='noopener noreferrer';a.target='_blank';$('gguf-license').append(' · ',a);
  const select=$('gguf-file'); select.replaceChildren();
  for(const file of data.files) {
    const opt=el('option','',`${file.filename} (${byteSize(file.size_bytes)})`);
    opt.value=file.filename;select.append(opt);
  }
  if(!data.files.length)select.append(el('option','','未找到 GGUF 文件'));
  $('gguf-license-confirm').checked=false;
  showGGUFFit();
}
function showGGUFFit() {
  const file=inspectedCatalog?.files.find(x=>x.filename===$('gguf-file').value);
  $('gguf-fit').textContent=file?fitText(file.fit):'显存适配性：尚未评估';
}
async function modelJob(path, data) {
  const job=await api(path,'POST',data);
  localLog(job);
  pollModelJob(job.job_id);
}
async function pollModelJob(id) {
  try {
    const job=await api(`/api/local/jobs/${id}`);
    localLog(job);
    if(['done','failed'].includes(job.state)) {
      notify(job.state==='done'?'本地模型操作已完成':'本地模型操作失败，请查看记录');
      if(job.kind==='gguf_download'||job.kind==='ollama_pull')await loadLocal();
      if(job.kind==='evaluation')await loadReports();
    } else setTimeout(()=>pollModelJob(id),1100);
  } catch(e) { reportError(e); }
}
async function downloadGGUF() {
  if(!inspectedCatalog) throw new Error('请先查询 GGUF 模型仓库');
  if(!$('gguf-license-confirm').checked)throw new Error('请查看模型卡并确认授权与下载');
  if(inspectedCatalog.gated||inspectedCatalog.private)throw new Error('不支持直接下载需授权或私有模型');
  const filename=$('gguf-file').value;
  if(!inspectedCatalog.files.some(x=>x.filename===filename))throw new Error('请选择有效 GGUF 文件');
  if(!window.confirm(`从 Hugging Face 下载 ${filename}？可能占用大量磁盘空间。`))return;
  await modelJob('/api/local/install', {kind:'gguf',repo:inspectedCatalog.repo,
    filename,revision:inspectedCatalog.revision,max_gb:Number($('gguf-max-gb').value),
    license_reviewed:true,confirm_download:true});
}
async function installOllama(){
  const model=$('ollama-model-name').value.trim();
  if(!model)throw new Error('请输入 Ollama 模型名称');
  if(!window.confirm(`确认让本地 Ollama 下载 ${model}？`))return;
  await modelJob('/api/local/install',{kind:'ollama',model,confirm_download:true});
}
async function launchGGUF(name) {
  if(!window.confirm(`启动 llama-server 并加载 ${name}？这会占用本机内存或显存。`))return;
  const result=await api('/api/local/launch','POST',{name,context:Number($('llama-context').value),port:8080,confirm_launch:true});
  $('provider').value='compatible';$('base-url').value=result.base_url;
  $('model-id').value=name.split('/').pop().replace(/\.gguf$/i,'');providerChanged();
  localLog(result);await loadLocal();notify('托管进程已启动，等待模型加载完成后再翻译');
}
async function stopGGUF() {
  const result=await api('/api/local/stop','POST',{});localLog(result);await loadLocal();
}
async function evaluateModel() {
  const provider=$('provider').value;
  if(provider==='mock')throw new Error('请先选择真实模型');
  if(!window.confirm('运行 3 条固定测试？会向当前模型发送测试提示词，并可能产生 API 费用。'))return;
  await modelJob('/api/local/evaluate',{provider,model:$('model-id').value.trim(),
    base_url:$('base-url').value.trim(),accept_remote:$('remote-accept').checked});
}
async function loadReports() {
  const {reports}=await api('/api/local/reports');
  $('evaluation-reports').textContent=reports.length ? reports.slice(0,3).map(x=>
    `${x.timestamp} · ${x.provider}/${x.model} · ${x.summary.completed}/${x.summary.total} 完成；疑似拒答 ${x.summary.suspected_refusals}（尚需人工复核）`).join('\n') : '暂无评测记录。';
}

async function main(){
  const setup=await api('/api/bootstrap');state.token=setup.csrf_token;
  bind('new-project','click',()=>{state.selected=null;state.job=null;$('current-name').textContent='工作台';toggle('welcome',true);toggle('editor',false);toggle('import-card',true);return loadProjects();});
  bind('import-form','submit',importBook);bind('book-file','change',()=>{$('file-label').textContent=$('book-file').files[0]?.name||'选择 TXT / EPUB 文件';});
  $('chapter-select').addEventListener('change',()=>{state.chapter=Number($('chapter-select').value);state.offset=0;loadSegments().catch(reportError);});
  bind('prev-page','click',()=>{state.offset=Math.max(0,state.offset-perPage);return loadSegments();});
  bind('next-page','click',()=>{state.offset+=perPage;return loadSegments();});
  bind('refresh','click',async()=>{await loadProjects();if(state.selected){await refreshSummary();await loadSegments();}});
  bind('glossary','click',openGlossary);bind('glossary-save','click',saveGlossary);bind('glossary-close','click',()=>$('glossary-dialog').close());
  bind('audit','click',audit);bind('export','click',doExport);bind('model-search','click',discover);bind('translate','click',translate);
  $('provider').addEventListener('change',providerChanged);$('base-url').addEventListener('change',providerChanged);
  bind('local-refresh','click',loadLocal);
  bind('gguf-inspect','click',inspectGGUF);
  $('gguf-file').addEventListener('change',showGGUFFit);
  bind('gguf-download','click',downloadGGUF);
  bind('ollama-install','click',installOllama);
  bind('llama-stop','click',stopGGUF);
  bind('model-evaluate','click',evaluateModel);
  $('local-manager').addEventListener('toggle',()=>{if($('local-manager').open){loadLocal().catch(reportError);loadReports().catch(reportError);}});
  providerChanged();await loadProjects();
}
main().catch(reportError);
