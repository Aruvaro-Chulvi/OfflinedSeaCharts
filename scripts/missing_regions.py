"""Qué cuadros de 10° faltan por bajar de Overpass y qué extractos de Geofabrik los
cubren (para completar con extract_pbf.py cuando Overpass no responde).

    python missing_regions.py      # → work/missing.json {"cells": [[w, s]…], "regions": [id…]}
"""
import json
import os
import re
import sys
from pathlib import Path

from shapely.geometry import Polygon, box, shape
from shapely.ops import unary_union
from shapely.prepared import prep

HERE = Path(__file__).resolve().parent
WORK = Path(os.environ.get("SEACHARTS_WORK") or (HERE / "work"))
ZONES = Path(os.environ.get("CHART_ZONES") or r"C:\SurvivalAI-phi4\frontend\geo\chart_zones.json")
RX = re.compile(r"^([+-][\d.]+)_([+-][\d.]+)_([\d.]+)\.json\.gz$")
STEP = 10


def main():
    zones = json.loads(ZONES.read_text(encoding="utf-8"))["zones"]
    area = prep(unary_union([Polygon([(r[i], r[i + 1]) for i in range(0, len(r), 2)]).buffer(0)
                             for z in zones.values() for r in z["p"]]))
    got = []
    for p in (WORK / "tiles").iterdir():
        m = RX.match(p.name)
        if m:
            w, s, st = map(float, m.groups())
            got.append(box(w, s, w + st, min(s + st, 90.0)))
    done = unary_union(got).buffer(1e-9)
    cells = [(w, s) for s in range(-80, 90, STEP) for w in range(-180, 180, STEP)
             if area.intersects(box(w, s, w + STEP, min(s + STEP, 90)))
             and not done.contains(box(w, s, w + STEP, min(s + STEP, 90)))]
    missing = unary_union([box(w, s, w + STEP, min(s + STEP, 90)) for w, s in cells])
    idx = json.loads((WORK / "geofabrik-index.json").read_text(encoding="utf-8"))
    regions = []
    for f in idx["features"]:
        pr = f["properties"]
        if pr.get("parent") or not f.get("geometry"):
            continue
        g = shape(f["geometry"]).buffer(0)
        if g.intersects(missing):
            share = g.intersection(missing).area / missing.area
            regions.append((pr["id"], round(share * 100, 1), pr["urls"]["pbf"]))
    regions.sort(key=lambda r: -r[1])
    (WORK / "missing.json").write_text(json.dumps({"cells": cells, "regions": [r[0] for r in regions],
                                                   "urls": {r[0]: r[2] for r in regions}}), encoding="utf-8")
    print(f"{len(cells)} cuadros sin bajar")
    for r in regions:
        print(f"  {r[0]}: {r[1]} % de lo que falta")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
