"""Recoverable, single-service E1/E2 execution. Gold is evaluator-only.

Normal selections and packet reads occur in the Landlock worker. This trusted
broker owns the frozen model, request ledger, privileged diagnostics and scoring.
It never feeds references, gold timestamps, judge feedback, or control outputs
into the normal final consumer prompt.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import time
from datetime import datetime, timezone
import numpy as np
from . import prompts
from .data import json_bytes, validate_snapshot_budget
from .encoding import ClipEncoder
from .model import QwenBackend
from .protocol import (BudgetLedger, BudgetExceeded, parse_answer, parse_control, parse_judge,
    anonymous_judge_batch, fixed_hash_order, merge_evidence_intervals,
    capsule_coverage_mask, packet_coverage_mask, select_rstar)
from .reader import SafeReader, packet_images, privileged_packet


def read_json(path): return json.loads(Path(path).read_text())
def write_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');temp.replace(path)
def rows(path):
    path=Path(path)
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []
def append(path,row):
    with Path(path).open('a') as f:f.write(json.dumps(row,ensure_ascii=False,default=str)+'\n');f.flush()
def result_id(phase,qid,condition):return f'{phase}:{qid}:{condition}'

def e1_images(root,qid,condition):
    root=Path(root)/'e1'/qid;manifest=read_json(root/'manifest.json')
    wanted=manifest['conditions'][condition]['group_ids']
    if not wanted:return [],manifest
    by_id={g['group_id']:g for g in manifest['groups']}
    with np.load(root/'pixels.npz',allow_pickle=False) as f: pixels=f['images']
    images=[]
    for i in wanted:
        group=by_id[i]
        for pts,image in zip(group['pts'],pixels[group['image_index']]):images.append({'image':image,'id':i,'pts':pts})
    return images,manifest

class ExperimentRunner:
    def __init__(self,run_dir,dataset_dir):
        self.run=Path(run_dir);self.dataset=Path(dataset_dir);self.prepared=self.run/'prepared'
        self.config=read_json(self.run/'resolved_config.json')
        self.frozen=read_json(self.run/'eval_manifest.json')
        if not self.config.get('eval_frozen'):raise ValueError('Eval configuration must be frozen before model predictions')
        if self.config['prompts']['sha256']!=prompts.identity()['sha256']:raise ValueError('Prompts changed after freeze')
        for path,expected in self.config['source_sha256'].items():
            if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:raise ValueError(f'Scientific source changed after freeze: {path}')
        self.ledger_path=self.run/'ledger.json'
        if self.ledger_path.exists():saved=read_json(self.ledger_path)
        else:
            candidates=['dev_final_ledger.json','dev_recheck_ledger.json','d0_ledger.json']
            saved=read_json(next(self.run/name for name in candidates if (self.run/name).exists()))
        self.ledger=BudgetLedger.from_records(saved)
        self.calls_path=self.run/'calls.jsonl'
        if not self.calls_path.exists():
            existing={}
            for filename in ['boundary_calls.jsonl','d0_calls.jsonl','dev_recheck_calls.jsonl','dev_final_calls.jsonl']:
                for record in rows(self.run/filename):existing[record['request_id']]=record
            for record in existing.values():append(self.calls_path,record)
        self.calls={r['request_id']:r for r in rows(self.calls_path)}
        self.backend=QwenBackend(cache_dir=self.run/'model_cache')
        self.clip=ClipEncoder()
        import torch
        torch.set_num_threads(4)
        if self.backend.identity()['identity_hash']!=self.config['model']['identity_hash']:
            raise ValueError('Model/processor/backend identity differs from frozen configuration')
        self.questions={}
        for record in read_json(self.dataset/'annotations/eval.json'):
            for q in record['questions']:
                self.questions[q['question_id']]={**q,'video_id':record['video_id']}
        self.planned=[self.questions[q['question_id']] for q in self.frozen['questions']]

    def _deadline(self):
        if datetime.now(timezone.utc)>=datetime.fromisoformat(self.config['timing']['model_deadline']):
            raise BudgetExceeded('Registered model-task deadline reached')

    def call(self,phase,qid,method,condition,role,text,images=None,snapshot_hash=None):
        self._deadline();rid=f'{phase}:{qid}:{method}:{condition}:{role}:1'
        if rid in self.calls:return self.calls[rid]
        prepared=self.backend.prepare(role,text,images or [])
        cached=self.backend.cache_lookup(prepared)
        if rid in self.ledger.entries:
            entry=self.ledger.entries[rid]
            if entry.state=='reserved' and cached is not None:
                # Recover a completed response after a crash between cache and ledger.
                record={**cached,'request_id':rid,'recovered_after_interrupt':True}
                self.ledger.finalize(rid,output_tokens=record['output_tokens'],error=record.get('error'))
            else:
                raise RuntimeError(f'Unresolved prior request {rid}; no hidden retry is allowed')
        else:
            self.ledger.reserve(request_id=rid,phase=phase,question_id=qid,method=method,condition=condition,
                                role=role,input_tokens=prepared.input_tokens,max_output_tokens=prepared.max_new_tokens,
                                physical_request=cached is None)
            write_json(self.ledger_path,self.ledger.records())
            record=self.backend.generate(prepared=prepared,request_id=rid,
                metadata={'phase':phase,'question_id':qid,'method':method,'condition':condition,'snapshot_hash':snapshot_hash})
            error=record.get('error') or ('output_truncated' if record.get('truncated') else None)
            out=None if record.get('output_tokens_complete') is False else int(record['output_tokens'])
            self.ledger.finalize(rid,output_tokens=out,error=error)
        record.update(phase=phase,question_id=qid,method=method,condition=condition,snapshot_hash=snapshot_hash)
        append(self.calls_path,record);self.calls[rid]=record;write_json(self.ledger_path,self.ledger.records())
        print(json.dumps({'request_id':rid,'cache_hit':record.get('cache_hit'),'tokens':record.get('total_tokens'),
                          'latency_s':round(record.get('latency_s',0),3),'error':record.get('error'),'truncated':record.get('truncated')},ensure_ascii=False),flush=True)
        return record

    def answer(self,phase,q,method,condition,images,snapshot_hash=None):
        ids=list(dict.fromkeys(i['id'] for i in images))
        row={'result_id':result_id(phase,q['question_id'],condition),'question_id':q['question_id'],'video_id':q['video_id'],
             'phase':phase,'method':method,'condition':condition,'selected_ids':ids,'snapshot_hash':snapshot_hash}
        try:
            result=self.call(phase,q['question_id'],method,condition,'answer',prompts.ANSWER.format(question=q['question']),images,snapshot_hash)
            parsed=parse_answer(result['output_text'],ids)
            row.update(parsed,request_id=result['request_id'],output_text=result['output_text'],
                       truncated=result.get('truncated',False),error=result.get('error'),
                       logical_latency_s=result.get('latency_s',0),physical_latency_s=result.get('physical_latency_s',0),
                       peak_cuda_reserved_bytes=result.get('peak_cuda_reserved_bytes',0))
            row['status']='complete' if parsed['parse_ok'] and not row['truncated'] and not row['error'] else 'failed'
        except Exception as exc:
            row.update(status='failed',error=f'{type(exc).__name__}: {exc}',answer='',citations=[],citations_legal=False,parse_ok=False)
        return row

    def run_e1(self):
        path=self.run/'e1_answers.jsonl';done={r['result_id'] for r in rows(path)}
        for q in self.planned:
            p=self.prepared/q['video_id']/'e1'/q['question_id']/'manifest.json'
            package=read_json(p) if p.exists() else {'construction_status':'missing','reasons':['missing_video_or_package']}
            m=len(merge_evidence_intervals([x['timestamp'] for x in q['evidence']]))
            conditions=['Full']+[f'Key-{i+1}' for i in range(m)]+['Irrel-1','Irrel-2','Blind']
            for condition in conditions:
                if result_id('E1',q['question_id'],condition) in done:continue
                if package['construction_status']!='constructed_pending_human_audit':
                    row={'result_id':result_id('E1',q['question_id'],condition),'phase':'E1','question_id':q['question_id'],
                         'video_id':q['video_id'],'condition':condition,'method':'E1','status':'construction_failed',
                         'error':','.join(package['reasons']),'answer':'','citations_legal':False,'intervention_valid':False}
                else:
                    images,package=e1_images(self.prepared/q['video_id'],q['question_id'],condition)
                    row=self.answer('E1',q,'E1',condition,images)
                    row.update(intervention_valid=True,intervention_validity_scope='mechanical_checks_only_human_pending',
                               replacement=package['conditions'][condition],package_hash=package['package_hash'])
                row.update(m=m,human_audit_status='pending')
                append(path,row)
        self.score('E1',path,self.run/'e1_pairs.jsonl')

    def run_e2(self):
        path=self.run/'e2_answers.jsonl';done={r['result_id'] for r in rows(path)}
        for q in self.planned:
            vid=q['video_id'];root=self.prepared/vid;snapshot=root/'snapshot'
            needed=[method for method in ['R0','R1','R2','R*'] if result_id('E2',q['question_id'],method) not in done]
            if not needed:continue
            try:
                manifest=read_json(snapshot/'manifest.json');validate_snapshot_budget(snapshot,manifest)
                groups=merge_evidence_intervals([x['timestamp'] for x in q['evidence']]);target=(1<<len(groups))-1
                coverage={c['capsule_id']:capsule_coverage_mask(c['pts'],c['valid_mask'],groups) for c in manifest['capsules']}
                candidates=read_json(root/'audit/candidates.json')
                full_coverage=0
                for c in candidates:full_coverage|=capsule_coverage_mask(c['pts'],c['valid_mask'],groups)
                qkey,qtrunc=self.clip.texts([q['question']])
                with SafeReader(snapshot) as reader:
                    ranked=reader.request('rank',query=qkey[0],k=len(manifest['capsules']))
                    reference=select_rstar(ranked,coverage,ranked,len(groups)) # trusted evaluator only
                    initial=ranked[:3]
                    for method in needed:
                        try:
                            started=time.monotonic();control=None;selection={};control_result=None
                            if method=='R0':selected=ranked[:6]
                            elif method=='R*':selected=reference['selected_ids']
                            else:
                                first_packet=reader.request('packet',ids=initial)
                                prompt=prompts.CONTROL_R1 if method=='R1' else prompts.CONTROL_R2
                                control_result=self.call('E2',q['question_id'],method,'control','control',prompt.format(question=q['question']),packet_images(first_packet),manifest['snapshot_hash'])
                                control=parse_control(control_result['output_text'],q['question'],method)
                                if control_result.get('error') or control_result.get('truncated'):
                                    control={'queries':[q['question']],'parse_ok':False,'fallback':True,'parse_error':'control_inference_error_or_truncation'}
                                gap_keys,gap_trunc=self.clip.texts(control['queries']);control['clip_text_truncated']=gap_trunc
                                if method=='R1':extra=reader.request('rank',query=gap_keys[0],k=3,exclude=initial)
                                else:
                                    selection=reader.request('r2',gap_keys=gap_keys,initial_ids=initial);extra=selection['selected_ids']
                                selected=initial+extra
                            packet=privileged_packet(snapshot,selected) if method=='R*' else reader.request('packet',ids=selected)
                            row=self.answer('E2',q,method,method,packet_images(packet),manifest['snapshot_hash'])
                            row.update(self.ledger.method_cost('E2',q['question_id'],method))
                            row.update(initial_ids=initial if method in ['R1','R2'] else [],control=control,selection=selection,
                                       stored_ann=reference['stored_ann'],feasible_ann=reference['feasible_ann'],
                                       minimum_cover_size=reference['minimum_cover_size'],
                                       access_ann=packet_coverage_mask(selected,coverage)==target,full_candidates_ann=full_coverage==target,
                                       covered_mask=packet_coverage_mask(selected,coverage),target_mask=target,
                                       clip_question_truncated=qtrunc[0],wall_elapsed_s=time.monotonic()-started,
                                       reader_isolation={'landlock_abi':reader.identity['abi'] if method!='R*' else None,'snapshot_hash_verified':True,'role':'privileged_diagnostic_process' if method=='R*' else 'normal_isolated_reader'},human_audit_status='pending')
                            if control_result:
                                row['logical_latency_s']=row.get('logical_latency_s',0)+control_result.get('latency_s',0)
                                row['physical_latency_s']=row.get('physical_latency_s',0)+control_result.get('physical_latency_s',0)
                                row['peak_cuda_reserved_bytes']=max(row.get('peak_cuda_reserved_bytes',0),control_result.get('peak_cuda_reserved_bytes',0))
                            append(path,row);done.add(row['result_id'])
                        except Exception as exc:
                            row={'result_id':result_id('E2',q['question_id'],method),'phase':'E2','question_id':q['question_id'],
                                 'video_id':vid,'method':method,'condition':method,'status':'failed','answer':'',
                                 'citations_legal':False,'error':f'{type(exc).__name__}: {exc}',
                                 'snapshot_hash':manifest['snapshot_hash'],'stored_ann':reference['stored_ann'],
                                 'feasible_ann':reference['feasible_ann'],'full_candidates_ann':full_coverage==target,
                                 'access_ann':False,**self.ledger.method_cost('E2',q['question_id'],method)}
                            append(path,row);done.add(row['result_id'])
            except Exception as exc:
                for method in needed:
                    rid=result_id('E2',q['question_id'],method)
                    if rid in done:continue
                    row={'result_id':rid,'phase':'E2','question_id':q['question_id'],'video_id':vid,'method':method,
                         'condition':method,'status':'failed','answer':'','citations_legal':False,
                         'error':f'{type(exc).__name__}: {exc}',**self.ledger.method_cost('E2',q['question_id'],method)}
                    append(path,row);done.add(rid)
        self.score('E2',path,self.run/'e2_results.jsonl')

    def score(self,phase,input_path,output_path):
        answers=rows(input_path);done={r['result_id'] for r in rows(output_path)}
        pending={r['result_id']:r for r in answers if r['result_id'] not in done}
        good=[]
        for rid in fixed_hash_order(pending):
            row=pending[rid]
            if row['status']!='complete' or row.get('abstained') or not row.get('answer','').strip():
                append(output_path,{**row,'verdict':'incorrect','judge_reason':'empty_answer_abstention' if row['status']=='complete' else 'execution_or_construction_failure','judge_parse_ok':row['status']=='complete'})
            else:good.append(row)
        for start in range(0,len(good),4):
            batch=good[start:start+4]
            items=[{'item_id':r['result_id'],'question':self.questions[r['question_id']]['question'],
                    'reference':self.questions[r['question_id']]['answer'],'prediction':r['answer']} for r in batch]
            blinded,mapping=anonymous_judge_batch(items,seed=43+start)
            batchid=hashlib.sha256(json_bytes([r['result_id'] for r in batch])).hexdigest()[:20]
            text=prompts.JUDGE.format(items=json.dumps(blinded,ensure_ascii=False))
            try:
                result=self.call(phase,'judge-'+batchid,'judge','batch','judge',text)
                parsed=parse_judge(result['output_text'],list(mapping))
                if result.get('error') or result.get('truncated'):
                    parsed=[{'id':i,'verdict':'uncertain','reason':'judge_error_or_truncation','parse_ok':False} for i in mapping]
            except Exception as exc:
                result={'request_id':None,'error':f'{type(exc).__name__}: {exc}'}
                parsed=[{'id':i,'verdict':'uncertain','reason':result['error'],'parse_ok':False} for i in mapping]
            byid={r['result_id']:r for r in batch}
            append(self.run/'judge_batches.jsonl',{'phase':phase,'request_id':result['request_id'],'blinded_items':blinded,'mapping':mapping})
            for p in parsed:
                row=byid[mapping[p['id']]]
                append(output_path,{**row,'verdict':p['verdict'],'judge_reason':p['reason'],'judge_parse_ok':p['parse_ok'],
                                    'judge_request_id':result['request_id'],'judge_type':'same_frozen_Qwen_local_pilot_not_official'})

    def close(self):self.backend.unload();self.clip.unload()
