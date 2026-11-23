# Cara Menjalankan CurryCoach 2.0 Secara Lokal (Windows)

> Hosting publik ditunda ke tahap akhir. Untuk sekarang, jalankan website di laptop sendiri.

## 1. Ekstrak dan buka folder
1. Ekstrak ZIP.
2. Buka folder `currycoach` di VS Code. Pastikan terminal berada di folder yang sama dengan `app.py`.

## 2. Buat virtual environment dan instal dependensi
Jalankan di PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Jika PowerShell menolak aktivasi karena execution policy, jalankan sekali pada terminal tersebut:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

## 3. Siapkan konfigurasi lokal

```powershell
Copy-Item .env.example .env
```

Buka `.env`, pastikan konfigurasi lokal berikut:

```env
APP_ENV=development
SESSION_COOKIE_SECURE=0
CURRYCOACH_API_URL=http://127.0.0.1:5000
```

`TELEGRAM_BOT_TOKEN` boleh dikosongkan jika hanya ingin menjalankan website. Jangan membagikan token atau file `.env` ke GitHub.

## 4. Jalankan website

```powershell
python app.py
```

Buka browser ke `http://127.0.0.1:5000/`. Untuk memeriksa server, buka `http://127.0.0.1:5000/api/health`. Biarkan terminal website tetap berjalan. Hentikan dengan `Ctrl+C`.

## 5. Jalankan Telegram Bot (opsional, terminal kedua)

1. Buat bot melalui Telegram `@BotFather` dan salin tokennya.
2. Isi `TELEGRAM_BOT_TOKEN=token_asli` pada `.env`.
3. Buka terminal VS Code kedua pada folder proyek yang sama.
4. Aktifkan environment dan jalankan:

```powershell
.venv\Scripts\Activate.ps1
python telegram_bot.py
```

5. Cari username bot di Telegram, lalu kirim `/start`. Coba `/tanya bagaimana cara melakukan free throw?`. Untuk `/lapangan`, kirim perintah itu lalu bagikan lokasi.

Flask harus tetap berjalan di terminal pertama. Bot polling berjalan selama terminal kedua tetap aktif.

## 6. Jalankan scraping (opsional; perlu URL sumber yang mengizinkan)

```powershell
python scripts/scrape_reference.py "https://alamat-sumber-yang-diizinkan/halaman"
```

Ganti URL contoh dengan sumber nyata. Periksa kebijakan situs dan `robots.txt`; jangan mencoba melewati larangan situs. Hasil scraping disimpan di folder `data/references/`.

## 7. Jalankan pengujian

```powershell
python -m pytest -v
python evaluate.py
```

## Urutan yang disarankan
1. Pastikan website lama berjalan.
2. Uji endpoint `/api/health`.
3. Uji Telegram Bot.
4. Uji pencarian lapangan OpenStreetMap.
5. Uji scraping dengan sumber yang diizinkan.
6. Hosting publik dikerjakan paling akhir setelah semua fitur stabil.
