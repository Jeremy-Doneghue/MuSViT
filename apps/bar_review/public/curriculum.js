const $ = id => document.getElementById(id);
let catalog, documents = [], stage = '0', latest = null, busy = false, revision = 0;
let recipe = [];
let focus = {x: .18, y: .055};
async function api(path, body) {
  let response;
  try {
    response = await fetch(path, body === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  } catch (error) {
    throw new Error('Lost connection to Bar Review. Check that the Python server and SSH tunnel are still running, then retry. If the server exited, check its terminal for the renderer error.');
  }
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}
function options(select, rows) {
  select.replaceChildren(...rows.map(([value, label]) => { const option = document.createElement('option'); option.value = value; option.textContent = label; return option; }));
}
function status(message, type='') { $('preview-status').textContent = message; $('preview-status').className = type; }
function dirty() {
  revision++;
  $('dirty').textContent = 'Settings changed. Generate a preview to apply them.';
  if (latest) status('Showing the previous preview. Generate again to apply the current settings.', 'stale');
}
function renderRecipe() {
  const list = $('effect-list'); list.replaceChildren();
  if (!recipe.length) { const empty = document.createElement('li'); empty.className = 'recipe-empty'; empty.textContent = 'No effects. The source stays unchanged.'; list.append(empty); }
  recipe.forEach((effect,index) => {
    const definition = catalog.effects[effect.type];
    const card = document.createElement('li'); card.className = 'effect-card';
    const head = document.createElement('div'); head.className = 'effect-head';
    const enabledLabel = document.createElement('label'); enabledLabel.className = 'effect-enabled';
    const enabled = document.createElement('input'); enabled.type = 'checkbox'; enabled.checked = effect.enabled;
    enabled.onchange = () => { effect.enabled = enabled.checked; dirty(); renderRecipe(); };
    enabledLabel.append(enabled,document.createTextNode(`${index+1}. ${definition.label}`)); head.append(enabledLabel);
    const actions = document.createElement('div'); actions.className = 'effect-actions';
    for (const [text,delta,label] of [['↑',-1,'Move up'],['↓',1,'Move down'],['×',0,'Remove']]) {
      const button = document.createElement('button'); button.type = 'button'; button.textContent = text; button.setAttribute('aria-label',`${label} ${definition.label}`); button.title = label;
      button.disabled = delta !== 0 && (index+delta < 0 || index+delta >= recipe.length);
      button.onclick = () => { if (delta) [recipe[index],recipe[index+delta]] = [recipe[index+delta],recipe[index]]; else recipe.splice(index,1); dirty(); renderRecipe(); const cards = list.querySelectorAll('.effect-card'); cards[Math.min(Math.max(0,index+delta),cards.length-1)]?.querySelector('button:not(:disabled)')?.focus(); };
      actions.append(button);
    }
    head.append(actions); card.append(head);
    if (definition.description) { const help = document.createElement('p'); help.className = 'small-note'; help.textContent = definition.description; card.append(help); }
    const fields = document.createElement('div'); fields.className = 'effect-fields';
    for (const [key,field] of Object.entries(definition.fields)) {
      const label = document.createElement('label'); label.textContent = field.label;
      const control = document.createElement(field.options ? 'select' : 'input');
      if (field.options) options(control,field.options.map(value => [value,value.replaceAll('_',' ')]));
      else { control.type = 'number'; control.min = field.min; control.max = field.max; control.step = field.step; }
      control.value = effect.parameters[key]; control.disabled = !effect.enabled;
      control.oninput = () => { effect.parameters[key] = field.options ? control.value : Number(control.value); dirty(); };
      label.append(control); fields.append(label);
    }
    card.append(fields); list.append(card);
  });
  $('add-effect').disabled = recipe.length >= 12;
}
function loadPreset() {
  recipe = structuredClone(catalog.recipe_presets[$('profile').value]); renderRecipe(); dirty();
}
function selectStage(id) {
  stage = id;
  const item = catalog.stages.find(s => s.id === id);
  for (const button of $('stages').children) {
    button.classList.toggle('selected', button.dataset.stage === id);
    button.setAttribute('aria-current', button.dataset.stage === id ? 'step' : 'false');
  }
  $('stage-title').textContent = item.title;
  $('stage-description').textContent = item.description;
  $('stage-focus').textContent = item.focus;
  $('stage-mix').textContent = item.mix;
  $('synthetic-fields').hidden = id === '4'; $('real-fields').hidden = id !== '4';
  $('source-kind').textContent = id === '4' ? 'Imported scan' : 'Generated example';
  $('source-help').textContent = id === '4' ? (documents.length ? 'Full imported pages. Original scan quality is preserved; additional damage is applied only to a preview copy.' : 'No scans imported yet. Return to the transcription queue and import a PDF or image, then reload this page.') : 'Seeds vary note, passage and page examples. Focused voice fixtures stay fixed.';
  options($('example'), item.examples.map(x => [x, catalog.examples[x]]));
  $('generate').disabled = busy || (id === '4' && !documents.length);
  dirty();
}
function updatePages() {
  const doc = documents.find(d => d.id === $('document').value);
  options($('page'), (doc?.pages || []).map(p => [p.number, `Page ${p.number}`]));
}
function request() {
  return {stage, example:$('example').value, music_seed:Number($('music-seed').value), font:$('font').value,
    document_id:$('document').value, page:Number($('page').value),
    settings:{recipe:structuredClone(recipe),seed:Number($('seed').value)}};
}
function drawDetail() {
  for (const name of ['source','augmented']) {
    const img = $(`${name}-image`), canvas = $(`${name}-detail`), ctx = canvas.getContext('2d');
    ctx.fillStyle = 'white'; ctx.fillRect(0,0,480,240);
    if (!img.complete || !img.naturalWidth) continue;
    const width = Math.min(240,img.naturalWidth), height = Math.min(120,img.naturalHeight);
    const x = Math.max(0,Math.min(img.naturalWidth-width,focus.x*img.naturalWidth-width/2));
    const y = Math.max(0,Math.min(img.naturalHeight-height,focus.y*img.naturalHeight-height/2));
    ctx.drawImage(img,x,y,width,height,0,0,480,240);
  }
}
function zoom() {
  for (const name of ['source','augmented']) {
    const img = $(`${name}-image`), fit = $('zoom').value === 'fit';
    img.parentElement.classList.toggle('pixel-view',!fit);
    img.style.width = fit ? '100%' : `${img.naturalWidth*Number($('zoom').value)}px`;
  }
}
async function showImages() {
  if (!latest) return;
  const suffix = $('resolution').value === '1024' ? '-1024' : '';
  await Promise.all(['source','augmented'].map(name => new Promise((resolve,reject) => {
    const img = $(`${name}-image`);
    img.onload = () => { $(`${name}-size`).textContent = `${img.naturalWidth} × ${img.naturalHeight}`; resolve(); };
    img.onerror = () => reject(new Error('Could not load preview image.'));
    img.src = `/curriculum-artifacts/${latest.id}/${name}${suffix}.png`;
  })));
  $('comparison').hidden = false; zoom(); drawDetail();
}
async function generate(event) {
  event?.preventDefault();
  if (busy) return;
  const requestedRevision = revision;
  busy = true; $('generate').disabled = true; $('generate').textContent = 'Rendering…';
  status('Rendering the score and applying Augraphy. The first preview may take a little longer.');
  try {
    const result = await api('/api/curriculum/preview', request());
    latest = result;
    $('source-label').textContent = result.source.kind === 'real-scan' ? 'Original scan' : 'Clean rendering';
    $('recipe').textContent = JSON.stringify(result,null,2);
    $('geometry-note').textContent = `Geometry: ${result.geometry}. ${result.preprocessing}.`;
    const link = $('export-preview'); link.href = `/api/curriculum/export/${result.id}`; link.classList.remove('disabled'); link.setAttribute('aria-disabled','false');
    await showImages();
    if (revision !== requestedRevision) status('Preview ready for earlier settings. Generate again to apply your latest changes.', 'stale');
    else { const dpiLimit = result.effects.some(effect => effect.parameters.source_limited) ? ' A DPI step exceeded the available source resolution; no extra detail was invented.' : ''; status(`Preview ready · ${result.effects.length} effect groups · seed ${result.settings.seed}. Export saves exactly this preview.${dpiLimit}`); $('dirty').textContent = 'Preview matches the current settings.'; }
  } catch (error) { status(error.message, 'error'); }
  finally { busy = false; $('generate').disabled = stage === '4' && !documents.length; $('generate').textContent = 'Generate preview'; }
}
$('recipe-form').addEventListener('submit',generate);
for (const id of ['seed','music-seed','font','example','document','page']) {
  $(id).addEventListener('input', () => { if (id === 'document') updatePages(); dirty(); });
}
$('load-preset').onclick = loadPreset;
$('add-effect').onclick = () => {
  if (recipe.length >= 12) return;
  const type = $('effect-type').value;
  recipe.push({id:crypto.randomUUID(),type,enabled:true,parameters:Object.fromEntries(Object.entries(catalog.effects[type].fields).map(([key,field]) => [key,field.default]))});
  renderRecipe(); dirty();
};
$('next-seed').onclick = () => { $('seed').value = (Number($('seed').value)+1)%2147483648; dirty(); };
$('reset-recipe').onclick = () => { recipe = []; renderRecipe(); dirty(); };
$('resolution').onchange = () => showImages().catch(e => status(e.message,'error'));
$('zoom').onchange = zoom;
for (const name of ['source','augmented']) {
  const img = $(`${name}-image`);
  img.onclick = event => { const rect = img.getBoundingClientRect(); focus = {x:(event.clientX-rect.left)/rect.width,y:(event.clientY-rect.top)/rect.height}; drawDetail(); };
  img.onkeydown = event => { if (!['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(event.key)) return; event.preventDefault(); focus.x = Math.max(0,Math.min(1,focus.x + (event.key === 'ArrowRight' ? .03 : event.key === 'ArrowLeft' ? -.03 : 0))); focus.y = Math.max(0,Math.min(1,focus.y + (event.key === 'ArrowDown' ? .03 : event.key === 'ArrowUp' ? -.03 : 0))); drawDetail(); };
}
try {
  [catalog,documents] = await Promise.all([api('/api/curriculum'),api('/api/documents')]);
  for (const item of catalog.stages) {
    const button = document.createElement('button'); button.className = 'stage-button'; button.dataset.stage = item.id;
    const number = document.createElement('span'); number.className = 'number'; number.textContent = item.id;
    const label = document.createElement('span'); label.textContent = item.title;
    button.append(number,label); button.onclick = () => selectStage(item.id); $('stages').append(button);
  }
  options($('document'),documents.map(d => [d.id,d.title])); updatePages(); selectStage('0'); options($('effect-type'),Object.entries(catalog.effects).map(([key,value]) => [key,value.label])); loadPreset(); await generate();
} catch (error) { status(error.message,'error'); $('generate').disabled = true; }
