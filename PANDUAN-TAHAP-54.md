# Panduan Pengembangan CurryCoach sampai Target 54%

Dokumen ini menjelaskan tambahan pada paket tahap 54%. Angka 54% adalah target rencana berdasarkan bobot pada laporan kemajuan, bukan klaim bahwa deployment/API eksternal sudah berhasil sebelum diuji pada akun dan jaringan pengguna.

Status terkini sudah melewati target scripting; lihat `PROGRES.md` untuk bukti scraping, API wger, TF-IDF, analitik, dan pengujian terkini. Deployment tetap ditunda.

## Isi pengembangan

1. **A1 — Deployment publik (ditunda ke tahap akhir)**
   - `render.yaml` dan `DEPLOYMENT.md` tetap disediakan sebagai persiapan.
   - Untuk tahap sekarang, jalankan aplikasi secara lokal terlebih dahulu.
   - Deployment publik baru dilakukan setelah fitur utama, Telegram Bot, API, dan scraping stabil.
   - Karena deployment ditunda, persentase kemajuan perlu dihitung ulang atau diberi catatan bahwa target 54% pada laporan awal memasukkan 8 poin deployment.

2. **A2 — Telegram Bot dasar (target kumulatif 38%)**
   - File: `telegram_bot.py`
   - Perintah: `/start`, `/tanya <pertanyaan>`, `/lapangan`.
   - Bot memakai mesin chatbot Flask yang sama melalui endpoint `/api/chat`.
   - Buat token melalui Telegram BotFather, lalu isi `TELEGRAM_BOT_TOKEN` di `.env`.
   - Jalankan Flask di terminal pertama. Jalankan bot di terminal kedua.
   - Polling digunakan agar demo awal tidak memerlukan webhook atau domain tambahan.

3. **A3 — OpenStreetMap (target kumulatif 46%)**
   - Modul: `services/osm.py`
   - Pengguna menjalankan `/lapangan`, lalu membagikan lokasi melalui Telegram.
   - Program meminta data objek bertag basketball dari Overpass API.
   - Hasil disimpan pada cache JSON selama 24 jam untuk mengurangi permintaan berulang.
   - Data OpenStreetMap dapat tidak lengkap; hasil harus diverifikasi langsung.

4. **A4 — Web scraping (target kumulatif 54%)**
   - Skrip: `scripts/scrape_reference.py`
   - Memeriksa `robots.txt`, menggunakan jeda request minimal 1 detik, dan menyimpan hasil ke JSON serta CSV.
   - Pengguna harus memilih URL sumber yang mengizinkan crawling. Jangan mengabaikan larangan robots.txt, syarat penggunaan, hak cipta, atau batas akses situs.
   - Scraping ini menghasilkan dataset referensi; belum otomatis memasukkan isi artikel ke jawaban chatbot.

## Instalasi pada Windows

Buka PowerShell di folder `currycoach`:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` dan isi nilai berikut:
- `SECRET_KEY`: string acak panjang untuk Flask.
- `ADMIN_KEY`: string acak berbeda dari SECRET_KEY.
- `TELEGRAM_BOT_TOKEN`: token dari BotFather.
- `CURRYCOACH_API_URL`: `http://127.0.0.1:5000` untuk pengujian lokal.

Buat dua secret berbeda menggunakan:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Menjalankan website dan bot secara lokal

Terminal 1:

```powershell
.venv\Scripts\Activate.ps1
$env:APP_ENV = "development"
python app.py
```

Terminal 2:

```powershell
.venv\Scripts\Activate.ps1
python telegram_bot.py
```

Buka `http://127.0.0.1:5000/`. Cari bot Telegram berdasarkan username yang dibuat melalui BotFather, lalu kirim `/start`.

Jika website sudah dideploy, `CURRYCOACH_API_URL` dapat diarahkan ke URL publik HTTPS tersebut. Bot tetap perlu dijalankan pada komputer/server yang aktif; menutup terminal akan menghentikan polling.

## Menguji OpenStreetMap

1. Buka chat Telegram dengan bot.
2. Kirim `/lapangan`.
3. Tekan tombol **Bagikan lokasi**.
4. Izinkan Telegram mengirim koordinat.
5. Bot mengembalikan objek lapangan yang ditemukan dan tautan OpenStreetMap.

Overpass API dapat membatasi permintaan saat ramai. Jika gagal, coba kembali nanti. Cache lokal disimpan pada `data/osm_cache.json`.

## Menjalankan scraping

Contoh format perintah:

```powershell
python scripts/scrape_reference.py "https://domain-sumber-yang-diizinkan.example/halaman"
```

Ganti URL contoh dengan halaman nyata yang sudah diperiksa izin crawling-nya. Hasil tersimpan di `data/references/` dalam format `.json` dan `.csv`.

Jika situs menolak request, jangan mencoba mengakali pembatasannya. Pilih sumber lain yang memperbolehkan akses otomatis atau gunakan API resmi.

## Deployment publik (tahap akhir; tidak perlu dilakukan sekarang)

Bagian ini sengaja ditunda. Kerjakan setelah seluruh fitur inti stabil.

1. Push source code ke repository GitHub tanpa `.env`, database lokal, `.venv`, atau token.
2. Buat Web Service pada layanan hosting yang mendukung Python.
3. Jika memakai Render, gunakan `render.yaml` sebagai konfigurasi awal.
4. Pastikan Environment Variables `APP_ENV`, `SECRET_KEY`, dan `ADMIN_KEY` terpasang. `render.yaml` dapat membuat secret secara otomatis.
5. Setelah deploy, buka `/api/health` dan uji website serta endpoint chat.
6. Catat URL publik dan waktu pengujian untuk bukti laporan.
7. Untuk database persisten, siapkan persistent disk atau database terkelola. SQLite pada filesystem sementara dapat hilang ketika instance diganti atau redeploy.

**Penting:** paket ini menyiapkan kode dan konfigurasi deployment. Deployment publik belum dapat dilakukan otomatis karena memerlukan akun hosting, repository, dan persetujuan pengguna. Jangan menulis bahwa aplikasi sudah online sampai URL benar-benar diuji.

## Pengujian otomatis

```powershell
python -m pytest -v
python evaluate.py
```

Tes otomatis yang sudah ada tetap dipertahankan. Fitur integrasi Telegram, Overpass, dan scraping memerlukan pengujian tambahan di lingkungan dengan token dan koneksi internet. Jangan menganggap hasil integrasi eksternal berhasil hanya karena tes lokal lulus.

## Struktur file tambahan

```text
currycoach/
├── telegram_bot.py
├── render.yaml
├── PANDUAN-TAHAP-54.md
├── services/
│   ├── __init__.py
│   └── osm.py
├── scripts/
│   ├── __init__.py
│   └── scrape_reference.py
└── data/
    ├── osm_cache.json       # dibuat otomatis setelah pencarian
    └── references/          # hasil scraping
```
