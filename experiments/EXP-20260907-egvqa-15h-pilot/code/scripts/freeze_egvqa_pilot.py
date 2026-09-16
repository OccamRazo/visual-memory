#!/usr/bin/env python3
"""Register the exact eval denominator/config before any eval prediction."""
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from egvqa_pilot import prompts
from egvqa_pilot.runner import read_json,write_json,rows
from egvqa_pilot.model import QwenBackend
from egvqa_pilot.encoding import ClipEncoder
from egvqa_pilot.protocol import fixed_hash_order,merge_evidence_intervals,capsule_coverage_mask,packet_coverage_mask,rank_topk,parse_answer
import numpy as np
import torch

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--dataset',default='data/downloads/egvqa-pilot');p.add_argument('--mode',choices=['standard','smoke'],required=True)
    a=p.parse_args();run=Path(a.run);data=Path(a.dataset);prepared=run/'prepared'
    if (run/'resolved_config.json').exists() or (run/'eval_manifest.json').exists():raise SystemExit('Configuration already frozen; refuse overwrite')
    timing=read_json(run/'timing.json');d0=read_json(run/'d0_summary.json');source=read_json(data/'manifest.json')
    if d0['ledger']['physical_calls']!=50 or d0['status']!='COMPLETE':raise SystemExit('Original 50-request profiling must be complete')
    recheck=read_json(run/'dev_final_summary.json')
    final_calls={r['request_id']:r for r in rows(run/'dev_final_calls.jsonl')}
    normalized=[]
    for row in rows(run/'dev_final_answers.jsonl'):
        call=final_calls[row['request_id']];parsed=parse_answer(row['output_text'],call['allowed_citation_ids'])
        normalized.append({'request_id':row['request_id'],'condition':row['condition'],**parsed})
    validation={'n_answers':len(normalized),'n_parse_failures':sum(not r['parse_ok'] for r in normalized),
        'n_illegal_citations':sum(not r['citations_legal'] for r in normalized),'n_abstentions':sum(r.get('abstained',False) for r in normalized),
        'model_errors':recheck['model_errors'],'truncated_outputs':recheck['truncated_outputs'],
        'empty_answer_rule':'valid JSON abstention is unsuccessful, not an absent logical condition','rows':normalized}
    validation['passed']=len(normalized)==32 and not any(validation[k] for k in ['n_parse_failures','n_illegal_citations','model_errors','truncated_outputs'])
    write_json(run/'dev_final_parser_validation.json',validation)
    if not validation['passed']:raise SystemExit('Final dev mechanical/format gate failed')
    checks=read_json(run/'protocol_checks.json')
    if checks['real_snapshots_checked']!=24 or not all(v=='PASS' for v in checks['checks'].values()):raise SystemExit('All 24 real snapshots and six protocol checks must pass')
    if any((run/name).exists() for name in ['e1_answers.jsonl','e2_answers.jsonl']):raise SystemExit('Eval predictions already exist')
    video_records={row['record']['video_id']:row for row in source['videos']}
    dev=[row['record'] for row in source['videos'] if row['role']=='dev']
    encoder=ClipEncoder();dev_cover=[]
    for v in dev:
        root=prepared/v['video_id'];m=read_json(root/'snapshot/manifest.json')
        with np.load(root/'snapshot/pixels.npz',allow_pickle=False) as f:keys=f['keys']
        ids=[c['capsule_id'] for c in m['capsules']]
        for q in v['questions']:
            groups=merge_evidence_intervals([g['timestamp'] for g in q['evidence']]);target=(1<<len(groups))-1
            masks={c['capsule_id']:capsule_coverage_mask(c['pts'],c['valid_mask'],groups) for c in m['capsules']}
            qkeys,trunc=encoder.texts([q['question']]);top=rank_topk(ids,keys,qkeys[0],6)
            dev_cover.append({'question_id':q['question_id'],'video_id':v['video_id'],
                'stored_ann':packet_coverage_mask(ids,masks)==target,'r0_access_ann':packet_coverage_mask(top,masks)==target,'query_truncated':trunc[0]})
    stored=sum(r['stored_ann'] for r in dev_cover)/len(dev_cover);access=sum(r['r0_access_ann'] for r in dev_cover)/len(dev_cover)
    decision={'n_dev_questions':len(dev_cover),'stored_ann_rate':stored,'r0_access_ann_rate':access,
              'rule':'switch K64 to K32 only if BOTH dev rates >0.90','selected_k':32 if stored>.9 and access>.9 else 64,'rows':dev_cover}
    write_json(run/'dev_k_decision.json',decision)
    if decision['selected_k']!=64:raise SystemExit('Dev rule requires K32. Preserve K64 assets, rebuild all snapshots at K32, then freeze a new run/config.')
    encoder.unload();torch.set_num_threads(4)
    eval_ids=fixed_hash_order([v for v,r in video_records.items() if r['role']=='eval'],seed=17)
    if a.mode=='smoke':eval_ids=eval_ids[:12]
    planned=[];snapshots={};available=[];unavailable=[]
    for vid in eval_ids:
        v=video_records[vid]['record'];sp=prepared/vid/'snapshot/manifest.json'
        if sp.exists() and read_json(sp).get('keys_status')=='ready':
            m=read_json(sp);snapshots[vid]=m['snapshot_hash'];available.append(vid)
        else:unavailable.append(vid)
        byid={q['question_id']:q for q in v['questions']}
        for qid in fixed_hash_order(byid,seed=17):
            q=byid[qid];m=len(merge_evidence_intervals([g['timestamp'] for g in q['evidence']]))
            planned.append({'question_id':qid,'video_id':vid,'m':m,'available':vid in available})
    if a.mode=='standard' and len(available)<15:raise SystemExit('Standard scale requires >=15 prepared eval videos before freeze')
    answer_calls_e1=0
    for q in planned:
        package=read_json(prepared/q['video_id']/'e1'/q['question_id']/'manifest.json')
        if package['construction_status']=='constructed_pending_human_audit':answer_calls_e1+=q['m']+4
    nq=len(planned);answer_remaining=answer_calls_e1+4*nq;control_remaining=2*nq;judge_remaining=(answer_calls_e1+3)//4+nq
    predicted_inference=(answer_remaining*max(d0['profile']['answer_with_images']['latency_s']['p75'],recheck['profile']['answer_with_images']['latency_s']['p75'])+
        control_remaining*d0['profile']['control']['latency_s']['p75']+judge_remaining*d0['profile']['judge']['latency_s']['p75'])
    now=datetime.now(timezone.utc)
    admission={'answer_requests_upper':answer_remaining,'control_requests_upper':control_remaining,'judge_requests_upper':judge_remaining,
        'inference_p75_seconds':predicted_inference,'inference_with_20pct_margin_seconds':1.2*predicted_inference,
        'remaining_implementation_encoding_seconds':1800,'reserved_audit_report_seconds':7200,
        'physical_requests_upper_including_dev':131+answer_remaining+control_remaining+judge_remaining,
        'basis':'D0 measured p75; no cache savings assumed; all original 50 and reserved 81 dev requests counted'}
    admission['total_remaining_seconds']=1.2*predicted_inference+1800+7200
    admission['time_admitted']=(datetime.fromisoformat(timing['deadline'])-now).total_seconds()>admission['total_remaining_seconds'] and (datetime.fromisoformat(timing['model_deadline'])-now).total_seconds()>1.2*predicted_inference+1800
    admission['calls_admitted']=admission['physical_requests_upper_including_dev']<=1400
    if not admission['time_admitted'] or not admission['calls_admitted']:raise SystemExit('Time/call admission failed')
    write_json(run/'budget_admission.json',admission)
    frozen_at=now.isoformat();backend=QwenBackend(cache_dir=run/'model_cache')
    source_files=sorted(Path('src/egvqa_pilot').glob('*.py'))+[Path('src/egvqa_subset.py')]
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
    gpu=subprocess.check_output(['nvidia-smi','--query-gpu=name,driver_version,memory.total,memory.used','--format=csv,noheader'],text=True).strip()
    config={'eval_frozen':True,'frozen_at':frozen_at,'scale':a.mode,'timing':timing,
        'dataset':{k:source[k] for k in ['dataset','revision','annotation_sha256','selection']},
        'dataset_manifest_sha256':hashlib.sha256((data/'manifest.json').read_bytes()).hexdigest(),
        'model':backend.identity(),'prompts':prompts.identity(),'clip':read_json(Path('/root/autodl-tmp/models/clip-vit-base-patch32/source_revision.json')),
        'budget_admission':admission,'final_parser_validation':{k:v for k,v in validation.items() if k!='rows'},'dev_recheck':recheck,'gpu':gpu,'K':64,'k_decision':{k:v for k,v in decision.items() if k!='rows'},
        'limits':{'single_request_tokens':8192,'single_request_images':24,'e2_method_tokens':12288,'core_physical_calls':1400,'total_physical_calls':1800,'R1_R2_calls':2},
        'seeds':{'writer':17,'selection':17,'bootstrap':43,'judge_order':43},'bootstrap_resamples':2000,
        'source_sha256':hashes,'git_base':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'snapshot_hashes':snapshots,'e3_status':'NOT_RUN','e3_reason':'Human judge calibration and core scientific audits must pass before E3 can enter.',
        'human_judge_calibration':'NOT_RUN_pending_external_human_review',
        'scientific_status':'PROVISIONAL_UNCALIBRATED_PILOT',
        'registered_deviations':['D0 human judge calibration is pending. Before any eval prediction, choose the preregistered 12-video/48-question smoke size; this downgrade is due to the missing human gate, not insufficient GPU throughput. It cannot pass standard-scale scientific acceptance.', 'The original 50 profiling calls are preserved. Use 81 of the 100 core reserve calls for two 40-call format checks and one updated max-context check. Final answer cap is 128, control96, judge256; include the exact allowed citation IDs (empty for Blind) in each answer request. Normalize legal single-string controller output to a one-query list using CPU; no extra controller model calls. Before eval, parse valid JSON empty answers as explicit abstentions scored zero, retaining the pair; malformed JSON remains a failure.'],
        'execution_note':'Run the frozen paired conditions to completion; retain all failures and all planned questions. Do not tune against eval answers.'}
    write_json(run/'eval_manifest.json',{'frozen_at':frozen_at,'mode':a.mode,'question_order_rule':'sha256 seed17 video then question',
        'n_questions':len(planned),'n_videos':len(eval_ids),'available_videos':available,'unavailable_videos':unavailable,'questions':planned})
    write_json(run/'resolved_config.json',config)
    print(json.dumps({'frozen_at':frozen_at,'mode':a.mode,'planned_questions':len(planned),'videos':len(eval_ids),'K':64,'dev_stored_ann':stored,'dev_r0_access_ann':access,'human_calibration':'PENDING'},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
