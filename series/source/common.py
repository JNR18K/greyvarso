def S(visual, *lines, chars=(), move=None, banner=None):
    sc = {"visual": visual, "chars": list(chars),
          "lines": [{"s": "narrateur", "t": l} if isinstance(l, str) else {"s": l[0], "t": l[1]} for l in lines]}
    if move: sc["move"] = move
    if banner:
        keys = ("label", "title", "subtitle", "color")
        sc["banner"] = dict(zip(keys, banner))
    return sc

def E(n, title, teaser, scenes, cover=None, pinned=None):
    e = {"n": n, "title": title, "teaser": teaser, "scenes": scenes}
    if cover: e["cover"] = cover
    if pinned: e["pinned"] = pinned
    return e
