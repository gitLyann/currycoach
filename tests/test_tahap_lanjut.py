"""Pengujian fitur tahap lanjut: dashboard latihan, katalog web, CRUD admin,
pola tambahan chatbot, perintah /dashboard, dan skrip otomatis."""
from datetime import datetime, timezone

import pytest

import services.osm as osm
import telegram_bot
from analytics.laporan import deret_harian, menit_per_kategori, ringkasan_mingguan
from analytics.rekap import rekap_harian
from app import create_app
from chatbot.database import (
    ambil_latihan, init_db, simpan_latihan, simpan_sesi_latihan,
)
from chatbot.tautan import baca_token, buat_token
from scripts import update_data
from scripts.rekap_harian import simpan_rekap

KUNCI = {"X-Admin-Key": "test-admin"}
LATIHAN_VALID = {"name": "Lompat Tali", "category": "Cardio", "level": "pemula",
                 "equipment": "tali", "muscles": "Calves", "description": "Latihan stamina."}


@pytest.fixture
def client(tmp_path):
    app = create_app({"TESTING": True, "SECRET_KEY": "test-secret",
                      "DATABASE": str(tmp_path / "t.sqlite3"), "ADMIN_KEY": "test-admin"})
    return app.test_client()


@pytest.fixture
def db_berisi(client):
    """Database dengan 1 latihan (id 1) dan 1 sesi milik pengguna 777."""
    db = client.application.config["DATABASE"]
    simpan_latihan(db, [{"external_id": 1, "name": "Squat", "category": "Legs",
                         "equipment": "tanpa alat", "muscles": "Quads", "level": "pemula",
                         "description": "Latihan kaki.", "source": "wger"}])
    simpan_sesi_latihan(db, 777, 1, 30, 12)
    return db


# ---------------------------------------------------------------- token tautan
def test_token_sah_dibaca_kembali():
    token = buat_token("rahasia", 123)
    assert baca_token("rahasia", token) == 123


def test_token_dipalsukan_atau_salah_kunci_ditolak():
    token = buat_token("rahasia", 123)
    assert baca_token("rahasia", token + "x") is None
    assert baca_token("kunci-lain", token) is None
    assert baca_token("rahasia", "") is None


def test_token_kedaluwarsa_ditolak():
    assert baca_token("rahasia", buat_token("rahasia", 123), max_age=-1) is None


# ---------------------------------------------------------------- halaman web
@pytest.mark.parametrize("url, teks", [
    ("/katalog", "Katalog Latihan"), ("/progres", "Latihan Saya"),
    ("/admin/kelola", "Kelola Data"),
])
def test_halaman_baru_terbuka(client, url, teks):
    res = client.get(url)
    assert res.status_code == 200
    assert teks in res.get_data(as_text=True)


def test_halaman_kelola_memuat_daftar_intent(client):
    assert "teknik_dribble" in client.get("/admin/kelola").get_data(as_text=True)


# ---------------------------------------------------------------- /api/progres
def test_api_progres_tanpa_atau_dengan_token_salah_401(client):
    assert client.get("/api/progres").status_code == 401
    assert client.get("/api/progres?t=ngawur").status_code == 401


def test_api_progres_menampilkan_data_pemilik_token(client, db_berisi):
    token = buat_token("test-secret", 777)
    data = client.get(f"/api/progres?t={token}").get_json()
    assert data["ringkasan_7"]["total_sesi"] == 1
    assert data["ringkasan_7"]["total_menit"] == 30
    assert len(data["harian"]) == 14
    assert data["kategori"] == {"Legs": 30}
    assert len(data["sesi_terbaru"]) == 1
    assert data["saran"]["saran"]


def test_api_progres_tidak_membocorkan_data_pengguna_lain(client, db_berisi):
    token = buat_token("test-secret", 999)          # pengguna tanpa sesi
    data = client.get(f"/api/progres?t={token}").get_json()
    assert data["ringkasan_7"]["total_sesi"] == 0
    assert data["sesi_terbaru"] == []


# ---------------------------------------------------------------- CRUD latihan
@pytest.mark.parametrize("metode, url", [
    ("get", "/api/admin/latihan"), ("post", "/api/admin/latihan"),
    ("put", "/api/admin/latihan/1"), ("delete", "/api/admin/latihan/1"),
    ("get", "/api/admin/pola"), ("post", "/api/admin/pola"),
    ("delete", "/api/admin/pola/1"),
])
def test_endpoint_admin_butuh_kunci(client, metode, url):
    assert getattr(client, metode)(url).status_code == 401


@pytest.mark.parametrize("ubah", [
    {"name": ""}, {"category": ""}, {"level": "dewa"}, {"name": "x" * 101},
    {"description": "d" * 1001}, {"name": 123},
])
def test_tambah_latihan_validasi(client, ubah):
    res = client.post("/api/admin/latihan", json={**LATIHAN_VALID, **ubah}, headers=KUNCI)
    assert res.status_code == 400
    assert res.get_json()["detail"]


