# Smart Shuttle ITB Jatinangor

Sistem informasi jadwal dan optimasi shuttle kampus, untuk Proyek II WI1102 Berpikir Komputasional (Kelompok 01 K33).

Ada dua versi yang memakai **logika yang sama** (folder `core/`):

- **Terminal**: `main.py`
- **Web**: `api/index.py` (Flask), bisa di-deploy ke Vercel

> ⚠️ Data di `data/shuttle.json` masih **data contoh**. Ganti dengan data survei lapangan.

## Struktur folder

```
core/                  logika inti, tanpa input()/print()
  waktu.py             konversi jam <-> menit, jam WIB sekarang
  data.py              model rute, jadwal, validasi data
  penumpang.py         jadwal halte, bus berikutnya, estimasi waktu tiba
  simulasi.py          simulasi sehari per menit, proses di halte (antrean)
  optimasi.py          fungsi skor + brute force interval x jumlah bus
  adopsi.py            simulasi pertambahan pengguna
  laporan.py           analisis hasil + laporan teks
  penyimpanan.py       baca/simpan data (file JSON atau Redis)
data/
  shuttle.json         data yang sedang dipakai (bisa diubah)
  shuttle_default.json data contoh untuk reset
main.py                program terminal (menu)
api/index.py           program web (Flask)
templates/             halaman HTML
vercel.json            pengaturan Vercel
requirements.txt       library Python untuk web (Flask)
```

## Hubungan dengan flowchart di laporan

| Flowchart | Fungsi |
|---|---|
| 2.2.1 Program utama | `main()` di `main.py` |
| 2.2.2 Layanan penumpang | `menu_penumpang()` di `main.py` |
| 2.2.3 Pencarian bus berikutnya | `cari_bus_berikutnya()` di `core/penumpang.py` |
| 2.2.4 Estimasi waktu tiba | `estimasi_perjalanan()` di `core/penumpang.py` |
| 2.2.5 Menu simulasi & optimasi | `menu_pengelola()` di `main.py` |
| 2.2.6 Simulasi sehari | `simulasi_sehari()` di `core/simulasi.py` |
| 2.2.7 Proses di halte | `proses_di_halte()` di `core/simulasi.py` |
| 2.2.8 Optimasi jadwal | `optimasi_jadwal()` + `hitung_skor()` di `core/optimasi.py` |
| 2.2.9 Simulasi adopsi | `simulasi_adopsi()` di `core/adopsi.py` |
| 2.2.10 Analisis & laporan | `ringkasan()` + `buat_teks_laporan()` di `core/laporan.py` |

## Menjalankan di laptop

Butuh Python 3.10 ke atas.

**Versi terminal** (tidak butuh library tambahan):

```bash
python main.py
```

**Versi web:**

```bash
pip install -r requirements.txt
python api/index.py
```

Lalu buka http://127.0.0.1:5000 di browser.

## Mengubah data

Data bisa diubah dengan tiga cara:

1. Menu **Kelola data** di terminal
2. Halaman **Data** di web (form atau edit JSON langsung)
3. Edit file `data/shuttle.json` langsung

Isi data:

- `jam_operasi`: jam mulai dan selesai keberangkatan
- `halte`: daftar halte **sesuai urutan rute** (rute melingkar, kembali ke halte pertama)
- `waktu_tempuh`: menit dari halte ke-i ke halte berikutnya (yang terakhir = kembali ke halte pertama)
- `waktu_henti`: menit bus berhenti di tiap halte
- `armada`: jumlah bus dan kapasitas
- `interval_menit`: jarak antar keberangkatan
- `permintaan`: rata-rata penumpang datang **per jam** di tiap halte, contoh `"7": [60, 70, 8, 5, 4, 3]` berarti jam 07:00–07:59
- `optimasi`: rentang yang dicoba + bobot fungsi skor
- `adopsi`: angka hasil kuesioner

## Deploy ke Vercel

1. Login ke https://vercel.com pakai akun GitHub
2. **Add New → Project**, pilih repo ini, lalu klik **Deploy** (pengaturan biarkan default)
3. Setelah selesai, web bisa dibuka di `https://<nama-proyek>.vercel.app`

Setiap `git push` ke branch `main` otomatis meng-update web.

### Supaya data bisa diedit dari web yang online

Di Vercel, program **tidak bisa menulis file** saat berjalan. Jadi untuk menyimpan perubahan data dibutuhkan database kecil:

1. Di dashboard proyek Vercel buka tab **Storage → Create / Browse Marketplace → Upstash (Redis)**, buat database gratis, lalu **Connect** ke proyek ini. Variabel `KV_REST_API_URL` dan `KV_REST_API_TOKEN` otomatis ditambahkan.
2. Buka **Settings → Environment Variables**, tambahkan `ADMIN_PASSWORD` dengan kata sandi pilihan kalian. Tanpa ini halaman Data terkunci supaya tidak bisa diubah sembarang orang.
3. **Redeploy** (tab Deployments → titik tiga → Redeploy).

Tanpa langkah ini, semua fitur tetap jalan, hanya data tidak bisa diubah lewat web online (ubah lewat `data/shuttle.json` lalu push).

## Konsep berpikir komputasional

- **Dekomposisi**: tiap fitur jadi fungsi sendiri di modul yang terpisah
- **Abstraksi**: waktu = menit sejak 00:00; rute = list halte melingkar; penumpang = asal, tujuan, waktu datang
- **Pola**: tiap menit simulasi berulang dengan pola yang sama (datang → antre → turun → naik)
- **Algoritma**: pencarian linear, simulasi waktu diskrit, antrean FIFO, brute force dengan fungsi skor
