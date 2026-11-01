import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source=['written_forms.js','review.js'].map(file=>fs.readFileSync(new URL(file,import.meta.url),'utf8')).join('\n');
function occurrence(anchor,start,triggerStart=start,triggerEnd=start+anchor.length,document='article') {
  return {anchor,anchor_start:start,anchor_end:start+Array.from(anchor).length,
    snippet:anchor,context_start:start,context_end:start+Array.from(anchor).length,
    document_id:document,title:'Article',url:'https://example.com',line:1,clause:anchor,
    source_triggers:[{anchor:'roman',anchor_start:triggerStart,anchor_end:triggerEnd}]};
}
function group(key,rows) {
  return {key,display:key,normalized_tl:key,parser_compatible:true,occurrences:rows,
    article_count:new Set(rows.map(row=>row.document_id)).size,dedup_lookup_forms:[key],review_words:[]};
}
function setup(groups,{saved=new Map(),details=[],boxes=[],extra={}}={}) {
  const nodes=new Map();
  const document={getElementById(id){if(!nodes.has(id))nodes.set(id,{value:'',checked:false,innerHTML:'',textContent:''});return nodes.get(id);},
    querySelectorAll(selector){return selector==='.review-disclosure'?details:selector==='.approve-box'?boxes:[];}};
  const data={groups,tracked_preferred_forms:[],unparseable_forms:[],known_forms:[],issue:385,
    corpus_sha256:'layout-test',moe:{snapshot:'test'},baseline:{source_characters:100,article_count:2},
    context_exclusions:{phrases:[],skipped_anchor_occurrences:0},...extra};
  const page=vm.createContext({data,document,setTimeout,localStorage:{getItem:k=>saved.get(k)||null,setItem:(k,v)=>saved.set(k,v)}});
  vm.runInContext(source,page);
  return {page,nodes,data,saved};
}
function value(page,expression){return JSON.parse(vm.runInContext('JSON.stringify('+expression+')',page));}

test('shared original Roman span groups subword matches longest first, in article order',()=>{
  const groups=[group('other',[occurrence('other',20,20,25)]),
    group('roman',[occurrence('roman',5,5,10)]),
    group('前roman後',[occurrence('前roman後',4,5,10)]),
    group('rom',[occurrence('rom',5,5,10)])];
  const {page}=setup(groups);
  assert.deepEqual(value(page,'reviewSections(data.groups).map(s=>s.matches.map(m=>m.group.key))'),
    [['前roman後','roman','rom'],['other']]);
  vm.runInContext("decision(byKey.get('roman')).approved=true",page);
  assert.deepEqual(value(page,'reviewExport().approvals.map(a=>a.anchor_key)'),['roman']);
});

test('repeated spellings stay local to their passages, with one shared decision and export',()=>{
  const {page}=setup([group('roman',[occurrence('roman',5),occurrence('roman',30),occurrence('roman',5,5,10,'second')]),
    group('roman後',[occurrence('roman後',30,30,35)])]);
  assert.equal(value(page,'reviewSections(data.groups).length'),3);
  assert.deepEqual(value(page,'reviewSections(data.groups).map(s=>s.matches.length)'),[1,2,1]);
  vm.runInContext("decision(byKey.get('roman')).approved=true;render()",page);
  assert.equal(value(page,'reviewExport().approvals.length'),1);
});

test('multi-trigger occurrences join local anchors without duplicating a candidate',()=>{
  const shared=occurrence('roman後roman',5,5,10);
  shared.source_triggers.push({anchor:'roman',anchor_start:11,anchor_end:16});
  const {page}=setup([group('roman後roman',[shared]),group('roman',[occurrence('roman',5,5,10),occurrence('roman',11,11,16)])]);
  assert.equal(value(page,'reviewSections(data.groups).length'),1);
  assert.deepEqual(value(page,'reviewSections(data.groups)[0].matches.map(m=>m.group.key)'),['roman後roman','roman']);
});

test('adjacent Roman spans and repeated words cannot join remote overlap sections',()=>{
  const {page}=setup([group('one',[occurrence('one',1,1,4),occurrence('one',40,40,43)]),
    group('two',[occurrence('two',4,4,7)]),group('long',[occurrence('long',39,40,43)])]);
  assert.equal(value(page,'reviewSections(data.groups).length'),3);
});

