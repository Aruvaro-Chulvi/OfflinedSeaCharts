"""Reparte por países lo bajado con fetch_tiles.py y prepara la release.

Cada señal va a todos los países en cuya zona cae (Marine Regions «eez_land»:
tierra + zona económica exclusiva; en la frontera dos zonas pueden solaparse),
igual que hacía Offlined al pedir un país a Overpass. Escribe en work/release/:

  seamarks-<ISO>.json.gz   {"key", "date", "count", "features": [[id, lon, lat, {tags}], …]}
  manifest.json            paquetes con tamaño, MD5 y número de señales

    python build_packs.py osm-2026-11-01
"""
import gzip
import hashlib
import json
import os
import sys
from pathlib import Path

from shapely import STRtree
from shapely.geometry import Point, Polygon

HERE = Path(__file__).resolve().parent
WORK = Path(os.environ.get("SEACHARTS_WORK") or (HERE / "work"))
ZONES = Path(os.environ.get("CHART_ZONES") or r"C:\SurvivalAI-phi4\frontend\geo\chart_zones.json")
REPO = "Aruvaro-Chulvi/OfflinedSeaCharts"


def main(tag: str) -> None:
    date = (WORK / "fetched.txt").read_text(encoding="utf-8").strip()
    zones = json.loads(ZONES.read_text(encoding="utf-8"))["zones"]
    polys, owner = [], []
    for iso, z in zones.items():
        for r in z["p"]:
            polys.append(Polygon([(r[i], r[i + 1]) for i in range(0, len(r), 2)]).buffer(0))
            owner.append(iso)
    tree = STRtree(polys)

    # Todas las señales, una vez (los cuadros vecinos no se solapan, pero por si acaso)
    feats = {}
    for p in sorted((WORK / "tiles").glob("*.json.gz")):
        with gzip.open(p, "rt", encoding="utf-8") as f:
            for x in json.load(f):
                if x["lon"] is None or x["lat"] is None:
                    continue
                feats[f'{x["type"]}/{x["id"]}'] = (round(x["lon"], 7), round(x["lat"], 7), x["tags"])
    print(f"{len(feats)} señales")

    packs = {}
    for fid, (lon, lat, tags) in feats.items():
        pt = Point(lon, lat)
        for i in tree.query(pt, predicate="intersects"):
            lst = packs.setdefault(owner[i], {})
            lst[fid] = [fid, lon, lat, tags]

    out = WORK / "release"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("seamarks-*.json.gz"):
        old.unlink()
    man = {"name": "Offlined Sea Charts", "version": tag, "data_date": date,
           "base_url": f"https://github.com/{REPO}/releases/download/{tag}/",
           "attribution": "© OpenStreetMap contributors", "license": "ODbL-1.0", "packs": {}}
    for iso in sorted(packs):
        items = sorted(packs[iso].values())
        name = f"seamarks-{iso}.json.gz"
        raw = json.dumps({"key": iso, "date": date, "count": len(items), "features": items},
                         ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        data = gzip.compress(raw, 9, mtime=0)
        (out / name).write_bytes(data)
        man["packs"][iso] = {"file": name, "size": len(data), "md5": hashlib.md5(data).hexdigest(), "count": len(items)}
    (out / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    total = sum(p["size"] for p in man["packs"].values())
    print(f"{len(man['packs'])} países · {total / 1e6:.0f} MB → {out}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
