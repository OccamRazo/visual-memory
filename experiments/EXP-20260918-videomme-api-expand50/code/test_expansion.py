import unittest
from expand import target_counts
class Counts(unittest.TestCase):
 def test_only_complete_multi_counts(self):
  baseline=[{'qid':f'old{i}'} for i in range(32)]
  rows=[{'qid':f'new{i}','status':'source_supported_multi'} for i in range(19)]+[{'qid':'single','status':'source_supported_single_or_redundant'},{'qid':'invalid','status':'output_invalid'}]
  self.assertEqual(target_counts(baseline,rows)['cumulative_multi'],51)
 def test_deduplicate_ids(self):
  r={'qid':'a','status':'source_supported_multi'};self.assertEqual(target_counts([], [r,r])['new_multi'],1)
 def test_old_question_cannot_count_twice(self):
  with self.assertRaises(AssertionError):target_counts([{'qid':'a'}],[{'qid':'a','status':'source_supported_multi'}])
if __name__=='__main__':unittest.main()
