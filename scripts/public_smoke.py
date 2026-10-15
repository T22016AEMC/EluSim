"""Test only an explicitly provided public HTTPS origin, never invent a URL."""
import sys,json,urllib.request,urllib.parse,pathlib,datetime,copy
root=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'backend'))
from elusim.schemas import Simulation,Compound,Node
url=sys.argv[1] if len(sys.argv)>1 else ''
u=urllib.parse.urlparse(url)
if u.scheme!='https' or not u.hostname or u.hostname in ['localhost','127.0.0.1'] or u.hostname.startswith(('192.168.','10.')):raise SystemExit('Explicit public HTTPS origin required')
origin=url.rstrip('/');result={'origin':origin,'tested_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actual_phone_cellular_test':'not performed','checks':{}}
def request(path,data=None):
 req=urllib.request.Request(origin+path,data=json.dumps(data).encode() if data else None,headers={'Content-Type':'application/json'} if data else {})
 with urllib.request.urlopen(req,timeout=60) as r:return r.status,r.read()
try:
 status,body=request('/');assert status==200 and b'<html' in body;result['checks']['site']=True
 status,body=request('/api/health');health=json.loads(body);assert health['rdkit'];result['checks']['health']=health
 _,body=request('/api/compounds/describe',{'name':'caffeine'});assert json.loads(body)['formula']=='C8H10N4O2';result['checks']['rdkit']=True
 cfg=Simulation(compounds=[Compound(id=str(i),name='Synthetic '+str(i),logkw=2+i*.5,s=4+i*.5) for i in range(3)],gradient=[Node(time_min=0,b_percent=5),Node(time_min=10,b_percent=95),Node(time_min=20,b_percent=95)]).model_dump()
 _,body=request('/api/simulate',cfg);sim=json.loads(body);assert len(sim['order'])==3 and len(sim['traces'])==3;result['checks']['simulation']=True
 variants={}
 slower=copy.deepcopy(cfg);slower['gradient'][1]['time_min']=15;slower['gradient'][-1]['time_min']=25;variants['slower_gradient']=slower
 faster=copy.deepcopy(cfg)
 for node in faster['gradient']:node['flow_ml_min']=.6
 variants['higher_flow']=faster
 longer=copy.deepcopy(cfg);longer['column']['length_mm']=150;variants['longer_column']=longer
 times={}
 for label,method in variants.items():
  _,body=request('/api/simulate',method);value=json.loads(body)['peaks'][0]['rt_min'];times[label]=value
 baseline=sim['peaks'][0]['rt_min'];assert times['slower_gradient']>baseline and times['longer_column']>baseline and times['higher_flow']<baseline
 result['checks']['online_sensitivity']={'baseline_rt_min':baseline,**times}
 _,body=request('/api/optimize',{'simulation':cfg,'durations_min':[8,12],'starts_percent':[5],'ends_percent':[95]});assert len(json.loads(body)['candidates'])==2;result['checks']['optimization']=True
 _,body=request('/api/source');assert body[:2]==b'\x1f\x8b';result['checks']['corresponding_source']=True
 result['status']='PASS_PUBLIC_API_SMOKE'
except Exception as exc:result.update(status='FAILED',error=str(exc))
(root/'artifacts/public-smoke.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result,indent=2));raise SystemExit(result['status']=='FAILED')
