#!/usr/bin/env python3
"""Package immutable automatic outputs for human review; does not adjudicate labels."""
import argparse
import csv
import html
import json
from pathlib import Path
from datetime import datetime

from prepare import dump, jsonl, sha


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--annotation",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():
        raise SystemExit("Use a new review package path; do not overwrite human work")
    a.output.mkdir(parents=True)
    drafts={r["qid"]:r for r in [json.loads(f.read_text()) for f in sorted((a.annotation/"drafts").glob("*.json"))]}
    visual={r["qid"]:r for r in [json.loads(f.read_text()) for f in sorted((a.annotation/"visual").glob("*.json"))]}
    checks=json.loads((a.annotation/"integrity_checks.json").read_text())
    citation_problems=checks["checks"].get("model_citation_timestamp_precision",{}).get("detail",[])
    cite_qids={r["qid"] for r in citation_problems}
    records=[]
    for qid,d in drafts.items():
        ann=d["annotation"];v=visual.get(qid,{})
        flags=[]
        if ann["adaptation_status"] in ["unsuitable","needs_review"]:
            flags.append("short_answer_adaptation_requires_review")
        if ann["evidence_scope"]=="global_coverage":
            flags.append("whole_range_coverage_required")
        if "event_order" in ann["task_type"] and len(ann["required_facts"])==1:
            flags.append("check_if_order_rubric_should_split_into_precedence_relations")
        if qid in cite_qids:
            flags.append("model_citation_time_mismatch")
        if not v:
            flags.append("source_verification_not_run")
        if v.get("comparison",{}).get("reference_status")=="conflict_requires_review":
            flags.append("reference_or_question_needs_source_review")
        if v.get("blind_audit",{}).get("package_status")=="sufficient_proxy" and v.get("comparison",{}).get("evidence_status")!="sufficient_proxy":
            flags.append("blind_audit_and_final_sufficiency_disagree")
        if not v.get("subtitles") and ann["modality"] in ["audio_subtitle","mixed"]:
            flags.append("audio_evidence_not_available_in_audited_package")
        records.append({"qid":qid,"short_question":ann["short_question"],"reference_draft":ann["reference_answer_draft"],"required_facts_draft":ann["required_facts"],"adaptation_status":ann["adaptation_status"],"task_type":ann["task_type"],"scope_draft":ann["evidence_scope"],"modality_draft":ann["modality"],"automatic_evidence_status":v.get("comparison",{}).get("evidence_status",v.get("evidence_status","not_run")),"automatic_reference_status":v.get("comparison",{}).get("reference_status","not_run"),"flags":flags,"source_annotation":str(a.annotation/"drafts"/(qid.replace(":","__")+".json")),"source_visual_audit":str(a.annotation/"visual"/(qid.replace(":","__")+".json")) if v else None,"human_review_status":"pending","reviewer":None,"reviewed_at":None,"final_reference":None,"final_evidence_status":None,"review_notes":None})
    jsonl(a.output/"review_queue.jsonl",records)
    fields=["qid","short_question","reference_draft","adaptation_status","automatic_evidence_status","automatic_reference_status","flags","human_review_status","reviewer","reviewed_at","final_reference","final_evidence_status","review_notes"]
    with (a.output/"review_queue.csv").open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in records:
            row={k:r.get(k) for k in fields};row["flags"]=";".join(row["flags"]);w.writerow(row)
    import os
    parts=["<!doctype html><meta charset='utf-8'><title>Video-MME 人工审核包</title><style>body{font:16px system-ui;margin:32px;max-width:1400px}pre{white-space:pre-wrap;background:#f5f5f5;padding:12px}section{border-top:2px solid #ccc;margin-top:28px}figure{display:inline-block;margin:4px;vertical-align:top}img{width:210px}figcaption{font-size:12px;max-width:210px}</style><h1>Video-MME 开发集：人工审核包</h1><p>60 题全部待人工审核。源证据先导仅含预先选定的 12 题。自动结论不是金标。请在 CSV/JSONL 中填写审核者、结论和理由；保留旧自动结果。</p>"]
    for r in records:
        qid=r["qid"];v=visual.get(qid,{})
        parts.append(f"<section id='{html.escape(qid)}'><h2>{html.escape(qid)}</h2><p>{html.escape(r['short_question'])}</p><p>待核验参考：{html.escape(r['reference_draft'])}</p><p>状态：{html.escape(r['automatic_evidence_status'])}；标记：{html.escape(', '.join(r['flags']))}</p>")
        for key,data in [("评分草稿",drafts[qid]["annotation"]),("独立核验",v.get("blind_audit")),("参考比对",v.get("comparison")),("原始字幕片段",v.get("subtitles"))]:
            if data:
                parts.append(f"<details><summary>{key}</summary><pre>{html.escape(json.dumps(data,ensure_ascii=False,indent=2))}</pre></details>")
        for source in v.get("visual_sources",[]):
            rel=os.path.relpath(source["video_path"],a.output)
            parts.append(f"<p><a href='{html.escape(rel,quote=True)}#t={source['start_s']},{source['end_s']}'>原视频 {html.escape(source['source_id'])}，{source['start_s']}–{source['end_s']} 秒</a></p>")
        for frame in v.get("frames",[]):
            rel=os.path.relpath(frame["path"],a.output)
            parts.append(f"<figure><img loading='lazy' src='{html.escape(rel,quote=True)}'><figcaption>{html.escape(frame['source_id'])}<br>PTS {frame['actual_pts_s']:.3f} 秒</figcaption></figure>")
        parts.append("</section>")
    (a.output/"index.html").write_text("\n".join(parts))
    dump(a.output/"manifest.json",{"created_at":datetime.now().astimezone().isoformat(),"source_annotation":str(a.annotation),"source_summary_sha256":sha(a.annotation/"summary.json"),"code_sha256":sha(__file__),"questions":len(records),"visual_records":len(visual),"human_reviewed":0,"citation_warning_qids":sorted(cite_qids)})
    print(json.dumps({"review_package":str(a.output),"questions":len(records),"human_reviewed":0},ensure_ascii=False))


if __name__=="__main__":
    main()
