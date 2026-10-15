"""Scoped measured curves and QSRR are separate from method-specific Rt."""
import json,pathlib,functools
from .features import molecular_features
from .conditions import scope_matches, scope_mismatches
from .schemas import Scope
from .sources import source_code
DATA=pathlib.Path(__file__).resolve().parents[2]/'data/retention'
@functools.lru_cache(maxsize=1)
def measured_curves():
    return json.loads((DATA/'curves.json').read_text(encoding='utf8'))

def predict_curve(smiles,method,use_literature=True):
    from .prediction import infer,load_model
    features,_=molecular_features(smiles)
    model=load_model('lss-parameters');meta=model['metadata'];scope=meta['scope']
    limits=meta['phi_range']
    result={'status':'Insufficient data','output_type':'lss_parameters','logkw':None,'s':None,'rt_min':None,
            'features':features,'model':{k:v for k,v in meta.items() if not k.endswith('_smiles')},
            'input_conditions':method.model_dump(),'warnings':list(meta['limitations']),
            'scope':{k:v for k,v in scope.items() if k!='mode'},'phi_range':limits,
            'curve':None,'parameter_source':None,'applicability':{'accepted':False}}
    mismatches=scope_mismatches(scope,method)
    specification=curve_conditions()
    if method.column.particle_um!=specification['particle_um']:
        mismatches.append(f"particle_um: current {method.column.particle_um}; required {specification['particle_um']}")
    for i,node in enumerate(method.gradient):
        if not limits[0]-1e-9<=node.b_percent/100<=limits[1]+1e-9:
            mismatches.append(f"gradient[{i}].b_percent: current {node.b_percent}; required {100*limits[0]}–{100*limits[1]}")
    result['condition_mismatches']=mismatches
    if mismatches:
        result['warnings']+=mismatches
        return result
    known=next((r for r in measured_curves() if r['smiles']==features['canonical_smiles']),None) if use_literature else None
    if known:
        kw,ss=known['logkw'],known['s'];result.update(status='Literature-derived',parameter_source='Measured isocratic log10(k) curve fitted to LSS',observations=known['observations'],fit_rmse_logk=known['fit_rmse_logk'])
        result['applicability']={'accepted':True,'rule':'Exact canonical structure and method chemistry in experimental database','seen_in_training':features['canonical_smiles'] in meta['train_smiles']}
    else:
        predicted=infer('lss-parameters',smiles)
        result.update({k:predicted[k] for k in ['status','applicability']});result['warnings']+=predicted['warnings']
        if predicted['prediction'] is None:return result
        kw,ss=predicted['prediction'];result['parameter_source']='Scaffold-heldout experimental QSRR; not measured for this query'
    if not -3<=kw<=12 or not 0<=ss<=30:
        result['warnings'].append('Nonphysical predicted parameters; quantitative output withheld');result['status']='Insufficient data';return result
    import numpy as np
    phi=np.linspace(*limits,31);result.update(logkw=float(kw),s=float(ss),curve={'phi':phi.tolist(),'k':(10**(kw-ss*phi)).tolist(),'logk':(kw-ss*phi).tolist(),'logarithm_base':10})
    return result

def resolve_compounds(req,overwrite_manual=False):
    compounds=[];records=[]
    for c in req.compounds:
        if c.parameter_origin=='manual' and c.logkw is not None and c.s is not None and not overwrite_manual:
            compounds.append(c);records.append({'compound_id':c.id,'status':'Manual parameters preserved','reason':'Explicit overwrite confirmation required'});continue
        if c.kind!='small_molecule' or not c.smiles:
            compounds.append(c);records.append({'compound_id':c.id,'status':'Insufficient data','reason':'Small-molecule SMILES required'});continue
        try:
            r=predict_curve(c.smiles,req);records.append({'compound_id':c.id,**r})
            if r['logkw'] is None:
                compounds.append(c);continue
            provenance={'model_id':r['model']['model_id'],'model_version':r['model']['model_version'],'source':r['parameter_source'],
                        'license':r['model']['license'],'canonical_smiles':r['features']['canonical_smiles'],
                        'scope':r['scope'],'phi_range':r['phi_range'],'validation_status':r['status'],'applicability':r['applicability'],'warnings':r['warnings'],
                        'reference':r['model']['original_dataset_source'],'particle_um':3.5}
            compounds.append(c.model_copy(update={'logkw':r['logkw'],'s':r['s'],'scope':Scope(**r['scope']),
                             'source':source_code(r['status']),'parameter_origin':'literature' if r['status']=='Literature-derived' else 'prediction',
                             'retention_provenance':provenance}))
        except (ValueError,OSError,KeyError) as e:
            compounds.append(c);records.append({'compound_id':c.id,'status':'Insufficient data','reason':str(e)})
    return req.model_copy(update={'compounds':compounds,'workflow':'known'}),records


def curve_conditions():
    """Expose existing model metadata and documented material specification, not a new model."""
    from .prediction import load_model
    meta=load_model('lss-parameters')['metadata']
    return {'model_id':meta['model_id'],'model_version':meta['model_version'],
            'scope':meta['scope'],'phi_range':meta['phi_range'],
            'particle_um':measured_curves()[0]['applicability_domain']['particle_um'],
            'status':'Experimental model prediction','limitations':meta['limitations'],
            'notice':'Matching training conditions does not establish external gradient accuracy.'}
