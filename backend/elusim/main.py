import os,pathlib,time,threading
from collections import OrderedDict,deque
from typing import Literal
from fastapi import FastAPI,UploadFile,File,HTTPException,Request
from fastapi.responses import FileResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field,model_validator
from .schemas import Strict, Simulation, Optimize, Calibration
from .engine import MODES,MODEL
from .chemistry import describe,import_file
from .jobs import compute

ROOT=pathlib.Path(__file__).resolve().parents[2]
app=FastAPI(title='EluSim_V2',version='2.1.0')
_rates=OrderedDict();_rate_lock=threading.Lock()

@app.middleware('http')
async def limits(request:Request,call_next):
 if request.url.path.startswith('/api/') and request.method=='POST':
  ip=request.client.host if request.client else 'unknown';now=time.monotonic()
  with _rate_lock:
   visits=_rates.setdefault(ip,deque())
   while visits and now-visits[0]>60:visits.popleft()
   if len(visits)>=30:return JSONResponse({'detail':'Rate limit: 30 requests/minute'},429)
   visits.append(now);_rates.move_to_end(ip)
   if len(_rates)>1024:_rates.popitem(last=False)
  chunks=[];size=0
  async for chunk in request.stream():
   size+=len(chunk)
   if size>1048576:return JSONResponse({'detail':'Request limit: 1 MiB'},413)
   chunks.append(chunk)
  request._body=b''.join(chunks)
 response=await call_next(request)
 response.headers['X-Content-Type-Options']='nosniff'
 response.headers['X-Frame-Options']='DENY'
 response.headers['Referrer-Policy']='same-origin'
 response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; worker-src 'self' blob:; frame-ancestors 'none'"
 return response

@app.exception_handler(ValueError)
async def bad_value(request,exc):return JSONResponse({'detail':str(exc)},422)
@app.exception_handler(TimeoutError)
async def timed_out(request,exc):return JSONResponse({'detail':str(exc)},504)
@app.exception_handler(RuntimeError)
async def busy(request,exc):return JSONResponse({'detail':str(exc)},503)

@app.get('/api/health')
def health():
 from rdkit import rdBase
 return {'status':'ok','app':'EluSim_V2','engine':MODEL,'rdkit':rdBase.rdkitVersion,'revision':os.getenv('SOURCE_REVISION',os.getenv('RENDER_GIT_COMMIT','local-unreleased'))}

@app.get('/api/library')
def library():return {'modes':MODES,'structure_models':[],'columns':[{'name':'Generic C18 100 × 2.1 mm','manufacturer':'Generic','stationary_phase':'Generic C18','length_mm':100,'diameter_mm':2.1,'particle_um':1.7,'pore_angstrom':100,'porosity':.68,'plates':12000,'temperature_c':25}],'notice':'Generic geometry only; no commercial selectivity claim'}

class Structure(Strict):
 smiles:str|None=Field(default=None,max_length=2000)
 name:str|None=Field(default=None,max_length=160)
 molblock:str|None=Field(default=None,max_length=100000)

@app.post('/api/compounds/describe')
def descriptors(req:Structure):return describe(req.smiles,req.name,req.molblock)

@app.post('/api/compounds/import')
async def upload(file:UploadFile=File(...)):
 content=await file.read(900001)
 if len(content)>900000:raise HTTPException(413,'File limit: 900 kB')
 try:decoded=content.decode('utf-8-sig')
 except UnicodeDecodeError:raise HTTPException(422,'UTF-8 file required')
 return {'compounds':import_file(decoded,file.filename or '')}

@app.post('/api/simulate')
def simulation(req:Simulation):return compute('simulation',req.model_dump())
@app.post('/api/optimize')
def optimization(req:Optimize):return compute('optimization',req.model_dump())
@app.post('/api/calibrate')
def calibration(req:Calibration):return compute('calibration',req.model_dump())

