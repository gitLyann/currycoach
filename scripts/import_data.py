"""Impor hasil scraping dan latihan dari API wger ke SQLite."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import requests
from bs4 import BeautifulSoup

from chatbot.database import init_db, simpan_latihan, simpan_referensi
from config import DATABASE, REFERENCE_DIR, USER_AGENT, WGER_API_URL

SNAPSHOT = REFERENCE_DIR.parent / "exercises_wger.json"


def muat_referensi(directory: Path = REFERENCE_DIR) -> list[dict]:
    """Kumpulkan paragraf dari berkas JSON hasil scraping."""
    records = []
    for path in sorted(Path(directory).glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for paragraph in data.get("paragraphs", []):
            if paragraph.strip():
                records.append({
                    "source_url": data.get("source_url", ""),
                    "domain": data.get("domain", ""),
                    "title": data.get("title", ""),
                    "paragraph": paragraph,
                    "extracted_at": data.get("extracted_at", ""),
                })
    return records


def normalisasi_latihan(item: dict) -> dict:
    """Ubah satu hasil API wger menjadi baris katalog latihan."""
    terjemahan = item.get("translations") or []
    pilihan = next(
        (t for t in terjemahan if t.get("language") == 2),
        terjemahan[0] if terjemahan else {},
    )
    name = str(item.get("name") or pilihan.get("name") or "").strip()
    kategori = str((item.get("category") or {}).get("name") or "")
    alat = ", ".join(
        str(equipment.get("name") or "") for equipment in item.get("equipment") or []
    ).strip(", ")
    otot = ", ".join(
        str(muscle.get("name_en") or muscle.get("name") or "")
        for muscle in item.get("muscles") or []
    ).strip(", ")
    deskripsi = BeautifulSoup(
        str(pilihan.get("description") or item.get("description") or ""),
        "html.parser",
    ).get_text(" ", strip=True)
    nama_rendah = name.lower()
    if not alat:
        level = "pemula"
    elif any(kata in nama_rendah for kata in ("advanced", "plyometric", "burpee")):
        level = "lanjutan"
    else:
        level = "menengah"
    return {
        "external_id": item.get("id"),
        "name": name,
        "category": kategori,
        "equipment": alat or "tanpa alat",
        "muscles": otot,
        "level": level,
        "description": deskripsi[:500],
        "source": "wger",
    }


def ambil_wger(limit: int = 150, timeout: int = 30) -> list[dict]:
    """Ambil daftar latihan dari API publik wger."""
    response = requests.get(
        WGER_API_URL,
        params={"language": 2, "limit": max(1, min(int(limit), 500))},
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
    )
    response.raise_for_status()
    hasil = response.json().get("results", [])
    return [normalisasi_latihan(item) for item in hasil]


def tulis_snapshot(data: list[dict], path: Path = SNAPSHOT) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def baca_snapshot(path: Path = SNAPSHOT) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def jalankan_impor(database: str, reference_dir: Path = REFERENCE_DIR,
                   snapshot: Path = SNAPSHOT, limit: int = 150,
                   offline: bool = False) -> dict:
    """Impor hasil scraping dan katalog wger ke database. Mengembalikan ringkasan."""
    init_db(database)
    referensi = muat_referensi(Path(reference_dir))
    jumlah_referensi = simpan_referensi(database, referensi)

    if offline:
        latihan = baca_snapshot(Path(snapshot))
    else:
        latihan = ambil_wger(limit)
        tulis_snapshot(latihan, Path(snapshot))
    jumlah_latihan = simpan_latihan(database, latihan)
    return {
        "referensi_dibaca": len(referensi),
        "referensi_baru": jumlah_referensi,
        "latihan_diimpor": jumlah_latihan,
        "database": str(database),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Impor referensi scraping dan katalog wger.")
    parser.add_argument("--database", default=DATABASE)
    parser.add_argument("--reference-dir", default=str(REFERENCE_DIR))
    parser.add_argument("--snapshot", default=str(SNAPSHOT))
    parser.add_argument("--limit", type=int, default=150)
    parser.add_argument("--offline", action="store_true",
                        help="Gunakan snapshot wger tanpa memanggil API.")
    args = parser.parse_args()
    hasil = jalankan_impor(args.database, Path(args.reference_dir), Path(args.snapshot),
                           args.limit, args.offline)
    print(json.dumps(hasil, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
