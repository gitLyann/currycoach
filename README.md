# CurryCoach 🏀

**Chatbot Edukasi Bola Basket untuk Pemula Berbasis Flask**

CurryCoach adalah aplikasi chatbot edukasi yang dirancang untuk membantu pengguna mempelajari dasar-dasar permainan bola basket. Chatbot ini menyediakan informasi seputar teknik bermain, posisi pemain, program latihan, serta profil Stephen Curry.

Proyek ini dikembangkan menggunakan Python dan Flask dengan sistem pencocokan pola dan kemiripan teks untuk mengenali maksud pertanyaan pengguna (*intent matching*).

## Fitur Utama

- **Chatbot Edukasi:** Menjawab pertanyaan seputar dasar-dasar bola basket.
- **Intent Matching:** Mengidentifikasi maksud pertanyaan menggunakan pencocokan pola dan kemiripan teks.
- **Explain Mode:** Menampilkan intent yang terdeteksi, kandidat intent, skor kemiripan, dan threshold.
- **Chat History:** Menyimpan serta menampilkan riwayat percakapan menggunakan SQLite.
- **Session Management:** Memisahkan riwayat percakapan berdasarkan sesi pengguna.
- **Quick Suggestions:** Menyediakan rekomendasi pertanyaan untuk mempermudah interaksi.
- **Admin Dashboard:** Menampilkan statistik pertanyaan, tingkat pengenalan intent, grafik distribusi intent, dan pertanyaan yang belum dikenali.
- **Evaluasi Chatbot:** Menyediakan dataset dan program evaluasi klasifikasi intent.
- **Local Production Server:** Mendukung penggunaan Waitress sebagai server WSGI.

## Teknologi yang Digunakan

| Teknologi | Kegunaan |
|---|---|
| Python | Bahasa pemrograman utama |
| Flask | Framework backend |
| SQLite | Penyimpanan riwayat percakapan |
| Waitress | Server WSGI |
| HTML | Struktur halaman |
| CSS | Desain dan responsivitas antarmuka |
| JavaScript | Interaksi chatbot dan dashboard |
| Pytest | Pengujian otomatis |

## Struktur Proyek

```text
currycoach/
├── app.py
├── wsgi.py
├── currycoach.json
├── intents.json
├── requirements.txt
├── evaluate.py
├── .env.example
├── .gitignore
│
├── chatbot/
│   ├── __init__.py
│   ├── database.py
│   └── engine.py
│
├── evaluasi/
│   └── currycoach.csv
│
├── static/
│   ├── admin.css
│   ├── admin.js
│   ├── script.js
│   └── style.css
│
├── templates/
│   ├── admin.html
│   └── index.html
│
├── tests/
│   ├── __init__.py
│   ├── test_backend.py
│   ├── test_chat.py
│   └── test_engine.py
│
├── DEPLOYMENT.md
├── LAPORAN-UJI-TAHAP-4.md
└── TEMPLATE-LAPORAN-AKHIR.md
```

Database SQLite dibuat secara otomatis di folder `instance/` ketika aplikasi dijalankan. Folder tersebut tidak disertakan dalam repository karena berisi data lokal.

## Persyaratan Sistem

Pastikan perangkat sudah memiliki:

- Python 3.10 atau lebih baru.
- pip.
- Git (opsional, untuk mengelola repository).
- Browser modern.

## Instalasi

### 1. Clone Repository

```bash
git clone URL_REPOSITORY_KAMU
cd currycoach
```

Ganti `URL_REPOSITORY_KAMU` dengan alamat repository GitHub CurryCoach.

### 2. Buat Virtual Environment

```powershell
python -m venv .venv
```

### 3. Aktifkan Virtual Environment

```powershell
.venv\Scripts\Activate.ps1
```

### 4. Instal Dependencies

```powershell
python -m pip install -r requirements.txt
```

## Konfigurasi Keamanan

CurryCoach menggunakan environment variables untuk mengatur konfigurasi aplikasi.

Variabel yang digunakan:

| Variabel | Fungsi |
|---|---|
| `APP_ENV` | Menentukan mode aplikasi |
| `SECRET_KEY` | Mengamankan session Flask |
| `ADMIN_KEY` | Melindungi akses statistik admin |
| `DATABASE` | Menentukan lokasi database SQLite |
| `THRESHOLD` | Mengatur ambang batas pengenalan intent |
| `SESSION_COOKIE_SECURE` | Mengatur keamanan cookie pada HTTPS |
| `FLASK_DEBUG` | Mengatur debug mode Flask |

### Membuat Secret Key

Buat nilai acak untuk `SECRET_KEY`:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Ulangi perintah tersebut untuk membuat `ADMIN_KEY` yang berbeda.

