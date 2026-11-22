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
try:
    import anim_ep01
    SERIES.setdefault("looks", {}).update(anim_ep01.LOOKS)
    ep1 = next(e for e in eps if e["n"] == 1)
    assert len(anim_ep01.ANIM) == len(ep1["scenes"]), "un plan animé par scène"
    for sc, a in zip(ep1["scenes"], anim_ep01.ANIM):
        sc["anim"] = a
except ImportError:
    pass
json.dump({"series": SERIES, "episodes": eps}, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
for e in eps:
    print(e["n"], len(e["scenes"]), sum(len(l["t"].split()) for s in e["scenes"] for l in s["lines"]))
