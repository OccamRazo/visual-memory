#!/usr/bin/env python3
"""Bounded resumable API source localization; no manual per-question image review."""
import argparse,base64,collections,concurrent.futures,datetime,fcntl,hashlib,html,json,math,os,random,re,shutil,signal,threading,time,zipfile
from pathlib import Path
from urllib.parse import urlsplit
import av,httpx,pysrt
from PIL import Image
from openai import OpenAI
REPO=Path(__file__).resolve().parents[1]
ROOT=Path('/home/baorui/projects/visual-memory')
BASE=Path('/mnt/raid5-01/baorui/visual-memory')
OUT=BASE/'EXP-20260918-videomme-api-expand50/run-001'
DATA=Path('/mnt/raid5-01/baorui/Video-MME')
PREV=BASE/'EXP-20260917-videomme-semantic-reassessment/run-002-caption-semantic'
POOL=ROOT/'experiments/EXP-20260917-videomme-semantic-reassessment/caption_multi_candidates.json'
def now():return datetime.datetime.now().astimezone().isoformat()
def read(p):return json.loads(Path(p).read_text())
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for chunk in iter(lambda:f.read(4*1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def digest(v):return hashlib.sha256(canon(v).encode()).hexdigest()
def safe(q):return q.replace(':','__')
def dump(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');t.replace(p)
def merge(spans):
 out=[]
 for a,b in sorted(spans):
  assert 0<=a<b
  if out and a<=out[-1][1]+.001:out[-1][1]=max(b,out[-1][1])
  else:out.append([float(a),float(b)])
 return out

def prepare():
 if (OUT/'manifest.json').exists():print('Frozen manifest already exists; unchanged.');return
 cfg=read(REPO/'protocol.json');pool=read(POOL);bins=collections.defaultdict(list)
 for d in pool:
  pfile=PREV/'packets'/f"{safe(d['qid'])}.json";p=read(pfile);assert sha(pfile)==d['source_packet_sha256'];lookup={c['id']:c for c in p['captions']};ids={cid for g in d['groups'] for cid in g['caption_ids']};duration=sum(lookup[i]['end_s']-lookup[i]['start_s'] for i in ids)
  if duration>cfg['selection']['max_selected_caption_seconds'] or len(d['groups'])>cfg['selection']['max_groups']:continue
  gs=[{'id':g['id'],'windows':merge([(lookup[i]['start_s'],lookup[i]['end_s']) for i in g['caption_ids']]),'caption_ids':g['caption_ids']} for g in d['groups']]
  bins[min(4,len(gs))].append({'qid':p['qid'],'video_id':p['video_id'],'question':p['question'],'options':p['options'],'reference_answer':p['reference_answer'],'groups':gs,'caption_packet_file':str(pfile),'caption_packet_sha256':sha(pfile),'selected_caption_seconds':duration})
 rng=random.Random(cfg['selection']['seed'])
 for key in sorted(bins):bins[key].sort(key=lambda x:x['qid']);rng.shuffle(bins[key])
 selected=[];seen=set()
 while len(selected)<50:
  progress=False
  for key in sorted(bins):
   while bins[key]:
    x=bins[key].pop()
    if x['video_id'] in seen:continue
    seen.add(x['video_id']);selected.append(x);progress=True;break
   if len(selected)==50:break
  assert progress,'Not enough eligible videos'
 for x in selected:
  v=DATA/'data'/f"{x['video_id']}.mp4";assert v.exists();x['video_path']=str(v);x['video_size_bytes']=v.stat().st_size;x['video_mtime_ns']=v.stat().st_mtime_ns
  dump(OUT/'inputs'/f"{safe(x['qid'])}.json",x)
 m={'created_at':now(),'questions':50,'pool_sha256':sha(POOL),'protocol_sha256':sha(REPO/'protocol.json'),'selection':cfg['selection'],'selected_qids':[x['qid'] for x in selected],'entries':[{'qid':x['qid'],'video_id':x['video_id'],'input_file':str(OUT/'inputs'/f"{safe(x['qid'])}.json"),'input_sha256':sha(OUT/'inputs'/f"{safe(x['qid'])}.json"),'caption_groups':len(x['groups']),'selected_caption_seconds':x['selected_caption_seconds']} for x in selected]}
 dump(OUT/'manifest.json',m);dump(REPO/'manifest.json',m);print(json.dumps({'selected':self.m['questions'],'videos':len(seen),'groups':sum(len(x['groups']) for x in selected),'qids':m['selected_qids']},ensure_ascii=False))

class Runner:
 def __init__(self):
  self.cfg=read(REPO/'protocol.json');self.m=read(OUT/'manifest.json');self.credentials=read(ROOT/'tmp/api.json');self.base=self.credentials['base_url'].rstrip('/')
  if urlsplit(self.base).path in ('','/'):self.base+='/v1'
  self.prompts={p.stem:p.read_text() for p in (REPO/'code/prompts').glob('*.txt')};self.stop=threading.Event();self.lock=threading.Lock();self.failed_consecutive=0;self.active={};self.local=threading.local()
  files={str(p.relative_to(REPO)):sha(p) for p in (REPO/'code').rglob('*') if p.is_file() and '__pycache__' not in str(p)};self.impl=digest({'files':files,'protocol':self.cfg});snap=OUT/'code_snapshots'/self.impl
  if not snap.exists():shutil.copytree(REPO/'code',snap/'code',ignore=shutil.ignore_patterns('__pycache__'));shutil.copy2(REPO/'protocol.json',snap/'protocol.json')
  dump(snap/'hashes.json',files);self.subs={};self.subhash={}
  with zipfile.ZipFile(DATA/'subtitle.zip') as z:
   names=set(z.namelist())
   for vid in {e['video_id'] for e in self.m['entries']}:
    member=f'subtitle/{vid}.srt'
    if member not in names:self.subs[vid]=[];self.subhash[vid]=None;continue
    raw=z.read(member);self.subhash[vid]=hashlib.sha256(raw).hexdigest();self.subs[vid]=[{'id':f'S{i:05}','start_s':s.start.ordinal/1000,'end_s':s.end.ordinal/1000,'text':re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]*>','',s.text))).strip()} for i,s in enumerate(pysrt.from_string(raw.decode('utf-8-sig',errors='replace')))]
 def redact(self,msg):
  for k in ['api_key','base_url']:msg=msg.replace(self.credentials[k],'<redacted>')
  return msg[:800]
 def stage(self,qid,stage):
  with self.lock:self.active[qid]=stage;self.progress('running')
 def progress(self,state):
  rs=[read(p) for p in (OUT/'results').glob('*.json')];calls=[read(p) for p in (OUT/'calls').glob('*/*/*/attempt-*.json')];counts=dict(collections.Counter(r['status'] for r in rs))
  s={'updated_at':now(),'pid':os.getpid(),'state':state,'selected':self.m['questions'],'terminal_results':len(rs),'remaining':self.m['questions']-len(rs),'status_counts':counts,'active':dict(self.active),'implementation':self.impl,'api_attempts':len(calls),'api_failed_attempts':sum(c['status']!='ok' for c in calls),'usage':{k:sum((c.get('usage') or {}).get(k,0) for c in calls) for k in ['prompt_tokens','completion_tokens','total_tokens']},'calls_without_returned_usage':sum(c.get('usage') is None for c in calls),'human_reviewed':False}
  dump(OUT/'status.json',s)
 def frame_packet(self,q,windows,stage):
  source_key=digest({'windows':windows,'sampling':self.cfg['source'],'membership_version':2})[:20]
  folder=OUT/'source'/safe(q['qid'])/stage/source_key;packetfile=folder/'packet.json'
  if packetfile.exists():
   packet=read(packetfile);assert packet['windows']==windows and all(sha(f['path'])==f['sha256'] for f in packet['frames']);return packet
  spacing=self.cfg['source']['coarse_spacing_s' if stage=='coarse' else 'refine_spacing_s'];cap=self.cfg['source']['max_coarse_frames' if stage=='coarse' else 'max_refine_frames'];wanted=collections.defaultdict(set)
  with av.open(q['video_path']) as con:
   stream=con.streams.video[0];duration=float(stream.duration*stream.time_base) if stream.duration else con.duration/av.time_base
   for g in windows:
    for a,b in g['windows']:
     assert 0<=a<b<=duration+.1
     ts=[a+i*spacing for i in range(int((b-a)/spacing)+1)];ts.append(max(a,b-.12))
     for t in ts:
      if t<duration:wanted[round(t,3)].add(g['id'])
   if len(wanted)>cap:raise ValueError(f'{stage} frame budget exceeded: {len(wanted)} > {cap}; no silent truncation')
   frames=[];folder.mkdir(parents=True,exist_ok=True)
   for i,(t,gids) in enumerate(sorted(wanted.items())):
    con.seek(int(t/stream.time_base),stream=stream,backward=True);chosen=None
    for f in con.decode(stream):
     if f.pts is not None and float(f.pts*stream.time_base)+1e-6>=t:chosen=f;break
    if chosen is None:raise ValueError(f'No decoded frame at {t}')
    actual=float(chosen.pts*stream.time_base);fid=f'{"C" if stage=="coarse" else "R"}{i:04}';path=folder/f'{fid}.jpg';im=chosen.to_image().convert('RGB');im.thumbnail((self.cfg['source']['max_image_side'],)*2,Image.Resampling.LANCZOS);im.save(path,quality=85)
    frames.append({'id':fid,'group_ids':sorted(g['id'] for g in windows if any(a-.15<=actual<=b+.15 for a,b in g['windows'])),'requested_s':t,'time_s':round(actual,6),'path':str(path),'sha256':sha(path)})
  subs=[]
  for s in self.subs[q['video_id']]:
   gids=[g['id'] for g in windows if any(s['start_s']<b and s['end_s']>a for a,b in g['windows'])]
   if gids:subs.append(dict(s,group_ids=gids))
  p={'packet_file':str(packetfile),'qid':q['qid'],'video_id':q['video_id'],'video_path':q['video_path'],'duration_s':duration,'windows':windows,'nominal_spacing_s':spacing,'frames':frames,'subtitles':subs,'subtitle_sha256':self.subhash[q['video_id']],'input_modalities':['original_video_sampled_frames','original_subtitles'],'audio_supplied':False}
  dump(packetfile,p);return p
 def align_witness_bounds(self,d,p):
  # Deterministic expansion to cited source timestamps, not a new semantic claim.
  changes=[];fs={f['id']:f for f in p['frames']};ss={s['id']:s for s in p['subtitles']}
  for f in d.get('facts',[]):
   for i,e in enumerate(f.get('evidence',[])):
    if not all(x in fs for x in e.get('frame_ids',[])) or not all(x in ss for x in e.get('subtitle_ids',[])):continue
    a,b=e['start_s'],e['end_s'];points=[fs[x]['time_s'] for x in e['frame_ids']];starts=points+[ss[x]['start_s'] for x in e['subtitle_ids']];ends=points+[ss[x]['end_s'] for x in e['subtitle_ids']]
    if not starts:continue
    lo=min([a]+starts);hi=max([b]+ends)
    if a-lo>10 or hi-b>10:continue
    if lo<hi and (lo!=a or hi!=b):
     e['start_s']=round(lo,6);e['end_s']=round(hi,6);changes.append({'fact_id':f['id'],'evidence_index':i,'proposed':[a,b],'source_aligned':[e['start_s'],e['end_s']],'rule':'expand by at most10s per edge to fully contain cited original subtitle cues/actual frame PTS; citations unchanged'})
  if changes:d['source_timestamp_normalizations']=changes
  return d
 def check_observation(self,d,p):
  assert isinstance(d,dict) and d['coverage'] in {'complete','partial','uncertain'} and isinstance(d['answer'],str) and isinstance(d['missing_zh'],list) and isinstance(d['groups_unresolved'],list)
  fs={f['id']:f for f in p['frames']};ss={s['id']:s for s in p['subtitles']};windows={g['id']:g['windows'] for g in p['windows']};facts=d['facts'];ids={f['id'] for f in facts};assert len(ids)==len(facts)
  for fact in facts:
   assert fact['status'] in {'supported','uncertain'} and isinstance(fact['statement'],str)
   if fact['status']=='supported':assert fact['evidence']
   for e in fact['evidence']:
    a,b=e['start_s'],e['end_s'];gid=e['group_id'];assert 0<=a<b<=p['duration_s']+.1 and b-a<=self.cfg['source']['max_evidence_interval_s'];assert gid in windows
    allowed=[(min([x]+[s['start_s'] for s in p['subtitles'] if gid in s['group_ids'] and s['start_s']<y and s['end_s']>x]),max([y]+[s['end_s'] for s in p['subtitles'] if gid in s['group_ids'] and s['start_s']<y and s['end_s']>x])) for x,y in windows[gid]]
    assert any(a>=x-.15 and b<=y+1.5 for x,y in allowed),'outside review windows'
    assert e['modality'] in {'visual','subtitle','mixed'} and e['frame_ids']+e['subtitle_ids'];assert isinstance(e['boundary_uncertainty_zh'],str)
    for fid in e['frame_ids']:assert fid in fs and gid in fs[fid]['group_ids'] and a-.15<=fs[fid]['time_s']<=b+.15,'bad frame citation'
    for sid in e['subtitle_ids']:assert sid in ss and gid in ss[sid]['group_ids'] and a-.15<=ss[sid]['start_s'] and ss[sid]['end_s']<=b+.15,'bad subtitle citation'
    if e['modality']=='visual':assert e['frame_ids']
    if e['modality']=='subtitle':assert e['subtitle_ids']
    if e['modality']=='mixed':assert e['frame_ids'] and e['subtitle_ids']
  for r in d['relations']:assert r['fact_ids'] and all(f in ids for f in r['fact_ids']) and r['status'] in {'supported','uncertain'}
 def check_audit(self,d,p,obs):
  for k in ['question_supported','reference_matches','relations_supported']:assert isinstance(d[k],bool)
  assert d['requires_multiple'] in {'yes','no','uncertain'};assert isinstance(d['missing_zh'],list) and isinstance(d['reference_issues_zh'],list);facts={f['id']:f for f in obs['facts']};fs={f['id'] for f in p['frames']};ss={s['id'] for s in p['subtitles']}
  assert len(d['fact_checks'])==len(facts) and {f['fact_id'] for f in d['fact_checks']}==set(facts)
  for c in d['fact_checks']:
   assert isinstance(c['supported'],bool) and set(c['frame_ids'])<=fs and set(c['subtitle_ids'])<=ss
   if c['supported']:assert c['frame_ids'] or c['subtitle_ids']
   evidences=facts[c['fact_id']]['evidence'];frame_map={f['id']:f for f in p['frames']};subtitle_map={z['id']:z for z in p['subtitles']}
   for fid in c['frame_ids']:
    f=frame_map[fid];assert any(e['group_id'] in f['group_ids'] and e['start_s']-.15<=f['time_s']<=e['end_s']+.15 for e in evidences),'audit citation outside fact interval'
   for sid in c['subtitle_ids']:
    z=subtitle_map[sid];assert any(e['group_id'] in z['group_ids'] and e['start_s']-.15<=z['start_s'] and z['end_s']<=e['end_s']+.15 for e in evidences),'audit subtitle outside fact interval'
  assert len({g['id'] for g in d['semantic_groups']})==len(d['semantic_groups'])
  for g in d['semantic_groups']:
   assert g['fact_ids'] and set(g['fact_ids'])<=set(facts) and g['interval_refs']
   for r in g['interval_refs']:assert r['fact_id'] in g['fact_ids'] and 0<=r['evidence_index']<len(facts[r['fact_id']]['evidence'])
 def call(self,q,stage,header,p,check):
  self.stage(q['qid'],stage);content=[{'type':'text','text':canon(header)}]
  for f in p['frames']:
   content.extend([{'type':'text','text':f"FRAME {f['id']} actual video timestamp {f['time_s']:.6f}s; groups {','.join(f['group_ids'])}"},{'type':'image_url','image_url':{'url':'data:image/jpeg;base64,'+base64.b64encode(Path(f['path']).read_bytes()).decode(),'detail':'high'}}])
  payload={'model':self.cfg['model'],'messages':[{'role':'system','content':self.prompts[stage]},{'role':'user','content':content}],'max_tokens':self.cfg['api']['max_output_tokens'],'temperature':0,'response_format':{'type':'json_object'},'extra_body':{'enable_thinking':self.cfg['api']['enable_thinking']},'stream':True,'stream_options':{'include_usage':True}}
  key=digest({'header':header,'frames':[{k:f[k] for k in ['id','sha256','time_s','group_ids']} for f in p['frames']],'prompt':self.prompts[stage],'cfg':self.cfg,'implementation':self.impl});folder=OUT/'calls'/safe(q['qid'])/stage/key[:24];completed=folder/'completed.json'
  if completed.exists():r=read(completed);check(r['parsed']);return r['parsed'],str(completed)
  logged=json.loads(canon(payload));fi=iter(p['frames'])
  for x in logged['messages'][1]['content']:
   if x['type']=='image_url':f=next(fi);x['image_url']['url']='sha256:'+f['sha256'];x['local_source_path']=f['path']
  dump(folder/'request.json',{'payload':logged,'implementation':self.impl,'cache_key':key,'source_packet_sha256':digest(p)})
  existing=len(list(folder.glob('attempt-*.json')))
  for n in range(self.cfg['api']['attempts_per_stage']):
   if self.stop.is_set() or (OUT/'STOP').exists():raise InterruptedError('stop requested')
   r={'qid':q['qid'],'stage':stage,'started_at':now(),'raw_text':'','usage':None,'implementation':self.impl,'attempt':existing+n+1};started=time.monotonic()
   try:
    with httpx.Client(proxy='http://127.0.0.1:7897',trust_env=False,timeout=self.cfg['api']['timeout_s']) as client:
     api=OpenAI(api_key=self.credentials['api_key'],base_url=self.base,http_client=client,max_retries=0)
     with api.chat.completions.create(**payload) as stream:
      for chunk in stream:
       if time.monotonic()-started>self.cfg['api']['max_stage_wall_s']:raise TimeoutError('stage wall deadline')
       r['resolved_model']=chunk.model
       if chunk.usage:r['usage']=chunk.usage.model_dump()
       for c in chunk.choices:
        if c.delta.content:r['raw_text']+=c.delta.content
        if c.finish_reason:r['finish_reason']=c.finish_reason
    assert r.get('finish_reason')=='stop','incomplete response';d=json.loads(r['raw_text'])
    if stage in {'locate','refine'}:d=self.align_witness_bounds(d,p)
    check(d)
    r.update(status='ok',parsed=d,completed_at=now(),elapsed_s=time.monotonic()-started);dump(folder/f'attempt-{existing+n+1:02}.json',r);dump(completed,r);return d,str(completed)
   except Exception as exc:
    r.update(status='failed',error_type=type(exc).__name__,error=self.redact(str(exc)),completed_at=now(),elapsed_s=time.monotonic()-started);dump(folder/f'attempt-{existing+n+1:02}.json',r)
    if getattr(exc,'status_code',None) in {401,403}:self.stop.set();dump(OUT/'circuit_breaker.json',{'at':now(),'reason':'authentication/authorization rejected'});raise
    if n+1==self.cfg['api']['attempts_per_stage']:raise RuntimeError(f'{stage} exhausted attempts; see call ledger') from None
    # Add the schema failure, not source hypotheses, to a deterministic retry prompt.
    payload['messages'][0]['content']=self.prompts[stage]+'\nPrevious response failed machine validation: '+self.redact(str(exc))+'. Recheck exact source IDs, required fields and timestamp bounds; output complete valid JSON.'
    dump(folder/f'retry-prompt-{existing+n+2:02}.json',{'system_prompt':payload['messages'][0]['content']})
    self.stop.wait(self.cfg['api']['retry_backoff_s'])
 def source_header(self,q,p):return {'qid':q['qid'],'question':q['question'],'video_id':q['video_id'],'review_windows':p['windows'],'subtitles':p['subtitles'],'sampling_spacing_s':p['nominal_spacing_s'],'audio_supplied':False}
 def one(self,e):
  if self.stop.is_set() or (OUT/'STOP').exists():return
  q=read(e['input_file']);assert sha(e['input_file'])==e['input_sha256'];dest=OUT/'results'/f"{safe(q['qid'])}.json";r={'qid':q['qid'],'video_id':q['video_id'],'started_at':now(),'implementation':self.impl,'input_sha256':e['input_sha256'],'human_reviewed':False}
  try:
   self.stage(q['qid'],'extract_coarse');v=Path(q['video_path']);assert v.stat().st_size==q['video_size_bytes'] and v.stat().st_mtime_ns==q['video_mtime_ns'];r['source_video_sha256']=sha(v)
   with av.open(str(v)) as con:duration=con.duration/av.time_base
   margin=self.cfg['source']['context_margin_s'];windows=[{'id':g['id'],'windows':merge([(max(0,a-margin),min(duration,b+margin)) for a,b in g['windows']])} for g in q['groups']]
   coarse=self.frame_packet(q,windows,'coarse');obs,c=self.call(q,'locate',self.source_header(q,coarse),coarse,lambda d:self.check_observation(d,coarse));r.update(coarse_call=c,coarse_observation=obs)
   if not any(f['evidence'] for f in obs['facts']):r.update(status='source_unresolved',reason='No cited source witness from blind localization');return
   spans=collections.defaultdict(list);margin=self.cfg['source']['refine_boundary_margin_s']
   for f in obs['facts']:
    for w in f['evidence']:spans[w['group_id']].append([max(0,w['start_s']-margin),min(duration,w['end_s']+margin)])
   refinedwindows=[{'id':gid,'windows':merge(v)} for gid,v in sorted(spans.items())];self.stage(q['qid'],'extract_refined');p=self.frame_packet(q,refinedwindows,'refined');header=self.source_header(q,p);header['prior_observation']=obs
   obs,c=self.call(q,'refine',header,p,lambda d:self.check_observation(d,p));r.update(refined_call=c,observation=obs,source_packet_file=p['packet_file'],source_packet_sha256=digest(p))
   header=self.source_header(q,p);header.update(options=q['options'],reference_answer=q['reference_answer'],observation=obs);audit,c=self.call(q,'audit',header,p,lambda d:self.check_audit(d,p,obs));r.update(audit=audit,audit_call=c)
   allok=bool(obs['facts']) and obs['coverage']=='complete' and not obs['missing_zh'] and not obs['groups_unresolved'] and all(f['status']=='supported' for f in obs['facts']) and all(z['status']=='supported' for z in obs['relations']) and all(audit[k] for k in ['question_supported','reference_matches','relations_supported']) and all(f['supported'] for f in audit['fact_checks']) and not audit['missing_zh'] and not audit['reference_issues_zh']
   r['status']='source_supported_multi' if allok and audit['requires_multiple']=='yes' and len(audit['semantic_groups'])>=2 else ('source_supported_single_or_redundant' if allok and audit['requires_multiple']=='no' else 'source_unresolved')
   r['fact_evidence']=[{'fact_id':f['id'],'statement':f['statement'],'status':f['status'],'video_id':q['video_id'],'intervals':f['evidence']} for f in obs['facts']];r['cross_segment_relations']=obs['relations'];r['boundary_precision']='1-second target sampling, actual frame PTS and subtitle timings; witness intervals, not exact event onset/end';r['audio_verified']=False
  except InterruptedError:r.update(status='interrupted',reason='graceful stop; resume stage cache')
  except Exception as exc:r.update(status='technical_failed',error_type=type(exc).__name__,error=self.redact(str(exc)))
  finally:
   r['completed_at']=now();dump(dest,r)
   with self.lock:
    self.active.pop(q['qid'],None);self.failed_consecutive=self.failed_consecutive+1 if r.get('status')=='technical_failed' else 0
    if self.failed_consecutive>=self.cfg['api']['stop_after_consecutive_failed_questions']:self.stop.set();dump(OUT/'circuit_breaker.json',{'at':now(),'reason':'consecutive technical failures; explicit inspection before resume'})
    self.progress('stopping' if self.stop.is_set() else 'running')
   print(json.dumps({'qid':q['qid'],'status':r.get('status'),'at':r['completed_at']},ensure_ascii=False),flush=True)
 def run(self,limit=None,retry_failed=False):
  if (OUT/'STOP').exists() or (OUT/'circuit_breaker.json').exists():raise RuntimeError('STOP/circuit breaker exists; inspect and explicitly clear before restart')
  todo=[]
  for e in self.m['entries']:
   dest=OUT/'results'/f"{safe(e['qid'])}.json"
   if dest.exists():
    previous=read(dest)
    if previous['status']=='interrupted' or retry_failed and previous['status']=='technical_failed':
     dump(OUT/'result_history'/safe(e['qid'])/f'{time.time_ns()}.json',previous);dest.unlink()
    else:continue
   todo.append(e)
  if limit:todo=todo[:limit]
  self.progress('running');stopheartbeat=threading.Event()
  def heartbeat():
   while not stopheartbeat.wait(20):
    with self.lock:self.progress('stopping' if self.stop.is_set() else 'running')
  thread=threading.Thread(target=heartbeat,daemon=True);thread.start()
  for sig in [signal.SIGTERM,signal.SIGINT]:signal.signal(sig,lambda *_:self.stop.set())
  try:
   with concurrent.futures.ThreadPoolExecutor(max_workers=self.cfg['api']['concurrency']) as pool:list(pool.map(self.one,todo))
  finally:
   stopheartbeat.set();thread.join();self.progress('paused' if self.stop.is_set() or (OUT/'STOP').exists() else ('completed' if len(list((OUT/'results').glob('*.json')))==self.m['questions'] else 'pilot_completed'));self.export()
 def export(self):
  rows=[read(p) for p in sorted((OUT/'results').glob('*.json'))];dump(OUT/'all_results.json',rows);dump(OUT/'supported_multi.json',[r for r in rows if r['status']=='source_supported_multi']);dump(OUT/'summary.json',read(OUT/'status.json'))

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','run','status']);ap.add_argument('--limit',type=int);ap.add_argument('--retry-failed',action='store_true');a=ap.parse_args()
 if a.action=='prepare':prepare()
 elif a.action=='status':print(json.dumps(read(OUT/'status.json'),ensure_ascii=False,indent=2))
 else:
  OUT.mkdir(parents=True,exist_ok=True)
  with (OUT/'runner.lock').open('a') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);Runner().run(a.limit,a.retry_failed)
