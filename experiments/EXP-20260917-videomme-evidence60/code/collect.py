#!/usr/bin/env python3
"""Source-grounded QA curation with cached, logged model calls and fixed draw order."""
import argparse
import base64
import collections
import concurrent.futures
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import threading
import time
import zipfile
from urllib.parse import urlsplit

import av
import httpx
from openai import OpenAI
from PIL import Image, ImageDraw
import pysrt

REPO=Path(__file__).resolve().parents[1]
ROOT=Path('/mnt/raid5-01/baorui/visual-memory')
SOURCE=ROOT/'EXP-20260916-memory-data-prep'
PRIOR=ROOT/'EXP-20260916-videomme-annotation-audit'
OUT=ROOT/'EXP-20260917-videomme-evidence60'
DATA=Path('/mnt/raid5-01/baorui/Video-MME')
OLD_CODE=Path('/home/baorui/projects/visual-memory/experiments/EXP-20260916-memory-data-prep/code')
sys.path.insert(0,str(OLD_CODE))
from annotate import retrieve


def canonical(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    temp=p.with_suffix(p.suffix+'.tmp')
    temp.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');temp.replace(p)
def jl(p): return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def safe(qid): return qid.replace(':','__')


class Collector:
    def __init__(self):
        self.cfg=json.loads((REPO/'protocol.json').read_text())
        self.prompts={p.stem:p.read_text() for p in (REPO/'code/prompts').glob('*.txt')}
        self.questions={q['qid']:q for q in jl(SOURCE/'run-001-inventory/questions.jsonl')}
        self.selection=json.loads((SOURCE/'run-001-inventory/selection_manifest.json').read_text())
        self.captions=collections.defaultdict(list)
        for c in jl(SOURCE/'run-001-inventory/candidates.jsonl'):self.captions[c['video_id']].append(c)
        self.subtitles={};self.subtitle_sha={}
        with zipfile.ZipFile(DATA/'subtitle.zip') as z:
            for vid in self.captions:
                member=f'subtitle/{vid}.srt'
                if member not in z.namelist():self.subtitles[vid]=[];self.subtitle_sha[vid]=None;continue
                raw=z.read(member);self.subtitle_sha[vid]=hashlib.sha256(raw).hexdigest()
                self.subtitles[vid]=[{'subtitle_id':f'S{i:05}','source_subtitle_id':f'videomme:{vid}:subtitle:{i:05}',
                    'start_s':s.start.ordinal/1000,'end_s':s.end.ordinal/1000,
                    'text':html.unescape(re.sub('<[^>]*>','',s.text)).replace('\n',' ')}
                    for i,s in enumerate(pysrt.from_string(raw.decode('utf-8-sig',errors='replace')))]
        self.durations={Path(v['path']).stem:v['duration_s'] for v in jl(SOURCE/'run-001-inventory/video_probes.jsonl')}
        self.credentials=json.loads(Path('/home/baorui/projects/visual-memory/tmp/api.json').read_text())
        self.base=self.credentials['base_url'].rstrip('/')
        if urlsplit(self.base).path in ('','/'):self.base+='/v1'
        self.local=threading.local()
        OUT.mkdir(parents=True,exist_ok=True)
        implementation=hashlib.sha256((sha(__file__)+canonical(self.prompts)).encode()).hexdigest()
        snap=OUT/'code_snapshots'/implementation
        if not snap.exists():shutil.copytree(REPO/'code',snap,ignore=shutil.ignore_patterns('__pycache__'))
        self.implementation=implementation
        dump(OUT/'protocol.json',self.cfg)
        manifest={'original_development_qids':self.selection['dev_qids'],'prior_pilot_qids':self.selection['visual_pilot_qids'],
            'remaining48':sorted(set(self.selection['dev_qids'])-set(self.selection['visual_pilot_qids'])),
            'replacement_order':sorted([q for q in self.questions if q not in self.selection['dev_qids']],key=lambda q:hashlib.sha256(f'20260917:replacement:{q}'.encode()).hexdigest()),
            'original_selection_sha256':sha(SOURCE/'run-001-inventory/selection_manifest.json')}
        p=OUT/'sampling_manifest.json'
        if p.exists():assert json.loads(p.read_text())==manifest
        else:dump(p,manifest)
        self.manifest=manifest
        self.init_prior()

    def init_prior(self):
        path=Path('/home/baorui/projects/visual-memory/experiments/EXP-20260916-videomme-annotation-audit/pilot_audit.json')
        priors=json.loads(path.read_text())
        for p in priors:
            out=OUT/'prior'/f"{safe(p['qid'])}.json"
            if out.exists():continue
            supported=p['result']=='source_supported_ai'
            dump(out,{'qid':p['qid'],'video_id':p['video_id'],'status':'prior_source_complete' if supported else 'skipped_prior',
                'reason':p['conclusion'],'prior_audit_file':str(path),'prior_audit_sha256':sha(path),'prior_record':p,
                'draft_file':str(PRIOR/'revised_drafts'/f"{safe(p['qid'])}.json"),'human_reviewed':False})

    def client(self):
        if not hasattr(self.local,'client'):
            self.local.client=OpenAI(api_key=self.credentials['api_key'],base_url=self.base,
                http_client=httpx.Client(proxy=os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy'),trust_env=False),
                timeout=self.cfg['api']['timeout_seconds'],max_retries=0)
        return self.local.client

    def call(self,qid,stage,data=None,content=None):
        messages=[{'role':'system','content':self.prompts[stage]},
                  {'role':'user','content':content if content is not None else canonical(data)}]
        payload={'model':self.credentials['model'],'messages':messages,'max_completion_tokens':self.cfg['api']['max_output_tokens'],
                 'response_format':{'type':'json_object'}}
        digest=hashlib.sha256(canonical(payload).encode()).hexdigest()
        folder=OUT/'calls'/safe(qid)/stage/digest[:16];folder.mkdir(parents=True,exist_ok=True)
        completed=folder/'completed.json'
        if completed.exists():return json.loads(completed.read_text())['parsed']
        logged=json.loads(canonical(payload))
        if content is not None:
            for item in logged['messages'][1]['content']:
                if item['type']=='image_url':item['image_url']['url']='sha256:'+hashlib.sha256(base64.b64decode(item['image_url']['url'].split(',',1)[1])).hexdigest()
        dump(folder/'request.json',{'request_sha256':digest,'implementation':self.implementation,'payload':logged})
        offset=len(list(folder.glob('attempt-*.json')))
        for attempt in range(self.cfg['api']['attempts']):
            start=time.time();rec={'qid':qid,'stage':stage,'request_sha256':digest,'started_unix':start,'attempt':offset+attempt+1,'implementation':self.implementation}
            try:
                r=self.client().chat.completions.create(**payload)
                rec.update(resolved_model=r.model,response_id=r.id,finish_reason=r.choices[0].finish_reason,
                           raw_text=r.choices[0].message.content,usage=r.usage.model_dump() if r.usage else None)
                if r.choices[0].finish_reason!='stop':raise ValueError('Incomplete model response')
                parsed=json.loads(r.choices[0].message.content)
                if not isinstance(parsed,dict):raise ValueError('Not a JSON object')
                rec.update(status='ok',parsed=parsed,elapsed_s=round(time.time()-start,3))
                dump(folder/f"attempt-{rec['attempt']:02}.json",rec);dump(completed,rec)
                return parsed
            except Exception as exc:
                msg=str(exc)
                for key in ['api_key','base_url']:msg=msg.replace(self.credentials[key],'<redacted>')
                rec.update(status='failed',error_type=type(exc).__name__,error=msg[:1200],elapsed_s=round(time.time()-start,3))
                dump(folder/f"attempt-{rec['attempt']:02}.json",rec)
                if attempt+1==self.cfg['api']['attempts']:raise RuntimeError(f'API failed {qid}/{stage}; see redacted ledger') from None

    def nomination_input(self,q):
        caps=self.captions[q['video_id']]
        queries=[q['original_question'],q['reference_draft']]
        queries+=re.findall(r'\([a-z]\)\s*(.*?)(?=\([a-z]\)|$)',q['original_question'],re.I|re.S)
        ranked=[retrieve(query,{'search_queries':[]},caps,8) for query in queries]
        ids=[]
        for i in range(8):
            for rs in ranked:
                if i<len(rs) and rs[i]['source_id'] not in ids:ids.append(rs[i]['source_id'])
        ids=ids[:28]
        ids+= [caps[round(i*(len(caps)-1)/11)]['source_id'] for i in range(12)]
        selected=[c for c in caps if c['source_id'] in set(ids)]
        return {'question':q['original_question'],'options':q['original_options'],'official_reference':q['reference_draft'],
            'duration_s':self.durations[q['video_id']],
            'subtitles':[[s['subtitle_id'],s['start_s'],s['end_s'],s['text']] for s in self.subtitles[q['video_id']]],
            'caption_hints':[[f"C{int(c['source_id'].split(':')[-1]):05}",c['start_s'],c['end_s'],c['text']] for c in selected]}

    def make_package(self,q,nom):
        duration=self.durations[q['video_id']];cfg=self.cfg['projection']
        intervals=[]
        if len(nom.get('intervals',[]))>cfg['max_intervals']:
            raise ValueError('Too many nominated intervals')
        for i,s in enumerate(nom.get('intervals',[])):
            a,b=float(s['start_s']),float(s['end_s'])
            if not (0<=a<b<=duration+1):raise ValueError('Invalid nominated interval')
            # Preserve the entire nominated span; normalize oversized windows,
            # rather than silently truncating source coverage or dropping the QA.
            parts=max(1,math.ceil((b-a)/cfg['max_interval_seconds']))
            for j in range(parts):
                left=a+(b-a)*j/parts;right=a+(b-a)*(j+1)/parts
                intervals.append({'interval_id':f'I{i+1:02}.{j+1:02}',
                    'nominated_interval_index':i,'start_s':max(0,left-3),'end_s':min(duration,right+3)})
        if not intervals:raise ValueError('No source intervals')
        times=[]
        def add(t):
            t=round(float(t),3)
            if 0<=t<duration and not any(abs(t-x)<0.08 for x in times):times.append(t)
        for t in nom.get('key_times_s',[])[:cfg['max_key_times']]:add(t)
        for s in intervals:
            for frac in [.05,.5,.95]:add(s['start_s']+(s['end_s']-s['start_s'])*frac)
        if nom.get('uniform_overview'):
            for i in range(12):add((duration-0.15)*i/11)
        for frac in [.2,.35,.65,.8,.1,.9]:
            for s in intervals:
                if len(times)<cfg['max_frames']:add(s['start_s']+(s['end_s']-s['start_s'])*frac)
        times=sorted(times[:cfg['max_frames']]);frames=[]
        video=DATA/'data'/f"{q['video_id']}.mp4"
        with av.open(str(video)) as container:
            stream=container.streams.video[0]
            for i,t in enumerate(times):
                container.seek(int(t/stream.time_base),stream=stream,backward=True)
                for f in container.decode(stream):
                    if f.pts is None:continue
                    actual=float(f.pts*stream.time_base)
                    if actual+1e-6<t:continue
                    im=f.to_image().convert('RGB');im.thumbnail((cfg['max_side'],cfg['max_side']),Image.Resampling.LANCZOS)
                    path=OUT/'frames'/safe(q['qid'])/f'V{i+1:03}.jpg';path.parent.mkdir(parents=True,exist_ok=True)
                    im.save(path,quality=cfg['jpeg_quality'])
                    frames.append({'frame_id':f'V{i+1:03}','requested_s':t,'actual_pts_s':actual,'path':str(path),'sha256':sha(path),
                                   'width':im.width,'height':im.height,'source_video':str(video)})
                    break
                else:raise ValueError(f'No frame at {t}')
        full=bool(nom.get('full_subtitles_for_audit'))
        subs=[s for s in self.subtitles[q['video_id']] if full or any(s['start_s']<w['end_s'] and s['end_s']>w['start_s'] for w in intervals)]
        package={'qid':q['qid'],'video_id':q['video_id'],'duration_s':duration,'intervals':intervals,'frames':frames,'subtitles':subs,
                 'subtitle_member_sha256':self.subtitle_sha[q['video_id']],'full_original_subtitles':full,'uniform_overview':bool(nom.get('uniform_overview')),
                 'generated_captions_in_evidence':False,'source_video':str(video)}
        dump(OUT/'packages'/f"{safe(q['qid'])}.json",package)
        return package

    def content(self,q,nom,package,grounded=False):
        header={'question':nom['short_question'],'source_intervals':package['intervals'],
          'duration_s':package['duration_s'],'full_original_subtitles':package['full_original_subtitles'],
          'uniform_overview':package['uniform_overview'],
          'subtitles':[[s['subtitle_id'],s['start_s'],s['end_s'],s['text']] for s in package['subtitles']],
          'note':'Actual sampled source frames below, original dataset subtitles above. No generated captions or audio supplied.'}
        if grounded:header.update(reference_answer=nom['reference_answer'],required_facts=nom['required_facts'],scope=nom['scope'])
        content=[{'type':'text','text':canonical(header)}]
        for f in package['frames']:
            content.append({'type':'text','text':f"Frame {f['frame_id']}; actual PTS {f['actual_pts_s']:.3f} s"})
            content.append({'type':'image_url','image_url':{'url':'data:image/jpeg;base64,'+base64.b64encode(Path(f['path']).read_bytes()).decode(),'detail':'high'}})
        return content

    def validate_audit(self,nom,package,observer,audit):
        errors=[];fids={f['frame_id'] for f in package['frames']};sids={s['subtitle_id'] for s in package['subtitles']}
        wanted={f['id'] for f in nom['required_facts']}
        got=[x.get('fact_id') for x in audit.get('facts',[])]
        if set(got)!=wanted or len(got)!=len(wanted):errors.append('fact_id_mismatch')
        for row in audit.get('facts',[])+observer.get('observations',[])+observer.get('relations',[]):
            if any(x not in fids for x in row.get('frame_ids',[])):errors.append('invalid_frame_citation')
            if any(x not in sids for x in row.get('subtitle_ids',[])):errors.append('invalid_subtitle_citation')
        for row in audit.get('facts',[]):
            if row.get('status')=='supported' and not (row.get('frame_ids') or row.get('subtitle_ids')):errors.append('supported_fact_without_citation')
        return sorted(set(errors))

    def sheets(self,qid,package,audit):
        cited={f for row in audit.get('facts',[]) for f in row.get('frame_ids',[])}
        frames=package['frames']
        priority=[f for f in frames if f['frame_id'] in cited]
        for i in range(min(16,len(frames))):
            f=frames[round(i*(len(frames)-1)/max(1,min(16,len(frames))-1))]
            if f not in priority:priority.append(f)
        priority.sort(key=lambda f:f['actual_pts_s'])
        sheets=[]
        for page in range(math.ceil(len(priority)/20)):
            fs=priority[page*20:(page+1)*20]
            im=Image.new('RGB',(1536,244*math.ceil(len(fs)/4)),'white');draw=ImageDraw.Draw(im)
            for i,f in enumerate(fs):
                tile=Image.open(f['path']);tile.thumbnail((384,216));x,y=i%4*384,i//4*244
                im.paste(tile,(x,y));draw.text((x+3,y+218),f"{qid} {f['frame_id']} {f['actual_pts_s']:.2f}s",fill='black')
            path=OUT/'sheets'/safe(qid)/f'page-{page+1:02}.jpg';path.parent.mkdir(parents=True,exist_ok=True);im.save(path,quality=95)
            sheets.append({'path':str(path),'sha256':sha(path),'frame_ids':[f['frame_id'] for f in fs]})
        return sheets

    def process(self,qid):
        dest=OUT/'results'/f'{safe(qid)}.json'
        if dest.exists():return json.loads(dest.read_text())
        q=self.questions[qid];record={'qid':qid,'video_id':q['video_id'],'original':q,'human_reviewed':False,'implementation':self.implementation}
        previous=PRIOR/'revised_drafts'/f'{safe(qid)}.json'
        if previous.exists():
            prior=json.loads(previous.read_text())
            if prior['annotation']['adaptation_status'] in ['needs_review','unsuitable']:
                record.update(status='skipped_ambiguity',reason='User requested skip of ambiguous/unsuitable items already documented in prior audit.',prior_file=str(previous),prior_sha256=sha(previous),prior_reasons=prior['audit']['notes'])
                dump(dest,record);return record
        try:
            nom=self.call(qid,'localize',data=self.nomination_input(q));record['nomination']=nom
            if nom.get('decision')!='inspect' or not nom.get('reference_unchanged_semantically'):
                record.update(status='skipped_localization',reason=nom.get('reason','No safe source-grounded adaptation'));dump(dest,record);return record
            fs=nom.get('required_facts',[])
            if not fs or len({x['id'] for x in fs})!=len(fs):raise ValueError('Invalid minimal-fact rubric')
            package_path=OUT/'packages'/f'{safe(qid)}.json'
            if package_path.exists():package=json.loads(package_path.read_text())
            else:package=self.make_package(q,nom)
            observer=self.call(qid,'observe',content=self.content(q,nom,package))
            audit=self.call(qid,'grounded_audit',content=self.content(q,nom,package,True))
            errors=self.validate_audit(nom,package,observer,audit)
            complete=(audit.get('standalone_question_valid') is True and audit.get('rubric_valid') is True and
                audit.get('reference_status')=='supported' and audit.get('scope_adequate') is True and audit.get('evidence_status')=='complete'
                and all(f.get('status')=='supported' for f in audit.get('facts',[])) and not audit.get('unresolved') and not errors)
            record.update(observer=observer,grounded_audit=audit,integrity_errors=errors,
                status='source_complete_candidate' if complete else 'skipped_evidence_not_complete',
                package_file=str(package_path),package_sha256=sha(package_path),
                review_sheets=self.sheets(qid,package,audit),
                reason=audit.get('admission_reason',''),codex_review='pending',
                observer_disagreement=observer.get('question_ambiguous') is True or observer.get('package_sufficiency')!='complete')
        except Exception as exc:
            msg=str(exc)
            for k in ['api_key','base_url']:msg=msg.replace(self.credentials[k],'<redacted>')
            record.update(status='processing_failed',error_type=type(exc).__name__,reason=msg[:800])
        dump(dest,record);return record

    def summarize(self):
        rs=[json.loads(p.read_text()) for p in sorted((OUT/'results').glob('*.json'))]
        counts=dict(collections.Counter(r['status'] for r in rs))
        reviews={r['qid']:r for r in (json.loads(p.read_text()) for p in (OUT/'codex_reviews').glob('*.json'))}
        pending=sum(r['status']=='source_complete_candidate' and r['qid'] not in reviews for r in rs)
        admitted=8+sum(r['decision']=='accept' for r in reviews.values())
        attempts=[json.loads(p.read_text()) for p in (OUT/'calls').glob('*/*/*/attempt-*.json')]
        summary={'processed':len(rs),'remaining48_processed':sum(r['qid'] in self.manifest['remaining48'] for r in rs),
                 'replacement_processed':sum(r['qid'] not in self.manifest['remaining48'] for r in rs),'counts':counts,
                 'prior_source_complete':8,'candidate_total_including_prior':8+counts.get('source_complete_candidate',0),
                 'api_attempts':len(attempts),'api_failures':sum(x['status']=='failed' for x in attempts),
                 'usage':{k:sum((x.get('usage') or {}).get(k,0) for x in attempts) for k in ['prompt_tokens','completion_tokens','total_tokens']},
                 'resolved_models':sorted({x['resolved_model'] for x in attempts if x.get('resolved_model')}),
                 'codex_accepted_including_prior':admitted,'codex_candidates_pending':pending,
                 'final_admission':'Codex review complete; see final/summary.json for exported dataset' if admitted>=60 and not pending else 'pending Codex evidence review','human_reviewed':False}
        dump(OUT/'progress.json',summary)
        excluded=set(self.selection['dev_video_ids'])|{r['video_id'] for r in rs}
        dump(OUT/'future_test_exclusions.json',{'video_ids':sorted(excluded),'reason':'Source histories accessed for development or curated evidence selection','remaining_unseen_long_videos':300-len(excluded)})
        print(canonical(summary),flush=True)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--phase',choices=['remaining','replacement','summary','ids'],required=True)
    ap.add_argument('--count',type=int,default=12);ap.add_argument('--ids',nargs='*');args=ap.parse_args()
    runner=Collector()
    if args.phase=='summary':runner.summarize();return
    if args.phase=='remaining':qids=runner.manifest['remaining48']
    elif args.phase=='ids':qids=args.ids or []
    else:qids=[q for q in runner.manifest['replacement_order'] if not (OUT/'results'/f'{safe(q)}.json').exists()][:args.count]
    batch=OUT/'batches'/f'{time.time_ns()}.json';dump(batch,{'phase':args.phase,'qids':qids,'implementation':runner.implementation,'created_unix':time.time()})
    with concurrent.futures.ThreadPoolExecutor(max_workers=runner.cfg['api']['concurrency']) as pool:
        futures={pool.submit(runner.process,q):q for q in qids}
        for future in concurrent.futures.as_completed(futures):
            r=future.result();print(canonical({'qid':r['qid'],'status':r['status'],'reason':r.get('reason','')[:180]}),flush=True)
    runner.summarize()


if __name__=='__main__':main()
