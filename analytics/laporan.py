"""Analitik latihan mingguan memakai pandas."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from chatbot.database import data_sesi_latihan


def ringkasan_mingguan(database: str, telegram_id: int, hari: int = 7) -> dict:
    """Ringkas sesi latihan pengguna dalam periode tertentu."""
    baris = data_sesi_latihan(database, telegram_id, hari)
    kosong = {
        "periode_hari": int(hari), "total_sesi": 0, "total_menit": 0,
        "rata_rata_menit": 0.0, "total_tembakan": 0,
        "kategori_teratas": {}, "per_hari": [],
    }
    if not baris:
        return kosong

    data = pd.DataFrame(baris)
    data["durasi"] = pd.to_numeric(data["durasi"], errors="coerce").fillna(0)
    data["tembakan"] = pd.to_numeric(data["tembakan"], errors="coerce").fillna(0)
    per_hari = (
        data.groupby("tanggal", as_index=False)
        .agg(menit=("durasi", "sum"), sesi=("durasi", "size"),
             tembakan=("tembakan", "sum"))
        .sort_values("tanggal")
        .to_dict("records")
    )
    return {
        "periode_hari": int(hari),
        "total_sesi": int(len(data)),
        "total_menit": int(data["durasi"].sum()),
        "rata_rata_menit": round(float(data["durasi"].mean()), 1),
        "total_tembakan": int(data["tembakan"].sum()),
        "kategori_teratas": {
            str(key): int(value)
            for key, value in data["kategori"].value_counts().head(3).items()
        },
        "per_hari": [
            {"tanggal": str(row["tanggal"]), "menit": int(row["menit"]),
             "sesi": int(row["sesi"]), "tembakan": int(row["tembakan"])}
            for row in per_hari
        ],
    }


def format_laporan(ringkasan: dict) -> str:
    """Ubah ringkasan menjadi pesan teks untuk bot atau chatbot."""
    baris = [
        f"Laporan {ringkasan['periode_hari']} hari terakhir:",
        f"- Sesi latihan: {ringkasan['total_sesi']}",
        f"- Total durasi: {ringkasan['total_menit']} menit",
        f"- Rata-rata durasi: {ringkasan['rata_rata_menit']} menit",
        f"- Tembakan masuk: {ringkasan['total_tembakan']}",
    ]
    if ringkasan["kategori_teratas"]:
        detail = ", ".join(
            f"{kategori} ({jumlah})"
            for kategori, jumlah in ringkasan["kategori_teratas"].items()
        )
        baris.append(f"- Fokus latihan: {detail}")
    return "\n".join(baris)


def menit_per_kategori(database: str, telegram_id: int, hari: int = 30) -> dict:
    """Total menit latihan per kategori (untuk grafik porsi latihan)."""
    baris = data_sesi_latihan(database, telegram_id, hari)
    if not baris:
        return {}
    data = pd.DataFrame(baris)
    data["durasi"] = pd.to_numeric(data["durasi"], errors="coerce").fillna(0)
    hasil = data.groupby("kategori")["durasi"].sum().sort_values(ascending=False)
    return {str(kategori): int(menit) for kategori, menit in hasil.items()}


def deret_harian(ringkasan: dict, hari: int = 14, akhir: date | None = None) -> list[dict]:
    """Isi hari tanpa latihan dengan 0 supaya grafik per hari tidak bolong."""
    akhir = akhir or date.today()
    peta = {item["tanggal"]: item for item in ringkasan["per_hari"]}
    deret = []
    for selisih in range(hari - 1, -1, -1):
        tanggal = (akhir - timedelta(days=selisih)).isoformat()
        item = peta.get(tanggal, {})
        deret.append({"tanggal": tanggal, "menit": int(item.get("menit", 0)),
                      "sesi": int(item.get("sesi", 0))})
    return deret
