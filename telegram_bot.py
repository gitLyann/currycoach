"""Telegram Bot CurryCoach: tanya, latihan, catat, laporan, dan lapangan."""
from __future__ import annotations

import time
from datetime import date

import requests

from analytics.laporan import format_laporan, ringkasan_mingguan
from analytics.rekomendasi import format_rekomendasi, rekomendasi
from chatbot.database import (
    ambil_latihan, ambil_riwayat, cari_latihan, daftar_sesi_telegram,
    info_sesi_aktif, pengguna_perlu_pengingat, pilih_sesi_telegram,
    sesi_aktif_telegram, sesi_baru_telegram, simpan_pesan, simpan_sesi_latihan,
)
from chatbot.handlers import format_latihan, parameter_latihan
from config import CURRYCOACH_API_URL, DATABASE, TELEGRAM_BOT_TOKEN
from services.osm import cari_lapangan

TOKEN = TELEGRAM_BOT_TOKEN
APP_BASE_URL = CURRYCOACH_API_URL
API_URL = f"https://api.telegram.org/bot{TOKEN}"
USER_AGENT = "CurryCoachTelegramBot/2.0"
_sessions: dict[int, requests.Session] = {}
_pending: dict[int, dict] = {}
_konteks: dict[int, dict] = {}


def telegram(method: str, payload: dict | None = None, timeout: int = 40):
    response = requests.post(f"{API_URL}/{method}", json=payload or {}, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("description", "Telegram API error"))
    return data.get("result")


def kirim(chat_id: int, text: str, **kwargs):
    hasil = telegram("sendMessage", {"chat_id": chat_id, "text": text, **kwargs})
    konteks = _konteks.get(chat_id)
    if konteks:
        try:
            simpan_pesan(DATABASE, konteks["session_id"], "currycoach", "bot",
                         text, intent=konteks.get("intent"))
        except Exception:
            pass
    return hasil


def mulai_konteks(chat_id: int, user_id: int, teks: str, ident: dict,
                  intent: str = "perintah") -> str:
    """Pastikan user & sesi dikenal, simpan pesan user, siapkan konteks balasan."""
    session_id = sesi_aktif_telegram(
        DATABASE, user_id,
        username=ident.get("username", ""),
        first_name=ident.get("first_name", ""),
    )
    if teks:
        simpan_pesan(DATABASE, session_id, "currycoach", "user", teks)
    _konteks[chat_id] = {"session_id": session_id, "intent": intent}
    return session_id


def keyboard_lokasi(chat_id: int):
    return kirim(chat_id,
        "Bagikan lokasi melalui tombol di bawah agar CurryCoach dapat mencari lapangan basket terdekat.",
        reply_markup={"keyboard": [[{"text": "📍 Bagikan lokasi", "request_location": True}]],
                      "resize_keyboard": True, "one_time_keyboard": True})


