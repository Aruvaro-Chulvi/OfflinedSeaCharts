"""Saca el balizamiento de un archivo .osm.pbf de OpenStreetMap (el planeta entero o
un extracto de Geofabrik), sin depender de los servidores de Overpass.

Lo mismo que pide fetch_tiles.py: node/way con seamark:type, node natural=reef|shoal|rock,
way natural=reef|shoal; las vías, por el centro de su recuadro (como «out center» de
Overpass). Dos pasadas: 1) objetos con esas etiquetas y los nodos que forman las vías,
2) solo las coordenadas de esos nodos. El filtrado va en C++ (pyosmium), así que el
planeta (~95 GB) se lee en una o dos horas.

    pip install osmium
    curl -L -o work/planet/planet-latest.osm.pbf https://download.bbbike.org/osm/planet/planet-latest.osm.pbf
    python extract_pbf.py work/planet/planet-latest.osm.pbf     # → work/planet/seamarks.json.gz + date.txt
"""
import gzip
import json
import os
import sys
import time
from pathlib import Path

import osmium
from osmium.filter import IdFilter, KeyFilter

NATURAL_NODE = {"reef", "shoal", "rock"}
NATURAL_WAY = {"reef", "shoal"}


def wanted(is_node: bool, tags: dict) -> bool:
    if tags.get("seamark:type"):
        return True
    return tags.get("natural") in (NATURAL_NODE if is_node else NATURAL_WAY)


def data_date(path: Path) -> str:
    """Fecha de los datos: la de la cabecera del PBF (si no, la del archivo)."""
    try:
        h = osmium.io.Reader(str(path), osmium.osm.osm_entity_bits.NOTHING).header()
        ts = h.get("osmosis_replication_timestamp") or h.get("timestamp")
        if ts:
            return ts[:10]
    except Exception:
        pass
    return time.strftime("%Y-%m-%d", time.gmtime(path.stat().st_mtime))


def main(pbf: Path) -> None:
    out = pbf.parent
    t0 = time.time()
    feats, ways, need = [], {}, set()
    fp = (osmium.FileProcessor(str(pbf), osmium.osm.NODE | osmium.osm.WAY)
          .with_filter(KeyFilter("seamark:type", "natural")))
    for i, o in enumerate(fp):
        tags = {t.k: t.v for t in o.tags}
        if o.is_node():
            if wanted(True, tags) and o.location.valid():
                feats.append({"type": "node", "id": o.id, "lon": o.location.lon, "lat": o.location.lat, "tags": tags})
        elif wanted(False, tags):
            refs = [n.ref for n in o.nodes]
            ways[o.id] = (tags, refs)
            need.update(refs)
        if i % 5_000_000 == 0 and i:
            print(f"  1.ª pasada: {i:,} objetos · {len(feats):,} nodos · {len(ways):,} vías · {time.time() - t0:.0f} s", flush=True)
    print(f"1.ª pasada: {len(feats):,} nodos, {len(ways):,} vías, {len(need):,} nodos de vías · {time.time() - t0:.0f} s", flush=True)

    loc = {}
    for n in osmium.FileProcessor(str(pbf), osmium.osm.NODE).with_filter(IdFilter(need)):
        if n.location.valid():
            loc[n.id] = (n.location.lon, n.location.lat)
    print(f"2.ª pasada: {len(loc):,} coordenadas · {time.time() - t0:.0f} s", flush=True)

    for wid, (tags, refs) in ways.items():
        pts = [loc[r] for r in refs if r in loc]
        if not pts:
            continue
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        feats.append({"type": "way", "id": wid, "lon": round((min(xs) + max(xs)) / 2, 7),
                      "lat": round((min(ys) + max(ys)) / 2, 7), "tags": tags})

    tmp = out / "seamarks.json.gz.tmp"
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(feats, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, out / "seamarks.json.gz")
    (out / "date.txt").write_text(data_date(pbf), encoding="utf-8")
    print(f"Hecho: {len(feats):,} señales · datos del {data_date(pbf)} · {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]).resolve())
