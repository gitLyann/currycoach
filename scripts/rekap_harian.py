"""Buat rekap latihan harian seluruh pengguna dan simpan sebagai CSV.

Contoh:
  python scripts/rekap_harian.py                       # rekap kemarin
  python scripts/rekap_harian.py --tanggal 2026-11-20
Bisa dijadwalkan harian (Windows Task Scheduler atau cron).
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.rekap import rekap_harian   # noqa: E402
from chatbot.database import init_db       # noqa: E402
from config import DATABASE                # noqa: E402


def simpan_rekap(database: str, tanggal: str, folder: Path) -> Path | None:
    """Tulis CSV rekap. Mengembalikan path berkas, atau None jika tidak ada sesi."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", tanggal):
        raise ValueError("Tanggal harus berformat YYYY-MM-DD.")
    init_db(database)
    tabel = rekap_harian(database, tanggal)
    if tabel.empty:
        return None
    folder.mkdir(parents=True, exist_ok=True)
    tujuan = folder / f"rekap_{tanggal}.csv"
    tabel.to_csv(tujuan, index=False)
    return tujuan


def main() -> int:
    parser = argparse.ArgumentParser(description="Rekap latihan harian CurryCoach.")
    parser.add_argument("--tanggal", default=(date.today() - timedelta(days=1)).isoformat())
    parser.add_argument("--database", default=DATABASE)
    parser.add_argument("--output-dir", default=str(ROOT / "data" / "rekap"))
    args = parser.parse_args()
    try:
        hasil = simpan_rekap(args.database, args.tanggal, Path(args.output_dir))
    except ValueError as exc:
        print(f"Galat: {exc}")
        return 2
    print(f"Rekap {args.tanggal}: " + (f"disimpan ke {hasil}" if hasil else "tidak ada sesi latihan."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
