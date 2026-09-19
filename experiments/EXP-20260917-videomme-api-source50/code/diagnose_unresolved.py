#!/usr/bin/env python3
"""Freeze source_unresolved gate failures, exact API inputs and result hashes."""
from pathlib import Path
import json
from run import OUT,REPO,read,sha,dump,now

def gates(o,a):
 checks={'has_facts':bool(o.get('facts')),'observer_complete':o.get('coverage')=='complete','observer_no_missing':not o.get('missing_zh'),'observer_groups_resolved':not o.get('groups_unresolved'),'observer_facts_supported':all(f['status']=='supported' for f in o.get('facts',[])),'observer_relations_supported':all(r['status']=='supported' for r in o.get('relations',[])),'auditor_question_supported':a.get('question_supported') is True,'auditor_reference_matches':a.get('reference_matches') is True,'auditor_relations_supported':a.get('relations_supported') is True,'auditor_facts_supported':all(f['supported'] for f in a.get('fact_checks',[])),'auditor_no_missing':not a.get('missing_zh'),'auditor_no_reference_issues':not a.get('reference_issues_zh')}
 if all(checks.values()):checks['grouping_status_consistent']=a.get('requires_multiple')=='no' or (a.get('requires_multiple')=='yes' and len(a.get('semantic_groups',[]))>=2)
 return [k for k,v in checks.items() if not v]

def main():
 rows=[]
 for path in sorted((OUT/'results').glob('*.json')):
  r=read(path)
  if r['status']!='source_unresolved':continue
  o=r.get('observation',r.get('coarse_observation',{}));a=r.get('audit',{});inp=OUT/'inputs'/path.name;q=read(inp);stages={}
  for field in ['coarse_call','refined_call','audit_call']:
   if field not in r:continue
   request=Path(r[field]).parent/'request.json';req=read(request);h=json.loads(req['payload']['messages'][1]['content'][0]['text']);stages[field]={'request_file':str(request),'request_sha256':sha(request),'has_options':'options' in h,'has_reference':'reference_answer' in h,'question':h['question']}
  rows.append({'qid':r['qid'],'result_file':str(path),'result_sha256':sha(path),'input_file':str(inp),'input_sha256':sha(inp),'question':q['question'],'options':q['options'],'reference_answer':q['reference_answer'],'observed_answer':o.get('answer'),'coverage':o.get('coverage'),'observer_missing':o.get('missing_zh'),'uncertain_facts':[f for f in o.get('facts',[]) if f['status']!='supported'],'audit':a,'false_acceptance_gates':gates(o,a),'request_fields':stages})
 report={'created_at':now(),'questions':len(rows),'no_new_api_calls':True,'no_original_images_viewed':True,'original_results_unchanged':True,'records':rows}
 for path in [REPO/'terminal_source_unresolved_audit.json',OUT/'diagnostics/terminal_source_unresolved_audit.json']:
  if path.exists():raise FileExistsError(path)
 for path in [REPO/'terminal_source_unresolved_audit.json',OUT/'diagnostics/terminal_source_unresolved_audit.json']:dump(path,report)
 print(json.dumps([{'qid':r['qid'],'failed_gates':r['false_acceptance_gates']} for r in rows],ensure_ascii=False))
if __name__=='__main__':main()
