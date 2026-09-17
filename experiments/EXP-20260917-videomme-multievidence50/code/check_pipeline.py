#!/usr/bin/env python3
"""Focused checks for the experiment's consequential selection/isolation rules."""
from run import Pipeline

p=object.__new__(Pipeline)
p.captions={'v':[{'source_id':f'videomme:v:{i:05}','start_s':i*10,'end_s':i*10+10,'text':f'caption {i}'} for i in range(123)]}
p.durations={'v':1230};p.subs={'v':[]}
q={'video_id':'v','original_question':'q','original_options':{},'reference_draft':'a'}
h=p.full_timeline(q)
assert h['caption_count']==123 and len(h['all_captions'])==123
assert [x[0] for x in h['all_captions']]==[f'C{i:05}' for i in range(123)]

r={'qid':'test','question':'q','required_facts':[{'id':'F1','fact':'answer'}]}
package={'groups':[
 {'id':'G01','start_s':10,'end_s':20,'review_start_s':7,'review_end_s':23,'frame_ids':['V1'],'label_zh':'excluded hypothesis 1'},
 {'id':'G02','start_s':40,'end_s':50,'review_start_s':37,'review_end_s':53,'frame_ids':['V2'],'label_zh':'excluded hypothesis 2'}],
 'frames':[{'frame_id':'V1','actual_pts_s':15},{'frame_id':'V2','actual_pts_s':45},{'frame_id':'R1','actual_pts_s':21}],
 'subtitles':[{'subtitle_id':'S1','start_s':11,'end_s':19,'text':'retained'},{'subtitle_id':'S2','start_s':41,'end_s':49,'text':'omitted'},{'subtitle_id':'S3','start_s':19,'end_s':21,'text':'boundary context'}]}
h,fs=p.group_content(r,package,ids=['G01'])
assert [f['frame_id'] for f in fs]==['V1']
assert [s['subtitle_id'] for s in h['intervals'][0]['subtitles']]==['S1']
assert 'omitted' not in str(h) and 'hypothesis' not in str(h) and 'boundary context' not in str(h)

# The singleton alternative must not be missed by a greedy two-group solution.
p.check_subset=lambda r,pkg,ids: ({'all_facts_supported':('G03' in ids or set(ids)>={'G01','G02'}),'scope_adequate':True,'facts':[{'status':'supported'}]},'mock')
assert p.ablate(r,{'groups':[{'id':x} for x in ['G01','G02','G03']]},{})['status']=='single_group_sufficient'
p.check_subset=lambda r,pkg,ids: ({'all_facts_supported':set(ids)>={'G01','G02'},'scope_adequate':True,'facts':[{'status':'supported'}]},'mock')
result=p.ablate(r,{'groups':[{'id':x} for x in ['G01','G02','G03']]},{})
assert result['status']=='multi_group_verified' and result['selected_group_ids']==['G01','G02']
assert all(any(t['group_ids']==[gid] and not t['supported'] for t in result['tests']) for gid in ['G01','G02','G03'])
print('PASS: all 123 captions retained; core-only source and label isolation; singleton alternative detection; redundant group removal; retained deletion tests.')

raw={'groups':[{'id':'A','start_s':10,'end_s':20,'frame_ids':['V1'],'subtitle_ids':[]},{'id':'B','start_s':20,'end_s':30,'frame_ids':['V2'],'subtitle_ids':[]}]}
bank={'duration_s':100,'frames':[{'frame_id':'V1','actual_pts_s':15},{'frame_id':'V2','actual_pts_s':25}],'subtitles':[]}
gs,log=p.normalize(raw,bank)
assert len(gs)==2 and gs[0]['end_s']==gs[1]['start_s']
print('PASS: adjacent independently proposed cores are retained for semantic audit, not automatically merged.')
