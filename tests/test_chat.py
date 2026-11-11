"""Tes otomatis CurryCoach. Jalankan: pytest -v"""
import csv
from pathlib import Path

import pytest
from app import app, cari_intent, validasi_tema, INTENTS, FALLBACK, TEMA

BASE = Path(__file__).resolve().parent.parent


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def kirim(client, pesan):
    return client.post("/chat", json={"message": pesan})


def tag_dari(pesan):
    intent = cari_intent(pesan)
    return intent["tag"] if intent else "fallback"


# ---------- Struktur currycoach.json (aturan dari template dosen) ----------
def test_tema_valid():
    assert validasi_tema(TEMA) == []


def test_id_sama_dengan_nama_file():
    assert TEMA["id"] == "currycoach"
    assert (BASE / f"{TEMA['id']}.json").exists()


def test_minimal_10_intent_5_pola_2_respons():
    assert len(INTENTS) >= 10
    for i in INTENTS:
        assert len(i["patterns"]) >= 5, i["tag"]
        assert len(i["responses"]) >= 2, i["tag"]


def test_tag_unik_dan_fallback_bukan_intent():
    tags = [i["tag"] for i in INTENTS]
    assert len(tags) == len(set(tags))
    assert "fallback" not in tags
    assert len(FALLBACK) >= 1


def test_validasi_menemukan_kesalahan():
    rusak = {"id": "x", "intents": [{"tag": "a", "patterns": [], "responses": ["r"]}]}
    masalah = validasi_tema(rusak)
    assert any("name" in m for m in masalah)


# ---------- Contoh percakapan dari dokumen tugas ----------
@pytest.mark.parametrize("pesan, tag", [
    ("Halo", "sapaan"),
    ("Gimana cara dribble yang benar?", "teknik_dribble"),
    ("Cara nembak three point?", "teknik_shooting"),
    ("Posisi point guard ngapain?", "posisi_pemain"),
    ("Siapa Steph Curry?", "profil_curry"),
    ("Resep nasi goreng?", "fallback"),
])
def test_contoh_percakapan(client, pesan, tag):
    r = kirim(client, pesan)
    assert r.status_code == 200
    assert r.get_json()["intent"] == tag


# ---------- Setiap pola menuju intent-nya sendiri ----------
def semua_pola():
    return [(p, i["tag"]) for i in INTENTS for p in i["patterns"]]


@pytest.mark.parametrize("pola, tag", semua_pola())
def test_pola_menuju_intent_sendiri(pola, tag):
    assert tag_dari(pola) == tag


# ---------- Perilaku pencocokan ----------
@pytest.mark.parametrize("pesan, tag", [
    ("HALO!!!", "sapaan"),
    ("latihan dribble", "teknik_dribble"),
    ("posisi shooting guard", "posisi_pemain"),
    ("dribel dong", "teknik_dribble"),
    ("makasi ya", "terima_kasih"),
    ("point-guard itu apa", "posisi_pemain"),
])
def test_perilaku_pencocokan(pesan, tag):
    assert tag_dari(pesan) == tag


@pytest.mark.parametrize("pesan", ["chicken", "resep kari curry", "bolanya keluar lapangan"])
def test_tidak_salah_cocok(pesan):
    assert tag_dari(pesan) == "fallback"


# ---------- Fallback, placeholder, dan input ----------
def test_fallback_dari_daftar_fallback(client):
    j = kirim(client, "siapa presiden indonesia").get_json()
    assert j["intent"] == "fallback"
    assert j["reply"] in FALLBACK


def test_placeholder_nama_bot_diganti(client):
    j = kirim(client, "kamu siapa").get_json()
    assert j["intent"] == "identitas"
    assert "{nama_bot}" not in j["reply"]
    assert TEMA["bot_name"] in j["reply"]


def test_pesan_kosong_ditolak(client):
    assert kirim(client, "   ").status_code == 400
    assert client.post("/chat", json={}).status_code == 400


def test_bukan_json_ditolak(client):
    assert client.post("/chat", data="halo").status_code == 400


def test_halaman_utama_memakai_data_tema(client):
    html = client.get("/").get_data(as_text=True)
    assert TEMA["bot_name"] in html
    assert TEMA["greeting"] in html
    for s in TEMA["suggestions"]:
        assert s in html


# ---------- Evaluasi akurasi (data uji tidak ada di file tema) ----------
def baca_evaluasi():
    with open(BASE / "evaluasi" / "currycoach.csv", encoding="utf-8") as f:
        return [(r["kalimat"], r["intent"]) for r in csv.DictReader(f)]


def test_kalimat_uji_tidak_ada_di_pola():
    pola = {p.lower() for i in INTENTS for p in i["patterns"]}
    assert not [k for k, _ in baca_evaluasi() if k.lower() in pola]


def test_akurasi_data_uji():
    data = baca_evaluasi()
    benar = sum(1 for k, h in data if tag_dari(k) == h)
    akurasi = benar / len(data)
    print(f"akurasi {akurasi:.1%} ({benar}/{len(data)})")
    assert akurasi >= 0.8
