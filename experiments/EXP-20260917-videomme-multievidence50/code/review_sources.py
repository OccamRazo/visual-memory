#!/usr/bin/env python3
"""Compact original-source review, with sheets of the ACTUAL cited support frames."""
import argparse,math
from PIL import Image,ImageDraw
from run import OUT,read,dump,safe,sha
ap=argparse.ArgumentParser();ap.add_argument('--ids',nargs='*');a=ap.parse_args()
files=sorted((OUT/'results').glob('*.json'))
if a.ids:files=[OUT/'results'/f"{safe(q if q.startswith('videomme:') else 'videomme:'+q)}.json" for q in a.ids]
for file in files:
 r=read(file)
 if not a.ids and (r['status']!='multi_verified_candidate' or (OUT/'reviews'/file.name).exists()):continue
 print('\n===',r['qid'],r['status'],'===\nQ:',r['question_original'],'\nA:',r['official_answer'],'\nFACTS:',r.get('required_facts'))
 if not r.get('package_file'):continue
 p=read(r['package_file']);fs={f['frame_id']:f for f in p['frames']};ss={s['subtitle_id']:s for s in p['subtitles']}
 chosen=r.get('subset_validation',{}).get('selected_group_ids',[])
 print('GROUPS:',[(g['id'],g['start_s'],g['end_s'],g['label_zh'],g.get('episode_reason_zh')) for g in r['groups']]);print('RETAINED:',chosen)
 print('BLIND:',r.get('observer',{}).get('answer'));print('COUNTERSEARCH:',r.get('countersearch'))
 source_rows=list(r.get('audit',{}).get('fact_support',[]))
 for t in r.get('subset_validation',{}).get('tests',[]):
  if t['group_ids']==chosen:source_rows+=t['result'].get('facts',[])
  print('TEST',t['group_ids'],t['supported'],t['result'].get('missing_zh'),[x.get('reason_zh') for x in t['result'].get('facts',[])])
 fids=[];sids=[]
 for x in source_rows:
  for fid in x.get('frame_ids',[]):
   if fid not in fids:fids.append(fid)
  for sid in x.get('subtitle_ids',[]):
   if sid not in sids:sids.append(sid)
 for sid in sorted(sids):print('SUBTITLE',ss.get(sid))
 ordered=sorted([fs[x] for x in fids],key=lambda f:f['actual_pts_s']);out=[]
 for page in range(math.ceil(len(ordered)/16)):
  batch=ordered[page*16:(page+1)*16];im=Image.new('RGB',(1600,252*math.ceil(len(batch)/4)),'white');d=ImageDraw.Draw(im)
  for i,f in enumerate(batch):
   tile=Image.open(f['path']);tile.thumbnail((400,225));x,y=i%4*400,i//4*252;im.paste(tile,(x,y));d.text((x+3,y+227),f"{f['frame_id']} {f['actual_pts_s']:.3f}s",fill='black')
  dest=OUT/'review_source_sheets'/safe(r['qid'])/sha(file)[:16]/f'page-{page+1:02}.jpg';dest.parent.mkdir(parents=True,exist_ok=True);im.save(dest,quality=95);out.append({'path':str(dest),'sha256':sha(dest),'frame_ids':[f['frame_id'] for f in batch]})
 dump(OUT/'review_source_sheets'/safe(r['qid'])/(sha(file)[:16]+'.json'),out)
 print('CITED_SOURCE_SHEETS:',out)
