"""Non-commercial experimental curve curation, never Rt->two-parameter inversion."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import sys,pathlib,csv,json,collections,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from elusim.retention_data import fit_retention_curve
from elusim.features import molecular_features
DATA=ROOT/'data/retention'
SCOPE={'mode':'RP','stationary_phase':'Agilent Eclipse Plus C18','mobile_a':'Water + 0.100% formic acid','mobile_b':'ACN','buffer':'0.100% formic acid in A and B','ph':None,'ph_control':'formulation','temperature_c':35}
SOURCE='https://www.retentionprediction.org/hplc/database/'
structure={int(line.split('\t')[1]):line.split('\t')[0] for line in (DATA/'smiles1026.smi').read_text().splitlines()}
curves=collections.defaultdict(list);excluded=[]
for row in csv.DictReader((DATA/'database_logk_1026.csv').open(),skipinitialspace=True):
 identity=int(row['ID']);phi=float(row['fi'])
 if not .2-1e-9<=phi<=.5+1e-9:continue
 curves[identity].append({**SCOPE,'smiles':structure[identity],'phi':phi,'logk':float(row['logk']),'source':SOURCE,'license':'CC-BY-NC-SA-3.0-US','original_compound_id':identity,'elution':'isocratic','logarithm_base':10})
labels=[]
for identity,rows in curves.items():
 try:
  if len({r['phi'] for r in rows})<4:raise ValueError('Fewer than four distinct measured compositions in 0.2–0.5')
  f=fit_retention_curve(rows)
  if f['fit_rmse_logk']>.1:raise ValueError('LSS representation error above 0.1 log10(k)')
  if molecular_features(f['smiles'])[0]['descriptors']['formal_charge']!=0:raise ValueError('Charged structures excluded: no independent ionization model')
  f.update(original_compound_id=identity,phi_range=[.2,.5],model_family='LSS',parameter_source='Least-squares fit of four measured isocratic log10(k) observations',reference=SOURCE,doi=None,applicability_domain={**SCOPE,'phi_range':[.2,.5],'particle_um':3.5},validation_status='Literature-derived; fit residual is not external gradient validation');labels.append(f)
 except ValueError as e:excluded.append({'id':identity,'reason':str(e)})
(DATA/'curves.json').write_text(json.dumps(labels,indent=2),encoding='utf8')
report={'scope':SCOPE,'phi_range':[.2,.5],'rows':sum(len(r['observations']) for r in labels),'curves':len(labels),'unique_structures':len({r['smiles'] for r in labels}),'excluded':excluded,'source':SOURCE,'license':'CC-BY-NC-SA-3.0-US','source_commit':'2951822d97bd76eeeb244989c9e1691ca4a1ff88','raw_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in DATA.glob('*.csv')},'limitations':['Original pH is formulation-defined and varies with solvent fraction; no pKa/logD estimated','LSS range limited to 20–50% ACN; pure-water intercept is extrapolation','Original isocratic Rt/t0 not supplied in curated logk data; no independent gradient accuracy claim']}
(ROOT/'docs/v2-evidence/retention-curve-curation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='excluded'}),flush=True)
