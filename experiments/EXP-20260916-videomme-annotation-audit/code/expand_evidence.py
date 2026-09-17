"""Extract targeted follow-up frames and uniform topic overviews with exact PTS."""
import math
import av
from PIL import Image, ImageDraw
from prepare_audit import OUT, SOURCE, dump, sha
import json

TIMES = {
    '660-2': [1467, 1475, 1482, 1492, 1501, 1511],
    '834-2': [1806, 1810, 1812, 1816, 1819, 1824],
    '821-1': [650, 655, 680, 700, 840, 855, 880, 900, 985, 990, 997],
    '845-2': list(range(1220, 1316, 5)),
    '806-3': [150, 180, 210, 275, 330, 400, 2715, 2745],
}


def main():
    questions = {q['qid']: q for q in map(json.loads, (SOURCE / 'run-001-inventory/questions.jsonl').read_text().splitlines())}
    manifests = {}
    for qid in [*TIMES, '669-1', '782-1', '843-3']:
        video = f"/mnt/raid5-01/baorui/Video-MME/data/{questions['videomme:'+qid]['video_id']}.mp4"
        frames = []
        with av.open(video) as container:
            stream = container.streams.video[0]
            duration = float(container.duration / av.time_base)
            times = TIMES.get(qid, [round((duration-1)*i/11, 3) for i in range(12)])
            for t in times:
                container.seek(int(t / stream.time_base), stream=stream, backward=True)
                for f in container.decode(stream):
                    actual = float(f.pts * stream.time_base)
                    if actual + 1e-7 < t:
                        continue
                    im = f.to_image()
                    im.thumbnail((1280, 1280))
                    path = OUT / 'expanded' / qid / f'{t:010.3f}.jpg'
                    path.parent.mkdir(parents=True, exist_ok=True)
                    im.save(path, quality=95)
                    frames.append({'requested_time_s': t, 'actual_pts_s': round(actual, 6), 'source_video': video, 'path': str(path), 'sha256': sha(path)})
                    break
                else:
                    raise RuntimeError(f'No frame: {qid} {t}')
        sheet = Image.new('RGB', (1536, math.ceil(len(frames)/4)*244), 'white')
        draw = ImageDraw.Draw(sheet)
        for i, f in enumerate(frames):
            im = Image.open(f['path'])
            im.thumbnail((384,216))
            x,y=i%4*384, i//4*244
            sheet.paste(im,(x,y))
            draw.text((x+3,y+218), f"{qid} | {f['actual_pts_s']:.3f}s", fill='black')
        path=OUT/'expanded'/f'{qid}.jpg'
        sheet.save(path,quality=95)
        manifests['videomme:'+qid]={'selection': 'targeted_followup' if qid in TIMES else 'uniform_12_overview', 'duration_s':duration,'frames':frames,'sheet':str(path),'sheet_sha256':sha(path)}
    dump(OUT/'expanded_manifest.json',manifests)
    print(json.dumps({'cases':len(manifests),'new_frames':sum(len(v['frames']) for v in manifests.values())}))


if __name__ == '__main__':
    main()
