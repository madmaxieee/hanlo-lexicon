import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

test('model rejections cannot reuse saved approvals; holds and mixed-source evidence remain visible',()=>{
  function row(anchor,doc,decision) {
    return {anchor,snippet:anchor,clause:anchor,document_id:doc,url:'https://example.com/'+doc,
      title:doc,line:1,anchor_start:0,anchor_end:anchor.length,context_start:0,context_end:anchor.length,
      machine_screening:{decision,model:'gpt-6-luna',reason:decision==='reject'?'English quotation.':'Taiwanese context needs review.'}};
  }
  function group(key,occurrence) {
    return {key,display:key,normalized_tl:key,parser_compatible:true,dedup_lookup_forms:[key],
      article_count:1,review_words:[],occurrences:[occurrence]};
  }
  const rejected={...group('the',row('the','english','reject')),exclusion_reason:'machine_rejected'};
  const held=group('hm',row('hm','taiwanese','hold'));
  const mixed={...group('a',row('a','taiwanese','keep')),
    machine_rejected_occurrences:[row('a','english','reject')]};
  const nodes=new Map();
  const document={getElementById(id){
    if(!nodes.has(id))nodes.set(id,{value:'',checked:false,innerHTML:'',textContent:''});
    return nodes.get(id);
  },querySelectorAll(){return [];}};
  const data={groups:[rejected,held,mixed],tracked_preferred_forms:[],unparseable_forms:[],known_forms:[],
    issue:388,corpus_sha256:'fixture',moe:{snapshot:'moe'},baseline:{source_characters:50,article_count:2},
    context_exclusions:{phrases:[],skipped_anchor_occurrences:0},
    machine_screening:{sha256:'screen-hash',models:['gpt-6-luna'],occurrences:4,decision_counts:{reject:2,keep:1,hold:1}}};
  const page=vm.createContext({data,document,setTimeout,localStorage:{getItem(){return JSON.stringify({
    ignored:[],decisions:{the:{preferred_form:'the',approved:true,word_id:'',canonical_choice_id:'',
      alternate_choice_ids:[],identity_note:'',import_mode:'source_anchor'}}});},setItem(){}}});
  vm.runInContext(fs.readFileSync(new URL('./written_forms.js',import.meta.url),'utf8')+'\n'+
    fs.readFileSync(new URL('./review.js',import.meta.url),'utf8'),page);
  assert.equal(vm.runInContext('excluded(data.groups[0])',page),true);
  assert.equal(vm.runInContext('approvable(data.groups[0])',page),false);
  assert.equal(vm.runInContext('excluded(data.groups[1])',page),false);
  assert.equal(vm.runInContext('reviewExport().approvals.length',page),0);
  assert.equal(vm.runInContext('reviewExport().screening_sha256',page),'screen-hash');
  assert.doesNotMatch(nodes.get('rows').innerHTML,/data-key="the"/);
  assert.match(nodes.get('rows').innerHTML,/Model hold/);
  assert.match(nodes.get('rows').innerHTML,/Model-rejected occurrences \(1\)/);
  assert.match(nodes.get('screening-policy').textContent,/2 rejected; 1 held/);
  nodes.get('showKnown').checked=true;
  vm.runInContext('render()',page);
  assert.match(nodes.get('rows').innerHTML,/Model rejected/);
  assert.match(nodes.get('rows').innerHTML,/English quotation/);
});
