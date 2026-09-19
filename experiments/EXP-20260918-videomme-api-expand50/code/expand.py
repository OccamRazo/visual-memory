#!/usr/bin/env python3
"""Frozen initial50, then bounded reserve batches until cumulative multi-source target."""
import argparse,collections,concurrent.futures,fcntl,json,random,signal,threading,time
from pathlib import Path
import engine as e
from repair import Repair,BANK
REPO=e.REPO;OUT=e.OUT
FIRST=e.BASE/'EXP-20260917-videomme-api-source50/run-001'
REPAIR=e.BASE/'EXP-20260918-videomme-api-repair32/run-001'

def baseline():
 rows=[]
 for item in e.read(FIRST/'manifest.json')['entries']:
  path=REPAIR/'results'/f"{e.safe(item['qid'])}.json"
  if not path.exists():path=FIRST/'results'/f"{e.safe(item['qid'])}.json"
  r=e.read(path)
  if r['status']!='source_supported_multi':continue
  packet=r.get('final_source_packet_file',r.get('source_packet_file'))
  packet_hash=r.get('final_source_packet_sha256',r.get('source_packet_sha256'))
  # v1 stored canonical-JSON digest; v2 stored literal file-byte digest.
  algorithm='file_bytes' if r.get('final_source_packet_file') else 'canonical_json'
  assert packet and (e.sha(packet) if algorithm=='file_bytes' else e.digest(e.read(packet)))==packet_hash
  rows.append({'qid':r['qid'],'video_id':r['video_id'],'result_file':str(path),'result_sha256':e.sha(path),'source_packet_file':packet,'source_packet_sha256':e.sha(packet),'original_packet_digest':packet_hash,'original_packet_digest_algorithm':algorithm,'status':r['status'],'historical_carry_over':True})
 assert len(rows)==32 and len({r['qid'] for r in rows})==32
 return rows

def prepare():
 if (OUT/'manifest.json').exists():raise FileExistsError('Frozen manifest exists; do not overwrite.')
 cfg=e.read(REPO/'protocol.json');first=e.read(FIRST/'manifest.json');excluded={i['video_id'] for i in first['entries']};bins=collections.defaultdict(list)
 for candidate in e.read(e.POOL):
  path=e.PREV/'packets'/f"{e.safe(candidate['qid'])}.json";p=e.read(path)
  assert e.sha(path)==candidate['source_packet_sha256']
  if p['video_id'] in excluded:continue
  lookup={c['id']:c for c in p['captions']}
  groups=[{'id':g['id'],'windows':e.merge([(lookup[c]['start_s'],lookup[c]['end_s']) for c in g['caption_ids']]),'caption_ids':g['caption_ids']} for g in candidate['groups']]
  q={k:p[k] for k in ['qid','video_id','question','options','reference_answer']}
  q.update(groups=groups,caption_packet_file=str(path),caption_packet_sha256=e.sha(path),old_status='caption_candidate',repair_hint='Find original source windows covering every requested fact and relation. Check identity, ordinal/order and comparison scope. Caption-based grouping is a proposal, not proof.')
  v=e.DATA/'data'/f"{q['video_id']}.mp4";assert v.exists();q.update(video_path=str(v),video_size_bytes=v.stat().st_size,video_mtime_ns=v.stat().st_mtime_ns)
  bins[min(4,len(groups))].append(q)
 rng=random.Random(cfg['selection']['seed'])
 for k in sorted(bins):bins[k].sort(key=lambda q:q['qid']);rng.shuffle(bins[k])
 ordered=[];seen=set()
 while any(bins.values()):
  for k in sorted(bins):
   while bins[k]:
    q=bins[k].pop()
    if q['video_id'] in seen:continue
    seen.add(q['video_id']);ordered.append(q);break
 assert len(ordered)>=cfg['selection']['initial_questions']
 entries=[]
 for rank,q in enumerate(ordered):
  path=OUT/'inputs'/f"{e.safe(q['qid'])}.json";e.dump(path,q)
  entries.append({'qid':q['qid'],'video_id':q['video_id'],'input_file':str(path),'input_sha256':e.sha(path),'rank':rank,'phase':'initial50' if rank<50 else 'reserve','caption_groups':len(q['groups'])})
 m={'created_at':e.now(),'questions':len(entries),'initial_questions':50,'pool_sha256':e.sha(e.POOL),'caption_bank_sha256':e.sha(BANK),'protocol_sha256':e.sha(REPO/'protocol.json'),'prior50_manifest_sha256':e.sha(FIRST/'manifest.json'),'excluded_video_ids':sorted(excluded),'selection':cfg['selection'],'entries':entries}
 base={'created_at':e.now(),'multi_count':32,'entries':baseline(),'note':'Historical source-supported results, not new verifications. 13 original +19 repaired.'}
 for name,data in [('manifest.json',m),('baseline32.json',base)]:e.dump(OUT/name,data);e.dump(REPO/name,data)
 e.dump(OUT/'queue.json',{'admitted_qids':[q['qid'] for q in entries[:50]],'batches':[{'admitted_at':e.now(),'kind':'initial50','qids':[q['qid'] for q in entries[:50]]}]})
 print(json.dumps({'initial':50,'reserve':len(entries)-50,'baseline_multi':32,'target':51}))

