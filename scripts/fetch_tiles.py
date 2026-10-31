"""Baja de OpenStreetMap (Overpass) el balizamiento de todo el planeta, en cuadros.

Lo mismo que Offlined pedía antes país a país desde cada ordenador, pero una sola
vez y con calma: un cuadro de 10° cada vez, una pausa entre consultas, esperas
crecientes si el servidor está lleno, y los cuadros ya bajados se guardan en
work/tiles/ (si se corta, se continúa). Un cuadro que el servidor no puede
servir entero (tiempo o memoria) se parte en cuatro.

Qué se pide (igual que la consulta «país» de Offlined):
  node/way con seamark:type, node natural=reef|shoal|rock, way natural=reef|shoal
Solo cuadros que tocan la zona de algún país (Marine Regions «eez_land»).

    python fetch_tiles.py            # ~400 cuadros, unas horas
    python fetch_tiles.py 0/2 & python fetch_tiles.py 1/2   # en dos procesos, cada uno con su servidor
"""
import gzip
import json
import os
import sys
import time
from pathlib import Path

import requests
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
from shapely.prepared import prep

HERE = Path(__file__).resolve().parent
WORK = Path(os.environ.get("SEACHARTS_WORK") or (HERE / "work"))
TILES = WORK / "tiles"
ZONES = Path(os.environ.get("CHART_ZONES") or r"C:\SurvivalAI-phi4\frontend\geo\chart_zones.json")
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
UA = {"User-Agent": "OfflinedSeaCharts/1.0 (+https://github.com/Aruvaro-Chulvi/OfflinedSeaCharts)",
      "Accept": "application/json"}
STEP = 10.0          # grados del cuadro inicial
MIN_STEP = 1.25      # no se parte más allá
PAUSE = 3            # segundos entre consultas (Overpass: no más de 2 a la vez por IP)


def query(w, s, e, n) -> str:
    b = f"{s:.4f},{w:.4f},{n:.4f},{e:.4f}"
    return ("[out:json][timeout:600];("
            f'node["seamark:type"]({b});'
            f'way["seamark:type"]({b});'
            f'node["natural"~"^(reef|shoal|rock)$"]({b});'
            f'way["natural"~"^(reef|shoal)$"]({b});'
            ");out center tags qt;")


class TooBig(Exception):
    pass


PART, PARTS = 0, 1    # este proceso hace los cuadros PART, PART+PARTS…


def ask(q: str) -> dict:
    """Respuesta de Overpass; TooBig si el cuadro no cabe; reintenta lo demás."""
    wait = 30
    for attempt in range(12):
        # Primero el servidor principal (admite dos consultas a la vez por IP); los otros, si falla
        ep = ENDPOINTS[attempt % len(ENDPOINTS)]
        try:
            r = requests.post(ep, data={"data": q}, headers=UA, timeout=(20, 700))
            if r.status_code == 200:
                data = r.json()
                remark = data.get("remark") or ""
                if "runtime error" in remark or "Query timed out" in remark or "out of memory" in remark:
                    raise TooBig(remark)
                return data
            err = f"HTTP {r.status_code}"
            if r.status_code == 400:
                sys.exit(f"Consulta rechazada: {r.text[:300]}")
        except TooBig:
            raise
        except (requests.RequestException, ValueError) as ex:
            err = type(ex).__name__
        print(f"    {err} @ {ep.split('/')[2]} · espero {wait} s", flush=True)
        time.sleep(wait)
        wait = min(wait * 2, 600)
    raise RuntimeError("Overpass no responde")


def tile_path(w, s, step) -> Path:
    return TILES / f"{w:+08.3f}_{s:+07.3f}_{step:g}.json.gz"


def fetch(w, s, step, area) -> int:
    """Baja un cuadro (o sus cuatro trozos si no cabe). Devuelve cuántos elementos."""
    e, n = w + step, min(s + step, 90.0)
    if not area.intersects(box(w, s, e, n)):
        return 0
    p = tile_path(w, s, step)
    if p.exists():
        with gzip.open(p, "rt", encoding="utf-8") as f:
            return len(json.load(f))
    done = p.with_suffix(".split")
    if not done.exists():
        try:
            t0 = time.time()
            data = ask(query(w, s, e, n))
            els = [{"type": x["type"], "id": x["id"],
                    "lon": x.get("lon", (x.get("center") or {}).get("lon")),
                    "lat": x.get("lat", (x.get("center") or {}).get("lat")),
                    "tags": x.get("tags") or {}} for x in data.get("elements", []) if x.get("tags")]
            tmp = p.with_suffix(".tmp")
            with gzip.open(tmp, "wt", encoding="utf-8") as f:
                json.dump(els, f, ensure_ascii=False, separators=(",", ":"))
            os.replace(tmp, p)
            print(f"  {p.name}: {len(els)} · {time.time() - t0:.0f} s", flush=True)
            time.sleep(PAUSE)
            return len(els)
        except TooBig as ex:
            if step / 2 < MIN_STEP:
                raise RuntimeError(f"{p.name} no cabe ni a {step}°: {ex}")
            print(f"  {p.name}: demasiado grande, lo parto", flush=True)
            done.write_text("split")
            time.sleep(PAUSE)
    h = step / 2
    return sum(fetch(w + dx, s + dy, h, area) for dx in (0, h) for dy in (0, h))


def main():
    global PART, PARTS
    if len(sys.argv) > 1:
        PART, PARTS = map(int, sys.argv[1].split("/"))
    TILES.mkdir(parents=True, exist_ok=True)
    zones = json.loads(ZONES.read_text(encoding="utf-8"))["zones"]
    polys = [Polygon([(r[i], r[i + 1]) for i in range(0, len(r), 2)]) for z in zones.values() for r in z["p"]]
    area = prep(unary_union([p.buffer(0) for p in polys]))
    cells = [(w, s) for s in range(-80, 90, int(STEP)) for w in range(-180, 180, int(STEP))
             if area.intersects(box(w, s, w + STEP, min(s + STEP, 90)))]
    cells = cells[PART::PARTS]
    print(f"{len(cells)} cuadros de {STEP:g}° (parte {PART + 1} de {PARTS})", flush=True)
    total = 0
    for i, (w, s) in enumerate(cells, 1):
        total += fetch(float(w), float(s), STEP, area)
        print(f"[{i}/{len(cells)}] total {total}", flush=True)
    if not (WORK / "fetched.txt").exists():
        (WORK / "fetched.txt").write_text(time.strftime("%Y-%m-%d"), encoding="utf-8")
    print("Hecho.", flush=True)


if __name__ == "__main__":
    main()
