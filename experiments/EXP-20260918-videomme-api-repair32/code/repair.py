#!/usr/bin/env python3
"""Source-grounded API repair of the frozen32 failed/unresolved historical cases."""
import argparse,collections,copy,fcntl,json,math,os,time
from pathlib import Path
import av
import engine as e
REPO=e.REPO;OUT=e.OUT
OLD=e.BASE/'EXP-20260917-videomme-api-source50/run-001'
BANK=e.BASE/'EXP-20260916-memory-data-prep/run-001-inventory/candidates.jsonl'
HINTS={
 'videomme:610-2':'Ensure semantic event grouping is consistent with the multi-group declaration; one continuous narrative can contain distinct events.',
 'videomme:634-2':'Options are supplied. Resolve requested between-events scope and the missing intermediate list item; distinguish required absence evidence from optional notes.',
 'videomme:763-1':'Earlier observation lacked the question options. They are now supplied; locate evidence addressing each relevant claim.',
 'videomme:725-1':'Earlier model mixed identities of scientists. Include introductions linking each person/company to the relevant research/trial statement; distinguish human clinical trials from animal/self experiments.',
 'videomme:734-3':'Establish the requested maximum kill streak using adequate comparisons; kills and kill streak are different metrics. An end screen is not the only acceptable route.',
 'videomme:815-2':'Link program titles/apparatus to ordinal positions in the video, including preceding program boundaries or a reliable ordered program list.',
 'videomme:816-3':'Cover every requested action in the options, including attempting to play the drum; an idle drum is not evidence of playing it.',
 'videomme:826-2':'Check earliest relevant introductions/construction steps for all listed objects, not incidental background visibility or later repeated placement. The old selected windows left ordering uncertain.',
 'videomme:844-1':'Locate the event about the brand nearly ceasing to exist as well as the other three events; do not equate routine family succession with near extinction without support.'}

def prepare():
 if (OUT/'manifest.json').exists():raise FileExistsError('Frozen manifest already exists')
 cfg=e.read(REPO/'protocol.json');oldmanifest=e.read(OLD/'manifest.json');entries=[]
 for old in oldmanifest['entries']:
  result=OLD/'results'/f"{e.safe(old['qid'])}.json";r=e.read(result)
  if r['status'] not in {'technical_failed','source_unresolved'}:continue
  q=e.read(old['input_file']);assert e.sha(old['input_file'])==old['input_sha256']
  q.update(old_status=r['status'],old_result_file=str(result),old_result_sha256=e.sha(result),repair_hint=HINTS.get(q['qid'],'Repair source references and temporal representation. Do not reuse old frame IDs; source times are derived from current IDs.'))
  dest=OUT/'inputs'/f"{e.safe(q['qid'])}.json";e.dump(dest,q);entries.append({'qid':q['qid'],'video_id':q['video_id'],'old_status':r['status'],'old_result_sha256':q['old_result_sha256'],'input_file':str(dest),'input_sha256':e.sha(dest)})
 pilots=cfg['repair']['pilot_qids'];entries.sort(key=lambda x:(pilots.index(x['qid']) if x['qid'] in pilots else 99,x['qid']));assert len(entries)==32
 m={'created_at':e.now(),'questions':32,'prior_questions':50,'original_manifest_sha256':e.sha(OLD/'manifest.json'),'caption_bank_sha256':e.sha(BANK),'protocol_sha256':e.sha(REPO/'protocol.json'),'entries':entries}
 e.dump(OUT/'manifest.json',m);e.dump(REPO/'manifest.json',m);print(json.dumps({'selected':32,'prior_statuses':dict(collections.Counter(x['old_status'] for x in entries))},ensure_ascii=False))

