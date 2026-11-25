"""Simulasi operasional shuttle selama satu hari, dengan langkah waktu per menit.

Pola simulasi (diulang setiap menit):
1. Penumpang baru datang ke halte dan masuk antrean (FIFO).
2. Bus yang tiba di halte menurunkan penumpang yang tujuannya halte itu.
3. Penumpang di antrean naik selama kapasitas bus masih cukup.
Di akhir hari, penumpang yang masih di antrean dihitung "tertinggal".
"""

import math
import random

from core.data import buat_jadwal, durasi_putaran, interval_efektif, jumlah_halte
from core.waktu import ke_menit


def angka_poisson(rata_rata, rng):
    """Mengambil angka acak berdistribusi Poisson (algoritma Knuth).

    Dipakai untuk menentukan berapa penumpang datang dalam satu menit.
    """
    if rata_rata <= 0:
        return 0
    batas = math.exp(-rata_rata)
    k = 0
    p = 1.0
    while True:
        p *= rng.random()
        if p <= batas:
            return k
        k += 1


def laju_per_menit(data, menit, indeks_halte, pengali):
    """Rata-rata penumpang datang per menit di halte, berdasarkan tabel permintaan per jam."""
    jam = str(menit // 60)
    if jam not in data["permintaan"]:
        return 0.0
    return data["permintaan"][jam][indeks_halte] / 60.0 * pengali


def pilih_tujuan(asal, n, rng):
    """Memilih tujuan acak setelah halte asal.

    Indeks n berarti kembali ke halte pertama. Penumpang dari halte pertama
    tidak mungkin bertujuan ke halte pertama lagi, jadi batas atasnya n - 1.
    """
    batas_atas = n
    if asal == 0:
        batas_atas = n - 1
    return rng.randint(asal + 1, batas_atas)


def buat_penumpang(data, pengali, rng):
    """Membangkitkan semua penumpang dalam sehari.

    Mengembalikan dict: menit -> list penumpang yang datang pada menit itu.
    Tujuan dipilih acak di antara perhentian setelah halte asal
    (indeks n = kembali ke halte pertama).
    """
    n = jumlah_halte(data)
    mulai = ke_menit(data["jam_operasi"]["mulai"])
    selesai = ke_menit(data["jam_operasi"]["selesai"])
    kedatangan = {}
    nomor = 0
    for menit in range(mulai, selesai + 1):
        for halte in range(n):
            jumlah = angka_poisson(laju_per_menit(data, menit, halte, pengali), rng)
            for _ in range(jumlah):
                nomor += 1
                penumpang = {
                    "id": nomor,
                    "asal": halte,
                    "tujuan": pilih_tujuan(halte, n, rng),
                    "datang": menit,
                    "naik": None,
                }
                kedatangan.setdefault(menit, []).append(penumpang)
    return kedatangan


def buat_peta_kejadian(jadwal, n):
    """Dict menit -> list (indeks_trip, perhentian) bus yang tiba pada menit itu."""
    peta = {}
    for i, trip in enumerate(jadwal):
        for perhentian in range(n + 1):
            peta.setdefault(trip["tiba"][perhentian], []).append((i, perhentian))
    return peta


def proses_di_halte(antrean, isi_bus, perhentian, n, kapasitas, menit):
    """Proses satu bus di satu perhentian: turunkan lalu naikkan penumpang.

    Mengembalikan (jumlah_turun, list_penumpang_yang_naik).
    """
    # 1. Turunkan penumpang yang tujuannya perhentian ini.
    tetap = []
    turun = 0
    for p in isi_bus:
        if p["tujuan"] == perhentian:
            turun += 1
        else:
            tetap.append(p)
    isi_bus[:] = tetap

    # 2. Di akhir putaran (perhentian n) tidak ada yang naik.
    naik = []
    if perhentian == n:
        return turun, naik

    # 3. Naikkan penumpang dari depan antrean selama masih ada kursi.
    while antrean and len(isi_bus) < kapasitas:
        p = antrean.pop(0)
        p["naik"] = menit
        isi_bus.append(p)
        naik.append(p)
    return turun, naik


def simulasi_sehari(data, interval=None, jumlah_bus=None, pengali_permintaan=1.0, seed=42):
    """Menjalankan simulasi satu hari dan mengembalikan rekap hasilnya."""
    if interval is None:
        interval = data["interval_menit"]
    if jumlah_bus is None:
        jumlah_bus = data["armada"]["jumlah_bus"]
    rng = random.Random(seed)
    n = jumlah_halte(data)
    kapasitas = data["armada"]["kapasitas"]

    jadwal = buat_jadwal(data, interval, jumlah_bus)
    kedatangan = buat_penumpang(data, pengali_permintaan, rng)
    peta = buat_peta_kejadian(jadwal, n)

    antrean = []
    for _ in range(n):
        antrean.append([])
    isi_trip = []
    for _ in jadwal:
        isi_trip.append([])
    muatan_maks = [0] * len(jadwal)
    antrean_maks = [0] * n
    semua_penumpang = []
    grafik_antrean = []

    mulai = ke_menit(data["jam_operasi"]["mulai"])
    selesai = ke_menit(data["jam_operasi"]["selesai"])
    akhir = selesai
    if jadwal:
        akhir = max(selesai, jadwal[-1]["tiba"][-1])

    for menit in range(mulai, akhir + 1):
        # Langkah 1: penumpang baru datang.
        for p in kedatangan.get(menit, []):
            antrean[p["asal"]].append(p)
            semua_penumpang.append(p)
        # Langkah 2-3: bus yang tiba diproses di halte.
        for indeks_trip, perhentian in peta.get(menit, []):
            halte = perhentian % n
            proses_di_halte(antrean[halte] if perhentian < n else [], isi_trip[indeks_trip],
                            perhentian, n, kapasitas, menit)
            if len(isi_trip[indeks_trip]) > muatan_maks[indeks_trip]:
                muatan_maks[indeks_trip] = len(isi_trip[indeks_trip])
        # Catat panjang antrean.
        total = 0
        for h in range(n):
            total += len(antrean[h])
            if len(antrean[h]) > antrean_maks[h]:
                antrean_maks[h] = len(antrean[h])
        if (menit - mulai) % 10 == 0:
            grafik_antrean.append({"menit": menit, "antrean": total})

    return rekap_hasil(data, semua_penumpang, jadwal, muatan_maks, antrean_maks, grafik_antrean,
                       interval, jumlah_bus, pengali_permintaan, seed)


def rekap_hasil(data, semua_penumpang, jadwal, muatan_maks, antrean_maks, grafik_antrean,
                interval, jumlah_bus, pengali, seed):
    """Merangkum hasil simulasi menjadi angka-angka statistik."""
    n = jumlah_halte(data)
    kapasitas = data["armada"]["kapasitas"]

    daftar_tunggu = []
    tertinggal = 0
    per_halte = []
    for h in range(n):
        per_halte.append({"nama": data["halte"][h]["nama"], "datang": 0, "terlayani": 0,
                          "tertinggal": 0, "total_tunggu": 0, "antrean_maks": antrean_maks[h]})
    per_jam = {}

    for p in semua_penumpang:
        h = per_halte[p["asal"]]
        h["datang"] += 1
        jam = p["datang"] // 60
        if jam not in per_jam:
            per_jam[jam] = {"jam": jam, "datang": 0, "terlayani": 0, "total_tunggu": 0}
        per_jam[jam]["datang"] += 1
        if p["naik"] is None:
            tertinggal += 1
            h["tertinggal"] += 1
        else:
            tunggu = p["naik"] - p["datang"]
            daftar_tunggu.append(tunggu)
            h["terlayani"] += 1
            h["total_tunggu"] += tunggu
            per_jam[jam]["terlayani"] += 1
            per_jam[jam]["total_tunggu"] += tunggu

    for h in per_halte:
        h["rata_tunggu"] = h["total_tunggu"] / h["terlayani"] if h["terlayani"] else 0
    daftar_jam = []
    for jam in sorted(per_jam):
        j = per_jam[jam]
        j["rata_tunggu"] = j["total_tunggu"] / j["terlayani"] if j["terlayani"] else 0
        daftar_jam.append(j)

    total = len(semua_penumpang)
    terlayani = len(daftar_tunggu)
    jumlah_penuh = 0
    total_muatan = 0
    for m in muatan_maks:
        total_muatan += m
        if m >= kapasitas:
            jumlah_penuh += 1

    return {
        "interval_diminta": interval,
        "interval_efektif": interval_efektif(data, interval, jumlah_bus),
        "jumlah_bus": jumlah_bus,
        "kapasitas": kapasitas,
        "pengali_permintaan": pengali,
        "seed": seed,
        "durasi_putaran": durasi_putaran(data),
        "jumlah_trip": len(jadwal),
        "total_penumpang": total,
        "terlayani": terlayani,
        "tertinggal": tertinggal,
        "persen_terlayani": terlayani / total * 100 if total else 0,
        "persen_tertinggal": tertinggal / total * 100 if total else 0,
        "rata_tunggu": sum(daftar_tunggu) / terlayani if terlayani else 0,
        "maks_tunggu": max(daftar_tunggu) if daftar_tunggu else 0,
        "rata_keterisian": total_muatan / (len(muatan_maks) * kapasitas) * 100 if muatan_maks else 0,
        "trip_penuh": jumlah_penuh,
        "per_halte": per_halte,
        "per_jam": daftar_jam,
        "grafik_antrean": grafik_antrean,
    }
