#!/usr/bin/env python3
"""Full-caption search followed by original-source multi-episode validation."""
import argparse, base64, collections, concurrent.futures, datetime, fcntl, hashlib, html, json, math, os, re, shutil, threading, time, zipfile
from pathlib import Path
from urllib.parse import urlsplit
import av, httpx, pysrt
from openai import OpenAI
from PIL import Image
import group_base as gb
from group_base import canon, dump, read, safe, sha
from order_rubric import ordered_rubric

REPO=Path(__file__).resolve().parents[1]
OUT=Path('/mnt/raid5-01/baorui/visual-memory/EXP-20260917-videomme-multievidence50/run-001')
INV=gb.INVENTORY
gb.OUT=OUT
gb.REPO=REPO

def rows(p): return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def now(): return datetime.datetime.now().astimezone().isoformat()
def priority_key(r,q):
 text=q['original_question'].lower()
 structural=bool(re.search(r'\border\b|\bsequence\b|\bchronolog|\bboth\b|\bin common\b|\bsimilarit|\bwhich days\b',text))
 exhaustive=bool(re.search(r'\bnot\b|\bnever\b|\bhow many\b|\btotal\b|\binappropriate\b',text)) or r.get('scope_risk',False)
 tier=0 if structural and not exhaustive and r['priority']>=3 else (1 if not exhaustive and r['priority']>=3 else 2)
 return (tier,-r['priority'],bool(exhaustive),r['qid'])