def jawab_pertanyaan(chat_id: int, user_id: int, pertanyaan: str,
                     session_id: str | None = None):
    if not pertanyaan:
        return kirim(chat_id, "Format: /tanya pertanyaan kamu\nContoh: /tanya bagaimana cara melakukan free throw?")
    session = _sessions.setdefault(user_id, requests.Session())
    try:
        response = session.post(
            f"{APP_BASE_URL}/api/chat",
            json={"message": pertanyaan, "theme": "currycoach",
                  "session_id": session_id, "simpan_riwayat": False},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        return kirim(chat_id, data.get("reply", "Maaf, belum ada jawaban."))
    except requests.RequestException:
        return kirim(chat_id, "Layanan chatbot web belum dapat dihubungi. Pastikan Flask berjalan dan CURRYCOACH_API_URL benar.")


def daftar_latihan(chat_id: int, argumen: str):
    parameter = parameter_latihan(argumen or "pemula")
    parameter["limit"] = 5
    items = cari_latihan(DATABASE, **parameter)
    return kirim(chat_id, format_latihan(items))


def format_pilihan(items: list[dict]) -> str:
    baris = ["Pilih nomor latihan yang ingin dicatat:"]
    baris.extend(
        f"{i}. {item['name']} — {item.get('category') or '-'} / {item.get('level') or '-'}"
        for i, item in enumerate(items, 1)
    )
    return "\n".join(baris)


def mulai_catat(chat_id: int, user_id: int, argumen: str):
    bagian = argumen.split()
    if len(bagian) >= 3 and bagian[0].isdigit():
        latihan = ambil_latihan(DATABASE, bagian[0])
        if latihan is None:
            return kirim(chat_id, "Nomor latihan tidak ditemukan. Ketik /latihan untuk melihat daftar.")
        try:
            durasi, tembakan = int(bagian[1]), int(bagian[2])
        except ValueError:
            return kirim(chat_id, "Format: /catat <id> <durasi_menit> <tembakan_masuk>")
        simpan_sesi_latihan(DATABASE, user_id, latihan["id"], durasi, tembakan)
        return kirim(chat_id, f"Tersimpan: {latihan['name']}, {durasi} menit, {tembakan} tembakan masuk.")

    items = cari_latihan(DATABASE, limit=5)
    _pending[user_id] = {"langkah": "pilih", "items": items}
    return kirim(chat_id, format_pilihan(items))


def lanjut_catat(chat_id: int, user_id: int, teks: str) -> bool:
    state = _pending.get(user_id)
    if not state:
        return False
    if state["langkah"] == "pilih":
        if not teks.isdigit() or not (1 <= int(teks) <= len(state["items"])):
            return kirim(chat_id, "Kirim nomor dari daftar latihan, atau /latihan untuk melihat ulang.")
        state["exercise_id"] = state["items"][int(teks) - 1]["id"]
        state["langkah"] = "durasi"
        return kirim(chat_id, "Berapa lama latihan berlangsung? (menit)")
    if state["langkah"] == "durasi":
        try:
            durasi = int(teks)
            if durasi <= 0:
                raise ValueError
        except ValueError:
            return kirim(chat_id, "Durasi harus berupa angka positif dalam menit.")
        state["durasi"] = durasi
        state["langkah"] = "tembakan"
        return kirim(chat_id, "Berapa tembakan yang masuk? (angka, 0 jika tidak ada)")
    try:
        tembakan = int(teks)
        if tembakan < 0:
            raise ValueError
    except ValueError:
        return kirim(chat_id, "Jumlah tembakan harus berupa angka.")
    latihan = ambil_latihan(DATABASE, state["exercise_id"])
    simpan_sesi_latihan(DATABASE, user_id, state["exercise_id"], state["durasi"], tembakan)
    _pending.pop(user_id, None)
    return kirim(chat_id, f"Tersimpan: {latihan['name']}, {state['durasi']} menit, {tembakan} tembakan masuk. Ketik /laporan untuk melihat progres.")


def kirim_laporan(chat_id: int, user_id: int):
    ringkasan = ringkasan_mingguan(DATABASE, user_id)
    saran = rekomendasi(DATABASE, user_id, ringkasan)
    return kirim(chat_id, format_laporan(ringkasan) + "\n\n" + format_rekomendasi(saran))


def info_sesi(chat_id: int, user_id: int):
    aktif = info_sesi_aktif(DATABASE, user_id)
    daftar = daftar_sesi_telegram(DATABASE, user_id)
    baris = [
        f"Sesi aktif: {aktif['label']} ({aktif['session_id'][:8]})",
        f"Pesan di sesi ini: {aktif['jumlah_pesan']}",
        "",
        "Daftar sesi kamu:",
    ]
    for nomor, item in enumerate(daftar, 1):
        penanda = " ← aktif" if item["aktif"] else ""
        baris.append(f"{nomor}. {item['label']} — {item['jumlah_pesan']} pesan{penanda}")
    baris.append("")
    baris.append("Ganti sesi: /session <nomor>")
    baris.append("Sesi baru: /session baru")
    return kirim(chat_id, "\n".join(baris))


def ganti_sesi(chat_id: int, user_id: int, argumen: str):
    if argumen.strip().lower() in {"baru", "new", "reset"}:
        session_id, label = sesi_baru_telegram(DATABASE, user_id)
        if chat_id in _konteks:
            _konteks[chat_id]["session_id"] = session_id
        return kirim(chat_id, f"{label} dibuat dan sekarang aktif.")
    pilihan = pilih_sesi_telegram(DATABASE, user_id, argumen.strip())
    if pilihan is None:
        return kirim(chat_id,
                     "Nomor sesi tidak valid. Ketik /session untuk melihat daftar.")
    if chat_id in _konteks:
        _konteks[chat_id]["session_id"] = pilihan["session_id"]
    return kirim(chat_id,
                 f"Beralih ke {pilihan['label']} ({pilihan['session_id'][:8]}).")


def info_user(chat_id: int, user_id: int, ident: dict):
    aktif = info_sesi_aktif(DATABASE, user_id)
    username = ident.get("username") or "-"
    nama = ident.get("first_name") or "-"
    return kirim(chat_id,
                 f"ID Telegram: {user_id}\nUsername: @{username}\nNama: {nama}\n"
                 f"Sesi aktif: {aktif['label']} ({aktif['session_id'][:8]})")


def riwayat_sesi(chat_id: int, user_id: int, limit: int = 5):
    session_id = info_sesi_aktif(DATABASE, user_id)["session_id"]
    pesan = ambil_riwayat(DATABASE, session_id, "currycoach", limit)
    if not pesan:
        return kirim(chat_id, "Belum ada riwayat pada sesi ini.")
    baris = ["Riwayat sesi ini (terbaru di bawah):"]
    for item in pesan:
        peran = "Kamu" if item["sender"] == "user" else "Bot"
        teks = str(item["text"]).replace("\n", " ")[:100]
        baris.append(f"- {peran}: {teks}")
    return kirim(chat_id, "\n".join(baris))


def format_lapangan(results: list[dict]) -> str:
    if not results:
        return "Belum ditemukan objek lapangan basket yang terdata di OpenStreetMap dalam radius pencarian. Data OSM mungkin belum lengkap."
    lines = ["🏀 Lapangan basket terdekat yang ditemukan:"]
    for i, item in enumerate(results, 1):
        address = f"\n   Lokasi: {item['address']}" if item.get("address") else ""
        lines.append(f"{i}. {item['name']}{address}\n   {item['map_url']}")
    lines.append("\nData berasal dari OpenStreetMap; kelengkapan dan kondisi lapangan perlu diverifikasi.")
    return "\n\n".join(lines)


def proses_update(update: dict):
    message = update.get("message") or update.get("edited_message")
    if not message:
        return
    chat_id = message["chat"]["id"]
    ident = message.get("from", {})
    user_id = ident.get("id", chat_id)
    text = (message.get("text") or "").strip()
    lokasi = message.get("location")
    teks_tersimpan = text or ("[lokasi dikirim]" if lokasi else "")
    intent = "perintah" if text.startswith("/") else ("lapangan" if lokasi else "chat")
    session_id = mulai_konteks(chat_id, user_id, teks_tersimpan, ident, intent)
    try:
        if text.startswith("/") and user_id in _pending:
            _pending.pop(user_id, None)
        if not text.startswith("/") and user_id in _pending:
            lanjut_catat(chat_id, user_id, text)
            return
        if text.startswith("/start"):
            kirim(chat_id,
                "🏀 Selamat datang di CurryCoach!\n\n"
                "Perintah yang tersedia:\n"
                "/tanya <pertanyaan> — bertanya tentang basket\n"
                "/latihan [filter] — melihat katalog latihan (contoh: /latihan pemula tanpa alat kaki)\n"
                "/catat — mencatat sesi latihan\n"
                "/laporan — ringkasan dan saran perkembangan\n"
                "/lapangan — mencari lapangan basket di sekitar lokasimu\n"
                "/session — lihat/ganti sesi chat\n"
                "/session baru — mulai sesi baru\n"
                "/user — lihat identitas Telegram & sesi aktif\n"
                "/riwayat — lihat 5 pesan terakhir di sesi ini\n\n"
                "Bot ini terhubung dengan mesin chatbot CurryCoach.")
        elif text.startswith("/tanya"):
            jawab_pertanyaan(chat_id, user_id, text[len("/tanya"):].strip(), session_id)
        elif text.startswith("/latihan"):
            daftar_latihan(chat_id, text[len("/latihan"):].strip())
        elif text.startswith("/catat"):
            mulai_catat(chat_id, user_id, text[len("/catat"):].strip())
        elif text.startswith("/laporan"):
            kirim_laporan(chat_id, user_id)
        elif text.startswith("/lapangan"):
            keyboard_lokasi(chat_id)
        elif text.startswith("/session"):
            argumen = text[len("/session"):].strip()
            if argumen:
                ganti_sesi(chat_id, user_id, argumen)
            else:
                info_sesi(chat_id, user_id)
        elif text.startswith("/reset"):
            ganti_sesi(chat_id, user_id, "baru")
        elif text.startswith("/user") or text.startswith("/id"):
            info_user(chat_id, user_id, ident)
        elif text.startswith("/riwayat") or text.startswith("/history"):
            riwayat_sesi(chat_id, user_id)
        elif lokasi:
            try:
                results = cari_lapangan(lokasi["latitude"], lokasi["longitude"])
                kirim(chat_id, format_lapangan(results),
                      reply_markup={"remove_keyboard": True}, disable_web_page_preview=True)
            except Exception:
                kirim(chat_id, "Pencarian lapangan sedang gagal. Coba lagi beberapa saat.")
        elif text:
            kirim(chat_id,
                  "Gunakan /tanya <pertanyaan>, /latihan, /catat, /laporan, "
                  "/lapangan, /session, /user, atau /riwayat.")
    finally:
        _konteks.pop(chat_id, None)


def kirim_pengingat(hari: int = 2) -> list[int]:
    """Ingatkan pengguna yang belum mencatat latihan beberapa hari."""
    ids = pengguna_perlu_pengingat(DATABASE, hari)
    for user_id in ids:
        pesan = ("🏀 Sudah {hari} hari sejak sesi terakhirmu. "
                 "Luangkan 15 menit untuk latihan hari ini!").format(hari=hari)
        try:
            session_id = sesi_aktif_telegram(DATABASE, user_id)
            simpan_pesan(DATABASE, session_id, "currycoach", "bot", pesan,
                         intent="pengingat")
            kirim(user_id, pesan)
        except Exception:
            continue
    return ids


def main():
    if not TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN belum diatur. Isi di file .env.")
    offset = None
    terakhir_pengingat = None
    print("CurryCoach Telegram Bot aktif. Tekan Ctrl+C untuk berhenti.")
    while True:
        try:
            updates = telegram("getUpdates", {"offset": offset, "timeout": 30}, timeout=40)
            for update in updates:
                offset = update["update_id"] + 1
                try:
                    proses_update(update)
                except Exception as exc:
                    print(f"Gagal memproses update {update.get('update_id')}: {exc}")
            hari_ini = date.today()
            if terakhir_pengingat != hari_ini:
                kirim_pengingat()
                terakhir_pengingat = hari_ini
        except KeyboardInterrupt:
            print("\nBot dihentikan.")
            break
        except Exception as exc:
            print(f"Koneksi Telegram bermasalah: {exc}")
            time.sleep(5)


if __name__ == "__main__":
    main()
