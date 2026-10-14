"""Real HTTPS tests: no local endpoint accepted; infer unseen recorded test inputs."""
import sys,pathlib,json,urllib.request,urllib.parse,datetime
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from elusim.schemas import Simulation,Compound,Node,Column,Mobile
from elusim.prediction import report_method
url=sys.argv[1].rstrip('/');u=urllib.parse.urlparse(url)
if u.scheme!='https' or not u.hostname or u.hostname in ['localhost','127.0.0.1']:raise SystemExit('Public HTTPS origin required')
def req(path,data=None):
 request=urllib.request.Request(url+path,data=json.dumps(data).encode() if data else None,headers={'Content-Type':'application/json'} if data else {})
 with urllib.request.urlopen(request,timeout=90) as response:return json.loads(response.read())
result={'origin':url,'date_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'physical_phone_test':False}
try:
 result['health']=req('/api/health');assert result['health']['app']=='EluSim_V2'
 result['models']=[m['model_id'] for m in req('/api/models')['models']]
 inputs=json.loads((ROOT/'frontend/tests/v2-inputs.json').read_text())
 template=report_method();m=Simulation(compounds=[Compound(id='x',name='Heldout SMILES')],column=Column(**template['column']),mobile=Mobile(**template['mobile']),gradient=[Node(**n) for n in template['gradient']])
 r=req('/api/retention/predict',{'smiles':inputs['report0259-rt'],'method':m.model_dump()});assert r['rt_min']>0 and r['logkw'] is None;result['retention']={'rt_min':r['rt_min'],'status':r['status'],'applicability':r['applicability']}
 m.column.length_mm=150;assert req('/api/retention/predict',{'smiles':inputs['report0259-rt'],'method':m.model_dump()})['rt_min'] is None;result['method_abstention']=True
 r=req('/api/uv/predict',{'smiles':inputs['pnnl-uv-shape']});assert r['model']['model_version']=='2.0.1' and r['model']['license']=='CC-BY-4.0';assert r['spectrum'] and len(r['spectrum']['intensity'])==181 and r['spectrum']['wavelength_nm'][0]==220 and r['spectrum']['wavelength_nm'][-1]==400;result['uv']={'model_id':r['model']['model_id'],'model_version':r['model']['model_version'],'data_license':r['model']['license'],'window_max_nm':r['lambda_max_nm'],'points':181,'status':r['status'],'unit':r['intensity_unit']}
 assert req('/api/uv/predict',{'smiles':'CCCC'})['spectrum'] is None;result['no_fake_uv']=True
 raw='wavelength_nm,intensity\n220,-0.01\n400,0.5\n';r=req('/api/uv/import',{'content':raw,'name':'Public QA synthetic import','unit':'absorbance'});assert r['original_csv']==raw and r['intensity'][0]==-.01;result['raw_import_preserved']=True
 result['status']='PASS_PUBLIC_V2_SMOKE'
except Exception as exc:result['status']='FAILED';result['error']=str(exc)
(ROOT/'artifacts').mkdir(exist_ok=True);(ROOT/'artifacts/public-v2-smoke.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result,indent=2));raise SystemExit(result['status']=='FAILED')
