"""Record Codex's direct source inspections separately from model outputs."""
import argparse
import datetime
import json
from pathlib import Path
from collect import OUT, dump, safe, sha


def main():
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['show','accept','reject','status'])
    ap.add_argument('--revise',action='store_true',help='Preserve an existing review before recording an explicit correction')
    ap.add_argument('qids',nargs='*');ap.add_argument('--note',default='');ap.add_argument('--inspection',choices=['subtitles','frames','mixed'],default='mixed')
    args=ap.parse_args();results={p.stem:json.loads(p.read_text()) for p in (OUT/'results').glob('*.json')}
    if args.action=='status':
        reviews=[json.loads(p.read_text()) for p in (OUT/'codex_reviews').glob('*.json')]
        done={r['qid'] for r in reviews}
        print(json.dumps({'accepted_new':sum(r['decision']=='accept' for r in reviews),'rejected_new':sum(r['decision']=='reject' for r in reviews),
                          'with_prior':8+sum(r['decision']=='accept' for r in reviews),
                          'pending':[r['qid'] for r in results.values() if r['status']=='source_complete_candidate' and r['qid'] not in done]},ensure_ascii=False));return
    for qid in args.qids:
        if not qid.startswith('videomme:'):qid='videomme:'+qid
        d=results[safe(qid)]
        if args.action=='show':
            p=json.loads(Path(d['package_file']).read_text()) if d.get('package_file') else {}
            print('\n'+qid+' '+d['status']);print('QUESTION',d.get('nomination',{}).get('short_question'))
            print('ORIGINAL',d['original']['original_question'],'OFFICIAL',d['original']['reference_draft'])
            print('REF',d.get('nomination',{}).get('reference_answer'));print('FACTS',json.dumps(d.get('nomination',{}).get('required_facts'),ensure_ascii=False))
            print('AUDIT',json.dumps(d.get('grounded_audit',{}),ensure_ascii=False));print('OBSERVER',d.get('observer',{}).get('answer'),d.get('observer',{}).get('package_sufficiency'))
            cited={x for f in d.get('grounded_audit',{}).get('facts',[]) for x in f.get('subtitle_ids',[])}
            ss=p.get('subtitles',[]);indices={j for i,s in enumerate(ss) if s['subtitle_id'] in cited for j in range(max(0,i-1),min(len(ss),i+2))}
            for i in sorted(indices):
                s=ss[i];print(s['subtitle_id'],round(s['start_s'],3),s['text'])
            print('SHEETS',json.dumps(d.get('review_sheets',[]),ensure_ascii=False));continue
        if not args.note:raise ValueError('A source-specific review note is required')
        if args.action=='accept' and d['status']!='source_complete_candidate':raise ValueError('Only grounded complete candidates can be admitted by this helper')
        result_path=OUT/'results'/f'{safe(qid)}.json'
        record={'qid':qid,'decision':args.action,'note':args.note,'inspection':args.inspection,
                'reviewer':'Codex active session; reference-visible source audit','human_reviewed':False,
                'reviewed_at':datetime.datetime.now().astimezone().isoformat(),'result_file':str(result_path),'result_sha256':sha(result_path),
                'package_file':d.get('package_file'),'package_sha256':d.get('package_sha256'),'answer_correctness_used_as_admission_rule':False}
        supplement=OUT/'supplements'/f'{safe(qid)}.json'
        if supplement.exists():
            record.update(original_model_package_file=d.get('package_file'),original_model_package_sha256=d.get('package_sha256'),
                package_file=str(supplement),package_sha256=sha(supplement),source_supplement_reviewed=True)
        target=OUT/'codex_reviews'/f'{safe(qid)}.json'
        if target.exists():
            if not args.revise:raise ValueError('Existing decision preserved; record a new revision explicitly')
            oldsha=sha(target);archive=OUT/'codex_reviews_history'/f'{safe(qid)}-{oldsha[:16]}.json'
            archive.parent.mkdir(exist_ok=True)
            if archive.exists():raise ValueError('Review history collision')
            target.rename(archive)
            record.update(supersedes_file=str(archive),supersedes_sha256=oldsha,explicit_correction=True)
        dump(target,record);print(qid,args.action)


if __name__=='__main__':main()