def target_counts(baseline_rows,rows):
 base={r['qid'] for r in baseline_rows};added={r['qid'] for r in rows if r['status']=='source_supported_multi'}
 assert not base.intersection(added),'New results must not repeat historical questions'
 return {'baseline_multi':len(base),'new_multi':len(added),'cumulative_multi':len(base|added)}

class Expansion(Repair):
 def __init__(self):
  super().__init__();self.baseline=e.read(OUT/'baseline32.json')['entries'];self.queue=e.read(OUT/'queue.json')
  for r in self.baseline:assert e.sha(r['result_file'])==r['result_sha256']
 def results(self):return [e.read(p) for p in sorted((OUT/'results').glob('*.json'))]
 def progress(self,state):
  rows=self.results();counts=target_counts(self.baseline,rows);calls=[e.read(p) for p in (OUT/'calls').glob('*/*/*/attempt-*.json')]
  s={'updated_at':e.now(),'pid':e.os.getpid(),'state':state,'selected':len(self.queue['admitted_qids']),'initial_questions':50,'terminal_results':len(rows),'remaining':len(self.queue['admitted_qids'])-len(rows),'reserve_unadmitted':self.m['questions']-len(self.queue['admitted_qids']),'status_counts':dict(collections.Counter(r['status'] for r in rows)),'active':dict(self.active),'implementation':self.impl,**counts,'target_multi':51,'target_met':counts['cumulative_multi']>=51,'api_attempts':len(calls),'api_failed_attempts':sum(c['status']!='ok' for c in calls),'usage':{k:sum((c.get('usage') or {}).get(k,0) for c in calls) for k in ['prompt_tokens','completion_tokens','total_tokens']},'calls_without_returned_usage':sum(c.get('usage') is None for c in calls),'human_reviewed':False}
  e.dump(OUT/'status.json',s)
 def export(self):
  rows=self.results();e.dump(OUT/'all_results.json',rows);e.dump(OUT/'supported_multi.json',[r for r in rows if r['status']=='source_supported_multi']);e.dump(OUT/'summary.json',e.read(OUT/'status.json'))
  combined=list(self.baseline)
  for r in rows:
   if r['status']=='source_supported_multi':
    path=OUT/'results'/f"{e.safe(r['qid'])}.json"
    combined.append({'qid':r['qid'],'video_id':r['video_id'],'result_file':str(path),'result_sha256':e.sha(path),'source_packet_file':r['final_source_packet_file'],'source_packet_sha256':r['final_source_packet_sha256'],'status':r['status'],'historical_carry_over':False})
  e.dump(OUT/'cumulative_supported_multi.json',{'updated_at':e.now(),**target_counts(self.baseline,rows),'entries':combined,'human_reviewed':False})
 def run(self):
  if (OUT/'STOP').exists() or (OUT/'circuit_breaker.json').exists():raise RuntimeError('STOP/circuit breaker present; inspect before restart')
  for r in self.results():
   if r['status']=='interrupted':
    p=OUT/'results'/f"{e.safe(r['qid'])}.json";e.dump(OUT/'result_history'/e.safe(r['qid'])/f'{time.time_ns()}.json',r);p.unlink()
  end=threading.Event()
  def heartbeat():
   while not end.wait(20):
    with self.lock:self.progress('stopping' if self.stop.is_set() else 'running')
  t=threading.Thread(target=heartbeat,daemon=True);t.start()
  for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,lambda *_:self.stop.set())
  state='running';self.progress(state)
  try:
   while True:
    admitted=set(self.queue['admitted_qids']);done={r['qid'] for r in self.results()};todo=[r for r in self.m['entries'] if r['qid'] in admitted and r['qid'] not in done]
    with concurrent.futures.ThreadPoolExecutor(max_workers=self.cfg['api']['concurrency']) as pool:list(pool.map(self.one,todo))
    if self.stop.is_set() or (OUT/'STOP').exists():state='paused';break
    rows=self.results();done={r['qid'] for r in rows};assert admitted<=done
    if target_counts(self.baseline,rows)['cumulative_multi']>=51:state='completed';break
    reserves=[r for r in self.m['entries'] if r['qid'] not in admitted][:self.cfg['selection']['reserve_batch_size']]
    if not reserves:state='pool_exhausted_below_target';break
    batch={'admitted_at':e.now(),'kind':'target_supplement','qids':[r['qid'] for r in reserves]}
    with self.lock:
     self.queue['admitted_qids'].extend(batch['qids']);self.queue['batches'].append(batch);e.dump(OUT/'queue.json',self.queue);self.progress('running')
    self.export()
  except BaseException:
   state='crashed';raise
  finally:
   end.set();t.join();self.progress(state);self.export()

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','run','status']);a=ap.parse_args()
 if a.action=='prepare':prepare()
 elif a.action=='status':print(json.dumps(e.read(OUT/'status.json'),ensure_ascii=False,indent=2))
 else:
  with (OUT/'runner.lock').open('a') as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);Expansion().run()