test('search keeps sibling candidates together and longer context uses code point offsets',()=>{
  const row=occurrence('roman',3,3,8),long=occurrence('roman後',3,3,8);
  const {page,nodes}=setup([group('roman',[row]),group('roman後',[long])],{extra:{reading_contexts:{
    '["article",3,8]':{snippet:'𠊎前，roman後。完整後文',context_start:0,context_end:17}}}});
  nodes.get('search').value='roman後';vm.runInContext('render()',page);
  assert.match(nodes.get('rows').innerHTML,/<h3>roman<\/h3>/);
  assert.match(nodes.get('rows').innerHTML,/𠊎前，<mark>roman<\/mark>後。完整後文/);
});

test('folded custom request stays folded when another word is approved and after reload',()=>{
  const details=[{dataset:{key:'roman',panel:'custom'},open:false}];
  const boxes=[{dataset:{key:'second'},checked:false}];
  const groups=[group('roman',[occurrence('roman',1)]),group('second',[occurrence('second',30)])];
  const {page,saved,nodes}=setup(groups,{details,boxes});
  vm.runInContext("decision(byKey.get('roman')).custom_handling='Check sense';save();render()",page);
  // Open, then explicitly fold the custom request before approving the other word.
  details[0].open=true;details[0].ontoggle();details[0].open=false;details[0].ontoggle();
  boxes[0].checked=true;boxes[0].onchange();
  assert.equal(value(page,"state.disclosures[disclosureId('roman','custom')]"),false);
  assert.match(nodes.get('rows').innerHTML,/data-key="roman" data-panel="custom"><summary>Custom handling · requested/);
  const bundle=value(page,'reviewExport()');
  assert.equal(bundle.custom_requests.length,1);
  assert.equal(bundle.approvals[0].anchor_key,'second');
  const reload=setup(groups,{saved});
  assert.equal(value(reload.page,"state.disclosures[disclosureId('roman','custom')]"),false);
  assert.match(reload.nodes.get('rows').innerHTML,/data-key="roman" data-panel="custom"><summary>Custom handling · requested/);
});

test('approving an import folds that editor without closing unrelated open panels',()=>{
  const details=[{dataset:{key:'roman',panel:'import'},open:true},{dataset:{key:'second',panel:'custom'},open:true}];
  const boxes=[{dataset:{key:'roman'},checked:false}];
  const {page}=setup([group('roman',[occurrence('roman',1)]),group('second',[occurrence('second',30)])],{details,boxes});
  boxes[0].checked=true;boxes[0].onchange();
  assert.equal(details[0].open,false);
  assert.equal(details[1].open,true);
  assert.equal(value(page,"state.disclosures[disclosureId('roman','import')]"),false);
});

test('article inventory controls section order rather than spelling or frequency',()=>{
  const {page}=setup([group('roman',[occurrence('roman',1,1,6,'a'),occurrence('roman',30,30,35,'a')]),
    group('second',[occurrence('second',10,10,16,'z')])],{extra:{article_inventory:[{id:'z'},{id:'a'}]}});
  assert.deepEqual(value(page,'reviewSections(data.groups).map(s=>[s.document,s.start])'),[['z',10],['a',1],['a',30]]);
});

test('panel state travels with review exports and old exports remain loadable',async()=>{
  const groups=[group('roman',[occurrence('roman',1)])];
  const original=setup(groups);
  vm.runInContext("setPanelOpen('roman','custom',false);setPanelOpen('roman','mapping',true);decision(byKey.get('roman')).custom_handling='Review this sense'",original.page);
  const bundle=value(original.page,'reviewExport()');
  const loaded=setup(groups);
  await loaded.nodes.get('review-file').onchange({target:{files:[{text:async()=>JSON.stringify(bundle)}]}});
  assert.deepEqual(value(loaded.page,'reviewExport().ui_state'),bundle.ui_state);
  assert.equal(value(loaded.page,'reviewExport().custom_requests[0].prompt'),'Review this sense');
  delete bundle.ui_state;
  await loaded.nodes.get('review-file').onchange({target:{files:[{text:async()=>JSON.stringify(bundle)}]}});
  assert.equal(value(loaded.page,'reviewExport().custom_requests[0].prompt'),'Review this sense');
  assert.match(loaded.nodes.get('rows').innerHTML,/data-key="roman" data-panel="custom"><summary>Custom handling · requested/);
});

