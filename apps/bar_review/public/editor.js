/* Smoosic supplies score structure, engraving, transformations and MusicXML. */
/* global Smo */
let view, currentContext, currentRegion, busy = Promise.resolve();
let duration = 4096, audioContext, playbackNodes = [];
const tell = (type, data = {}) => parent.postMessage({ type, ...data }, location.origin);
const escapeXml = (value) => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('"', '&quot;');

function blankXml(context) {
  const clefs = {treble:['G',2],bass:['F',4],alto:['C',3],tenor:['C',4],percussion:['percussion',2]};
  const [sign,line] = clefs[context.clef];
  const types = {1:'whole',2:'half',4:'quarter',8:'eighth',16:'16th',32:'32nd',64:'64th'};
  const rest = `<note><rest/><duration>${64/context.beat_type}</duration><type>${types[context.beat_type]}</type></note>`;
  return `<?xml version="1.0" encoding="utf-8"?><score-partwise version="4.0"><part-list><score-part id="P1"><part-name>${escapeXml(context.instrument || 'Part')}</part-name></score-part></part-list><part id="P1"><measure number="1"><attributes><divisions>16</divisions><key><fifths>${context.fifths}</fifths></key><time><beats>${context.beats}</beats><beat-type>${context.beat_type}</beat-type></time><clef><sign>${sign}</sign><line>${line}</line></clef><transpose><chromatic>${context.transpose}</chromatic></transpose></attributes>${rest.repeat(context.beats)}</measure></part></score-partwise>`;
}

function compact(score) {
  // Smoosic switches to the part's own layout when a single part is exposed.
  // Compact both layouts so passage navigation cannot restore a full paper page.
  const layouts = new Set([score.layoutManager,
    ...score.staves.map(staff => staff.partInfo.layoutManager)]);
  for (const manager of layouts) {
    Object.assign(manager.globalLayout, {
      pageWidth: Math.max(320, document.documentElement.clientWidth),
      pageHeight:220, svgScale:.8, zoomScale:1, maxMeasureSystem:4
    });
    manager.pageLayouts.forEach(page => Object.assign(page,
      {topMargin:25,bottomMargin:20,leftMargin:25,rightMargin:25}));
  }
  score.preferences.autoPlay = false;
  score.preferences.autoAdvance = false;
  return score;
}

function parseXml(xml) {
  const doc = new DOMParser().parseFromString(xml, 'application/xml');
  if (doc.querySelector('parsererror') || doc.documentElement.nodeName !== 'score-partwise') {
    throw new Error('Choose an uncompressed partwise MusicXML file.');
  }
  const score = Smo.XmlToSmo.convert(doc);
  // Smoosic imports dynamics, but does not import general words directions.
  Array.from(doc.querySelectorAll('part')).forEach((part, si) => {
    Array.from(part.querySelectorAll(':scope > measure')).forEach((measure, mi) => {
      let pending = [];
      const indices = {};
      for (const child of measure.children) {
        if (child.tagName === 'direction') pending.push(...child.querySelectorAll('direction-type > words'));
        if (child.tagName !== 'note' || child.querySelector('chord')) continue;
        const voice = Number(child.querySelector('voice')?.textContent || 1) - 1;
        const index = indices[voice] || 0;
        const note = score.staves[si]?.measures[mi]?.voices[voice]?.notes[index];
        if (note) pending.forEach(words => note.addAnnotation(new Smo.SmoLyric({
          ...Smo.SmoLyric.defaults, parser:Smo.SmoLyric.parsers.annotation,
          text:words.textContent, verse:note.getAnnotations().length
        })));
        pending = [];
        indices[voice] = index + 1;
      }
    });
  });
  return score;
}

