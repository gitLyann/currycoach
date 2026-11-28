"""Rekap latihan harian seluruh pengguna (pandas)."""
from __future__ import annotations

import pandas as pd

from chatbot.database import get_connection

KOLOM = ["telegram_id", "sesi", "total_menit", "tembakan_masuk"]


def rekap_harian(database: str, tanggal: str) -> pd.DataFrame:
    """Rekap per pengguna untuk satu tanggal (format YYYY-MM-DD).

    Tanggal mengikuti waktu UTC yang disimpan database.
    """
    with get_connection(database) as connection:
        baris = connection.execute(
            """SELECT telegram_id, COUNT(*) AS sesi,
                      SUM(duration_min) AS total_menit,
                      SUM(shots_made) AS tembakan_masuk
               FROM workout_sessions WHERE date(created_at) = ?
               GROUP BY telegram_id ORDER BY total_menit DESC""",
            (tanggal,),
        ).fetchall()
    return pd.DataFrame([dict(b) for b in baris], columns=KOLOM)
