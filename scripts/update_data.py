"""Satu perintah untuk memperbarui data CurryCoach (otomatisasi skrip).

Urutan kerja:
  1. (opsional) scraping halaman referensi yang diberikan lewat --url
  2. impor hasil scraping ke database
  3. impor katalog latihan dari API wger (atau snapshot jika --offline)

Contoh:
  python scripts/update_data.py --dry-run
  python scripts/update_data.py --offline
  python scripts/update_data.py --url https://en.wikipedia.org/wiki/Basketball --limit 150
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:               # agar bisa dijalankan dari folder mana pun
    sys.path.insert(0, str(ROOT))

from config import DATABASE, REFERENCE_DIR                      # noqa: E402
from scripts.import_data import SNAPSHOT, jalankan_impor        # noqa: E402
from scripts.scrape_reference import scrape                     # noqa: E402

log = logging.getLogger("update_data")


def jalankan(urls: list[str], delay: float, limit: int, offline: bool,
             database: str, dry_run: bool = False) -> dict:
    """Jalankan seluruh tahap dan kembalikan ringkasan (dipakai juga oleh tes)."""
    ringkasan = {"scraping_berhasil": 0, "scraping_gagal": [], "impor": None,
                 "dry_run": dry_run}
    rencana = [f"scraping: {url}" for url in urls]
    rencana.append(f"impor ke database: {database}")
    rencana.append("latihan: snapshot lokal" if offline else f"latihan: API wger (limit {limit})")
    if dry_run:
        for langkah in rencana:
            log.info("[rencana] %s", langkah)
        return ringkasan

    if urls and offline:
        log.warning("Mode --offline: scraping dilewati karena butuh internet.")
    else:
        for url in urls:
            try:
                hasil = scrape(url, delay)
                ringkasan["scraping_berhasil"] += 1
                log.info("Scraping berhasil: %s", hasil.get("title", url))
            except Exception as exc:                        # satu URL gagal tidak menghentikan yang lain
                ringkasan["scraping_gagal"].append({"url": url, "alasan": str(exc)})
                log.error("Scraping gagal (%s): %s", url, exc)

    ringkasan["impor"] = jalankan_impor(database, REFERENCE_DIR, SNAPSHOT, limit, offline)
    return ringkasan


def main() -> int:
    parser = argparse.ArgumentParser(description="Perbarui data referensi dan katalog latihan CurryCoach.")
    parser.add_argument("--url", action="append", default=[], help="URL referensi untuk di-scrape (boleh berulang)")
    parser.add_argument("--delay", type=float, default=2.0, help="jeda scraping dalam detik")
    parser.add_argument("--limit", type=int, default=150, help="jumlah latihan dari API wger")
    parser.add_argument("--offline", action="store_true", help="pakai snapshot wger, tanpa internet")
    parser.add_argument("--database", default=DATABASE)
    parser.add_argument("--dry-run", action="store_true", help="tampilkan rencana tanpa menjalankan")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    hasil = jalankan(args.url, args.delay, args.limit, args.offline, args.database, args.dry_run)
    print(json.dumps(hasil, ensure_ascii=False, indent=2))
    return 1 if hasil["scraping_gagal"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
