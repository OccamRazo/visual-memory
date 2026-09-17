#!/usr/bin/env python3
"""Source-grounded temporal grouping. Immutable calls; deterministic projection/replay."""
import argparse,base64,collections,concurrent.futures,datetime,hashlib,html,itertools,json,math,os,re,shutil,threading,time,zipfile
from pathlib import Path
from urllib.parse import urlsplit
import av,httpx,pysrt
from PIL import Image,ImageDraw
from openai import OpenAI
REPO=Path(__file__).resolve().parents[1]
OUT=Path('/mnt/raid5-01/baorui/visual-memory/EXP-20260917-videomme-evidence-groups/run-002-continuity')
DATA=Path('/mnt/raid5-01/baorui/Video-MME')
INVENTORY=Path('/mnt/raid5-01/baorui/visual-memory/EXP-20260916-memory-data-prep/run-001-inventory')
def read(p):return json.loads(Path(p).read_text())
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def safe(q):return q.replace(':','__')
def dump(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');t.replace(p)
def unique(xs):return list(dict.fromkeys(xs))
def ts(t):return f'{int(t)//60:02}:{t%60:06.3f}'
class Runner:
 def __init__(self):
  self.cfg=read(REPO/'protocol.json');self.rows={r['qid']:r for r in map(json.loads,Path(self.cfg['source']).read_text().splitlines())};self.local=threading.local()
  self.prompts={p.stem:p.read_text() for p in (REPO/'code/prompts').glob('*.txt')}
  self.credentials=read('/home/baorui/projects/visual-memory/tmp/api.json')
  self.base=self.credentials['base_url'].rstrip('/')
  if urlsplit(self.base).path in ('','/'):self.base+='/v1'
  self.durations={Path(v['path']).stem:v['duration_s'] for v in map(json.loads,(INVENTORY/'video_probes.jsonl').read_text().splitlines())}
  self.subs={};self.subhash={}
  with zipfile.ZipFile(DATA/'subtitle.zip') as archive:
   for vid in {r['video_id'] for r in self.rows.values()}:
    name=f'subtitle/{vid}.srt'
    if name not in archive.namelist():self.subs[vid]=[];self.subhash[vid]=None;continue
    raw=archive.read(name);self.subhash[vid]=hashlib.sha256(raw).hexdigest()
    self.subs[vid]=[{'subtitle_id':f'S{i:05}','start_s':s.start.ordinal/1000,'end_s':s.end.ordinal/1000,'text':re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]*>','',s.text))).strip()} for i,s in enumerate(pysrt.from_string(raw.decode('utf-8-sig',errors='replace')))]
  self.impl=hashlib.sha256((sha(__file__)+canon(self.prompts)+canon(self.cfg)).encode()).hexdigest()
  OUT.mkdir(parents=True,exist_ok=True);snap=OUT/'code_snapshots'/self.impl
  if not snap.exists():shutil.copytree(REPO/'code',snap,ignore=shutil.ignore_patterns('__pycache__'))
  manifest={'qids':list(self.rows),'source_file':self.cfg['source'],'source_sha256':sha(self.cfg['source']),'protocol_sha256':sha(REPO/'protocol.json')}
  if (OUT/'input_manifest.json').exists():assert read(OUT/'input_manifest.json')==manifest
  else:dump(OUT/'input_manifest.json',manifest)
 def client(self):
  if not hasattr(self.local,'client'):self.local.client=OpenAI(api_key=self.credentials['api_key'],base_url=self.base,http_client=httpx.Client(proxy=os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy'),trust_env=False),timeout=self.cfg['api']['timeout_seconds'],max_retries=0)
  return self.local.client
 def call(self,qid,stage,header,frames):
  content=[{'type':'text','text':canon(header)}]
  for f in frames:
   content.extend([{'type':'text','text':f"Frame {f['frame_id']} actual PTS {f['actual_pts_s']:.3f}s"},{'type':'image_url','image_url':{'url':'data:image/jpeg;base64,'+base64.b64encode(Path(f['path']).read_bytes()).decode(),'detail':'high'}}])
  payload={'model':self.credentials['model'],'messages':[{'role':'system','content':self.prompts[stage]},{'role':'user','content':content}],'max_completion_tokens':self.cfg['api']['max_output_tokens'],'response_format':{'type':'json_object'}}
  digest=hashlib.sha256(canon(payload).encode()).hexdigest();folder=OUT/'calls'/safe(qid)/stage/digest[:20]
  if (folder/'completed.json').exists():return read(folder/'completed.json')['parsed'],str(folder/'completed.json')
  logged=json.loads(canon(payload))
  for x in logged['messages'][1]['content']:
   if x['type']=='image_url':x['image_url']['url']='sha256:'+hashlib.sha256(base64.b64decode(x['image_url']['url'].split(',',1)[1])).hexdigest()
  dump(folder/'request.json',{'implementation':self.impl,'request_sha256':digest,'payload':logged})
  offset=len(list(folder.glob('attempt-*.json')))
  for attempt in range(self.cfg['api']['attempts']):
   rec={'qid':qid,'stage':stage,'implementation':self.impl,'request_sha256':digest,'started_unix':time.time(),'attempt':offset+attempt+1}
   try:
    result=self.client().chat.completions.create(**payload);choice=result.choices[0]
    rec.update(resolved_model=result.model,usage=result.usage.model_dump() if result.usage else None,raw_text=choice.message.content,finish_reason=choice.finish_reason,response_id=result.id)
    if choice.finish_reason!='stop':raise ValueError('Model output incomplete')
    parsed=json.loads(choice.message.content)
    if not isinstance(parsed,dict):raise ValueError('Response is not object')
    rec.update(parsed=parsed,status='ok',elapsed_s=time.time()-rec['started_unix']);dump(folder/f"attempt-{rec['attempt']:02}.json",rec);dump(folder/'completed.json',rec)
    return parsed,str(folder/'completed.json')
   except Exception as e:
    msg=str(e)
    for key in ['api_key','base_url']:msg=msg.replace(self.credentials[key],'<redacted>')
    rec.update(status='failed',error_type=type(e).__name__,error=msg[:1000]);dump(folder/f"attempt-{rec['attempt']:02}.json",rec)
    if attempt+1==self.cfg['api']['attempts']:raise RuntimeError(f'{qid}/{stage} failed; see redacted ledger') from None
 def source(self,r):
  p=read(r['package_file']);assert sha(r['package_file'])==r['package_sha256']
  supports=json.loads(canon(r['fact_support']))
  for f in supports:f['subtitle_ids']=[f'S{int(x.split(":")[-1].lstrip("S")):05}' for x in f.get('subtitle_ids',[])]
  bank={'qid':r['qid'],'video_id':r['video_id'],'duration_s':self.durations[r['video_id']],'original_package_file':r['package_file'],'original_package_sha256':r['package_sha256'],'frames':p['frames'],'subtitles':self.subs[r['video_id']],'subtitle_member_sha256':self.subhash[r['video_id']],'prior_fact_support':supports}
  path=OUT/'sources'/f'{safe(r["qid"])}.json'
  if path.exists():assert read(path)==bank
  else:dump(path,bank)
  return bank
 def propose_input(self,r,bank,revision=None):
  fs={x for s in bank['prior_fact_support'] for x in s.get('frame_ids',[])};chosen=[x for x in bank['frames'] if x['frame_id'] in fs]
  # Preserve cited frames and six deterministic overview/context samples.
  for i in range(min(6,len(bank['frames']))):
   x=bank['frames'][round(i*(len(bank['frames'])-1)/max(1,min(6,len(bank['frames']))-1))]
   if x not in chosen:chosen.append(x)
  eligible_subs=[s for s in bank['subtitles'] if 0<=s['start_s']<s['end_s']<=bank['duration_s']+.001]
  h={'question':r['question'],'required_facts':r['required_facts'],'duration_s':bank['duration_s'],'full_original_subtitles':eligible_subs,'trailing_subtitle_units_beyond_video_omitted':len(bank['subtitles'])-len(eligible_subs),'prior_fact_support':bank['prior_fact_support'],'prior_scope':r['task_labels']['scope'],'frame_index':[{'id':x['frame_id'],'time_s':x['actual_pts_s']} for x in chosen],'caption_evidence':False,'source_constraints':'Every cited frame/subtitle must actually belong inside its group interval. Check the explicit frame PTS index; never move a far-away frame to a plausible scene. Do not use subtitle units extending beyond video duration.'}
  if revision:h['revision_request']=revision
  return h,chosen
 def normalize(self,raw,bank):
  fs={f['frame_id']:f for f in bank['frames']};ss={s['subtitle_id']:s for s in bank['subtitles']};groups=[];log=[]
  for g0 in raw.get('groups',[]):
   g=json.loads(canon(g0));assert isinstance(g.get('frame_ids'),list) and isinstance(g.get('subtitle_ids'),list)
   assert set(g['frame_ids'])<=set(fs),('unknown frame',g)
   assert set(g['subtitle_ids'])<=set(ss),('unknown subtitle',g)
   assert g['frame_ids'] or g['subtitle_ids'],'Empty group'
   a=float(g['start_s']);b=float(g['end_s']);assert math.isfinite(a) and math.isfinite(b) and 0<=a<b<=bank['duration_s']+.1,('interval_outside_video',g['id'],a,b,bank['duration_s'])
   aa=[fs[x]['actual_pts_s'] for x in g['frame_ids']]+[ss[x]['start_s'] for x in g['subtitle_ids']]
   bb=[fs[x]['actual_pts_s']+.04 for x in g['frame_ids']]+[ss[x]['end_s'] for x in g['subtitle_ids']]
   assert all(a-3<=fs[x]['actual_pts_s']<=b+3 for x in g['frame_ids']) and all(ss[x]['start_s']>=a-15 and ss[x]['end_s']<=b+15 for x in g['subtitle_ids']),('misplaced_source_anchor',g['id'],'interval',[a,b],'frame_times',[(x,fs[x]['actual_pts_s']) for x in g['frame_ids']],'subtitle_spans',[(x,ss[x]['start_s'],ss[x]['end_s']) for x in g['subtitle_ids']])
   assert max(bb)<=bank['duration_s']+.001,('cited_subtitle_beyond_video',g['id'])
   newa=round(max(0,min(a,*aa)),3);newb=round(min(bank['duration_s'],max(b,*bb)),3)
   if newa!=a or newb!=b:log.append({'action':'expand_to_include_cited_source','old':[a,b],'new':[newa,newb]})
   g.update(start_s=newa,end_s=newb,proposal_ids=[g['id']]);groups.append(g)
  assert groups,'No groups'
  groups.sort(key=lambda g:g['start_s']);merged=[]
  for g in groups:
   if merged and g['start_s']<=merged[-1]['end_s']:
    prev=merged[-1];log.append({'action':'merge_touching_or_overlap','proposal_ids':prev['proposal_ids']+g['proposal_ids']});prev['end_s']=max(prev['end_s'],g['end_s'])
    for field in ['frame_ids','subtitle_ids','fact_ids','proposal_ids']:prev[field]=unique(prev.get(field,[])+g.get(field,[]))
    for field in ['label_zh','episode_reason_zh','source_summary_zh','boundary_uncertainty_zh']:prev[field]='；'.join(unique([x for x in [prev.get(field,''),g.get(field,'')] if x]))
    prev['boundary_basis']='mixed';prev['role']='direct'
   else:merged.append(g)
  for i,g in enumerate(merged):g['id']=f'G{i+1:02}';g['review_start_s']=max(0,g['start_s']-3);g['review_end_s']=min(bank['duration_s'],g['end_s']+3)
  return merged,log
 def project(self,r,bank,groups,roundno):
  variant=hashlib.sha256(canon(groups).encode()).hexdigest()[:12]
  dest=OUT/'packages'/safe(r['qid'])/f'round-{roundno:02}-{variant}.json'
  if dest.exists():
   old=read(dest);assert old['groups']==groups;return old,dest
  times=[]
  for g in groups:
   offsets=[-2,0,2] if g['frame_ids'] else [0]
   for edge in [g['start_s'],g['end_s']]:
    for off in offsets:times.append(edge+off)
   for frac in ([.25,.5,.75] if g['frame_ids'] else [.5]):times.append(g['start_s']+frac*(g['end_s']-g['start_s']))
  selected=[]
  for t in sorted(times):
   if 0<=t<bank['duration_s'] and not any(abs(t-v)<.08 for v in selected):selected.append(t)
  frames=list(bank['frames']);video=DATA/'data'/f'{r["video_id"]}.mp4'
  with av.open(str(video)) as con:
   stream=con.streams.video[0]
   for i,t in enumerate(selected):
    con.seek(int(t/stream.time_base),stream=stream,backward=True)
    for f in con.decode(stream):
     if f.pts is None:continue
     actual=float(f.pts*stream.time_base)
     if actual+1e-6<t:continue
     im=f.to_image().convert('RGB');im.thumbnail((1024,1024),Image.Resampling.LANCZOS)
     path=OUT/'frames'/safe(r['qid'])/f'round-{roundno:02}-{variant}'/f'R{i+1:03}.jpg';path.parent.mkdir(parents=True,exist_ok=True);im.save(path,quality=94)
     frames.append({'frame_id':f'R{i+1:03}','actual_pts_s':actual,'requested_s':t,'path':str(path),'sha256':sha(path),'source_video':str(video)});break
    else:raise ValueError(f'Cannot extract frame {t}')
  package={'qid':r['qid'],'video_id':r['video_id'],'groups':groups,'frames':frames,'subtitles':bank['subtitles'],'subtitle_member_sha256':bank['subtitle_member_sha256'],'source_video':str(video),'source_bank_file':str(OUT/'sources'/f'{safe(r["qid"])}.json'),'generated_captions_in_evidence':False,'round':roundno}
  dump(dest,package);return package,dest
 def group_content(self,r,p,ids=None,audit=False):
  groups=[g for g in p['groups'] if ids is None or g['id'] in ids];frames=[];chunks=[]
  for i,g in enumerate(groups):
   a,b=(g['review_start_s'],g['review_end_s']) if audit else (g['start_s'],g['end_s'])
   subs=[s for s in p['subtitles'] if (s['start_s']<b and s['end_s']>a) if audit or (s['start_s']>=a-.001 and s['end_s']<=b+.001)]
   pool=[f for f in p['frames'] if a<=f['actual_pts_s']<=b]
   selected=[f for f in pool if f['frame_id'] in g['frame_ids'] or f['frame_id'].startswith('R')]
   context=[f for f in pool if f not in selected]
   for j in range(min(4,len(context))):
    selected.append(context[round(j*(len(context)-1)/max(1,min(4,len(context))-1))])
   for f in selected:
    if f not in frames:frames.append(f)
   part={'interval_id':g['id'] if audit else f'I{i+1:02}','start_s':g['start_s'],'end_s':g['end_s'],'subtitles':subs}
   if audit:part.update(proposed_group={k:v for k,v in g.items() if k!='proposal_ids'},context_start_s=a,context_end_s=b)
   chunks.append(part)
  frames.sort(key=lambda f:f['actual_pts_s'])
  header={'question':r['question'],'required_facts':r['required_facts'],'intervals':chunks,'note':'Original source only. No generated captions. Intervals identify retrieval windows; frame PTS and subtitle spans are original.'}
  return header,frames
 def check_subset(self,r,p,ids):
  if not ids:return {'all_facts_supported':False,'scope_adequate':False,'facts':[{'fact_id':f['id'],'status':'unresolved','frame_ids':[],'subtitle_ids':[],'reason_zh':'无保留源证据'} for f in r['required_facts']],'missing_zh':['Empty source set: no evidence-backed answer.']},None
  h,frames=self.group_content(r,p,ids=ids)
  notes=REPO/'evaluation_notes'/f'{safe(r["qid"])}.json'
  if notes.exists():h['rubric_interpretation_constraints']=read(notes)['constraints']
  wanted={f['id'] for f in r['required_facts']}
  fs={f['frame_id'] for f in frames};ss={s['subtitle_id'] for c in h['intervals'] for s in c['subtitles']}
  h['output_schema_constraints']={'exact_fact_ids':sorted(wanted),'one_row_per_fact':True,'allowed_frame_ids':sorted(fs),'allowed_subtitle_ids':sorted(ss),'instruction':'Use exactly these fact IDs; do not add subfact rows. Cite only explicitly allowed source IDs, never interpolate missing numbers.'}
  for schema_attempt in range(3):
   result,path=self.call(r['qid'],'subset',h,frames);errors=[];got=[x.get('fact_id') for x in result.get('facts',[])]
   if set(got)!=wanted or len(got)!=len(wanted):errors.append('fact_id_mismatch')
   for f in result.get('facts',[]):
    if not set(f.get('frame_ids',[]))<=fs or not set(f.get('subtitle_ids',[]))<=ss:errors.append('invalid_source_citation')
    if f.get('status')=='supported' and not (f.get('frame_ids') or f.get('subtitle_ids')):errors.append('supported_fact_without_citation')
   dump(Path(path).parent/'schema_validation.json',{'passed':not errors,'errors':unique(errors)})
   if not errors:return result,path
   h['format_retry']={'attempt':schema_attempt+1,'errors':unique(errors),'instruction':'Re-evaluate only the supplied source and follow the exact output schema. No omitted evidence or prior response is supplied.'}
  raise ValueError('Subset schema invalid after bounded repair')
 def subset_success(self,r):return r.get('all_facts_supported') is True and r.get('scope_adequate') is True and all(f['status']=='supported' for f in r['facts'])
 def test_sets(self,r,p,audit):
  allids=[g['id'] for g in p['groups']];tested=[];cache={}
  def check(ids):
   key=tuple(sorted(ids))
   if key not in cache:
    value,path=self.check_subset(r,p,list(key));cache[key]=self.subset_success(value);tested.append({'group_ids':list(key),'supported':cache[key],'result':value,'call_file':path})
   return cache[key]
  if not check(allids):return {'status':'full_group_set_not_sufficient','selected_group_ids':allids,'tests':tested,'minimality':'not established'}
  candidates=[set()]
  for f in audit.get('fact_support',[]):
   options=f.get('supported_by',[])
   if not options:candidates=[];break
   candidates=[a|set(b) for a in candidates for b in options]
   candidates=[set(t) for t in {tuple(sorted(c)) for c in candidates}]
   candidates=[c for c in candidates if not any(other<c for other in candidates)]
   if len(candidates)>10000:raise ValueError('Too many support-set combinations')
  durations={g['id']:g['end_s']-g['start_s'] for g in p['groups']};candidates=sorted(candidates,key=lambda s:(len(s),sum(durations[x] for x in s),sorted(s)))
  active=list(allids)
  if candidates:
   candidate=sorted(candidates[0]);assert set(candidate)<=set(allids)
   if check(candidate):active=candidate
  # Greedy remove redundant groups. Exact cached replay; no claim of global cardinality minimum.
  changed=True
  while changed:
   changed=False
   for gid in list(reversed(active)):
    remaining=[x for x in active if x!=gid]
    if check(remaining):active=remaining;changed=True
  for gid in active:assert not check([x for x in active if x!=gid])
  return {'status':'source_subset_verified','selected_group_ids':active,'redundant_or_alternative_group_ids':[g for g in allids if g not in active],
   'tests':tested,'minimality':'inclusion-minimal within this provided evidence collection and evaluator; not guaranteed global/video-wide cardinality minimum','irreducible_group_count':len(active)}
 def sheet(self,p,qid):
  byid={f['frame_id']:f for f in p['frames']};items=[]
  for g in p['groups']:
   points=[g['start_s'],(g['start_s']+g['end_s'])/2,g['end_s']]
   fs=[f for f in p['frames'] if g['review_start_s']<=f['actual_pts_s']<=g['review_end_s']]
   chosen=[]
   for t in points:
    if fs:
     f=min(fs,key=lambda f:abs(f['actual_pts_s']-t))
     if f not in chosen:chosen.append(f)
   for fid in g['frame_ids'][:2]:
    if byid[fid] not in chosen:chosen.append(byid[fid])
   items.extend((g['id'],f) for f in chosen)
  paths=[]
  for page in range(math.ceil(len(items)/16)):
   batch=items[page*16:(page+1)*16];im=Image.new('RGB',(1536,244*math.ceil(len(batch)/4)),'white');draw=ImageDraw.Draw(im)
   for j,(gid,f) in enumerate(batch):
    tile=Image.open(f['path']);tile.thumbnail((384,216));x,y=j%4*384,j//4*244;im.paste(tile,(x,y));draw.text((x+3,y+218),f'{gid} {f["frame_id"]} {f["actual_pts_s"]:.2f}s',fill='black')
   variant=hashlib.sha256(canon(p['groups']).encode()).hexdigest()[:12]
   dest=OUT/'sheets'/safe(qid)/variant/f'page-{page+1:02}.jpg';dest.parent.mkdir(parents=True,exist_ok=True);im.save(dest,quality=95);paths.append({'path':str(dest),'sha256':sha(dest)})
  return paths
 def process(self,qid):
  dest=OUT/'results'/f'{safe(qid)}.json'
  if dest.exists():return read(dest)
  r=self.rows[qid];record={'qid':qid,'video_id':r['video_id'],'question':r['question'],'required_facts':r['required_facts'],'implementation':self.impl,'human_reviewed':False,'source_dataset_sha256':sha(self.cfg['source']),'started_at':datetime.datetime.now().astimezone().isoformat(),'rounds':[]}
  try:
   bank=self.source(r);revision=None;ablation=None
   for roundno in range(1,self.cfg['audit']['max_revision_rounds']+2):
    h,frames=self.propose_input(r,bank,revision)
    for format_attempt in range(3):
     override=REPO/'group_overrides'/f'{safe(qid)}.json'
     if roundno==1 and format_attempt==0 and override.exists():
      frozen=OUT/'manual_inputs'/safe(qid)/(sha(override)+'.json')
      if not frozen.exists():dump(frozen,read(override))
      raw=read(frozen)['proposal'];propath=str(frozen)
     else:raw,propath=self.call(qid,'propose',h,frames)
     try:groups,normal=self.normalize(raw,bank);break
     except (AssertionError,ValueError,KeyError,TypeError) as exc:
      dump(Path(propath).parent/'schema_validation.json',{'passed':False,'error':str(exc)[:4000]})
      if format_attempt==2:raise
      h['format_retry']={'attempt':format_attempt+1,'error':str(exc)[:4000],'instruction':'Correct the temporal/ID schema error. Reassign or omit misplaced anchors; do not fabricate frame times or stretch unrelated groups to encompass a far-away wrong citation. Return a complete corrected proposal from the source.'}
    p,ppath=self.project(r,bank,groups,roundno)
    h,frames=self.group_content(r,p,audit=True)
    notes=REPO/'evaluation_notes'/f'{safe(qid)}.json'
    if notes.exists():h['rubric_interpretation_constraints']=read(notes)['constraints']
    expected_groups={g['id'] for g in groups};expected_facts={f['id'] for f in r['required_facts']}
    h['output_schema_constraints']={'exact_group_ids':sorted(expected_groups),'exact_fact_ids':sorted(expected_facts),'one_row_per_group_and_fact':True,'instruction':'Use only these current group IDs. Do not use old proposal group IDs or invent subgroups in the output checks.'}
    for format_attempt in range(3):
     audit,apath=self.call(qid,'audit',h,frames);errors=[]
     if {x.get('group_id') for x in audit.get('group_checks',[])}!=expected_groups or len(audit.get('group_checks',[]))!=len(expected_groups):errors.append('group_id_mismatch')
     if {x.get('fact_id') for x in audit.get('fact_support',[])}!=expected_facts or len(audit.get('fact_support',[]))!=len(expected_facts):errors.append('fact_id_mismatch')
     for fact in audit.get('fact_support',[]):
      for option in fact.get('supported_by',[]):
       if not set(option)<=expected_groups:errors.append('invalid_support_group_id')
     dump(Path(apath).parent/'schema_validation.json',{'passed':not errors,'errors':unique(errors)})
     if not errors:break
     if format_attempt==2:raise ValueError('Audit schema invalid after bounded repair')
     h['format_retry']={'attempt':format_attempt+1,'errors':unique(errors),'instruction':'Use exactly the provided current group IDs and fact IDs. Reinspect source and output valid schema; any desired split/merge goes in revision instructions, not invented group IDs.'}
    record['rounds'].append({'round':roundno,'proposal_call':propath,'audit_call':apath,'package_file':str(ppath),'package_sha256':sha(ppath),'normalization':normal,'proposal_unresolved':raw.get('unresolved',[]),'audit':audit})
    if audit.get('segmentation_status')=='pass' and audit.get('all_facts_supported') is True:
     ablation=self.test_sets(r,p,audit);record['rounds'][-1]['subset_validation']=ablation
     if ablation['status']=='source_subset_verified':break
    else:ablation=None
    revision={'previous_proposal':raw,'normalized_groups':groups,'independent_source_audit':audit,'raw_subset_failure':ablation,'instruction':'Revise only the grouping/source anchors/bounds. Preserve the frozen question and facts. Fix the specific issue using actual source, do not merely restate prior claims. A failed all-group raw-source test identifies a real possible gap not resolved by the boundary audit.'}
   record.update(groups=groups,package_file=str(ppath),package_sha256=sha(ppath),audit=audit,sheets=self.sheet(p,qid))
   if ablation is not None:
    record['subset_validation']=ablation
    record['status']='review_candidate' if ablation['status']=='source_subset_verified' else 'needs_source_review'
   else:record['status']='needs_segmentation_review'
  except Exception as e:
   msg=str(e)
   for k in ['api_key','base_url']:msg=msg.replace(self.credentials[k],'<redacted>')
   record.update(status='processing_failed',error_type=type(e).__name__,error=msg[:1600])
  record['completed_at']=datetime.datetime.now().astimezone().isoformat();dump(dest,record);return record
 def summary(self):
  rows=[read(p) for p in (OUT/'results').glob('*.json')];calls=[read(p) for p in (OUT/'calls').glob('*/*/*/attempt-*.json')]
  s={'processed':len(rows),'target':60,'status_counts':dict(collections.Counter(r['status'] for r in rows)),'groups':sum(len(r.get('groups',[])) for r in rows),'api_attempts':len(calls),'api_failures':sum(x['status']=='failed' for x in calls),'usage':{k:sum((x.get('usage') or {}).get(k,0) for x in calls) for k in ['prompt_tokens','completion_tokens','total_tokens']},'models':sorted({x['resolved_model'] for x in calls if x.get('resolved_model')})};dump(OUT/'progress.json',s);print(canon(s),flush=True)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--phase',choices=['run','summary'],default='run');ap.add_argument('--ids',nargs='*');args=ap.parse_args();runner=Runner()
 if args.phase=='summary':runner.summary();return
 qids=[q if q.startswith('videomme:') else 'videomme:'+q for q in args.ids] if args.ids else list(runner.rows)
 dump(OUT/'batches'/f'{time.time_ns()}.json',{'qids':qids,'implementation':runner.impl,'started_unix':time.time()})
 with concurrent.futures.ThreadPoolExecutor(max_workers=runner.cfg['api']['concurrency']) as pool:
  futures={pool.submit(runner.process,q):q for q in qids}
  for future in concurrent.futures.as_completed(futures):
   r=future.result();print(canon({'qid':r['qid'],'status':r['status'],'groups':len(r.get('groups',[])),'needed':r.get('subset_validation',{}).get('irreducible_group_count'),'error':r.get('error')}),flush=True)
 runner.summary()
if __name__=='__main__':main()
