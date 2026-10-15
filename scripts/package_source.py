"""Package corresponding source without local secrets, environments or user data."""
import pathlib,tarfile,os
root=pathlib.Path(__file__).resolve().parents[1];out=root/'artifacts';out.mkdir(exist_ok=True)
dirs=['backend','frontend','third_party','scripts','docs','.github','database','data']
files=['.gitattributes','LICENSE','NOTICE.md','README.md','Dockerfile','compose.yaml','render.yaml','.env.example','.dockerignore','.gitignore','pyproject.toml']
paths=[root/f for f in files if (root/f).is_file()]
for directory in dirs:
 for folder,subdirs,filenames in os.walk(root/directory):
  subdirs[:]=[x for x in subdirs if x not in ['node_modules','dist','__pycache__','.venv','.pytest_cache']]
  for filename in filenames:
   p=pathlib.Path(folder)/filename
   if p.suffix!='.pyc':paths.append(p)
with tarfile.open(out/'source.tar.gz','w:gz') as tar:
 for p in sorted(paths):tar.add(p,arcname='EluSim_V2/'+p.relative_to(root).as_posix(),recursive=False)
print('Corresponding Source archive:',len(paths),'files')