async function load(data) {
  stop();
  // Register Smoosic's dynamic constructors before parsing XML or saved scores.
  // Deserialization needs these even before the first score view exists.
  if (!view) Smo.SuiApplication.initSync();
  currentContext = data.context;
  currentRegion = data.region;
  const score = compact(data.score ? Smo.SmoScore.deserialize(JSON.stringify(data.score)) :
    parseXml(data.musicxml || blankXml(currentContext)));
  if (!view) {
    // Prevent native sample downloads: playback below uses the browser's synthesizer.
    Smo.SuiOscillator.playSelectionNow = () => {};
    // configure(mode:'library') still mounts the full standalone application DOM.
    // Use the exported score view with our own navigation surface instead.
    await Smo.SuiApplication.registerFonts();
    const scroll = document.getElementById('score-scroll');
    const element = document.getElementById('score-canvas');
    const scrollHandlers = [];
    const navigation = {
      outerContainer:document.getElementById('score-root'), scrollContainer:scroll,
      scoreContainer:element, displayMode:'vertical', initialize(){}, isInitialized:()=>true,
      pushScrollHandler:handler=>scrollHandlers.push(handler),
      popScrollHandler:()=>scrollHandlers.pop(),
      showSplashModal(){},showProgressModal(){},showHelpModal(){},setProgress(){},
      hideProgressModal(){},showDialogModal(){},hideDialogModal(){},showDebugString(){},
      displayExceptionDialog:text=>tell('editor-error',{message:String(text)})
    };
    view = new Smo.SuiScoreViewOperations({navigation,demonPollTime:50,idleRedrawTime:250,
      audioAnimation:{audioAnimationHandler(){},clearAudioAnimationHandler(){}}},score,new Smo.UndoBuffer());
    view.startRenderingEngine();
    // The standalone UI normally supplies the single-note selection delegate.
    // Draw its outline here because our embedded view has no standalone UI.
    view.tracker.delegate = {
      onSingleNoteHighlighted(selection) { view.tracker.drawSelectionRects([selection.note.logicalBox]); },
      onPitchIndexChanged() {}
    };
    scroll.addEventListener('scroll',event=>{
      view.scroller.handleScroll(scroll.scrollLeft,scroll.scrollTop);
      scrollHandlers.forEach(handler=>handler(event));
    });
    element.addEventListener('mousemove', event => {
      view.tracker.intersectingArtifact(Smo.SvgHelpers.smoBox({x:event.clientX,y:event.clientY}));
    });
    element.addEventListener('click', event => {
      view.tracker.intersectingArtifact(Smo.SvgHelpers.smoBox({x:event.clientX,y:event.clientY}));
      view.tracker.selectSuggestion({type:'click',shiftKey:event.shiftKey,ctrlKey:event.ctrlKey,altKey:event.altKey});
      document.getElementById('score-root').focus();
    });
  } else {
    await view.changeScore(score);
  }
  await view.renderer.updatePromise();
  document.getElementById('loading').hidden = true;
  view.tracker.moveHome();
  view.scroller.scrollAbsolute(0,0);
  tell('editor-loaded', {region:currentRegion});
}

function snapshot() {
  if (!view) throw new Error('The notation editor is still loading.');
  const score = view.storeScore.serialize({skipStaves:false,useDictionary:false,preserveStaffIds:true});
  const doc = Smo.SmoToXml.convert(view.storeScore);
  // Preserve note-anchored directions missing from Smoosic's MusicXML writer.
  Array.from(doc.querySelectorAll('part')).forEach((part, si) => {
    Array.from(part.querySelectorAll(':scope > measure')).forEach((measure, mi) => {
      const indices = {};
      for (const element of Array.from(measure.querySelectorAll(':scope > note'))) {
        if (element.querySelector('chord')) continue;
        const voice = Number(element.querySelector('voice')?.textContent || 1) - 1;
        const index = indices[voice] || 0;
        indices[voice] = index + 1;
        const note = view.storeScore.staves[si]?.measures[mi]?.voices[voice]?.notes[index];
        if (!note) continue;
        const add = (tag, text, placement) => {
          const direction = doc.createElement('direction');
          direction.setAttribute('placement', placement);
          const type = doc.createElement('direction-type');
          const content = doc.createElement(tag);
          if (tag === 'dynamics') content.appendChild(doc.createElement(text));
          else content.textContent = text;
          type.appendChild(content); direction.appendChild(type);
          measure.insertBefore(direction, element);
        };
        note.getModifiers('SmoDynamicText').forEach(mod => add('dynamics',mod.text,'below'));
        note.getAnnotations().forEach(mod => add('words',mod.text,'above'));
      }
    });
  });
  const xml = new XMLSerializer().serializeToString(doc);
  return {region:currentRegion, score, musicxml:xml, editor_context:currentContext};
}

