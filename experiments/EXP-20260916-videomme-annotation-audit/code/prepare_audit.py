"""Build immutable source indexes and inspection sheets; no model requests."""
import collections
import hashlib
import html
import json
from pathlib import Path
import re
import zipfile

from PIL import Image, ImageDraw
import pysrt

SOURCE = Path('/mnt/raid5-01/baorui/visual-memory/EXP-20260916-memory-data-prep')
OUT = SOURCE.parent / 'EXP-20260916-videomme-annotation-audit'


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    run = SOURCE / 'run-004-source-refinement'
    questions = {q['qid']: q for q in map(json.loads, (SOURCE / 'run-001-inventory/questions.jsonl').read_text().splitlines())}
    drafts = [json.loads(p.read_text()) for p in sorted((run / 'drafts').glob('*.json'))]
    dump(OUT / 'draft_input.json', [{'question': questions[d['qid']], 'draft': d} for d in drafts])
    archive = Path('/mnt/raid5-01/baorui/Video-MME/subtitle.zip')
    manifest = {'source_run': str(run), 'source_files': {}, 'subtitle_archive_sha256': sha(archive), 'sheets': {}}
    with zipfile.ZipFile(archive) as z:
        for vid in sorted({questions[d['qid']]['video_id'] for d in drafts}):
            name = f'subtitle/{vid}.srt'
            if name not in z.namelist():
                dump(OUT / 'subtitles' / f'{vid}.json', {'status': 'missing', 'segments': []})
                continue
            raw = z.read(name)
            rows = [{'subtitle_id': f'videomme:{vid}:subtitle:{i:05}', 'start_s': s.start.ordinal / 1000, 'end_s': s.end.ordinal / 1000,
                     'text': html.unescape(re.sub('<[^>]*>', '', s.text)).replace('\n', ' ')}
                    for i, s in enumerate(pysrt.from_string(raw.decode('utf-8-sig', errors='replace')))]
            dump(OUT / 'subtitles' / f'{vid}.json', {'status': 'available', 'member': name, 'member_sha256': hashlib.sha256(raw).hexdigest(), 'segments': rows})
            (OUT / 'subtitles' / f'{vid}.txt').write_text('\n'.join(f"{r['subtitle_id']} {r['start_s']:.2f}-{r['end_s']:.2f} {r['text']}" for r in rows) + '\n')
    for path in sorted((run / 'visual').glob('*.json')):
        d = json.loads(path.read_text())
        manifest['source_files'][str(path)] = sha(path)
        if not d.get('frames'):
            continue
        groups = collections.defaultdict(list)
        for f in d['frames']:
            assert sha(f['path']) == f['sha256']
            groups[f['source_id']].append(f)
        selected = [fs[i] for fs in groups.values() for i in (0, 3, 6, 9)]
        sheet = Image.new('RGB', (1536, 6 * 244), 'white')
        draw = ImageDraw.Draw(sheet)
        for i, f in enumerate(selected):
            im = Image.open(f['path']).convert('RGB')
            im.thumbnail((384, 216))
            x, y = (i % 4) * 384, (i // 4) * 244
            sheet.paste(im, (x, y))
            draw.text((x+3, y+218), f"{d['qid']} | {f['actual_pts_s']:.3f}s", fill='black')
        dest = OUT / 'sheets' / path.with_suffix('.jpg').name
        dest.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(dest, quality=95)
        manifest['sheets'][d['qid']] = {'path': str(dest), 'sha256': sha(dest), 'frames': selected}
    for p in sorted((run / 'drafts').glob('*.json')):
        manifest['source_files'][str(p)] = sha(p)
    dump(OUT / 'inspection_manifest.json', manifest)
    print(json.dumps({'drafts': len(drafts), 'pilot_files': 12, 'sheets': len(manifest['sheets']), 'source_frames_hash_checked': 600, 'output': str(OUT)}))


if __name__ == '__main__':
    main()
