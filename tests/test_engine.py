"""Unit test khusus preprocessing dan algoritma pencocokan intent."""
import json
from pathlib import Path

import pytest
from chatbot.engine import (
    DEFAULT_THRESHOLD, cari_intent, cari_intent_detail, normalisasi,
    skor_kemiripan, tokenisasi,
)

BASE = Path(__file__).resolve().parent.parent
with open(BASE / "currycoach.json", encoding="utf-8") as file:
    INTENTS = json.load(file)["intents"]


def tag(pesan):
    hasil = cari_intent(pesan, INTENTS)
    return hasil["tag"] if hasil else "fallback"


@pytest.mark.parametrize("teks, hasil", [
    ("GIMANA cara DRIBBLE???", "bagaimana cara dribble"),
    ("aku udh latihan yg bener", "aku sudah latihan yang benar"),
    ("gue gak paham", "gue tidak paham"),
    ("makasi coach!!!", "makasih coach"),
])
def test_normalisasi(teks, hasil):
    assert normalisasi(teks) == hasil


def test_tokenisasi_menghapus_stopwords():
    assert "yang" not in tokenisasi("cara dribble yang benar")
    assert "dribble" in tokenisasi("cara dribble yang benar")


def test_skor_kemiripan_memiliki_tiga_komponen():
    skor = skor_kemiripan("cara dribble", "cara dribble")
    assert skor["jaccard"] == 1
    assert skor["fuzzy"] == 1
    assert skor["coverage"] == 1
    assert skor["total"] == pytest.approx(1)


def test_bobot_sesuai_modul():
    assert DEFAULT_THRESHOLD == 0.45


@pytest.mark.parametrize("pesan, harapan", [
    ("halo coach aku mau belajar", "sapaan"),
    ("tips menggiring bola untuk pemula", "teknik_dribble"),
    ("teknik free throw yang benar", "teknik_shooting"),
    ("apa itu center dalam basket", "posisi_pemain"),
    ("program latihan seminggu", "program_latihan"),
    ("ceritakan tentang stephen curry", "profil_curry"),
    ("oke makasih coach", "terima_kasih"),
    ("dadah coach", "pamit"),
    ("namamu siapa", "identitas"),
    ("resep nasi goreng", "fallback"),
])
def test_pencarian_intent(pesan, harapan):
    assert tag(pesan) == harapan


def test_detail_mengembalikan_kandidat_dan_skor():
    terbaik, kandidat = cari_intent_detail("cara dribble", INTENTS)
    assert terbaik is not None
    assert terbaik["tag"] == "teknik_dribble"
    assert kandidat[0]["score"] >= DEFAULT_THRESHOLD


def test_threshold_menghasilkan_fallback():
    hasil = cari_intent("xyzqwerty", INTENTS, threshold=0.99)
    assert hasil is None


def test_frasa_spesifik_mengalahkan_kata_umum():
    assert tag("shooting guard") == "posisi_pemain"
    assert tag("Shooting guard itu ngapain?") == "posisi_pemain"
    assert tag("menu latihan") == "program_latihan"
    assert tag("posisi shooting guard") == "posisi_pemain"
