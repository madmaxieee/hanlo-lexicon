const $ = id => document.getElementById(id);
const norm = text => text.normalize('NFC').toLowerCase();
const esc = text => String(text).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const byKey = new Map(data.groups.map(group => [group.key, group]));
const tracked = new Set([...data.tracked_preferred_forms,
  ...data.groups.filter(group=>group.preferred_matches?.length).map(group=>group.key)]);
const unparseable = new Set(data.unparseable_forms);
const machineRejected = new Set(data.groups.filter(group=>group.exclusion_reason==='machine_rejected').map(group=>group.key));
const storageKey = 'hanlo-review:v1:' + data.issue + ':' + data.corpus_sha256 + ':' + data.moe?.snapshot;
let state = {ignored: data.known_forms, ignored_segments:data.ignored_segments||[], decisions: {}};
let storageAvailable = true;
try {
  const saved = JSON.parse(localStorage.getItem(storageKey) || 'null');
  if (saved && Array.isArray(saved.ignored) && saved.decisions) state = saved;
} catch { storageAvailable = false; }
function editableIgnores(forms) {return new Set(forms.filter(form=>!tracked.has(form)));}
let ignored = editableIgnores(state.ignored);
let ignoredSegments = new Set(state.ignored_segments||data.ignored_segments||[]);
// Rebase local edits onto persisted settings when a rerun embeds a new snapshot.
if(data.segment_settings_sha256&&data.segment_settings_sha256!==state.segment_settings_sha256) {
  const previous=new Set(state.segment_settings_base||[]);
  const removed=new Set([...previous].filter(id=>!ignoredSegments.has(id)));
  const added=[...ignoredSegments].filter(id=>!previous.has(id));
  ignoredSegments=new Set([...(data.ignored_segments||[]).filter(id=>!removed.has(id)),...added]);
  state.segment_settings_base=data.ignored_segments||[];
  state.segment_settings_sha256=data.segment_settings_sha256;
}

