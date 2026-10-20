import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';

const cases = [
  ['想beh', 'siūnn-beh', 'siūnn-bueh', '想bueh'],
  ['hip相', 'hip-siòng', 'hip-siōng', 'hip相'],
  ['beh食飯', 'beh-tsiah-pn̄g', 'bueh-tsiah-pn̄g', 'bueh食飯'],
  ['想beh食飯', 'siūnn-beh-tsiah-pn̄g', 'siūnn-bueh-tsiah-pn̄g', '想bueh食飯'],
  ['好--ah', 'hó--ah', 'hó--a', '好--a'],
  ['後--日', 'āu--ji̍t', 'āu--li̍t', '後--日'],
  ['m̄知', 'm̄ tsai', 'm̄ chai', 'm̄知'],
  ['beh', 'beh', 'bueh', 'bueh'],
  ['--ah', '--ah', '--a', '--a'],
  ['想bèh', 'siūnn-bèh', 'siūnn-bueh', '想bueh'],
];
const context = vm.createContext({});
vm.runInContext(fs.readFileSync(new URL('./written_forms.js', import.meta.url), 'utf8'), context);

test('review and repository generate identical alternate spellings', () => {
  const source = `import json,sys\nfrom tools.lexicon import written_form\nprint(json.dumps([written_form(*row[:3]) for row in json.load(sys.stdin)],ensure_ascii=False))`;
  const root = process.env.LEXICON_ROOT || fileURLToPath(new URL('../../', import.meta.url));
  const python = JSON.parse(execFileSync('python3', ['-c', source], {cwd: root, input: JSON.stringify(cases), encoding:'utf8'}));
  cases.forEach((row, index) => {
    assert.equal(context.writtenForm(...row.slice(0,3)), row[3]);
    assert.equal(python[index], row[3]);
  });
  for (const args of [['想beh','siūnn-beh','sióng'], ['想beh','siūnn-bueh','siūnn-beh'], ['想beh','siūnn-beh','siūnn--beh']])
    assert.throws(()=>context.writtenForm(...args));
});

test('review shows both approved outputs and rejects inconsistent mixed readings', () => {
  const group={key:'想beh',display:'想beh',normalized_forms:['想beh'],dedup_lookup_forms:['想beh'],
    occurrences:[{snippet:'我想beh去',anchor_start:1,anchor_end:5,context_start:0,context_end:6,
      document_id:'test',url:'https://example.com',title:'Fixture',line:1,clause:'我想beh去'}],
    article_count:1,review_words:[{id:'moe:14370',headword:'想欲',readings:[
      {id:'one',headword:'想欲',reading:'siūnn-beh',detected:true,references:[{source:{sheet:'詞目'}}]},
      {id:'two',headword:'想欲',reading:'siūnn-bueh',detected:false,references:[{source:{sheet:'又唸作'}}]}]}]};
  const nodes=new Map();
  const document={getElementById(id){if(!nodes.has(id))nodes.set(id,{value:'',checked:false,innerHTML:'',textContent:''});return nodes.get(id);},querySelectorAll(){return [];}};
  const data={groups:[group],tracked_preferred_forms:[],unparseable_forms:[],known_forms:[],issue:390,
    corpus_sha256:'test',moe:{snapshot:'test'},baseline:{source_characters:20,article_count:1},context_exclusions:{phrases:[],skipped_anchor_occurrences:0}};
  const page=vm.createContext({data,document,localStorage:{getItem(){return null;},setItem(){}},setTimeout});
  vm.runInContext(fs.readFileSync(new URL('./written_forms.js',import.meta.url),'utf8')+'\n'+fs.readFileSync(new URL('./review.js',import.meta.url),'utf8'),page);
  vm.runInContext(`Object.assign(decision(data.groups[0]),{preferred_form:'想beh',word_id:'moe:14370',canonical_choice_id:'one',alternate_choice_ids:['two'],approved:true});render();`,page);
  assert.match(nodes.get('rows').innerHTML, /<strong>想beh<\/strong> · siūnn-beh/);
  assert.match(nodes.get('rows').innerHTML, /<strong>想bueh<\/strong> · siūnn-bueh/);
  assert.equal(vm.runInContext('reviewExport().approvals.length',page),1);
  assert.match(nodes.get('rows').innerHTML,/siūnn-beh · 想欲 · MOE primary \(詞目\) · selected filing/);
  assert.match(nodes.get('rows').innerHTML,/siūnn-bueh · 想欲 · MOE alternate \(又唸作\)/);
  vm.runInContext(`decision(data.groups[0]).canonical_choice_id='two';decision(data.groups[0]).alternate_choice_ids=[];`,page);
  assert.equal(vm.runInContext('approvable(data.groups[0])',page),false);
  vm.runInContext(`decision(data.groups[0]).preferred_form='想bueh';render();`,page);
  assert.match(nodes.get('rows').innerHTML,/siūnn-bueh · 想欲 · MOE alternate \(又唸作\) · selected filing/);
  assert.match(nodes.get('rows').innerHTML,/siūnn-beh · 想欲 · MOE primary \(詞目\)/);
});

