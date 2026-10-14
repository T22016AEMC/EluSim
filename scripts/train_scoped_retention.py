"""Fit experimental scoped QSRR; heldout molecules never enter curve model training."""
import json,pathlib,sys,os
os.environ['OPENBLAS_NUM_THREADS']='1'
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from train_v2_models import train
labels=json.loads((ROOT/'data/retention/curves.json').read_text())
if len({r['smiles'] for r in labels})<40:raise ValueError('Insufficient independent structures for this pipeline')
report=train('lss-parameters',[r['smiles'] for r in labels],[[r['logkw'],r['s']] for r in labels],{'model_version':'2.1.0','output':'lss_parameters','dataset':'Boswell isocratic database via Wiczling curated log10(k) records','dataset_source':'https://github.com/wiczling/isocratic-qsrr/tree/2951822d97bd76eeeb244989c9e1691ca4a1ff88/data/deliv','original_dataset_source':'https://www.retentionprediction.org/hplc/database/','license':'CC-BY-NC-SA-3.0-US','scope':labels[0]['scope'],'phi_range':[.2,.5],'external_validation':'Molecule/scaffold heldout experimental logk curves; no independent laboratory or gradient dataset','limitations':['Only this stationary phase, acidified ACN/water and 35°C','No fixed numeric pH; exact formic-acid formulation required','No pKa/logD or overload model','logKw extrapolated to pure water: do not simulate beyond 20–50% ACN','Non-commercial only']})
from elusim.prediction import load_model,evaluate
from elusim.features import molecular_features
import numpy as np
artifact=load_model('lss-parameters');truth=[];pred=[];parameters=[]
for r in labels:
 if r['smiles'] not in report['test_smiles']:continue
 f,x=molecular_features(r['smiles']);kw,s=evaluate(artifact['weights'],x)
 parameters.append({'smiles':r['smiles'],'reference_logkw':r['logkw'],'reference_s':r['s'],'predicted_logkw':float(kw),'predicted_s':float(s)})
 for o in r['observations']:truth.append(o['logk']);pred.append(float(kw-s*o['phi']))
a=np.array(truth);b=np.array(pred)
metrics={'logk_mae':float(np.mean(abs(a-b))),'logk_rmse':float(np.sqrt(np.mean((a-b)**2))),'k_mae':float(np.mean(abs(10**a-10**b))),'k_rmse':float(np.sqrt(np.mean((10**a-10**b)**2))),'heldout_observations':len(a),'heldout_curves':len(parameters),'rt_mae_min':None,'rt_rmse_min':None,'reason_no_rt_error':'No independent gradient experiments / documented t0 in curated dataset; do not infer Rt accuracy from parameter fitting','heldout_parameters':parameters}
(ROOT/'docs/v2-evidence/scoped-retention-errors.json').write_text(json.dumps(metrics,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in metrics.items() if k!='heldout_parameters'}),flush=True)

# Publish transparent curve validation alongside the safe weights.
import runpy
runpy.run_path(str(ROOT/'scripts/validate_scoped_retention.py'),run_name='__main__')