def test_tambah_latihan_body_bukan_json_ditolak(client):
    assert client.post("/api/admin/latihan", data="x", headers=KUNCI).status_code == 400


def test_alur_crud_latihan(client):
    dibuat = client.post("/api/admin/latihan", json=LATIHAN_VALID, headers=KUNCI)
    assert dibuat.status_code == 201
    id_baru = dibuat.get_json()["id"]

    daftar = client.get("/api/admin/latihan?q=Lompat", headers=KUNCI).get_json()
    assert daftar["total"] == 1 and daftar["items"][0]["source"] == "manual"

    ubah = client.put(f"/api/admin/latihan/{id_baru}",
                      json={**LATIHAN_VALID, "name": "Lompat Tali Cepat"}, headers=KUNCI)
    assert ubah.status_code == 200
    assert ambil_latihan(client.application.config["DATABASE"], id_baru)["name"] == "Lompat Tali Cepat"

    assert client.put("/api/admin/latihan/9999", json=LATIHAN_VALID, headers=KUNCI).status_code == 404
    assert client.delete(f"/api/admin/latihan/{id_baru}", headers=KUNCI).status_code == 200
    assert client.delete(f"/api/admin/latihan/{id_baru}", headers=KUNCI).status_code == 404


def test_hapus_latihan_yang_sudah_dipakai_sesi_ditolak(client, db_berisi):
    res = client.delete("/api/admin/latihan/1", headers=KUNCI)
    assert res.status_code == 409


def test_daftar_latihan_parameter_bukan_angka(client):
    assert client.get("/api/admin/latihan?limit=abc", headers=KUNCI).status_code == 400


# ---------------------------------------------------------------- pola tambahan
def tag_balasan(client, pesan):
    return client.post("/api/chat", json={"message": pesan}).get_json()["intent"]


def test_pola_tambahan_mengubah_jawaban_chatbot(client):
    assert tag_balasan(client, "qwertyuiop") == "fallback"
    res = client.post("/api/admin/pola", json={"tag": "teknik_dribble", "pattern": "qwertyuiop"},
                      headers=KUNCI)
    assert res.status_code == 201
    assert tag_balasan(client, "qwertyuiop") == "teknik_dribble"
    assert client.delete(f"/api/admin/pola/{res.get_json()['id']}", headers=KUNCI).status_code == 200
    assert tag_balasan(client, "qwertyuiop") == "fallback"


@pytest.mark.parametrize("badan, kode", [
    ({"tag": "tidak_ada", "pattern": "abc"}, 404),
    ({"tag": "teknik_dribble", "pattern": ""}, 400),
    ({"tag": "teknik_dribble", "pattern": "x" * 101}, 400),
    ({"tag": "teknik_dribble", "pattern": "yang"}, 400),       # hanya kata henti
    ({"tag": "teknik_dribble", "pattern": "dribble"}, 409),    # sudah ada di currycoach.json
])
def test_pola_tambahan_validasi(client, badan, kode):
    assert client.post("/api/admin/pola", json=badan, headers=KUNCI).status_code == kode


def test_pola_tambahan_ganda_ditolak(client):
    badan = {"tag": "teknik_dribble", "pattern": "kocok bola cepat"}
    assert client.post("/api/admin/pola", json=badan, headers=KUNCI).status_code == 201
    assert client.post("/api/admin/pola", json=badan, headers=KUNCI).status_code == 409
    assert client.delete("/api/admin/pola/9999", headers=KUNCI).status_code == 404


# ---------------------------------------------------------------- bot /dashboard
def test_bot_dashboard_mengirim_tautan_bertoken(tmp_path, monkeypatch):
    database = str(tmp_path / "bot.sqlite3")
    init_db(database)
    monkeypatch.setattr(telegram_bot, "DATABASE", database)
    monkeypatch.setattr(telegram_bot, "SECRET_KEY", "rahasia-bot")
    pesan = []
    monkeypatch.setattr(telegram_bot, "kirim", lambda chat_id, text, **kw: pesan.append(text))
    telegram_bot._pending.clear()
    telegram_bot._konteks.clear()
    telegram_bot.proses_update({"message": {"chat": {"id": 55}, "from": {"id": 55}, "text": "/dashboard"}})
    tautan = next(t for t in pesan if "/progres?t=" in t)
    token = tautan.split("/progres?t=")[1].split()[0]
    assert baca_token("rahasia-bot", token) == 55


# ---------------------------------------------------------------- analitik
def test_menit_per_kategori_dan_deret_harian(db_berisi):
    assert menit_per_kategori(db_berisi, 777, 30) == {"Legs": 30}
    assert menit_per_kategori(db_berisi, 555, 30) == {}
    deret = deret_harian(ringkasan_mingguan(db_berisi, 777, 30), 14)
    assert len(deret) == 14
    assert sum(d["menit"] for d in deret) == 30
    assert [d["tanggal"] for d in deret] == sorted(d["tanggal"] for d in deret)


