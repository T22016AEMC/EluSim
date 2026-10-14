"""Standard observations; never identify two LSS parameters from one gradient Rt."""
import numpy as np
from .features import molecular_features
FIELDS=['mode','stationary_phase','mobile_a','mobile_b','buffer','ph','temperature_c','source','license']
def normalize_observation(row):
 r=dict(row);features,_=molecular_features(r['smiles']);r['canonical_smiles']=features['canonical_smiles']
 if any(r.get(k) in [None,''] for k in FIELDS if k!='ph') or (r.get('ph') is None and r.get('ph_control')!='formulation'):raise ValueError('Complete condition scope, source and license required')
 if r['mode']!='RP':raise ValueError('LSS normalization is RP only')
 if r.get('rt_min') is not None and r.get('t0_min') is not None:
  if r.get('elution')!='isocratic':raise ValueError('Rt/t0 to k conversion requires isocratic elution')
  if not float(r['rt_min'])>float(r['t0_min'])>0:raise ValueError('Retained isocratic Rt > t0 > 0 required')
  r['k']=float(r['rt_min'])/float(r['t0_min'])-1
 if r.get('k') is not None:
  if float(r['k'])<=0:raise ValueError('k must be positive')
  r['logk']=float(np.log10(float(r['k'])))
 if r.get('logk') is None:r['identifiability']='Single/method-specific Rt only; no unique logKw/S'
 else:
  r['logk']=float(r['logk']);r['phi']=float(r['phi'])
  if not np.isfinite(r['logk']) or not 0<=r['phi']<=1:raise ValueError('Finite logk and phi fraction 0–1 required')
  r['identifiability']='Retention curve candidate'
 return r
def fit_retention_curve(rows):
 data=[normalize_observation(r) for r in rows]
 if len(data)<2 or any(r.get('logk') is None for r in data):raise ValueError('At least two distinct isocratic logk(phi) observations required')
 key=lambda r:tuple(r[k] for k in FIELDS[:-2])+ (r.get('ph_control','fixed'),r['canonical_smiles'])
 if len({key(r) for r in data})!=1:raise ValueError('Curve observations must share molecule and exact physicochemical scope')
 phi=np.array([r['phi'] for r in data]);y=np.array([r['logk'] for r in data]);A=np.c_[np.ones(len(phi)),-phi]
 if np.linalg.matrix_rank(A)<2 or np.linalg.cond(A)>1e4:raise ValueError('Distinct compositions required for identifiable parameters')
 logkw,s=np.linalg.lstsq(A,y,rcond=None)[0]
 if not -3<=logkw<=12 or not 0<=s<=30:raise ValueError('Parameters outside supported LSS boundaries')
 return {'smiles':data[0]['canonical_smiles'],'logkw':float(logkw),'s':float(s),'scope':{**{k:data[0][k] for k in FIELDS[:-2]},'ph_control':data[0].get('ph_control','fixed')},'source':'Calibrated','observations':data,'fit_rmse_logk':float(np.sqrt(np.mean((A@np.array([logkw,s])-y)**2))),'external_prediction_error':None}
