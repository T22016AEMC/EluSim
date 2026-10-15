import urllib.request,pathlib
root=pathlib.Path(__file__).resolve().parents[1]
sha='2951822d97bd76eeeb244989c9e1691ca4a1ff88'
for name in ['LICENSE','README.md','data/deliv/database_logk_1026.csv','data/deliv/smiles1026.smi','data/deliv/pH.csv']:
 raw=urllib.request.urlopen('https://raw.githubusercontent.com/wiczling/isocratic-qsrr/'+sha+'/'+name,timeout=30).read()
 (root/'artifacts'/('iso-'+name.rsplit('/',1)[-1])).write_bytes(raw)
 print(name,len(raw))
