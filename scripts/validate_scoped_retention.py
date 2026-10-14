"""Unseen structure curve errors, including applicability-domain subset."""
import os,sys,pathlib,json
os.environ['OPENBLAS_NUM_THREADS']='1'
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
import numpy as np
from elusim.prediction import load_model,evaluate,infer
from elusim.features import molecular_features
model=load_model('lss-parameters');meta=model['metadata'];rows=json.loads((ROOT/'data/retention/curves.json').read_text());test=set(meta['test_smiles']);train=set(meta['train_smiles'])
assert not test&train
records=[]
for r in rows:
 if r['smiles'] not in test:continue
 f,x=molecular_features(r['smiles']);kw,s=evaluate(model['weights'],x);domain=infer('lss-parameters',r['smiles'])['applicability']['accepted']
 records.append({'smiles':r['smiles'],'reference_logkw':r['logkw'],'reference_s':r['s'],'predicted_logkw':float(kw),'predicted_s':float(s),'in_domain':domain,'reference_logk':[o['logk'] for o in r['observations']],'predicted_logk':[float(kw-s*o['phi']) for o in r['observations']]})
def errors(records):
 a=np.array([v for r in records for v in r['reference_logk']]);b=np.array([v for r in records for v in r['predicted_logk']]);refs=np.array([[r['reference_logkw'],r['reference_s']] for r in records]);pred=np.array([[r['predicted_logkw'],r['predicted_s']] for r in records]);phi=.35
 order_ref=refs[:,0]-phi*refs[:,1];order_pred=pred[:,0]-phi*pred[:,1];mask=np.triu(abs(order_ref[:,None]-order_ref[None,:])>.01,1)
 return {'logk_mae':float(np.mean(abs(a-b))),'logk_rmse':float(np.sqrt(np.mean((a-b)**2))),'k_mae':float(np.mean(abs(10**a-10**b))),'k_rmse':float(np.sqrt(np.mean((10**a-10**b)**2))),'logkw_mae':float(np.mean(abs(refs[:,0]-pred[:,0]))),'s_mae':float(np.mean(abs(refs[:,1]-pred[:,1]))),'retention_order_accuracy_phi_035':float(np.mean(((order_ref[:,None]-order_ref[None,:])*(order_pred[:,None]-order_pred[None,:])>0)[mask])) if mask.any() else None,'heldout_observations':len(a),'heldout_curves':len(records),'heldout_unique_structures':len({r['smiles'] for r in records})}
report={**errors(records),'in_domain_only':errors([r for r in records if r['in_domain']]),'rt_mae_min':None,'rt_rmse_min':None,'reason_no_rt_error':'No independent gradient experiments / documented t0 in curated dataset; do not infer Rt accuracy from parameter fitting','heldout_parameters':records,'scientific_status':'Experimental QSRR; dataset-heldout curves, no independent laboratory / gradient validation'}
(ROOT/'docs/v2-evidence/scoped-retention-errors.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in report.items() if k!='heldout_parameters'}),flush=True)
