"""Offline delivery checks against exported files, local references and provenance."""
import collections,csv,datetime,json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote,urlsplit
from group import OUT,REPO,read,dump,sha,safe

def main():
 final=OUT/'final';rows=[json.loads(s) for s in (final/'evidence_groups60.jsonl').read_text().splitlines()]
 flat=[json.loads(s) for s in (final/'groups.jsonl').read_text().splitlines()];summary=read(final/'summary.json')
 assert len(rows)==60 and len({r['qid'] for r in rows})==60
 assert len(flat)==summary['candidate_groups']['total']==sum(len(r['groups']) for r in rows)
 assert len({(g['qid'],g['id']) for g in flat})==len(flat)
 assert sha(final/'evidence_groups60.jsonl')==summary['dataset_sha256']
 expected={(r['qid'],g['id']) for r in rows for g in r['groups']};assert expected=={(g['qid'],g['id']) for g in flat}
 for g in flat:
  p=read(g['group_package_file']);assert sha(g['group_package_file'])==g['group_package_sha256']
  assert (p['qid'],p['group_id'])==(g['qid'],g['id']) and (p['start_s'],p['end_s'])==(g['start_s'],g['end_s'])
  assert p['reference_answer_included'] is False and p['generated_captions_in_evidence'] is False
  assert not {'question','required_facts','reference_answer','source_summary_zh','label_zh'}&set(p)
  assert Path(p['source_video']).is_file()
 assert len(list((final/'group_packages').glob('*/*.json')))==len(flat)
 with (final/'groups.csv').open(encoding='utf-8-sig',newline='') as stream:assert len(list(csv.DictReader(stream)))==len(flat)
 class Links(HTMLParser):
  def __init__(self):super().__init__();self.links=[];self.sections=0
  def handle_starttag(self,tag,attrs):
   if tag=='section':self.sections+=1
   for key,val in attrs:
    if key in ('src','href'):self.links.append(val)
 parser=Links();parser.feed((final/'index.html').read_text());assert parser.sections==60
 for url in parser.links:
  part=urlsplit(url);assert not part.scheme
  assert (final/unquote(part.path)).resolve().is_file(),url
 repro=read(final/'reproducibility.json')
 for f in repro['files']:assert sha(f['path'])==f['sha256'],f['path']
 for r in rows:assert sha(r['review_file'])==r['review_sha256'] and sha(r['result_file'])==r['result_sha256']
 result={'passed':True,'checked_at':datetime.datetime.now().astimezone().isoformat(),'questions':len(rows),'group_packages':len(flat),'csv_rows':len(flat),'html_local_references_checked':len(parser.links),'reproduction_file_hashes_checked':len(repro['files']),'review_result_hash_pairs_checked':len(rows),'model_facing_packages_exclude_question_reference_and_generated_labels':True,'browser_playback_tested':False,'browser_playback_note':'Local media targets and temporal fragments checked as references; no interactive browser playback test.'}
 dump(REPO/'delivery_checks.json',result);dump(final/'delivery_checks.json',result);print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
