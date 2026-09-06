#!/usr/bin/env python3
"""CPU CLIP encoding can run alongside the single loaded VLM and data ingest."""
import argparse
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from egvqa_pilot.encoding import ClipEncoder
from egvqa_pilot.data import add_snapshot_keys

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prepared',required=True);parser.add_argument('--expected-videos',type=int,default=24);parser.add_argument('--watch',action='store_true')
    args=parser.parse_args();root=Path(args.prepared);encoder=ClipEncoder();started=time.monotonic()
    while True:
        complete=0
        for path in sorted(root.glob('*/snapshot/manifest.json')):
            manifest=json.loads(path.read_text())
            if manifest['keys_status']=='ready': complete+=1;continue
            # Prepare publishes the manifest after payload; encoding never opens audit/QA.
            with np.load(path.parent/'pixels.npz',allow_pickle=False) as f: pixels=f['images']
            t=time.monotonic();keys=encoder.capsule_keys(pixels,[c['valid_mask'] for c in manifest['capsules']])
            identity={**encoder.identity,'aggregation':'mean_raw_projected_valid_frame_features_then_L2','image_preprocessor':'CLIPProcessor use_fast=False fixed input letterbox224','image_device':'cpu','text_max_tokens':77,'text_truncation':'explicit logged'}
            sealed=add_snapshot_keys(path.parent,keys,identity);complete+=1
            print(json.dumps({'video_id':manifest['video_id'],'encoding_s':time.monotonic()-t,'snapshot_hash':sealed['snapshot_hash'],'complete':complete}),flush=True)
        if not args.watch or complete>=args.expected_videos:break
        time.sleep(5)
    print(json.dumps({'encoded_videos':complete,'wall_s':time.monotonic()-started}),flush=True)
if __name__=='__main__': main()
