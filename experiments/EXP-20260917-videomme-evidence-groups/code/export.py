"""Validate and export frozen 60-Q temporal evidence annotations, including flags."""
import collections,datetime,hashlib,html,json,os,statistics,re,zipfile,csv
import pysrt
from pathlib import Path
from group import OUT,REPO,DATA,Runner,read,dump,sha,canon,safe,ts

def main():
 manifest=read(OUT/'input_manifest.json');assert sha(manifest['source_file'])==manifest['source_sha256']
 original={r['qid']:r for r in map(json.loads,Path(manifest['source_file']).read_text().splitlines())};assert len(original)==60
 results={r['qid']:r for r in (read(p) for p in (OUT/'results').glob('*.json'))};reviews={r['qid']:r for r in (read(p) for p in (OUT/'reviews').glob('*.json'))}
 assert set(results)==set(original)==set(reviews),'All 60 results and current-session reviews required'
 rows=[];frames_checked={};subcount=0;core_included=0;subtitle_members={};subset_checks=0
 with zipfile.ZipFile(DATA/'subtitle.zip') as archive:
  for vid in {r['video_id'] for r in original.values()}:
   member=f'subtitle/{vid}.srt'
   if member not in archive.namelist():subtitle_members[vid]=(None,[]);continue
   raw=archive.read(member)
   normalized=[{'subtitle_id':f'S{i:05}','start_s':s.start.ordinal/1000,'end_s':s.end.ordinal/1000,'text':re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]*>','',s.text))).strip()} for i,s in enumerate(pysrt.from_string(raw.decode('utf-8-sig',errors='replace')))]
   subtitle_members[vid]=(hashlib.sha256(raw).hexdigest(),normalized)
 corrections=read(REPO/'corrections.json') if (REPO/'corrections.json').exists() else {}
 for q in manifest['qids']:
  r=results[q];review=reviews[q];assert r['status']!='processing_failed',q;assert review['result_sha256']==sha(review['result_file'])
  assert r['question']==original[q]['question'] and r['required_facts']==original[q]['required_facts']
  p=read(r['package_file']);assert sha(r['package_file'])==r['package_sha256'];assert p['groups']==r['groups'];assert p['generated_captions_in_evidence'] is False
  assert (p['subtitle_member_sha256'],p['subtitles'])==subtitle_members[r['video_id']],('original SRT mismatch',q)
  fs={f['frame_id']:f for f in p['frames']};ss={s['subtitle_id']:s for s in p['subtitles']};duration=read(p['source_bank_file'])['duration_s'];subcount+=len(ss)
  prior_end=-1
  for g in r['groups']:
   assert 0<=g['start_s']<g['end_s']<=duration+.001 and g['start_s']>prior_end;prior_end=g['end_s']
   assert g['review_start_s']<=g['start_s'] and g['review_end_s']>=g['end_s']
   assert g['frame_ids'] or g['subtitle_ids']
   for fid in g['frame_ids']:assert fid in fs and g['start_s']-.002<=fs[fid]['actual_pts_s']<=g['end_s']+.002
   for sid in g['subtitle_ids']:assert sid in ss and g['start_s']-.002<=ss[sid]['start_s'] and ss[sid]['end_s']<=g['end_s']+.002
   core_included+=len(g['frame_ids'])+len(g['subtitle_ids'])
  for f in p['frames']:
   if f['path'] not in frames_checked:assert sha(f['path'])==f['sha256'];frames_checked[f['path']]=f['sha256']
  gids={g['id'] for g in r['groups']};sv=r.get('subset_validation',{});selected=sv.get('selected_group_ids',[]);assert set(selected)<=gids
  for t in sv.get('tests',[]):
   if not t.get('call_file'):assert not t['group_ids'] and not t['supported'];continue
   header,source_frames=Runner.__new__(Runner).group_content(r,p,ids=t['group_ids'])
   request=read(Path(t['call_file']).parent/'request.json')['payload'];content=request['messages'][1]['content'];sent=json.loads(content[0]['text'])
   assert sent['intervals']==header['intervals'] and sent['required_facts']==r['required_facts']
   assert all('proposed_group' not in part for part in sent['intervals'])
   supplied_frames={f['frame_id'] for f in source_frames};supplied_subs={s['subtitle_id'] for part in header['intervals'] for s in part['subtitles']}
   assert [x['image_url']['url'] for x in content if x['type']=='image_url']==['sha256:'+sha(f['path']) for f in source_frames]
   for fact in t['result']['facts']:
    assert set(fact.get('frame_ids',[]))<=supplied_frames and set(fact.get('subtitle_ids',[]))<=supplied_subs,(q,'excluded source citation')
   subset_checks+=1
  if review['decision']=='confirmed':
   assert r['status']=='review_candidate' and sv['status']=='source_subset_verified'
   tests={tuple(t['group_ids']):t['supported'] for t in sv['tests']};assert tests[tuple(sorted(selected))]
   for gid in selected:assert tests[tuple(sorted(set(selected)-{gid}))] is False
   for a,passed in tests.items():
    if passed:
     assert not any(set(a)<=set(b) and not outcome for b,outcome in tests.items()), 'Non-monotonic source evaluator: qualify instead of claiming irreducibility'
  rows.append({'qid':q,'video_id':r['video_id'],'question':r['question'],'reference_answer':original[q]['reference_answer'],'required_facts':r['required_facts'],'groups':r['groups'],'candidate_group_count':len(r['groups']),'validated_irreducible_group_ids':selected if review['decision']=='confirmed' else None,'validated_irreducible_group_count':len(selected) if review['decision']=='confirmed' else None,'grouping_status':review['decision'],'review_note_zh':review['note_zh'],'boundary_limitations_zh':r.get('audit',{}).get('boundary_limitations_zh'),'fact_support_sets':r.get('audit',{}).get('fact_support'),'subset_validation':sv,'package_file':r['package_file'],'package_sha256':r['package_sha256'],'result_file':review['result_file'],'result_sha256':review['result_sha256'],'review_file':str(OUT/'reviews'/f'{safe(q)}.json'),'review_sha256':sha(OUT/'reviews'/f'{safe(q)}.json'),'human_reviewed':False,'minimum_scope':'Current supplied source collection and evaluator; inclusion-minimal, not global/video-wide minimum.'})
 final=OUT/'final';final.mkdir(exist_ok=True);data=final/'evidence_groups60.jsonl'
 for r in rows:
  if r['qid'] in corrections:
   changes=corrections[r['qid']];r['groups']=json.loads(canon(r['groups']))
   for g in r['groups']:g.update(changes.get('group_fields',{}).get(g['id'],{}))
   r['annotation_corrections']=changes
 data.write_text(''.join(canon(r)+'\n' for r in rows))
 flat=[]
 projector=Runner.__new__(Runner)
 for r in rows:
  p=read(r['package_file'])
  for g in r['groups']:
   header,frames=projector.group_content(r,p,ids=[g['id']])
   package={'qid':r['qid'],'group_id':g['id'],'video_id':r['video_id'],'start_s':g['start_s'],'end_s':g['end_s'],'frames':frames,'subtitles':header['intervals'][0]['subtitles'],'anchor_frame_ids':g['frame_ids'],'anchor_subtitle_ids':g['subtitle_ids'],'source_video':p['source_video'],'subtitle_member_sha256':p['subtitle_member_sha256'],'parent_package_file':r['package_file'],'parent_package_sha256':r['package_sha256'],'reference_answer_included':False,'generated_captions_in_evidence':False}
   path=final/'group_packages'/safe(r['qid'])/f'{g["id"]}.json';dump(path,package)
   flat.append({'qid':r['qid'],'video_id':r['video_id'],**g,'selected_for_verified_subset':g['id'] in (r['validated_irreducible_group_ids'] or []),'group_package_file':str(path),'group_package_sha256':sha(path)})
 (final/'groups.jsonl').write_text(''.join(canon(g)+'\n' for g in flat))
 with (final/'groups.csv').open('w',newline='',encoding='utf-8-sig') as stream:
  writer=csv.DictWriter(stream,fieldnames=['qid','video_id','id','start_s','end_s','label_zh','selected_for_verified_subset','group_package_file'])
  writer.writeheader();writer.writerows({k:g[k] for k in writer.fieldnames} for g in flat)
 progress=read(OUT/'progress.json');counts=[r['candidate_group_count'] for r in rows];confirmed=[r for r in rows if r['grouping_status']=='confirmed'];needed=[r['validated_irreducible_group_count'] for r in confirmed]
 pilot_calls=[read(p) for p in OUT.parent.glob('calls/*/*/*/attempt-*.json')]
 pilot_api={'api_attempts':len(pilot_calls),'api_failures':sum(c['status']=='failed' for c in pilot_calls),'usage':{k:sum((c.get('usage') or {}).get(k,0) for c in pilot_calls) for k in ['prompt_tokens','completion_tokens','total_tokens']},'note':'Preserved v1.0 methodological pilot; excluded from final grouping counts, included in experiment cost accounting.'}
 stats=lambda values:{'n':len(values),'total':sum(values),'mean':statistics.mean(values) if values else None,'median':statistics.median(values) if values else None,'min':min(values) if values else None,'max':max(values) if values else None,'histogram':dict(sorted(collections.Counter(values).items()))}
 summary={'status':'complete','completed_at':datetime.datetime.now().astimezone().isoformat(),'questions':60,'confirmed':len(confirmed),'qualified':60-len(confirmed),'candidate_groups':stats(counts),'verified_irreducible_groups':stats(needed),'multi_group_questions_among_confirmed':sum(n>=2 for n in needed),'source_dataset_sha256':manifest['source_sha256'],'dataset_file':str(data),'dataset_sha256':sha(data),'api':{k:progress[k] for k in ['api_attempts','api_failures','usage','models']},'preserved_v1_pilot_api':pilot_api,'human_reviewed':False,'minimum_scope':'Inclusion-minimal within sampled evidence, not guaranteed minimum over all possible groups in the full video.'}
 validation={'passed':True,'questions':60,'all_original_questions_and_rubrics_preserved':True,'source_anchors_checked':core_included,'unique_frame_hashes_checked':len(frames_checked),'original_subtitle_members_checked':len(subtitle_members),'raw_subset_payloads_checked':subset_checks,'excluded_group_content_absent_from_subset_payloads':True,'all_group_intervals_disjoint_and_citations_contained':True,'confirmed_subsets_and_every_single_group_deletion_have_results':True,'no_captions_as_evidence':True,'checked_at':datetime.datetime.now().astimezone().isoformat()}
 for name,obj in [('summary.json',summary),('validation.json',validation),('manifest.json',[{'qid':r['qid'],'candidate_groups':r['candidate_group_count'],'verified_irreducible_groups':r['validated_irreducible_group_count'],'status':r['grouping_status'],'result_sha256':r['result_sha256']} for r in rows])]:dump(final/name,obj);dump(REPO/name,obj)
 sources=[Path(manifest['source_file']),REPO/'protocol.json',OUT/'input_manifest.json']+[REPO/name for name in ['corrections.json','adjudication_rules.json','environment.json','implementation_fixes.json'] if (REPO/name).exists()]+sorted((REPO/'group_overrides').glob('*.json'))+sorted((REPO/'evaluation_notes').glob('*.json'))+sorted((REPO/'adjudication_history').glob('*.json'))+sorted((REPO/'code').glob('*.py'))+sorted((REPO/'code/prompts').glob('*.txt'))
 repro={'files':[{'path':str(p),'sha256':sha(p)} for p in sources],'code_snapshots':str(OUT/'code_snapshots'),'raw_calls':str(OUT/'calls'),'source_bank':str(OUT/'sources'),'review_records':str(OUT/'reviews'),'cache_replay_exact':True,'fresh_model_calls_deterministic':False};dump(REPO/'reproducibility.json',repro);dump(final/'reproducibility.json',repro)
 table=['# 60题证据组索引','','候选组并非全部必要。通过删组的集合仅限当前源证据和核验器；存疑题不报告可靠必要组数。完整原帧/字幕见同目录 index.html 和 group_packages。','','|题号|问题|候选组（分:秒）|通过复核后保留|状态|','|---|---|---|---|---|']
 for r in rows:
  intervals='；'.join(f'{g["id"]} {ts(g["start_s"])}–{ts(g["end_s"])}' for g in r['groups'])
  table.append('|'+ '|'.join([r['qid'],r['question'].replace('|','/'),intervals,', '.join(r['validated_irreducible_group_ids'] or []) or '存疑',r['grouping_status']])+'|')
 (final/'groups60.md').write_text('\n'.join(table)+'\n')
 dump(final/'qualified_cases.json',[{'qid':r['qid'],'reason_zh':r['review_note_zh']} for r in rows if r['grouping_status']=='qualified'])
 esc=html.escape;sections=[]
 for r in rows:
  p=read(r['package_file']);fs={f['frame_id']:f for f in p['frames']};ss={s['subtitle_id']:s for s in p['subtitles']};pieces=[]
  for g in r['groups']:
   _,shown=projector.group_content(r,p,ids=[g['id']])
   imgs=''.join(f'<figure><img loading="lazy" src="{esc(os.path.relpath(f["path"],final))}"><figcaption>{f["frame_id"]} {ts(f["actual_pts_s"])}</figcaption></figure>' for f in shown)
   subtitles=''.join(f'<p>{esc(x)} [{ts(ss[x]["start_s"])}–{ts(ss[x]["end_s"])}] {esc(ss[x]["text"])}</p>' for x in g['subtitle_ids'])
   video=esc(os.path.relpath(p['source_video'],final))+f'#t={g["start_s"]},{g["end_s"]}'
   package_link=f'group_packages/{safe(r["qid"])}/{g["id"]}.json'
   pieces.append(f'<details><summary>{g["id"]} [{ts(g["start_s"])}–{ts(g["end_s"])}] {esc(g["label_zh"])}</summary><p>{esc(g["episode_reason_zh"])}</p><p>内容：{esc(g["source_summary_zh"])}</p><p>边界：{esc(g.get("boundary_uncertainty_zh", ""))}</p><p><a href="{package_link}">该组原始证据包</a></p><video controls preload="none" width="640" style="max-width:100%" src="{video}"></video><div class="frames">{imgs}</div>{subtitles}</details>')
  sections.append(f'<section id="{r["qid"]}"><h2>{esc(r["qid"])} — {esc(r["question"])}</h2><p>参考：{esc(r["reference_answer"])}</p><p>候选组 {r["candidate_group_count"]}；通过删组核验的组：{esc(str(r["validated_irreducible_group_ids"]))}；状态：{r["grouping_status"]}</p><p>{esc(r["review_note_zh"])}</p>'+''.join(pieces)+'</section>')
 (final/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Video-MME evidence groups</title><style>body{font:16px system-ui;max-width:1400px;margin:2rem}section{border-top:2px solid #ccc;padding:1rem 0}details{padding:.7rem;border-bottom:1px solid #ddd}summary{cursor:pointer}.frames{display:flex;flex-wrap:wrap}figure{margin:6px}img{width:360px;max-width:100%}figcaption{font-size:12px}</style><h1>60题时间证据组</h1><p>连续事件/主题发生段；帧数和字幕数不等于组数。证据核心范围与复查上下文分别保存。不可再删集合只针对已提供源证据，不等于全视频最少组数。AI审计，非人工金标。</p>'+''.join(sections))
 print(canon(summary))
if __name__=='__main__':main()
