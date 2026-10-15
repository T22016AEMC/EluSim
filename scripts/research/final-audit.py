"""Persist source hashes, exact source-review locations, and environment license metadata."""
import pathlib,os,json,hashlib,re,urllib.request,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]; OUT=ROOT/'docs/research-evidence'; CACHE=pathlib.Path(os.environ['TEMP'])/'lc-gradient-research-20261013'
reviews={
'gmrandazzo__PyLSS':['src/pylss/ssengine.py','src/pylss/nlssengine.py','src/pylss/gradientutils.py','src/pylss/plotengine.py','src/pylss/optseparation.py','src/pylss/lsscoltransfer.py','tests/test_ssengine.py','tests/test_optimizer.py','tests/test_chromanalysis.py'],
'gurevichlab__grip':['grip/models/grip.py','grip/models/layers.py','grip_inference.py','grip/featurizers/system_descriptors.py'],
'sartorius-research__STLC':['stlc/lkm.py','stlc/grm.py','stlc/occ.py','examples/lkm/multi_component.py'],
'jonkeeley__openiex':['src/openiex/physics.py','src/openiex/system.py','src/openiex/solver.py','src/openiex/species.py','src/openiex/method.py','src/openiex/analysis.py'],
'boecker-lab__2-step':['dmpnn.py','dmpnn_graph.py','mpnranker2.py','predict.py','mapping.py','.github/workflows/test_container.yaml'],
'josiehong__TIMPANI':['timp/trainer/timp_trainer.py','timp/models/chrom_encoder.py','timp/models/graphormer_rt.py','timp/models/gnn.py','tests/test_chrom_encoder.py','tests/test_base_trainer.py','doc/RESULTS.md'],
'DLUT-datas__MDL-TL':['CPEncoder/Column Type Encoder/ColumnTypeEncoder.py','CPEncoder/Gradient Program Encoder/AutoEncoder.py','train_base_model/build.py','train_small_data/build.py','data_process/preprocess.py'],
'statisticalbiotechnology__NonlinearGradientsUI':['src/nonlineargradientsui/GradientCalculator.java','src/nonlineargradientsui/EludeWorker.java','src/nonlineargradientsui/MzOptimizer.java'],
'cadet__CADET-Core':['LICENSE.txt','pyproject.toml','src/libcadet/model/binding/StericMassActionBinding.cpp','src/libcadet/model/GeneralRateModel.cpp','test/GeneralRateModel.cpp','test/BindingModels.cpp'],
'fau-advanced-separations__CADET-Process':['CADETProcess/processModel/binding.py','CADETProcess/processModel/unitOperation.py','CADETProcess/simulator/cadetAdapter.py','CADETProcess/comparison/peaks.py','CADETProcess/optimization/optimizationProblem.py'],
'HopkinsLaboratory__Graphormer-RT':['graphormer/models/graphormer.py','graphormer/models/graphormerHILIC.py','graphormer/modules/graphormer_layers.py'],
'CompOmics__DeepLC':['deeplc/core.py','deeplc/_architecture.py','deeplc/calibration/simple.py','deeplc/_reference_selection.py'],
'michaelwitting__RepoRT':['LICENSE','README.md'],
'yufree__mzrtsim':['DESCRIPTION','R/mzmlsim.R','R/mzrtsim.R','tests/testthat/test-mzml-integrity.R'],
'jraysajulga__High-Performance-Liquid-Chromatography-Research-Programs':['simulation.java','matrix.java'],
'Jimbo994__AutoLC-BO':['license.md','rm_code/retention_model.py','rm_code/peak_width.py','rm_code/crf.py','bo_code/BO.py'],
'Qiong-Yang__GNN-TL':['model/train.py','model/transferlearning.py','model/preprocess.py'],
'julianealdag__hplc-retention-prediction':['src/hplc_rt/predictor.py','src/hplc_rt/features.py','src/hplc_rt/models.py','src/hplc_rt/splits.py','tests/test_predictor.py','docs/corrections.md']}
inventory={}
for repo,paths in reviews.items():
 rows=[]
 for path in paths:
  f=CACHE/repo/path
  if f.exists():
   raw=f.read_bytes(); lines=raw.decode('utf8',errors='replace').splitlines()
   symbols=[{'line':i+1,'symbol':s.strip()} for i,s in enumerate(lines) if re.match(r'\s*(def |class |public .*\(|.*ln_K_eq.*=|.*sol\.success.*)',s)]
   rows.append({'path':path,'sha256':hashlib.sha256(raw).hexdigest(),'lines':len(lines),'symbols':symbols})
  else: rows.append({'path':path,'error':'not downloaded / path absent'})
 inventory[repo]=rows
(OUT/'source-review-index.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding='utf8')
# Additional pinned commit dates from patch headers (API rate-limited).
for p in OUT.glob('extra-*.json'):
 d=json.loads(p.read_text(encoding='utf8'))
 if d.get('sha') and not d.get('commit_patch_header'):
  try:
   with urllib.request.urlopen('https://github.com/'+d['repo']+'/commit/'+d['sha']+'.patch',timeout=30) as response: text=response.read(16000).decode('utf8',errors='replace')
   d['commit_patch_header']=text.split('\n---\n')[0][:4000]
   p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
  except Exception as e: d['patch_error']=str(e)
 print(d['repo'],d.get('sha'),re.search(r'^Date: (.+)$',d.get('commit_patch_header',''),re.M).group(1) if re.search(r'^Date: (.+)$',d.get('commit_patch_header',''),re.M) else 'date unavailable')
print('CORE EXCERPTS')
for repo,paths in reviews.items():
 if repo not in ['Jimbo994__AutoLC-BO','Qiong-Yang__GNN-TL','julianealdag__hplc-retention-prediction']: continue
 for path in paths[:4]:
  f=CACHE/repo/path
  if f.exists():
   lines=f.read_text(encoding='utf8',errors='replace').splitlines()
   print(repo,path,'\n'+'\n'.join(str(i+1)+': '+s for i,s in enumerate(lines) if re.search(r'def |class |import |exp\(|log\(|predict|gradient|\.fit|\bLicense|CC |SMILES|Smiles|error|unknown|RandomForest|\.load|model_path|uncertain|clip',s))[:7500])
