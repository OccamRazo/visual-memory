#!/usr/bin/env python3
"""Read compact source-linked cases; record explicit final AI review decisions."""
import argparse
from run import OUT, read, dump, safe, sha, now
ap=argparse.ArgumentParser();ap.add_argument('action',choices=['show','record','status']);ap.add_argument('--ids',nargs='*');ap.add_argument('--decision',choices=['confirmed','qualified']);ap.add_argument('--reason');a=ap.parse_args()
files=list((OUT/'results').glob('*.json'))
if a.ids:files=[OUT/'results'/f"{safe(q if q.startswith('videomme:') else 'videomme:'+q)}.json" for q in a.ids]
for path in sorted(files):
 r=read(path)
 if a.action=='status':
  if r['status']=='multi_verified_candidate':print(r['qid'],(read(OUT/'reviews'/path.name)['decision'] if (OUT/'reviews'/path.name).exists() else 'pending'))
 elif a.action=='record':
  assert a.ids and a.decision and a.reason
  if a.decision=='confirmed':assert r['status']=='multi_verified_candidate'
  dest=OUT/'reviews'/path.name
  assert not dest.exists(),'Review immutable; preserve a superseded review explicitly before correction.'
  dump(dest,{'qid':r['qid'],'decision':a.decision,'reason_zh':a.reason,'reviewer':'Codex source review','reviewed_at':now(),'human_reviewed':False,'result_file':str(path),'result_sha256':sha(path)})
 else:
  print('\nQUESTION',r['qid'],r['question_original'],'\nANSWER',r['official_answer'],'\nSTATUS',r['status'])
  print('FACTS',r.get('required_facts'));print('GROUPS',[(g['id'],g['start_s'],g['end_s'],g.get('label_zh'),g.get('episode_reason_zh')) for g in r.get('groups',[])])
  print('AUDIT',r.get('audit'));print('OBSERVER',r.get('observer'));print('COUNTERSEARCH',r.get('countersearch'))
  print('TESTS',[(t['group_ids'],t['supported'],t['result'].get('missing_zh')) for t in r.get('subset_validation',{}).get('tests',[])])
  if r.get('package_file'):
   p=read(r['package_file']);subs={s['subtitle_id']:s for s in p['subtitles']};frames={f['frame_id']:f for f in p['frames']}
   for f in r.get('audit',{}).get('fact_support',[]):
    print('SOURCE',f.get('fact_id'),[subs.get(s) for s in f.get('subtitle_ids',[])],[frames.get(s) for s in f.get('frame_ids',[])])
  print('SHEETS',r.get('sheets'))
