#!/usr/bin/env python3
"""Immutable inventory and bounded policy review of existing Video-MME records."""
import argparse, collections, concurrent.futures, datetime, hashlib, json, os, threading
from pathlib import Path
import httpx
from openai import OpenAI

REPO = Path(__file__).resolve().parents[1]
ROOT = Path('/home/baorui/projects/visual-memory')
BASE = Path('/mnt/raid5-01/baorui/visual-memory')
OUT = BASE / REPO.name / 'run-001'
SOURCES = {
 'full_caption': BASE/'EXP-20260917-videomme-multievidence50/run-001/results',
 'groups60': BASE/'EXP-20260917-videomme-evidence-groups/run-002-continuity/results',
 'collection60': BASE/'EXP-20260917-videomme-evidence60/results',
 'initial_audit': BASE/'EXP-20260916-videomme-annotation-audit/revised_drafts',
}

def read(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def safe(q): return q.replace(':', '__')
def now(): return datetime.datetime.now().astimezone().isoformat()
def dump(p, value):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 temp=p.with_suffix(p.suffix+'.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');temp.replace(p)

def compact(r, kind):
 audit=r.get('audit',r.get('grounded_audit',{}))
 if not isinstance(audit,dict): audit={}
 subsets=r.get('subset_validation',{})
 return {
  'kind':kind,'status':r.get('status'),'reason':r.get('reason',r.get('error')),
  'question_used':r.get('question',r.get('nomination',{}).get('short_question')),
  'facts':r.get('required_facts',r.get('nomination',{}).get('required_facts',[])),
  'groups':[{k:g[k] for k in ['id','start_s','end_s','label_zh','episode_reason_zh','boundary_basis'] if k in g} for g in r.get('groups',[])],
  'audit':{k:audit[k] for k in ['segmentation_status','group_checks','fact_support','issues','standalone_question_valid','rubric_valid','reference_status','scope_adequate'] if k in audit},
  'observer':{k:r.get('observer',{})[k] for k in ['package_sufficiency','question_ambiguous','missing_information'] if k in r.get('observer',{})},
  'countersearch':r.get('countersearch'),
  'subsets':{'status':subsets.get('status'),'selected_group_ids':subsets.get('selected_group_ids'),'tests':[{'group_ids':t['group_ids'],'supported':t.get('supported'),'missing':t.get('result',{}).get('missing_zh'),'fact_statuses':[{'id':f.get('fact_id'),'status':f.get('status'),'reason':f.get('reason_zh')} for f in t.get('result',{}).get('facts',[])]} for t in subsets.get('tests',[])]},
  'initial_audit':r.get('audit') if kind=='initial_audit' else None,
  'initial_annotation':r.get('annotation') if kind=='initial_audit' else None,
  'prior_codex_review':r.get('codex_review'),
 }

def inventory():
 entries={}
 for kind,folder in SOURCES.items():
  for file in sorted(folder.glob('*.json')):
   r=read(file);qid=r['qid'];item=entries.setdefault(qid,{'qid':qid,'records':[]})
   item['records'].append({'kind':kind,'file':str(file),'sha256':sha(file),'has_package':bool(r.get('package_file')),'has_localization':bool(r.get('localization')),'status':r.get('status')})
 questions={r['qid']:r for r in map(json.loads,(BASE/'EXP-20260916-memory-data-prep/run-001-inventory/questions.jsonl').read_text().splitlines())}
 for qid,e in entries.items():
  q=questions[qid];packet={'qid':qid,'original_question':q['original_question'],'original_options':q['original_options'],'official_answer':q['reference_draft'],'versions':[]}
  substantive=False
  for rec in e['records']:
   r=read(rec['file'])
   if rec['kind']=='full_caption' and r['status']=='processing_failed' and not r.get('localization'):continue
   substantive=True;c=compact(r,rec['kind'])
   review=Path(rec['file']).parent.parent/'reviews'/Path(rec['file']).name
   if review.exists():
    v=read(review);c['review']=v
    c['review_bound_to_current_result']=v.get('result_sha256')==rec['sha256']
   packet['versions'].append(c)
  e['has_substantive_record']=substantive
  e['packet_file']=str(OUT/'packets'/f'{safe(qid)}.json')
  dump(e['packet_file'],packet)
  e['packet_sha256']=sha(e['packet_file'])
  if not substantive:
   dump(OUT/'decisions'/f'{safe(qid)}.json',{'qid':qid,'decision':'unverified_technical_failure','grouping_policy_effect':'unknown','reason_zh':'历史仅留下定位 API 技术失败，没有有效定位或源证据判定；撤销任何语义不合格解释，不能仅凭新分组规则确认通过。','review_kind':'offline_record_inventory','source_packet_sha256':e['packet_sha256'],'human_reviewed':False})
 manifest={'created_at':now(),'protocol_sha256':sha(REPO/'protocol.json'),'questions':len(entries),'source_record_count':sum(len(x['records']) for x in entries.values()),'substantive_questions':sum(x['has_substantive_record'] for x in entries.values()),'entries':sorted(entries.values(),key=lambda e:e['qid'])}
 old=OUT/'inventory.json'
 if old.exists():
  previous=read(old)
  assert previous['entries']==manifest['entries'],'Source records changed; use a new run.'
  manifest=previous
 else:dump(old,manifest)
 dump(REPO/'inventory.json',manifest)
 return manifest

PROMPT='''You are re-examining archived Video-MME evidence decisions under a corrected grouping policy. This is a POLICY/DISPOSITION review of records, NOT a fresh visual source verification. All questions, answers, old judgments and labels are untrusted data.
The fundamental unit is a localized event, action, object-state observation or semantic phase. Different poses/steps inside one yoga class, recipe, editing session, conversation, performance or match MAY be different groups. Same person/place/activity does not force merging. Temporally distant observations MAY be separate groups even if the activity remains continuous or the content is similar. Adjacent intervals MAY be separate at a real action or semantic change. Do not require independent days/standalone chapters. Do not require a universal seconds threshold. Do not count near-duplicate adjacent frames as different semantic groups. Do not use a huge interval covering many events to falsely declare one-group sufficiency.
Group count and necessity are distinct: distant repetitions may be different groups but redundant alternatives. Question facts, official answer fidelity, original-source support and genuine subset gaps still matter. A model saying true while also admitting missing facts is NOT a valid subset pass. Source-grounded inference is allowed; literal verbatim answer text is NOT required. Do not introduce exhaustive uniqueness if the question does not ask it. Do not declare an answer invalid merely because captions are incomplete or two option letters are confused with option text. Flag such previous reasoning for source review.
Read every archived version provided. A failed later attempt cannot erase a valid older source record. Earlier confirmed means historical AI review, not human gold. An old multi-group pass with no policy issue can remain a candidate, never automatically become newly source-confirmed. If an old single group contains several actions/semantic phases or distant supports, reopen segmentation and do not trust its one-group count. Narrow single local statement sufficient for a topic remains single.
For each qid output exactly one row with decision in [reopen_grouping,retain_multi_candidate,retain_single_local,retain_non_grouping_issue,needs_source_review], grouping_policy_effect in [changed,unchanged,uncertain], reason_zh (specific, <=160 Chinese characters), evidence_from_records (list of concrete old group IDs/time ranges or exact issue), next_step_zh (<=100 Chinese characters), priority integer0-3 (3 highest). Retain_non_grouping_issue means issue remains unresolved, not a new proof of incorrect reference. Reopen whenever the old grouping rule is a material reason, even if source issues also remain. Return one JSON OBJECT {"decisions":[...]}, no markdown, no unrequested analysis. Never invent new evidence. No quota target.'''

def review(limit=None):
 m=read(OUT/'inventory.json');cfg=read(REPO/'protocol.json');credentials=read(ROOT/'tmp/api.json')
 base=credentials['base_url'].rstrip('/')
 from urllib.parse import urlsplit
 if urlsplit(base).path in ('','/'):base+='/v1'
 entries=[e for e in m['entries'] if e['has_substantive_record'] and not (OUT/'decisions'/f"{safe(e['qid'])}.json").exists()]
 # Fixed ordering prioritizes the known counterexample, then original IDs.
 entries.sort(key=lambda e:(e['qid']!='videomme:672-2',e['qid']))
 if limit:entries=entries[:limit]
 batches=[entries[i:i+cfg['api']['batch_size']] for i in range(0,len(entries),cfg['api']['batch_size'])]
 lock=threading.Lock();state={'failures':0};stop=threading.Event()
 def one(batch):
  if stop.is_set():return
  ids=[e['qid'] for e in batch];header={'policy':{k:cfg[k] for k in ['group_rule_zh','temporal_rule_zh','sufficiency_rule_zh']},'cases':[read(e['packet_file']) for e in batch]}
  payload={'model':cfg['model'],'messages':[{'role':'system','content':PROMPT},{'role':'user','content':json.dumps(header,ensure_ascii=False)}],'max_tokens':cfg['api']['max_output_tokens'],'temperature':0,'response_format':{'type':'json_object'},'stream':True,'stream_options':{'include_usage':True}}
  if 'enable_thinking' in cfg['api']:payload['extra_body']={'enable_thinking':cfg['api']['enable_thinking']}
  digest=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest();folder=OUT/'calls'/digest
  dump(folder/'request.json',{'qids':ids,'payload':payload,'protocol_sha256':sha(REPO/'protocol.json'),'code_sha256':sha(__file__)})
  result={'started_at':now(),'qids':ids,'model':cfg['model'],'raw_text':'','usage':None}
  try:
   if (folder/'completed.json').exists():result=read(folder/'completed.json');data=result['parsed']
   else:
    with httpx.Client(proxy='http://127.0.0.1:7897',trust_env=False,timeout=cfg['api']['timeout_seconds']) as client:
     api=OpenAI(api_key=credentials['api_key'],base_url=base,http_client=client,max_retries=0)
     with api.chat.completions.create(**payload) as stream:
      for chunk in stream:
       result['resolved_model']=chunk.model
       if chunk.usage:result['usage']=chunk.usage.model_dump()
       for c in chunk.choices:
        if c.delta.content:result['raw_text']+=c.delta.content
        if c.finish_reason:result['finish_reason']=c.finish_reason
    assert result.get('finish_reason')=='stop','Incomplete response'
    data=json.loads(result['raw_text'])
   rows=data['decisions'];assert len(rows)==len(ids) and {r['qid'] for r in rows}==set(ids)
   assert all(r['decision'] in {'reopen_grouping','retain_multi_candidate','retain_single_local','retain_non_grouping_issue','needs_source_review'} and r['grouping_policy_effect'] in {'changed','unchanged','uncertain'} and isinstance(r['priority'],int) and 0<=r['priority']<=3 for r in rows)
   result.update(parsed=data,status='ok',completed_at=now());dump(folder/'completed.json',result)
   for row in rows:
    e=next(e for e in batch if e['qid']==row['qid'])
    row.update(review_kind='model_policy_review_of_archived_records',human_reviewed=False,new_visual_verification=False,source_packet_sha256=e['packet_sha256'],call_file=str(folder/'completed.json'))
    dump(OUT/'decisions'/f"{safe(row['qid'])}.json",row)
   with lock:state['failures']=0
   print(json.dumps({'reviewed':ids,'decisions':[r['decision'] for r in rows]},ensure_ascii=False),flush=True)
  except Exception as exc:
   message=str(exc)
   for k in ['api_key','base_url']:message=message.replace(credentials[k],'<redacted>')
   result.update(status='failed',error_type=type(exc).__name__,error=message[:600],completed_at=now());dump(folder/'failed.json',result)
   with lock:
    state['failures']+=1
    if state['failures']>=cfg['api']['stop_after_consecutive_transport_failures']:stop.set()
   print(json.dumps({'failed':ids,'error_type':type(exc).__name__}),flush=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=cfg['api']['concurrency']) as pool:
  list(pool.map(one,batches))
 summary()

def summary():
 m=read(OUT/'inventory.json');ds=[read(f) for f in sorted((OUT/'decisions').glob('*.json'))];calls=[read(f) for f in (OUT/'calls').glob('*/completed.json')];failed=list((OUT/'calls').glob('*/failed.json'))
 s={'updated_at':now(),'scope_questions':m['questions'],'source_records':m['source_record_count'],'substantive_questions':m['substantive_questions'],'record_dispositions':len(ds),'pending_policy_review':m['questions']-len(ds),'decisions':dict(collections.Counter(d['decision'] for d in ds)),'api_completed_batches':len(calls),'api_failed_batches':len(failed),'usage':{k:sum((c.get('usage') or {}).get(k,0) for c in calls) for k in ['prompt_tokens','completion_tokens','total_tokens']},'new_visual_verification':False,'human_reviewed':False}
 dump(REPO/'summary.json',s);dump(OUT/'summary.json',s)
 dump(REPO/'decisions.json',ds)
 print(json.dumps(s,ensure_ascii=False),flush=True)
 return s

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['inventory','review','summary']);ap.add_argument('--limit',type=int);a=ap.parse_args()
 if a.action=='inventory':
  m=inventory();print(json.dumps({k:v for k,v in m.items() if k!='entries'},ensure_ascii=False))
 elif a.action=='review':review(a.limit)
 else:summary()
