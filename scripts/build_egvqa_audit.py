#!/usr/bin/env python3
"""Make local, traceable audit pages. This exports material, never human verdicts."""
import argparse
import base64
import hashlib
from html import escape
import io
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from PIL import Image
from egvqa_pilot.runner import read_json,rows,write_json

def thumbnail(pixel):
    stream=io.BytesIO();Image.fromarray(pixel).save(stream,format='JPEG',quality=90)
    return 'data:image/jpeg;base64,'+base64.b64encode(stream.getvalue()).decode()
def packet_html(capsules,pixels,id_field):
    html=[]
    for c,images in zip(capsules,pixels):
        html.append('<div class="group"><b>'+escape(c[id_field])+'</b><div class="frames">')
        for t,pixel,valid in zip(c['pts'],images,c['valid_mask']):
            suffix='' if valid else ' — 填充帧，不计新证据'
            html.append(f'<figure><img src="{thumbnail(pixel)}"><figcaption>PTS {t:.6f}s{suffix}</figcaption></figure>')
        html.append('</div></div>')
    return ''.join(html)
def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--dataset',default='data/downloads/egvqa-pilot');p.add_argument('--output');a=p.parse_args()
    run=Path(a.run);summary=read_json(run/'summary.json');out=Path(a.output) if a.output else run/'audit_pages'
    # Refuse to overwrite pages or keys that may already carry a human's notes.
    out.mkdir(parents=True,exist_ok=False)
    questions={q['question_id']:{**q,'video_id':v['video_id']} for v in read_json(Path(a.dataset)/'annotations/eval.json') for q in v['questions']}
    e1rows={};e2rows={}
    for r in rows(run/'e1_pairs.jsonl'):e1rows.setdefault(r['question_id'],[]).append(r)
    for r in rows(run/'e2_results.jsonl'):e2rows.setdefault(r['question_id'],{})[r['method']]=r
    css='<style>body{font:16px system-ui;max-width:1100px;margin:28px auto;padding:12px}article{border-top:2px solid #888;margin-top:30px}.frames{display:flex;flex-wrap:wrap}figure{margin:5px}img{width:224px;height:224px}figcaption{font:12px monospace}.group{padding:8px;background:#f5f5f5;margin:8px 0}table{border-collapse:collapse}td,th{padding:8px;border:1px solid #bbb}pre{white-space:pre-wrap}</style>'
    head='<meta charset="utf-8">'+css
    e1=['<h1>E1 人工审核候选</h1><p>本页不代表已完成审核。请检查独立必要事实、画面可辨识性、替代证据、参考答案与引用合法性；不得把审核意见回灌本轮模型。</p>']
    # Automatic candidates get first priority; if none, export deterministic failure
    # examples for representation diagnostics, explicitly separated from confirmation.
    queue=summary['E1']['audit_queue'];case_kind='automatic_joint_candidate'
    if not queue:
        ids=[p['question_id'] for p in summary['E1']['pairs'] if p['valid_pair']]
        queue=sorted(ids,key=lambda q:hashlib.sha256(f'43:{q}'.encode()).hexdigest())[:4];case_kind='diagnostic_sample_not_joint_candidate'
    for qid in queue:
        q=questions[qid];root=run/'prepared'/q['video_id']/'e1'/qid;m=read_json(root/'manifest.json')
        with np.load(root/'pixels.npz',allow_pickle=False) as f:pixels=f['images']
        e1+=['<article><h2>'+escape(qid)+'</h2><p>'+escape(q['question'])+'</p><p>参考答案：'+escape(q['answer'])+'</p>',
             '<p>案例类型：'+case_kind+'</p>',packet_html(m['groups'],pixels,'group_id'),'<table><tr><th>条件</th><th>输入ID</th><th>答案</th><th>引用</th><th>执行状态 / 解析 / 截断</th><th>本地judge</th></tr>']
        for r in sorted(e1rows[qid],key=lambda r:r['condition']):
            status={k:r.get(k) for k in ['status','parse_ok','truncated','citations_legal']}
            e1.append('<tr>'+''.join('<td>'+escape(str(x))+'</td>' for x in [r['condition'],r.get('selected_ids',[]),r.get('answer',''),r.get('citations',[]),status,r['verdict']])+'</tr>')
        e1.append('</table><p>人工意见：待填写；审核者与时间：待填写。</p></article>')
    (out/'e1.html').write_text(head+''.join(e1))
    e2=['<h1>E2 增益案例盲审</h1><p>每题的A/B排列固定hash随机化。本页隐藏方法名和自动分数；请先判断新增真实证据能否解释答案差异，再打开独立映射文件。</p>'];keys=[]
    for qid in summary['E2']['audit_queue']:
        q=questions[qid];root=run/'prepared'/q['video_id']/'snapshot';m=read_json(root/'manifest.json');byid={c['capsule_id']:(j,c) for j,c in enumerate(m['capsules'])}
        with np.load(root/'pixels.npz',allow_pickle=False) as f:pixels=f['images']
        methods=['R1','R2']
        if int(hashlib.sha256(f'43:{qid}'.encode()).hexdigest(),16)%2:methods.reverse()
        e2.append('<article><h2>'+escape(qid)+'</h2><p>'+escape(q['question'])+'</p><p>参考答案：'+escape(q['answer'])+'</p>')
        for label,method in zip(['A','B'],methods):
            r=e2rows[qid][method];ids=r.get('selected_ids',[]);selected=[byid[i][1] for i in ids]
            status={k:r.get(k) for k in ['status','parse_ok','truncated','citations_legal']}
            e2+=['<h3>输入包 '+label+'</h3><p>执行状态：'+escape(str(status))+'</p><p>答案：'+escape(r.get('answer',''))+'</p><p>引用：'+escape(str(r.get('citations',[])))+'</p>',packet_html(selected,pixels[[byid[i][0] for i in ids]],'capsule_id') if ids else '<p>该条件未形成合法输入包；不能据此确认新增证据解释了改善。</p>']
            keys.append({'question_id':qid,'anonymous_packet':label,'method':method,'verdict':r['verdict']})
        e2.append('<p>人工意见：待填写；新增证据是否能解释差异：待填写。</p></article>')
    if not summary['E2']['audit_queue']:e2.append('<p>本轮没有 R2 正确而 R1 错误的自动增益案例。</p>')
    (out/'e2_blind.html').write_text(head+''.join(e2));write_json(out/'e2_blinding_key.json',keys)
    write_json(out/'audit_queue.json',{'e1':queue,'e1_case_kind':case_kind,'e2':summary['E2']['audit_queue'],'human_review_status':'pending','image_source':'sealed snapshot or privileged E1 pixel payload; display JPEG90 only, numeric results unchanged'})
    (out/'README.md').write_text('本目录仅导出待审材料，没有生成任何人工结论。\n\n请将实际完成的人工审核单独保存到 run/audit.jsonl；每行必须显式包含 kind（e1_joint 或 e2_gain）、question_id、reviewer_type、审核者和时间。AI 审核不得标为 human。具体布尔字段见 src/egvqa_pilot/analysis.py。D0 的 32 条校准另存 human_judge_calibration.json，不与案例审核混用。\n\n重复生成时请用 --output 指定一个新目录；脚本拒绝覆盖既有页面和盲审映射。\n')
    print(json.dumps({'e1_cases':len(queue),'e2_cases':len(summary['E2']['audit_queue']),'path':str(out)},ensure_ascii=False))
if __name__=='__main__':main()
