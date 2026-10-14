"""Verify PNNL raw spectra against original CC BY4 experimental data, not code license."""
import pathlib,zipfile,csv,io,json,hashlib,urllib.request
import numpy as np
from rdkit import Chem
ROOT=pathlib.Path(__file__).resolve().parents[1];out=ROOT/'docs/v2-evidence'
meta=json.loads(urllib.request.urlopen('https://api.figshare.com/v2/articles/15217512/versions/3',timeout=40).read());assert meta['license']['name']=='CC BY 4.0'
archive=ROOT/'artifacts/uv-original-dataset.zip'
if not archive.exists():archive.write_bytes(urllib.request.urlopen(meta['files'][0]['download_url'],timeout=90).read())
z=zipfile.ZipFile(archive);name='Datasets I, II, III spectra and SMILES/Dataset_I.csv';original=list(csv.DictReader(io.StringIO(z.read(name).decode('utf-8-sig'))));mapping={}
def canonical(s):
 mol=Chem.MolFromSmiles(s)
 return Chem.MolToSmiles(mol) if mol else None
for row in original:
 if not row.get('SMILES'):continue
 s=canonical(row['SMILES'])
 if s:
  values=[float(row['V'+str(i)]) for i in range(1,182)];mapping.setdefault(s,[]).append((row['Molecule_ID'],(np.array(values)-min(values))/max(1e-20,max(values)-min(values))))
full_path=ROOT/'artifacts/pnnl-original-uv.csv'
if not full_path.exists():full_path.write_bytes(urllib.request.urlopen('https://raw.githubusercontent.com/PNNL-CompBio/ML_UVvisModels/b61855b53bdae841ac38b820554d8f8e2a412ace/Data/UV_w_SMILES.csv',timeout=40).read())
raw=list(csv.reader(full_path.open(encoding='utf8')));matches=[];unmatched=[]
for index,row in enumerate(raw):
 s=canonical(row[0]);ys=np.array([float(x) for x in row[1:]]);found=[(mid,float(np.max(np.abs(y-ys)))) for mid,y in mapping.get(s,[]) if np.allclose(y,ys,atol=1e-6,rtol=1e-6)]
 if found:matches.append({'row':index,'original_id':found[0][0],'max_difference':found[0][1]})
 else:unmatched.append({'row':index,'smiles':row[0]})
report={'source_doi':meta['doi'],'source_url':meta['url_public_html'],'license':meta['license'],'authors':[a['full_name'] for a in meta['authors']],'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'archive_download_url':meta['files'][0]['download_url'],'member':name,'matched':len(matches),'raw_records':len(raw),'comparison':'Canonical isomeric SMILES and all181 normalized experimental spectral values; tolerance1e-6, minmax-normalized original rounded values','matches':matches,'unmatched':unmatched}
(out/'uv-data-provenance.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in report.items() if k not in ['matches','authors']},indent=2));
if '--filter' in __import__('sys').argv:
 source=ROOT/'data/v2/uv_spectra.csv';backup=full_path
 if not backup.exists():backup.write_bytes(source.read_bytes())
 accepted={m['row'] for m in matches};verified=[row for i,row in enumerate(raw) if i in accepted]
 with source.open('w',encoding='utf8',newline='') as f:csv.writer(f,lineterminator='\n').writerows(verified)
 report['deployment_records']=len(verified);report['excluded_from_training']=unmatched;report['source_full_sha256']=hashlib.sha256(backup.read_bytes()).hexdigest();report['verified_sha256']=hashlib.sha256(source.read_bytes()).hexdigest();report['transformation']='Remove only unmatched rows; numerical strings unmodified; full original retained in local artifacts and public upstream'
 (out/'uv-data-provenance.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 manifest_path=ROOT/'data/v2/manifest.json'
 manifest=json.loads(manifest_path.read_text(encoding='utf8'))
 for item in manifest:
  if item['file']=='uv_spectra.csv':item['original_sha256']=report['source_full_sha256'];item['sha256']=report['verified_sha256'];item['original_dataset_doi']=report['source_doi'];item['data_license']='CC-BY-4.0';item['excluded_rows']=[r['row'] for r in unmatched];item['processing']=report['transformation']
 manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf8')
 print('Filtered verified records:',len(verified))
elif unmatched:raise SystemExit('Data rights not resolved for all records; filter unmatched records before training')
