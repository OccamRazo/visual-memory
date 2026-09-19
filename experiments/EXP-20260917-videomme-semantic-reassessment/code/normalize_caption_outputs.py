#!/usr/bin/env python3
"""Recover only unambiguous formatting variants, preserving failed raw outputs."""
import json,re
from caption_review import OUT,REPO,read,dump,safe,sha

def main():
 recovered=[]
 for e in read(OUT/'manifest.json')['entries']:
  target=OUT/'decisions'/f"{safe(e['qid'])}.json"
  if target.exists() or not e['caption_count']:continue
  calls=sorted((OUT/'calls'/safe(e['qid'])).glob('attempt-*.json'))
  if not calls:continue
  call=calls[-1];r=read(call)
  if r['status']!='failed' or r.get('finish_reason')!='stop':continue
  try:
   d=json.loads(r['raw_text']);changes=[];p=read(e['packet_file']);lookup={c['id']:c for c in p['captions']}
   if d.get('coverage')=='insufficient':d['coverage']='unclear';changes.append('unsupported enum insufficient -> unclear; original insufficiency reason preserved')
   assert d['qid']==e['qid'] and d['grouping'] in {'multi','single','unclear'} and d['requires_multiple'] in {'yes','no','unclear'} and d['coverage'] in {'sufficient','partial','unclear'} and d['reference_consistency'] in {'consistent','conflict','unclear'}
   gs=d['groups'];assert (d['grouping']!='multi' or len(gs)>=2) and (d['grouping']!='single' or len(gs)==1);assert not(d['requires_multiple']=='yes' and d['grouping']!='multi');assert len({g['id'] for g in gs})==len(gs)
   for g in gs:
    assert g['caption_ids']
    for i,cid in enumerate(g['caption_ids']):
     if cid not in lookup:
      assert re.fullmatch(r'C[0-9]+',cid);replacement=f'C{int(cid[1:]):05}'
      assert replacement in lookup;g['caption_ids'][i]=replacement;changes.append(f'{cid} -> {replacement}; zero-padding only')
    refs=[lookup[c] for c in g['caption_ids']];g['start_s']=min(c['start_s'] for c in refs);g['end_s']=max(c['end_s'] for c in refs);g['caption_spans']=[{k:c[k] for k in ['id','start_s','end_s']} for c in refs]
   assert changes
   d.update(review_kind='selected_caption_semantic_review',source_packet_sha256=e['packet_sha256'],call_file=str(call),new_visual_verification=False,human_reviewed=False,boundary_precision='caption_span_envelope; may contain gaps; see caption_spans',output_normalizations=changes,normalizer_sha256=sha(__file__))
   dump(target,d);recovered.append({'qid':e['qid'],'call_file':str(call),'normalizations':changes})
  except (AssertionError,KeyError,ValueError,TypeError):continue
 existing=read(REPO/'caption_output_normalizations.json') if (REPO/'caption_output_normalizations.json').exists() else []
 dump(REPO/'caption_output_normalizations.json',existing+recovered);print(json.dumps(recovered,ensure_ascii=False))
if __name__=='__main__':main()
