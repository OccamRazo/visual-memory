#!/usr/bin/env python3
"""Offline validation and inspectable caption-only export, with no model calls."""
import csv,html,json,statistics
from pathlib import Path
from caption_review import REPO,OUT,BASE,read,sha,dump,summary

def main():
 s=summary();m=read(OUT/'manifest.json');ds={d['qid']:d for d in read(REPO/'caption_decisions.json')};old=read(BASE/REPO.name/'run-001/inventory.json');checks={'questions_unique':len({e['qid'] for e in m['entries']}),'archived_records_hash_checked':0,'caption_packets_hash_checked':0,'caption_citations_checked':0,'reviewable_decisions_checked':0}
 assert len(ds)==825 and s['pending_caption_review']==0
 for e in old['entries']:
  for r in e['records']:assert sha(r['file'])==r['sha256'];checks['archived_records_hash_checked']+=1
 for e in m['entries']:
  assert sha(e['packet_file'])==e['packet_sha256']==ds[e['qid']]['source_packet_sha256'];checks['caption_packets_hash_checked']+=1
  d=ds[e['qid']];p=read(e['packet_file']);lookup={c['id']:c for c in p['captions']}
  if not e['caption_count']:assert d['grouping']=='not_reviewable';continue
  assert d['grouping'] in {'multi','single','unclear'};checks['reviewable_decisions_checked']+=1
  request=read(read(d['call_file'])['request_file'])['payload'];assert all(isinstance(x['content'],str) for x in request['messages']);assert json.loads(request['messages'][1]['content'])==p
  assert request['model']=='qwen3.8-flash' and request['extra_body']['enable_thinking'] is False
  for g in d['groups']:
   assert all(i in lookup for i in g['caption_ids']);checks['caption_citations_checked']+=len(g['caption_ids'])
   assert g['start_s']==min(lookup[i]['start_s'] for i in g['caption_ids']) and g['end_s']==max(lookup[i]['end_s'] for i in g['caption_ids'])
 checks['status']='pass';checks['new_visual_verification']=False;dump(REPO/'caption_checks.json',checks)
 with (REPO/'caption_review_table.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['qid','caption_count','grouping','group_count','requires_multiple','coverage','reference_consistency','reason_zh','groups','missing_zh'])
  for e in m['entries']:
   d=ds[e['qid']];w.writerow([e['qid'],e['caption_count'],d['grouping'],len(d['groups']),d['requires_multiple'],d['coverage'],d['reference_consistency'],d['reason_zh'],' | '.join(f"{g['id']} {g['start_s']}-{g['end_s']}s {g['label_zh']}" for g in d['groups']),' | '.join(d.get('missing_zh',[]))])
 esc=html.escape;parts=['<!doctype html><html lang="zh"><meta charset="utf-8"><title>Caption语义分组复查</title><style>body{max-width:1100px;margin:32px auto;font:16px/1.6 sans-serif}details{border:1px solid #ddd;padding:12px;margin:10px 0}small{color:#555}blockquote{background:#f5f7f9;padding:8px 14px}summary{cursor:pointer}input{width:95%;padding:12px}</style><h1>Caption语义分组复查</h1><p>仅检查历史API选出的caption。分组依据事件/语义和时间分离；未执行新的原始图像验证。时间范围为引用caption外包络，可能有间隔，不是逐帧边界。</p><input id="filter" placeholder="搜索题号、题目、状态" oninput="document.querySelectorAll(\'details.case\').forEach(e=>e.hidden=!e.dataset.search.includes(this.value.toLowerCase()))">']
 for e in m['entries']:
  d=ds[e['qid']]
  if d['grouping']=='not_reviewable':continue
  p=read(e['packet_file']);lookup={c['id']:c for c in p['captions']};title=f"{e['qid']} · {d['grouping']} · {len(d['groups'])}组 · 需联合:{d['requires_multiple']} · 覆盖:{d['coverage']}"
  parts.append(f'<details class="case" data-search="{esc((title+p["question"]).lower(),quote=True)}"><summary>{esc(title)}</summary><h3>{esc(p["question"])}</h3><p>参考答案：{esc(p["reference_answer"])}</p><p>{esc(d["reason_zh"])}</p>')
  for g in d['groups']:
   parts.append(f'<h4>{esc(g["id"])} {g["start_s"]}–{g["end_s"]}秒：{esc(g["label_zh"])}</h4><p>{esc(g["contribution_zh"])}</p>')
   for cid in g['caption_ids']:
    c=lookup[cid];parts.append(f'<blockquote><small>{esc(cid)} [{c["start_s"]}, {c["end_s"]}]</small><br>{esc(c["text"])}</blockquote>')
  parts.append('</details>')
 (OUT/'caption_review.html').write_text(''.join(parts)+'</html>')
 print(json.dumps(checks,ensure_ascii=False))
if __name__=='__main__':main()
