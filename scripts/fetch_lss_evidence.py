"""Fetch public Figshare metadata by exact paper title; never guess record IDs."""
import urllib.request,json,pathlib
root=pathlib.Path(__file__).resolve().parents[1]
query={'search_for':'In Silico High-Performance Liquid Chromatography Method Development via Machine Learning','limit':10}
r=urllib.request.Request('https://api.figshare.com/v2/articles/search',data=json.dumps(query).encode(),headers={'Content-Type':'application/json'})
results=json.load(urllib.request.urlopen(r,timeout=30))
(root/'artifacts/lss-search.json').write_text(json.dumps(results,indent=2))
for a in results:print(a['id'],a['title'],a['url'])

for a in results:
 detail=json.load(urllib.request.urlopen(a['url'],timeout=30))
 (root/'artifacts'/('lss-record-'+str(a['id'])+'.json')).write_text(json.dumps(detail,indent=2))
 print('LICENSE',detail.get('license'))
 for f in detail['files']:
  print(f)
  if f['name'].endswith('.xlsx'):
   content=urllib.request.urlopen(f['download_url'],timeout=30).read()
   (root/'artifacts'/f['name']).write_bytes(content)