@app.get('/api/source')
def source():
 p=ROOT/'artifacts/source.tar.gz'
 if not p.exists():raise HTTPException(503,'Corresponding Source archive must be generated before release')
 return FileResponse(p,media_type='application/gzip',filename='EluSim_V2-source.tar.gz')

@app.get('/api/license')
def license_text():return FileResponse(ROOT/'LICENSE',media_type='text/plain')

@app.get('/api/reference/pylss')
def reference():return {'upstream':'gmrandazzo/PyLSS','commit':'d2cda850fa0b0881fc3cf1cd68c4d93b59dac04f','role':'Pinned optional scientific reference; independent migration solver is production engine','nlss_enabled':False,'zero_gradient_sentinel_used':False}


from .prediction import library as model_library,predict_retention
from .uv import predict_uv,import_spectrum
class RetentionInput(Strict):
 smiles:str=Field(min_length=1,max_length=2000)
 method:Simulation
 model_id:Literal['report0259-rt','lss-parameters','auto']='report0259-rt'
class UVInput(Strict):
 smiles:str=Field(min_length=1,max_length=2000)
 solvent:str|None=Field(default=None,max_length=120)
 ph:float|None=Field(default=None,ge=0,le=14)
 start_nm:float=Field(default=190,ge=100,le=1500)
 end_nm:float=Field(default=800,ge=101,le=1600)
 resolution_nm:float=Field(default=1,ge=.5,le=20)
 @model_validator(mode='after')
 def ordered(self):
  if self.end_nm<=self.start_nm:raise ValueError('End wavelength must exceed start wavelength')
  return self
class SpectrumInput(Strict):
 content:str=Field(max_length=180000)
 name:str=Field(default='Experimental spectrum',max_length=160)
 unit:Literal['absorbance','normalized relative absorption (dimensionless)','molar absorptivity (L mol^-1 cm^-1)']='absorbance'
@app.get('/api/models')
def models():return model_library()
@app.post('/api/retention/predict')
def retention_prediction(req:RetentionInput):
 if req.model_id in ['auto','lss-parameters']:
  from .retention_registry import predict_curve
  return predict_curve(req.smiles,req.method,use_literature=req.model_id=='auto')
 return predict_retention(req.smiles,req.method,req.model_id)
class ResolveRetention(Strict):
 method:Simulation
 overwrite_manual:bool=False
@app.post('/api/retention/resolve')
def resolve_retention(req:ResolveRetention):
 from .retention_registry import resolve_compounds
 prepared,records=resolve_compounds(req.method,req.overwrite_manual)
 return {'compounds':[c.model_dump() for c in prepared.compounds],'records':records,'workflow':'known'}
@app.get('/api/retention/database')
def retention_database():
 from .retention_registry import measured_curves
 rows=measured_curves()
 return {'scope':rows[0]['scope'],'phi_range':[.2,.5],'count':len(rows),'license':'CC-BY-NC-SA-3.0-US',
         'examples':[{'smiles':r['smiles'],'logkw':r['logkw'],'s':r['s'],'observations':r['observations']} for r in rows[:3]],
         'source':'https://www.retentionprediction.org/hplc/database/','noncommercial_only':True}
@app.post('/api/uv/predict')
def uv_prediction(req:UVInput):return predict_uv(**req.model_dump())
@app.post('/api/uv/import')
def uv_import(req:SpectrumInput):return import_spectrum(req.content,req.name,req.unit)

dist=ROOT/'frontend/dist'
if dist.exists():
 app.mount('/assets',StaticFiles(directory=dist/'assets'),name='assets')
 @app.get('/{path:path}')
 def frontend(path:str):
  if path.startswith('api/'):raise HTTPException(404,'Unknown API endpoint')
  candidate=(dist/path).resolve()
  if candidate.is_relative_to(dist.resolve()) and candidate.is_file():return FileResponse(candidate)
  return FileResponse(dist/'index.html')
