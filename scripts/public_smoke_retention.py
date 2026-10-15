"""Public HTTPS acceptance: real curves, heldout QSRR and protected manual values."""
import sys,json,urllib.request,pathlib,time
ROOT=pathlib.Path(__file__).resolve().parents[1];base=sys.argv[1].rstrip('/')
if not base.startswith('https://'):raise ValueError('Public acceptance requires HTTPS')
def api(path,body=None):
 request=urllib.request.Request(base+'/api/'+path,data=json.dumps(body).encode() if body else None,headers={'Content-Type':'application/json'})
 return json.load(urllib.request.urlopen(request,timeout=90))
health=api('health');database=api('retention/database');models=api('models');scope=database['scope']
method={'mode':'RP','workflow':'known','compounds':[{'id':str(i),'name':'Real curve '+str(i),'smiles':c['smiles'],'mixture_parts':p} for i,(c,p) in enumerate(zip(database['examples'],[5,3,2]))],
 'column':{'manufacturer':'Agilent','stationary_phase':scope['stationary_phase'],'temperature_c':35,'particle_um':3.5},
 'mobile':{'a':scope['mobile_a'],'b':'ACN','buffer':scope['buffer'],'ph':None,'ph_control':'formulation'},
 'gradient':[{'time_min':t,'b_percent':b,'temperature_c':35} for t,b in [(0,20),(10,50),(20,50)]],'points':1500}
resolved=api('retention/resolve',{'method':method});method['compounds']=resolved['compounds'];assert all(c['logkw'] is not None for c in method['compounds'])
first=api('simulate',method);assert len(first['order'])==3 and [p['mixture_fraction'] for p in first['peaks']]==[.5,.3,.2]
method['gradient'][1]['time_min']=15;second=api('simulate',method);assert second['peaks'][0]['rt_min']!=first['peaks'][0]['rt_min']
method['compounds'][0]['mixture_parts']=10;third=api('simulate',method);assert [p['rt_min'] for p in second['peaks']]==[p['rt_min'] for p in third['peaks']] and third['peaks'][0]['peak_area']>second['peaks'][0]['peak_area']
optimized=api('optimize',{'simulation':method,'durations_min':[8,12],'starts_percent':[20],'ends_percent':[50],'hold_min':10});assert optimized['evaluated']==2
inputs=json.loads((ROOT/'frontend/tests/v2-inputs.json').read_text());predicted=api('retention/predict',{'smiles':inputs['lss-parameters'],'method':method,'model_id':'lss-parameters'});assert predicted['logkw'] is not None and not predicted['applicability']['seen_in_training']
method['compounds'][0]['parameter_origin']='manual';method['compounds'][0]['logkw']=1.234;protected=api('retention/resolve',{'method':method});assert protected['compounds'][0]['logkw']==1.234
method['mobile']['b']='MeOH';incompatible=api('retention/predict',{'smiles':inputs['lss-parameters'],'method':method,'model_id':'lss-parameters'});assert incompatible['logkw'] is None
report={'url':base,'timestamp_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'health':health,'status':'PASS','real_curve_components':3,'rt_before':[p['rt_min'] for p in first['peaks']],'rt_after_gradient':[p['rt_min'] for p in second['peaks']],'fractions':[p['mixture_fraction'] for p in first['peaks']],'areas_after_ratio':[p['peak_area'] for p in third['peaks']],'optimized_candidates':optimized['evaluated'],'heldout_qsrr':{'smiles':inputs['lss-parameters'],'logkw':predicted['logkw'],'s':predicted['s'],'status':predicted['status']},'license':models['lss_structure_model']['license'],'manual_protection':True,'solvent_abstention':True,'experimental_gradient_accuracy':'Not established'}
(ROOT/'artifacts/public-retention-smoke.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report,indent=2),flush=True)
