"""Validate actual audit artifacts and build a local review report."""
import collections
import datetime
import html
import importlib.metadata
import json
import platform
import subprocess
from pathlib import Path
from prepare_audit import OUT, SOURCE, dump, sha

RECORD=Path(__file__).resolve().parents[1]


def main():
    manifest=json.loads((OUT/'inspection_manifest.json').read_text())
    expanded=json.loads((OUT/'expanded_manifest.json').read_text())
    selection=json.loads((SOURCE/'run-001-inventory/selection_manifest.json').read_text())
    reviews=[json.loads(x) for x in (RECORD/'draft_review.jsonl').read_text().splitlines()]
    pilots=json.loads((RECORD/'pilot_audit.json').read_text())
    drafts=[json.loads(p.read_text()) for p in sorted((OUT/'revised_drafts').glob('*.json'))]
    assert len(drafts)==60 and {d['qid'] for d in drafts}==set(selection['dev_qids'])
    assert len(pilots)==12 and {p['qid'] for p in pilots}==set(selection['visual_pilot_qids'])
    assert len(reviews)==60 and len({r['qid'] for r in reviews})==60
    for path,expected in manifest['source_files'].items():
        assert sha(path)==expected, ('source changed',path)
    hash_checked=0
    for path in (SOURCE/'run-004-source-refinement/visual').glob('*.json'):
        for f in json.loads(path.read_text()).get('frames',[]):
            assert sha(f['path'])==f['sha256']
            hash_checked+=1
    assert hash_checked==600
    for case in expanded.values():
        assert sha(case['sheet'])==case['sheet_sha256']
        for f in case['frames']:
            assert sha(f['path'])==f['sha256']
            assert f['requested_time_s']-1e-6<=f['actual_pts_s']<f['requested_time_s']+0.06
    for case in manifest['sheets'].values():
        assert sha(case['path'])==case['sha256']
    for p in pilots:
        assert sha(p['source_file'])==p['source_file_sha256']
        assert not p['human_reviewed'] and not p['blind_review']
        sub=json.loads(Path(p['subtitle_evidence_file']).read_text())
        assert p['subtitle_ids']==[x['subtitle_id'] for x in sub['segments']]
        assert len(set(p['subtitle_ids']))==len(p['subtitle_ids'])
        for f in p['key_old_frames']+p['key_new_frames']:
            assert sha(f['path'])==f['sha256']
    for d in drafts:
        a=d['annotation'];fs=a['required_facts']
        assert not d['human_reviewed'] and not d['frozen_for_evaluation']
        assert [f['id'] for f in fs]==[f'F{i}' for i in range(1,len(fs)+1)]
        assert all(f['statement'].strip() for f in fs)
        if a['adaptation_status']=='unsuitable':assert not fs
        elif a['adaptation_status']!='needs_review':assert fs
        assert d['qid']==d['official_question']['qid']
        assert d['source_verified']==(d['audit']['source_review_status']=='source_supported_ai')
    checks={'checked_at':datetime.datetime.now().astimezone().isoformat(),'status':'passed',
      'checks':{'dev_qids_unchanged':60,'pilot_qids_unchanged':12,'source_annotation_files_unchanged':len(manifest['source_files']),
                'old_frame_hashes':hash_checked,'new_frame_hashes_and_pts':sum(len(v['frames']) for v in expanded.values()),
                'evidence_citations_resolve':True,'no_human_or_frozen_claims':True,'fact_ids_and_exclusion_schema':True},
      'limitation':'Integrity checks do not establish semantic truth, reviewer independence, or complete video coverage.'}
    dump(RECORD/'integrity_checks.json',checks)
    environment={'python':platform.python_version(),'host':platform.node(),'platform':platform.platform(),
                 'packages':{p:importlib.metadata.version(p) for p in ['av','Pillow','pysrt']},
                 'reviewer':'Codex active conversation; exact deployed model build unavailable',
                 'new_api_calls':0,'credentials_accessed':False,
                 'base_git_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                 'branch':subprocess.check_output(['git','branch','--show-current'],text=True).strip(),
                 'code_sha256':{p.name:sha(p) for p in sorted((RECORD/'code').glob('*.py'))},
                 'inspection_manifest_sha256':sha(OUT/'inspection_manifest.json'),
                 'expanded_manifest_sha256':sha(OUT/'expanded_manifest.json')}
    dump(RECORD/'provenance.json',environment)
    e=html.escape
    cards=[]; by_q={p['qid']:p for p in pilots}
    for d in drafts:
        q=d['qid'];a=d['annotation'];p=by_q.get(q)
        original=json.loads((SOURCE/'run-004-source-refinement/drafts'/f"{q.replace(':','__')}.json").read_text())['annotation']
        content=[f'<article id="{e(q)}"><h2>{e(q)} · {e(a["adaptation_status"])}</h2>',f'<p>{e(a["short_question"])}</p>',
                 '<p><b>仅为 AI 复核；未人工审核、未冻结。</b></p>',
                 '<h3>审核意见</h3><ul>'+''.join(f'<li>{e(x)}</li>' for x in d['audit']['notes'])+'</ul>',
                 f'<p>原参考：{e(d["official_question"]["reference_draft"])}</p>',
                 f'<p>当前候选参考：{e(a["reference_answer_draft"])}</p>',
                 '<h3>修正版必要事实</h3><ul>'+''.join(f'<li>{e(f["id"])}: {e(f["statement"])}</li>' for f in a['required_facts'])+'</ul>',
                 '<details><summary>旧版草稿</summary><pre>'+e(json.dumps(original,ensure_ascii=False,indent=2))+'</pre></details>']
        if p:
            content += [f'<h3>源证据：{e(p["result"])}</h3><p>{e(p["conclusion"])}</p><p>{e(p["limits"])}</p>',
                        f'<p><a href="{e(Path(p["subtitle_evidence_file"]).as_uri())}">原始字幕片段及 ID</a></p>']
            for label, field in [('旧包抽帧','inspected_old_sheet'),('补充抽帧','inspected_expanded_sheet')]:
                if p[field]:content += [f'<details><summary>{label}</summary><img src="{e(Path(p[field]).as_uri())}" alt="{label}"></details>']
            content += ['<details><summary>关键原帧</summary>']
            for f in p['key_old_frames']+p['key_new_frames']:
                content += [f'<p>{f["actual_pts_s"]:.3f}s · <a href="{e(Path(f["path"]).as_uri())}">原帧</a></p>']
            content += ['</details>']
        else:content += ['<p>本题未进行源视频事实核验。</p>']
        content+=['</article>'];cards.append(''.join(content))
    body='<!doctype html><meta charset="utf-8"><title>Video-MME AI 复核</title><style>body{max-width:1100px;margin:30px auto;font:16px/1.65 sans-serif;padding:0 16px}article{border-top:1px solid #bbb;padding:18px 0}img{max-width:100%}pre{white-space:pre-wrap}a{color:#145cb3}</style><h1>Video-MME AI 复核记录</h1><p>60 题文本检查；固定 12 题源证据/适配复核。8 题获源证据支持，2 题待定，2 题不适配。旧结果保留。此页面不构成人工金标。</p>'
    (OUT/'index.html').write_text(body+''.join(cards))
    print(json.dumps(checks,ensure_ascii=False))


if __name__=='__main__':
    main()