const sectionPageSize=20;
let sectionPage=0;
const occurrenceLimits=new Map();
function occurrenceRows(group,rejected=false) {
  const rows=rejected?(group.machine_rejected_occurrences||[]):group.occurrences;
  const key=disclosureId(group.key,rejected?'rejected':'occurrences');
  const limit=occurrenceLimits.get(key)||25;
  return rows.slice(0,limit).map(row=>'<div class="occurrence"><div class="snippet">'+snippet(row)+'</div>'+source(row)+screeningNote(row)+coverageNote(row)+(segmentIgnored(row)?'<div class="muted">Ignored with this Roman-text segment</div>':'')+'<div>'+esc(row.clause||'')+'</div></div>').join('')+
    (rows.length>limit?'<button type="button" class="more-occurrences">Show next '+Math.min(25,rows.length-limit)+' occurrences</button>':'');
}
function loadDisclosure(detail) {
  if(detail.dataset.loaded||!detail.open)return;
  const group=byKey.get(detail.dataset.key),panel=detail.dataset.panel;
  if(panel==='related')detail.querySelector('.moe-results').innerHTML=collapseRelated(group.moe_related).map(moeCard).join('');
  else if(panel==='occurrences'||panel==='rejected') {
    const target=detail.querySelector('.occurrence-results');
    target.innerHTML=occurrenceRows(group,panel==='rejected');
    const more=target.querySelector('.more-occurrences');
    if(more)more.onclick=()=>{
      const key=disclosureId(group.key,panel);occurrenceLimits.set(key,(occurrenceLimits.get(key)||25)+25);
      delete detail.dataset.loaded;loadDisclosure(detail);
    };
  } else return;
  detail.dataset.loaded='yes';
}
// Disclosure state is presentation state, independent of saved word decisions.
state.disclosures ??= {};
function disclosureId(key, panel) {return JSON.stringify([key,panel]);}
function panelAttrs(group, panel, className, defaultOpen=false) {
  const id=disclosureId(group.key,panel), open=state.disclosures[id]??defaultOpen;
  return 'class="review-disclosure '+className+'" data-key="'+esc(group.key)+'" data-panel="'+panel+'"'+(open?' open':'');
}
function captureDisclosures() {
  document.querySelectorAll('.review-disclosure').forEach(detail=>{
    state.disclosures[disclosureId(detail.dataset.key,detail.dataset.panel)]=detail.open;
  });
}
function setPanelOpen(key,panel,open) {
  state.disclosures[disclosureId(key,panel)]=open;
  document.querySelectorAll('.review-disclosure').forEach(detail=>{
    if(detail.dataset.key===key&&detail.dataset.panel===panel)detail.open=open;
  });
}
function rowTriggers(row) {
  return row.source_triggers?.length?row.source_triggers:[{
    anchor:row.base_anchor||row.anchor,
    anchor_start:row.base_anchor_start??row.anchor_start,
    anchor_end:row.base_anchor_end??row.anchor_end,
  }];
}
function triggerId(document,trigger) {return JSON.stringify([document,trigger.anchor_start,trigger.anchor_end]);}
function segmentIgnored(row) {return rowTriggers(row).some(t=>ignoredSegments.has(triggerId(row.document_id,t)));}
function eligibleOccurrences(group) {return group.occurrences.filter(row=>!segmentIgnored(row)&&!row.tracked_coverage?.length);}
function sectionIgnored(section) {return section.anchors.some(anchor=>ignoredSegments.has(anchor.id));}
function setSegmentIgnored(section,ignore=true) {
  for(const anchor of section.anchors)ignore?ignoredSegments.add(anchor.id):ignoredSegments.delete(anchor.id);
  if(ignore)for(const {group} of section.matches)decision(group).approved=false;
  save();
}
function coverageNote(row) {
  const entries=(row.tracked_coverage||[]).flatMap(cover=>cover.entries||[]);
  return entries.length?'<div class="muted">Covered by '+entries.map(e=>'entry '+e.id+' · '+esc(e.preferred_form)).join(', ')+'</div>':'';
}
function reviewSections(groups,showExcluded=false) {
  const nodes=new Map(), records=[];
  function root(node) {if(node.parent!==node)node.parent=root(node.parent);return node.parent;}
  function join(a,b) {a=root(a);b=root(b);if(a!==b)b.parent=a;}
  for(const group of groups)for(const row of group.occurrences) {
    if(!showExcluded&&(segmentIgnored(row)||row.tracked_coverage?.length))continue;
    const triggers=rowTriggers(row), anchors=triggers.map(trigger=>{
      const id=triggerId(row.document_id,trigger);
      if(!nodes.has(id)) {
        const node={id,document:row.document_id,trigger,row};node.parent=node;nodes.set(id,node);
      }
      return nodes.get(id);
    });
    anchors.slice(1).forEach(node=>join(anchors[0],node));
    records.push({group,row,node:anchors[0]});
  }
  // Older packets may record a subquery rather than the original whole trigger.
  // Overlapping trigger positions still belong to the same local review section.
  const ordered=[...nodes.values()].sort((a,b)=>a.document.localeCompare(b.document)||a.trigger.anchor_start-b.trigger.anchor_start||a.trigger.anchor_end-b.trigger.anchor_end);
  let covering=null;
  for(const node of ordered) {
    if(covering&&covering.document===node.document&&node.trigger.anchor_start<covering.trigger.anchor_end) {
      join(covering,node);
      if(node.trigger.anchor_end>covering.trigger.anchor_end)covering=node;
    } else covering=node;
  }
  const sections=new Map();
  for(const node of nodes.values()) {
    const id=root(node).id;
    if(!sections.has(id))sections.set(id,{id,document:node.document,anchors:[],matches:new Map()});
    sections.get(id).anchors.push(node);
  }
  for(const {group,row,node} of records) {
    const section=sections.get(root(node).id);
    if(!section.matches.has(group.key))section.matches.set(group.key,{group,rows:[]});
    section.matches.get(group.key).rows.push(row);
  }
  const articles=new Map((data.article_inventory||[]).map((article,index)=>[article.id,index]));
  return [...sections.values()].map(section=>{
    section.anchors.sort((a,b)=>a.trigger.anchor_start-b.trigger.anchor_start||a.trigger.anchor_end-b.trigger.anchor_end);
    section.start=section.anchors[0].trigger.anchor_start;
    section.matches=[...section.matches.values()].sort((a,b)=>
      Math.max(...b.rows.map(r=>r.anchor_end-r.anchor_start))-Math.max(...a.rows.map(r=>r.anchor_end-r.anchor_start))||
      a.rows[0].anchor_start-b.rows[0].anchor_start||a.group.key.localeCompare(b.group.key));
    return section;
  }).sort((a,b)=>(articles.get(a.document)??Infinity)-(articles.get(b.document)??Infinity)||a.document.localeCompare(b.document)||a.start-b.start);
}
function sectionContext(section) {
  const rows=section.matches.flatMap(match=>match.rows), first=rows[0];
  const start=Math.min(...rows.map(row=>row.anchor_start),...section.anchors.map(a=>a.trigger.anchor_start));
  const end=Math.max(...rows.map(row=>row.anchor_end),...section.anchors.map(a=>a.trigger.anchor_end));
  const context=section.anchors.map(anchor=>data.reading_contexts?.[anchor.id]).find(c=>c&&c.context_start<=start&&c.context_end>=end);
  if(context)return context;
  const clause=rows.find(row=>row.clause&&row.clause_start<=start&&row.clause_end>=end);
  if(clause)return {snippet:clause.clause,context_start:clause.clause_start,context_end:clause.clause_end};
  return first;
}
function sectionSnippet(section) {
  const context=sectionContext(section), chars=Array.from(context.snippet);
  const ranges=section.anchors.map(({trigger})=>[trigger.anchor_start-context.context_start,trigger.anchor_end-context.context_start]);
  let html='',marked=false;
  chars.forEach((char,index)=>{
    const inside=ranges.some(([start,end])=>start<=index&&index<end);
    if(inside!==marked){html+=inside?'<mark>':'</mark>';marked=inside;}
    html+=esc(char);
  });
  if(marked)html+='</mark>';
  return (context.clipped_left?'…':'')+html+(context.clipped_right?'…':'');
}

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
  state.ignored_segments = [...ignoredSegments].sort();
  try { localStorage.setItem(storageKey, JSON.stringify(state)); }
  catch { storageAvailable = false; }
}
const entryById = new Map((data.lexicon_inventory||[]).map(entry=>[entry.id,entry]));
function sourceMapping(group) {
  const item=state.decisions[group.key];
  const mapping=item&&Object.hasOwn(item,'source_mapping')?item.source_mapping:group.source_mapping;
  const entry=mapping&&entryById.get(mapping.entry_id);
  return entry&&entry.preferred_form===mapping.preferred_form&&entry.canonical_tl===mapping.canonical_tl?mapping:null;
}
function mapToEntry(group, id) {
  const entry=entryById.get(Number(id));
  if(!entry)throw Error('Choose an existing entry ID from this lexicon.');
  const item=decision(group);
  if(hasCustomRequest(item))throw Error('Resolve the custom request before mapping this word.');
  item.source_mapping={source_form:group.key,entry_id:entry.id,preferred_form:entry.preferred_form,canonical_tl:entry.canonical_tl};
  item.approved=false;
  ignored.delete(group.key);
  save();
}
function mappingEditor(group) {
  const mapping=sourceMapping(group);
  if(mapping)return '<div class="handling-panel mapping-editor" data-key="'+esc(group.key)+'"><strong>Already handled → '+esc(mapping.preferred_form)+'</strong> · '+esc(mapping.canonical_tl)+' · entry '+mapping.entry_id+
    '<button class="unmap-source" type="button">Review again</button></div>';
  const stale=(data.stale_source_mappings||[]).find(row=>norm(row.source_form)===norm(group.key));
  return '<details '+panelAttrs(group,'mapping','handling-panel mapping-editor')+'><summary>Use existing entry</summary>'+
    (stale?'<p>Previous mapping needs review: entry '+stale.entry_id+' · '+esc(stale.preferred_form)+' · '+esc(stale.canonical_tl)+'. The target changed or disappeared.</p>':'')+
    '<p>Confirm that this whole source word is the same word as the selected entry. Its preferred spelling and readings stay in effect.</p>'+
    '<label>Existing entry ID <input class="mapping-id" type="number" min="1"></label><div class="mapping-preview"></div>'+
    '<button class="map-source" type="button">Confirm whole-word mapping</button><div class="mapping-status" role="status"></div></details>';
}
function isIgnored(group) { return group.dedup_lookup_forms.some(form => ignored.has(form)); }
function excluded(group) { return !eligibleOccurrences(group).length || !!sourceMapping(group) || isIgnored(group) || tracked.has(group.key) || unparseable.has(group.key) || machineRejected.has(group.key); }
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
  if (!eligibleOccurrences(group).length || sourceMapping(group) || !item.preferred_form.trim() || hasCustomRequest(item) || isIgnored(group) || unparseable.has(group.key) || machineRejected.has(group.key)
    || (tracked.has(group.key) && !item.identity_note.trim())) return false;
  try { outputForms(group); } catch { return false; }
  if (item.import_mode==='source_anchor') return sourceAnchorEligible(group) && !item.word_id && !item.canonical_choice_id && !item.alternate_choice_ids.length;
  return !!(item.import_mode==='moe' && word && canonical
    && item.alternate_choice_ids.every(id => id !== canonical.id && word.readings.some(reading => reading.id === id)));
}
function snippet(row) {
  const text=Array.from(row.snippet), a=row.anchor_start-row.context_start, b=row.anchor_end-row.context_start;
  return esc(text.slice(0,a).join(''))+'<mark>'+esc(text.slice(a,b).join(''))+'</mark>'+esc(text.slice(b).join(''));
}
function source(row) {
  return '<div class="muted"><a target="_blank" rel="noreferrer" href="'+esc(row.url)+'">'+esc(row.title)+'</a> · article text line '+row.line+'</div>';
}
function screeningNote(row) {
  const review=row.machine_screening;
  return review?'<div class="muted"><strong>Model '+esc(review.decision)+'</strong> · '+esc(review.model)+' · '+esc(review.reason)+'</div>':'';
}
function anchorNote(group, row=group.occurrences[0]) {
  const title=row.title.replace(/[\\[\]]/g, '\\$&');
  return (row.anchor||group.display)+': '+row.snippet+' ['+title+']('+row.url+')';
}
async function copyAnchorNote(group, button) {
  const row=group.occurrences[Number(button.dataset.occurrence)||0];
  const text=anchorNote(group,row), controls=button.parentElement;
  const field=controls.querySelector('textarea'), status=controls.querySelector('[role="status"]');
  button.disabled=true;
  status.textContent='';
  let copied=false;
  try {
    try {
      await navigator.clipboard.writeText(text);
      copied=true;
    } catch {
      // Local-file browsers may only support copying a selected text field.
      field.value=text;
      field.hidden=false;
      field.focus();field.select();
      try {copied=document.execCommand('copy');} catch {}
    }
    field.hidden=copied;
    status.textContent=copied?'Copied!':'Select the note below and copy it.';
    if(copied)button.focus();
  } finally {button.disabled=false;}
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
  if(item.import_mode==='source_anchor'&&eligible) return '<details '+panelAttrs(group,'import','handling-panel import-editor')+'><summary>Import word · article evidence'+(item.approved?' · approved':'')+'</summary>'+modeSelect+
    '<label>Preferred spelling <input type="text" class="preferred-input" value="'+esc(item.preferred_form)+'"></label>'+
    '<div>Filing TL reading: <strong>'+esc(group.normalized_tl)+'</strong></div>'+
    '<div class="written-form-preview"><strong>'+esc(item.preferred_form)+'</strong> · '+esc(group.normalized_tl)+'</div>'+
    '<label>Distinct word note (optional) <input type="text" class="identity-input" value="'+esc(item.identity_note)+'"></label>'+
    '<p class="muted">Approve this romanized form and reading using the article as evidence. No MOE match is required. New entries remain imported; offline LKK/MOE and existing-entry checks still run.</p>'+approvalControl(group)+'</details>';
  if(!words.length) return '<details '+panelAttrs(group,'import','handling-panel')+'><summary>Import word · reading needed</summary><p class="muted">This match needs a supported reading. Use Custom handling to propose its spelling and TL reading.</p></details>';
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
  return '<details '+panelAttrs(group,'import','handling-panel import-editor',!item.approved&&!hasCustomRequest(item)&&!sourceMapping(group))+'><summary>Import word · MOE evidence'+(item.approved?' · approved':'')+'</summary>'+modeSelect+
    '<label>Preferred spelling <input type="text" class="preferred-input" value="'+esc(item.preferred_form)+'"></label>'+
    '<label>MOE entry / meaning <select class="word-select">'+options+'</select></label>'+
    '<label>Filing TL reading <select class="canonical-select">'+primary+'</select></label>'+
    '<div>Alternate readings from this same MOE entry</div>'+readings.filter(reading=>reading.id!==canonical?.id).map(reading=>
      '<label class="reading-alt"><input type="checkbox" class="alternate-box" data-choice="'+reading.id+'" '+(item.alternate_choice_ids.includes(reading.id)?'checked':'')+'> '+esc(reading.reading)+' · '+esc(moeReadingRole(reading))+(reading.detected?'':' · additional MOE reading')+'</label>').join('')+
    '<div class="written-form-preview"><strong>Written forms to import</strong>'+preview+'</div>'+
    '<label>Distinct word note (optional) <input type="text" class="identity-input" value="'+esc(item.identity_note)+'"></label>'+
    '<p class="muted">Alternate outputs preserve Han characters and change the romanized syllables. Keep readings of one word together. For an existing word, update its entry; use the distinct word note only for an unrelated homograph. New records start as imported.</p>'+approvalControl(group)+'</details>';
}
function hasCustomRequest(item) {
  return ['custom_handling','custom_preferred_form','custom_hanji','custom_reading'].some(field=>item[field]?.trim());
}
function customRequests() {
  return Object.entries(state.decisions).filter(([key,item])=>hasCustomRequest(item)&&(!byKey.has(key)||eligibleOccurrences(byKey.get(key)).length)).map(([key,item])=>{
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
  return '<details '+panelAttrs(group,'custom','handling-panel custom-handling-editor')+'><summary>Custom handling'+(hasCustomRequest(item)?' · requested':'')+'</summary>'+
    '<label>Preferred form <input class="custom-preferred-form-input" type="text" value="'+esc(item.custom_preferred_form)+'" placeholder="食飯"></label>'+
    '<label>Hanji (optional) <input class="custom-hanji-input" type="text" value="'+esc(item.custom_hanji)+'" placeholder="食飯"></label>'+
    '<label>Reading (TL) <input class="custom-reading-input" type="text" value="'+esc(item.custom_reading)+'" placeholder="tsia̍h-pn̄g"></label>'+
    (structured&&(!item.custom_preferred_form.trim()||!item.custom_reading.trim())?'<p class="muted">Enter both a preferred form and reading. Hanji is optional.</p>':'')+
    '<label>Additional instructions (optional)<textarea class="custom-handling-input" placeholder="For example: split these meanings or check a missing reading.">'+esc(item.custom_handling)+'</textarea></label>'+
    (item.handled_custom_request?'<div class="muted">Previous request handled by entry '+esc(item.handled_custom_request.entry_id)+': '+esc(item.handled_custom_request.prompt)+'</div>':'')+
    '<p class="muted">Use preferred form and reading together; Hanji is optional and does not claim MOE inclusion. Saved locally and included in Export review.json for source and duplicate checks. Custom requests pause automatic import until reviewed.</p><button class="custom-save" type="button">Save request and fold</button></details>';
}
function approvalControl(group) {
  const item=decision(group);
  return '<label class="approve-label '+(item.approved?'approval-good':'')+'"><input class="approve-box" data-key="'+esc(group.key)+'" type="checkbox" aria-label="Approve import '+esc(group.key)+'" '+(item.approved&&approvable(group)?'checked ':'')+(approvable(group)?'':'disabled')+'> Approve import</label>';
}
function moePanel(group) {
  const cards=group.moe_cards||[], related=group.moe_related||[], preferred=group.preferred_matches||[];
  return '<div class="handling-options">'+importEditor(group)+customEditor(group)+mappingEditor(group)+'</div><div class="evidence">'+
    (preferred.length?'<details '+panelAttrs(group,'preferred','preferred-evidence')+'><summary>Existing spelling matches ('+preferred.length+')</summary>'+preferred.map(record=>'<div class="occurrence">Entry '+record.id+' · <strong>'+esc(record.preferred_form)+'</strong><div>Matched written form: '+esc((record.matched_written_forms||[record.preferred_form]).join(', '))+'</div>'+(record.hanji_forms?.length?'<div>Hanji: '+esc(record.hanji_forms.join(', '))+'</div>':'')+'<div class="muted">'+esc(record.path)+'</div></div>').join('')+'</details>':'')+
    (cards.length?'<details '+panelAttrs(group,'moe','anchor-matches',!decision(group).moe_matches_collapsed)+'><summary>MOE evidence ('+cards.length+')</summary>'+cards.map(moeCard).join('')+'</details>':'')+
    (related.length?'<details '+panelAttrs(group,'related','moe-related')+'><summary>Related dictionary entries</summary><div class="moe-results"></div></details>':'')+'</div>';
}
function matchStatus(group,rows=group.occurrences) {
  const item=decision(group);
  return rows.every(segmentIgnored)?'Segment ignored':rows.every(row=>row.tracked_coverage?.length)?'Covered by tracked word':sourceMapping(group)?'Mapped source spelling':tracked.has(group.key)?'Tracked form':unparseable.has(group.key)?'Parser did not recognize':machineRejected.has(group.key)?'Model rejected':isIgnored(group)?'Ignored':hasCustomRequest(item)?'Custom request saved':item.approved&&approvable(group)?'Approved import':'Pending';
}
function matchCard({group,rows}) {
  const row=rows[0],item=decision(group),omit=excluded(group)||rows.every(r=>segmentIgnored(r)||r.tracked_coverage?.length);
  const fixed=rows.every(r=>segmentIgnored(r)||r.tracked_coverage?.length)||sourceMapping(group)||tracked.has(group.key)||unparseable.has(group.key)||machineRejected.has(group.key);
  const status=matchStatus(group,rows);
  return '<article class="match-card'+(omit?' known':'')+'" data-key="'+esc(group.key)+'"><div class="match-header"><div><h3>'+esc(group.display)+'</h3><div class="muted">'+(group.normalized_tl?'TL lookup: '+esc(group.normalized_tl)+' · ':'')+group.occurrences.length+' occurrence'+(group.occurrences.length===1?'':'s')+' in '+group.article_count+' article'+(group.article_count===1?'':'s')+'</div></div><div class="match-actions"><span class="match-status '+(item.approved?'approval-good':'')+'">'+status+'</span><label><input class="ignore-box" type="checkbox" data-key="'+esc(group.key)+'" aria-label="Ignore '+esc(group.key)+'" '+(omit?'checked ':'')+(fixed?'disabled':'')+'> Ignore match</label><div class="note-controls"><button class="copy-note" data-key="'+esc(group.key)+'" data-occurrence="'+group.occurrences.indexOf(row)+'" type="button" title="Copy note" aria-label="Copy note for '+esc(group.display)+'"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true" focusable="false"><rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V4a1 1 0 0 0-1-1H4a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1h4"/></svg></button><span class="muted" role="status"></span><textarea hidden readonly aria-label="Anchor note"></textarea></div></div></div>'+
    rows.map(row=>'<div class="candidate-context">'+snippet(row)+'</div>'+screeningNote(row)+coverageNote(row)).join('')+moePanel(group)+
    '<details '+panelAttrs(group,'occurrences','all-occurrences')+'><summary>All '+group.occurrences.length+' source occurrences</summary><div class="occurrence-results"></div></details>'+
    (group.machine_rejected_occurrences?.length?'<details '+panelAttrs(group,'rejected','rejected-occurrences')+'><summary>Model-rejected occurrences ('+group.machine_rejected_occurrences.length+')</summary><div class="occurrence-results"></div></details>':'')+'</article>';
}
function sectionHtml(section) {
  const row=section.matches[0].rows[0];
  return '<section class="anchor-group" data-section="'+esc(section.id)+'"><header class="anchor-context"><div class="eyebrow">Roman-text segment</div><h2>'+section.anchors.map(anchor=>esc(anchor.trigger.anchor||anchor.row.base_anchor||anchor.row.anchor)).join(' · ')+'</h2><div class="reading-context">'+sectionSnippet(section)+'</div>'+source(row)+'<div class="muted">'+section.matches.length+' candidate'+(section.matches.length===1?'':'s')+' · longest first</div><button class="ignore-segment" data-section="'+esc(section.id)+'" type="button">'+(sectionIgnored(section)?'Restore segment':'Ignore this segment')+'</button></header>'+section.matches.map(matchCard).join('')+'</section>';
}
function render() {
  captureDisclosures();
  const active=data.groups.filter(group=>!excluded(group));
  const approved=active.filter(group=>decision(group).approved&&approvable(group)).length;
  const activeSections=reviewSections(active);
  $('stats').innerHTML=[['Articles',data.baseline.article_count],['Roman-text segments',activeSections.length],['Candidate words',active.length],['Approved imports',approved]].map(([label,value])=>'<div class="card"><div class="number">'+value+'</div>'+label+'</div>').join('');
  const query=norm($('search').value);
  const available=data.groups.filter(group=>!excluded(group)||$('showKnown').checked);
  const sections=reviewSections(available,$('showKnown').checked).filter(section=>!query||norm(sectionContext(section).snippet+' '+section.matches.map(({group,rows})=>group.key+' '+(group.normalized_tl||'')+' '+(group.moe_related||[]).map(record=>record.headword+' '+record.matched_reading).join(' ')+' '+rows.map(row=>row.snippet+' '+row.title).join(' ')).join(' ')).includes(query)).filter(section=>!$('showKnown').checked||$('excluded-filter').value!=='segments'||sectionIgnored(section));
  $('count').textContent=sections.length+' visible Roman-text segments · '+ignored.size+' ignored forms · '+approved+' approved imports · '+customRequests().length+' custom requests';
  $('review-status').textContent=(storageAvailable?'Decisions save locally in this browser. ':'Local saving is unavailable; export decisions before closing. ')+approved+' ready approvals and '+customRequests().length+' custom requests. '+data.groups.filter(sourceMapping).length+' mapped words. '+(data.stale_source_mappings?.length?data.stale_source_mappings.length+' saved mappings need target review. ':'')+'Export review.json to retain approvals, requests and mappings. Nothing is imported by this page.';
  const pageCount=Math.ceil(sections.length/sectionPageSize);
  sectionPage=Math.max(0,Math.min(sectionPage,pageCount-1));
  const pageSections=sections.slice(sectionPage*sectionPageSize,(sectionPage+1)*sectionPageSize);
  $('rows').innerHTML=pageSections.map(sectionHtml).join('');
  $('section-page').textContent=pageCount?'Page '+(sectionPage+1)+' of '+pageCount+' · '+pageSections.length+' segments shown':'No matching segments';
  $('previous-page').disabled=sectionPage===0;
  $('next-page').disabled=sectionPage+1>=pageCount;
  $('excluded-filter-label').hidden=!$('showKnown').checked;
  const sectionsById=new Map(sections.map(section=>[section.id,section]));
  document.querySelectorAll('.ignore-segment').forEach(button=>button.onclick=()=>{
    const section=sectionsById.get(button.dataset.section);setSegmentIgnored(section,!sectionIgnored(section));render();
  });
  document.querySelectorAll('.review-disclosure').forEach(detail=>detail.ontoggle=()=>{
    if(detail.isConnected===false)return;
    setPanelOpen(detail.dataset.key,detail.dataset.panel,detail.open);save();
    loadDisclosure(detail);
  });
  document.querySelectorAll('.review-disclosure').forEach(loadDisclosure);
  document.querySelectorAll('.mapping-editor').forEach(editor=>{
    const group=byKey.get(editor.dataset.key), input=editor.querySelector('.mapping-id');
    const clear=editor.querySelector('.unmap-source');
    if(clear)clear.onclick=()=>{decision(group).source_mapping=null;save();render();};
    if(input) {
      input.oninput=()=>{
        const entry=entryById.get(Number(input.value));
        editor.querySelector('.mapping-preview').textContent=entry?entry.preferred_form+' · '+entry.canonical_tl+' · '+entry.path:'No such entry';
      };
      editor.querySelector('.map-source').onclick=()=>{
        try {mapToEntry(group,input.value);render();}
        catch(error){editor.querySelector('.mapping-status').textContent=error.message;}
      };
    }
  });
  document.querySelectorAll('.copy-note').forEach(button=>button.onclick=()=>copyAnchorNote(byKey.get(button.dataset.key),button));
  document.querySelectorAll('.ignore-box').forEach(box=>box.onchange=()=>{
    box.checked?ignored.add(box.dataset.key):ignored.delete(box.dataset.key);
    if(box.checked)decision(byKey.get(box.dataset.key)).approved=false;
    $('known').value=[...ignored].sort().join(', ');save();render();
  });
  document.querySelectorAll('.approve-box').forEach(box=>box.onchange=()=>{const group=byKey.get(box.dataset.key);decision(group).approved=box.checked&&approvable(group);if(box.checked)setPanelOpen(group.key,'import',false);save();render();});
  document.querySelectorAll('.custom-handling-editor').forEach(editor=>{
    const item=decision(byKey.get(editor.dataset.key));
    editor.querySelector('.custom-save').onclick=()=>{setPanelOpen(editor.dataset.key,'custom',false);save();render();};
    for(const [selector,field] of [['.custom-handling-input','custom_handling'],
      ['.custom-preferred-form-input','custom_preferred_form'],['.custom-hanji-input','custom_hanji'],
      ['.custom-reading-input','custom_reading']])
      editor.querySelector(selector).oninput=event=>{
        item[field]=event.target.value.normalize('NFC');item.approved=false;
        editor.querySelector('summary').textContent='Custom handling'+(hasCustomRequest(item)?' · requested':'');
        document.querySelectorAll('.approve-box').forEach(box=>{
          if(box.dataset.key===editor.dataset.key){box.checked=false;box.disabled=!approvable(byKey.get(editor.dataset.key));}
        });
        document.querySelectorAll('.match-card').forEach(card=>{
          if(card.dataset.key===editor.dataset.key) {
            const status=card.querySelector('.match-status');status.textContent=matchStatus(byKey.get(editor.dataset.key));status.classList.remove('approval-good');
          }
        });
        save();
      };
  });
  document.querySelectorAll('.import-editor').forEach(editor=>{
    const group=byKey.get(editor.dataset.key), item=decision(group);
    function update(callback){callback();item.approved=false;setPanelOpen(group.key,'import',true);save();render();}
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
  captureDisclosures();
  reconcileHandledRequests();
  const approvals=data.groups.filter(group=>decision(group).approved&&approvable(group)).map(group=>({anchor_key:group.key,approved:true,...decision(group),...(decision(group).import_mode==='source_anchor'?{source_reading:group.normalized_tl}:{})}));
  return {schema_version:1,issue:data.issue,corpus_sha256:data.corpus_sha256,groups_sha256:data.review_groups_sha256,
    moe_snapshot:data.moe?.snapshot,screening_sha256:data.machine_screening?.sha256||null,ignored_forms:[...ignored].sort(),ignored_segments:[...ignoredSegments].sort(),ui_state:{disclosures:state.disclosures},
    source_mappings:data.groups.map(sourceMapping).filter(Boolean),
    source_mapping_removals:data.groups.filter(g=>g.source_mapping&&Object.hasOwn(decision(g),'source_mapping')&&decision(g).source_mapping===null).map(g=>g.key),approvals,custom_requests:customRequests(),decisions:state.decisions};
}
$('title').textContent='TSBP issue '+data.issue+' · vocabulary review pilot';
$('screening-policy').textContent=data.machine_screening?
  data.machine_screening.models.join(', ')+' screened '+data.machine_screening.occurrences+' occurrences: '+
  data.machine_screening.decision_counts.reject+' rejected; '+data.machine_screening.decision_counts.hold+
  ' held for your review. Model rejections are visible under Show excluded rows. This screen does not approve imports.':'';
$('known').value=[...ignored].sort().join(', ');
$('policy').textContent='The page groups candidates by original Roman-text positions, in article order, longest first. Decisions remain per word; repeated passages share that decision. Nested and overlapping multi-syllable anchors are listed. A single-syllable match is shown only where no longer MOE or tracked-word match contains it. Identical article/span matches appear once; text coverage counts overlaps once. Exclusions apply to each final written form. Matches remain candidates for human review.';
$('normalization').textContent='TL lookup spellings preserve original source text. Identical MOE headword/reading cards are merged while all IDs, definitions and source references remain available.';
$('moe-policy').textContent='Nested and overlapping multi-syllable anchors are listed separately; contained single-syllable matches are suppressed. Pure romanized anchors can use the article and displayed normalized TL reading without an MOE match. For dictionary-backed imports, choose one MOE entry / meaning, its filing reading and any alternates. Additional readings are sourced from that same MOE entry, even when they were not the detected anchor reading.';
$('context-policy').textContent='Exact context exclusions: '+data.context_exclusions.phrases.join(', ')+' · '+data.context_exclusions.skipped_anchor_occurrences+' anchor occurrences omitted.';
$('apply').onclick=()=>{ignored=editableIgnores($('known').value.split(/[,，\n]+/).map(text=>norm(text.trim())).filter(Boolean));$('known').value=[...ignored].sort().join(', ');for(const group of data.groups)if(isIgnored(group))decision(group).approved=false;save();render();};
$('search').oninput=()=>{sectionPage=0;render();};$('showKnown').onchange=()=>{sectionPage=0;render();};
$('excluded-filter').onchange=()=>{sectionPage=0;render();};
$('previous-page').onclick=()=>{sectionPage--;render();};
$('next-page').onclick=()=>{sectionPage++;render();};
$('download').onclick=()=>download('ignored-forms.json',[...ignored].sort());
$('export-review').onclick=()=>download('review.json',reviewExport());
$('load-review').onclick=()=>$('review-file').click();
$('review-file').onchange=async event=>{
  try {
    const bundle=JSON.parse(await event.target.files[0].text());
    if(bundle.schema_version!==1||bundle.corpus_sha256!==data.corpus_sha256||bundle.issue!==data.issue)throw Error('This review belongs to another corpus or issue.');
    state={ignored:bundle.ignored_forms||data.known_forms,decisions:bundle.decisions||{},ignored_segments:bundle.ignored_segments||[],segment_settings_base:data.ignored_segments||[],segment_settings_sha256:data.segment_settings_sha256,disclosures:bundle.ui_state?.disclosures||{}};
    for(const mapping of bundle.source_mappings||[]){const group=byKey.get(norm(mapping.source_form));if(group)decision(group).source_mapping=mapping;}
    for(const form of bundle.source_mapping_removals||[]){const group=byKey.get(norm(form));if(group)decision(group).source_mapping=null;}
    for(const approval of bundle.approvals||[])state.decisions[approval.anchor_key]=approval;
    for(const request of bundle.custom_requests||[]){
      const group=byKey.get(request.anchor_key);
      const item=group?decision(group):(state.decisions[request.anchor_key]??={});
      item.custom_handling=request.prompt;item.approved=false;
      item.custom_preferred_form=request.preferred_form||'';
      item.custom_hanji=request.hanji||'';item.custom_reading=request.reading||'';
    }
    ignored=editableIgnores(state.ignored);ignoredSegments=new Set(state.ignored_segments||[]);$('known').value=[...ignored].sort().join(', ');reconcileHandledRequests();$('rows').innerHTML='';save();render();
  } catch(error) {$('review-status').textContent='Could not load review: '+error.message;}
};
reconcileHandledRequests();

save();
render();
