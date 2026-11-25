"""Membaca dan menyimpan data shuttle.

Ada dua tempat penyimpanan:
1. File  data/shuttle.json  -> dipakai saat program jalan di laptop (terminal / Flask lokal).
2. Redis (Upstash / Vercel KV) -> dipakai saat jalan di Vercel, karena di Vercel
   file tidak bisa ditulis saat program berjalan.

Kalau variabel lingkungan Redis tersedia, program otomatis memakai Redis.
Kalau tidak, program memakai file JSON.
"""

import json
import os
import urllib.request

FOLDER_PROYEK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE_DATA = os.path.join(FOLDER_PROYEK, "data", "shuttle.json")
FILE_DEFAULT = os.path.join(FOLDER_PROYEK, "data", "shuttle_default.json")
KUNCI_REDIS = "smart_shuttle:data"


# ---------- Redis lewat REST API (tanpa library tambahan) ----------

def _konfigurasi_redis():
    """Mengembalikan (url, token) Redis kalau tersedia, atau None."""
    pasangan = [
        ("KV_REST_API_URL", "KV_REST_API_TOKEN"),
        ("UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN"),
    ]
    for nama_url, nama_token in pasangan:
        url = os.environ.get(nama_url)
        token = os.environ.get(nama_token)
        if url and token:
            return url.rstrip("/"), token
    return None


def _perintah_redis(perintah):
    """Mengirim satu perintah Redis, contoh ["GET", "kunci"]."""
    url, token = _konfigurasi_redis()
    permintaan = urllib.request.Request(
        url,
        data=json.dumps(perintah).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(permintaan, timeout=10) as respons:
        return json.loads(respons.read().decode("utf-8")).get("result")


# ---------- Fungsi utama ----------

def jenis_penyimpanan():
    """Teks singkat: data disimpan di mana."""
    if _konfigurasi_redis():
        return "redis"
    return "file"


def bisa_disimpan():
    """True kalau perubahan data bisa disimpan permanen."""
    if _konfigurasi_redis():
        return True
    # Di Vercel tanpa Redis, sistem file hanya bisa dibaca.
    return not os.environ.get("VERCEL")


def muat_data_default():
    """Membaca data bawaan (contoh) dari file."""
    with open(FILE_DEFAULT, encoding="utf-8") as f:
        return json.load(f)


def muat_data():
    """Membaca data shuttle yang sedang dipakai."""
    if _konfigurasi_redis():
        try:
            isi = _perintah_redis(["GET", KUNCI_REDIS])
            if isi:
                return json.loads(isi)
        except Exception:
            pass  # Redis bermasalah: pakai file sebagai cadangan.
    if os.path.exists(FILE_DATA):
        with open(FILE_DATA, encoding="utf-8") as f:
            return json.load(f)
    return muat_data_default()


def simpan_data(data):
    """Menyimpan data shuttle. Mengembalikan pesan teks hasilnya."""
    teks = json.dumps(data, indent=2, ensure_ascii=False)
    if _konfigurasi_redis():
        _perintah_redis(["SET", KUNCI_REDIS, teks])
        return "Data tersimpan di database (Redis)."
    if not bisa_disimpan():
        raise PermissionError(
            "Di Vercel data tidak bisa disimpan ke file. "
            "Hubungkan database Redis (Upstash) di tab Storage Vercel."
        )
    with open(FILE_DATA, "w", encoding="utf-8") as f:
        f.write(teks)
    return "Data tersimpan di data/shuttle.json."


def reset_data():
    """Mengembalikan data ke data contoh bawaan."""
    data = muat_data_default()
    pesan = simpan_data(data)
    return data, pesan
