"""Train a scoped LSS adapter only from identifiable, licensed experimental curves.
Usage: python scripts/train_lss_model.py curves.json
JSON list: each entry is >=2 same-compound/scope observations accepted by retention_data.
No synthetic production artifacts are supplied.
"""
import sys,pathlib,json
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from elusim.retention_data import fit_retention_curve
from train_v2_models import train
if __name__=='__main__':
 curves=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf8'));labels=[fit_retention_curve(rows) for rows in curves]
 if len({r['smiles'] for r in labels})<40:raise ValueError('At least 40 distinct experimental structures required; still experimental validation, not universal applicability')
 scopes={json.dumps(r['scope'],sort_keys=True) for r in labels}
 if len(scopes)!=1:raise ValueError('Train independent artifacts for different scopes')
 scope=labels[0]['scope'];report=train('lss-parameters',[r['smiles'] for r in labels],[[r['logkw'],r['s']] for r in labels],{'output':'lss_parameters','dataset':'User supplied identifiable experimental retention curves','dataset_source':list({o['source'] for r in labels for o in r['observations']}),'license':list({o['license'] for r in labels for o in r['observations']}),'scope':scope,'external_validation':'scaffold-heldout labels; independent laboratory validation still required'})
 (ROOT/'data/v2/lss-training-labels.json').write_text(json.dumps(labels,indent=2),encoding='utf8')
