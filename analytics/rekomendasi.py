"""Rekomendasi personal berbasis aturan yang bisa dijelaskan."""
from __future__ import annotations

from chatbot.database import cari_latihan


def rekomendasi(database: str, telegram_id: int, ringkasan: dict | None = None) -> dict:
    """Buat saran singkat berdasarkan ringkasan latihan pengguna."""
    if ringkasan is None:
        from analytics.laporan import ringkasan_mingguan
        ringkasan = ringkasan_mingguan(database, telegram_id)

    saran = []
    if ringkasan["total_sesi"] < 3:
        saran.append("Tambah frekuensi menjadi 3 sesi per minggu untuk membangun konsistensi.")
    if ringkasan["rata_rata_menit"] < 20:
        saran.append("Perpanjang durasi setiap sesi menjadi minimal 20 menit secara bertahap.")
    if ringkasan["total_tembakan"] < 30:
        saran.append("Sisihkan 10 menit untuk latihan shooting dan catat tembakan masuk.")
    if not saran:
        saran.append("Konsistensimu sudah baik. Fokus ke kualitas gerakan dan istirahat cukup.")

    latihan = cari_latihan(database, level="pemula", limit=2)
    return {"saran": saran, "latihan": [item["name"] for item in latihan]}


def format_rekomendasi(data: dict) -> str:
    baris = ["Saran CurryCoach:"]
    baris.extend(f"- {saran}" for saran in data["saran"])
    if data["latihan"]:
        baris.append("Latihan pendukung: " + ", ".join(data["latihan"]) + ".")
    return "\n".join(baris)