test('custom handling is available without MOE matches and survives export and reload', () => {
  const group={key:'unknown',display:'unknown',normalized_forms:['unknown'],dedup_lookup_forms:['unknown'],
    occurrences:[{snippet:'我unknown',anchor_start:1,anchor_end:8,context_start:0,context_end:8,
      document_id:'test',url:'https://example.com',title:'Fixture',line:1,clause:'我unknown'}],
    article_count:1,review_words:[]};
  const nodes=new Map(), saved=new Map();
  const document={getElementById(id){if(!nodes.has(id))nodes.set(id,{value:'',checked:false,innerHTML:'',textContent:''});return nodes.get(id);},querySelectorAll(){return [];}};
  const data={groups:[group],tracked_preferred_forms:[],unparseable_forms:[],known_forms:[],issue:390,
    corpus_sha256:'custom-test',moe:{snapshot:'test'},baseline:{source_characters:20,article_count:1},context_exclusions:{phrases:[],skipped_anchor_occurrences:0}};
  const localStorage={getItem(key){return saved.get(key)||null;},setItem(key,value){saved.set(key,value);}};
  const source=fs.readFileSync(new URL('./written_forms.js',import.meta.url),'utf8')+'\n'+fs.readFileSync(new URL('./review.js',import.meta.url),'utf8');
  const page=vm.createContext({data,document,localStorage,setTimeout});
  vm.runInContext(source,page);
  assert.match(nodes.get('rows').innerHTML,/Custom handling/);
  vm.runInContext(`Object.assign(decision(data.groups[0]),{custom_handling:'Check <this> reading and split the word.',approved:true});render();`,page);
  const bundle=JSON.parse(vm.runInContext('JSON.stringify(reviewExport())',page));
  assert.equal(bundle.approvals.length,0);
  assert.deepEqual(bundle.custom_requests,[{anchor_key:'unknown',prompt:'Check <this> reading and split the word.',anchor_present:true}]);
  assert.match(nodes.get('rows').innerHTML,/Check &lt;this&gt; reading/);
  const reloaded=vm.createContext({data,document,localStorage,setTimeout});
  vm.runInContext(source,reloaded);
  assert.equal(vm.runInContext('reviewExport().custom_requests[0].prompt',reloaded),'Check <this> reading and split the word.');
});

