"""Export exactly 60 approved records; verify provenance before publication locally."""
import collections
import datetime
import html
import json
import os
import re
import hashlib
import zipfile
import pysrt
from pathlib import Path
from collect import OUT, REPO, SOURCE, DATA, canonical, dump, jl, safe, sha


def read(p): return json.loads(Path(p).read_text())


def prior_package(d):
    old=d['prior_record']; raw=read(old['source_file'])
    assert sha(old['source_file'])==old['source_file_sha256']
    frames=[];seen=set()
    for f in raw['frames']+old['key_new_frames']:
        if f['path'] in seen:continue
        seen.add(f['path']);frames.append(dict(f,frame_id=f'P{len(frames)+1:03}'))
    sub=read(old['subtitle_evidence_file'])
    package={'qid':d['qid'],'video_id':d['video_id'],'frames':frames,'subtitles':sub['segments'],
        'subtitle_member_sha256':sub['subtitle_member_sha256'],'generated_captions_in_evidence':False,
        'source_video':str(DATA/'data'/f"{d['video_id']}.mp4"),
        'intervals':[{'start_s':a,'end_s':b} for a,b in old['subtitle_windows']],
        'provenance':'Existing source audit; original frame package plus separately inspected expansion and original subtitle windows. Context frames are not all individually cited.',
        'prior_audit_file':d['prior_audit_file'],'prior_audit_sha256':d['prior_audit_sha256']}
    path=OUT/'final/prior_packages'/f"{safe(d['qid'])}.json";dump(path,package)
    return path,package


# Conservative fact-to-window mappings transcribed from the existing adjudication.
PRIOR_WINDOWS={
 'videomme:660-2':{'F1':[(1480,1501)],'F2':[(1480,1517)]},
 'videomme:674-2':{'F1':[(78,145),(145,220)],'F2':[(145,220),(339,410)],'F3':[(339,410),(484,510)]},
 'videomme:821-1':{'F1':[(106,150),(211,241)],'F2':[(211,241),(648,711)],'F3':[(648,711),(834,1001)]},
 'videomme:845-2':{'F1':[(1234,1262)]},
 'videomme:885-2':{'F1':[(196,215)]},
}


def build_prior(d):
    a=read(d['draft_file'])['annotation'];path,p=prior_package(d)
    facts=[{'id':f['id'],'statement':f['statement']} for f in a['required_facts']]
    supports=[]
    for f in facts:
        windows=PRIOR_WINDOWS.get(d['qid'],{}).get(f['id'])
        keypaths={x['path'] for x in d['prior_record']['key_old_frames']+d['prior_record']['key_new_frames']}
        fs=[x['frame_id'] for x in p['frames'] if x['path'] in keypaths and (windows is None or any(lo<=x['actual_pts_s']<=hi for lo,hi in windows))]
        ss=[x['subtitle_id'] for x in p['subtitles'] if windows is None or any(x['start_s']<hi and x['end_s']>lo for lo,hi in windows)]
        supports.append({'fact_id':f['id'],'status':'supported','frame_ids':fs,'subtitle_ids':ss,
            'source_observation':d['reason'],'mapping_kind':'Window mapping of preserved prior AI adjudication; not a fresh blind audit.'})
    return {'qid':d['qid'],'video_id':d['video_id'],'question':a['short_question'],
        'reference_answer':a['reference_answer_draft'],'required_facts':facts,
        'task_labels':{'task_tags':a.get('task_type',[]),'scope':a.get('evidence_scope'),'modality':a.get('modality')},
        'fact_support':supports,'package_file':str(path),'package_sha256':sha(path),'origin':'prior_pilot',
        'review_file':d['prior_audit_file'],'review_sha256':d['prior_audit_sha256'],
        'review_note':d['reason'],'review_kind':'reused_prior_source_audit','human_reviewed':False}


