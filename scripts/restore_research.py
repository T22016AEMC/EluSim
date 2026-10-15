"""Import user-supplied research without deleting or overwriting its source."""
import pathlib,shutil
root=pathlib.Path.cwd();source=root/'調查報告'
for relative in ['docs','scripts/research']:
 src=source/relative;dst=root/relative
 if not src.is_dir():raise FileNotFoundError(src)
 for p in src.rglob('*'):
  if p.is_file():
   target=dst/p.relative_to(src)
   if target.exists():continue
   target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
print('Imported missing research files; original folder and ZIP preserved')