test('pure romanized anchor can be approved from article evidence and exported', () => {
  const group={key:'chhiū-lo̍h',display:'Chhiū-lo̍h',normalized_tl:'tshiū-lo̍h',normalized_forms:['tshiū-lo̍h'],
    parser_compatible:true,dedup_lookup_forms:['chhiū-lo̍h','tshiū-lo̍h'],review_words:[],article_count:1,
    occurrences:[{anchor:'Chhiū-lo̍h',snippet:'甲Chhiū-lo̍h乙',anchor_start:1,anchor_end:10,context_start:0,context_end:11,
      document_id:'test',url:'https://example.com/article',title:'Fixture',line:1,clause:'甲Chhiū-lo̍h乙'}]};
  const nodes=new Map(),saved=new Map();
  const document={getElementById(id){if(!nodes.has(id))nodes.set(id,{value:'',checked:false,innerHTML:'',textContent:''});return nodes.get(id);},querySelectorAll(){return [];}};
  const data={groups:[group],tracked_preferred_forms:[],unparseable_forms:[],known_forms:[],issue:390,
    corpus_sha256:'article-test',moe:{snapshot:'test'},baseline:{source_characters:20,article_count:1},context_exclusions:{phrases:[],skipped_anchor_occurrences:0}};
  const page=vm.createContext({data,document,setTimeout,localStorage:{getItem(key){return saved.get(key)||null;},setItem(key,value){saved.set(key,value);}}});
  vm.runInContext(fs.readFileSync(new URL('./written_forms.js',import.meta.url),'utf8')+'\n'+fs.readFileSync(new URL('./review.js',import.meta.url),'utf8'),page);
  assert.equal(vm.runInContext('approvable(data.groups[0])',page),true);
  assert.match(nodes.get('rows').innerHTML,/Article anchor import/);
  assert.match(nodes.get('rows').innerHTML,/Filing TL reading: <strong>tshiū-lo̍h/);
  vm.runInContext('decision(data.groups[0]).approved=true;render();',page);
  const approval=JSON.parse(vm.runInContext('JSON.stringify(reviewExport().approvals[0])',page));
  assert.equal(approval.import_mode,'source_anchor');
  assert.equal(approval.source_reading,'tshiū-lo̍h');
  assert.equal(approval.preferred_form,'tshiū-lo̍h');
  assert.equal(approval.word_id,'');
  const root=fileURLToPath(new URL('../../',import.meta.url));
  const pilot=new URL('.',import.meta.url).pathname;
  const script=`import sys,json\nsys.path.insert(0,sys.argv[1])\nfrom import_review import build_request\na,g=json.load(sys.stdin)\nprint(json.dumps(build_request(a,g,[],[]),ensure_ascii=False))`;
  const request=JSON.parse(execFileSync('python3',['-c',script,pilot],{cwd:root,input:JSON.stringify([approval,group]),encoding:'utf8'}));
  assert.equal(request.canonical_tl,'tshiū-lo̍h');
  assert.deepEqual(request.moe_forms,[]);
  assert.equal(request.sources[0].url,'https://example.com/article');
  vm.runInContext(`decision(data.groups[0]).custom_handling='check reading';`,page);
  assert.equal(vm.runInContext('approvable(data.groups[0])',page),false);
  vm.runInContext(`decision(data.groups[0]).custom_handling='';data.groups[0].parser_compatible=false;`,page);
  assert.equal(vm.runInContext('approvable(data.groups[0])',page),false);
});

test('MOE anchor match folding survives rerenders and local reload', () => {
  const card={headword:'翕',reading:'hip',definitions:[],record_ids:['1'],references:[]};
  const group={key:'hip',display:'hip',normalized_tl:'hip',parser_compatible:true,normalized_forms:['hip'],
    dedup_lookup_forms:['hip'],review_words:[],moe_cards:[card],article_count:1,
    occurrences:[{snippet:'甲hip乙',anchor_start:1,anchor_end:4,context_start:0,context_end:5,
      document_id:'test',url:'https://example.com',title:'Fixture',line:1,clause:'甲hip乙'}]};
  const nodes=new Map(),saved=new Map(),detail={dataset:{key:'hip'},open:true};
  const document={getElementById(id){if(!nodes.has(id))nodes.set(id,{value:'',checked:false,innerHTML:'',textContent:''});return nodes.get(id);},querySelectorAll(selector){return selector==='.anchor-matches'?[detail]:[];}};
  const data={groups:[group],tracked_preferred_forms:[],unparseable_forms:[],known_forms:[],issue:390,
    corpus_sha256:'fold-test',moe:{snapshot:'test'},baseline:{source_characters:20,article_count:1},context_exclusions:{phrases:[],skipped_anchor_occurrences:0}};
  const localStorage={getItem(key){return saved.get(key)||null;},setItem(key,value){saved.set(key,value);}};
  const source=fs.readFileSync(new URL('./written_forms.js',import.meta.url),'utf8')+'\n'+fs.readFileSync(new URL('./review.js',import.meta.url),'utf8');
  const page=vm.createContext({data,document,localStorage,setTimeout});vm.runInContext(source,page);
  assert.match(nodes.get('rows').innerHTML,/<details class="anchor-matches" data-key="hip" open>/);
  detail.open=false;detail.ontoggle();vm.runInContext('render()',page);
  assert.match(nodes.get('rows').innerHTML,/<details class="anchor-matches" data-key="hip"><summary>MOE anchor match \(1\)/);
  const reloaded=vm.createContext({data,document,localStorage,setTimeout});vm.runInContext(source,reloaded);
  assert.equal(vm.runInContext('decision(data.groups[0]).moe_matches_collapsed',reloaded),true);
});

