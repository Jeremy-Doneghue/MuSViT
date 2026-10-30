const $ = id => document.getElementById(id);
const state = {documents:[], doc:null, region:null, filter:'pending', image:null,
  fullPage:false, editorReady:false, editorLoaded:false, draft:null, dirty:false,
  saving:Promise.resolve(), loading:false, processing:false, requests:new Map()};
let saveTimer, toastTimer;
const editor = () => $('notation').contentWindow;
const message = data => editor().postMessage(data,location.origin);
function toast(text) { $('toast').textContent=text; $('toast').hidden=false; clearTimeout(toastTimer); toastTimer=setTimeout(()=>$('toast').hidden=true,8000); }
async function api(path,body) {
  const response = await fetch(path,body===undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Request failed');
  return result;
}
const activePage = () => state.doc?.pages.find(p=>p.number===state.region.page);
const context = () => ({instrument:$('instrument').value, clef:$('clef').value,
  fifths:Number($('fifths').value), beats:Number($('beats').value),
  beat_type:Number($('beat-type').value), transpose:Number($('transpose').value),
  confirmed:$('context-confirmed').checked});

function saveLabel(text) {$('save-state').textContent=text;}
function markDirty() {
  if (state.loading || !state.region) return;
  state.dirty=true; saveLabel('Unsaved changes'); clearTimeout(saveTimer);
  saveTimer=setTimeout(()=>save().catch(error=>toast(error.message)),900);
}

function payload(status) {
  const data = {document_id:state.doc.id, region_id:state.region.id,
    notes:$('notes').value, bar_count:Number($('bar-count').value), context:context()};
  if ($('context-page').checked) data.page_context=context();
  if (state.draft?.region===state.region.id) Object.assign(data,{score:state.draft.score,musicxml:state.draft.musicxml,editor_context:state.draft.editor_context});
  if (status) data.status=status;
  return data;
}

async function save(status, extra={}) {
  clearTimeout(saveTimer);
  if (!state.region || (!state.dirty && !status && !Object.keys(extra).length)) return state.saving;
  const data = {...payload(status),...extra};
  const selectedId=state.region.id, documentId=state.doc.id;
  state.dirty=false; saveLabel('Saving…');
  const work=state.saving.catch(()=>{}).then(()=>api('/api/region',data)).then(doc=>{
    state.documents=state.documents.map(d=>d.id===doc.id?doc:d);
    if(state.doc?.id===documentId) {
      state.doc=doc;
      if(state.region?.id===selectedId) state.region=doc.regions.find(r=>r.id===selectedId);
      updateSummary();
    }
    saveLabel(state.dirty?'Unsaved changes':'Saved on this computer');
    return doc;
  }).catch(error=>{state.dirty=true;saveLabel('Save failed — changes retained');throw error;});
  state.saving=work;
  return work;
}

function requestSnapshot() {
  if (!state.editorLoaded) return Promise.reject(new Error('Wait for the notation editor to finish loading.'));
  const request=crypto.randomUUID();
  return new Promise((resolve,reject)=>{
    const timeout=setTimeout(()=>{state.requests.delete(request);reject(new Error('Notation editor did not respond. Your passage has not been approved.'));},12000);
    state.requests.set(request,{resolve,reject,timeout});
    message({type:'editor-export',request});
  });
}

function updateSummary() {
  const doc=state.doc;
  $('documents').replaceChildren(...state.documents.map(document=>{
    const element=window.document.createElement('button');
    element.className='document-button'+(doc?.id===document.id?' selected':'');
    const title=window.document.createElement('span'); title.textContent=document.title;
    const detail=window.document.createElement('small');
    detail.textContent=`${document.pages.length} page(s) · ${document.regions.filter(r=>r.status==='reviewed').length} reviewed`;
    element.append(title,detail);element.onclick=()=>chooseDocument(document.id).catch(error=>toast(error.message));
    return element;
  }));
  if (!doc) return;
  $('document-title').textContent=doc.title;
  const reviewed=doc.regions.filter(r=>r.status==='reviewed').length;
  $('progress-number').textContent=`${reviewed} / ${doc.regions.length}`;
  $('progress-fill').style.width=`${reviewed/doc.regions.length*100}%`;
  document.querySelectorAll('[data-filter]').forEach(button=>{
    button.classList.toggle('selected',button.dataset.filter===state.filter);
    const labels={pending:'To transcribe',reviewed:'Reviewed',skipped:'Skipped',unclear:'Unclear',bad_crop:'Bad crops'};
    button.textContent=`${labels[button.dataset.filter]} ${doc.regions.filter(r=>r.status===button.dataset.filter).length}`;
  });
  $('region-list').replaceChildren(...doc.regions.map((region,index)=>{
    const button=document.createElement('button');button.className=`region-chip ${region.status}`+(region.id===state.region?.id?' current':'');
    button.textContent=index+1;button.title=`Page ${region.page}, staff ${region.staff_index+1} · ${region.status.replaceAll('_',' ')}`;
    button.onclick=()=>navigate(region.id).catch(error=>toast(error.message));return button;
  }));
  $('export').disabled=false;
}

async function chooseDocument(id) {
  await save();
  state.doc=state.documents.find(doc=>doc.id===id);
  state.filter='pending';
  const region=state.doc.regions.find(r=>r.status==='pending') || state.doc.regions[0];
  await showRegion(region.id);
}

async function navigate(id) {if(state.loading||state.processing)return;await save();await showRegion(id);}

function setContext(value) {
  $('instrument').value=value.instrument;
  $('clef').value=value.clef;$('fifths').value=value.fifths;
  $('beats').value=value.beats;$('beat-type').value=value.beat_type;
  if (![...$('transpose').options].some(o=>Number(o.value)===Number(value.transpose))) {
    $('transpose').add(new Option(`Custom (${value.transpose})`,value.transpose));
  }
  $('transpose').value=value.transpose;$('context-confirmed').checked=value.confirmed;
}

async function showRegion(id) {
  state.loading=true;state.editorLoaded=false;state.draft=null;
  state.region=state.doc.regions.find(r=>r.id===id);
  const r=state.region,page=activePage();
  $('empty').hidden=true;$('review').hidden=false;
  $('region-title').textContent=`Passage ${state.doc.regions.indexOf(r)+1}`;
  $('region-subtitle').textContent=`Page ${r.page} · Staff ${r.staff_index+1} · ${r.status.replaceAll('_',' ')} · Read and enter written pitch`;
  $('focus-title').textContent=`Source passage · ${r.bar_count} bar${r.bar_count===1?'':'s'} represented`;
  $('detection-tag').textContent=r.detection==='adjusted'?'Boundary adjusted':'Unverified boundary';
  $('notes').value=r.notes;$('bar-count').value=r.bar_count;
  setContext(r.context || page.context);
  $('context-page').checked=!r.context || JSON.stringify(r.context)===JSON.stringify(page.context);
  ['left','top','right','bottom'].forEach((side,index)=>$('crop-'+side).value=r.box[index]);
  $('crop-details').open=false;
  updateSummary();
  const image=new Image();image.src=page.image;
  await image.decode();state.image=image;drawImages();
  if (state.editorReady) loadEditor();
  state.dirty=false;state.loading=false;
  saveLabel('Saved on this computer');
}

function loadEditor() {
  message({type:'editor-load',region:state.region.id,context:state.region.editor_context || context(),score:state.region.score,musicxml:state.region.musicxml});
}

function drawImages() {
  if(!state.image || !state.region)return;
  const image=state.image,r=state.region;
  const ctxCanvas=$('context-canvas'),focusCanvas=$('focus-canvas');
  const box=state.fullPage?[0,0,image.width,image.height]:r.staff_box;
  ctxCanvas.width=box[2]-box[0];ctxCanvas.height=box[3]-box[1];
  const ctx=ctxCanvas.getContext('2d');
  ctx.drawImage(image,...box.slice(0,2),box[2]-box[0],box[3]-box[1],0,0,ctxCanvas.width,ctxCanvas.height);
  const x=r.box[0]-box[0],y=r.box[1]-box[1],w=r.box[2]-r.box[0],h=r.box[3]-r.box[1];
  ctx.fillStyle='#5e99432b';ctx.fillRect(x,y,w,h);ctx.strokeStyle='#378158';ctx.lineWidth=3;ctx.strokeRect(x+1,y+1,w-2,h-2);
  focusCanvas.width=w;focusCanvas.height=h;
  focusCanvas.getContext('2d').drawImage(image,r.box[0],r.box[1],w,h,0,0,w,h);
}

async function move(direction) {
  if(!state.region)return;
  const regions=state.doc.regions.filter(r=>r.status===state.filter);
  let index=regions.findIndex(r=>r.id===state.region.id);
  if(index<0)index=direction>0?-1:regions.length;
  const next=regions[index+direction];
  if(next)await navigate(next.id);else toast('No more passages in this queue. Choose another review tab.');
}

async function finish(status) {
  if(!state.region||state.processing||state.loading)return;
  state.processing=true;
  try {
  if(status==='reviewed') {
    if(!$('context-confirmed').checked)throw new Error('Check the musical context and tick its confirmation before approving.');
    const draft=await requestSnapshot();
    if(draft.region!==state.region.id)throw new Error('The editor is switching passages. Please try again.');
    state.draft=draft;
  }
  const index=state.doc.regions.indexOf(state.region);
  await save(status);
  const remaining=state.doc.regions.filter(r=>r.status==='pending');
  const next=state.doc.regions.slice(index+1).find(r=>r.status==='pending') || remaining[0];
  if(next) {state.filter='pending';await showRegion(next.id);message({type:'editor-focus'});}
  else {
    updateSummary();$('region-subtitle').textContent='No pending passages remain. Revisit skipped, unclear or bad-crop regions above.';
    toast('Pending queue complete. Your work is saved.');
  }
  } finally {state.processing=false;}
}

function shortcut(event) {
  if(!state.region || $('import-dialog').open || $('help-dialog').open)return;
  if(event.altKey || event.alt) {
    const statuses={KeyS:'skipped',KeyU:'unclear',KeyB:'bad_crop'};
    if(statuses[event.code]) {event.preventDefault?.();finish(statuses[event.code]).catch(error=>toast(error.message));}
  } else if(event.key==='Enter' && (event.ctrlKey || event.metaKey || event.type==='queue-shortcut')) {
    event.preventDefault?.();finish('reviewed').catch(error=>toast(error.message));
  }
}

window.addEventListener('message',event=>{
  if(event.origin!==location.origin || event.source!==editor())return;
  const data=event.data;
  if(data.type==='editor-ready' && !state.editorReady) {state.editorReady=true;if(state.region)loadEditor();}
  if(data.type==='editor-loaded' && data.region===state.region?.id)state.editorLoaded=true;
  if(data.type==='editor-changed' && data.region===state.region?.id){state.draft=data;markDirty();}
  if(data.type==='editor-duration')document.querySelectorAll('[data-duration]').forEach(button=>button.classList.toggle('active',Number(button.dataset.duration)===data.duration));
  if(data.type==='editor-error') {
    toast(data.message);
    if(data.request && state.requests.has(data.request)) {const req=state.requests.get(data.request);clearTimeout(req.timeout);req.reject(new Error(data.message));state.requests.delete(data.request);}
  }
  if(data.type==='editor-snapshot') {
    const req=state.requests.get(data.request);
    if(req){clearTimeout(req.timeout);req.resolve(data);state.requests.delete(data.request);}
  }
  if(data.type==='queue-shortcut')shortcut(data);
});

// Recover if the iframe's initial ready message preceded this module's listener.
$('notation').addEventListener('load',()=>message({type:'editor-check-ready'}));
message({type:'editor-check-ready'});

for(const id of ['instrument','clef','fifths','beats','beat-type','transpose','context-confirmed','context-page','bar-count','notes']) {
  $(id).addEventListener('change',markDirty);
}
$('notes').addEventListener('input',markDirty);
$('apply-context').onclick=()=>{
  if(!state.region)return;
  message({type:'editor-action',action:'context',value:context()});markDirty();
};
$('editor-toolbar').onclick=event=>{
  const button=event.target.closest('button');if(!button)return;
  if(button.dataset.action==='reset' && !confirm('Replace this passage’s notation with blank rests? You can undo this only by reloading a saved version.'))return;
  message({type:'editor-action',action:button.dataset.duration?'duration':button.dataset.action,value:button.dataset.duration});
};
$('play').onclick=()=>message({type:'editor-play'});
$('apply-dynamic').onclick=()=>message({type:'editor-action',action:'dynamic',value:$('dynamic').value});
$('apply-direction').onclick=()=>message({type:'editor-action',action:'direction',value:$('direction-text').value.trim()});
$('context-toggle').onclick=()=>{state.fullPage=!state.fullPage;$('context-toggle').textContent=state.fullPage?'Show staff context':'Show full page';drawImages();};
$('crop-apply').onclick=()=>{
  const box=['left','top','right','bottom'].map(side=>Number($('crop-'+side).value));
  save(undefined,{box}).then(()=>{drawImages();$('detection-tag').textContent='Boundary adjusted';}).catch(error=>toast(error.message));
};
$('previous').onclick=()=>move(-1).catch(error=>toast(error.message));
$('next').onclick=()=>move(1).catch(error=>toast(error.message));
for(const [id,status] of [['approve','reviewed'],['skip','skipped'],['unclear','unclear'],['bad-crop','bad_crop']])$(id).onclick=()=>finish(status).catch(error=>toast(error.message));
$('filters').onclick=event=>{
  const button=event.target.closest('button');if(!button || !state.doc)return;
  save().then(()=>{
    state.filter=button.dataset.filter;
    const next=state.doc.regions.find(r=>r.status===state.filter);
    updateSummary();if(next)return showRegion(next.id);
    toast('There are no passages with this status yet.');
  }).catch(error=>toast(error.message));
};
$('export').onclick=()=>save().then(()=>{if(state.doc)window.location.href='/api/export/'+state.doc.id;}).catch(error=>toast(error.message));
$('xml-import').onclick=()=>$('xml-file').click();
$('xml-file').onchange=async()=>{
  const file=$('xml-file').files[0];if(file)message({type:'editor-action',action:'xml',value:await file.text()});
  $('xml-file').value='';
};
for(const id of ['import-open','empty-import'])$(id).onclick=()=>$('import-dialog').showModal();
$('import-close').onclick=()=>$('import-dialog').close();
$('help-open').onclick=()=>$('help-dialog').showModal();
$('help-close').onclick=()=>$('help-dialog').close();
$('find-files').onclick=async()=>{
  $('find-files').disabled=true;$('import-status').textContent='Looking for scans…';
  try {
    const paths=await api('/api/files?root='+encodeURIComponent($('source-folder').value));
    $('source-file').replaceChildren(...paths.map(path=>new Option(path.replace($('source-folder').value.replace(/\/$/,'')+'/',''),path)));
    $('import-status').textContent=`Found ${paths.length} scans.`;
  } catch(error){$('import-status').textContent=error.message;}
  finally{$('find-files').disabled=false;}
};
$('import-form').onsubmit=async event=>{
  event.preventDefault();if(!$('source-file').value)return;
  $('import-submit').disabled=true;$('import-status').textContent='Preparing pages and proposing bar regions…';
  try {
    await save();
    const doc=await api('/api/import',{path:$('source-file').value,start_page:Number($('start-page').value),pages:Number($('page-count').value)});
    state.documents=await api('/api/documents');
    $('import-dialog').close();await chooseDocument(doc.id);
  }catch(error){$('import-status').textContent=error.message;}
  finally{$('import-submit').disabled=false;}
};
document.addEventListener('keydown',event=>{
  shortcut(event);
  if(event.key==='?' && !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName))$('help-dialog').showModal();
});
window.addEventListener('beforeunload',event=>{if(state.dirty){event.preventDefault();event.returnValue='';}});

const keys=['7 flats','6 flats','5 flats','4 flats','3 flats','2 flats','1 flat','No accidentals','1 sharp','2 sharps','3 sharps','4 sharps','5 sharps','6 sharps','7 sharps'];
$('fifths').replaceChildren(...keys.map((key,index)=>new Option(key,index-7,index===7,index===7)));
$('export').disabled=true;
try {
  const settings=await api('/api/settings');$('source-folder').value=settings.scan_dir;
  state.documents=await api('/api/documents');updateSummary();
  if(state.documents.length)await chooseDocument(state.documents[0].id);
}catch(error){toast(error.message);}
