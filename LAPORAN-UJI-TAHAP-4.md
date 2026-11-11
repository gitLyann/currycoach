# Catatan Pengujian CurryCoach — Tahap 4

## 1. Cakupan

Tahap ini mencakup evaluasi klasifikasi intent, pemeriksaan pengujian otomatis, dan penguatan konfigurasi keamanan untuk lingkungan produksi.

## 2. Hasil evaluasi dataset

Dataset `evaluasi/currycoach.csv` berisi 37 kalimat berlabel:

- 29 contoh pertanyaan yang termasuk 10 intent topik CurryCoach.
- 8 contoh pertanyaan di luar topik yang diharapkan masuk ke `fallback`.

Hasil menjalankan `python evaluate.py` pada mesin pencocokan intent saat ini:

| Metrik | Hasil |
|---|---:|
| Total data | 37 |
| Prediksi benar | 37 |
| Prediksi salah | 0 |
| Akurasi | 100% |
| Data berlabel fallback | 8 |

Akurasi dihitung dengan rumus:

`akurasi = jumlah prediksi benar / jumlah seluruh data uji × 100%`

**Batasan:** hasil ini hanya menggambarkan dataset yang tersedia. Dataset masih relatif kecil dan perlu ditambah dengan variasi kalimat dari pengujian pengguna. Jangan menyimpulkan bahwa akurasi penggunaan nyata pasti 100%.

## 3. Pengujian otomatis

Jalankan di virtual environment proyek:

```powershell
python -m pytest -v
```

Pengujian mencakup struktur basis pengetahuan, pola intent, normalisasi bahasa informal, pencocokan intent, fallback, validasi input, riwayat SQLite, isolasi sesi, proteksi API statistik, dan halaman admin.

**Status eksekusi:** pengujian penuh perlu dijalankan pada komputer pengembang yang memiliki Flask dan pytest terpasang. Lingkungan penyusunan arsip ini tidak memiliki Flask, sehingga hasil `pytest` belum dapat dikonfirmasi di sini.

## 4. Penguatan konfigurasi keamanan

- Mode `APP_ENV=production` sekarang mewajibkan `SECRET_KEY` dan `ADMIN_KEY`.
- Contoh konfigurasi `.env.example` memuat `APP_ENV`.
- Cookie sesi tetap memakai `HttpOnly` dan `SameSite=Lax`; untuk HTTPS produksi, atur `SESSION_COOKIE_SECURE=1`.
- Statistik admin tetap dilindungi header `X-Admin-Key`.
- Jangan gunakan Flask debug server untuk deployment publik. Gunakan HTTPS dan server WSGI produksi.

## 5. Uji manual dengan pengguna

Lakukan pengujian dengan minimal 3 orang teman. Minta mereka mencoba aplikasi tanpa diarahkan ke jawaban yang benar. Catat hasilnya pada tabel berikut.

| Penguji | Chat & respons | Explain Mode | Riwayat | Dashboard/admin | Masukan |
|---|---|---|---|---|---|
| Penguji 1 | Belum diuji | Belum diuji | Belum diuji | Belum diuji | — |
| Penguji 2 | Belum diuji | Belum diuji | Belum diuji | Belum diuji | — |
| Penguji 3 | Belum diuji | Belum diuji | Belum diuji | Belum diuji | — |

Isi tabel hanya setelah pengujian benar-benar dilakukan.

## 6. Bukti yang perlu disimpan

- Screenshot halaman chat dan percakapan uji.
- Screenshot Explain Mode yang menampilkan kandidat intent.
- Screenshot dashboard admin setelah beberapa pertanyaan dikirim.
- Screenshot terminal hasil `python -m pytest -v`.
- Screenshot terminal hasil `python evaluate.py`.
- Catatan hasil uji dari minimal 3 teman.

## 7. Perbandingan sebelum dan sesudah

Belum dicantumkan angka perbandingan akurasi sebelum dan sesudah karena baseline lama belum dieksekusi ulang dengan dataset uji yang sama. Perbandingan yang sah harus menggunakan dataset identik untuk kedua versi.
