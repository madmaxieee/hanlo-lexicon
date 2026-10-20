const $ = id => document.getElementById(id);
const norm = text => text.normalize('NFC').toLowerCase();
const esc = text => String(text).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const byKey = new Map(data.groups.map(group => [group.key, group]));
const tracked = new Set(data.tracked_preferred_forms);
const unparseable = new Set(data.unparseable_forms);
const storageKey = 'hanlo-review:v1:' + data.issue + ':' + data.corpus_sha256 + ':' + data.moe?.snapshot;
let state = {ignored: data.known_forms, decisions: {}};
let storageAvailable = true;
try {
  const saved = JSON.parse(localStorage.getItem(storageKey) || 'null');
  if (saved && Array.isArray(saved.ignored) && saved.decisions) state = saved;
} catch { storageAvailable = false; }
let ignored = new Set(state.ignored);

function reconcileHandledRequests() {
  for(const resolution of data.handled_custom_requests||[]) {
    const item=state.decisions[resolution.anchor_key];
    const sameFields=['preferred_form','hanji','reading'].every(field=>
      (item?.['custom_'+field]||'').trim()===(resolution.request_fields?.[field]||'').trim());
    if(sameFields && item?.custom_handling?.trim()===resolution.prompt.trim()) {
      item.custom_handling='';
      item.custom_preferred_form='';item.custom_hanji='';item.custom_reading='';
      item.approved=false;
      item.handled_custom_request={prompt:resolution.prompt,entry_id:resolution.entry_id};
    }
  }
}

