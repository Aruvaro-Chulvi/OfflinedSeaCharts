"""Baja el planeta de OpenStreetMap (~95 GB) en trozos a la vez desde varios espejos,
continuando lo que ya haya, y comprueba el MD5 publicado por planet.openstreetmap.org.

    python download_planet.py        # → work/planet/planet-latest.osm.pbf
"""
import hashlib
import os
import sys
import threading
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
OUT = Path(os.environ.get("SEACHARTS_WORK") or (HERE / "work")) / "planet"
NAME = "planet-latest.osm.pbf"
MIRRORS = [  # mismos archivos (mismo MD5); cada uno aguanta unos pocos MB/s por conexión
    "https://download.bbbike.org/osm/planet/" + NAME,
    "https://ftp5.gwdg.de/pub/misc/openstreetmap/planet.openstreetmap.org/pbf/" + NAME,
    "https://ftp.fau.de/osm-planet/pbf/" + NAME,
    "https://planet.openstreetmap.org/pbf/" + NAME,
]
MD5_URL = "https://planet.openstreetmap.org/pbf/" + NAME + ".md5"
PARTS = 12
UA = {"User-Agent": "OfflinedSeaCharts/1.0 (+https://github.com/Aruvaro-Chulvi/OfflinedSeaCharts)"}
done = [0] * PARTS


def part(i: int, start: int, end: int) -> None:
    p = OUT / f"{NAME}.part{i:02d}"
    while True:
        have = p.stat().st_size if p.exists() else 0
        done[i] = have
        if start + have > end:
            return
        url = MIRRORS[i % len(MIRRORS)]
        try:
            with requests.get(url, headers={**UA, "Range": f"bytes={start + have}-{end}"}, stream=True, timeout=(20, 120)) as r:
                if r.status_code != 206:
                    raise IOError(f"HTTP {r.status_code}")
                with open(p, "ab") as f:
                    for b in r.iter_content(1 << 20):
                        f.write(b)
                        done[i] += len(b)
        except Exception as e:
            print(f"  trozo {i}: {type(e).__name__} {e} · reintento", flush=True)
            time.sleep(15)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    size = int(requests.head(MIRRORS[0], headers=UA, allow_redirects=True, timeout=30).headers["Content-Length"])
    md5 = requests.get(MD5_URL, headers=UA, timeout=30).text.split()[0]
    step = -(-size // PARTS)
    th = [threading.Thread(target=part, args=(i, i * step, min(size, (i + 1) * step) - 1), daemon=True) for i in range(PARTS)]
    for t in th:
        t.start()
    t0, last = time.time(), sum(done)
    while any(t.is_alive() for t in th):
        time.sleep(30)
        now = sum(done)
        print(f"{now / 1e9:.1f} / {size / 1e9:.1f} GB · {(now - last) / 30 / 1e6:.1f} MB/s", flush=True)
        last = now
    print("Uniendo y comprobando el MD5…", flush=True)
    h = hashlib.md5()
    tmp = OUT / (NAME + ".tmp")
    with open(tmp, "wb") as out:
        for i in range(PARTS):
            with open(OUT / f"{NAME}.part{i:02d}", "rb") as f:
                for b in iter(lambda: f.read(64 << 20), b""):
                    h.update(b)
                    out.write(b)
    if tmp.stat().st_size != size or h.hexdigest() != md5:
        sys.exit(f"MD5 o tamaño distintos ({h.hexdigest()} / {md5}): borra los trozos y vuelve a empezar")
    os.replace(tmp, OUT / NAME)
    for i in range(PARTS):
        (OUT / f"{NAME}.part{i:02d}").unlink()
    print(f"Hecho en {(time.time() - t0) / 60:.0f} min: {OUT / NAME}", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
