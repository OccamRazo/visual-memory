#!/usr/bin/env python3
"""Freeze and detach the bounded repair worker; successful pilot results are retained."""
import argparse,json,shlex,shutil,subprocess
from engine import REPO,OUT,sha,digest,read,dump,now
SESSION='videomme-expand50'
PYTHON='/home/baorui/projects/WorldMM/.venv/bin/python'
def start():
 if subprocess.run(['tmux','has-session','-t',SESSION],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:raise SystemExit('Existing tmux worker; no duplicate started.')
 if (OUT/'STOP').exists() or (OUT/'circuit_breaker.json').exists():raise SystemExit('STOP/circuit breaker present; inspect before restarting.')
 files={str(p.relative_to(REPO)):sha(p) for p in (REPO/'code').rglob('*') if p.is_file() and '__pycache__' not in str(p)};key=digest({'code':files,'protocol':read(REPO/'protocol.json')});deployment=OUT/'deployment'/key
 if not deployment.exists():shutil.copytree(REPO/'code',deployment/'code',ignore=shutil.ignore_patterns('__pycache__'));shutil.copy2(REPO/'protocol.json',deployment/'protocol.json')
 worker=[PYTHON,str(deployment/'code/expand.py'),'run']
 command=shlex.join(['flock','-x',str(OUT/'runner.lock'),'-c','true'])+' && exec '+shlex.join(worker)+' >> '+shlex.quote(str(OUT/'background.log'))+' 2>&1'
 subprocess.run(['tmux','new-session','-d','-s',SESSION,command],check=True)
 launch={'launched_at':now(),'session':SESSION,'deployment_sha256':key,'frozen_script':worker[1],'worker_argv':worker,'pilot_coordination':'waits for runner.lock; skips existing terminal results','log_file':str(OUT/'background.log'),'state_file':str(OUT/'status.json')}
 if (OUT/'launch.json').exists():dump(OUT/'launch_history'/f'{now().replace(":","-")}.json',read(OUT/'launch.json'))
 dump(OUT/'launch.json',launch);dump(REPO/'launch.json',launch);print(json.dumps(launch,ensure_ascii=False,indent=2))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['start','status','stop']);a=ap.parse_args()
 if a.action=='start':start()
 elif a.action=='status':
  alive=subprocess.run(['tmux','has-session','-t',SESSION],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
  print(json.dumps({'tmux_alive':alive,'progress':read(OUT/'status.json') if (OUT/'status.json').exists() else None},ensure_ascii=False,indent=2))
 else:dump(OUT/'STOP',{'at':now(),'reason':'explicit stop command'});print('Stop requested; current API stage will finish.')
