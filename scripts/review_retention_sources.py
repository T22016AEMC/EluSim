import json,pathlib,urllib.request
root=pathlib.Path(__file__).resolve().parents[1]
urls={'isocratic-repo':'https://api.github.com/repos/wiczling/isocratic-qsrr','isocratic-tree':'https://api.github.com/repos/wiczling/isocratic-qsrr/git/trees/main?recursive=1','bmc-xml':'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC9635186/fullTextXML'}
for key,url in urls.items():
 try:
  raw=urllib.request.urlopen(url,timeout=30).read();(root/'artifacts'/(key+'.txt')).write_bytes(raw);print(key,len(raw))
 except Exception as e:print(key,str(e))
