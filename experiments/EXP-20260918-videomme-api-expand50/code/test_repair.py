"""Regression contracts for the concrete failures diagnosed in the prior32 cases."""
import copy,unittest
from repair import Repair
class Contract(unittest.TestCase):
 def setUp(self):
  self.r=Repair.__new__(Repair);self.r.cfg={'repair':{'max_planned_windows':16,'max_planned_total_seconds':600}}
  self.p={'frames':[{'id':'C0000','time_s':12.03,'sha256':'a'},{'id':'R0000','time_s':50.1,'sha256':'b'}],'subtitles':[{'id':'S00001','start_s':12,'end_s':14,'text':'fact'}],'windows':[],'nominal_spacing_s':1,'duration_s':100}
  self.d={'answer':'A','coverage':'complete','question_supported':True,'requires_multiple':'no','facts':[{'id':'F01','statement':'static fact','status':'supported','source_ids':['C0000']}],'semantic_groups':[{'id':'E01','label_zh':'event','fact_ids':['F01'],'source_ids':['C0000']}],'relations':[],'missing_required':[],'notes':[],'reference_status':'matches','reference_reason_zh':'supported'}
 def test_point_witness_accepted_and_bound_to_pts(self):
  self.r.check(self.d,self.p,True);out=self.r.bound_result({'video_id':'v'},self.p,self.d);self.assertEqual(out[0]['source_spans'][0]['start_s'],12.03);self.assertEqual(out[0]['source_spans'][0]['end_s'],12.03)
 def test_bare_plan_array_has_actionable_schema_error(self):
  with self.assertRaisesRegex(AssertionError,'root must be object'):self.r.check_plan([],{'video_id':'v'})
 def test_disjoint_citations_do_not_fill_gap(self):
  self.d['facts'][0]['source_ids']=['C0000','R0000'];out=self.r.bound_result({'video_id':'v'},self.p,self.d);self.assertEqual(len(out[0]['source_spans']),2);self.assertEqual(out[0]['source_spans'][1]['start_s'],50.1)
 def test_complete_question_options_preserved(self):
  h=self.r.header({'qid':'x','video_id':'v','question':'Which option?','options':{'A':'one','B':'two'},'reference_answer':'one'},self.p);self.assertEqual(len(h['options']),2);self.assertNotIn('reference_answer',h)
 def test_old_frame_id_not_silently_renamed(self):
  self.d['facts'][0]['source_ids']=['C9999']
  with self.assertRaisesRegex(AssertionError,'unknown IDs'):self.r.check(self.d,self.p)
 def test_new_nearby_audit_source_rebinds_time(self):
  self.d['facts'][0]['source_ids']=['R0000'];self.d['semantic_groups'][0]['source_ids']=['R0000'];self.r.check(self.d,self.p,True);self.assertEqual(self.r.bound_result({'video_id':'v'},self.p,self.d)[0]['source_spans'][0]['start_s'],50.1)
 def test_positive_with_required_gap_rejected(self):
  self.d['missing_required']=['missing step']
  with self.assertRaisesRegex(AssertionError,'positive coverage'):self.r.check(self.d,self.p)
 def test_optional_note_does_not_block(self):
  self.d['notes']=['irrelevant detail not shown'];self.r.check(self.d,self.p,True);self.assertEqual(self.r.decision(self.d),'source_supported_single_or_redundant')
 def test_inconsistent_multi_group_rejected(self):
  self.d['requires_multiple']='yes'
  with self.assertRaisesRegex(AssertionError,'fewer than2'):self.r.check(self.d,self.p)
 def test_reference_conflict_not_promoted(self):
  self.d['reference_status']='conflict';self.assertEqual(self.r.decision(self.d),'reference_conflict')
 def test_group_sources_must_support_its_facts(self):
  self.d['semantic_groups'][0]['source_ids']=['R0000']
  with self.assertRaisesRegex(AssertionError,'must belong'):self.r.check(self.d,self.p)
if __name__=='__main__':unittest.main()
