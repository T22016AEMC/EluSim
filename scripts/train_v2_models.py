"""Offline training only. Safe JSON export: no sklearn, pickle or torch in serving process."""
import os,sys,pathlib,csv,json,hashlib,gzip
os.environ['OPENBLAS_NUM_THREADS']='1'
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
import numpy as np
from elusim.features import molecular_features,VERSION
from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor,GradientBoostingRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.metrics import mean_absolute_error,mean_squared_error,r2_score
DATA=ROOT/'data/v2';OUT=ROOT/'backend/models'
def metrics(y,p):
 return {'mae':float(mean_absolute_error(y,p)),'rmse':float(np.sqrt(mean_squared_error(y,p))),'r2':float(r2_score(y,p))}
def tree(t):
 a=t.tree_;return {'left':a.children_left.tolist(),'right':a.children_right.tolist(),'feature':a.feature.tolist(),'threshold':a.threshold.tolist(),'value':[a.value[i,:,0].tolist() if a.children_left[i]==-1 else None for i in range(a.node_count)]}
def export(model):
 if isinstance(model,MultiOutputRegressor):return {'kind':'multioutput','outputs':[export(m) for m in model.estimators_]}
 if hasattr(model,'estimators_') and isinstance(model,RandomForestRegressor):return {'kind':'forest','trees':[tree(t) for t in model.estimators_]}
 if isinstance(model,GradientBoostingRegressor):return {'kind':'boosting','initial':float(model.init_.constant_[0,0]),'rate':float(model.learning_rate),'trees':[tree(t[0]) for t in model.estimators_]}
 scaler,reg=model.steps[0][1],model.steps[1][1];return {'kind':'ridge','mean':scaler.mean_.tolist(),'scale':scaler.scale_.tolist(),'coef':np.atleast_2d(reg.coef_).tolist(),'intercept':np.atleast_1d(reg.intercept_).tolist()}
