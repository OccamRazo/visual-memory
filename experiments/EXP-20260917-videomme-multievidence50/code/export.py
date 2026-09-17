#!/usr/bin/env python3
"""Offline integrity validation and source-only evidence package export."""
import collections,csv,hashlib,html,json,os,re,zipfile
import pysrt
from pathlib import Path
from types import MethodType
from run import OUT,REPO,INV,Pipeline,read,dump,rows,sha,safe,canon,now,gb

def main():
 p=object.__new__(Pipeline)
 def bind_content(record):
  version=read(OUT/'code_snapshots'/record['implementation']/'protocol.json')['version']
  p.group_content=MethodType(gb.Runner.group_content if version in ['1.0','1.1'] else Pipeline.group_content,p)
  return 'closed (legacy nonoverlapping cores)' if version in ['1.0','1.1'] else 'half-open [start,end)'
 questions={q['qid']:q for q in rows(INV/'questions.jsonl')};caps=collections.defaultdict(list)
 for c in rows(INV/'candidates.jsonl'):caps[c['video_id']].append([f"C{int(c['source_id'].split(':')[-1]):05}",c['start_s'],c['end_s'],c['text']])
 records=[];excluded=[];checks=collections.Counter();images={};models=set();reviews=[];original_subs={};subtitle_hash={}
 with zipfile.ZipFile(gb.DATA/'subtitle.zip') as archive:
  for vid in caps:
   member=f'subtitle/{vid}.srt'
   if member not in archive.namelist():original_subs[vid]=[];subtitle_hash[vid]=None;continue
   raw=archive.read(member);subtitle_hash[vid]=hashlib.sha256(raw).hexdigest()
   original_subs[vid]=[{'subtitle_id':f'S{i:05}','start_s':s.start.ordinal/1000,'end_s':s.end.ordinal/1000,'text':re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]*>','',s.text))).strip()} for i,s in enumerate(pysrt.from_string(raw.decode('utf-8-sig',errors='replace')))]
 for file in sorted((OUT/'results').glob('*.json')):
  r=read(file);rp=OUT/'reviews'/file.name
  if not rp.exists() or read(rp)['decision']!='confirmed':excluded.append({'qid':r['qid'],'status':r['status'],'review':read(rp) if rp.exists() else None,'reason':r.get('reason',r.get('error'))});continue
  rv=read(rp);assert rv['result_sha256']==sha(file);assert r['status']=='multi_verified_candidate';reviews.append({'file':str(rp),'sha256':sha(rp),'result_sha256':sha(file)})
  bind_content(r)
  assert r['question_original']==questions[r['qid']]['original_question'] and r['official_answer']==questions[r['qid']]['reference_draft'];checks['unchanged_original_questions']+=1
  assert r['captions_supplied']==r['captions_total']==len(caps[r['video_id']])
  for call in [z['localization_call'] for z in r['rounds']]+[r['countersearch_call']]:
   cp=Path(call);req=read(cp.parent/'request.json')['payload'];header=json.loads(req['messages'][1]['content'][0]['text']);assert header['all_captions']==caps[r['video_id']]
   assert req['model']=='qwen3.8-flash';models.add(read(cp)['resolved_model']);checks['full_caption_request_payloads']+=1
  package=read(r['package_file']);assert sha(r['package_file'])==r['package_sha256']
  assert package['subtitles']==original_subs[r['video_id']] and package['subtitle_member_sha256']==subtitle_hash[r['video_id']];checks['original_subtitle_packages']+=1
  observer_request=read(Path(r['observer_call']).parent/'request.json')['payload'];observer_header=json.loads(observer_request['messages'][1]['content'][0]['text'])
  expected_h,expected_frames=p.group_content({'question':r['question'],'required_facts':r['required_facts']},package);expected_h.pop('required_facts')
  assert observer_header==expected_h and observer_request['model']=='qwen3.8-flash';checks['answer_blind_observer_requests']+=1
  assert [x['image_url']['url'] for x in observer_request['messages'][1]['content'] if x['type']=='image_url']==['sha256:'+f['sha256'] for f in expected_frames]
  assert r['observer']['package_sufficiency']=='complete' and not r['observer']['question_ambiguous']
  audit=r['audit'];assert audit['standalone_question_valid'] and audit['rubric_valid'] and audit['reference_status']=='supported' and audit['segmentation_status']=='pass' and audit['all_facts_supported'] and audit['scope_adequate']
  assert len(audit['group_checks'])==len(r['groups']) and all(all(g.get(k) is True for k in ['continuous_occurrence','bounds_adequate','source_supported']) for g in audit['group_checks'])
  assert len(audit['fact_support'])==len(r['required_facts']) and all(f['status']=='supported' and f['supported_by'] for f in audit['fact_support'])
  assert all(r['countersearch'].get(k) is False for k in ['single_group_alternative_possible','artificial_split_risk','rubric_overreach','unresolved_scope'])
  fs={f['frame_id']:f for f in package['frames']};ss={s['subtitle_id']:s for s in package['subtitles']}
  prev=-1
  for g in r['groups']:
   assert prev<=g['start_s']<g['end_s'];prev=g['end_s']
   for fid in g['frame_ids']:assert g['start_s']<=fs[fid]['actual_pts_s']<=g['end_s'];checks['contained_frame_anchors']+=1
   for sid in g['subtitle_ids']:assert g['start_s']-.001<=ss[sid]['start_s']<ss[sid]['end_s']<=g['end_s']+.001;checks['contained_subtitle_anchors']+=1
  for f in package['frames']:images[f['path']]=f['sha256']
  abl=r['subset_validation'];selected=abl['selected_group_ids'];assert len(selected)>=2 and abl['status']=='multi_group_verified'
  tests={tuple(sorted(t['group_ids'])):t for t in abl['tests']}
  assert tests[tuple(sorted(selected))]['supported']
  for g in r['groups']:assert not tests[(g['id'],)]['supported'];checks['candidate_singleton_failures']+=1
  for g in selected:assert not tests[tuple(sorted(set(selected)-{g}))]['supported'];checks['retained_group_deletion_failures']+=1
  for t in abl['tests']:
   if t['supported']:assert t['result'].get('all_facts_supported') is True and t['result'].get('scope_adequate') is True and not t['result'].get('missing_zh') and all(f.get('status')=='supported' for f in t['result']['facts'])
   if not t['call_file']:continue
   h,frames=p.group_content({'question':r['question'],'required_facts':r['required_facts']},package,t['group_ids'])
   request=read(Path(t['call_file']).parent/'request.json')['payload'];actual=json.loads(request['messages'][1]['content'][0]['text'])
   for key in ['question','required_facts','intervals','note']:assert actual[key]==h[key]
   assert [i['image_url']['url'] for i in request['messages'][1]['content'] if i['type']=='image_url']==['sha256:'+f['sha256'] for f in frames]
   assert not any('proposed_group' in it for it in actual['intervals'])
   af={f['frame_id'] for f in frames};ass={s['subtitle_id'] for it in h['intervals'] for s in it['subtitles']}
   for fact in t['result']['facts']:
    assert set(fact.get('frame_ids',[]))<=af and set(fact.get('subtitle_ids',[]))<=ass
    if 'status' not in fact:
     # Legacy one-fact response explicitly rejects support and scope and gives
     # the missing source. Preserve raw omission; never infer a positive claim.
     assert len(r['required_facts'])==len(t['result']['facts'])==1 and not t['supported'] and t['result'].get('all_facts_supported') is False and t['result'].get('scope_adequate') is False and t['result'].get('missing_zh')
     checks['legacy_explicit_negative_with_omitted_fact_status']+=1
    if fact.get('status')=='supported':assert fact.get('frame_ids') or fact.get('subtitle_ids')
    required=next(f.get('endpoints',[]) for f in r['required_facts'] if f['id']==fact['fact_id'])
    if required:
     endpoints=fact['endpoint_evidence'];assert {x['endpoint_id'] for x in endpoints}=={x['id'] for x in required} and len(endpoints)==len(required)
     for endpoint in endpoints:
      assert set(endpoint.get('frame_ids',[]))<=af and set(endpoint.get('subtitle_ids',[]))<=ass
      if endpoint['status']=='supported':assert endpoint.get('frame_ids') or endpoint.get('subtitle_ids')
     if fact.get('status')=='supported':assert all(x['status']=='supported' for x in endpoints)
   checks['isolated_subset_requests']+=1
  records.append(r)
 for path,digest in images.items():assert sha(path)==digest
 checks['unique_frame_hashes']=len(images)
 # Freeze final selection in priority order (all confirmed are retained, >= target).
 rank={x['qid']:i for i,x in enumerate(read(OUT/'ranking.json'))};records.sort(key=lambda r:rank[r['qid']])
 final=OUT/'final';final.mkdir(exist_ok=True)
 exported=[];group_rows=[];pages=[];md=['# Video-MME long 多证据题与证据组','',f'导出时间：{now()}。AI源复核，不是人工金标。','']
 for n,r in enumerate(records,1):
  semantics=bind_content(r)
  package=read(r['package_file']);selected=r['subset_validation']['selected_group_ids'];e={'qid':r['qid'],'video_id':r['video_id'],'original_question':r['question_original'],'question':r['question'],'official_answer':r['official_answer'],'required_facts':r['required_facts'],'groups':[],'necessary_group_ids':selected,'model':'qwen3.8-flash','human_reviewed':False,'result_file':str(OUT/'results'/f"{safe(r['qid'])}.json"),'result_sha256':sha(OUT/'results'/f"{safe(r['qid'])}.json")}
  e.update(original_options=questions[r['qid']]['original_options'],reference_answer=r['localization'].get('reference_answer'),task_labels=r['localization'].get('task_labels'),review_file=str(OUT/'reviews'/f"{safe(r['qid'])}.json"))
  parts=[f'<details><summary>{n}. {html.escape(r["qid"])} — {html.escape(r["question"])}</summary><p>参考：{html.escape(r["official_answer"])}</p>'];md += [f'## {n}. {r["qid"]}',r['question'],'',f'参考：{r["official_answer"]}','']
  for g in r['groups']:
   if g['id'] not in selected:continue
   h,fs=p.group_content({'question':r['question'],'required_facts':r['required_facts']},package,[g['id']]);chunk=h['intervals'][0]
   source={'qid':r['qid'],'group_id':g['id'],'start_s':g['start_s'],'end_s':g['end_s'],'interval_semantics':semantics,'source_video':package['source_video'],'frames':fs,'subtitles':chunk['subtitles'],'generated_captions_in_evidence':False}
   target=final/'group_packages'/safe(r['qid'])/f"{g['id']}.json";dump(target,source)
   row={'qid':r['qid'],'group_id':g['id'],'start_s':g['start_s'],'end_s':g['end_s'],'label_zh':g['label_zh'],'package_file':str(target),'package_sha256':sha(target)};e['groups'].append(row);group_rows.append(row)
   md += [f'- **{g["id"]} {g["start_s"]:.3f}–{g["end_s"]:.3f}秒**：{g["label_zh"]}。{g.get("episode_reason_zh","")}']
   video=os.path.relpath(package['source_video'],final);link=os.path.relpath(target,final)
   parts += [f'<h3>{g["id"]} · {g["start_s"]:.3f}–{g["end_s"]:.3f}s · {html.escape(g["label_zh"])}</h3><p>{html.escape(g.get("episode_reason_zh",""))}</p><a href="{html.escape(link)}">原始证据包</a><br><video controls preload="none" src="{html.escape(video)}#t={g["start_s"]},{g["end_s"]}"></video><div class="frames">']
   for f in fs:parts += [f'<figure><img loading="lazy" src="{html.escape(os.path.relpath(f["path"],final))}"><figcaption>{f["frame_id"]} {f["actual_pts_s"]:.3f}s</figcaption></figure>']
   parts += ['</div><details><summary>原字幕</summary>']+[f'<p>{s["subtitle_id"]} {s["start_s"]:.3f}–{s["end_s"]:.3f} {html.escape(s["text"])}</p>' for s in chunk['subtitles']]+['</details>']
  parts += ['</details>'];pages.extend(parts);exported.append(e);md+=['']
 (final/'multievidence.jsonl').write_text(''.join(canon(r)+'\n' for r in exported));(final/'groups.jsonl').write_text(''.join(canon(r)+'\n' for r in group_rows));(final/'questions_and_groups.md').write_text('\n'.join(md)+'\n')
 with (final/'groups.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['qid','group_id','start_s','end_s','label_zh','package_file','package_sha256']);w.writeheader();w.writerows(group_rows)
 (final/'index.html').write_text('<!doctype html><html lang="zh"><meta charset="utf-8"><title>Video-MME 多证据题</title><style>body{font:16px sans-serif;max-width:1250px;margin:32px auto;padding:16px}summary{cursor:pointer;padding:12px;background:#eef2f6}details{margin:12px 0}video{max-width:680px;width:100%}.frames{display:flex;flex-wrap:wrap}figure{margin:8px;width:240px}img{max-width:240px}</style><h1>Video-MME long 多证据题</h1><p>每题通过原源支持与单组/删组验证。AI复核，非人工金标；区间播放原视频，未另存MP4。</p>'+''.join(pages)+'</html>')
 allrs=[read(f) for f in (OUT/'results').glob('*.json')];calls=[read(f) for f in (OUT/'calls').glob('*/*/*/attempt-*.json')]
 count=collections.Counter(len(r['necessary_group_ids']) for r in exported)
 summary={'completed_at':now(),'status':'complete' if len(exported)>=50 else 'incomplete','target':50,'confirmed_questions':len(exported),'videos':len({r['video_id'] for r in exported}),'necessary_groups':len(group_rows),'group_count_histogram':dict(sorted(count.items())),'mean_groups':len(group_rows)/len(exported) if exported else None,'processed_questions':len(allrs),'dispositions':dict(collections.Counter(r['status'] for r in allrs)),'dataset_file':str(final/'multievidence.jsonl'),'dataset_sha256':sha(final/'multievidence.jsonl'),'models':sorted({x.get('resolved_model') for x in calls if x.get('resolved_model')}),'api_attempts':len(calls),'api_failures':sum(x['status']=='failed' for x in calls),'usage':{k:sum((x.get('usage') or {}).get(k,0) for x in calls) for k in ['prompt_tokens','completion_tokens','total_tokens']},'human_reviewed':False}
 if (REPO/'pause_record.json').exists():
  pause=read(REPO/'pause_record.json')
  if pause['status']=='paused_by_user':summary.update(status='paused_by_user',paused_at=pause['paused_at'],target_met=len(exported)>=50)
 validation={'passed':True,'checked_at':now(),**dict(checks),'confirmed_questions':len(exported),'target_reached':len(exported)>=50,'browser_playback_tested':False}
 dump(final/'summary.json',summary);dump(REPO/'summary.json',summary);dump(final/'validation.json',validation);dump(REPO/'validation.json',validation);dump(final/'excluded.json',excluded)
 reproduction={'input_manifest':read(OUT/'input_manifest.json'),'files':{str(f.relative_to(REPO)):sha(f) for f in sorted(REPO.rglob('*')) if f.is_file() and (any(str(f.relative_to(REPO)).startswith(x) for x in ['code/','question_constraints/','rubric_refinements/','protocol-history/']) or f.name in ['protocol.json','environment.json','execution_amendments.json','formal_order_rubrics.json','technical_retry_v17.json','supplemental_candidates_v18.json','trailing_frame_check.json','pause_record.json']) and '__pycache__' not in str(f)},'reviews':reviews,'fresh_model_output_deterministic':False}
 dump(REPO/'reproducibility.json',reproduction);dump(final/'reproducibility.json',reproduction)
 prev=read('/home/baorui/projects/visual-memory/experiments/EXP-20260917-videomme-evidence60/future_test_exclusions.json')
 dump(REPO/'future_test_exclusions.json',{'reason':'Question-only screening saw all 900 QA; full-caption/source-contacted videos below are not unseen-video test candidates. Prior exclusions retained separately.','question_screened_qids':list(questions),'this_run_caption_source_video_ids':sorted({r['video_id'] for r in allrs}),'prior_exclusions':prev})
 print(canon(summary))
if __name__=='__main__':main()