class Pipeline(gb.Runner):
 def __init__(self):
  self.cfg=read(REPO/'protocol.json');self.questions={q['qid']:q for q in rows(INV/'questions.jsonl')}
  self.prompts={p.stem:p.read_text() for p in (REPO/'code/prompts').glob('*.txt')}
  self.credentials=read('/home/baorui/projects/visual-memory/tmp/api.json');self.base=self.credentials['base_url'].rstrip('/')
  if urlsplit(self.base).path in ('','/'):self.base+='/v1'
  self.local=threading.local();self.captions=collections.defaultdict(list)
  for c in rows(INV/'candidates.jsonl'):self.captions[c['video_id']].append(c)
  self.durations={Path(v['path']).stem:v['duration_s'] for v in rows(INV/'video_probes.jsonl')}
  self.subs={};self.subhash={}
  with zipfile.ZipFile(gb.DATA/'subtitle.zip') as z:
   for vid in self.captions:
    member=f'subtitle/{vid}.srt'
    if member not in z.namelist():self.subs[vid]=[];self.subhash[vid]=None;continue
    raw=z.read(member);self.subhash[vid]=hashlib.sha256(raw).hexdigest()
    self.subs[vid]=[{'subtitle_id':f'S{i:05}','start_s':s.start.ordinal/1000,'end_s':s.end.ordinal/1000,'text':re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]*>','',s.text))).strip()} for i,s in enumerate(pysrt.from_string(raw.decode('utf-8-sig',errors='replace')))]
  implementation={str(p.relative_to(REPO)):sha(p) for p in sorted((REPO/'code').rglob('*')) if p.is_file() and '__pycache__' not in str(p)}
  self.impl=hashlib.sha256(canon([implementation,self.cfg]).encode()).hexdigest()
  snap=OUT/'code_snapshots'/self.impl
  snapshot_lock=OUT/'locks'/'snapshot-init.lock';snapshot_lock.parent.mkdir(parents=True,exist_ok=True)
  with snapshot_lock.open('a') as handle:
   fcntl.flock(handle,fcntl.LOCK_EX)
   if not snap.exists():shutil.copytree(REPO/'code',snap,ignore=shutil.ignore_patterns('__pycache__'))
   if not (snap/'protocol.json').exists():dump(snap/'protocol.json',self.cfg)
  manifest={'questions_sha256':sha(INV/'questions.jsonl'),'captions_sha256':sha(INV/'candidates.jsonl'),'source_subtitle_zip_sha256':sha(gb.DATA/'subtitle.zip'),'qids':list(self.questions),'questions':len(self.questions),'videos':len(self.captions),'captions':sum(map(len,self.captions.values())),'requested_model':self.cfg['model']}
  dest=OUT/'input_manifest.json'
  if dest.exists():assert read(dest)==manifest
  else:dump(dest,manifest)
 def client(self):
  if not hasattr(self.local,'client'):
   mode=os.environ.get('MULTIEVIDENCE_NETWORK','proxy')
   self.local.client=OpenAI(api_key=self.credentials['api_key'],base_url=self.base,http_client=httpx.Client(proxy=(os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')) if mode=='proxy' else None,trust_env=False),timeout=self.cfg['api']['timeout_seconds'],max_retries=0)
  return self.local.client
 def call(self,qid,stage,header,frames=()):
  content=[{'type':'text','text':canon(header)}]
  for f in frames:
   content.extend([{'type':'text','text':f"Frame {f['frame_id']} actual PTS {f['actual_pts_s']:.3f}s"},{'type':'image_url','image_url':{'url':'data:image/jpeg;base64,'+base64.b64encode(Path(f['path']).read_bytes()).decode(),'detail':'high'}}])
  payload={'model':self.cfg['model'],'messages':[{'role':'system','content':self.prompts[stage]+'\nThe root JSON value MUST be one OBJECT with the specified top-level keys, never an array of facts or a wrapper list. No markdown fences.'},{'role':'user','content':content}],'max_tokens':self.cfg['api']['max_output_tokens'],'response_format':{'type':'json_object'},'temperature':0,'stream':True,'stream_options':{'include_usage':True}}
  digest=hashlib.sha256(canon(payload).encode()).hexdigest();folder=OUT/'calls'/safe(qid)/stage/digest[:20]
  done=folder/'completed.json'
  if done.exists():return read(done)['parsed'],str(done)
  logged=json.loads(canon(payload))
  for x in logged['messages'][1]['content']:
   if x['type']=='image_url':x['image_url']['url']='sha256:'+hashlib.sha256(base64.b64decode(x['image_url']['url'].split(',',1)[1])).hexdigest()
  dump(folder/'request.json',{'request_sha256':digest,'implementation':self.impl,'payload':logged})
  offset=len(list(folder.glob('attempt-*.json')))
  for attempt in range(self.cfg['api']['attempts']):
   rec={'qid':qid,'stage':stage,'implementation':self.impl,'request_sha256':digest,'started_at':now(),'attempt':offset+attempt+1,'network_mode':os.environ.get('MULTIEVIDENCE_NETWORK','proxy')};t=time.monotonic()
   try:
    rec.update(raw_text='',finish_reason=None,usage=None,streamed=True)
    with self.client().chat.completions.create(**payload) as stream:
     for chunk in stream:
      rec.update(resolved_model=chunk.model,response_id=chunk.id)
      if chunk.usage:rec['usage']=chunk.usage.model_dump()
      for choice in chunk.choices:
       if choice.delta.content:rec['raw_text']+=choice.delta.content
       if choice.finish_reason:rec['finish_reason']=choice.finish_reason
    if rec['finish_reason']!='stop':raise ValueError('Incomplete response')
    raw=rec['raw_text'].strip()
    if raw.startswith('```'):raw=re.sub(r'^```(?:json)?\s*|\s*```$','',raw)
    parsed=json.loads(raw)
    if isinstance(parsed,list) and len(parsed)==1 and isinstance(parsed[0],dict):
     parsed=parsed[0];rec['format_normalization']='Unwrapped a single-object root array; original response retained unchanged.'
    if not isinstance(parsed,dict):raise ValueError('Response not object')
    rec.update(status='ok',parsed=parsed,elapsed_s=time.monotonic()-t);dump(folder/f"attempt-{rec['attempt']:02}.json",rec);dump(done,rec)
    return parsed,str(done)
   except Exception as exc:
    msg=str(exc)
    for k in ['api_key','base_url']:msg=msg.replace(self.credentials[k],'<redacted>')
    rec.update(status='failed',error_type=type(exc).__name__,error=msg[:1000],elapsed_s=time.monotonic()-t);dump(folder/f"attempt-{rec['attempt']:02}.json",rec)
    if attempt+1==self.cfg['api']['attempts']:raise RuntimeError(f'{qid}/{stage} API failed; see redacted ledger') from None
 def full_timeline(self,q):
  caps=self.captions[q['video_id']]
  return {'original_question':q['original_question'],'original_options':q['original_options'],'official_answer':q['reference_draft'],'duration_s':self.durations[q['video_id']],
   'caption_count':len(caps),'caption_timeline_complete':True,
   'all_captions':[[f"C{int(c['source_id'].split(':')[-1]):05}",c['start_s'],c['end_s'],c['text']] for c in caps],
   'all_original_subtitles':self.subs[q['video_id']]}
 def screen(self):
  dest=OUT/'ranking.json'
  if dest.exists():return read(dest)
  qs=list(self.questions.values());batches=[qs[i:i+30] for i in range(0,len(qs),30)]
  def one(pair):
   i,batch=pair;h={'questions':[{k:q[k] for k in ['qid','original_question','original_options','reference_draft','official_task_type']} for q in batch]}
   for repair in range(3):
    r,p=self.call(f'screen-{i:03}','screen',h)
    if {x.get('qid') for x in r.get('questions',[])}=={q['qid'] for q in batch} and len(r['questions'])==len(batch):
     for x in r['questions']:x['call_file']=p;x['priority']=int(x['priority']);assert 0<=x['priority']<=5
     print(canon({'screen_batch':i,'complete':True}),flush=True);return r['questions']
    h['repair']='Return exactly one valid row for each input qid.'
   raise ValueError('screen schema')
  ranked=[]
  with concurrent.futures.ThreadPoolExecutor(max_workers=self.cfg['api']['concurrency']) as pool:
   for out in pool.map(one,enumerate(batches)):ranked.extend(out)
  ranked.sort(key=lambda r:priority_key(r,self.questions[r['qid']]))
  dump(dest,ranked);dump(REPO/'candidate_ranking.json',ranked);return ranked
 def normalize(self,raw,bank):
  # Temporal adjacency is not semantic identity: independently introduced days or
  # chapters may meet at a cut. The source audit, never this rule, decides episodes.
  groups=[];log=[]
  for g in raw.get('groups',[]):
   g=json.loads(canon(g));a,b=g['start_s'],g['end_s'];fs={f['frame_id']:f for f in bank['frames']};ss={s['subtitle_id']:s for s in bank['subtitles']}
   assert all(a<=fs[x]['actual_pts_s']<b for x in g['frame_ids'])
   assert all(a<=ss[x]['start_s']<ss[x]['end_s']<=b for x in g['subtitle_ids'])
   g.update(proposal_ids=[g['id']],review_start_s=max(0,a-3),review_end_s=min(bank['duration_s'],b+3))
   groups.append(g)
  groups.sort(key=lambda g:g['start_s'])
  for i,g in enumerate(groups):
   g['id']=f'G{i+1:02}'
   if i and groups[i-1]['end_s']>g['start_s']:
    raise ValueError(f"Overlapping cores {groups[i-1]['id']} / {g['id']}: revise evidence-bearing bounds without splitting one activity or merging distinct chapters. Choose source anchors contained in their episode.")
  return groups,log
 def group_content(self,r,p,ids=None,audit=False):
  h,frames=super().group_content(r,p,ids,audit)
  if not audit:
   selected=[g for g in p['groups'] if ids is None or g['id'] in ids]
   frames=[f for f in frames if any(g['start_s']<=f['actual_pts_s']<g['end_s'] for g in selected)]
  return h,frames
 def initial_source(self,q,nom):
  duration=self.durations[q['video_id']];caps={f"C{int(c['source_id'].split(':')[-1]):05}":c for c in self.captions[q['video_id']]};subs={s['subtitle_id']:s for s in self.subs[q['video_id']]};groups=[];anchor_log=[]
  for i,g0 in enumerate(nom['groups']):
   g=json.loads(canon(g0));a,b=float(g['start_s']),float(g['end_s']);assert math.isfinite(a) and math.isfinite(b) and 0<=a<b<=duration+1
   for field,source in [('caption_ids',caps),('subtitle_ids',subs)]:
    retained=[]
    for key in g.get(field,[]):
     unit=source.get(key)
     valid=unit is not None and ((unit['start_s']<b and unit['end_s']>a) if field=='caption_ids' else (a<=unit['start_s']<unit['end_s']<=min(b,duration)))
     if valid:retained.append(key)
     else:anchor_log.append({'action':'discard_invalid_localization_anchor_only','group':g['id'],'kind':field,'id':key,'proposed_core':[a,b],'actual_span':[unit['start_s'],unit['end_s']] if unit else None,'note':'Raw proposal preserved. Core unchanged. Full original subtitles remain in source bank; verifier sees actual core subtitles and frames, never caption truth.'})
    g[field]=retained
   g.update(start_s=round(a,3),end_s=round(min(duration,b),3),frame_ids=[],boundary_basis='source_projection',role='direct')
   groups.append(g)
  assert len(groups)>=2,'fewer than two candidate episodes'
  times=[]
  for g in groups:
   a,b=g['start_s'],g['end_s'];n=max(3,min(13,math.ceil((b-a)/15)+1))
   times.extend(a+(b-a)*i/(n-1) for i in range(n));times.extend(g.get('key_times_s',[]))
  times=sorted({round(max(0,min(duration-.1,float(t))),3) for t in times});frames=[];video=gb.DATA/'data'/f"{q['video_id']}.mp4"
  variant=hashlib.sha256(canon(times).encode()).hexdigest()[:16];d=OUT/'frames'/safe(q['qid'])/variant
  cached=d/'index.json'
  if cached.exists():frames=read(cached)
  else:
   with av.open(str(video)) as con:
    st=con.streams.video[0]
    for i,t in enumerate(times):
     f,actual=gb.frame_at(con,st,t)
     im=f.to_image().convert('RGB');im.thumbnail((1024,1024),Image.Resampling.LANCZOS);p=d/f'V{i+1:03}.jpg';p.parent.mkdir(parents=True,exist_ok=True);im.save(p,quality=94)
     frames.append({'frame_id':f'V{i+1:03}','requested_s':t,'actual_pts_s':actual,'path':str(p),'sha256':sha(p),'source_video':str(video),'trailing_padding_fallback':actual+1e-6<t})
   dump(cached,frames)
  for g in groups:g['frame_ids']=[f['frame_id'] for f in frames if g['start_s']<=f['actual_pts_s']<g['end_s']]
  bank={'qid':q['qid'],'video_id':q['video_id'],'duration_s':duration,'frames':frames,'subtitles':self.subs[q['video_id']],'subtitle_member_sha256':self.subhash[q['video_id']]}
  source_dest=OUT/'sources'/f"{safe(q['qid'])}.json"
  if source_dest.exists() and read(source_dest)!=bank:
   archive=OUT/'superseded_sources'/safe(q['qid'])/(sha(source_dest)+'.json')
   if not archive.exists():dump(archive,read(source_dest))
  dump(source_dest,bank)
  norm,log=self.normalize({'groups':groups},bank)
  # Generated caption text and localization hypotheses are never verifier source.
  for g in norm:g.pop('caption_ids',None);g.pop('key_times_s',None)
  return bank,norm,anchor_log+log
 def checked_audit(self,r,p,q):
  h,frames=self.group_content(r,p,audit=True);h.update(original_question=q['original_question'],original_options=q['original_options'],official_answer=q['reference_draft'])
  fids={f['frame_id'] for f in frames};sids={s['subtitle_id'] for it in h['intervals'] for s in it['subtitles']};gids={g['id'] for g in p['groups']};facts={f['id'] for f in r['required_facts']}
  for repair in range(3):
   a,path=self.call(r['qid'],'audit',h,frames);errors=[]
   if {x.get('group_id') for x in a.get('group_checks',[])}!=gids or len(a.get('group_checks',[]))!=len(gids):errors.append('group IDs')
   if {x.get('fact_id') for x in a.get('fact_support',[])}!=facts or len(a.get('fact_support',[]))!=len(facts):errors.append('fact IDs')
   for f in a.get('fact_support',[]):
    if not set(f.get('frame_ids',[]))<=fids or not set(f.get('subtitle_ids',[]))<=sids:errors.append('source IDs')
    if f.get('status')=='supported' and not (f.get('frame_ids') or f.get('subtitle_ids')):errors.append('uncited support')
    for option in f.get('supported_by',[]):
     if not option or not set(option)<=gids:errors.append('support group IDs')
   dump(Path(path).parent/'schema_validation.json',{'passed':not errors,'errors':errors})
   if not errors:return a,path
   h['format_retry']={'errors':errors,'valid_frame_ids':sorted(fids),'valid_subtitle_ids':sorted(sids),'valid_fact_ids':sorted(facts),'valid_group_ids':sorted(gids)}
  raise ValueError('audit schema')
 def ablate(self,r,p,audit):
  ids=[g['id'] for g in p['groups']];tests=[];cache={}
  def test(gs):
   key=tuple(sorted(gs))
   if key not in cache:
    v,path=self.check_subset(r,p,list(key));ok=self.subset_success(v);cache[key]=ok;tests.append({'group_ids':list(key),'supported':ok,'result':v,'call_file':path})
   return cache[key]
  if not test(ids):return {'status':'full_set_insufficient','tests':tests}
  for gid in ids:
   if test([gid]):return {'status':'single_group_sufficient','singleton':gid,'tests':tests}
  active=list(ids)
  for gid in reversed(ids):
   rest=[x for x in active if x!=gid]
   if test(rest):active=rest
  for gid in active:assert not test([x for x in active if x!=gid])
  assert len(active)>=2
  for a,oa in cache.items():
   for b,ob in cache.items():
    if set(a)<set(b) and oa and not ob:return {'status':'inconsistent_subset_judgments','tests':tests}
  return {'status':'multi_group_verified','selected_group_ids':active,'irreducible_group_count':len(active),'tests':tests,'minimality':'inclusion-minimal among projected candidates; every candidate singleton also tested'}
 def process(self,qid):
  lock=OUT/'locks'/f'{safe(qid)}.lock';lock.parent.mkdir(parents=True,exist_ok=True)
  with lock.open('a') as handle:
   fcntl.flock(handle,fcntl.LOCK_EX)
   return self._process(qid)
 def _process(self,qid):
  dest=OUT/'results'/f'{safe(qid)}.json'
  if dest.exists():return read(dest)
  q=self.questions[qid];rec={'qid':qid,'video_id':q['video_id'],'question_original':q['original_question'],'official_answer':q['reference_draft'],'implementation':self.impl,'started_at':now(),'model':self.cfg['model'],'human_reviewed':False,'rounds':[]}
  try:
   h=self.full_timeline(q);rec.update(captions_supplied=len(h['all_captions']),captions_total=len(self.captions[q['video_id']]),all_captions_sha256=hashlib.sha256(canon(h['all_captions']).encode()).hexdigest())
   constraints=REPO/'question_constraints'/f'{safe(qid)}.json'
   if constraints.exists():
    h['faithful_question_constraints']=read(constraints)
    frozen=OUT/'manual_inputs'/safe(qid)/(sha(constraints)+'.json');dump(frozen,read(constraints));rec['question_constraints_file']=str(frozen);rec['question_constraints_sha256']=sha(frozen)
   for roundno in [1,2]:
    nom,npath=self.call(qid,'locate',h);rec['localization']=nom;rec['localization_call']=npath
    if not nom.get('suitable_multi_candidate') or len(nom.get('groups',[]))<2:rec.update(status='rejected_localization',reason=nom.get('reason_zh'));break
    formal=ordered_rubric(q)
    if formal:
     nom=json.loads(canon(nom));nom.update(short_question=formal['question'],required_facts=formal['required_facts'])
     for g in nom['groups']:g['fact_ids']=[]
     rec.update(localization=nom,deterministic_order_rubric=formal)
    assert nom.get('required_facts') and len({f['id'] for f in nom['required_facts']})==len(nom['required_facts'])
    r={'qid':qid,'video_id':q['video_id'],'question':nom['short_question'],'required_facts':nom['required_facts'],'task_labels':nom['task_labels']}
    try:bank,groups,normal=self.initial_source(q,nom)
    except (AssertionError,ValueError,KeyError) as exc:
     rec['rounds'].append({'round':roundno,'localization_call':npath,'format_error':str(exc)})
     if roundno==2:raise
     h['revision']={'error':str(exc),'previous_localization':nom,'instruction':'Correct source IDs and intervals; return a complete new localization, no invented evidence.'};continue
    p,ppath=self.project(r,bank,groups,roundno);rec.update(question=r['question'],required_facts=r['required_facts'],groups=groups,package_file=str(ppath),package_sha256=sha(ppath))
    if len(groups)<2:rec.update(status='rejected_merged_single_episode',reason='Overlapping/touching source groups merged to one');break
    oh,of=self.group_content(r,p);oh.pop('required_facts');obs,opath=self.call(qid,'observe',oh,of)
    allowedf={f['frame_id'] for f in of};alloweds={s['subtitle_id'] for it in oh['intervals'] for s in it['subtitles']}
    obs_valid=all(set(x.get('frame_ids',[]))<=allowedf and set(x.get('subtitle_ids',[]))<=alloweds for x in obs.get('observations',[])+obs.get('relations',[]))
    audit,apath=self.checked_audit(r,p,q);rec.update(observer=obs,observer_call=opath,audit=audit,audit_call=apath)
    roundrec={'round':roundno,'localization_call':npath,'normalization':normal,'package_file':str(ppath),'observer_call':opath,'audit_call':apath};rec['rounds'].append(roundrec)
    passed=all([obs_valid,not obs.get('question_ambiguous',True),obs.get('package_sufficiency')=='complete',audit.get('standalone_question_valid') is True,audit.get('rubric_valid') is True,audit.get('reference_status')=='supported',audit.get('segmentation_status')=='pass',audit.get('all_facts_supported') is True,audit.get('scope_adequate') is True,all(f.get('status')=='supported' and f.get('supported_by') for f in audit.get('fact_support',[])),all(all(g.get(k) is True for k in ['continuous_occurrence','bounds_adequate','source_supported']) for g in audit.get('group_checks',[]))])
    if not passed:
     rec.update(status='rejected_source_or_segmentation',reason=audit.get('issues',[]))
     if roundno==1:
      h['revision']={'previous_localization':nom,'source_audit':audit,'blind_observation_gaps':obs.get('missing_information',[]),'instruction':'Use the full timeline to resolve specific source gaps and grouping; preserve original semantics and official answer. If unsuitable, reject.'};continue
     break
    abl=self.ablate(r,p,audit);rec['subset_validation']=abl
    if abl['status']!='multi_group_verified':rec.update(status='rejected_'+abl['status'],reason=abl['status']);break
    counterh=self.full_timeline(q);counterh.update(short_question=r['question'],required_facts=r['required_facts'],proposed_groups=[{'start_s':g['start_s'],'end_s':g['end_s'],'label_zh':g['label_zh']} for g in groups])
    counter,cpath=self.call(qid,'countersearch',counterh);rec.update(countersearch=counter,countersearch_call=cpath)
    if any(counter.get(k,True) for k in ['single_group_alternative_possible','artificial_split_risk','rubric_overreach','unresolved_scope']):
     rec.update(status='qualified_countersearch',reason=counter.get('reason_zh'));break
    rec.update(status='multi_verified_candidate',reason='Full-caption search, blind original-source observation, source/group audit, singleton+deletion tests and full-caption countersearch passed',sheets=self.sheet(p,qid));break
  except Exception as exc:
   msg=str(exc)
   for k in ['api_key','base_url']:msg=msg.replace(self.credentials[k],'<redacted>')
   rec.update(status='processing_failed',error_type=type(exc).__name__,error=msg[:1600])
  rec['completed_at']=now();dump(dest,rec);return rec
 def summary(self):
  rs=[read(p) for p in (OUT/'results').glob('*.json')];cs=[read(p) for p in (OUT/'calls').glob('*/*/*/attempt-*.json')]
  ss={'updated_at':now(),'target':self.cfg['target'],'processed':len(rs),'status_counts':dict(collections.Counter(r['status'] for r in rs)),'api_attempts':len(cs),'api_failures':sum(c['status']=='failed' for c in cs),'models':sorted({c.get('resolved_model') for c in cs if c.get('resolved_model')}),'usage':{k:sum((c.get('usage') or {}).get(k,0) for c in cs) for k in ['prompt_tokens','completion_tokens','total_tokens']},'all_candidate_caption_inputs_complete':all(r.get('captions_supplied')==r.get('captions_total') for r in rs),'contacted_video_ids':sorted({r['video_id'] for r in rs})}
  dump(OUT/'progress.json',ss);dump(REPO/'progress.json',ss);return ss

def main():
 ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['screen','run','summary']);ap.add_argument('--limit',type=int,default=900);ap.add_argument('--min-priority',type=int,default=0);ap.add_argument('--ids',nargs='*');args=ap.parse_args();p=Pipeline()
 if args.phase=='screen':p.screen()
 elif args.phase=='run':
  ranking=p.screen();ids=args.ids or [r['qid'] for r in ranking if r['priority']>=args.min_priority];ids=[x if x.startswith('videomme:') else 'videomme:'+x for x in ids]
  ids=[x for x in ids if not (OUT/'results'/f'{safe(x)}.json').exists()][:args.limit]
  # Process bounded waves; stop only at >=50 verified candidates, then source review may require replacements.
  dump(OUT/'batches'/f'{time.time_ns()}.json',{'qids':ids,'implementation':p.impl,'started_at':now()})
  for i in range(0,len(ids),p.cfg['api']['concurrency']):
   with concurrent.futures.ThreadPoolExecutor(max_workers=p.cfg['api']['concurrency']) as pool:
    for r in pool.map(p.process,ids[i:i+p.cfg['api']['concurrency']]):print(canon({'qid':r['qid'],'status':r['status'],'groups':len(r.get('groups',[])),'needed':r.get('subset_validation',{}).get('irreducible_group_count'),'error':r.get('error')}),flush=True)
   s=p.summary();print(canon(s),flush=True)
   if s['status_counts'].get('multi_verified_candidate',0)>=p.cfg['target']:break
 print(canon(p.summary()),flush=True)
if __name__=='__main__':main()
