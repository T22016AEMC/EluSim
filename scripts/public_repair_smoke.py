"""Legacy provenance compatibility against an explicitly provided HTTPS origin."""
import json,sys,urllib.request,urllib.error,pathlib,datetime
origin=sys.argv[1].rstrip('/')
assert origin.startswith('https://')
baseline='--baseline' in sys.argv
method={'mode':'RP','workflow':'known','compounds':[{'id':str(i),'name':'Legacy test '+str(i),'logkw':2+.5*i,'s':4+.5*i,'source':source,'mixture_parts':part} for i,(source,part) in enumerate(zip(['基於模型','Model-based','historic unknown label'],[5,3,2]))],'gradient':[{'time_min':0,'b_percent':5},{'time_min':10,'b_percent':95},{'time_min':20,'b_percent':95}]}
def request(path,data=None):
 req=urllib.request.Request(origin+'/api/'+path,data=json.dumps(data).encode() if data else None,headers={'Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=90) as r:return r.status,json.load(r)
 except urllib.error.HTTPError as e:return e.code,json.load(e)
_,health=request('health');status,result=request('simulate',method)
report={'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'origin':origin,'health':health,'legacy_simulation_http':status,'baseline':baseline}
if baseline:
 assert status==422
 report['validation_errors']=result['detail'];report['status']='REPRODUCED_LEGACY_422'
else:
 assert status==200,result
 assert len(result['order'])==3 and len({p['rt_min'] for p in result['peaks']})==3 and all(max(t['y'])>0 for t in result['traces'])
 assert [p['source'] for p in result['peaks']]==['model_based','model_based','unknown_legacy']
 assert [p['mixture_fraction'] for p in result['peaks']]==[.5,.3,.2]
 assert result['input']['compounds'][2]['source_legacy']=='historic unknown label'
 report.update(status='PASS',rt_min=[p['rt_min'] for p in result['peaks']],areas=[p['peak_area'] for p in result['peaks']],source_codes=[p['source'] for p in result['peaks']])
 method['compounds'][1]['s']=-1;code,invalid=request('simulate',method);assert code==422 and invalid['detail'][0]['loc']==['body','compounds',1,'s'];report['specific_validation_error']=invalid['detail'][0]['loc']
 _,conditions=request('retention/conditions');scope=conditions['scope'];smiles='CC(=O)Nc1ccc(OCCC)cc1'
 qm={'mode':scope['mode'],'workflow':'structure','compounds':[{'id':'nonlookup','name':'Non-database QSRR test','smiles':smiles}],
     'column':{'stationary_phase':scope['stationary_phase'],'temperature_c':scope['temperature_c'],'particle_um':conditions['particle_um']},
     'mobile':{'a':scope['mobile_a'],'b':scope['mobile_b'],'buffer':scope['buffer'],'ph':scope['ph'],'ph_control':scope['ph_control']},
     'gradient':[{'time_min':t,'b_percent':b,'temperature_c':scope['temperature_c']} for t,b in [(0,20),(10,50),(20,50)]]}
 code,prediction=request('retention/predict',{'smiles':smiles,'method':qm,'model_id':'auto'})
 assert code==200 and prediction['status']=='Experimental model prediction' and prediction['logkw'] is not None and 'observations' not in prediction and not prediction['applicability']['seen_in_training']
 code,qsrr_sim=request('simulate',qm);assert code==200 and len(qsrr_sim['order'])==1 and qsrr_sim['resolved_compounds'][0]['source']=='experimental_model_prediction'
 report['non_database_qsrr']={'smiles':smiles,'logkw':prediction['logkw'],'s':prediction['s'],'rt_min':qsrr_sim['peaks'][0]['rt_min'],'observations_returned':False,'seen_in_training':False,'status':prediction['status'],'experimental_accuracy':'Not established'}

path=pathlib.Path(__file__).resolve().parents[1]/'artifacts'/('repair-baseline-422.json' if baseline else 'public-repair-smoke.json');path.write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report,indent=2),flush=True)
