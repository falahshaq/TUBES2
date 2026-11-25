"""Simulasi adopsi: berapa banyak orang yang mulai memakai shuttle
kalau informasi jadwal tersedia dan waktu tunggu membaik.

Dasar angka: kuesioner (misalnya 51,9% pernah memakai shuttle; dari yang belum,
60,7% beralasan tidak tahu jadwal dan 42,9% beralasan menunggu terlalu lama).

Model sederhana:
- Aplikasi ini menyelesaikan masalah informasi -> sebagian kelompok "tidak tahu jadwal" beralih.
- Jadwal yang lebih baik memperpendek waktu tunggu -> sebagian kelompok "tunggu lama" beralih,
  sebanding dengan seberapa besar waktu tunggu turun.
- Dua alasan bisa dimiliki orang yang sama, jadi peluang beralih digabung:
      peluang = 1 - (1 - a)(1 - b)
- Pengguna bertambah -> permintaan naik -> antrean bisa lebih panjang -> waktu tunggu naik lagi.
  Karena itu dihitung berulang (beberapa putaran) sampai hasilnya stabil.
"""

from core.simulasi import simulasi_sehari


def peluang_beralih(pengaturan, tunggu_awal, tunggu_baru, ada_informasi=True):
    """Peluang seorang bukan-pengguna mulai memakai shuttle (0 sampai 1)."""
    peluang = pengaturan["peluang_beralih"] / 100
    a = 0.0
    if ada_informasi:
        a = pengaturan["persen_alasan_info"] / 100 * peluang

    perbaikan = 0.0
    if tunggu_awal > 0:
        perbaikan = (tunggu_awal - tunggu_baru) / tunggu_awal
    if perbaikan < 0:
        perbaikan = 0.0
    if perbaikan > 1:
        perbaikan = 1.0
    b = pengaturan["persen_alasan_tunggu"] / 100 * peluang * perbaikan

    return 1 - (1 - a) * (1 - b)


def simulasi_adopsi(data, interval=None, jumlah_bus=None, ada_informasi=True, seed=42):
    """Menghitung perubahan jumlah pengguna dalam beberapa putaran."""
    pengaturan = data["adopsi"]
    pengguna_awal = pengaturan["persen_pengguna"] / 100

    # Kondisi awal: jadwal saat ini, permintaan normal.
    awal = simulasi_sehari(data, None, None, 1.0, seed)
    tunggu_awal = awal["rata_tunggu"]

    riwayat = []
    pengali = 1.0
    for putaran in range(1, pengaturan["putaran"] + 1):
        hasil = simulasi_sehari(data, interval, jumlah_bus, pengali, seed)
        peluang = peluang_beralih(pengaturan, tunggu_awal, hasil["rata_tunggu"], ada_informasi)
        pengguna = pengguna_awal + (1 - pengguna_awal) * peluang
        riwayat.append({
            "putaran": putaran,
            "pengali": pengali,
            "total_penumpang": hasil["total_penumpang"],
            "rata_tunggu": hasil["rata_tunggu"],
            "persen_tertinggal": hasil["persen_tertinggal"],
            "persen_pengguna": pengguna * 100,
        })
        pengali_baru = pengguna / pengguna_awal
        if abs(pengali_baru - pengali) < 0.01:
            break
        pengali = pengali_baru

    akhir = riwayat[-1]
    return {
        "persen_pengguna_awal": pengguna_awal * 100,
        "persen_pengguna_akhir": akhir["persen_pengguna"],
        "kenaikan_penumpang": (akhir["pengali"] - 1) * 100,
        "rata_tunggu_awal": tunggu_awal,
        "rata_tunggu_akhir": akhir["rata_tunggu"],
        "ada_informasi": ada_informasi,
        "riwayat": riwayat,
    }