def train(name,smiles,targets,meta):
 grouped={}
 for s,y in zip(smiles,targets):
  try:f,x=molecular_features(s)
  except ValueError:continue
  key=f['canonical_smiles'];grouped.setdefault(key,{'x':x,'ys':[]})['ys'].append(y)
 sm=sorted(grouped);X=np.array([grouped[s]['x'] for s in sm]);Y=np.array([np.mean(grouped[s]['ys'],axis=0) for s in sm]);groups=[MurckoScaffold.MurckoScaffoldSmiles(smiles=s) or s for s in sm]
 trainval,test=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=41).split(X,Y,groups));tr,va=next(GroupShuffleSplit(n_splits=1,test_size=.25,random_state=42).split(X[trainval],Y[trainval],np.array(groups)[trainval]));tr=trainval[tr];va=trainval[va]
 models={'ridge':make_pipeline(StandardScaler(),Ridge(alpha=10)),'random_forest':RandomForestRegressor(n_estimators=32,max_depth=8,min_samples_leaf=3,max_features=.7,random_state=42,n_jobs=1)}
 if Y.ndim==2 and Y.shape[1]==2:models['gradient_boosting']=MultiOutputRegressor(GradientBoostingRegressor(n_estimators=80,max_depth=2,min_samples_leaf=4,random_state=42))
 if Y.ndim==1:models['gradient_boosting']=GradientBoostingRegressor(n_estimators=80,max_depth=2,min_samples_leaf=4,random_state=42)
 scores={};trained={}
 for kind,m in models.items():m.fit(X[tr],Y[tr]);scores[kind]={'validation':metrics(Y[va],m.predict(X[va]))};trained[kind]=m
 winner=min(scores,key=lambda k:scores[k]['validation']['rmse']);m=trained[winner];pred=m.predict(X[test]);
 for kind,other in trained.items():scores[kind]['heldout_test']=metrics(Y[test],other.predict(X[test]))
 baseline=np.broadcast_to(np.mean(Y[tr],axis=0),Y[test].shape);base=metrics(Y[test],baseline)
 bits=X[tr,10:].astype(bool);counts=bits.sum(axis=1);sim=bits.astype(float)@bits.T.astype(float);sim=sim/np.maximum(1,counts[:,None]+counts[None,:]-sim);np.fill_diagonal(sim,0);threshold=float(np.quantile(sim.max(axis=1),.1))
 report={'model_id':name,'model_version':'2.0.0','feature_version':VERSION,'selected':winner,'selection':'validation RMSE; test never used for model choice','split':'Murcko scaffold groups, canonical duplicates aggregated; seeds41/42','counts':{'all':len(sm),'train':len(tr),'validation':len(va),'test':len(test)},'benchmark':scores,'heldout_mean_baseline':base,'beats_mean_baseline':scores[winner]['heldout_test']['rmse']<base['rmse'],'domain_threshold':threshold,'domain_rule':'10th percentile train leave-one-out maximum Morgan Tanimoto; descriptor min/max; not a confidence probability','test_smiles':[sm[i] for i in test],'train_smiles':[sm[i] for i in tr],'validation_smiles':[sm[i] for i in va],'external_study_validation':False,**meta}
 if Y.ndim==1:
  a=Y[test];b=pred;mask=np.abs(a[:,None]-a[None,:])>.01;upper=np.triu(mask,1);report['retention_order_accuracy']=float(np.mean(((a[:,None]-a[None,:])*(b[:,None]-b[None,:])>0)[upper])) if upper.any() else None
 elif Y.shape[1]>2:report['lambda_max_mae_nm']=float(np.mean(np.abs(np.argmax(Y[test],axis=1)-np.argmax(pred,axis=1))))
 from elusim.prediction import evaluate
 weights=export(m)
 for index in test:
  if not np.allclose(evaluate(weights,X[index]),np.atleast_1d(m.predict(X[index:index+1])[0]),atol=1e-6):raise ValueError('Safe export numerical parity failure')
 artifact={'metadata':report,'domain':{'min':X[tr,:10].min(axis=0).tolist(),'max':X[tr,:10].max(axis=0).tolist(),'fingerprints':bits.astype(int).tolist()},'weights':weights}
 OUT.mkdir(exist_ok=True);(OUT/(name+'.json.gz')).write_bytes(gzip.compress(json.dumps(artifact,separators=(',',':')).encode('utf8'),compresslevel=9,mtime=0));(ROOT/'docs/v2-evidence'/ (name+'-validation.json')).write_text(json.dumps(report,indent=2),encoding='utf8');print(name,json.dumps({k:v for k,v in report.items() if not k.endswith('smiles')}),flush=True)
 # all split assignments and original raw targets remain available; model not refit on test
 return report
if __name__=='__main__':
 lc=list(csv.DictReader((DATA/'0259_rtdata.tsv').open(encoding='utf-8-sig'),delimiter='\t'))
 train('report0259-rt',[r['pubchem.smiles.isomeric'] if r['pubchem.smiles.isomeric'] not in ['', 'NA'] else r['pubchem.smiles.canonical'] for r in lc],[float(r['rt']) for r in lc],{'output':'rt_min','dataset':'RepoRT0259','dataset_source':'https://github.com/michaelwitting/RepoRT/tree/9de8d603377bbb6cc0f74e250eb7533fd8874df1/example','license':'CC-BY-SA-4.0','scope':'Exact RepoRT0259 method only; no logKw/S, no gradient transfer; pH and dwell undocumented','cross_column_validation':'not performed; other methods rejected','cross_solvent_validation':'not performed; other solvents rejected'})
 uv=list(csv.reader((DATA/'uv_spectra.csv').open(encoding='utf8')))
 train('pnnl-uv-shape',[r[0] for r in uv],[[float(x) for x in r[1:]] for r in uv],{'output':'normalized_spectrum','dataset':'UV-adVISor Dataset I via PNNL: 930 verified records','model_version':'2.0.1','dataset_source':'https://github.com/PNNL-CompBio/ML_UVvisModels/tree/b61855b53bdae841ac38b820554d8f8e2a412ace/Data','license':'CC-BY-4.0','original_dataset_source':'https://doi.org/10.6084/m9.figshare.15217512.v3','wavelength_nm':list(range(220,401)),'intensity_unit':'normalized relative absorption (dimensionless), not molar absorptivity','scope':'Dataset-specific organic molecules, 220–400nm; solvent/pH unannotated in CSV; no solvent/pH adjustments','external_validation':'scaffold-heldout experimental records only; no independent laboratory dataset'})
