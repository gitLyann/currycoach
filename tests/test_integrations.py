"""Tes validasi offline untuk modul integrasi tahap 54%."""
import pytest
from chatbot.database import (
    ambil_riwayat, ambil_sesi_latihan, info_sesi_aktif, init_db, simpan_latihan,
)
from services.osm import cari_lapangan
from scripts.scrape_reference import scrape
import telegram_bot


def test_osm_rejects_invalid_coordinates_without_network():
    with pytest.raises(ValueError):
        cari_lapangan(120, 200)


def test_scraper_rejects_non_http_url_without_network():
    with pytest.raises(ValueError):
        scrape("file:///etc/passwd")


@pytest.fixture
def bot_offline(tmp_path, monkeypatch):
    database = str(tmp_path / "bot.sqlite3")
    init_db(database)
    simpan_latihan(database, [{
        "external_id": 9001, "name": "Braced Squat", "category": "Legs",
        "equipment": "tanpa alat", "muscles": "Quads", "level": "pemula",
        "description": "Latihan kaki tanpa alat.", "source": "wger",
    }])
    monkeypatch.setattr(telegram_bot, "DATABASE", database)
    pesan = []
    monkeypatch.setattr(telegram_bot, "kirim", lambda chat_id, text, **kw: pesan.append(text))
    telegram_bot._pending.clear()
    telegram_bot._konteks.clear()
    return pesan, database


def update_teks(text, user_id=4242):
    return {"message": {"chat": {"id": user_id}, "from": {"id": user_id}, "text": text}}


def test_bot_latihan_membaca_database(bot_offline):
    pesan, _ = bot_offline
    telegram_bot.proses_update(update_teks("/latihan pemula tanpa alat kaki"))
    assert any("Braced Squat" in teks for teks in pesan)


def test_bot_catat_tiga_langkah_tersimpan(bot_offline):
    pesan, database = bot_offline
    for teks in ["/catat", "1", "30", "20"]:
        telegram_bot.proses_update(update_teks(teks))
    assert any("Berapa lama" in teks for teks in pesan)
    assert any("Tersimpan" in teks for teks in pesan)
    assert len(ambil_sesi_latihan(database, 4242)) == 1


def test_bot_laporan_memakai_analitik(bot_offline):
    pesan, database = bot_offline
    telegram_bot.proses_update(update_teks("/laporan"))
    assert any("Laporan 7 hari terakhir" in teks for teks in pesan)
    assert any("Saran CurryCoach" in teks for teks in pesan)


def test_pengingat_dikirim_ke_pengguna(bot_offline, monkeypatch):
    pesan, _ = bot_offline
    monkeypatch.setattr(telegram_bot, "pengguna_perlu_pengingat", lambda db, hari: [4242])
    assert telegram_bot.kirim_pengingat() == [4242]
    assert any("Sudah 2 hari" in teks for teks in pesan)


def test_bot_session_baru_dan_ganti(bot_offline):
    pesan, database = bot_offline
    telegram_bot.proses_update(update_teks("/session"))
    awal = info_sesi_aktif(database, 4242)["session_id"]
    telegram_bot.proses_update(update_teks("/session baru"))
    baru = info_sesi_aktif(database, 4242)["session_id"]
    assert baru != awal
    assert any("Sesi 2 dibuat" in teks for teks in pesan)
    telegram_bot.proses_update(update_teks("/session 1"))
    assert info_sesi_aktif(database, 4242)["session_id"] == awal
    assert any("Beralih ke Sesi 1" in teks for teks in pesan)


def test_bot_user_dan_riwayat(bot_offline):
    pesan, database = bot_offline
    update = {"message": {
        "chat": {"id": 4242},
        "from": {"id": 4242, "username": "ucup", "first_name": "Ucup"},
        "text": "/user",
    }}
    telegram_bot.proses_update(update)
    assert any("ID Telegram: 4242" in teks and "@ucup" in teks for teks in pesan)
    telegram_bot.proses_update(update_teks("/riwayat"))
    assert any("Riwayat sesi ini" in teks for teks in pesan)
    session_id = info_sesi_aktif(database, 4242)["session_id"]
    riwayat = ambil_riwayat(database, session_id, "currycoach", 100)
    assert any(item["sender"] == "user" and item["text"] == "/user" for item in riwayat)


def test_bot_menyimpan_pesan_user_dan_bot(tmp_path, monkeypatch):
    database = str(tmp_path / "pesan.sqlite3")
    init_db(database)
    monkeypatch.setattr(telegram_bot, "DATABASE", database)
    monkeypatch.setattr(telegram_bot, "telegram",
                        lambda method, payload=None, timeout=None: {"ok": True})
    telegram_bot._pending.clear()
    telegram_bot._konteks.clear()
    telegram_bot.proses_update(update_teks("/laporan"))
    session_id = info_sesi_aktif(database, 4242)["session_id"]
    riwayat = ambil_riwayat(database, session_id, "currycoach", 100)
    assert any(item["sender"] == "user" and item["text"] == "/laporan" for item in riwayat)
    assert any(item["sender"] == "bot" and "Laporan 7 hari" in item["text"]
               for item in riwayat)
