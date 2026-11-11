# CurryCoach — Tahap 4: Pengujian, Evaluasi, dan Keamanan

CurryCoach adalah chatbot edukasi basket untuk pemula. Tahap ini memperbarui antarmuka chat dan menambahkan dashboard admin berbasis data SQLite, tanpa mengganti mesin chatbot maupun API pada Tahap 2.

## Identitas visual

- Warriors Blue: `#1D428A`
- Warriors Gold: `#FFC72C`
- Font antarmuka: DM Sans dan Outfit (Google Fonts; fallback sistem tetap tersedia)
- Layout responsif untuk desktop, tablet, dan ponsel.

## Instalasi dan menjalankan

```powershell
python -m venv .venv
.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
$env:SECRET_KEY = "ganti-dengan-secret-random-yang-panjang"
$env:ADMIN_KEY = "ganti-dengan-kunci-admin-yang-kuat"
python app.py
```

Buka:
- Chat: `http://127.0.0.1:5000/`
- Admin: `http://127.0.0.1:5000/admin`

Jika `ADMIN_KEY` disetel, masukkan nilai yang sama pada halaman Admin Dashboard. Kunci hanya disimpan di `sessionStorage` browser dan dikirim melalui header `X-Admin-Key`; jangan gunakan halaman ini melalui koneksi HTTP publik tanpa HTTPS.

## Fitur UI Tahap 3

- Chat UI baru dengan palet Warriors Blue dan Warriors Gold.
- Layout responsif desktop dan mobile.
- Riwayat percakapan dimuat dari `/api/history/currycoach`.
- Hapus riwayat sesi melalui `DELETE /api/history/currycoach`.
- Quick suggestions dari `currycoach.json`.
- Explain Mode menggunakan `/api/explain` untuk menampilkan kandidat intent dan skor.
- Pesan pengguna dan balasan dirender menggunakan `textContent` untuk mengurangi risiko XSS.
- Admin Dashboard menggunakan `/api/stats/currycoach`, dengan kartu metrik, grafik batang distribusi intent, ringkasan recognized/fallback, dan tabel pertanyaan yang belum dikenali.

## Endpoint backend

Seluruh endpoint Tahap 2 dipertahankan: `/chat`, `/api/chat`, `/api/explain`, `/api/history/<theme>`, `/api/stats/<theme>`, `/api/themes`, dan `/api/health`. Halaman baru `/admin` hanya menyajikan antarmuka; proteksi data statistik tetap berada pada endpoint API.

## Pengujian dan evaluasi Tahap 4

Jalankan seluruh tes otomatis:

```powershell
python -m pytest -v
```

Jalankan evaluasi dataset secara terpisah (tidak perlu menyalakan server Flask):

```powershell
python evaluate.py
```

Dataset evaluasi berisi minimal 20 contoh kalimat dan minimal 4 pertanyaan di luar topik basket yang diharapkan masuk ke `fallback`. Akurasi adalah proporsi prediksi intent yang sama dengan label harapan pada dataset tersebut. Hasil evaluasi bukan jaminan akurasi untuk semua pertanyaan pengguna; tambahkan data uji baru dari hasil uji pengguna.

Database lokal dibuat otomatis di `instance/currycoach.sqlite3`. Database tidak disertakan dalam arsip ZIP.

## Catatan

- Grafik dibuat dengan HTML/CSS dan JavaScript tanpa dependensi chart eksternal.
- Font Google Fonts memerlukan koneksi internet; fallback font sistem akan digunakan jika tidak tersedia.
- Untuk deployment, set `APP_ENV=production`, gunakan `SECRET_KEY` dan `ADMIN_KEY` yang kuat, aktifkan HTTPS dan `SESSION_COOKIE_SECURE=1`, serta gunakan server WSGI produksi. Aplikasi menolak startup production jika `SECRET_KEY` atau `ADMIN_KEY` belum diatur. Jangan aktifkan Flask debug mode.

## Tahap 5 — Deployment dan laporan akhir

- `wsgi.py`: entry point untuk server WSGI.
- Waitress ditambahkan sebagai server WSGI yang dapat dijalankan di Windows.
- `DEPLOYMENT.md`: panduan server lokal/WSGI, konfigurasi production, dan catatan persistensi SQLite.
- `TEMPLATE-LAPORAN-AKHIR.md`: kerangka laporan yang harus diisi dengan bukti aktual.

Contoh menjalankan WSGI di Windows (set environment variables production terlebih dahulu):

```powershell
waitress-serve --listen=127.0.0.1:8000 wsgi:app
```

Jangan menyatakan aplikasi telah online sebelum deployment dan pengujian URL publik benar-benar dilakukan.