class Repair(e.Runner):
 def __init__(self):
  super().__init__();self.caps=collections.defaultdict(list);vids=set(self.subs)
  for line in BANK.open():
   c=json.loads(line)
   if c['video_id'] in vids:self.caps[c['video_id']].append({'id':f"C{int(c['source_id'].split(':')[-1]):05}",'start_s':c['start_s'],'end_s':c['end_s'],'text':c['text']})
 def check_plan(self,d,q):
  assert isinstance(d,dict),'root must be object with windows, reason_zh and remaining_search_uncertainties; do not return a bare window array'
  assert isinstance(d.get('windows'),list),'windows must be list';assert len(d['windows'])<=self.cfg['repair']['max_planned_windows'],'too many windows'
  ids={c['id'] for c in self.caps[q['video_id']]};subs={s['id'] for s in self.subs[q['video_id']]}
  for w in d['windows']:
   assert 0<=w['start_s']<w['end_s']<=q['duration_s'],'window outside video'
   assert set(w.get('caption_ids',[]))<=ids and set(w.get('subtitle_ids',[]))<=subs,'unknown locator caption/subtitle ID'
  assert sum(b-a for a,b in e.merge([(w['start_s'],w['end_s']) for w in d['windows']]))<=self.cfg['repair']['max_planned_total_seconds'],'selected windows exceed source budget; choose shorter witnesses'
 def plan(self,q,roundno,missing):
  header={'qid':q['qid'],'question':q['question'],'options':q['options'],'duration_s':q['duration_s'],'repair_hint':q['repair_hint'],'current_required_gaps':missing,'all_captions':self.caps[q['video_id']],'all_subtitles':self.subs[q['video_id']],'caption_count':len(self.caps[q['video_id']]),'all_caption_input':True,'max_total_window_seconds':600}
  d,path=self.call(q,'plan',header,{'frames':[]},lambda d:self.check_plan(d,q));return d,path
 def windows(self,spans,duration,margin=0):
  return [{'id':f'W{i:03}','windows':[[a,b]]} for i,(a,b) in enumerate(e.merge([(max(0,a-margin),min(duration,b+margin)) for a,b in spans]))]
 def packet(self,q,windows,stage):
  spacing=self.cfg['source']['coarse_spacing_s' if stage=='coarse' else 'refine_spacing_s'];cap=self.cfg['source']['max_coarse_frames' if stage=='coarse' else 'max_refine_frames'];duration=sum(b-a for w in windows for a,b in w['windows']);n=len(windows)
  effective=max(spacing,math.ceil(duration/max(1,cap-2*n)))
  local=object.__new__(e.Runner);local.__dict__=self.__dict__.copy();local.cfg=copy.deepcopy(self.cfg);local.cfg['source']['coarse_spacing_s' if stage=='coarse' else 'refine_spacing_s']=effective
  p=e.Runner.frame_packet(local,q,windows,stage)
  return p
 def catalog(self,p):
  out={f['id']:{'id':f['id'],'kind':'frame_point','start_s':f['time_s'],'end_s':f['time_s'],'frame_sha256':f['sha256']} for f in p['frames']}
  out.update({s['id']:{'id':s['id'],'kind':'subtitle_span','start_s':s['start_s'],'end_s':s['end_s'],'text':s['text']} for s in p['subtitles']});return out
 def header(self,q,p):
  return {'qid':q['qid'],'video_id':q['video_id'],'question':q['question'],'options':q['options'],'source_catalog':list(self.catalog(p).values()),'retrieval_windows_not_semantic_groups':p['windows'],'actual_nominal_sampling_s':p['nominal_spacing_s'],'audio_supplied':False}
 def check(self,d,p,verification=False):
  assert isinstance(d,dict),'root must be object'
  assert d.get('coverage') in {'complete','partial','uncertain'},'coverage must be complete/partial/uncertain'
  assert isinstance(d.get('question_supported'),bool),'question_supported must be boolean'
  assert isinstance(d.get('answer'),str),'answer required'
  assert d.get('requires_multiple') in {'yes','no','uncertain'},'requires_multiple enum invalid'
  assert isinstance(d.get('missing_required'),list) and isinstance(d.get('notes'),list),'missing_required and notes must be arrays'
  catalog=self.catalog(p);facts=d['facts'];fm={f['id']:f for f in facts};assert len(fm)==len(facts),'duplicate fact IDs'
  for f in facts:
   assert f['status'] in {'supported','uncertain'},f"{f['id']}: invalid status"
   assert isinstance(f['statement'],str) and isinstance(f['source_ids'],list),f"{f['id']}: statement/source_ids missing"
   unknown=set(f['source_ids'])-set(catalog);assert not unknown,f"{f['id']}: unknown IDs {sorted(unknown)}; current frame IDs {[x['id'] for x in p['frames']]}; do not alter prefixes"
   assert len(f['source_ids'])<=40,f"{f['id']}: cite at most40 directly relevant sources"
   if f['status']=='supported':assert f['source_ids'],f"{f['id']}: supported claim needs citations"
  groups=d['semantic_groups'];assert len({g['id'] for g in groups})==len(groups),'duplicate semantic group IDs'
  for g in groups:
   assert g['fact_ids'] and set(g['fact_ids'])<=set(fm),f"{g['id']}: invalid fact IDs"
   allowed={sid for fid in g['fact_ids'] for sid in fm[fid]['source_ids']}
   assert g['source_ids'] and set(g['source_ids'])<=allowed,f"{g['id']}: group sources must belong to its listed facts"
  for relation in d['relations']:
   assert relation['fact_ids'] and set(relation['fact_ids'])<=set(fm),'relation cites unknown facts'
   assert relation['status'] in {'supported','uncertain'},'invalid relation status'
  if d['requires_multiple']=='yes':
   assert len(groups)>=2,'requires_multiple=yes but fewer than2 semantic groups; correct semantic grouping or declaration'
   assert len({tuple(sorted(g['source_ids'])) for g in groups})>=2,'identical citation sets do not establish distinct groups'
  if d['coverage']=='complete' or d['question_supported']:
   assert facts and not d['missing_required'] and all(f['status']=='supported' for f in facts) and all(r['status']=='supported' for r in d['relations']),'positive coverage conflicts with missing/uncertain required evidence; set partial/false or substantiate it'
  if verification:assert d.get('reference_status') in {'matches','conflict','uncertain'} and isinstance(d.get('reference_reason_zh'),str),'reference_status/reference_reason_zh required'
 def dense_windows(self,q,p,obs):
  cat=self.catalog(p);spans=[]
  for fact in obs['facts']:
   ids=list(dict.fromkeys(fact['source_ids']))
   # Retain all coarse sources for audit; densify up to6 evenly distributed anchors per fact.
   ids=ids if len(ids)<=6 else [ids[round(i*(len(ids)-1)/5)] for i in range(6)]
   for sid in ids:
    c=cat[sid];spans.append((max(0,c['start_s']-2),min(q['duration_s'],c['end_s']+2)))
  return self.windows(spans,q['duration_s']) if spans else []
 def combine(self,q,coarse,dense,roundno):
  frames={f['id']:f for f in coarse['frames']};frames.update({f['id']:f for f in dense['frames']});subs={s['id']:s for s in coarse['subtitles']};subs.update({s['id']:s for s in dense['subtitles']});p={'qid':q['qid'],'video_id':q['video_id'],'duration_s':q['duration_s'],'frames':list(frames.values()),'subtitles':sorted(subs.values(),key=lambda s:s['start_s']),'windows':coarse['windows']+dense['windows'],'nominal_spacing_s':{'coarse':coarse['nominal_spacing_s'],'dense':dense['nominal_spacing_s']},'source_packets':[{'file':coarse['packet_file'],'sha256':e.sha(coarse['packet_file'])},{'file':dense['packet_file'],'sha256':e.sha(dense['packet_file'])}]};path=OUT/'combined'/e.safe(q['qid'])/f'round-{roundno:02}-{e.digest(p)[:16]}.json';p['packet_file']=str(path);e.dump(path,p);return p
 def bound_result(self,q,p,d):
  cat=self.catalog(p)
  return [{'fact_id':f['id'],'statement':f['statement'],'status':f['status'],'video_id':q['video_id'],'source_spans':[dict(cat[sid],source_id=sid) for sid in f['source_ids']],'span_semantics':'Frame points and full original subtitle cues; gaps remain explicit. These are source supports, not semantic group counts.'} for f in d['facts']]
 def decision(self,d):
  if d['reference_status']=='conflict':return 'reference_conflict'
  complete=d['coverage']=='complete' and d['question_supported'] and not d['missing_required'] and d['reference_status']=='matches'
  if complete and d['requires_multiple']=='yes':return 'source_supported_multi'
  if complete and d['requires_multiple']=='no':return 'source_supported_single_or_redundant'
  return 'source_incomplete'
 def one(self,item):
  if self.stop.is_set() or (OUT/'STOP').exists():return
  q=e.read(item['input_file']);assert e.sha(item['input_file'])==item['input_sha256'];assert e.sha(q['old_result_file'])==q['old_result_sha256'];r={'qid':q['qid'],'video_id':q['video_id'],'old_status':q['old_status'],'old_result_file':q['old_result_file'],'old_result_sha256':q['old_result_sha256'],'started_at':e.now(),'implementation':self.impl,'rounds':[],'human_reviewed':False}
  try:
   self.stage(q['qid'],'prepare_source');v=Path(q['video_path']);assert v.stat().st_size==q['video_size_bytes'] and v.stat().st_mtime_ns==q['video_mtime_ns'];r['source_video_sha256']=e.sha(v)
   with av.open(str(v)) as con:q['duration_s']=con.duration/av.time_base
   missing=[]
   for roundno in range(1,self.cfg['repair']['max_source_rounds']+1):
    record={'round':roundno};r['rounds'].append(record)
    if q['old_status']=='source_unresolved' or roundno>1:
     plan,path=self.plan(q,roundno,missing);record.update(plan_call=path,plan=plan)
     if not plan['windows']:
      r.update(status='source_incomplete',reason='API full-timeline search found no usable source windows');break
     windows=self.windows([(w['start_s'],w['end_s']) for w in plan['windows']],q['duration_s'],3)
    else:windows=self.windows([(a,b) for g in q['groups'] for a,b in g['windows']],q['duration_s'],5)
    self.stage(q['qid'],f'coarse_frames_r{roundno}');coarse=self.packet(q,windows,'coarse');header=self.header(q,coarse);obs,path=self.call(q,'observe',header,coarse,lambda d:self.check(d,coarse));record.update(observe_call=path,observation=obs,coarse_packet_file=coarse['packet_file'])
    dw=self.dense_windows(q,coarse,obs)
    if not dw:
     missing=obs['missing_required'] or ['No cited source witness'];r.update(status='source_incomplete',reason='No cited source witness',missing_required=missing);continue
    self.stage(q['qid'],f'dense_frames_r{roundno}');dense=self.packet(q,dw,'refined');packet=self.combine(q,coarse,dense,roundno);header=self.header(q,packet)
    header.update(reference_answer=q['reference_answer'],prior_observation=obs);audit,path=self.call(q,'verify',header,packet,lambda d:self.check(d,packet,True));record.update(verify_call=path,verification=audit,source_packet_file=packet['packet_file'],source_packet_sha256=e.sha(packet['packet_file']))
    r.update(status=self.decision(audit),answer=audit['answer'],reference_status=audit['reference_status'],missing_required=audit['missing_required'],notes=audit['notes'],fact_evidence=self.bound_result(q,packet,audit),semantic_groups=audit['semantic_groups'],cross_segment_relations=audit['relations'],final_source_packet_file=packet['packet_file'],final_source_packet_sha256=e.sha(packet['packet_file']),boundary_precision=packet['nominal_spacing_s'])
    if r['status'].startswith('source_supported'):break
    missing=audit['missing_required'][:]
    if audit['reference_status']=='conflict':missing.append('Observed evidence conflicts with reference; search alternate or earlier occurrences and identity context. Do not assume either side is correct.')
    if not missing:missing=['Resolve uncertainty of source coverage, reference identity/order or complementary semantic groups.']
  except InterruptedError:r.update(status='interrupted',reason='graceful stop; cached stages preserved')
  except Exception as exc:
   failed=[]
   for f in (OUT/'calls'/e.safe(q['qid'])).glob('*/*/attempt-*.json'):
    c=e.read(f)
    if c['status']=='failed' and c['implementation']==self.impl:failed.append(c)
   last=max(failed,key=lambda c:c['completed_at']) if failed else {};typ=last.get('error_type',type(exc).__name__);status='output_invalid' if typ in {'AssertionError','KeyError','TypeError','JSONDecodeError'} else ('api_failed' if any(x in typ for x in ['API','Timeout','Connection','RateLimit','Authentication']) else 'preparation_failed')
   r.update(status=status,error_type=typ,error=self.redact(str(exc)),last_call_error=last.get('error'))
  finally:
   r['completed_at']=e.now();e.dump(OUT/'results'/f"{e.safe(q['qid'])}.json",r)
   with self.lock:
    self.active.pop(q['qid'],None);self.failed_consecutive=self.failed_consecutive+1 if r['status']=='api_failed' else 0
    if self.failed_consecutive>=self.cfg['api']['stop_after_consecutive_failed_questions']:self.stop.set();e.dump(OUT/'circuit_breaker.json',{'at':e.now(),'reason':'consecutive API failures; inspect before resume'})
    self.progress('stopping' if self.stop.is_set() else 'running')
   print(json.dumps({'qid':q['qid'],'old_status':q['old_status'],'status':r['status'],'rounds':len(r['rounds']),'at':r['completed_at']},ensure_ascii=False),flush=True)
 def export(self):
  super().export();rows=[e.read(p) for p in (OUT/'results').glob('*.json')];oldrows=[e.read(p) for p in (OLD/'results').glob('*.json')];replacement={r['qid']:r for r in rows};combined=[replacement.get(r['qid'],r) for r in oldrows]
  e.dump(OUT/'combined50_status.json',{'updated_at':e.now(),'reprocessed':len(rows),'unchanged_historical':50-len(rows),'status_counts':dict(collections.Counter(r['status'] for r in combined)),'note':'Original18 supported results are historical carry-over, not new verification; pending repair cases retain old labels.'})

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','run','status']);ap.add_argument('--limit',type=int);a=ap.parse_args()
 if a.action=='prepare':prepare()
 elif a.action=='status':print(json.dumps(e.read(OUT/'status.json'),ensure_ascii=False,indent=2))
 else:
  OUT.mkdir(parents=True,exist_ok=True)
  with (OUT/'runner.lock').open('a') as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);Repair().run(a.limit)
