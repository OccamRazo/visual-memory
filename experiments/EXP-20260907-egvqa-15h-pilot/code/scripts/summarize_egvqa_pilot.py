#!/usr/bin/env python3
"""Recompute tables, denominators, bootstrap intervals and honest acceptance status."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from egvqa_pilot.runner import read_json,write_json,rows
from egvqa_pilot.analysis import aggregate_e1,aggregate_e2,_score
from egvqa_pilot.protocol import BudgetLedger

def pct(x):return '—' if x is None else f'{100*x:.1f}%'
def difftext(d):
    if d['estimate'] is None:return '未计算'
    a,b=d['ci95'];return f"{100*d['estimate']:+.1f} pp，95% CI [{100*a:+.1f}, {100*b:+.1f}]"
def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--publish-dir');a=p.parse_args()
    run=Path(a.run);config=read_json(run/'resolved_config.json');manifest=read_json(run/'eval_manifest.json');planned=manifest['questions']
    check=read_json(run/'protocol_checks.json');audits=rows(run/'audit.jsonl')
    if any(r.get('kind') not in {'e1_joint','e2_gain'} or not r.get('reviewer_type') for r in audits):
        raise ValueError('Audit rows require an explicit kind and reviewer_type; never infer human review')
    # Only actual human responses can satisfy this gate. An AI review stays separate.
    calibration=read_json(run/'human_judge_calibration.json') if (run/'human_judge_calibration.json').exists() else None
    e1=aggregate_e1(planned,rows(run/'e1_pairs.jsonl'),audits=audits,protocol_checks=check['checks'],d0_calibration=calibration)
    e2=aggregate_e2(planned,rows(run/'e2_results.jsonl'),audits=audits,protocol_checks=check['checks'],d0_calibration=calibration)
    ledger=BudgetLedger.from_records(read_json(run/'ledger.json'));calls=rows(run/'calls.jsonl')
    ids=[r['request_id'] for r in calls]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate raw physical/logical call record')
    if set(ids)!=set(ledger.entries):raise ValueError('Call records do not match the persisted reservation ledger')
    phase_counts=Counter(e.phase for e in ledger.entries.values() if e.physical_request)
    physical_seconds=sum(r.get('physical_latency_s',r.get('latency_s',0)) for r in calls if not r.get('cache_hit'))
    now=datetime.now(timezone.utc);start=datetime.fromisoformat(config['timing']['started_at'])
    elapsed=(now-start).total_seconds()
    expected_e1=sum(q['m']+4 for q in planned);n1=len(rows(run/'e1_pairs.jsonl'));n2=len(rows(run/'e2_results.jsonl'))
    execution={'E1':{'recorded_conditions':n1,'expected_conditions':expected_e1,'all_conditions_recorded':n1==expected_e1},
               'E2':{'recorded_conditions':n2,'expected_conditions':4*len(planned),'all_conditions_recorded':n2==4*len(planned)}}
    for value in execution.values():
        value['registered_execution_status']='COMPLETE' if value['all_conditions_recorded'] else 'INCOMPLETE'
    summary={'generated_at':now.isoformat(),'scale':config['scale'],'execution':execution,'E1':e1,'E2':e2,
        'E3':{'engineering_status':'NOT_RUN','reason':'D0 human calibration and core scientific acceptance/grounding are not passed; optional entry conditions unmet.'},
        'cost':{**ledger.summary(),'physical_calls_by_phase':dict(phase_counts),'model_physical_latency_s':physical_seconds,
                'elapsed_wall_s':elapsed,'peak_cuda_reserved_bytes':max(r.get('peak_cuda_reserved_bytes',0) for r in calls),
                'peak_device_used_bytes_estimate':max(r.get('peak_device_used_bytes_estimate',0) for r in calls),
                'max_request_input_tokens':max(r['input_tokens'] for r in calls),
                'max_request_input_plus_reserved_output':max(r['input_tokens']+r['max_new_tokens'] for r in calls),
                'max_request_images':max(len(r.get('image_records',[])) for r in calls),
                'n_model_errors':sum(bool(r.get('error')) for r in calls),'n_truncated':sum(bool(r.get('truncated')) for r in calls)},
        'scientific_validity_passed':e1['scientific_validity_passed'] and e2['scientific_validity_passed'],
        'limitations':['A is a local same-model judge score; human calibration/grounding pending.',
            'Time-group coverage is a proxy and R* is a particular injection reference, not an upper bound.',
            'With <=4 evidence groups and six-capsule read capacity, Stored_ann equals Feasible_ann by definition.',
            'Sample is selected from official train for this pilot, not an official benchmark score.',
            'Landlock restricts normal-reader file reads; it is not a mount namespace or network sandbox.']}
    write_json(run/'summary.json',summary)
    compact={**summary,'E1':{k:v for k,v in e1.items() if k!='pairs'},'E2':{k:v for k,v in e2.items() if k!='results'}}
    output=Path(a.publish_dir) if a.publish_dir else run
    output.mkdir(parents=True,exist_ok=True)
    if output.resolve()!=run.resolve():write_json(output/'summary.json',compact)
    e2_index={(r['question_id'],r['method']):r for r in e2['results']}
    paired=[]
    for pair in e1['pairs']:
        methods={}
        for method in ['R0','R1','R2','R*']:
            r=e2_index[pair['question_id'],method]
            methods[method]={'A':_score(r),**{k:r.get(k) for k in ['status','verdict','access_ann','feasible_ann','stored_ann','citations_legal','logical_tokens','logical_calls']}}
        paired.append({'question_id':pair['question_id'],'video_id':pair['video_id'],
            'E1':{k:pair[k] for k in ['num_gold_groups','valid_pair','invalid_reasons','scores','delta_key','delta_irrel','D','full_minus_blind','any_uncertain']},'E2':methods})
    write_json(output/'paired_scores.json',{'score_label':e1['score_label'],'source_run':str(run),
        'bootstrap':{'unit':'video','n_resamples':2000,'seed':43},'questions':paired})
    n=len(planned);v=manifest['n_videos'];cost=summary['cost']
    lines=['# EG-VQA 单卡验证结果','',f"冻结规模：{config['scale']}，{v} 视频/{n} 题。全部预定条件的执行或终止记录：E1 {n1}/{expected_e1}，E2 {n2}/{4*n}。",'',
        '**这些是未经人工校准的本地 judge 探索结果；不能记作科学验收通过。** E3 未启动。','',
        '## E1：联合证据干预','',f"机械构造与执行完整的配对题：{e1['n_valid_pairs']}/{n}，覆盖 {e1['n_valid_videos']} 个视频。语义独立性、替代路径及视觉 grounding 仍待人工审核。",'',
        '| 条件 | 正确 / 计划条件数 | 计划分母准确率 | uncertain |','|---|---:|---:|---:|']
    for name in ['Full','Key-1','Key-2','Key-3','Key-4','Irrel-1','Irrel-2','Blind']:
        if name in e1['condition_table']:
            t=e1['condition_table'][name];lines.append(f"| {name} | {t['n_correct']}/{t['n_planned']} | {pct(t['accuracy'])} | {t['n_uncertain']} |")
    lines+=['',f"配对 Full 准确率 {pct(e1['paired_full_accuracy'])}；Full−Blind：{difftext(e1['full_minus_blind'])}。",'',
        f"预注册主差值 D：{difftext(e1['primary_D'])}。自动联合候选 {e1['n_automatic_candidates']} 题；人工确认 {e1['n_human_confirmed']} 题。原计划分母始终保留为 {n}，各 Key 条件只存在于相应组数的题目中。",'',
        '## E2：固定快照读取','',f"Feasible_ann：{e2['n_feasible_ann']}/{n} 题，{e2['n_feasible_videos']} 视频。本轮 m≤4，故 Stored_ann 与 Feasible_ann 相同。",'',
        '| 方法 | 正确 / 计划题数 | A | 时间组完整覆盖 | 可行子集覆盖 | J_ann（代理） | 平均逻辑 token |','|---|---:|---:|---:|---:|---:|---:|']
    for name in ['R0','R1','R2','R*']:
        t=e2['method_table'][name];tokens=t['mean_logical_tokens'];token_text='—' if tokens is None else f'{tokens:.1f}'
        lines.append(f"| {name} | {t['n_correct']}/{n} | {pct(t['accuracy'])} | {t['n_access_ann']}/{n} | {pct(t['access_ann_feasible'])} | {round(t['J_ann']*n)}/{n} | {token_text} |")
    lines+=['',f"主比较 R2−R1：{difftext(e2['primary_R2_minus_R1'])}，净增 {e2['primary_R2_minus_R1']['net_gain_questions']} 题；正向变化涉及 {e2['primary_R2_minus_R1']['n_gain_videos']} 个视频。",'',
        f"可行子集 R*−R1：{difftext(e2['Rstar_minus_R1_feasible'])}；R2−R1 时间覆盖差：{difftext(e2['access_R2_minus_R1_feasible'])}。",'',
        f"R1/R2 平均累计逻辑 token 差为 {pct(e2['relative_mean_logical_token_gap'])}（分母取较小均值，门槛5%）。R*只取该快照的存活载荷，是具体标注注入参考，不是性能上界。J_ann 是答对、时间组覆盖与引用合法的交集，仍不证明实际视觉 grounding。",'',
        '### 失败分解与输出可靠性','',
        '下列归因按冻结规则互斥分类，先检查已知路径是否存活，再看回答。答对但未存齐已知路径的题仍计入“已知路径未存下”，所以“其余 A=1”栏不等于上表 A 的正确数。“已覆盖但仍答错”不能直接区分消费者、帧表示与注入策略。', '',
        '| 类别 | R0 | R1 | R2 | R* |','|---|---:|---:|---:|---:|']
    labels={'frontend_or_data_not_captured':'完整前端/标注覆盖不足',
        'known_path_not_stored':'已知路径未存下', 'read_budget_infeasible':'已存但读取预算不可行',
        'method_execution_or_parse_failure':'方法执行/解析失败',
        'observed_repairable_read_gap':'观察到可修复读取缺口', 'consumer_representation_or_injection_unresolved':'消费者/表示/注入仍待区分',
        'success':'其余 A=1','insufficient_diagnostic_information':'诊断信息不足'}
    categories=sorted({k for t in e2['method_table'].values() for k in t['failure_categories']})
    for category in categories:
        counts=[e2['method_table'][m]['failure_categories'].get(category,0) for m in ['R0','R1','R2','R*']]
        lines.append('| '+labels.get(category,category)+' | '+' | '.join(map(str,counts))+' |')
    lines+=['','| 方法 | 引用合法 / 计划题数 | uncertain | 控制回退 | 平均逻辑推理耗时 |','|---|---:|---:|---:|---:|']
    for method,t in e2['method_table'].items():
        latency=t['mean_latency_s_known'];latency_text='—' if latency is None else f'{latency:.2f}s'
        lines.append(f"| {method} | {t['n_legal_citations']}/{n} | {t['n_uncertain']} | {t['control_fallback_count']} | {latency_text} |")
    lines+=['',f"排除 uncertain 的敏感性分析：E1 D {difftext(e1['sensitivity_excluding_uncertain_D'])}；E2 R2−R1 {difftext(e2['sensitivity_R2_minus_R1_excluding_uncertain'])}。主表仍保留这些未成功项。",'',
        '## 成本、检查与判定','',f"共 {cost['physical_calls']} 次物理模型请求、{cost['logical_calls']} 次逻辑调用，{cost['physical_tokens']:,} 物理 token；离线 judge 的逻辑 token 单列为 {cost['judge_logical_tokens']:,}。核心/全轮额度为 1400/1800，预算违规 {cost['budget_violations']}，未结请求 {cost['pending_requests']}。",'',
        f"模型请求物理耗时累计 {physical_seconds/60:.1f} 分钟；自T0至报告生成 {elapsed/3600:.2f} 小时。峰值 CUDA reserved 为 {cost['peak_cuda_reserved_bytes']/2**30:.2f} GiB。所有真实时间与历史D0格式错误均保留在原始账本中。",'',
        f"真实快照检查 {check['real_snapshots_checked']} 个；完整自动化测试记录见run/tests.log。D0初始50次、两轮各40次格式复核及更新后的1次边界检查分别保留。人工judge校准、联合依赖和增益grounding审核均未完成；不能以自动候选替代。另行 AI 文本盲审与本地 judge 一致 26/32，有 6 处分歧，原评分未改；该结果不是人工校准，详见 ai_review_summary.json。",'',
        f"注册的 smoke 执行状态：E1 {execution['E1']['registered_execution_status']}，E2 {execution['E2']['registered_execution_status']}；按原标准规模验收的状态仍是 E1 {e1['engineering_status']}，E2 {e2['engineering_status']}。两类状态的分母与用途不同。",'',
        f"E1研究判断：{e1['research_judgment']}；E2研究判断：{e2['research_judgment']}。标准规模/有效配对、消费者入口、联合信号、读取空间、组合改善、成本公平和人工审核的每项门槛均可在summary.json中重算。",'',
        '唯一下一步：先完成预留的人工盲审与失败案例核验，再决定是否修正表示/读取规则或扩大独立样本；本轮不启动学习写入器或E3。','',
        '## 复现与本地原始产物','',f"原始run：`{run}`。配置与输入包、独立快照、逐调用输出、逻辑/物理费用、E1/E2条件结果、匿名judge映射均留在本设备。",'',
        '```bash',f'OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 .venv/bin/python scripts/summarize_egvqa_pilot.py --run {run} --publish-dir {output}','```','']
    (output/'results.md').write_text('\n'.join(lines))
    print(json.dumps({'physical_calls':cost['physical_calls'],'E1_valid_pairs':e1['n_valid_pairs'],'D':e1['primary_D']['estimate'],
        'E2_accuracy':{k:v['accuracy'] for k,v in e2['method_table'].items()},'R2_minus_R1':e2['primary_R2_minus_R1']['estimate'],
        'scientific_validity_passed':summary['scientific_validity_passed']},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
