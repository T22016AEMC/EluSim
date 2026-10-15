import pathlib
root=pathlib.Path(__file__).resolve().parents[1]
(root/'frontend/pnpm-workspace.yaml').write_text('packages:\n  - .\nallowBuilds:\n  esbuild: true\n',encoding='utf8')
p=root/'backend/elusim/engine.py';s=p.read_text(encoding='utf8');s=s.replace("return {'model':MODEL,'mode':req.mode,", "return {'input':req.model_dump(),'model':MODEL,'mode':req.mode,");p.write_text(s,encoding='utf8')
print('Normalized build settings and added immutable simulation inputs')
