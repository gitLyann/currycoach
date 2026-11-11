"""Mesin NLU rule-based CurryCoach dengan skor kemiripan berbobot."""
from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
THEME_PATH = BASE_DIR / "currycoach.json"

# Normalisasi bahasa informal Indonesia (lebih dari 10 variasi).
NORMALISASI_INFORMAL = {
    "gmn": "bagaimana", "gimana": "bagaimana", "knp": "kenapa",
    "udh": "sudah", "udah": "sudah", "blm": "belum", "aja": "saja",
    "yg": "yang", "dgn": "dengan", "dr": "dari", "utk": "untuk",
    "gak": "tidak", "ga": "tidak", "nggak": "tidak", "enggak": "tidak",
    "kalo": "kalau", "kl": "kalau", "bgt": "banget", "pgn": "ingin",
    "pengen": "ingin", "tdk": "tidak", "makasi": "makasih",
    "bener": "benar",
    "drill": "latihan",
    "thx": "terima kasih", "bro": "", "dong": "", "nih": "",
}
STOPWORDS = {
    "yang", "dan", "di", "ke", "dari", "untuk", "dengan", "apa",
    "apakah", "itu", "ini", "saya", "aku", "kamu", "nya", "ya",
    "dong", "tolong", "bagaimana", "gimana", "adalah", "kah", "sih",
}
BOBOT = {"jaccard": 0.4, "fuzzy": 0.3, "coverage": 0.3}
DEFAULT_THRESHOLD = 0.45


def muat_tema(path: Path = THEME_PATH) -> dict:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def normalisasi(teks: str) -> str:
    """Case folding, cleaning, normalisasi slang, dan perapian spasi."""
    teks = str(teks or "").lower().replace("ё", "е")
    teks = re.sub(r"[^\w\s]", " ", teks, flags=re.UNICODE)
    tokens = []
    for token in teks.split():
        pengganti = NORMALISASI_INFORMAL.get(token, token)
        if pengganti:
            tokens.extend(pengganti.split())
    return " ".join(tokens)


def tokenisasi(teks: str, hapus_stopwords: bool = True) -> list[str]:
    tokens = normalisasi(teks).split()
    if hapus_stopwords:
        tokens = [token for token in tokens if token not in STOPWORDS]
    return tokens


def skor_kemiripan(kalimat: str, pola: str) -> dict[str, float]:
    """Menghitung Jaccard, fuzzy ratio, coverage, dan skor gabungan."""
    teks_normal = normalisasi(kalimat)
    pola_normal = normalisasi(pola)
    teks_tokens = set(tokenisasi(kalimat))
    pola_tokens = set(tokenisasi(pola))

    if not teks_normal or not pola_normal:
        return {"jaccard": 0.0, "fuzzy": 0.0, "coverage": 0.0, "total": 0.0}

    # Pencocokan frasa/kata utuh diprioritaskan agar kata pendek seperti
    # "menu", "permisi", atau "drill" tidak kalah oleh pola yang lebih panjang.
    if re.search(rf"(?<!\w){re.escape(pola_normal)}(?!\w)", teks_normal):
        return {"jaccard": 1.0, "fuzzy": 1.0, "coverage": 1.0, "total": 1.0}

    irisan = teks_tokens & pola_tokens
    gabungan = teks_tokens | pola_tokens
    jaccard = len(irisan) / len(gabungan) if gabungan else 0.0
    fuzzy = SequenceMatcher(None, teks_normal, pola_normal).ratio()
    coverage = len(irisan) / len(teks_tokens) if teks_tokens else 0.0
    total = (BOBOT["jaccard"] * jaccard + BOBOT["fuzzy"] * fuzzy
             + BOBOT["coverage"] * coverage)
    return {"jaccard": jaccard, "fuzzy": fuzzy,
            "coverage": coverage, "total": total}


def cari_intent_detail(pesan: str, intents: list[dict], threshold: float = DEFAULT_THRESHOLD):
    """Kembalikan intent terbaik beserta skor; None jika di bawah threshold.

    Jika beberapa pola sama-sama cocok persis (skor 1.0), pola yang lebih
    spesifik diprioritaskan. Contoh: "shooting guard" mengalahkan "shooting",
    dan "menu latihan" mengalahkan "menu".
    """
    teks_normal = normalisasi(pesan)
    kandidat = []

    for intent in intents:
        skor_terbaik = -1.0
        pola_terbaik = ""
        rincian_terbaik = None
        spesifisitas_terbaik = (0, 0, 0)

        for pola in intent.get("patterns", []):
            rincian = skor_kemiripan(pesan, pola)
            pola_normal = normalisasi(pola)
            cocok_frasa = bool(
                pola_normal and re.search(
                    rf"(?<!\w){re.escape(pola_normal)}(?!\w)", teks_normal
                )
            )
            # Tie-break: exact phrase, jumlah token, lalu panjang karakter.
            spesifisitas = (
                int(cocok_frasa),
                len(tokenisasi(pola)),
                len(pola_normal),
            )
            if (rincian["total"] > skor_terbaik or
                    (rincian["total"] == skor_terbaik and
                     spesifisitas > spesifisitas_terbaik)):
                skor_terbaik = rincian["total"]
                pola_terbaik = pola
                rincian_terbaik = rincian
                spesifisitas_terbaik = spesifisitas

        kandidat.append({
            "tag": intent["tag"], "intent": intent,
            "score": skor_terbaik, "pattern": pola_terbaik,
            "details": rincian_terbaik or {},
            "specificity": spesifisitas_terbaik,
        })

    kandidat.sort(
        key=lambda item: (item["score"], *item["specificity"]),
        reverse=True,
    )
    terbaik = kandidat[0] if kandidat else None
    if terbaik is None or terbaik["score"] < threshold:
        return None, kandidat
    return terbaik, kandidat


def cari_intent(pesan: str, intents: list[dict] | None = None,
                threshold: float = DEFAULT_THRESHOLD):
    """Kompatibilitas API lama: mengembalikan dict intent atau None."""
    if intents is None:
        intents = muat_tema()["intents"]
    terbaik, _ = cari_intent_detail(pesan, intents, threshold)
    return terbaik["intent"] if terbaik else None
