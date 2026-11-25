"""Optimasi jadwal dengan pencarian menyeluruh (brute force).

Setiap kombinasi (interval, jumlah bus) dicoba, disimulasikan, lalu diberi skor.
Skor makin KECIL makin baik:

    skor = bobot_tunggu     x rata-rata waktu tunggu (menit)
         + bobot_tertinggal x persen penumpang tertinggal
         + biaya_per_bus    x jumlah bus

Semua kombinasi memakai seed acak yang sama supaya perbandingannya adil
(penumpang yang datang persis sama, hanya jadwalnya yang berbeda).
"""

from core.simulasi import simulasi_sehari


def hitung_skor(hasil, pengaturan):
    """Menghitung skor dari hasil simulasi. Makin kecil makin baik."""
    return (
        pengaturan["bobot_tunggu"] * hasil["rata_tunggu"]
        + pengaturan["bobot_tertinggal"] * hasil["persen_tertinggal"]
        + pengaturan["biaya_per_bus"] * hasil["jumlah_bus"]
    )


def daftar_kandidat(pengaturan):
    """Semua kombinasi (interval, jumlah_bus) yang akan dicoba."""
    kandidat = []
    interval = pengaturan["interval_min"]
    while interval <= pengaturan["interval_max"]:
        for bus in range(pengaturan["bus_min"], pengaturan["bus_max"] + 1):
            kandidat.append((interval, bus))
        interval += pengaturan["interval_langkah"]
    return kandidat


def optimasi_jadwal(data, seed=42, pengali_permintaan=1.0, pengaturan=None):
    """Mencari kombinasi interval dan jumlah bus dengan skor terbaik.

    Mengembalikan dict berisi: semua hasil (urut dari terbaik), yang terbaik,
    dan hasil jadwal saat ini sebagai pembanding.
    """
    if pengaturan is None:
        pengaturan = data["optimasi"]

    semua = []
    sudah_dicoba = {}
    for interval, bus in daftar_kandidat(pengaturan):
        hasil = simulasi_sehari(data, interval, bus, pengali_permintaan, seed)
        # Interval yang terlalu kecil untuk armadanya akan dinaikkan otomatis,
        # jadi beberapa kombinasi bisa menghasilkan jadwal yang sama persis.
        kunci = (hasil["interval_efektif"], bus)
        if kunci in sudah_dicoba:
            continue
        sudah_dicoba[kunci] = True
        semua.append(ringkas(hasil, hitung_skor(hasil, pengaturan)))

    semua.sort(key=lambda h: h["skor"])

    sekarang = simulasi_sehari(data, None, None, pengali_permintaan, seed)
    return {
        "terbaik": semua[0] if semua else None,
        "semua": semua,
        "jumlah_dicoba": len(daftar_kandidat(pengaturan)),
        "saat_ini": ringkas(sekarang, hitung_skor(sekarang, pengaturan)),
        "pengaturan": pengaturan,
    }


def ringkas(hasil, skor):
    """Mengambil angka penting saja dari hasil simulasi."""
    return {
        "interval_diminta": hasil["interval_diminta"],
        "interval": hasil["interval_efektif"],
        "jumlah_bus": hasil["jumlah_bus"],
        "jumlah_trip": hasil["jumlah_trip"],
        "rata_tunggu": hasil["rata_tunggu"],
        "maks_tunggu": hasil["maks_tunggu"],
        "persen_tertinggal": hasil["persen_tertinggal"],
        "rata_keterisian": hasil["rata_keterisian"],
        "skor": skor,
    }
