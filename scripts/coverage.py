"""Qué países tienen ya bajados todos sus cuadros (sirve para publicar una release
parcial mientras fetch_tiles.py sigue con el resto).

    python coverage.py            # lista de ISO completos, en work/complete.json
"""
import json
import os
import re
import sys
from pathlib import Path

from shapely.geometry import Polygon, box
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
WORK = Path(os.environ.get("SEACHARTS_WORK") or (HERE / "work"))
ZONES = Path(os.environ.get("CHART_ZONES") or r"C:\SurvivalAI-phi4\frontend\geo\chart_zones.json")
RX = re.compile(r"^([+-][\d.]+)_([+-][\d.]+)_([\d.]+)\.json\.gz$")


def main():
    boxes = []
    for p in (WORK / "tiles").iterdir():
        m = RX.match(p.name)
        if m:
            w, s, step = map(float, m.groups())
            boxes.append(box(w, s, w + step, min(s + step, 90.0)))
    done = unary_union(boxes).buffer(1e-9)
    zones = json.loads(ZONES.read_text(encoding="utf-8"))["zones"]
    ok = []
    for iso, z in zones.items():
        polys = [Polygon([(r[i], r[i + 1]) for i in range(0, len(r), 2)]).buffer(0) for r in z["p"]]
        if all(done.contains(p) for p in polys):
            ok.append(iso)
    ok.sort()
    (WORK / "complete.json").write_text(json.dumps(ok), encoding="utf-8")
    print(f"{len(ok)} de {len(zones)} países completos")
    print(" ".join(ok))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
