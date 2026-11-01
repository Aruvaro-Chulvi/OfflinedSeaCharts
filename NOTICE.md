# Notice

**Offlined Sea Charts** — a project of **[Offlined](https://www.offlined.org)** by **Álvaro C. Chulvi**.

## What is licensed under what

| Part | Files | License |
|---|---|---|
| Sea mark packs (one per country) and `manifest.json` | `seamarks-*.json.gz` in Releases | [ODbL 1.0](LICENSE) — © OpenStreetMap contributors |
| Build scripts | `scripts/` | [PolyForm Noncommercial 1.0.0](LICENSE-CODE.md) |

The packs are an extract of the **OpenStreetMap** database, so they are a *Derivative Database* under the
[Open Database License 1.0](LICENSE): you may copy, share, adapt and use them, **also commercially**, as long
as you credit OpenStreetMap, keep the packs (and any database you derive from them) under the ODbL and do
not add technical restrictions. Maps or other *Produced Works* made from them only need the attribution.

## How to credit

> Sea marks © OpenStreetMap contributors, ODbL 1.0 (https://www.openstreetmap.org/copyright) — packaged by
> Offlined Sea Charts (https://github.com/Aruvaro-Chulvi/OfflinedSeaCharts), a project of Offlined.

## Sources

- **OpenStreetMap** — © OpenStreetMap contributors, [ODbL 1.0](https://www.openstreetmap.org/copyright).
  Taken once per release from the weekly planet file (planet.openstreetmap.org and its mirrors), or, as an
  alternative, from the public [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API) instances.
- **Country zones** used to split the planet into countries — Flanders Marine Institute (2024), *Marine
  Regions «eez_land»: union of world country boundaries and EEZ*, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/),
  www.marineregions.org (simplified by
  [`build_chart_zones.py`](https://github.com/Aruvaro-Chulvi/OfflinedSeafloor/blob/main/scripts/build_chart_zones.py)
  of Offlined Seafloor). The zones are only used to decide which country a sea mark belongs to; they are not
  part of the packs.

## Not for navigation

OpenStreetMap sea marks are collected by volunteers and may be incomplete, wrong or out of date. These packs
are for learning and exploring, **never for navigation** or for anything involving safety at sea: use the
official nautical charts of your hydrographic office.

Offlined Sea Charts is not affiliated with or endorsed by the OpenStreetMap Foundation or OpenSeaMap.
