"""Tes offline untuk scraping, import data, TF-IDF, dan analitik."""
from chatbot.database import (
    ambil_referensi, daftar_sesi_telegram, data_sesi_latihan, info_sesi_aktif,
    init_db, pilih_sesi_telegram, sesi_aktif_telegram, sesi_baru_telegram,
    simpan_latihan, simpan_pesan, simpan_referensi, simpan_sesi_latihan,
)
from analytics.laporan import format_laporan, ringkasan_mingguan
from analytics.rekomendasi import rekomendasi
from chatbot.tfidf import MesinTFIDF
from scripts.import_data import muat_referensi, normalisasi_latihan


PARAGRAF = (
    "Basketball was invented in 1891 by James Naismith as an indoor game "
    "and later spread through schools and communities around the world."
)


def test_muat_referensi_membaca_json_hasil_scraping():
    data = muat_referensi()
    assert data
    assert all(item["source_url"].startswith("https://") for item in data)
    assert all(item["paragraph"].strip() for item in data)


def test_simpan_referensi_mengabaikan_duplikat(tmp_path):
    database = str(tmp_path / "data.sqlite3")
    init_db(database)
    record = {
        "source_url": "https://contoh.example/a", "domain": "contoh.example",
        "title": "A", "paragraph": PARAGRAF, "extracted_at": "2026-01-01",
    }
    assert simpan_referensi(database, [record, record]) == 1
    assert len(ambil_referensi(database)) == 1


def test_normalisasi_latihan_memakai_translasi_wger():
    hasil = normalisasi_latihan({
        "id": 77,
        "category": {"name": "Legs"},
        "equipment": [],
        "muscles": [{"name_en": "Quads"}],
        "translations": [{
            "language": 2, "name": "Braced Squat",
            "description": "<p>Latih kaki tanpa alat.</p>",
        }],
    })
    assert hasil["name"] == "Braced Squat"
    assert hasil["equipment"] == "tanpa alat"
    assert hasil["level"] == "pemula"
    assert "<p>" not in hasil["description"]


def test_tfidf_menjawab_topik_basket_dan_menolak_topik_lain():
    mesin = MesinTFIDF(
        documents=[PARAGRAF, "Resep nasi goreng memakai bumbu dan nasi."],
        sources=["basket", "masakan"], threshold=0.1,
    )
    assert mesin.cari("siapa yang menemukan basketball?")
    assert not mesin.cari("cuaca hari ini di yogyakarta")


def test_sesi_telegram_tersimpan_dan_bisa_diganti(tmp_path):
    database = str(tmp_path / "sesi.sqlite3")
    init_db(database)
    awal = sesi_aktif_telegram(database, 77, "ucup", "Ucup")
    assert awal == sesi_aktif_telegram(database, 77)
    simpan_pesan(database, awal, "currycoach", "user", "halo")
    baru, label = sesi_baru_telegram(database, 77)
    assert baru != awal
    assert label == "Sesi 2"
    assert info_sesi_aktif(database, 77)["session_id"] == baru
    assert len(daftar_sesi_telegram(database, 77)) == 2
    assert pilih_sesi_telegram(database, 77, 1)["session_id"] == awal
    assert info_sesi_aktif(database, 77)["jumlah_pesan"] == 1
    assert pilih_sesi_telegram(database, 77, 99) is None


def test_ringkasan_dan_rekomendasi_mingguan(tmp_path):
    database = str(tmp_path / "latihan.sqlite3")
    init_db(database)
    simpan_latihan(database, [{
        "external_id": 1, "name": "Braced Squat", "category": "Legs",
        "equipment": "tanpa alat", "muscles": "Quads", "level": "pemula",
        "description": "", "source": "wger",
    }])
    simpan_sesi_latihan(database, 99, 1, 25, 40)
    ringkasan = ringkasan_mingguan(database, 99)
    assert ringkasan["total_sesi"] == 1
    assert ringkasan["total_menit"] == 25
    assert "Laporan 7 hari" in format_laporan(ringkasan)
    saran = rekomendasi(database, 99, ringkasan)
    assert saran["saran"]
    assert len(data_sesi_latihan(database, 99)) == 1