test('handled custom requests are reconciled after reload without hiding changed prompts', () => {
  const group={key:'liô',display:'liô',normalized_forms:['liô'],dedup_lookup_forms:['liô'],
    occurrences:[{snippet:'liô',anchor_start:0,anchor_end:3,context_start:0,context_end:3,
      document_id:'test',url:'https://example.com',title:'Fixture',line:1,clause:'liô'}],
    article_count:1,review_words:[]};
  const nodes=new Map();
  const document={getElementById(id){if(!nodes.has(id))nodes.set(id,{value:'',checked:false,innerHTML:'',textContent:''});return nodes.get(id);},querySelectorAll(){return [];}};
  const saved={ignored:[],decisions:{
    'liô':{custom_handling:'use "liô心"',approved:true,preferred_form:'liô',identity_note:''},
    'lê':{custom_handling:'use "lê-lê"',approved:false},
    'other':{custom_handling:'A changed request',approved:false}}};
  const data={groups:[group],tracked_preferred_forms:[],unparseable_forms:[],known_forms:[],issue:390,
    corpus_sha256:'handled-test',moe:{snapshot:'test'},baseline:{source_characters:20,article_count:1},
    context_exclusions:{phrases:[],skipped_anchor_occurrences:0},handled_custom_requests:[
      {anchor_key:'liô',prompt:'use "liô心"',entry_id:671},
      {anchor_key:'lê',prompt:'use "lê-lê"',entry_id:544},
      {anchor_key:'other',prompt:'An older request',entry_id:1}]};
  const page=vm.createContext({data,document,setTimeout,localStorage:{getItem(){return JSON.stringify(saved);},setItem(){}}});
  vm.runInContext(fs.readFileSync(new URL('./written_forms.js',import.meta.url),'utf8')+'\n'+fs.readFileSync(new URL('./review.js',import.meta.url),'utf8'),page);
  const bundle=JSON.parse(vm.runInContext('JSON.stringify(reviewExport())',page));
  assert.deepEqual(bundle.custom_requests,[{anchor_key:'other',prompt:'A changed request',anchor_present:false}]);
  assert.equal(bundle.decisions['liô'].custom_handling,'');
  assert.equal(bundle.decisions['liô'].approved,false);
  assert.equal(bundle.decisions['lê'].handled_custom_request.entry_id,544);
  assert.match(nodes.get('rows').innerHTML,/Previous request handled by entry 671/);
});

test('structured custom handling exports preferred, optional Hanji and reading across reloads', () => {
  const group={key:'liô',display:'liô',normalized_forms:['liô'],dedup_lookup_forms:['liô'],
    normalized_tl:'liô',parser_compatible:true,
    occurrences:[{anchor:'liô',snippet:'liô心',anchor_start:0,anchor_end:3,context_start:0,context_end:4,
      document_id:'test',url:'https://example.com',title:'Fixture',line:1,clause:'liô心'}],
    article_count:1,review_words:[]};
  const nodes=new Map(),saved=new Map();
  const document={getElementById(id){if(!nodes.has(id))nodes.set(id,{value:'',checked:false,innerHTML:'',textContent:''});return nodes.get(id);},querySelectorAll(){return [];}};
  const data={groups:[group],tracked_preferred_forms:[],unparseable_forms:[],known_forms:[],issue:390,
    corpus_sha256:'structured-test',moe:{snapshot:'test'},baseline:{source_characters:20,article_count:1},
    context_exclusions:{phrases:[],skipped_anchor_occurrences:0}};
  const localStorage={getItem(key){return saved.get(key)||null;},setItem(key,value){saved.set(key,value);}};
  const source=fs.readFileSync(new URL('./written_forms.js',import.meta.url),'utf8')+'\n'+fs.readFileSync(new URL('./review.js',import.meta.url),'utf8');
  const page=vm.createContext({data,document,setTimeout,localStorage});vm.runInContext(source,page);
  assert.match(nodes.get('rows').innerHTML,/Hanji \(optional\)/);
  vm.runInContext(`Object.assign(decision(data.groups[0]),{custom_preferred_form:'liô心',custom_hanji:'𠞭心',custom_reading:'liô-sim',approved:true});render();`,page);
  let bundle=JSON.parse(vm.runInContext('JSON.stringify(reviewExport())',page));
  assert.equal(bundle.approvals.length,0);
  assert.deepEqual(bundle.custom_requests,[{anchor_key:'liô',prompt:'',anchor_present:true,preferred_form:'liô心',hanji:'𠞭心',reading:'liô-sim'}]);
  const reloaded=vm.createContext({data,document,setTimeout,localStorage});vm.runInContext(source,reloaded);
  assert.equal(vm.runInContext('reviewExport().custom_requests[0].hanji',reloaded),'𠞭心');
  vm.runInContext(`decision(data.groups[0]).custom_hanji='';render();`,reloaded);
  bundle=JSON.parse(vm.runInContext('JSON.stringify(reviewExport())',reloaded));
  assert.equal(Object.hasOwn(bundle.custom_requests[0],'hanji'),false);
  assert.equal(bundle.custom_requests[0].reading,'liô-sim');
});
