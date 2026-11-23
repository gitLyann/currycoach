"""Pencarian lapangan basket menggunakan OpenStreetMap Overpass API."""
from __future__ import annotations
import json
import time
from pathlib import Path
import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
CACHE_PATH = Path(__file__).resolve().parents[1] / "data" / "osm_cache.json"
CACHE_SECONDS = 24 * 60 * 60


def cari_lapangan(lat: float, lon: float, radius: int = 5000, limit: int = 8) -> list[dict]:
    """Cari objek OSM bertag basketball di sekitar koordinat; hasil dicache 24 jam."""
    if not (-90 <= float(lat) <= 90 and -180 <= float(lon) <= 180):
        raise ValueError("Koordinat tidak valid.")
    radius = max(500, min(int(radius), 15000))
    key = f"{round(float(lat),3)}:{round(float(lon),3)}:{radius}"
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    cache = {}
    if CACHE_PATH.exists():
        try:
            cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            cache = {}
    entry = cache.get(key)
    if entry and time.time() - entry.get("saved_at", 0) < CACHE_SECONDS:
        return entry.get("results", [])[:limit]

    query = f"""[out:json][timeout:25];
(
  node(around:{radius},{lat},{lon})["sport"="basketball"];
  way(around:{radius},{lat},{lon})["sport"="basketball"];
  relation(around:{radius},{lat},{lon})["sport"="basketball"];
  node(around:{radius},{lat},{lon})["leisure"="pitch"]["sport"~"basketball"];
  way(around:{radius},{lat},{lon})["leisure"="pitch"]["sport"~"basketball"];
);
out center tags;"""
    response = requests.post(
        OVERPASS_URL, data={"data": query}, timeout=35,
        headers={"User-Agent": "CurryCoach/2.0 educational project"}
    )
    response.raise_for_status()
    elements = response.json().get("elements", [])
    results = []
    for item in elements:
        tags = item.get("tags", {})
        center = item.get("center", {})
        item_lat = item.get("lat", center.get("lat"))
        item_lon = item.get("lon", center.get("lon"))
        if item_lat is None or item_lon is None:
            continue
        name = tags.get("name") or tags.get("leisure") or "Lapangan basket"
        results.append({
            "name": name, "lat": item_lat, "lon": item_lon,
            "type": item.get("type", "object"),
            "osm_id": item.get("id"),
            "address": ", ".join(x for x in [
                tags.get("addr:street"), tags.get("addr:city")
            ] if x),
            "map_url": f"https://www.openstreetmap.org/{item.get('type')}/{item.get('id')}",
        })
    results = results[:limit]
    cache[key] = {"saved_at": time.time(), "results": results}
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    return results
