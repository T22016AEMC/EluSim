"""Small CPU-only model registry. Method-specific Rt is never converted to LSS."""
import json,pathlib,functools,gzip
import numpy as np
from .features import molecular_features,VERSION
ROOT=pathlib.Path(__file__).resolve().parents[1]/'models'
@functools.lru_cache(maxsize=4)
def load_model(model_id):
 if model_id not in ['report0259-rt','pnnl-uv-shape','lss-parameters']:raise ValueError('Unknown / unavailable model ID')
 data=json.loads(gzip.decompress((ROOT/(model_id+'.json.gz')).read_bytes()).decode('utf8'))
 if data['metadata']['feature_version']!=VERSION:raise ValueError('Descriptor version mismatch')
 return data

def evaluate(weights,x):
 if weights['kind']=='multioutput':return np.array([evaluate(w,x)[0] for w in weights['outputs']])
 x=np.asarray(x,dtype=np.float32)
 def walk(tree):
  i=0
  while tree['left'][i]!=-1:i=tree['left'][i] if x[tree['feature'][i]]<=tree['threshold'][i] else tree['right'][i]
  return np.array(tree['value'][i])
 if weights['kind']=='forest':return np.mean([walk(t) for t in weights['trees']],axis=0)
 if weights['kind']=='boosting':return np.array([weights['initial']])+weights['rate']*np.sum([walk(t) for t in weights['trees']],axis=0)
 return np.array(weights['coef'])@((x-np.array(weights['mean']))/np.array(weights['scale']))+weights['intercept']

def infer(model_id,smiles):
 model=load_model(model_id);features,x=molecular_features(smiles);d=model['domain'];a=np.array(features['fingerprint'],dtype=bool);b=np.array(d['fingerprints'],dtype=bool);inter=(b&a).sum(axis=1);similarity=float(np.max(inter/np.maximum(1,(b|a).sum(axis=1))))
 violations=[name for i,name in enumerate(features['descriptors']) if x[i]<d['min'][i] or x[i]>d['max'][i]]
 accepted=not violations and similarity>=model['metadata']['domain_threshold']
 meta={k:v for k,v in model['metadata'].items() if not k.endswith('_smiles')}
 result={'model':meta,'features':features,'applicability':{'accepted':accepted,'max_training_tanimoto':similarity,'threshold':meta['domain_threshold'],'descriptor_violations':violations,'rule':meta['domain_rule'],'seen_in_training':features['canonical_smiles'] in model['metadata']['train_smiles']},'status':'Experimental model prediction' if accepted else 'Insufficient data','warnings':['Dataset-heldout validation is not an independent laboratory validation',features['ionization_warning']],'prediction':None}
 if accepted and meta['beats_mean_baseline']:result['prediction']=evaluate(model['weights'],x).tolist()
 elif accepted:result['status']='Insufficient data';result['warnings'].append('Model did not outperform heldout mean baseline; quantitative inference disabled')
 else:result['warnings'].append('Out of applicability domain: no quantitative result returned')
 return result

def report_method():
 return {'id':'report0259','mode':'RP','column':{'manufacturer':'Waters','stationary_phase':'Waters, ACQUITY UPLC BEH C18','length_mm':100,'diameter_mm':2.1,'particle_um':1.7,'temperature_c':40},'mobile':{'a':'Water + 0.1% formic acid','b':'ACN','buffer':'0.1% formic acid in A and B'},'gradient':[{'time_min':t,'b_percent':b,'flow_ml_min':.4,'temperature_c':40,'interpolation':'linear'} for t,b in [(0,5),(1.12,5),(6.41,99.5),(10.01,99.5)]],'unreported':['pH','dwell volume','hold-up time','pore size','efficiency'],'source':'RepoRT0259 raw metadata and gradient; full-method descriptor, not generic C18'}
def method_matches(method):
 expected=report_method()
 if method.mode!=expected['mode']:return False
 if any(getattr(method.column,k)!=v for k,v in expected['column'].items()):return False
 if any(getattr(method.mobile,k)!=v for k,v in expected['mobile'].items()):return False
 return [n.model_dump() for n in method.gradient]==expected['gradient']
def predict_retention(smiles,method,model_id='report0259-rt'):
 if model_id!='report0259-rt':raise ValueError('No deployed LSS parameter model; direct Rt model only')
 r=infer(model_id,smiles);r['input_conditions']=method.model_dump();r['output_type']='rt_min';r['logkw']=None;r['s']=None;r['rt_min']=None;r['method_match']=method_matches(method)
 r['warnings']+=['pH/dwell/hold-up time were not documented in this source; numerical pH/dwell inputs cannot be validated','Direct method-specific Rt model cannot simulate another gradient or provide logKw/S']
 if not r['method_match']:r['status']='Insufficient data';r['prediction']=None;r['warnings'].append('Method mismatch: phase, solvents, geometry, temperature, flow or gradient changed')
 elif r['prediction'] is not None:r['rt_min']=float(r['prediction'][0])
 return r

def prepare_structure(req):
    """Acquire tiered LSS estimates for the structure workflow without scope gates."""
    if req.workflow != 'structure' or req.mode != 'RP':
        return req, []
    from .retention_registry import resolve_compounds

    return resolve_compounds(req)

def library():
 from .retention_registry import curve_conditions
 models=[]
 for mid in ['report0259-rt','pnnl-uv-shape','lss-parameters']:
  data=load_model(mid);models.append({k:v for k,v in data['metadata'].items() if not k.endswith('_smiles')})
 return {'lss_conditions':curve_conditions(),'models':models,'retention_method':report_method(),'lss_structure_model':models[-1],'lss_warning':'Experimental scoped LSS model: Eclipse Plus C18, 35°C, formic-acid ACN/water, 20–50% ACN; non-commercial only; independent gradient accuracy unavailable','uv_levels':{'1':'RDKit chromophore screening','2':'Window maximum derived from experimental full-spectrum model; not separate λmax model','3':'Experimental 220–400nm normalized shape model; no molar absorptivity or solvent adjustment'}}