def test_rekap_harian_per_pengguna(db_berisi):
    hari_ini = datetime.now(timezone.utc).date().isoformat()
    tabel = rekap_harian(db_berisi, hari_ini)
    assert list(tabel["telegram_id"]) == [777]
    assert int(tabel.loc[0, "total_menit"]) == 30
    assert rekap_harian(db_berisi, "2000-01-01").empty


# ---------------------------------------------------------------- skrip otomatis
def test_update_data_dry_run_tidak_menjalankan_apa_pun(monkeypatch, tmp_path):
    def terlarang(*a, **k):
        raise AssertionError("tidak boleh dipanggil saat dry run")
    monkeypatch.setattr(update_data, "scrape", terlarang)
    monkeypatch.setattr(update_data, "jalankan_impor", terlarang)
    hasil = update_data.jalankan(["https://contoh.id"], 2.0, 10, False, str(tmp_path / "x.db"), dry_run=True)
    assert hasil["dry_run"] is True and hasil["impor"] is None


def test_update_data_satu_url_gagal_tidak_menghentikan_impor(monkeypatch, tmp_path):
    def gagal(url, delay):
        raise ValueError("URL ditolak")
    monkeypatch.setattr(update_data, "scrape", gagal)
    monkeypatch.setattr(update_data, "jalankan_impor", lambda *a, **k: {"ok": True})
    hasil = update_data.jalankan(["a", "b"], 0, 10, False, str(tmp_path / "x.db"))
    assert len(hasil["scraping_gagal"]) == 2
    assert hasil["impor"] == {"ok": True}


def test_update_data_offline_memakai_snapshot(tmp_path):
    hasil = update_data.jalankan([], 0, 150, True, str(tmp_path / "x.db"))
    assert hasil["impor"]["latihan_diimpor"] > 0


def test_simpan_rekap_menulis_csv_atau_none(db_berisi, tmp_path):
    hari_ini = datetime.now(timezone.utc).date().isoformat()
    berkas = simpan_rekap(db_berisi, hari_ini, tmp_path / "rekap")
    assert berkas is not None and berkas.read_text().startswith("telegram_id,sesi")
    assert simpan_rekap(db_berisi, "2000-01-01", tmp_path / "rekap") is None
    with pytest.raises(ValueError):
        simpan_rekap(db_berisi, "kemarin", tmp_path / "rekap")


# ---------------------------------------------------------------- OpenStreetMap
def test_jarak_haversine_masuk_akal():
    assert osm.hitung_jarak_km(-7.7, 110.5, -7.7, 110.5) == 0
    assert 110 < osm.hitung_jarak_km(0, 0, 1, 0) < 112          # 1 derajat lintang sekitar 111 km


class _Balasan:
    def __init__(self, elemen):
        self._e = elemen
    def raise_for_status(self):
        pass
    def json(self):
        return {"elements": self._e}


def _node(osm_id, lat, lon):
    return {"type": "node", "id": osm_id, "lat": lat, "lon": lon, "tags": {"sport": "basketball"}}


def test_lapangan_diurutkan_dari_yang_terdekat(monkeypatch, tmp_path):
    monkeypatch.setattr(osm, "CACHE_PATH", tmp_path / "cache.json")
    jauh, dekat = _node(1, -7.80, 110.50), _node(2, -7.701, 110.501)
    monkeypatch.setattr(osm.requests, "post", lambda *a, **k: _Balasan([jauh, dekat]))
    hasil = osm.cari_lapangan(-7.70, 110.50, 15000, limit=2)
    assert [h["osm_id"] for h in hasil] == [2, 1]
    assert hasil[0]["jarak_km"] < hasil[1]["jarak_km"]


def test_lapangan_bertahap_memperbesar_radius(monkeypatch, tmp_path):
    monkeypatch.setattr(osm, "CACHE_PATH", tmp_path / "cache.json")
    radius_dicoba = []

    def palsu(url, data, **kw):
        radius_dicoba.append(int(data["data"].split("around:")[1].split(",")[0]))
        return _Balasan([_node(9, -7.70, 110.51)] if len(radius_dicoba) == 3 else [])

    monkeypatch.setattr(osm.requests, "post", palsu)
    hasil, radius = osm.cari_lapangan_bertahap(-7.70, 110.50)
    assert radius_dicoba == [5000, 10000, 15000] and radius == 15000 and len(hasil) == 1


def test_lapangan_bertahap_kosong_di_semua_radius(monkeypatch, tmp_path):
    monkeypatch.setattr(osm, "CACHE_PATH", tmp_path / "cache.json")
    monkeypatch.setattr(osm.requests, "post", lambda *a, **k: _Balasan([]))
    assert osm.cari_lapangan_bertahap(-7.70, 110.50) == ([], 15000)


def test_format_lapangan_menampilkan_jarak_dan_radius():
    teks = telegram_bot.format_lapangan(
        [{"name": "GOR A", "map_url": "https://osm.org/n/1", "address": "", "jarak_km": 1.2}], 10000)
    assert "1.2 km" in teks and "10 km" in teks
    assert "Belum ada lapangan" in telegram_bot.format_lapangan([], 15000)