function changed() { tell('editor-changed', snapshot()); }

async function setDuration(ticks) {
  duration = ticks;
  let note = view.tracker.selections[0]?.note;
  if (!note) return;
  // Smoosic splits or combines notes to retain the measure's total duration.
  for (let attempt=0; attempt<6; attempt++) {
    note = view.tracker.selections[0]?.note;
    if (!note) break;
    const current = note.tickCount;
    if (Math.abs(current-ticks) < 1) break;
    await view.batchDurationOperation(current > ticks ? 'halveDuration' : 'doubleDuration');
  }
  tell('editor-duration', {duration});
}

async function enterPitch(letter) {
  const note = view.tracker.selections[0]?.note;
  if (!note) return;
  await setDuration(duration);
  // Existing score context resolves diatonic pitches and their accidentals.
  await view.setPitch(letter);
  view.tracker.moveSelectionRight();
}

async function action(name, value) {
  if (!view) throw new Error('The notation editor is still loading.');
  stop();
  if (name === 'duration') await setDuration(Number(value));
  else if (name === 'pitch') await enterPitch(value);
  else if (name === 'rest') { await setDuration(duration); await view.makeRest(); view.tracker.moveSelectionRight(); }
  else if (name === 'undo') await view.undo();
  else if (name === 'dot') await view.batchDurationOperation('dotDuration');
  else if (name === 'triplet') await view.makeTuplet({numNotes:3,notesOccupied:2,ratioed:false,bracketed:true});
  else if (name === 'sharp') await view.transposeSelections(1);
  else if (name === 'flat') await view.transposeSelections(-1);
  else if (name === 'up') await view.transposeSelections(12);
  else if (name === 'down') await view.transposeSelections(-12);
  else if (name === 'accent' || name === 'staccato') await view.toggleArticulation(name,'SmoArticulation');
  else if (name === 'tie') await view.tie();
  else if (name === 'slur') await view.addSlur();
  else if (name === 'dynamic') {
    const selection = view.tracker.selections[0];
    if (!selection?.note) throw new Error('Select a note or rest first.');
    for (const mod of [...selection.note.getModifiers('SmoDynamicText')]) await view.removeDynamic(mod);
    if (value) await view.addDynamic(selection,new Smo.SmoDynamicText({...Smo.SmoDynamicText.defaults,text:value}));
  }
  else if (name === 'direction') {
    const selection = view.tracker.selections[0];
    if (!selection?.note) throw new Error('Select a note or rest first.');
    const existing = selection.note.getAnnotations()[0];
    if (!value && existing) await view.removeAnnotation(selection.selector,existing);
    else if (value) await view.addOrUpdateAnnotation(selection.selector,new Smo.SmoLyric({
      ...Smo.SmoLyric.defaults,parser:Smo.SmoLyric.parsers.annotation,text:value,verse:existing?.verse || 0
    }));
  }
  else if (name === 'reset') await view.changeScore(compact(parseXml(blankXml(currentContext))));
  else if (name === 'xml') await view.changeScore(compact(parseXml(value)));
  else if (name === 'context') {
    currentContext = value;
    const xml = new DOMParser().parseFromString(snapshot().musicxml, 'application/xml');
    const template = new DOMParser().parseFromString(blankXml(value), 'application/xml');
    const first = xml.querySelector('part measure');
    const old = first.querySelector('attributes');
    const attributes = template.querySelector('attributes');
    // Keep original duration units when changing the notation context.
    if (old?.querySelector('divisions')) attributes.querySelector('divisions').textContent = old.querySelector('divisions').textContent;
    if (old) old.replaceWith(xml.importNode(attributes,true));
    else first.prepend(xml.importNode(attributes,true));
    xml.querySelector('part-name').textContent = value.instrument || 'Part';
    await view.changeScore(compact(parseXml(new XMLSerializer().serializeToString(xml))));
  }
  await view.renderer.updatePromise();
  changed();
  document.getElementById('score-root').focus();
}

