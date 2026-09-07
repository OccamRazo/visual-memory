#!/usr/bin/env python3
"""Validate fresh-context answers and export anonymous, text-deduplicated review."""
import argparse
import hashlib
import json
from pathlib import Path
import random

def read(p): return json.loads(p.read_text())
def write(p,value): p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def key(question,reference,answer):
    return 'a'+hashlib.sha256(json.dumps([question,reference,answer],ensure_ascii=False).encode()).hexdigest()[:16]

def load_answers(run):
    manifest=read(run/'packet_manifest.json');answers={};checks=[]
    for packet in manifest['packets']:
        pid=packet['packet_id'];input_path=Path(packet['input_path']);item=read(input_path)
        assert hashlib.sha256(input_path.read_bytes()).hexdigest()==packet['input_sha256']
        for name,expected in packet['pages_sha256'].items():
            assert hashlib.sha256((input_path.parent/name).read_bytes()).hexdigest()==expected
        r=read(run/'responses'/f'{pid}.json')
        assert r['packet_id']==pid and r['reviewer_type']=='AI'
        assert r['reference_seen'] is False and r['other_packets_seen'] is False
        assert isinstance(r['answer'],str) and len(r['answer'].split())<=30
        assert isinstance(r['citations'],list) and set(r['citations'])<=set(item['allowed_citation_ids'])
        assert len(set(r['citations']))<=6
        assert r['viewed_image_paths']==item['image_pages']
        answers[pid]=r
        checks.append({'packet_id':pid,'n_images':item['n_images'],'word_count':len(r['answer'].split()),
                       'answer_sha256':hashlib.sha256((run/'responses'/f'{pid}.json').read_bytes()).hexdigest()})
    records=[]
    for original in read(run/'private_condition_mapping.json'):
        answer=answers[original['packet_id']]
        records.append({**original,'new_answer':answer['answer'],'new_citations':answer['citations'],
                        'new_reviewer_type':'AI','human_review_status':'pending',
                        'old_judge_item_id':key(original['question'],original['reference'],original['original_answer']),
                        'new_judge_item_id':key(original['question'],original['reference'],answer['answer'])})
    write(run/'response_checks.json',{'status':'PASS','unique_packets':len(answers),'logical_conditions':len(records),
                                     'fresh_context_declarations_checked':True,'OS_isolation_claimed':False,'packets':checks})
    return records

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--stage',choices=['prepare-judge','report'],required=True)
    a=p.parse_args();run=Path(a.run);records=load_answers(run)
    if a.stage=='prepare-judge':
        items={}
        for r in records:
            for which in ['old','new']:
                answer=r['original_answer'] if which=='old' else r['new_answer']
                if not answer.strip(): continue  # Original explicit abstentions stay zero.
                iid=r[f'{which}_judge_item_id']
                item={'id':iid,'question':r['question'],'reference':r['reference'],'prediction':answer}
                if iid in items: assert items[iid]==item
                items[iid]=item
        for reviewer,seed in [('A',43),('B',44)]:
            path=run/f'blind_text_review_{reviewer}.json'
            if path.exists():raise FileExistsError(path)
            ordered=sorted(items.values(),key=lambda x:x['id']);random.Random(seed).shuffle(ordered)
            write(path,{'reviewer_label':reviewer,'ordering_seed':seed,'items':ordered})
        write(run/'reanswers_unscored.json',records)
        print(json.dumps({'unique_text_items':len(items),'logical_conditions':len(records),'new_unique_packets':read(run/'packet_manifest.json')['unique_packets']}))
        return
    reviews={}
    for label in ['A','B']:
        source=read(run/f'blind_text_review_{label}.json');data=read(run/f'text_review_{label}.json')
        results=data['results'];index={r['id']:r for r in results}
        assert len(index)==len(results) and set(index)=={r['id'] for r in source['items']}
        assert data['reviewer_type']=='AI'
        assert all(r['verdict'] in ['correct','incorrect','uncertain'] for r in results)
        assert all(isinstance(r['reason'],str) and len(r['reason'].split())<=8 for r in results)
        reviews[label]=index
    for r in records:
        for which in ['old','new']:
            answer=r['original_answer'] if which=='old' else r['new_answer']
            judgments={label:index[r[f'{which}_judge_item_id']] if answer.strip()
                       else {'verdict':'incorrect','reason':'Explicit empty answer abstention'} for label,index in reviews.items()}
            r[f'{which}_text_reviews']=judgments
            r[f'{which}_reviewers_agree']=judgments['A']['verdict']==judgments['B']['verdict']
    write(run/'reanswers_scored.json',records)
    write(run.parent/'reanswers.json',{'scope':'four post-hoc selected questions, all frozen E1/E2 final packets',
        'not_same_model_or_token_budget':True,'human_calibration':'NOT_RUN','records':records})
    condition_order={'Full':0,**{f'Key-{i}':i for i in range(1,5)},'Irrel-1':5,'Irrel-2':6,'Blind':7,'R0':8,'R1':9,'R2':10,'R*':11}
    escape=lambda s:str(s).replace('|','\\|').replace('\n',' ')
    lines=['# 四题各设置的独立 AI 重答','',
        '每个不同输入使用新上下文，只展示原问题及原尺寸帧包。参考、原预测及条件名在作答时隐藏；原检索选择不变。相同输入共用一个答案：44个逻辑条件，42次独立视觉/无图作答。', '',
        '下表“复核”是两名新上下文AI文本审核者的 A/B 判定：✓正确、×错误、?参考有歧义。原答案与新答案混合匿名、同题同文只判一次。审核不是人工校准，表格不估计总体正确率。模型、展示接口和推理预算与原Qwen不同。','']
    symbol={'correct':'✓','incorrect':'×','uncertain':'?'}
    for case in read(run/'selection_manifest.json')['cases']:
        subset=sorted([r for r in records if r['question_id']==case['question_id']],key=lambda r:condition_order[r['condition']])
        r=subset[0];lines += [f"## {r['question_id']}",'',f"选择层：`{case['stratum']}`。",'',f"问题：{r['question']}",'',f"参考：{r['reference']}",'',
            '| 条件 | 独立重答（英文原文） | 引用ID | 新答复核 A/B | 原答复核 A/B |','|---|---|---|---|---|']
        for r in subset:
            verdict=lambda w:'/'.join(symbol[r[f'{w}_text_reviews'][j]['verdict']] for j in ['A','B'])
            lines.append(f"| {r['phase']} {r['condition']} | {escape(r['new_answer'])} | {escape(', '.join(r['new_citations']))} | {verdict('new')} | {verdict('old')} |")
        lines.append('')
    (run.parent/'reanswers.md').write_text('\n'.join(lines))
    items=set(reviews['A']);agreement=sum(reviews['A'][i]['verdict']==reviews['B'][i]['verdict'] for i in items)
    brief={'logical_conditions':len(records),'unique_packets':read(run/'packet_manifest.json')['unique_packets'],
           'unique_text_items':len(items),'text_reviewer_agreement':agreement,
           'disagreement_ids':[i for i in sorted(items) if reviews['A'][i]['verdict']!=reviews['B'][i]['verdict']],
           'human_calibration':'NOT_RUN','population_accuracy_claimed':False,
           'cases':{case['question_id']:{'n_conditions':sum(r['question_id']==case['question_id'] for r in records),
                   'new_correct_by_reviewer':{j:sum(r['question_id']==case['question_id'] and r['new_text_reviews'][j]['verdict']=='correct' for r in records) for j in ['A','B']}}
                    for case in read(run/'selection_manifest.json')['cases']}}
    write(run.parent/'reanswer_summary.json',brief);print(json.dumps(brief,ensure_ascii=False))

if __name__=='__main__':main()
