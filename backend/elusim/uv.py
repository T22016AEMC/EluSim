"""Independent UV-Vis inference. No arbitrary Gaussian reconstruction or LC intensity coupling."""
import csv,io,hashlib,math
import numpy as np
from scipy.signal import find_peaks
from .features import molecular_features
from .prediction import infer

def predict_uv(smiles,solvent=None,ph=None,start_nm=190,end_nm=800,resolution_nm=1):
 from .chemistry import describe
 features,_=molecular_features(smiles);screen={k:v for k,v in features['substructures'].items() if k in ['aromatic_ring','alkene','carbonyl','nitro','azo','conjugated_diene'] and v}
 r=infer('pnnl-uv-shape',smiles);r.update(structure_svg=describe(smiles=smiles)['svg'],chromophores=screen,screening_status='Qualitative screening',input_conditions={'smiles':smiles,'solvent':solvent,'ph':ph,'start_nm':start_nm,'end_nm':end_nm,'resolution_nm':resolution_nm},valid_range_nm=[220,400],spectrum=None,lambda_max_nm=None,bands=[],intensity_unit='normalized relative absorption (dimensionless)',molar_absorptivity_available=False)
 r['warnings']+=['220–400nm only; no prediction or zero padding outside valid range','Solvent and pH not annotated in training CSV; no solvent effect or pH response model','Window maximum may not be global λmax; intensity is not absolute absorbance or extinction coefficient']
 if solvent or ph is not None:r['status']='Insufficient data';r['prediction']=None;r['warnings'].append('Requested solvent/pH-conditioned prediction unsupported; omit conditions for dataset-specific shape screening')
 if not screen:r['status']='Qualitative screening';r['prediction']=None;r['warnings'].append('No matched UV chromophore: no strong artificial absorption band generated; far-UV absorption may still occur')
 if r['prediction'] is not None:
  lo=max(220,start_nm);hi=min(400,end_nm)
  if lo>=hi:r['status']='Unsupported';r['warnings'].append('View range does not overlap model range')
  else:
   values=np.array(r['prediction']);axis=np.arange(220,401);x=np.arange(lo,hi+1e-8,resolution_nm);y=np.interp(x,axis,values);r['spectrum']={'wavelength_nm':x.tolist(),'intensity':y.tolist(),'native_resolution_nm':1,'interpolation':resolution_nm!=1};r['lambda_max_nm']=float(axis[np.argmax(values)]);idx,_=find_peaks(values,prominence=.05);r['bands']=[{'wavelength_nm':int(axis[i]),'relative_intensity':float(values[i])} for i in idx]
 r.pop('prediction',None);return r

def import_spectrum(content,name,unit):
 rows=list(csv.DictReader(io.StringIO(content)))
 if not 2<=len(rows)<=2000:raise ValueError('Experimental spectrum needs 2–2000 points')
 try:x=[float(row['wavelength_nm']) for row in rows];y=[float(row['intensity']) for row in rows]
 except (ValueError,KeyError):raise ValueError('CSV needs wavelength_nm,intensity numeric columns')
 if any(not math.isfinite(a) for a in x+y) or any(not 100<=a<=2000 for a in x):raise ValueError('Finite wavelengths 100–2000nm and intensities required')
 if any(b<=a for a,b in zip(x,x[1:])):raise ValueError('Wavelengths must strictly increase; raw records are not silently sorted')
 return {'id':hashlib.sha256(content.encode()).hexdigest(),'name':name,'status':'Experimental','unit':unit,'wavelength_nm':x,'intensity':y,'original_csv':content,'transformations':[],'source':'User supplied; no automatic model training or overwrite'}
