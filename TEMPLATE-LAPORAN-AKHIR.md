# TEMPLATE LAPORAN AKHIR PROYEK CURRYCOACH

> Lengkapi bagian bertanda `[ISI ...]` dengan hasil nyata. Hapus instruksi ini sebelum dikumpulkan. Jangan mengarang hasil pengujian, wawancara, atau deployment.

## 1. Pendahuluan

CurryCoach merupakan chatbot edukasi bola basket untuk pemula. Sistem membantu pengguna mempelajari teknik dasar dribble dan shooting, posisi pemain, program latihan, serta profil Stephen Curry. Tujuan pengembangan adalah menyediakan media belajar interaktif berbasis web.

## 2. Analisis dan perancangan

- Permasalahan: `[ISI masalah pembelajaran yang ditemukan dari wawancara/observasi]`
- Target pengguna: `[ISI target pengguna]`
- Kebutuhan fungsional: percakapan chatbot, quick suggestions, Explain Mode, riwayat percakapan, dan dashboard admin.
- Basis pengetahuan: `[ISI jumlah intent, pola, respons, dan sumber penyusunan]`
- Teknologi: Python, Flask, SQLite, HTML, CSS, dan JavaScript.

## 3. Implementasi

Jelaskan arsitektur aplikasi, mesin pencocokan intent, normalisasi bahasa informal, penyimpanan riwayat SQLite, API, antarmuka chat, Explain Mode, dan dashboard admin. Sertakan screenshot halaman chat, Explain Mode, dan dashboard.

## 4. Pengujian dan evaluasi

### 4.1 Pengujian otomatis

| Pengujian | Hasil aktual | Status |
|---|---|---|
| `python -m pytest -v` | `[ISI jumlah passed/failed]` | `[ISI]` |
| `python evaluate.py` | `[ISI jumlah benar/total dan akurasi]` | `[ISI]` |

### 4.2 Uji pengguna

| Penguji | Fitur yang dicoba | Masukan | Tindak lanjut |
|---|---|---|---|
| 1 | `[ISI]` | `[ISI]` | `[ISI]` |
| 2 | `[ISI]` | `[ISI]` | `[ISI]` |
| 3 | `[ISI]` | `[ISI]` | `[ISI]` |

### 4.3 Analisis hasil

Jelaskan pertanyaan yang berhasil dikenali, pertanyaan fallback, kesalahan klasifikasi, dan perbaikan yang dilakukan. Jika membandingkan versi sebelum/sesudah, gunakan dataset uji yang sama dan laporkan angka hasil eksekusi keduanya.

## 5. Keamanan dan deployment

Jelaskan penggunaan environment variables untuk `SECRET_KEY` dan `ADMIN_KEY`, pembatasan panjang input, proteksi endpoint statistik, konfigurasi cookie, server WSGI, HTTPS, dan pengelolaan database. Status deployment: `[BELUM DIDEploy / SUDAH DIDEploy, URL DAN BUKTI]`.

## 6. Kesimpulan dan pengembangan selanjutnya

Simpulkan hasil berdasarkan bukti pengujian. Cantumkan keterbatasan dataset, cakupan intent, dan rencana pengembangan seperti penambahan variasi bahasa pengguna serta peningkatan basis pengetahuan.

## Lampiran bukti

1. Screenshot aplikasi.
2. Output terminal pytest.
3. Output terminal evaluasi.
4. Rekap uji tiga pengguna.
5. Bukti deployment (jika benar-benar dilakukan).
