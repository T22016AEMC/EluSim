import urllib.request,pathlib,hashlib
root=pathlib.Path(__file__).resolve().parents[1]
for key,url in {'original-isocratic.csv':'https://www.retentionprediction.org/hplc/database/isocratic_database.csv','original-isocratic-license.html':'https://www.retentionprediction.org/hplc/database/'}.items():
 raw=urllib.request.urlopen(url,timeout=30).read();(root/'artifacts'/key).write_bytes(raw);print(key,len(raw),hashlib.sha256(raw).hexdigest())
