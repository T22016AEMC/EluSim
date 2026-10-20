import urllib.request,pathlib
root=pathlib.Path(__file__).resolve().parents[1]
u='https://www.cambridge.org/engage/chemrxiv/article-details/64d5b446dfabaf06ff14d19e'
raw=urllib.request.urlopen(u,timeout=30).read()
(root/'artifacts/neuekuss-page.html').write_bytes(raw)
print(len(raw))
