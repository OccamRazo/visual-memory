#!/usr/bin/env python3
"""Fetch the preregistered frozen CLIP checkpoint into the local model directory."""
import argparse
import json
import os
from pathlib import Path
from huggingface_hub import snapshot_download

REPO='openai/clip-vit-base-patch32'
REVISION='3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='~/autodl-tmp/models/clip-vit-base-patch32');args=parser.parse_args()
    root=Path(args.output).expanduser()
    snapshot_download(repo_id=REPO,revision=REVISION,local_dir=root,max_workers=4,
        allow_patterns=['config.json','preprocessor_config.json','tokenizer_config.json','special_tokens_map.json','vocab.json','merges.txt','tokenizer.json','pytorch_model.bin'])
    (root/'source_revision.json').write_text(json.dumps({'model_id':REPO,'revision':REVISION,'endpoint':os.environ.get('HF_ENDPOINT','https://huggingface.co'),'weights':'pytorch_model.bin'},indent=2)+'\n')
if __name__=='__main__':main()
