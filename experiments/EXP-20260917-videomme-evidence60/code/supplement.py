"""Preserve the model package and add original SRT context for Codex review."""
import argparse
import datetime
import hashlib
import html
import json
import re
import zipfile
import pysrt
from collect import DATA, OUT, dump, safe, sha


def main():
    ap=argparse.ArgumentParser();ap.add_argument('qid');ap.add_argument('--note',required=True);args=ap.parse_args()
    qid=args.qid if args.qid.startswith('videomme:') else 'videomme:'+args.qid
    original=OUT/'packages'/f'{safe(qid)}.json';p=json.loads(original.read_text())
    target=OUT/'supplements'/f'{safe(qid)}.json'
    if target.exists():raise ValueError('Existing supplement preserved')
    with zipfile.ZipFile(DATA/'subtitle.zip') as z:raw=z.read(f"subtitle/{p['video_id']}.srt")
    assert hashlib.sha256(raw).hexdigest()==p['subtitle_member_sha256']
    p['subtitles']=[{'subtitle_id':f'S{i:05}','source_subtitle_id':f"videomme:{p['video_id']}:subtitle:{i:05}",
        'start_s':s.start.ordinal/1000,'end_s':s.end.ordinal/1000,
        'text':html.unescape(re.sub('<[^>]*>','',s.text)).replace('\n',' ')}
        for i,s in enumerate(pysrt.from_string(raw.decode('utf-8-sig',errors='replace')))]
    p.update(full_original_subtitles=True,source_supplement={'original_package':str(original),'original_package_sha256':sha(original),
        'added_by':'Codex direct source review','created_at':datetime.datetime.now().astimezone().isoformat(),'reason':args.note,
        'new_model_call':False,'original_model_inputs_preserved':True})
    dump(target,p);print(target)


if __name__=='__main__':main()