function stop() {
  playbackNodes.forEach(node => {try{node.stop();}catch{ /* Already stopped. */ }});
  playbackNodes = [];
}

async function play() {
  stop();
  audioContext ||= new AudioContext();
  await audioContext.resume();
  const doc = new DOMParser().parseFromString(snapshot().musicxml,'application/xml');
  let seconds = audioContext.currentTime+.05, divisions=16;
  for (const measure of doc.querySelectorAll('part:first-of-type > measure')) {
    divisions = Number(measure.querySelector('divisions')?.textContent || divisions);
    for (const note of measure.querySelectorAll(':scope > note')) {
      const length = Number(note.querySelector('duration')?.textContent || 0) / divisions * .5;
      const pitch = note.querySelector('pitch');
      if (pitch) {
        const steps = {C:0,D:2,E:4,F:5,G:7,A:9,B:11};
        const midi = (Number(pitch.querySelector('octave').textContent)+1)*12+
          steps[pitch.querySelector('step').textContent]+Number(pitch.querySelector('alter')?.textContent || 0)+Number(currentContext.transpose);
        const oscillator = audioContext.createOscillator(), gain = audioContext.createGain();
        oscillator.type = 'triangle'; oscillator.frequency.value = 440*2**((midi-69)/12);
        gain.gain.setValueAtTime(.0001,seconds); gain.gain.exponentialRampToValueAtTime(.14,seconds+.015);
        gain.gain.exponentialRampToValueAtTime(.0001,seconds+Math.max(.025,length*.95));
        oscillator.connect(gain).connect(audioContext.destination);
        oscillator.start(seconds); oscillator.stop(seconds+Math.max(.03,length)); playbackNodes.push(oscillator);
      }
      if (!note.querySelector('chord')) seconds += length;
    }
  }
}

window.addEventListener('message', event => {
  if (event.origin !== location.origin || event.source !== parent) return;
  const data = event.data;
  if (data.type === 'editor-check-ready') { tell('editor-ready'); return; }
  busy = busy.then(async () => {
    if (data.type === 'editor-load') await load(data);
    if (data.type === 'editor-action') await action(data.action,data.value);
    if (data.type === 'editor-export') tell('editor-snapshot',{request:data.request,...snapshot()});
    if (data.type === 'editor-play') await play();
    if (data.type === 'editor-focus') document.getElementById('score-root').focus();
  }).catch(error => tell('editor-error',{message:String(error.message || error), request:data.request}));
});

window.addEventListener('keydown', event => {
  if ((event.ctrlKey || event.metaKey) && event.key === 'Enter' || event.altKey && ['KeyS','KeyU','KeyB'].includes(event.code)) {
    event.preventDefault(); tell('queue-shortcut',{key:event.key,code:event.code,alt:event.altKey}); return;
  }
  if (!view) return;
  let command, value;
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') command='undo';
  else if (event.ctrlKey || event.metaKey || event.altKey) return;
  else if (/^[a-g]$/i.test(event.key)) {command='pitch';value=event.key.toLowerCase();}
  else if (/^[1-5]$/.test(event.key)) {command='duration';value=[16384,8192,4096,2048,1024][Number(event.key)-1];}
  else if (event.key === 'r') command='rest';
  else if (event.key === '.') command='dot';
  else if (event.key === 't') command='triplet';
  else if (event.key === '+' || event.key === '=') command='sharp';
  else if (event.key === '-') command='flat';
  else if (event.key === 'ArrowUp') command='up';
  else if (event.key === 'ArrowDown') command='down';
  else if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
    event.preventDefault();
    const direction = event.key === 'ArrowRight' ? 'Right' : 'Left';
    view.tracker[(event.shiftKey ? 'growSelection' : 'moveSelection')+direction](); return;
  } else if (event.key === ' ') {event.preventDefault(); play().catch(error=>tell('editor-error',{message:error.message}));return;}
  if (command) {event.preventDefault(); busy=busy.then(()=>action(command,value)).catch(error=>tell('editor-error',{message:error.message}));}
});
if (typeof Smo === 'undefined') tell('editor-error',{message:'Smoosic is missing. Run npm install in apps/bar_review.'});
else tell('editor-ready');