Jangan membagikan kedua nilai tersebut atau menyimpannya secara langsung di source code maupun repository publik.

## Menjalankan Aplikasi

### A. Mode Development

Untuk menjalankan aplikasi menggunakan server pengembangan Flask:

```powershell
$env:APP_ENV = "development"
python app.py
```

Buka browser:

```text
http://127.0.0.1:5000/
```

### B. Mode Local Production dengan Waitress

Untuk menjalankan aplikasi menggunakan server WSGI Waitress, atur environment variables terlebih dahulu:

```powershell
$env:APP_ENV = "production"
$env:SECRET_KEY = "MASUKKAN_SECRET_KEY"
$env:ADMIN_KEY = "MASUKKAN_ADMIN_KEY"
$env:SESSION_COOKIE_SECURE = "0"
```

Ganti nilai contoh dengan secret yang sudah dibuat sebelumnya.

Kemudian jalankan:

```powershell
waitress-serve --listen=127.0.0.1:8000 wsgi:app
```

Buka aplikasi melalui:

- Chatbot: http://127.0.0.1:8000/
- Dashboard Admin: http://127.0.0.1:8000/admin

**Catatan:** Konfigurasi di atas ditujukan untuk demonstrasi lokal melalui HTTP. Jika aplikasi dipublikasikan melalui HTTPS, gunakan `SESSION_COOKIE_SECURE=1`.

Waitress merupakan server aplikasi, bukan layanan hosting. Penggunaan perintah tersebut tidak otomatis membuat CurryCoach dapat diakses melalui internet.

## Endpoint API

| Method | Endpoint | Keterangan |
|---|---|---|
| GET | `/` | Halaman utama chatbot |
| GET | `/chat/<theme>` | Halaman chatbot berdasarkan tema |
| GET | `/admin` | Dashboard admin |
| GET | `/api/themes` | Daftar tema chatbot |
| POST | `/chat` | Endpoint chat kompatibilitas |
| POST | `/api/chat` | Mengirim pesan chatbot |
| POST | `/api/explain` | Mengirim pesan dengan Explain Mode |
| GET | `/api/history/<theme>` | Mengambil riwayat percakapan |
| DELETE | `/api/history/<theme>` | Menghapus riwayat percakapan |
| GET | `/api/stats/<theme>` | Mengambil statistik chatbot |
| GET | `/api/health` | Memeriksa status aplikasi |

Endpoint statistik admin memerlukan header `X-Admin-Key` jika `ADMIN_KEY` telah dikonfigurasi.

## Pengujian

### 1. Menjalankan Pengujian Otomatis

```powershell
python -m pytest -v
```

### 2. Menjalankan Evaluasi Chatbot

```powershell
python evaluate.py
```

Program evaluasi menggunakan dataset `evaluasi/currycoach.csv` untuk mengukur kesesuaian prediksi intent dengan label yang diharapkan.

Hasil evaluasi berlaku untuk dataset pengujian yang digunakan dan bukan jaminan bahwa chatbot selalu memberikan klasifikasi yang benar untuk semua pertanyaan.

## Keamanan dan Privasi

Beberapa hal yang perlu diperhatikan:

- Jangan mengunggah file `.env` atau secret asli ke repository publik.
- Database lokal di dalam folder `instance/` dikecualikan dari Git.
- Folder virtual environment tidak disertakan dalam repository.
- Gunakan `SECRET_KEY` dan `ADMIN_KEY` yang berbeda serta kuat.
- Jangan mengaktifkan Flask debug mode pada penggunaan production.
- Untuk akses melalui internet, gunakan HTTPS dan konfigurasi server yang sesuai.
- Pastikan penyimpanan riwayat percakapan memperhatikan privasi pengguna.

## Deployment

Panduan menjalankan aplikasi dengan Waitress dan konfigurasi deployment tersedia pada:

`DEPLOYMENT.md`

Proyek ini telah disiapkan untuk demonstrasi menggunakan Waitress pada lingkungan lokal (*local production*). Proyek tidak diklaim telah di-hosting secara online.

## Laporan Proyek

Dokumentasi pengujian dan evaluasi tersedia dalam:

- `LAPORAN-UJI-TAHAP-4.md`
- `TEMPLATE-LAPORAN-AKHIR.md`

Template laporan akhir dapat digunakan untuk melengkapi dokumentasi hasil pengembangan dan demonstrasi proyek.

## Identitas Visual

CurryCoach menggunakan kombinasi warna yang terinspirasi dari identitas visual Golden State Warriors:

- Warriors Blue: `#1D428A`
- Warriors Gold: `#FFC72C`

---

**CurryCoach — Learn Basketball, One Question at a Time.** 🏀