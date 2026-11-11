# Panduan Deployment CurryCoach — Tahap 5

## A. Jalankan lokal (pengembangan)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:APP_ENV = "development"
python app.py
```

Buka `http://127.0.0.1:5000/`. Server bawaan Flask hanya untuk pengembangan lokal.

## B. Jalankan dengan WSGI server (Windows)

Buat secret yang berbeda untuk `SECRET_KEY` dan `ADMIN_KEY`. Contoh membuat nilai acak:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Jalankan perintah tersebut dua kali, lalu atur environment variables (ganti nilai contoh):

```powershell
$env:APP_ENV = "production"
$env:SECRET_KEY = "ISI_SECRET_ACAK_PERTAMA"
$env:ADMIN_KEY = "ISI_KUNCI_ADMIN_ACAK_KEDUA"
$env:SESSION_COOKIE_SECURE = "0"
waitress-serve --listen=127.0.0.1:8000 wsgi:app
```

Buka `http://127.0.0.1:8000/`. `SESSION_COOKIE_SECURE=0` hanya untuk uji lokal melalui HTTP. Jika aplikasi dipasang di belakang HTTPS pada server publik, atur `SESSION_COOKIE_SECURE=1`.

## C. Checklist sebelum publikasi

- [ ] `APP_ENV=production`.
- [ ] `SECRET_KEY` dan `ADMIN_KEY` kuat, berbeda, dan tidak disimpan di Git.
- [ ] `FLASK_DEBUG` tidak aktif.
- [ ] HTTPS aktif dan `SESSION_COOKIE_SECURE=1`.
- [ ] Server menggunakan WSGI (Waitress/Gunicorn), bukan Flask development server.
- [ ] Endpoint `/api/health` merespons status `ok`.
- [ ] Endpoint statistik admin menolak permintaan tanpa kunci yang benar.
- [ ] Chat, Explain Mode, riwayat, dan dashboard diuji setelah deployment.
- [ ] Lokasi database memiliki izin tulis dan backup.

## D. Catatan penting untuk hosting

Aplikasi saat ini menggunakan SQLite. Jangan menganggap filesystem pada hosting gratis selalu persisten. Beberapa platform menghapus file lokal ketika aplikasi di-redeploy atau instance diganti. Jika memakai hosting seperti itu, siapkan persistent disk/volume dan arahkan `DATABASE` ke lokasi yang persisten, atau migrasikan lapisan database ke layanan database terkelola sebelum menyimpan percakapan pengguna secara permanen.

Jangan membuka aplikasi ke internet publik hanya dengan server pengembangan. Jangan menaruh secret di source code, screenshot, atau repository publik. Pastikan kebijakan privasi dan persetujuan pengguna sesuai jika percakapan disimpan.

## E. Batas verifikasi

Panduan dan entry point WSGI telah disiapkan, tetapi deployment ke akun hosting belum dilakukan dari paket ini. Klaim aplikasi sudah online hanya boleh ditulis setelah pengguna benar-benar melakukan deployment dan menguji URL publiknya.
