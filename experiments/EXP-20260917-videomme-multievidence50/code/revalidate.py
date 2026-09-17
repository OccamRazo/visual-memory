#!/usr/bin/env python3
"""Revalidate reviewed rubric/core corrections; preserve every superseded result."""
import argparse,fcntl,json
from pathlib import Path
from run import Pipeline,OUT,REPO,read,dump,sha,safe,canon,now
ap=argparse.ArgumentParser();ap.add_argument('qid');args=ap.parse_args();qid=args.qid if args.qid.startswith('videomme:') else 'videomme:'+args.qid
rules=REPO/'rubric_refinements'/f'{safe(qid)}.json';override=read(rules);p=Pipeline();file=OUT/'results'/f'{safe(qid)}.json'
lock=OUT/'locks'/f'{safe(qid)}.lock';lock.parent.mkdir(parents=True,exist_ok=True)
with lock.open('a') as handle:
 fcntl.flock(handle,fcntl.LOCK_EX)
 old=read(file);oldsha=sha(file)
 assert override['source_result_sha256']==oldsha
 rec=json.loads(canon(old));rec.update(implementation=p.impl,required_facts=override['required_facts'],rubric_refinement_file=str(rules),rubric_refinement_sha256=sha(rules),revalidated_from_result_sha256=oldsha,revalidation_started_at=now())
 frozen=OUT/'manual_inputs'/safe(qid)/(sha(rules)+'.json');dump(frozen,override);rec['rubric_refinement_file']=str(frozen)
 q=p.questions[qid];r={'qid':qid,'video_id':old['video_id'],'question':old['question'],'required_facts':override['required_facts'],'task_labels':old['localization']['task_labels']};package=read(old['package_file'])
 if override.get('question'):
  r['question']=override['question'];rec['question']=override['question']
 if override.get('core_overrides'):
  nom=json.loads(canon(old['localization']))
  for g in nom['groups']:
   if g['id'] in override['core_overrides']:
    g.update(override['core_overrides'][g['id']])
    g['key_times_s']=[t for t in g.get('key_times_s',[]) if g['start_s']<=t<g['end_s']]
  bank,groups,normal=p.initial_source(q,nom)
  package,ppath=p.project(r,bank,groups,99)
  rec.update(groups=groups,package_file=str(ppath),package_sha256=sha(ppath),source_refinement_log=normal)
 if override.get('core_overrides') or r['question']!=old['question']:
  oh,of=p.group_content(r,package);oh.pop('required_facts')
  obs,opath=p.call(qid,'observe',oh,of)
  allowedf={f['frame_id'] for f in of};alloweds={s['subtitle_id'] for it in oh['intervals'] for s in it['subtitles']}
  assert all(set(x.get('frame_ids',[]))<=allowedf and set(x.get('subtitle_ids',[]))<=alloweds for x in obs.get('observations',[])+obs.get('relations',[]))
  rec.update(observer=obs,observer_call=opath)
 audit,apath=p.checked_audit(r,package,q);rec.update(audit=audit,audit_call=apath)
 passed=all([rec['observer'].get('package_sufficiency')=='complete',not rec['observer'].get('question_ambiguous',True),audit.get('standalone_question_valid'),audit.get('rubric_valid'),audit.get('reference_status')=='supported',audit.get('segmentation_status')=='pass',audit.get('all_facts_supported'),audit.get('scope_adequate'),all(all(g.get(k) is True for k in ['continuous_occurrence','bounds_adequate','source_supported']) for g in audit.get('group_checks',[]))])
 if passed:
  ablation=p.ablate(r,package,audit);rec['subset_validation']=ablation
  if ablation['status']=='multi_group_verified':
   h=p.full_timeline(q);h.update(short_question=r['question'],required_facts=r['required_facts'],proposed_groups=[{'start_s':g['start_s'],'end_s':g['end_s'],'label_zh':g['label_zh']} for g in rec['groups']])
   counter,cp=p.call(qid,'countersearch',h);rec.update(countersearch=counter,countersearch_call=cp)
   rec['status']='qualified_countersearch' if any(counter.get(k,True) for k in ['single_group_alternative_possible','artificial_split_risk','rubric_overreach','unresolved_scope']) else 'multi_verified_candidate'
  else:rec['status']='rejected_'+ablation['status']
 else:rec['status']='rejected_source_or_segmentation'
 rec['reason']='Reviewed rubric/core refinement, followed by renewed source audit, ablation and full-caption countersearch; see status.'
 rec['rounds'].append({'round':'minimal_rubric_revalidation','localization_call':old['localization_call'],'audit_call':apath,'package_file':rec['package_file'],'reason_zh':override['reason_zh']})
 rec['sheets']=p.sheet(package,qid)
 rec['completed_at']=now();dump(OUT/'superseded_results'/safe(qid)/(oldsha+'.json'),old)
 review=OUT/'reviews'/file.name
 if review.exists():dump(OUT/'superseded_reviews'/safe(qid)/(sha(review)+'.json'),read(review));review.unlink()
 dump(file,rec);print(canon({'qid':qid,'status':rec['status'],'needed':rec.get('subset_validation',{}).get('irreducible_group_count')}),flush=True)
