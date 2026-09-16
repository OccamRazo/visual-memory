#!/usr/bin/env python3
"""Export content-equivalent anonymous frame sheets for fresh-context AI answers.

This is a secondary diagnostic, not a replay of the Qwen inference interface.
Never write to the original run. Repeated identical packets share one answer.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from egvqa_pilot import prompts
from egvqa_pilot.protocol import fixed_hash_order


def read(path):
    return json.loads(path.read_text())


def rows(path):
    return [json.loads(line) for line in path.open()]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source-run', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--dataset', default='data/downloads/egvqa-pilot')
    a = p.parse_args()
    source, output = Path(a.source_run), Path(a.output)
    destination = output / 'blind_packets'
    destination.mkdir(exist_ok=False)
    summary = read(source / 'summary.json')
    e1 = {(r['question_id'], r['condition']): r for r in rows(source / 'e1_pairs.jsonl')}
    e2 = {(r['question_id'], r['method']): r for r in rows(source / 'e2_results.jsonl')}
    questions = {q['question_id']: {**q, 'video_id': v['video_id']}
                 for v in read(Path(a.dataset) / 'annotations/eval.json') for q in v['questions']}
    valid = {r['question_id'] for r in summary['E1']['pairs'] if r['valid_pair']}
    losses = summary['E2']['primary_R2_minus_R1']['loss_question_ids']
    gains = summary['E2']['primary_R2_minus_R1']['gain_question_ids']
    identical_loss = [q for q in losses if e2[q, 'R1']['answer'].strip() == e2[q, 'R2']['answer'].strip()]
    strata = [
        ('same_answer_scoring_disagreement', identical_loss),
        ('other_R2_loss', [q for q in losses if q not in identical_loss]),
        ('R2_gain', gains),
        ('E1_Full_incorrect', [r['question_id'] for r in summary['E1']['pairs']
                               if r['valid_pair'] and not r['scores']['Full']]),
    ]
    chosen = []
    for label, candidates in strata:
        eligible = [q for q in candidates if q in valid and q not in [r['question_id'] for r in chosen]]
        if not eligible:
            raise ValueError(f'Empty stratum {label}')
        chosen.append({'stratum': label, 'question_id': fixed_hash_order(eligible, seed=43)[0]})
    selection = {'selected_before_new_image_review': True, 'selection_seed': 43,
                 'selection_rule': 'strata in declared order; first seed43 SHA question not previously selected; mechanically valid E1 only',
                 'selection_uses_original_outcomes': True, 'scope': 'four diagnostic cases, all E1/E2 final input conditions',
                 'not_population_estimate': True, 'cases': chosen}
    write(output / 'selection_manifest.json', selection)
    call_index = {r['request_id']: r for r in rows(source / 'calls.jsonl')}
    logical, unique = [], {}
    for case in chosen:
        qid = case['question_id']; q = questions[qid]
        root = source / 'prepared' / q['video_id']
        em = read(root / 'e1' / qid / 'manifest.json')
        sm = read(root / 'snapshot' / 'manifest.json')
        with np.load(root / 'e1' / qid / 'pixels.npz', allow_pickle=False) as z:
            ep = z['images']
        with np.load(root / 'snapshot' / 'pixels.npz', allow_pickle=False) as z:
            sp = z['images']
        groups = {g['group_id']: (g, ep[g['image_index']]) for g in em['groups']}
        capsules = {g['capsule_id']: (g, sp[i]) for i, g in enumerate(sm['capsules'])}
        conditions = [('E1', c, r) for (qq, c), r in e1.items() if qq == qid]
        conditions += [('E2', m, e2[qid, m]) for m in ['R0', 'R1', 'R2', 'R*']]
        for phase, condition, row in conditions:
            frames = []
            bank = groups if phase == 'E1' else capsules
            for cid in row['selected_ids']:
                meta, pixels = bank[cid]
                for pts, pixel in zip(meta['pts'], pixels):
                    frames.append({'id': cid, 'pts': pts, 'pixels': pixel,
                                   'rgb_sha256': hashlib.sha256(pixel.tobytes()).hexdigest()})
            original = call_index[row['request_id']]
            assert len(frames) == len(original['image_records'])
            for frame, recorded in zip(frames, original['image_records']):
                assert frame['rgb_sha256'] == recorded['rgb_sha256']
                assert {'id': frame['id'], 'pts': frame['pts']} == recorded['visible_label']
            ids = list(dict.fromkeys(f['id'] for f in frames))
            prompt = prompts.ANSWER.format(question=q['question']) + '\nAllowed citation IDs: ' + json.dumps(ids)
            visible = [{k: v for k, v in frame.items() if k != 'pixels'} for frame in frames]
            key = digest({'prompt': prompt, 'frames': visible})
            packet_id = 'p' + key[:12]
            if key not in unique:
                folder = destination / packet_id; folder.mkdir()
                pages = []
                # One row per group, pixels pasted at original size; labels outside.
                if frames:
                    canvas = Image.new('RGB', (4 * 224, (len(frames) // 4) * 252), 'white')
                    draw = ImageDraw.Draw(canvas)
                    for j, frame in enumerate(frames):
                        x, y = j % 4 * 224, j // 4 * 252
                        draw.text((x + 2, y + 2), frame['id'], fill='black')
                        draw.text((x + 2, y + 14), f"PTS {frame['pts']:.6f} s", fill='black')
                        canvas.paste(Image.fromarray(frame['pixels']), (x, y + 28))
                    path = folder / 'frames.png'; canvas.save(path)
                    pages = [str(path.resolve())]
                packet = {'packet_id': packet_id, 'prompt': prompt, 'image_pages': pages,
                          'visible_frames': visible, 'n_images': len(frames),
                          'presentation': 'original-size frames in chronological rows; printed PTS rounded to six decimals, exact values in visible_frames',
                          'allowed_citation_ids': ids}
                write(folder / 'input.json', packet)
                unique[key] = {'packet_id': packet_id, 'input_path': str((folder / 'input.json').resolve()),
                               'input_sha256': hashlib.sha256((folder / 'input.json').read_bytes()).hexdigest(),
                               'pages_sha256': {str(Path(f).name): hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in pages}}
            logical.append({'question_id': qid, 'video_id': q['video_id'], 'phase': phase, 'condition': condition,
                            'packet_id': packet_id, 'packet_content_hash': key, 'original_result_id': row['result_id'],
                            'original_verdict': row['verdict'], 'original_answer': row.get('answer'),
                            'reference': q['answer'], 'question': q['question'], 'frame_payload_verified': True})
    write(output / 'private_condition_mapping.json', logical)
    write(output / 'packet_manifest.json', {'logical_conditions': len(logical), 'unique_packets': len(unique),
                                         'packets': sorted(unique.values(), key=lambda r: r['packet_id']),
                                         'identical_input_reuse': True, 'scope': selection})
    print(json.dumps({'cases': chosen, 'logical_conditions': len(logical), 'unique_packets': len(unique)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
