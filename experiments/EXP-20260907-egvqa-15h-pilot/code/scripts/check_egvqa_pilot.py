#!/usr/bin/env python3
"""Protocol checks against real sealed snapshots/packages, without a VLM call."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from egvqa_pilot.reader import SafeReader
from egvqa_pilot.data import validate_snapshot_budget

def load(p):return json.loads(p.read_text())
def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--dataset',default='data/downloads/egvqa-pilot');a=p.parse_args()
    run=Path(a.run);root=run/'prepared';dataset=Path(a.dataset).resolve();records=[]
    paths=sorted(root.glob('*/snapshot/manifest.json'))
    for path in paths:
        manifest=load(path)
        if manifest['keys_status']!='ready':continue
        budget=validate_snapshot_budget(path.parent)
        # All prohibited paths exist: denial cannot be faked by missing data.
        vid=manifest['video_id'];record=next(r['record'] for r in load(dataset/'manifest.json')['videos'] if r['record']['video_id']==vid)
        probes=[str(dataset/record['video_path']),str(dataset/'annotations/eval.json'),str(path.parent.parent/'audit/candidates.json')]
        with SafeReader(path.parent) as reader:
            denied=reader.request('probe',paths=[str(Path(x).resolve()) for x in probes])
            assert all(v=='denied' for v in denied.values()),denied
            candidates=load(path.parent.parent/'audit/candidates.json');live=set(reader.identity['ids'])
            evicted=next((c['capsule_id'] for c in candidates if c['capsule_id'] not in live),'__illegal_id__')
            try:reader.request('packet',ids=[evicted])
            except PermissionError:pass
            else:raise AssertionError('evicted ID returned payload')
            with np.load(path.parent/'pixels.npz',allow_pickle=False) as payload:query=payload['keys'][0]
            before=reader.request('rank',query=query,k=6)
            reader.request('rank',query=-query,k=6)
            after=reader.request('rank',query=query,k=6)
            assert before==after
            packet=reader.request('packet',ids=before)
            for capsule,pixels in zip(packet['capsules'],packet['images']):
                for pixel,valid,expected in zip(pixels,capsule['valid_mask'],capsule['frame_hashes']):
                    if valid:assert hashlib.sha256(pixel.tobytes()).hexdigest()==expected
        records.append({'video_id':vid,'snapshot_hash':manifest['snapshot_hash'],'byte_budget':budget,
                        'forbidden_paths':denied,'evicted_id_rejected':evicted,'query_order_invariant':True,'packet_hashes_verified':True})
    pairs=[]
    for path in sorted(root.glob('*/e1/*/manifest.json')):
        pkg=load(path)
        if pkg['construction_status']!='constructed_pending_human_audit':continue
        groups={g['group_id']:g for g in pkg['groups']}
        full=pkg['conditions']['Full'];full_ids=set(full['group_ids'])
        assert len(full_ids)*4<=24
        with np.load(path.parent/'pixels.npz',allow_pickle=False) as f:pixels=f['images']
        for g in groups.values():
            assert len(set(g['pts']))==4
            assert [hashlib.sha256(x.tobytes()).hexdigest() for x in pixels[g['image_index']]]==g['frame_hashes']
        for name,c in pkg['conditions'].items():
            if name in ['Full','Blind']:continue
            selected=set(c['group_ids'])
            assert c['num_images']==full['num_images']
            assert full_ids-selected=={c['replaced_group_id']}
            assert selected-full_ids=={c['replacement_group_id']}
            removed=groups[c['replaced_group_id']]
            # Exact duplicates elsewhere invalidate the intervention mechanically.
            retained_hashes={h for i in selected for h in groups[i]['frame_hashes']}
            overlap=set(removed['frame_hashes'])&retained_hashes
            pairs.append({'question_id':pkg['question_id'],'condition':name,'paired_input_difference_checked':True,
                          'removed_frame_hash_still_present':sorted(overlap),'human_semantic_duplicate_audit':'pending'})
    testenv={k:v for k,v in os.environ.items() if k.lower() not in ('http_proxy','https_proxy','all_proxy')}
    test=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],capture_output=True,text=True,env=testenv)
    (run/'tests.log').write_text(test.stdout+test.stderr)
    result={'real_snapshots_checked':len(records),'snapshots':records,'paired_interventions':pairs,'unit_test_returncode':test.returncode,
            'checks':{'snapshot_causality':'PASS' if test.returncode==0 else 'FAIL',
                      'no_replay':'PASS' if records else '未运行','dual_budget':'PASS' if records and test.returncode==0 else '未运行',
                      'paired_intervention':'PASS' if pairs and not any(p['removed_frame_hash_still_present'] for p in pairs) else 'FAIL',
                      'cross_question_isolation':'PASS' if records and test.returncode==0 else '未运行',
                      'scoring_aggregation':'PASS' if test.returncode==0 else 'FAIL'},
            'limits':['No VLM cross-order replay was added; backend constructs independent messages and clears request tensors.',
                      'Hash equality checks cannot establish semantic absence of alternative evidence. Human audit remains pending.']}
    (run/'protocol_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['snapshots','paired_interventions']},ensure_ascii=False),flush=True)
    if test.returncode:raise SystemExit(test.returncode)
if __name__=='__main__':main()
