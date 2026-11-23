"""Telegram Bot CurryCoach: /start, /tanya, dan /lapangan (polling)."""
from __future__ import annotations
import os
import time
import requests
from dotenv import load_dotenv
from services.osm import cari_lapangan

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
APP_BASE_URL = os.getenv("CURRYCOACH_API_URL", "http://127.0.0.1:5000").rstrip("/")
API_URL = f"https://api.telegram.org/bot{TOKEN}"
USER_AGENT = "CurryCoachTelegramBot/2.0"
_sessions: dict[int, requests.Session] = {}


def telegram(method: str, payload: dict | None = None, timeout: int = 40):
    response = requests.post(f"{API_URL}/{method}", json=payload or {}, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("description", "Telegram API error"))
    return data.get("result")


def kirim(chat_id: int, text: str, **kwargs):
    return telegram("sendMessage", {"chat_id": chat_id, "text": text, **kwargs})


def keyboard_lokasi(chat_id: int):
    return kirim(chat_id,
        "Bagikan lokasi melalui tombol di bawah agar CurryCoach dapat mencari lapangan basket terdekat.",
        reply_markup={"keyboard": [[{"text": "📍 Bagikan lokasi", "request_location": True}]],
                      "resize_keyboard": True, "one_time_keyboard": True})


def jawab_pertanyaan(chat_id: int, user_id: int, pertanyaan: str):
    if not pertanyaan:
        return kirim(chat_id, "Format: /tanya pertanyaan kamu\nContoh: /tanya bagaimana cara melakukan free throw?")
    session = _sessions.setdefault(user_id, requests.Session())
    try:
        response = session.post(
            f"{APP_BASE_URL}/api/chat",
            json={"message": pertanyaan, "theme": "currycoach"},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        return kirim(chat_id, data.get("reply", "Maaf, belum ada jawaban."))
    except requests.RequestException:
        return kirim(chat_id, "Layanan chatbot web belum dapat dihubungi. Pastikan Flask berjalan dan CURRYCOACH_API_URL benar.")


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
    user_id = message.get("from", {}).get("id", chat_id)
    text = (message.get("text") or "").strip()
    if text.startswith("/start"):
        kirim(chat_id,
            "🏀 Selamat datang di CurryCoach!\n\n"
            "Perintah yang tersedia:\n"
            "/tanya <pertanyaan> — bertanya tentang basket\n"
            "/lapangan — mencari lapangan basket di sekitar lokasimu\n\n"
            "Bot ini terhubung dengan mesin chatbot CurryCoach.")
    elif text.startswith("/tanya"):
        jawab_pertanyaan(chat_id, user_id, text[len("/tanya"):].strip())
    elif text.startswith("/lapangan"):
        keyboard_lokasi(chat_id)
    elif message.get("location"):
        loc = message["location"]
        try:
            results = cari_lapangan(loc["latitude"], loc["longitude"])
            kirim(chat_id, format_lapangan(results),
                  reply_markup={"remove_keyboard": True}, disable_web_page_preview=True)
        except Exception:
            kirim(chat_id, "Pencarian lapangan sedang gagal. Coba lagi beberapa saat.")
    elif text:
        kirim(chat_id, "Gunakan /tanya <pertanyaan> atau /lapangan untuk memulai.")


def main():
    if not TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN belum diatur. Isi di file .env.")
    offset = None
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
        except KeyboardInterrupt:
            print("\nBot dihentikan.")
            break
        except Exception as exc:
            print(f"Koneksi Telegram bermasalah: {exc}")
            time.sleep(5)


if __name__ == "__main__":
    main()
