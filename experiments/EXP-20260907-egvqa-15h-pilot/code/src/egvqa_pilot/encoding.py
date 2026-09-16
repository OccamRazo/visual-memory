"""Frozen CLIP keys. Encode only retained pixel payloads; no QA or gold input."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np

class ClipEncoder:
    def __init__(self, model_path='/root/autodl-tmp/models/clip-vit-base-patch32', device='cpu'):
        import torch
        from transformers import CLIPModel, CLIPProcessor
        torch.set_num_threads(8)
        self.torch = torch
        self.device = device
        self.processor = CLIPProcessor.from_pretrained(model_path, local_files_only=True, use_fast=False)
        self.model = CLIPModel.from_pretrained(model_path, local_files_only=True).eval().to(device)
        self.identity = json.loads((Path(model_path)/'source_revision.json').read_text())

    def texts(self, texts):
        # CLIP has 77 positions. Truncation of retrieval queries is explicit in the log;
        # this does not truncate the VLM question or count as model evidence.
        raw = self.processor.tokenizer(texts, padding=False, truncation=False)
        enc = self.processor(text=texts, return_tensors='pt', padding=True, truncation=True, max_length=77)
        with self.torch.inference_mode():
            z = self.model.get_text_features(**{k:v.to(self.device) for k,v in enc.items()})
            z = z / z.norm(dim=-1, keepdim=True).clamp_min(1e-12)
        return z.float().cpu().numpy(), [len(ids)>77 for ids in raw['input_ids']]

    def images(self, pixels, batch_size=32):
        from PIL import Image
        features=[]
        for start in range(0,len(pixels),batch_size):
            imgs=[Image.fromarray(np.asarray(x,dtype=np.uint8)) for x in pixels[start:start+batch_size]]
            enc=self.processor(images=imgs,return_tensors='pt')
            with self.torch.inference_mode():
                z=self.model.get_image_features(**{k:v.to(self.device) for k,v in enc.items()})
            features.append(z.float().cpu().numpy())
        return np.concatenate(features,axis=0)

    def capsule_keys(self, pixels, valid_masks):
        shape=pixels.shape
        features=self.images(pixels.reshape((-1,)+shape[2:])).reshape((shape[0],shape[1],-1))
        masks=np.asarray(valid_masks,dtype=bool)
        z=(features*masks[...,None]).sum(axis=1)/np.maximum(masks.sum(axis=1,keepdims=True),1)
        return (z/np.maximum(np.linalg.norm(z,axis=1,keepdims=True),1e-12)).astype(np.float32)

    def unload(self):
        self.model.to('cpu')
        del self.model
        if self.device.startswith('cuda'):
            self.torch.cuda.empty_cache()
