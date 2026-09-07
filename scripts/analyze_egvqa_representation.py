#!/usr/bin/env python3
"""Post-hoc CPU diagnostics; no VLM calls and no change to frozen outputs."""
import argparse
from collections import Counter
import itertools
import json
from pathlib import Path
import statistics
import sys
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from egvqa_pilot.protocol import merge_evidence_intervals, capsule_coverage_mask, packet_coverage_mask
from egvqa_pilot.encoding import ClipEncoder


def read(p): return json.loads(p.read_text())
def rows(p): return [json.loads(s) for s in p.open()]
def stats(xs):
    return {'n': len(xs), 'min': min(xs), 'median': statistics.median(xs),
            'mean': statistics.mean(xs), 'max': max(xs)} if xs else {'n': 0}
def write(p, value): p.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def main():
    p = argparse.ArgumentParser(); p.add_argument('--source-run', required=True); p.add_argument('--output', required=True)
    p.add_argument('--dataset', default='data/downloads/egvqa-pilot'); a = p.parse_args()
    source, output = Path(a.source_run), Path(a.output)
    summary = read(source/'summary.json'); planned = read(source/'eval_manifest.json')['questions']
    questions = {q['question_id']: {**q, 'video_id': v['video_id']}
                 for v in read(Path(a.dataset)/'annotations/eval.json') for q in v['questions']}
    e1 = {(r['question_id'],r['condition']):r for r in rows(source/'e1_pairs.jsonl')}
    e2 = {(r['question_id'],r['method']):r for r in rows(source/'e2_results.jsonl')}
    valid = [r for r in summary['E1']['pairs'] if r['valid_pair']]
    groups_out=[]; question_out=[]; snapshots={}
    for q in planned:
        qid=q['question_id']; video=q['video_id']; root=source/'prepared'/video
        if video not in snapshots:
            manifest=read(root/'snapshot/manifest.json')
            with np.load(root/'snapshot/pixels.npz',allow_pickle=False) as z: keys=z['keys']
            snapshots[video]=(manifest,keys)
        if (qid,'Full') not in e1 or e1[qid,'Full']['status']!='complete': continue
        m=read(root/'e1'/qid/'manifest.json'); byid={g['group_id']:g for g in m['groups']}
        for i,interval in enumerate(m['gold_groups']):
            cid=m['conditions'][f'Key-{i+1}']['replaced_group_id']; g=byid[cid]
            duration=interval[1]-interval[0]; pts=g['pts']; gaps=np.diff(pts).tolist()
            groups_out.append({'question_id':qid,'group_id':cid,'interval':interval,'duration_s':duration,
                               'selected_pts':pts,'max_adjacent_gap_s':max(gaps), 'images_per_interval_second':4/duration})
    for typ in sorted({questions[q['question_id']]['type'] for q in planned}):
        pairs=[r for r in valid if questions[r['question_id']]['type']==typ]
        question_out.append({'type':typ,'n_valid_E1':len(pairs),'n_Full_correct':sum(r['scores']['Full'] for r in pairs),
                             'mean_D':statistics.mean(r['D'] for r in pairs),
                             'E2_correct':{method:sum(e2[q['question_id'],method]['verdict']=='correct'
                                 for q in planned if questions[q['question_id']]['type']==typ) for method in ['R0','R1','R2','R*']}})
    overlaps=[]; read_details=[]; query_texts=[]
    for q in planned:
        qid=q['question_id']; r1=e2[qid,'R1']; r2=e2[qid,'R2']
        overlaps.append(len(set(r1['selected_ids'])&set(r2['selected_ids'])))
        query_texts.extend(r2['control']['queries'])
    # Existing frozen CLIP only: a read-only retrieval ablation at alpha=0.
    encoder=ClipEncoder(device='cpu'); ablations=[]
    for q in planned:
        qid=q['question_id']; video=q['video_id']; m,keys=snapshots[video]
        ids=[c['capsule_id'] for c in m['capsules']]; byid={i:j for j,i in enumerate(ids)}
        gold=merge_evidence_intervals([r['timestamp'] for r in questions[qid]['evidence']]); target=(1<<len(gold))-1
        masks={c['capsule_id']:capsule_coverage_mask(c['pts'],c['valid_mask'],gold) for c in m['capsules']}
        r1,r2,rs=[e2[qid,name] for name in ['R1','R2','R*']]
        qkeys,_=encoder.texts(r2['control']['queries']); pool=r2['selection']['candidate_ids']
        redundancy_metrics={}
        initial=keys[[byid[i] for i in r2['initial_ids']]]
        for name,row in [('R1',r1),('R2',r2)]:
            extra=[i for i in row['selected_ids'] if i not in row['initial_ids']]
            z=keys[[byid[i] for i in extra]]
            redundancy_metrics[name]={'mean_extra_pair_cosine':statistics.mean(float(z[i]@z[j]) for i,j in itertools.combinations(range(len(z)),2)),
                              'mean_extra_max_initial_cosine':float((z@initial.T).max(axis=1).mean())}
        r2extra=r2['selection']['selected_ids']; extra_keys=keys[[byid[i] for i in r2extra]]
        scores=extra_keys@qkeys.T; contributors=len(set(scores.argmax(axis=0).tolist()))
        query_cosine=float(qkeys[0]@qkeys[1]) if len(qkeys)==2 else None
        candidates=[]
        for chosen in itertools.combinations(sorted(pool), min(3,len(pool))):
            z=keys[[byid[i] for i in chosen]]
            coverage=float((z@qkeys.T).max(axis=0).sum())
            redundancy=statistics.mean(float(z[i]@z[j]) for i,j in itertools.combinations(range(len(z)),2)) if len(z)>1 else 0.0
            candidates.append({'chosen':list(chosen),'coverage':coverage,'redundancy':redundancy})
        # Float32 CLIP dot products; compare to recorded choices and report any mismatch.
        pick=lambda alpha:min(candidates,key=lambda c:(-(c['coverage']-alpha*c['redundancy']),c['chosen']))
        without=pick(0); original=pick(.2)
        new_ids=r2['initial_ids']+without['chosen']
        new_access=packet_coverage_mask(new_ids,masks)==target
        ablations.append({'question_id':qid,'recorded_selected_extra':r2['selection']['selected_ids'],
                           'alpha02_recomputed':original['chosen'],'alpha02_matches_recorded':original['chosen']==r2['selection']['selected_ids'],
                           'alpha0_extra':without['chosen'],'alpha0_access_ann':new_access,'recorded_access_ann':r2['access_ann'],
                           'alpha0_coverage_objective':without['coverage'],'alpha0_redundancy':without['redundancy'],
                           'alpha02_coverage_objective':original['coverage'],'alpha02_redundancy':original['redundancy']})
        pergroup=[]
        for j,(start,end) in enumerate(gold):
            times=sorted({t for c in m['capsules'] if c['capsule_id'] in rs['selected_ids']
                          for t,valid in zip(c['pts'],c['valid_mask']) if valid and start<=t<end})
            pergroup.append({'interval':[start,end],'n_Rstar_distinct_pts':len(times),
                             'Rstar_selected_pts':times,'covered_by_proxy':any(masks[i]&(1<<j) for i in rs['selected_ids'])})
        read_details.append({'question_id':qid,'question':questions[qid]['question'],'type':questions[qid]['type'],
            'R1_queries':r1['control']['queries'],'R2_queries':r2['control']['queries'],
            'R1_R2_packet_overlap':len(set(r1['selected_ids'])&set(r2['selected_ids'])),
            'redundancy':redundancy_metrics,'R2_coverage_contributing_extra_items':contributors,
            'R2_gap_query_cosine':query_cosine,
            'R1_access':r1['access_ann'],'R2_access':r2['access_ann'],'Rstar_groups':pergroup,
            'Rstar_verdict':rs['verdict'],'Rstar_min_cover':rs['minimum_cover_size'],
            'n_padding_images_in_Rstar':sum(not v for c in m['capsules'] if c['capsule_id'] in rs['selected_ids'] for v in c['valid_mask'])})
    encoder.unload()
    padding_counts={method:sum(not valid for q in planned for c in snapshots[q['video_id']][0]['capsules']
                    if c['capsule_id'] in e2[q['question_id'],method]['selected_ids'] for valid in c['valid_mask'])
                    for method in ['R0','R1','R2','R*']}
    rstar_positions=[]
    for row in read_details:
        for g in row['Rstar_groups']:
            if g['covered_by_proxy']:
                lo,hi=g['interval'];rstar_positions.append((min(g['Rstar_selected_pts'])-lo)/(hi-lo))
    result={'analysis_kind':'post_hoc_diagnostic_not_preregistered_effect_test','n_questions':len(planned),
        'question_types':dict(Counter(questions[q['question_id']]['type'] for q in planned)),
        'E1_gold_group_duration_s':stats([g['duration_s'] for g in groups_out]),
        'E1_gold_group_max_frame_gap_s':stats([g['max_adjacent_gap_s'] for g in groups_out]),
        'E1_gold_groups_over_30s':sum(g['duration_s']>30 for g in groups_out),
        'E1_gold_groups_over_60s':sum(g['duration_s']>60 for g in groups_out),
        'E1_visual_category_matching_performed':False,'type_subgroups':question_out,
        'R1_R2_packet_overlap_counts':dict(Counter(overlaps)),
        'control_query_words':{method:stats([len(t.split()) for q in planned for t in e2[q['question_id'],method]['control']['queries']]) for method in ['R1','R2']},
        'R2_query_counts':dict(Counter(len(e2[q['question_id'],'R2']['control']['queries']) for q in planned)),
        'R2_coverage_contributing_extra_item_counts':dict(Counter(r['R2_coverage_contributing_extra_items'] for r in read_details)),
        'R2_two_gap_query_cosine':stats([r['R2_gap_query_cosine'] for r in read_details if r['R2_gap_query_cosine'] is not None]),
        'retrieval_redundancy':{method:{field:stats([r['redundancy'][method][field] for r in read_details])
            for field in ['mean_extra_pair_cosine','mean_extra_max_initial_cosine']} for method in ['R1','R2']},
        'Rstar_first_selected_frame_relative_position_in_covered_group':stats(rstar_positions),
        'padding_images_in_final_packets':padding_counts,
        'retrieval_only_alpha0_ablation':{'new_VLM_requests':0,'n_alpha02_recorded_match':sum(r['alpha02_matches_recorded'] for r in ablations),
            'n_extra_sets_changed':sum(r['alpha0_extra']!=r['recorded_selected_extra'] for r in ablations),
            'recorded_R2_n_access':sum(r['recorded_access_ann'] for r in ablations),
            'alpha0_n_access':sum(r['alpha0_access_ann'] for r in ablations),
            'n_coverage_gains':sum(r['alpha0_access_ann'] and not r['recorded_access_ann'] for r in ablations),
            'n_coverage_losses':sum(r['recorded_access_ann'] and not r['alpha0_access_ann'] for r in ablations),
            'limitation':'Only retrieval/annotation coverage recomputed; no new answer score and no claim of causal answer benefit.', 'rows':ablations},
        'gold_groups':groups_out,'reading_details':read_details}
    write(output/'representation_diagnostics.json',result)
    compact={k:v for k,v in result.items() if k not in ['gold_groups','reading_details']}
    compact['retrieval_only_alpha0_ablation']={k:v for k,v in compact['retrieval_only_alpha0_ablation'].items() if k!='rows'}
    write(output.parent/'representation_summary.json',compact)
    print(json.dumps(compact,ensure_ascii=False))


if __name__=='__main__':main()