function save() {
  state.ignored = [...ignored].sort();
  try { localStorage.setItem(storageKey, JSON.stringify(state)); }
  catch { storageAvailable = false; }
}
function isIgnored(group) { return group.dedup_lookup_forms.some(form => ignored.has(form)); }
function excluded(group) { return isIgnored(group) || tracked.has(group.key) || unparseable.has(group.key); }
function pureRomanized(text) {
  return typeof text==='string' && /\p{Script=Latin}/u.test(text)
    && /^[\p{Script=Latin}\p{M}\p{Nd}\-’' ]+$/u.test(text);
}
function sourceAnchorEligible(group) {
  return group.parser_compatible===true && pureRomanized(group.display||group.key) && pureRomanized(group.normalized_tl);
}
function regularMoeWord(word) {
  return word.id.startsWith('moe:') && word.readings.some(reading=>
    (reading.references||[]).some(ref=>ref.source?.sheet==='詞目'));
}
function decision(group) {
  if(!Object.hasOwn(state.decisions,group.key))state.decisions[group.key] = {preferred_form: group.normalized_forms?.[0] || group.display,
    word_id: '', canonical_choice_id: '', alternate_choice_ids: [], identity_note: '', custom_handling: '', approved: false};
  const item=state.decisions[group.key];
  item.custom_handling ??= '';
  item.custom_preferred_form ??= '';item.custom_hanji ??= '';item.custom_reading ??= '';
  item.moe_matches_collapsed ??= false;
  item.import_mode ??= (!(group.review_words||[]).length && sourceAnchorEligible(group))?'source_anchor':'moe';
  const words = group.review_words || [];
  if (item.import_mode==='moe' && !item.word_id) {
    const regular=words.filter(regularMoeWord);
    if(regular.length===1)item.word_id=regular[0].id;
    else if(words.length===1)item.word_id=words[0].id;
  }
  const word = words.find(word => word.id === item.word_id);
  if (item.import_mode==='moe' && !item.canonical_choice_id && word) {
    const detected=word.readings.filter(reading=>reading.detected);
    const primary=word.readings.filter(reading=>(reading.references||[]).some(ref=>ref.source?.sheet==='詞目'))
      .sort((a,b)=>(a.primary_index??Infinity)-(b.primary_index??Infinity));
    const selected=primary[0]||(detected.length===1?detected[0]:word.readings.length===1?word.readings[0]:null);
    if(selected) {
      const originalForm=group.normalized_forms?.[0]||group.display;
      if(detected.length===1&&item.preferred_form===originalForm&&selected.id!==detected[0].id) {
        try {item.preferred_form=writtenForm(item.preferred_form,detected[0].reading,selected.reading);}catch{}
      }
      item.canonical_choice_id=selected.id;
    }
  }
  return item;
}
function choices(group) {
  const item = decision(group), word = (group.review_words || []).find(word => word.id === item.word_id);
  return {item, word, canonical: word?.readings.find(reading => reading.id === item.canonical_choice_id)};
}
function outputForms(group) {
  const {item, word, canonical} = choices(group);
  if (item.import_mode==='source_anchor') {
    if(!sourceAnchorEligible(group)||!pureRomanized(item.preferred_form.trim()))throw Error('A pure romanized spelling and normalized TL reading are required.');
    return [{form:item.preferred_form.trim(),reading:group.normalized_tl}];
  }
  if (!canonical) return [];
  return [canonical.id, ...item.alternate_choice_ids].map(id => {
    const option = word.readings.find(reading => reading.id === id);
    if (!option) throw Error('Choose a reading from the selected MOE entry.');
    return {form: writtenForm(item.preferred_form.trim(), canonical.reading, option.reading), reading: option.reading};
  });
}
function approvable(group) {
  const {item, word, canonical} = choices(group);
  if (!item.preferred_form.trim() || hasCustomRequest(item) || isIgnored(group) || unparseable.has(group.key)
    || (tracked.has(group.key) && !item.identity_note.trim())) return false;
  try { outputForms(group); } catch { return false; }
  if (item.import_mode==='source_anchor') return sourceAnchorEligible(group) && !item.word_id && !item.canonical_choice_id && !item.alternate_choice_ids.length;
  return !!(item.import_mode==='moe' && word && canonical
    && item.alternate_choice_ids.every(id => id !== canonical.id && word.readings.some(reading => reading.id === id)));
}
function countUnion(groups) {
  const ranges = {};
  for (const group of groups) for (const row of group.occurrences)
    (ranges[row.document_id] ??= []).push([row.context_start, row.context_end]);
  let count = 0;
  for (const list of Object.values(ranges)) {
    list.sort((a,b) => a[0]-b[0]); let start=-1, end=-1;
    for (const [a,b] of list) { if(a<=end) end=Math.max(end,b); else {if(start>=0)count+=end-start;start=a;end=b;} }
    if(start>=0) count+=end-start;
  }
  return count;
}
function snippet(row) {
  const text=Array.from(row.snippet), a=row.anchor_start-row.context_start, b=row.anchor_end-row.context_start;
  return esc(text.slice(0,a).join(''))+'<mark>'+esc(text.slice(a,b).join(''))+'</mark>'+esc(text.slice(b).join(''));
}
function source(row) {
  return '<div class="muted"><a target="_blank" rel="noreferrer" href="'+esc(row.url)+'">'+esc(row.title)+'</a> · article text line '+row.line+'</div>';
}
function collapseRelated(records) {
  const cards=new Map();
  for(const record of records) {
    const reading=record.matched_reading || record.reading, key=norm(record.headword)+'\u0000'+norm(reading);
    if(!cards.has(key)) cards.set(key,{headword:record.headword,reading,definitions:[],references:[],record_ids:[]});
    const card=cards.get(key);
    for(const definition of record.definitions) if(definition&&!card.definitions.includes(definition))card.definitions.push(definition);
    const ref={source:record.source,column:record.column,record_id:record.record_id,definitions:record.definitions};
    if(!card.references.some(old=>JSON.stringify(old)===JSON.stringify(ref)))card.references.push(ref);
    if(record.record_id&&!card.record_ids.includes(record.record_id))card.record_ids.push(record.record_id);
  }
  return [...cards.values()];
}
function moeCard(card) {
  return '<div class="occurrence moe-card"><strong>'+esc(card.headword)+'</strong> · '+esc(card.reading)+
    '<div>'+esc(card.definitions.join('；'))+'</div><div class="muted">MOE '+esc(card.record_ids.join(', ')||'(no numeric ID)')+'</div>'+
    '<details><summary>Source references ('+card.references.length+')</summary>'+card.references.map(ref=>
      '<div class="muted">'+esc(ref.source.snapshot)+' · '+esc(ref.source.sheet)+' row '+ref.source.row+' · '+esc(ref.column)+' · MOE '+esc(ref.record_id||'—')+'</div>').join('')+'</details></div>';
}
function moeReadingRole(reading) {
  const sheets=[...new Set((reading.references||[]).map(ref=>ref.source?.sheet).filter(Boolean))];
  if(sheets.includes('詞目'))return 'MOE primary'+(reading.primary_count>1?' '+reading.primary_index:'')+' (詞目)';
  if(sheets.includes('又唸作'))return 'MOE alternate (又唸作)';
  if(sheets.includes('語音差異'))return 'MOE dialect (語音差異)';
  if(sheets.includes('合音唸作'))return 'MOE contraction (合音唸作)';
  if(sheets.includes('俗唸作'))return 'MOE colloquial (俗唸作)';
  return 'MOE reading'+(sheets.length?' ('+sheets.join(', ')+')':'');
}
function importEditor(group) {
  const {item, word, canonical}=choices(group), words=group.review_words||[];
  const eligible=sourceAnchorEligible(group);
  const modeSelect=eligible&&words.length?'<label>Import evidence <select class="mode-select"><option value="moe" '+(item.import_mode==='moe'?'selected':'')+'>MOE entry and readings</option><option value="source_anchor" '+(item.import_mode==='source_anchor'?'selected':'')+'>Article anchor and normalized TL</option></select></label>':'';
  if(item.import_mode==='source_anchor'&&eligible) return '<details class="import-editor" data-key="'+esc(group.key)+'"><summary>Article anchor import'+(item.approved?' · approved':'')+'</summary>'+modeSelect+
    '<label>Preferred spelling <input type="text" class="preferred-input" value="'+esc(item.preferred_form)+'"></label>'+
    '<div>Filing TL reading: <strong>'+esc(group.normalized_tl)+'</strong></div>'+
    '<div class="written-form-preview"><strong>'+esc(item.preferred_form)+'</strong> · '+esc(group.normalized_tl)+'</div>'+
    '<label>Distinct word note (optional) <input type="text" class="identity-input" value="'+esc(item.identity_note)+'"></label>'+
    '<p class="muted">Approve this romanized form and reading using the article as evidence. No MOE match is required. New entries remain imported; offline LKK/MOE and existing-entry checks still run.</p></details>';
  if(!words.length) return '<p class="muted">A mixed or unrecognized anchor needs a supported reading or custom handling before import.</p>';
  const orderedWords=[...words].sort((a,b)=>Number(regularMoeWord(b))-Number(regularMoeWord(a)));
  const options='<option value="">Choose the MOE entry / meaning</option>'+orderedWords.map(option=>{
    const refs=option.readings.flatMap(reading=>reading.references||[]);
    const label=option.record_id?'MOE '+option.record_id:[...new Set(refs.map(ref=>ref.source.sheet+' row '+ref.source.row))].join(', ');
    return '<option value="'+esc(option.id)+'" '+(option.id===item.word_id?'selected':'')+'>'+esc(option.headword)+' · '+esc(label||option.id)+'</option>';
  }).join('');
  const readings=word?.readings||[];
  let preview='';
  try { preview=outputForms(group).map(row=>'<div><strong>'+esc(row.form)+'</strong> · '+esc(row.reading)+'</div>').join(''); }
  catch(error) { preview='<div class="muted">'+esc(error.message)+'</div>'; }
  const primary='<option value="">Choose the filing TL reading</option>'+readings.map(reading=>'<option value="'+reading.id+'" '+(reading.id===item.canonical_choice_id?'selected':'')+'>'+esc(reading.reading)+' · '+esc(reading.headword)+' · '+esc(moeReadingRole(reading))+(reading.id===item.canonical_choice_id?' · selected filing':'')+(reading.detected?' · anchor match':' · additional MOE reading')+'</option>').join('');
  return '<details class="import-editor" data-key="'+esc(group.key)+'"><summary>Choose spelling and import readings'+(item.approved?' · approved':'')+'</summary>'+modeSelect+
    '<label>Preferred spelling <input type="text" class="preferred-input" value="'+esc(item.preferred_form)+'"></label>'+
    '<label>MOE entry / meaning <select class="word-select">'+options+'</select></label>'+
    '<label>Filing TL reading <select class="canonical-select">'+primary+'</select></label>'+
    '<div>Alternate readings from this same MOE entry</div>'+readings.filter(reading=>reading.id!==canonical?.id).map(reading=>
      '<label class="reading-alt"><input type="checkbox" class="alternate-box" data-choice="'+reading.id+'" '+(item.alternate_choice_ids.includes(reading.id)?'checked':'')+'> '+esc(reading.reading)+' · '+esc(moeReadingRole(reading))+(reading.detected?'':' · additional MOE reading')+'</label>').join('')+
    '<div class="written-form-preview"><strong>Written forms to import</strong>'+preview+'</div>'+
    '<label>Distinct word note (optional) <input type="text" class="identity-input" value="'+esc(item.identity_note)+'"></label>'+
    '<p class="muted">Alternate outputs preserve Han characters and change the romanized syllables. Keep readings of one word together. For an existing word, update its entry; use the distinct word note only for an unrelated homograph. New records start as imported.</p></details>';
}
function hasCustomRequest(item) {
  return ['custom_handling','custom_preferred_form','custom_hanji','custom_reading'].some(field=>item[field]?.trim());
}
function customRequests() {
  return Object.entries(state.decisions).filter(([key,item])=>hasCustomRequest(item)).map(([key,item])=>{
    const request={anchor_key:key,prompt:(item.custom_handling||'').trim(),anchor_present:byKey.has(key)};
    if(['custom_preferred_form','custom_hanji','custom_reading'].some(field=>item[field]?.trim())) {
      request.preferred_form=(item.custom_preferred_form||'').trim().normalize('NFC');
      request.reading=(item.custom_reading||'').trim().normalize('NFC');
      if(item.custom_hanji?.trim())request.hanji=item.custom_hanji.trim().normalize('NFC');
    }
    return request;
  });
}
function customEditor(group) {
  const item=decision(group);
  const structured=!!(item.custom_preferred_form||item.custom_hanji||item.custom_reading);
  return '<details class="custom-handling-editor" data-key="'+esc(group.key)+'"'+(hasCustomRequest(item)?' open':'')+'><summary>Custom handling'+(hasCustomRequest(item)?' · requested':'')+'</summary>'+
    '<label>Preferred form <input class="custom-preferred-form-input" type="text" value="'+esc(item.custom_preferred_form)+'" placeholder="食飯"></label>'+
    '<label>Hanji (optional) <input class="custom-hanji-input" type="text" value="'+esc(item.custom_hanji)+'" placeholder="食飯"></label>'+
    '<label>Reading (TL) <input class="custom-reading-input" type="text" value="'+esc(item.custom_reading)+'" placeholder="tsia̍h-pn̄g"></label>'+
    (structured&&(!item.custom_preferred_form.trim()||!item.custom_reading.trim())?'<p class="muted">Enter both a preferred form and reading. Hanji is optional.</p>':'')+
    '<label>Additional instructions (optional)<textarea class="custom-handling-input" placeholder="For example: split these meanings or check a missing reading.">'+esc(item.custom_handling)+'</textarea></label>'+
    (item.handled_custom_request?'<div class="muted">Previous request handled by entry '+esc(item.handled_custom_request.entry_id)+': '+esc(item.handled_custom_request.prompt)+'</div>':'')+
    '<p class="muted">Use preferred form and reading together; Hanji is optional and does not claim MOE inclusion. Saved locally and included in Export review.json for source and duplicate checks. Custom requests pause automatic import until reviewed.</p></details>';
}
function moePanel(group) {
  const cards=group.moe_cards||[], related=group.moe_related||[], preferred=group.preferred_matches||[];
  return (preferred.length?'<details><summary>Final preferred-form matches ('+preferred.length+')</summary>'+preferred.map(record=>'<div class="occurrence">Entry '+record.id+' · <strong>'+esc(record.preferred_form)+'</strong><div>Matched written form: '+esc((record.matched_written_forms||[record.preferred_form]).join(', '))+'</div>'+(record.hanji_forms?.length?'<div>Hanji: '+esc(record.hanji_forms.join(', '))+'</div>':'')+'<div class="muted">'+esc(record.path)+'</div></div>').join('')+'</details>':'')+
    customEditor(group)+importEditor(group)+(cards.length?'<details class="anchor-matches" data-key="'+esc(group.key)+'"'+(decision(group).moe_matches_collapsed?'':' open')+'><summary>MOE anchor match ('+cards.length+')</summary>'+cards.map(moeCard).join('')+'</details>':'')+
    (related.length?'<details class="moe-related" data-key="'+esc(group.key)+'"><summary>MOE related entries</summary><div class="moe-results"></div></details>':'');
}
function render() {
  const active=data.groups.filter(group=>!excluded(group)), total=data.baseline.source_characters;
  const compact=active.reduce((sum,group)=>sum+Array.from(group.occurrences[0].snippet).length,0), union=countUnion(active);
  $('stats').innerHTML=[['Articles',data.baseline.article_count],['Candidate groups',active.length],['Occurrences',active.reduce((sum,group)=>sum+group.occurrences.length,0)],['Compact text reduction',((1-compact/total)*100).toFixed(1)+'%'],['All-context reduction',((1-union/total)*100).toFixed(1)+'%']].map(([label,value])=>'<div class="card"><div class="number">'+value+'</div>'+label+'</div>').join('');
  const query=norm($('search').value), shown=data.groups.filter(group=>(!excluded(group)||$('showKnown').checked)&&(!query||norm(group.key+' '+(group.normalized_tl||'')+' '+(group.moe_related||[]).map(record=>record.headword+' '+record.matched_reading).join(' ')+' '+group.occurrences.map(row=>row.snippet+' '+row.title).join(' ')).includes(query)));
  const approved=data.groups.filter(group=>decision(group).approved&&approvable(group)).length;
  $('count').textContent=shown.length+' visible groups · '+ignored.size+' ignored forms · '+approved+' approved imports · '+customRequests().length+' custom requests · '+compact.toLocaleString()+' compact snippet characters / '+total.toLocaleString()+' source characters · '+union.toLocaleString()+' source characters covered by all contexts';
  $('review-status').textContent=(storageAvailable?'Decisions save locally in this browser. ':'Local saving is unavailable; export decisions before closing. ')+approved+' ready approvals and '+customRequests().length+' custom requests. Export review.json to hand them to the import script; nothing is imported by this page.';
  $('rows').innerHTML=shown.map(group=>{
    const row=group.occurrences[0], item=decision(group), omit=excluded(group);
    return '<tr class="'+(omit?'known':'')+'" data-key="'+esc(group.key)+'"><td><input class="ignore-box" type="checkbox" data-key="'+esc(group.key)+'" aria-label="Ignore '+esc(group.key)+'" '+(omit?'checked ':'')+(tracked.has(group.key)||unparseable.has(group.key)?'disabled':'')+'>'+(tracked.has(group.key)?'<br><span class="tag">Tracked form</span>':'')+(unparseable.has(group.key)?'<br><span class="tag">Parser did not recognize</span>':'')+'</td><td><strong>'+esc(group.display)+'</strong>'+(group.kind==='moe_context'?'<br><span class="tag">MOE-backed mixed form</span>':'')+(group.normalized_tl&&group.normalized_tl!==group.key?'<br><span class="tag">TL lookup: '+esc(group.normalized_tl)+'</span>':'')+'<br>'+group.occurrences.length+' occurrences<br>'+group.article_count+' articles'+
      '<label class="approve-label '+(item.approved?'approval-good':'')+'"><input class="approve-box" data-key="'+esc(group.key)+'" type="checkbox" aria-label="Approve import '+esc(group.key)+'" '+(item.approved&&approvable(group)?'checked ':'')+(approvable(group)?'':'disabled')+'> Approve import</label></td><td><div class="snippet">'+snippet(row)+'</div>'+source(row)+moePanel(group)+'<details><summary>Full clause and all '+group.occurrences.length+' occurrences</summary>'+group.occurrences.map(row=>'<div class="occurrence"><div class="snippet">'+snippet(row)+'</div>'+source(row)+'<div>'+esc(row.clause)+'</div></div>').join('')+'</details></td></tr>';
  }).join('');
  document.querySelectorAll('.anchor-matches').forEach(detail=>detail.ontoggle=()=>{decision(byKey.get(detail.dataset.key)).moe_matches_collapsed=!detail.open;save();});
  document.querySelectorAll('.moe-related').forEach(detail=>detail.ontoggle=()=>{if(detail.open&&!detail.dataset.loaded){const cards=collapseRelated(byKey.get(detail.dataset.key).moe_related);detail.querySelector('.moe-results').innerHTML=cards.map(moeCard).join('');detail.dataset.loaded='yes';}});
  document.querySelectorAll('.ignore-box').forEach(box=>box.onchange=()=>{
    box.checked?ignored.add(box.dataset.key):ignored.delete(box.dataset.key);
    if(box.checked)decision(byKey.get(box.dataset.key)).approved=false;
    $('known').value=[...ignored].sort().join(', ');save();render();
  });
  document.querySelectorAll('.approve-box').forEach(box=>box.onchange=()=>{decision(byKey.get(box.dataset.key)).approved=box.checked;save();render();});
  document.querySelectorAll('.custom-handling-editor').forEach(editor=>{
    const item=decision(byKey.get(editor.dataset.key));
    for(const [selector,field] of [['.custom-handling-input','custom_handling'],
      ['.custom-preferred-form-input','custom_preferred_form'],['.custom-hanji-input','custom_hanji'],
      ['.custom-reading-input','custom_reading']])
      editor.querySelector(selector).onchange=event=>{
        item[field]=event.target.value.normalize('NFC');item.approved=false;save();render();
      };
  });
  document.querySelectorAll('.import-editor').forEach(editor=>{
    const group=byKey.get(editor.dataset.key), item=decision(group);
    function update(callback){callback();item.approved=false;save();const key=group.key;render();document.querySelectorAll('.import-editor').forEach(node=>{if(node.dataset.key===key)node.open=true;});}
    editor.querySelector('.preferred-input').onchange=event=>update(()=>item.preferred_form=event.target.value.normalize('NFC'));
    editor.querySelector('.identity-input').onchange=event=>update(()=>item.identity_note=event.target.value);
    const modeSelect=editor.querySelector('.mode-select');
    if(modeSelect)modeSelect.onchange=event=>update(()=>{item.import_mode=event.target.value;item.word_id='';item.canonical_choice_id='';item.alternate_choice_ids=[];});
    const wordSelect=editor.querySelector('.word-select');
    if(wordSelect)wordSelect.onchange=event=>update(()=>{item.word_id=event.target.value;item.canonical_choice_id='';item.alternate_choice_ids=[];});
    const canonicalSelect=editor.querySelector('.canonical-select');
    if(canonicalSelect)canonicalSelect.onchange=event=>update(()=>{
      const readings=(group.review_words||[]).find(word=>word.id===item.word_id)?.readings||[];
      const previous=readings.find(reading=>reading.id===item.canonical_choice_id)||readings.find(reading=>reading.detected);
      const next=readings.find(reading=>reading.id===event.target.value);
      if(previous&&next)try {item.preferred_form=writtenForm(item.preferred_form,previous.reading,next.reading);}catch{}
      item.canonical_choice_id=event.target.value;item.alternate_choice_ids=item.alternate_choice_ids.filter(id=>id!==event.target.value);
    });
    editor.querySelectorAll('.alternate-box').forEach(box=>box.onchange=()=>update(()=>{item.alternate_choice_ids=item.alternate_choice_ids.filter(id=>id!==box.dataset.choice);if(box.checked)item.alternate_choice_ids.push(box.dataset.choice);}));
  });
  save();
}
function download(filename,value) {
  const link=document.createElement('a'), url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)+'\n'],{type:'application/json'}));
  link.href=url;link.download=filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function reviewExport() {
  reconcileHandledRequests();
  const approvals=data.groups.filter(group=>decision(group).approved&&approvable(group)).map(group=>({anchor_key:group.key,approved:true,...decision(group),...(decision(group).import_mode==='source_anchor'?{source_reading:group.normalized_tl}:{})}));
  return {schema_version:1,issue:data.issue,corpus_sha256:data.corpus_sha256,groups_sha256:data.review_groups_sha256,
    moe_snapshot:data.moe?.snapshot,ignored_forms:[...ignored].sort(),approvals,custom_requests:customRequests(),decisions:state.decisions};
}
$('title').textContent='TSBP issue '+data.issue+' · vocabulary review pilot';
$('known').value=[...ignored].sort().join(', ');
$('policy').textContent='Nested and overlapping multi-syllable anchors are listed. A single-syllable match is shown only where no longer MOE or tracked-word match contains it. Identical article/span matches appear once; text coverage counts overlaps once. Exclusions apply to each final written form. Matches remain candidates for human review.';
$('normalization').textContent='TL lookup spellings preserve original source text. Identical MOE headword/reading cards are merged while all IDs, definitions and source references remain available.';
$('moe-policy').textContent='Nested and overlapping multi-syllable anchors are listed separately; contained single-syllable matches are suppressed. Pure romanized anchors can use the article and displayed normalized TL reading without an MOE match. For dictionary-backed imports, choose one MOE entry / meaning, its filing reading and any alternates. Additional readings are sourced from that same MOE entry, even when they were not the detected anchor reading.';
$('context-policy').textContent='Exact context exclusions: '+data.context_exclusions.phrases.join(', ')+' · '+data.context_exclusions.skipped_anchor_occurrences+' anchor occurrences omitted.';
$('apply').onclick=()=>{ignored=new Set($('known').value.split(/[,，\n]+/).map(text=>norm(text.trim())).filter(Boolean));for(const group of data.groups)if(isIgnored(group))decision(group).approved=false;save();render();};
$('search').oninput=render;$('showKnown').onchange=render;
$('download').onclick=()=>download('ignored-forms.json',[...ignored].sort());
$('export-review').onclick=()=>download('review.json',reviewExport());
$('load-review').onclick=()=>$('review-file').click();
$('review-file').onchange=async event=>{
  try {
    const bundle=JSON.parse(await event.target.files[0].text());
    if(bundle.schema_version!==1||bundle.corpus_sha256!==data.corpus_sha256||bundle.issue!==data.issue)throw Error('This review belongs to another corpus or issue.');
    state={ignored:bundle.ignored_forms||data.known_forms,decisions:bundle.decisions||{}};
    for(const approval of bundle.approvals||[])state.decisions[approval.anchor_key]=approval;
    for(const request of bundle.custom_requests||[]){
      const group=byKey.get(request.anchor_key);
      const item=group?decision(group):(state.decisions[request.anchor_key]??={});
      item.custom_handling=request.prompt;item.approved=false;
      item.custom_preferred_form=request.preferred_form||'';
      item.custom_hanji=request.hanji||'';item.custom_reading=request.reading||'';
    }
    ignored=new Set(state.ignored);reconcileHandledRequests();save();render();
  } catch(error) {$('review-status').textContent='Could not load review: '+error.message;}
};
reconcileHandledRequests();
save();
render();
