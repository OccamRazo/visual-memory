#!/usr/bin/env python3
"""Read-only diagnosis of frozen failed responses; no API calls or result rewrites."""
import argparse,ast,copy,json,traceback
from pathlib import Path
import run

def main(output_name="technical_failure_audit"):
 if not output_name.replace("_", "").isalnum():raise ValueError("Invalid output name")
 source=Path(run.__file__).read_text();tree=ast.parse(source)
 class ExplainAssert(ast.NodeTransformer):
  def visit_Assert(self,node):
   if node.msg is None:node.msg=ast.Constant(value=f'line {node.lineno}: '+ast.unparse(node.test))
   return node
 ns={'__name__':'diagnostic_only','__file__':run.__file__};exec(compile(ast.fix_missing_locations(ExplainAssert().visit(tree)),run.__file__,'exec'),ns)
 r=ns['Runner'].__new__(ns['Runner']);r.cfg=run.read(run.REPO/'protocol.json');snapshot=run.read(run.OUT/'status.json');rows=[]
 for path in sorted((run.OUT/'results').glob('*.json')):
  res=run.read(path)
  if res['status']!='technical_failed':continue
  attempts=[]
  for file in (run.OUT/'calls'/run.safe(res['qid'])).glob('*/*/attempt-*.json'):
   c=run.read(file)
   if c['status']=='failed' and c['implementation']==res['implementation'] and c['completed_at']<=res['completed_at']:attempts.append((c['completed_at'],file,c))
  row={'qid':res['qid'],'result_sha256':run.sha(path),'result_file':str(path),'attempt_diagnostics':[]}
  for _,file,c in sorted(attempts):
   request=run.read(file.parent/'request.json');header=json.loads(request['payload']['messages'][1]['content'][0]['text']);packet=next((run.read(p) for p in (run.OUT/'source'/run.safe(res['qid'])).glob('*/*/packet.json') if run.digest(run.read(p))==request['source_packet_sha256']),None)
   item={'stage':c['stage'],'call_file':str(file),'call_sha256':run.sha(file),'original_error':c['error'],'original_error_type':c['error_type']}
   try:
    d=json.loads(c['raw_text'])
    if c['stage']!='audit':d=r.align_witness_bounds(d,packet)
    def validate(p):
     if c['stage']=='audit':r.check_audit(d,p,header['observation'])
     else:r.check_observation(d,p)
    try:validate(packet);item['replay']='pass'
    except Exception as exc:item['replay']=str(exc)
    corrected=copy.deepcopy(packet);changes=[]
    for fr in corrected['frames']:
     actual_groups=sorted(g['id'] for g in corrected['windows'] if any(a-.15<=fr['time_s']<=b+.15 for a,b in g['windows']))
     if actual_groups!=fr['group_ids']:changes.append({'frame_id':fr['id'],'time_s':fr['time_s'],'old':fr['group_ids'],'based_on_all_overlapping_windows':actual_groups});fr['group_ids']=actual_groups
    item['frame_membership_defects']=changes
    try:validate(corrected);item['replay_after_membership_only_correction']='pass'
    except Exception as exc:item['replay_after_membership_only_correction']=str(exc)
   except Exception as exc:item['diagnostic_error']=type(exc).__name__+':'+str(exc)
   row['attempt_diagnostics'].append(item)
  rows.append(row)
 audit={'created_at':run.now(),'progress_snapshot':snapshot,'reviewed_failed_questions':len(rows),'scope':'Read-only replay of terminal technical failures as encountered; background worker unchanged. No images viewed or new API calls. Counterfactual membership correction is not a production result or source pass.','records':rows}
 out=run.OUT/'diagnostics'/f'{output_name}.json'
 for target in [out,run.REPO/f'{output_name}.json']:
  if target.exists():raise FileExistsError(f'Preserve previous audit: {target}')
 for target in [out,run.REPO/f'{output_name}.json']:run.dump(target,audit)
 print(json.dumps({'reviewed':len(rows),'latest_errors':[{ 'qid':x['qid'],'error':x['attempt_diagnostics'][-1].get('replay'),'after_membership_fix':x['attempt_diagnostics'][-1].get('replay_after_membership_only_correction')} for x in rows]},ensure_ascii=False))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--output-name',default='technical_failure_audit');a=ap.parse_args();main(a.output_name)
