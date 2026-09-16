"""A normal reader can access one sealed snapshot, public queries, and nothing else."""
from __future__ import annotations
import hashlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import sys
import numpy as np
from .isolation import restrict_read_paths
from .protocol import rank_topk, select_r2

def _worker(conn, snapshot_dir):
    # Resolve runtime and snapshot paths before the irreversible allowlist.
    import encodings.cp437
    import zipfile
    root=Path(snapshot_dir).resolve()
    runtime=[Path(sys.base_prefix)/'lib'/f'python{sys.version_info.major}.{sys.version_info.minor}',
             Path(sys.prefix)/'lib'/f'python{sys.version_info.major}.{sys.version_info.minor}']
    if len(list(Path('/proc/self/task').iterdir()))!=1:
        raise RuntimeError('Landlock ABI1 requires a single-threaded reader before restriction')
    abi=restrict_read_paths([root]+[p for p in runtime if p.exists()])
    try:
        manifest=json.loads((root/'manifest.json').read_text())
        if manifest['keys_status']!='ready':
            raise ValueError('snapshot keys are not sealed')
        if manifest['pixels_file']!='pixels.npz':
            raise ValueError('noncanonical snapshot payload')
        with np.load(root/'pixels.npz',allow_pickle=False) as f:
            pixels=f['images']; keys=f['keys']
        content={k:v for k,v in manifest.items() if k!='snapshot_hash'}
        canonical=json.dumps(content,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
        actual=hashlib.sha256(canonical+pixels.tobytes()+keys.tobytes()).hexdigest()
        if actual!=manifest['snapshot_hash']:
            raise ValueError('snapshot hash mismatch')
        capsules=manifest['capsules']; ids=[c['capsule_id'] for c in capsules]; positions={i:j for j,i in enumerate(ids)}
        conn.send({'ready':True,'abi':abi,'snapshot_hash':actual,'ids':ids})
        while True:
            command=conn.recv(); action=command['action']
            if action=='close': break
            try:
                if action=='rank':
                    result=rank_topk(ids,keys,command['query'],command['k'],command.get('exclude',[]))
                elif action=='r2':
                    result=select_r2(ids,keys,command['gap_keys'],command['initial_ids'])
                elif action=='packet':
                    selected=command['ids']
                    if len(selected)>6 or len(selected)!=len(set(selected)) or not set(selected)<=set(ids):
                        raise PermissionError('packet must contain at most six unique live IDs')
                    ordered=sorted(selected,key=lambda i:(capsules[positions[i]]['pts'][0],i))
                    result={'capsules':[capsules[positions[i]] for i in ordered],
                            'images':pixels[[positions[i] for i in ordered]],'snapshot_hash':actual}
                elif action=='probe':
                    result={}
                    for path in command['paths']:
                        try:
                            with open(path,'rb') as f: f.read(1)
                            result[path]='UNEXPECTED_READ'
                        except PermissionError: result[path]='denied'
                        except FileNotFoundError: result[path]='missing_not_a_valid_probe'
                else:
                    raise ValueError('unknown reader action')
                conn.send({'ok':True,'result':result})
            except Exception as exc:
                conn.send({'ok':False,'error':f'{type(exc).__name__}: {exc}'})
    except Exception as exc:
        conn.send({'ready':False,'error':f'{type(exc).__name__}: {exc}'})
    finally:
        conn.close()

class SafeReader:
    def __init__(self,snapshot_dir):
        ctx=mp.get_context('spawn')
        self.conn,child=ctx.Pipe()
        self.process=ctx.Process(target=_worker,args=(child,str(Path(snapshot_dir).resolve())),daemon=True)
        thread_vars=('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')
        saved={k:os.environ.get(k) for k in thread_vars}
        try:
            for k in thread_vars:os.environ[k]='1'
            self.process.start()
        finally:
            for k,v in saved.items():
                if v is None:os.environ.pop(k,None)
                else:os.environ[k]=v
        child.close()
        if not self.conn.poll(30): raise RuntimeError('isolated reader startup timeout')
        self.identity=self.conn.recv()
        if not self.identity.get('ready'): raise RuntimeError(self.identity.get('error'))
    def request(self,action,**kwargs):
        self.conn.send({'action':action,**kwargs})
        if not self.conn.poll(30): raise RuntimeError('isolated reader request timeout')
        response=self.conn.recv()
        if not response['ok']: raise PermissionError(response['error'])
        return response['result']
    def close(self):
        if self.process.is_alive():
            self.conn.send({'action':'close'}); self.process.join(5)
        if self.process.is_alive(): self.process.terminate(); self.process.join()
        self.conn.close()
    def __enter__(self): return self
    def __exit__(self,*args): self.close()

def packet_images(packet):
    result=[]
    for group,pixels in zip(packet['capsules'],packet['images']):
        for timestamp,image in zip(group['pts'],pixels):
            result.append({'image':image,'id':group['capsule_id'],'pts':timestamp})
    return result

def _diagnostic_packet_worker(conn,snapshot_dir,selected):
    """Privileged R* process, distinct from all normal reader worker instances."""
    try:
        root=Path(snapshot_dir);manifest=json.loads((root/'manifest.json').read_text())
        by_id={c['capsule_id']:(j,c) for j,c in enumerate(manifest['capsules'])}
        if len(selected)>6 or len(set(selected))!=len(selected) or not set(selected)<=set(by_id):
            raise ValueError('R* can inject only up to six distinct surviving capsules')
        ordered=sorted(selected,key=lambda i:(by_id[i][1]['pts'][0],i))
        with np.load(root/'pixels.npz',allow_pickle=False) as f:
            pixels=f['images'][[by_id[i][0] for i in ordered]]
        conn.send({'ok':True,'packet':{'capsules':[by_id[i][1] for i in ordered],'images':pixels,
                                     'snapshot_hash':manifest['snapshot_hash']}})
    except Exception as exc:conn.send({'ok':False,'error':f'{type(exc).__name__}: {exc}'})
    finally:conn.close()

def privileged_packet(snapshot_dir,selected):
    ctx=mp.get_context('spawn');parent,child=ctx.Pipe()
    process=ctx.Process(target=_diagnostic_packet_worker,args=(child,str(snapshot_dir),selected),daemon=True)
    process.start();child.close()
    try:
        if not parent.poll(30):raise RuntimeError('R* diagnostic packet timeout')
        result=parent.recv()
        if not result['ok']:raise RuntimeError(result['error'])
        return result['packet']
    finally:
        process.join(5)
        if process.is_alive():process.terminate();process.join()
        parent.close()