def build_new(d,review,overrides):
    a=d['nomination'];facts=[{'id':f['id'],'statement':f['statement']} for f in a['required_facts']]
    changes=overrides.get(d['qid'],{})
    if 'required_fact_ids' in changes:facts=[f for f in facts if f['id'] in changes['required_fact_ids']]
    for f in facts:
        if f['id'] in changes.get('fact_statements',{}):f['statement']=changes['fact_statements'][f['id']]
    supports=json.loads(json.dumps(d['grounded_audit']['facts']))
    supports=[s for s in supports if s['fact_id'] in {f['id'] for f in facts}]
    for support in supports:
        support.update(changes.get('support_overrides',{}).get(support['fact_id'],{}))
    return {'qid':d['qid'],'video_id':d['video_id'],'question':changes.get('question',a['short_question']),
        'reference_answer':changes.get('reference_answer',a['reference_answer']),'required_facts':facts,
        'task_labels':{'task_tags':a.get('task_tags',[]),'scope':a.get('scope'),'modality':a.get('modality')},
        'fact_support':supports,'package_file':review['package_file'],'package_sha256':review['package_sha256'],
        'origin':'remaining48' if d['qid'] in read(OUT/'sampling_manifest.json')['remaining48'] else 'replacement',
        'review_file':str(OUT/'codex_reviews'/f"{safe(d['qid'])}.json"),
        'review_sha256':sha(OUT/'codex_reviews'/f"{safe(d['qid'])}.json"),'review_note':review['note'],
        'review_kind':'fresh_grounded_model_audit_and_Codex_source_review','human_reviewed':False,
        'result_file':str(OUT/'results'/f"{safe(d['qid'])}.json"),'result_sha256':sha(OUT/'results'/f"{safe(d['qid'])}.json"),
        'rubric_cleanup':changes or None,'source_supplement_reviewed':review.get('source_supplement_reviewed',False),
        'original_model_package_file':d['package_file'],'original_model_package_sha256':d['package_sha256']}


def verify(rows,results,manifest):
    assert len(rows)==60 and len({r['qid'] for r in rows})==60
    assert set(manifest['remaining48'])<=set(results)
    assert not any(r['status']=='processing_failed' for r in results.values()), 'Unresolved technical failures'
    for r in results.values():
        if r['status']=='source_complete_candidate':
            decision=read(OUT/'codex_reviews'/f"{safe(r['qid'])}.json")
            assert decision['decision'] in {'accept','reject'}, 'Candidate not dispositioned'
    checked_frames=0;checked_subtitles=0;source_subtitles={}
    with zipfile.ZipFile(DATA/'subtitle.zip') as archive:
        for r in rows:
            p=read(r['package_file']);vid=r['video_id']
            if not p['subtitles'] or vid in source_subtitles:continue
            raw=archive.read(f'subtitle/{vid}.srt')
            source_subtitles[vid]=(hashlib.sha256(raw).hexdigest(),pysrt.from_string(raw.decode('utf-8-sig',errors='replace')))
    for r in rows:
        assert sha(r['package_file'])==r['package_sha256']
        assert sha(r['review_file'])==r['review_sha256']
        p=read(r['package_file']);assert p['qid']==r['qid'] and p['video_id']==r['video_id']
        assert p['generated_captions_in_evidence'] is False
        assert Path(p['source_video']).exists()
        fs={f['frame_id']:f for f in p['frames']};ss={s['subtitle_id']:s for s in p['subtitles']}
        assert len(fs)==len(p['frames']) and len(ss)==len(p['subtitles'])
        for f in fs.values():assert sha(f['path'])==f['sha256'];checked_frames+=1
        for s in ss.values():
            assert 0<=s['start_s']<s['end_s']
            digest,originals=source_subtitles[r['video_id']]
            assert digest==p['subtitle_member_sha256']
            original=originals[int(s['subtitle_id'].split(':')[-1].lstrip('S'))]
            clean=lambda text:re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]*>','',text))).strip()
            assert abs(s['start_s']-original.start.ordinal/1000)<.002 and abs(s['end_s']-original.end.ordinal/1000)<.002
            assert clean(s['text'])==clean(original.text)
            checked_subtitles+=1
        assert {f['id'] for f in r['required_facts']}=={f['fact_id'] for f in r['fact_support']}
        for f in r['fact_support']:
            assert f['status']=='supported'
            assert set(f.get('frame_ids',[]))<=set(fs) and set(f.get('subtitle_ids',[]))<=set(ss)
            assert f.get('frame_ids') or f.get('subtitle_ids')
        if r['origin']!='prior_pilot':
            review=read(r['review_file']);assert review['decision']=='accept'
            assert review['result_sha256']==sha(r['result_file'])
            assert not results[r['qid']]['integrity_errors']
    observer_requests=0
    for f in (OUT/'calls').glob('*/observe/*/request.json'):
        request=read(f)['payload']['messages'][1]['content'];header=json.loads(request[0]['text'])
        assert not {'reference_answer','required_facts','options','official_reference'} & set(header)
        observer_requests+=1
    assert sha(SOURCE/'run-001-inventory/selection_manifest.json')==manifest['original_selection_sha256']
    return {'passed':True,'verified_at':datetime.datetime.now().astimezone().isoformat(),
        'unique_complete_questions':60,'remaining48_dispositioned':48,'frame_hashes_checked':checked_frames,
        'subtitle_rows_checked':checked_subtitles,'blind_observer_requests_checked':observer_requests,
        'checks':['All accepted records have traceable reviewed source packages and supported citations.',
                  'Original selection manifest unchanged; no unresolved technical failures.',
                  'Blind observer payload headers contain no answer/options/fact rubric.',
                  'Generated captions excluded from all final evidence packages.',
                  'All final subtitle timestamps/texts and member hashes match the original dataset SRT archive.'],
        'limits':'Integrity checks do not independently prove semantic correctness. Human calibration not run.'}


