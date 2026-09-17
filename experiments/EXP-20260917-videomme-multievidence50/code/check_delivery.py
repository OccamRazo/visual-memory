#!/usr/bin/env python3
"""Check exported source-only packages, local preview references and final quota."""
import argparse,collections,html.parser
from pathlib import Path
from urllib.parse import unquote,urlsplit
from run import OUT,read,rows,sha

ap=argparse.ArgumentParser();ap.add_argument('--min-count',type=int,default=50);args=ap.parse_args()
base=OUT/'final';questions=rows(base/'multievidence.jsonl');groups=rows(base/'groups.jsonl')
assert len({q['qid'] for q in questions})==len(questions)>=args.min_count
assert len(groups)==sum(len(q['groups']) for q in questions)
assert read(base/'summary.json')['dataset_sha256']==sha(base/'multievidence.jsonl')
for q in questions:
 assert len(q['groups'])>=2 and {g['group_id'] for g in q['groups']}==set(q['necessary_group_ids'])
 assert q['original_options'] and q['official_answer'] and q['required_facts']
 assert q['model']=='qwen3.8-flash' and q['human_reviewed'] is False
 assert sha(q['result_file'])==q['result_sha256']
 assert read(q['review_file'])['result_sha256']==q['result_sha256']
 prev=-1
 for g in q['groups']:
  assert prev<=g['start_s']<g['end_s'];prev=g['end_s']
  assert sha(g['package_file'])==g['package_sha256']
  p=read(g['package_file']);assert Path(p['source_video']).is_file()
  assert p['generated_captions_in_evidence'] is False
  assert not set(p)&{'question','official_answer','reference_answer','required_facts','task_labels','captions','label_zh'}
  assert p['frames'] or p['subtitles']
  for f in p['frames']:
   assert p['start_s']<=f['actual_pts_s']
   assert f['actual_pts_s']<p['end_s'] if p['interval_semantics'].startswith('half-open') else f['actual_pts_s']<=p['end_s']
   assert sha(f['path'])==f['sha256']
  for s in p['subtitles']:assert p['start_s']-.001<=s['start_s']<s['end_s']<=p['end_s']+.001

class References(html.parser.HTMLParser):
 def __init__(self):super().__init__();self.refs=[]
 def handle_starttag(self,tag,attrs):
  for k,v in attrs:
   if k in ['src','href']:self.refs.append(v)
parser=References();parser.feed((base/'index.html').read_text())
for ref in parser.refs:
 uri=urlsplit(ref);assert not uri.scheme and not uri.netloc
 assert (base/unquote(uri.path)).resolve().is_file(),ref
print(f'PASS: {len(questions)} questions, {len(groups)} source-only groups; source hashes, interval isolation, review binding and {len(parser.refs)} local preview links. Browser playback not tested.')
