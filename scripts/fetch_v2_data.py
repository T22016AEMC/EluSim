import pathlib,json,urllib.request,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'data/v2';OUT.mkdir(parents=True,exist_ok=True)
files=[('PNNL-CompBio/ML_UVvisModels','b61855b53bdae841ac38b820554d8f8e2a412ace','Data/UV_w_SMILES.csv','uv_spectra.csv'),('PNNL-CompBio/ML_UVvisModels','b61855b53bdae841ac38b820554d8f8e2a412ace','LICENSE','UV-LICENSE'),('michaelwitting/RepoRT','9de8d603377bbb6cc0f74e250eb7533fd8874df1','example/0259_rtdata.tsv','0259_rtdata.tsv'),('michaelwitting/RepoRT','9de8d603377bbb6cc0f74e250eb7533fd8874df1','example/0259_metadata.tsv','0259_metadata.tsv'),('michaelwitting/RepoRT','9de8d603377bbb6cc0f74e250eb7533fd8874df1','example/0259_gradient.tsv','0259_gradient.tsv'),('michaelwitting/RepoRT','9de8d603377bbb6cc0f74e250eb7533fd8874df1','LICENSE','LC-LICENSE')]
manifest=[]
for repo,sha,p,name in files:
 url='https://raw.githubusercontent.com/'+repo+'/'+sha+'/'+p;req=urllib.request.Request(url,headers={'User-Agent':'EluSim-V2'});raw=urllib.request.urlopen(req,timeout=40).read();(OUT/name).write_bytes(raw);manifest.append({'file':name,'url':url,'sha256':hashlib.sha256(raw).hexdigest()});print(name,len(raw),raw[:800],flush=True)
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
