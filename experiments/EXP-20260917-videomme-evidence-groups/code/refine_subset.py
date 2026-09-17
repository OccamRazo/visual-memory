"""Test a source-reviewed alternative subset, retaining original decisions and calls."""
import argparse,copy,datetime
from pathlib import Path
from group import Runner,OUT,read,dump,sha,safe

def main():
 ap=argparse.ArgumentParser();ap.add_argument('qid');ap.add_argument('--groups',nargs='+',required=True);ap.add_argument('--reason',required=True);args=ap.parse_args()
 q=args.qid if args.qid.startswith('videomme:') else 'videomme:'+args.qid
 path=OUT/'results'/f'{safe(q)}.json';original=read(path);assert original['status']=='review_candidate'
 assert not (OUT/'reviews'/f'{safe(q)}.json').exists(),'Preserve completed reviews: explicit archival required'
 r=copy.deepcopy(original);p=read(r['package_file']);runner=Runner();sv=r['subset_validation'];tests=sv['tests']
 assert set(args.groups)<={g['id'] for g in r['groups']}
 def check(ids):
  ids=sorted(ids)
  for t in tests:
   if t['group_ids']==ids:return t['supported']
  value,call=runner.check_subset(r,p,ids);passed=runner.subset_success(value)
  tests.append({'group_ids':ids,'supported':passed,'result':value,'call_file':call});return passed
 chosen=sorted(args.groups);supported=check(chosen)
 if supported:
  for gid in list(reversed(chosen)):
   if check([g for g in chosen if g!=gid]):chosen.remove(gid)
  for gid in chosen:assert not check([g for g in chosen if g!=gid])
  sv['selected_group_ids']=chosen;sv['irreducible_group_count']=len(chosen);sv['redundant_or_alternative_group_ids']=[g['id'] for g in r['groups'] if g['id'] not in chosen]
 archive=OUT/'superseded_results'/f'{safe(q)}-{sha(path)[:12]}.json';archive.parent.mkdir(exist_ok=True);path.rename(archive)
 r.setdefault('subset_adjudications',[]).append({'reason_zh':args.reason,'proposed_group_ids':args.groups,'supported':supported,'previous_result':str(archive),'previous_result_sha256':sha(archive),'created_at':datetime.datetime.now().astimezone().isoformat()})
 dump(path,r);print(q,'supported',supported,'selected',sv['selected_group_ids']);runner.summary()

if __name__=='__main__':main()
