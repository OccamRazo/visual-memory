"""Offline safeguards against stale/wrong citations and invented timestamp bounds."""
import copy,unittest
from run import Runner,merge
class Contracts(unittest.TestCase):
 def setUp(self):
  self.runner=Runner.__new__(Runner);self.runner.cfg={'source':{'max_evidence_interval_s':120}}
  self.packet={'duration_s':100,'windows':[{'id':'G01','windows':[[10,20]]}],'frames':[{'id':'R0000','time_s':12.03,'group_ids':['G01']}],'subtitles':[{'id':'S00001','start_s':12,'end_s':14,'group_ids':['G01']}]}
  self.obs={'answer':'a','coverage':'complete','facts':[{'id':'F01','statement':'visible fact','status':'supported','evidence':[{'group_id':'G01','start_s':12,'end_s':14,'frame_ids':['R0000'],'subtitle_ids':['S00001'],'modality':'mixed','boundary_uncertainty_zh':'sampled witness'}]}],'relations':[],'missing_zh':[],'groups_unresolved':[]}
 def test_valid_actual_source(self):self.runner.check_observation(self.obs,self.packet)
 def test_nonexistent_frame_rejected(self):
  self.obs['facts'][0]['evidence'][0]['frame_ids']=['C0000']
  with self.assertRaises(AssertionError):self.runner.check_observation(self.obs,self.packet)
 def test_time_hit_without_citations_rejected(self):
  e=self.obs['facts'][0]['evidence'][0];e['frame_ids']=[];e['subtitle_ids']=[]
  with self.assertRaises(AssertionError):self.runner.check_observation(self.obs,self.packet)
 def test_range_must_contain_subtitle(self):
  self.obs['facts'][0]['evidence'][0]['end_s']=13
  with self.assertRaises(AssertionError):self.runner.check_observation(self.obs,self.packet)
 def test_wrong_group_rejected(self):
  self.obs['facts'][0]['evidence'][0]['group_id']='G02'
  with self.assertRaises(AssertionError):self.runner.check_observation(self.obs,self.packet)
 def test_disjoint_caption_spans_not_enveloped(self):self.assertEqual(merge([[10,20],[30,40],[18,21]]),[[10.,21],[30.,40.]])
 def test_relation_must_reference_real_fact(self):
  self.obs['relations']=[{'fact_ids':['F99'],'status':'supported'}]
  with self.assertRaises(AssertionError):self.runner.check_observation(self.obs,self.packet)
 def test_positive_audit_requires_source_citation(self):
  d={'question_supported':True,'reference_matches':True,'relations_supported':True,'requires_multiple':'no','missing_zh':[],'reference_issues_zh':[],'semantic_groups':[],'fact_checks':[{'fact_id':'F01','supported':True,'frame_ids':[],'subtitle_ids':[]}]}
  with self.assertRaises(AssertionError):self.runner.check_audit(d,self.packet,self.obs)
 def test_audit_cannot_move_fact_to_another_time(self):
  self.packet['frames'].append({'id':'R0001','time_s':18,'group_ids':['G01']})
  d={'question_supported':True,'reference_matches':True,'relations_supported':True,'requires_multiple':'no','missing_zh':[],'reference_issues_zh':[],'semantic_groups':[],'fact_checks':[{'fact_id':'F01','supported':True,'frame_ids':['R0001'],'subtitle_ids':[]}]}
  with self.assertRaises(AssertionError):self.runner.check_audit(d,self.packet,self.obs)
if __name__=='__main__':unittest.main()
