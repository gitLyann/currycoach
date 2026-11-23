"""Pengambilan data latihan dari database untuk web dan Telegram."""
from __future__ import annotations

from chatbot.database import cari_latihan
from chatbot.engine import normalisasi

PETA_OTOT = {
    "kaki": "Legs", "tungkai": "Legs", "dada": "Chest",
    "perut": "Abs", "tangan": "Arms", "punggung": "Back",
    "bahu": "Shoulders", "pantat": "Glutes",
}


def parameter_latihan(pesan: str) -> dict:
    """Ekstrak filter sederhana dari kalimat pengguna."""
    teks = normalisasi(pesan)
    level = next((item for item in ("pemula", "menengah", "lanjutan")
                  if item in teks), None)
    alat = "tanpa alat" if (
        "tanpa alat" in teks or "tidak pakai alat" in teks
        or "ga pakai alat" in teks
    ) else None
    otot = next((nilai for kata, nilai in PETA_OTOT.items() if kata in teks), None)
    return {"level": level, "alat": alat, "otot": otot, "limit": 3}


def format_latihan(items: list[dict]) -> str:
    if not items:
        return "Belum ada latihan yang cocok di katalog database."
    baris = ["Latihan dari database CurryCoach:"]
    for item in items:
        detail = ", ".join(x for x in [
            item.get("category"), item.get("equipment"), item.get("level")
        ] if x)
        baris.append(f"- {item['name']} ({detail})")
    return "\n".join(baris)


def jawaban_latihan(database: str, pesan: str) -> str | None:
    """Kembalikan teks jawaban bila katalog punya latihan yang cocok."""
    items = cari_latihan(database, **parameter_latihan(pesan))
    if not items:
        return None
    return format_latihan(items)
