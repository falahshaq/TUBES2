"""Layanan untuk penumpang: jadwal halte, bus berikutnya, dan estimasi waktu tiba."""

from core.data import buat_jadwal, durasi_putaran, jumlah_halte, nama_halte, selisih_waktu_halte


def jadwal_di_halte(data, indeks_halte):
    """List waktu (menit) bus tiba di halte tertentu sepanjang hari."""
    hasil = []
    for trip in buat_jadwal(data):
        hasil.append({"waktu": trip["tiba"][indeks_halte], "bus": trip["bus"], "trip": trip["nomor"]})
    return hasil


def cari_bus_berikutnya(data, indeks_halte, sekarang, jumlah=3):
    """Mencari beberapa bus terdekat yang akan tiba di halte setelah waktu `sekarang`.

    Pola: telusuri jadwal secara berurutan (linear search), ambil yang
    waktunya >= sekarang, berhenti setelah dapat `jumlah` bus.
    """
    hasil = []
    for kedatangan in jadwal_di_halte(data, indeks_halte):
        if kedatangan["waktu"] >= sekarang:
            kedatangan["tunggu"] = kedatangan["waktu"] - sekarang
            hasil.append(kedatangan)
            if len(hasil) == jumlah:
                break
    return hasil


def lama_perjalanan(data, asal, tujuan):
    """Menit perjalanan di dalam bus dari halte asal ke halte tujuan.

    Karena rute melingkar, kalau tujuan ada "di belakang" asal,
    penumpang tetap di bus melewati halte pertama.
    """
    selisih = selisih_waktu_halte(data)
    return (selisih[tujuan] - selisih[asal]) % durasi_putaran(data)


def halte_yang_dilewati(data, asal, tujuan):
    """List nama halte dari asal sampai tujuan (urut sesuai rute)."""
    n = jumlah_halte(data)
    rute = [nama_halte(data, asal)]
    i = asal
    while i != tujuan:
        i = (i + 1) % n
        rute.append(nama_halte(data, i))
    return rute


def estimasi_perjalanan(data, asal, tujuan, sekarang):
    """Estimasi lengkap: kapan bus datang, berapa lama menunggu, dan kapan sampai.

    Mengembalikan dict, atau None kalau sudah tidak ada bus hari ini.
    """
    if asal == tujuan:
        raise ValueError("Halte asal dan tujuan tidak boleh sama.")
    berikutnya = cari_bus_berikutnya(data, asal, sekarang, jumlah=1)
    if not berikutnya:
        return None
    bus = berikutnya[0]
    durasi = lama_perjalanan(data, asal, tujuan)
    return {
        "asal": nama_halte(data, asal),
        "tujuan": nama_halte(data, tujuan),
        "bus": bus["bus"],
        "trip": bus["trip"],
        "waktu_bus_datang": bus["waktu"],
        "lama_tunggu": bus["tunggu"],
        "lama_perjalanan": durasi,
        "waktu_tiba": bus["waktu"] + durasi,
        "total_waktu": bus["tunggu"] + durasi,
        "rute": halte_yang_dilewati(data, asal, tujuan),
    }
