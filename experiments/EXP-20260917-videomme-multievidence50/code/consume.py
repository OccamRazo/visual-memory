#!/usr/bin/env python3
"""Consume completed question-screening batches; preserve every actual draw wave."""
import concurrent.futures,os,time
from run import Pipeline,OUT,read,dump,safe,canon,now,priority_key

def main():
 p=Pipeline();pool=concurrent.futures.ThreadPoolExecutor(max_workers=32);active={};seeds={f'videomme:{x}' for x in ['626-3','715-1','782-2','872-1','888-1','723-3','791-3','641-3']}
 def eligible_count():
  count=0
  for f in (OUT/'results').glob('*.json'):
   if read(f)['status']!='multi_verified_candidate':continue
   review=OUT/'reviews'/f.name
   if not review.exists() or read(review)['decision']=='confirmed':count+=1
  return count
 try:
  while True:
   for future in list(active):
    if not future.done():continue
    q=active.pop(future);r=future.result();print(canon({'qid':q,'status':r['status'],'needed':r.get('subset_validation',{}).get('irreducible_group_count'),'error':r.get('error')}),flush=True)
    p.summary()
   enough=eligible_count()>=p.cfg['target'] or (OUT/'pause_queue').exists()
   if enough and not active:break
   rankings={}
   complete=(OUT/'ranking.json').exists()
   if complete:rankings={r['qid']:r for r in read(OUT/'ranking.json')}
   else:
    for f in sorted((OUT/'calls').glob('screen-*/screen/*/completed.json')):
     for r in read(f)['parsed'].get('questions',[]):rankings[r['qid']]=r
   order=sorted(rankings.values(),key=lambda r:priority_key(r,p.questions[r['qid']]))
   reserved=set(read(OUT/'draining_reserved_qids.json')) if (OUT/'draining_reserved_qids.json').exists() else set()
   workers=read(OUT/'worker_limit.json')['workers'] if (OUT/'worker_limit.json').exists() else p.cfg['api']['concurrency']
   assert 1<=workers<=32
   available=[r for r in order if r['priority']>=(0 if complete else 3) and r['qid'] not in seeds|reserved and r['qid'] not in active.values() and not (OUT/'results'/f"{safe(r['qid'])}.json").exists()]
   take=[]
   if not enough:
    for r in available[:max(0,min(workers-len(active),p.cfg['target']-eligible_count()-len(active)))]:
     q=r['qid'];take.append(r);active[pool.submit(p.process,q)]=q
   if take:dump(OUT/'batches'/f'queue-{time.time_ns()}.json',{'draw_rule':'Prioritize positive sequence/cross-episode comparison questions (model priority >=3), then other positive candidates, then exhaustive/negative candidates; model priority and qid break ties. All actual draw waves frozen.','workers':workers,'screening_complete':complete,'qids':[r['qid'] for r in take],'priorities':take,'implementation':p.impl,'started_at':now()})
   if complete and not available and not active:break
   time.sleep(5)
 finally:pool.shutdown(wait=True)
 print(canon(p.summary()),flush=True)
if __name__=='__main__':main()