test('pending MOE import opens by default while saved folds and completed handling win',()=>{
  const moe=group('roman',[occurrence('roman',1)]);
  moe.review_words=[{id:'moe:1',headword:'字',readings:[{id:'main',headword:'字',reading:'roman',detected:true,references:[{source:{sheet:'詞目'}}]}]}];
  const {page,nodes}=setup([moe]);
  assert.match(nodes.get('rows').innerHTML,/data-key="roman" data-panel="import" open><summary>Import word · MOE evidence/);
  vm.runInContext("setPanelOpen('roman','import',false);render()",page);
  assert.match(nodes.get('rows').innerHTML,/data-key="roman" data-panel="import"><summary>Import word · MOE evidence/);
  vm.runInContext("delete state.disclosures[disclosureId('roman','import')];decision(byKey.get('roman')).approved=true;render()",page);
  assert.match(nodes.get('rows').innerHTML,/data-key="roman" data-panel="import"><summary>Import word · MOE evidence · approved/);
  vm.runInContext("decision(byKey.get('roman')).approved=false;decision(byKey.get('roman')).custom_handling='Check sense';render()",page);
  assert.match(nodes.get('rows').innerHTML,/data-key="roman" data-panel="import"><summary>Import word · MOE evidence/);
  const article=setup([group('roman',[occurrence('roman',1)])]);
  assert.match(article.nodes.get('rows').innerHTML,/data-key="roman" data-panel="import"><summary>Import word · article evidence/);
});

test('ignore segment hides all its candidates, clears approval, and preserves other passages',()=>{
  const groups=[group('roman',[occurrence('roman',5),occurrence('roman',30)]),
    group('roman後',[occurrence('roman後',5,5,10)])];
  const {page,nodes,saved}=setup(groups);
  vm.runInContext("decision(byKey.get('roman後')).approved=true;setSegmentIgnored(reviewSections(data.groups)[0]);render()",page);
  assert.equal(value(page,'reviewSections(data.groups).length'),1);
  assert.equal(value(page,'decision(byKey.get("roman後")).approved'),false);
  assert.equal(value(page,'excluded(byKey.get("roman"))'),false);
  assert.equal(value(page,'excluded(byKey.get("roman後"))'),true);
  assert.equal(value(page,'reviewExport().ignored_segments.length'),1);
  assert.equal(value(page,'reviewExport().ignored_forms.length'),0);
  assert.doesNotMatch(nodes.get('rows').innerHTML,/<h3>roman後<\/h3>/);
  nodes.get('showKnown').checked=true;vm.runInContext('render()',page);
  assert.match(nodes.get('rows').innerHTML,/Restore segment/);
  const reloaded=setup(groups,{saved});
  assert.equal(value(reloaded.page,'reviewSections(data.groups).length'),1);
  vm.runInContext('setSegmentIgnored(reviewSections(data.groups,true)[0],false);render()',page);
  assert.equal(value(page,'reviewSections(data.groups).length'),2);
});

test('segment ignores survive file restore without deleting custom request text',async()=>{
  const groups=[group('roman',[occurrence('roman',5)])];
  const {page}=setup(groups);
  vm.runInContext("decision(byKey.get('roman')).custom_handling='Keep this draft';setSegmentIgnored(reviewSections(data.groups)[0])",page);
  const bundle=value(page,'reviewExport()');
  assert.equal(bundle.custom_requests.length,0);
  const loaded=setup(groups);
  await loaded.nodes.get('review-file').onchange({target:{files:[{text:async()=>JSON.stringify(bundle)}]}});
  assert.equal(value(loaded.page,'reviewSections(data.groups).length'),0);
  vm.runInContext('setSegmentIgnored(reviewSections(data.groups,true)[0],false);render()',loaded.page);
  assert.equal(value(loaded.page,'reviewExport().custom_requests[0].prompt'),'Keep this draft');
});

