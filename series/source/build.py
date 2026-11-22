import json, sys, importlib
from header import SERIES
eps = []
for mod in sys.argv[2:]:
    m = importlib.import_module(mod)
    eps += m.EPISODES
extra = {}
for mod in ("extra01_10",):
    extra.update(importlib.import_module(mod).EXTRA)
for e in eps:
    for pos, sc in sorted(extra.get(e["n"], []), key=lambda x: -x[0]):
        e["scenes"].insert(pos, sc)
json.dump({"series": SERIES, "episodes": eps}, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
for e in eps:
    print(e["n"], len(e["scenes"]), sum(len(l["t"].split()) for s in e["scenes"] for l in s["lines"]))
