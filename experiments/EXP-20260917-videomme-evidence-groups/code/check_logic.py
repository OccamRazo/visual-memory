"""Critical invariants: temporal normalization and exclusion isolation (no API)."""
from group import Runner

def main():
 r=Runner.__new__(Runner)
 bank={'duration_s':100,'frames':[{'frame_id':'V1','actual_pts_s':10.123}],
       'subtitles':[{'subtitle_id':'S1','start_s':12,'end_s':15},{'subtitle_id':'S2','start_s':30,'end_s':34}]}
 def group(name,a,b,frames,subs):return {'id':name,'start_s':a,'end_s':b,'frame_ids':frames,'subtitle_ids':subs,'fact_ids':['F1'],'label_zh':name,'episode_reason_zh':'same event','source_summary_zh':'source','boundary_uncertainty_zh':''}
 g,log=r.normalize({'groups':[group('a',11,14,['V1'],['S1']),group('b',15,18,[],['S1'])]},bank)
 assert len(g)==1 and g[0]['start_s']==10.123 and g[0]['end_s']==18
 g,_=r.normalize({'groups':[group('a',10,18,['V1'],['S1']),group('b',30,34,[],['S2'])]},bank)
 assert len(g)==2 and g[0]['end_s']<g[1]['start_s']
 frames=[{'frame_id':'V1','actual_pts_s':11,'path':'unused'}, {'frame_id':'R1','actual_pts_s':19,'path':'unused'}, {'frame_id':'V2','actual_pts_s':32,'path':'unused'}]
 subs=[{'subtitle_id':'S1','start_s':12,'end_s':15,'text':'retained'}, {'subtitle_id':'S_boundary','start_s':17,'end_s':21,'text':'crosses boundary'}, {'subtitle_id':'S2','start_s':30,'end_s':34,'text':'EXCLUDED CONTENT'}]
 p={'groups':g,'frames':frames,'subtitles':subs};row={'question':'frozen question','required_facts':[{'id':'F1','statement':'target'}]}
 h,fs=r.group_content(row,p,ids=['G01'])
 assert [x['frame_id'] for x in fs]==['V1']
 assert [s['subtitle_id'] for s in h['intervals'][0]['subtitles']]==['S1']
 assert 'EXCLUDED' not in str(h) and 'G02' not in str(h)
 assert 'source_summary_zh' not in str(h) and 'fact_ids' not in str(h)
 assert all(x not in h for x in ['reference_answer','previous_answer','excluded_groups'])
 ha,fa=r.group_content(row,p,ids=['G01'],audit=True)
 assert any(s['subtitle_id']=='S_boundary' for s in ha['intervals'][0]['subtitles'])
 assert any(f['frame_id']=='R1' for f in fa)
 print('PASS: enclosure, overlap merge, separated groups, boundary-context isolation, excluded-source and proposal-label isolation.')
if __name__=='__main__':main()
