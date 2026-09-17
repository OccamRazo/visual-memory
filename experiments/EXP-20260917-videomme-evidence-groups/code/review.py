"""Inspect and record current-session review separately from API decisions."""
import argparse,datetime,json
from pathlib import Path
from group import OUT,read,dump,safe,sha,ts

def main():
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['status','show','record']);ap.add_argument('qids',nargs='*');ap.add_argument('--note');ap.add_argument('--decision',choices=['confirmed','qualified']);ap.add_argument('--inspection',choices=['subtitles','frames','mixed','audit_and_source_indices'],default='mixed');args=ap.parse_args()
 rows={r['qid']:r for r in (read(p) for p in (OUT/'results').glob('*.json'))}
 if args.action=='status':
  reviews={r['qid']:r for r in (read(p) for p in (OUT/'reviews').glob('*.json'))}
  print(json.dumps({'processed':len(rows),'reviewed':len(reviews),'pending':[q for q in rows if q not in reviews],'flagged':[{ 'qid':q,'status':r['status'],'error':r.get('error')} for q,r in rows.items() if r['status']!='review_candidate']},ensure_ascii=False));return
 for q in args.qids:
  if not q.startswith('videomme:'):q='videomme:'+q
  r=rows[q]
  if args.action=='record':
   if not args.note or not args.decision:raise ValueError('Decision and specific source review note required')
   p=OUT/'reviews'/f'{safe(q)}.json'
   if p.exists():raise ValueError('Existing review preserved; archive explicitly before a correction')
   if args.decision=='confirmed':assert r['status']=='review_candidate'
   dump(p,{'qid':q,'decision':args.decision,'note_zh':args.note,'inspection':args.inspection,'reviewer':'Codex active session; reference visible','human_reviewed':False,'reviewed_at':datetime.datetime.now().astimezone().isoformat(),'result_file':str(OUT/'results'/f'{safe(q)}.json'),'result_sha256':sha(OUT/'results'/f'{safe(q)}.json')});print(q,args.decision);continue
  print('\n'+q+' '+r['status']+' '+r['question']);print('FACTS',r['required_facts']);print('ERROR',r.get('error'));print('ISSUES',r.get('audit',{}).get('issues'));print('BOUNDARY_LIMITS',r.get('audit',{}).get('boundary_limitations_zh'))
  p=read(r['package_file']) if r.get('package_file') else {};subs={s['subtitle_id']:s for s in p.get('subtitles',[])}
  for g in r.get('groups',[]):
   print(g['id'],ts(g['start_s']),ts(g['end_s']),g['label_zh'],g.get('role'),g.get('fact_ids'));print(' continuity:',g.get('episode_reason_zh'));print(' uncertainty:',g.get('boundary_uncertainty_zh'));print(' frames:',g.get('frame_ids'))
   for sid in g['subtitle_ids']:
    s=subs[sid];print(' ',sid,ts(s['start_s']),ts(s['end_s']),s['text'])
  print('FACT_SUPPORT',r.get('audit',{}).get('fact_support'))
  a=r.get('subset_validation',{});print('SUBSET',a.get('status'),a.get('selected_group_ids'))
  for t in a.get('tests',[]):print(' TEST',t['group_ids'],t['supported'],[(f['fact_id'],f['status'],f['reason_zh']) for f in t['result']['facts']])
  print('SHEETS',[x['path'] for x in r.get('sheets',[])])
if __name__=='__main__':main()
