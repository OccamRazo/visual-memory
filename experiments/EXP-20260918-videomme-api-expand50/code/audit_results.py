#!/usr/bin/env python3
"""Read-only source/manifest audit; save new terminal record only after completion."""
import argparse,collections,json
from pathlib import Path
import engine as e
from repair import Repair
from expand import target_counts

def audit(record_dir=None):
 out=e.OUT;status=e.read(out/'status.json');manifest=e.read(out/'manifest.json');queue=e.read(out/'queue.json');base=e.read(out/'baseline32.json')['entries'];rows=e.read(out/'all_results.json')
 assert status['state']=='completed' and not status['active'] and status['remaining']==0
 assert {r['qid'] for r in rows}==set(queue['admitted_qids']) and len(rows)==len(queue['admitted_qids'])>=50
 assert {i['qid'] for i in manifest['entries'][:50]}<=set(queue['admitted_qids'])
 assert dict(collections.Counter(r['status'] for r in rows))==status['status_counts']
 counts=target_counts(base,rows);assert counts['cumulative_multi']>=51
 assert all(status[k]==v for k,v in counts.items())
 entries={i['qid']:i for i in manifest['entries']};checker=Repair.__new__(Repair);frame_hashes={};reviewed=[]
 for item in manifest['entries']:
  assert e.sha(item['input_file'])==item['input_sha256']
  q=e.read(item['input_file']);assert e.sha(q['caption_packet_file'])==q['caption_packet_sha256']
  v=Path(q['video_path']);assert v.stat().st_size==q['video_size_bytes'] and v.stat().st_mtime_ns==q['video_mtime_ns']
 for b in base:
  assert e.sha(b['result_file'])==b['result_sha256'] and e.sha(b['source_packet_file'])==b['source_packet_sha256']
  assert e.read(b['result_file'])['status']=='source_supported_multi'
 for r in rows:
  q=e.read(entries[r['qid']]['input_file'])
  if not r['status'].startswith('source_supported'):continue
  p=e.read(r['final_source_packet_file']);assert e.sha(r['final_source_packet_file'])==r['final_source_packet_sha256']
  last=r['rounds'][-1];v=last['verification'];call=e.read(last['verify_call']);assert call['status']=='ok' and call['parsed']==v
  checker.check(v,p,True);assert checker.decision(v)==r['status']
  assert r['fact_evidence']==checker.bound_result(q,p,v)
  for f in p['frames']:
   if f['path'] not in frame_hashes:frame_hashes[f['path']]=e.sha(f['path'])
   assert frame_hashes[f['path']]==f['sha256']
  reviewed.append({'qid':r['qid'],'status':r['status'],'semantic_groups':len(r['semantic_groups']),'facts':len(r['fact_evidence']),'source_packet_sha256':r['final_source_packet_sha256']})
 index=e.read(out/'cumulative_supported_multi.json');assert len(index['entries'])==counts['cumulative_multi']
 assert len({r['qid'] for r in index['entries']})==len(index['entries'])
 assert len({r['video_id'] for r in index['entries']})==len(index['entries'])
 for r in index['entries']:
  assert e.sha(r['result_file'])==r['result_sha256'] and e.sha(r['source_packet_file'])==r['source_packet_sha256']
 calls=[e.read(p) for p in (out/'calls').glob('*/*/*/attempt-*.json')]
 report={'checked_at':e.now(),'status':status,'counts':counts,'initial50_all_terminal':True,'baseline32_hashes_unchanged':True,'all98_frozen_inputs_unchanged':True,'cumulative_unique_videos':len(index['entries']),'new_supported_source_packets_checked':len(reviewed),'new_source_frame_hashes_checked':len(frame_hashes),'returned_models':sorted({c.get('resolved_model','unknown') for c in calls}),'source_audit_kind':'Automated integrity/schema audit of actual saved API/source artifacts; no new visual or human review.','supported_question_checks':reviewed,'remaining_cases':[{'qid':r['qid'],'status':r['status'],'error':r.get('last_call_error',r.get('error')),'missing_required':r.get('missing_required',[])} for r in rows if not r['status'].startswith('source_supported')]}
 for name,data in [('terminal_summary.json',report),('cumulative_supported_multi.json',index)]:
  dest=(Path(record_dir) if record_dir else e.REPO)/name
  if dest.exists():raise FileExistsError(f'Preserve existing record: {dest}')
  e.dump(dest,data)
 print(json.dumps({'processed':len(rows),**counts,'statuses':status['status_counts'],'checked_frames':len(frame_hashes)},ensure_ascii=False))

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--record-dir');args=ap.parse_args();audit(args.record_dir)