test('covered fragment hides only covered occurrences and cannot be approved without other evidence',()=>{
  const first=occurrence('roman',5),second=occurrence('roman',30);
  first.tracked_coverage=[{entries:[{id:4741,preferred_form:'roman後'}]}];
  const {page,nodes}=setup([group('roman',[first,second])]);
  assert.equal(value(page,'reviewSections(data.groups).length'),1);
  vm.runInContext('data.groups[0].occurrences.pop();render()',page);
  assert.equal(value(page,'approvable(data.groups[0])'),false);
  assert.equal(nodes.get('rows').innerHTML,'');
  nodes.get('showKnown').checked=true;vm.runInContext('render()',page);
  assert.match(nodes.get('rows').innerHTML,/Covered by entry 4741/);
});

test('segment ignores survive a rerun where the candidate disappears and later returns',()=>{
  const groups=[group('roman',[occurrence('roman',5)])];
  const original=setup(groups);
  vm.runInContext('setSegmentIgnored(reviewSections(data.groups)[0])',original.page);
  const absent=setup([],{saved:original.saved});
  assert.equal(value(absent.page,'reviewExport().ignored_segments.length'),1);
  const returned=setup(groups,{saved:original.saved});
  assert.equal(value(returned.page,'reviewSections(data.groups).length'),0);
});

test('persisted segment settings seed fresh browsers and preserve local restores across reruns',()=>{
  const groups=[group('roman',[occurrence('roman',5)])],id='["article",5,10]';
  const first=setup(groups,{extra:{ignored_segments:[id],segment_settings_sha256:'one'}});
  assert.equal(value(first.page,'reviewSections(data.groups).length'),0);
  vm.runInContext('setSegmentIgnored(reviewSections(data.groups,true)[0],false)',first.page);
  const rerun=setup(groups,{saved:first.saved,extra:{ignored_segments:[id],segment_settings_sha256:'two'}});
  assert.equal(value(rerun.page,'reviewSections(data.groups).length'),1);
});

test('excluded rows are paged and search covers results beyond the current page',()=>{
  const groups=Array.from({length:45},(_,i)=>group('roman'+i,[occurrence('roman'+i,i*20)]));
  const {page,nodes}=setup(groups,{extra:{known_forms:groups.map(g=>g.key)}});
  nodes.get('showKnown').checked=true;nodes.get('showKnown').onchange();
  assert.equal((nodes.get('rows').innerHTML.match(/class="anchor-group"/g)||[]).length,20);
  assert.match(nodes.get('section-page').textContent,/Page 1 of 3/);
  nodes.get('next-page').onclick();
  assert.match(nodes.get('section-page').textContent,/Page 2 of 3/);
  nodes.get('search').value='roman44';nodes.get('search').oninput();
  assert.match(nodes.get('rows').innerHTML,/<h3>roman44<\/h3>/);
  assert.match(nodes.get('section-page').textContent,/Page 1 of 1/);
});

test('frequent words do not eagerly repeat their full occurrence history in every section',()=>{
  const {page,nodes}=setup([group('roman',Array.from({length:100},(_,i)=>occurrence('roman',i*20)))]);
  assert.equal((nodes.get('rows').innerHTML.match(/class="anchor-group"/g)||[]).length,20);
  assert.doesNotMatch(nodes.get('rows').innerHTML,/class="occurrence"/);
  const history=value(page,'occurrenceRows(data.groups[0])');
  assert.equal((history.match(/class="occurrence"/g)||[]).length,25);
  assert.match(history,/Show next 25 occurrences/);
});

test('ignored-segments filter shows restore controls without unrelated tracked rows',()=>{
  const groups=[group('roman',[occurrence('roman',5)]),group('second',[occurrence('second',30)])];
  const {page,nodes}=setup(groups,{extra:{known_forms:['second']}});
  vm.runInContext('setSegmentIgnored(reviewSections([data.groups[0]])[0])',page);
  nodes.get('showKnown').checked=true;nodes.get('excluded-filter').value='segments';nodes.get('excluded-filter').onchange();
  assert.match(nodes.get('rows').innerHTML,/Restore segment/);
  assert.doesNotMatch(nodes.get('rows').innerHTML,/<h3>second<\/h3>/);
});