def main():
    manifest=read(OUT/'sampling_manifest.json')
    priors={d['qid']:d for d in [read(p) for p in (OUT/'prior').glob('*.json')]}
    results={d['qid']:d for d in [read(p) for p in (OUT/'results').glob('*.json')]}
    reviews={d['qid']:d for d in [read(p) for p in (OUT/'codex_reviews').glob('*.json')]}
    overrides=read(REPO/'rubric_overrides.json')
    order=sorted(priors)+manifest['remaining48']+manifest['replacement_order']
    rows=[]
    for q in order:
        if q in priors and priors[q]['status']=='prior_source_complete':rows.append(build_prior(priors[q]))
        elif q in results and q in reviews and reviews[q]['decision']=='accept':rows.append(build_new(results[q],reviews[q],overrides))
        if len(rows)==60:break
    check=verify(rows,results,manifest);accepted={r['qid'] for r in rows}
    questions={q['qid']:q for q in jl(SOURCE/'run-001-inventory/questions.jsonl')}
    for r in rows:
        r.update(original=questions[r['qid']],evidence_status='complete_at_required_fact_granularity',
            scoring={'rule':'Semantic entailment of each minimal fact; reject contradictions. Normalize fact scores within each question. Task labels are metadata and never scoring requirements.',
                     'acceptable_variants_policy':'Unverified generated variants omitted; accept only semantic equivalents preserving specificity.',
                     'answer_correctness_used_for_admission':False},reference_visible_source_audit=True)
        r['task_labels'].update(official_task_type=questions[r['qid']]['official_task_type'],
            generated_tags_status='Metadata only; not scoring facts or human-calibrated labels')
    final=OUT/'final';final.mkdir(exist_ok=True)
    (final/'evidence60.jsonl').write_text(''.join(canonical(r)+'\n' for r in rows))
    # Keep model-facing questions separate from evaluator-only labels and gold.
    (final/'questions.jsonl').write_text(''.join(canonical({'qid':r['qid'],'history_id':'videomme:'+r['video_id'],'question':r['question']})+'\n' for r in rows))
    (final/'scoring_facts.jsonl').write_text(''.join(canonical({k:r[k] for k in ['qid','reference_answer','required_facts','scoring']})+'\n' for r in rows))
    (final/'task_labels.jsonl').write_text(''.join(canonical({'qid':r['qid'],**r['task_labels']})+'\n' for r in rows))
    (final/'evidence_index.jsonl').write_text(''.join(canonical({k:r[k] for k in ['qid','fact_support','package_file','package_sha256','review_file','review_sha256','review_kind']})+'\n' for r in rows))
    dispositions=[]
    for q in order:
        d=priors.get(q) or results.get(q)
        if not d:continue
        review=reviews.get(q)
        disposition='accepted' if q in accepted else ('source_complete_reserve' if review and review['decision']=='accept' else ('skipped_codex_review' if review and review['decision']=='reject' else d['status']))
        dispositions.append({'qid':q,'video_id':d['video_id'],'disposition':disposition,'pipeline_status':d['status'],
            'reason':review['note'] if review else d.get('reason'),'result_file':str(OUT/('prior' if q in priors else 'results')/f'{safe(q)}.json')})
    dump(final/'dispositions.json',dispositions)
    excluded=sorted({questions[q]['video_id'] for q in manifest['original_development_qids']}|{d['video_id'] for d in results.values()})
    dump(OUT/'future_test_exclusions.json',{'video_ids':excluded,'remaining_unseen_long_videos':300-len(excluded),'reason':'All accessed development and replacement video histories excluded from future held-out selection.'})
    progress=read(OUT/'progress.json')
    summary={'status':'complete','completed_at':datetime.datetime.now().astimezone().isoformat(),'target':60,'accepted':60,'accepted_by_origin':dict(collections.Counter(r['origin'] for r in rows)),
        'accepted_videos':len({r['video_id'] for r in rows}),'original60_dispositioned':60,
        'official_task_types':dict(collections.Counter(r['original']['official_task_type'] for r in rows)),
        'evidence_scopes':dict(collections.Counter(r['task_labels']['scope'] for r in rows)),
        'required_fact_count':sum(len(r['required_facts']) for r in rows),
        'multi_fact_questions':sum(len(r['required_facts'])>1 for r in rows),
        'replacement_questions_processed':sum(q in manifest['replacement_order'] for q in results),
        'all_dispositions':dict(collections.Counter(r['disposition'] for r in dispositions)),
        'technical_failures_preserved':len(list((OUT/'failed_results').rglob('*.json'))),
        'future_test_excluded_videos':len(excluded),'human_reviewed':False,'independent_human_calibration':'not run',
        'dataset_type':'curated development/diagnostic set; not a natural-distribution or held-out benchmark',
        'api':{k:progress[k] for k in ['api_attempts','api_failures','usage','resolved_models']},
        'pipeline_counts':progress['counts'],'dataset_file':str(final/'evidence60.jsonl'),'dataset_sha256':sha(final/'evidence60.jsonl')}
    dump(final/'validation.json',check);dump(final/'summary.json',summary)
    source_files=[SOURCE/'run-001-inventory'/name for name in ['questions.jsonl','candidates.jsonl','video_probes.jsonl','selection_manifest.json']]
    source_files+=[REPO/'protocol.json',REPO/'rubric_overrides.json',REPO/'source_supplement_policy.json',OUT/'sampling_manifest.json']
    code_files=sorted((REPO/'code').glob('*.py'))+sorted((REPO/'code/prompts').glob('*.txt'))
    reproducibility={'files':[{'path':str(p),'sha256':sha(p)} for p in source_files+code_files],
        'collector_snapshots':str(OUT/'code_snapshots'),'protocol_history':str(REPO/'protocol-history'),
        'raw_api_ledger':str(OUT/'calls'),'failed_results':str(OUT/'failed_results'),
        'environment_file':str(REPO/'environment.json'),'environment_sha256':sha(REPO/'environment.json')}
    dump(final/'reproducibility.json',reproducibility);dump(REPO/'reproducibility.json',reproducibility)
    dump(REPO/'summary.json',summary);dump(REPO/'validation.json',check)
    dump(REPO/'accepted_manifest.json',[{'qid':r['qid'],'video_id':r['video_id'],'origin':r['origin'],'package_sha256':r['package_sha256']} for r in rows])
    dump(REPO/'dispositions.json',dispositions)
    dump(REPO/'future_test_exclusions.json',read(OUT/'future_test_exclusions.json'))
    sections=[]
    esc=html.escape
    for r in rows:
        p=read(r['package_file']);fs={f['frame_id']:f for f in p['frames']};ss={s['subtitle_id']:s for s in p['subtitles']}
        facts=''.join(f"<li>{esc(f['id'])}: {esc(f['statement'])}</li>" for f in r['required_facts'])
        citedframes={x for f in r['fact_support'] for x in f.get('frame_ids',[])}
        citedsubs={x for f in r['fact_support'] for x in f.get('subtitle_ids',[])}
        images=''.join(f'<figure><img loading="lazy" src="{esc(os.path.relpath(fs[x]["path"],final))}"><figcaption>{x} / {fs[x]["actual_pts_s"]:.3f}s</figcaption></figure>' for x in sorted(citedframes))
        subs=''.join(f'<p>{esc(x)} [{ss[x]["start_s"]:.3f}, {ss[x]["end_s"]:.3f}] {esc(ss[x]["text"])}</p>' for x in sorted(citedsubs))
        sections.append(f'<details id="{esc(r["qid"])}"><summary>{esc(r["qid"])} — {esc(r["question"])}</summary><p>Reference: {esc(r["reference_answer"])}</p><ul>{facts}</ul><p>Review: {esc(r["review_note"])}</p><div class="frames">{images}</div>{subs}<p><a href="{esc(os.path.relpath(r["package_file"],final))}">Complete source package</a></p></details>')
    (final/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Video-MME evidence60</title><style>body{font:16px system-ui;margin:2rem;max-width:1400px}details{border-top:1px solid #ccc;padding:1rem}summary{cursor:pointer}.frames{display:flex;flex-wrap:wrap}figure{margin:8px}img{width:400px;max-width:100%}figcaption{font-size:12px}</style><h1>Video-MME：60 题源证据核验</h1><p>AI 复核诊断集；非人工金标。事实评分与任务标签分离。原始证据、筛选及失败记录均保留。</p>'+''.join(sections))
    print(canonical(summary))


if __name__=='__main__':main()
