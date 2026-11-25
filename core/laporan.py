"""Analisis hasil simulasi dan pembuatan laporan teks."""

from core.waktu import format_durasi, ke_jam


def jam_tersibuk(hasil):
    """Jam dengan penumpang datang paling banyak."""
    terbaik = None
    for j in hasil["per_jam"]:
        if terbaik is None or j["datang"] > terbaik["datang"]:
            terbaik = j
    return terbaik


def halte_tersibuk(hasil):
    """Halte dengan penumpang datang paling banyak."""
    terbaik = None
    for h in hasil["per_halte"]:
        if terbaik is None or h["datang"] > terbaik["datang"]:
            terbaik = h
    return terbaik


def halte_tunggu_terlama(hasil):
    """Halte dengan rata-rata waktu tunggu paling lama."""
    terbaik = None
    for h in hasil["per_halte"]:
        if terbaik is None or h["rata_tunggu"] > terbaik["rata_tunggu"]:
            terbaik = h
    return terbaik


def buat_rekomendasi(hasil):
    """Saran untuk pengelola berdasarkan aturan sederhana (if-else)."""
    saran = []
    if hasil["persen_tertinggal"] > 5:
        saran.append(f"{hasil['persen_tertinggal']:.1f}% penumpang tertinggal. "
                     "Pertimbangkan menambah bus atau memperpendek interval.")
    if hasil["rata_tunggu"] > 10:
        saran.append(f"Rata-rata tunggu {hasil['rata_tunggu']:.1f} menit cukup lama. "
                     "Interval keberangkatan bisa diperpendek.")
    if hasil["rata_keterisian"] < 30:
        saran.append(f"Keterisian bus rata-rata hanya {hasil['rata_keterisian']:.0f}%. "
                     "Armada bisa dikurangi di luar jam sibuk.")
    if hasil["trip_penuh"] > hasil["jumlah_trip"] * 0.3:
        saran.append(f"{hasil['trip_penuh']} dari {hasil['jumlah_trip']} perjalanan penuh. "
                     "Kapasitas kurang di jam sibuk.")
    if hasil["interval_efektif"] > hasil["interval_diminta"]:
        saran.append(f"Interval {hasil['interval_diminta']} menit tidak bisa dicapai dengan "
                     f"{hasil['jumlah_bus']} bus (satu putaran {hasil['durasi_putaran']} menit), "
                     f"jadi interval nyatanya {hasil['interval_efektif']} menit.")
    if not saran:
        saran.append("Layanan sudah cukup baik untuk permintaan yang disimulasikan.")
    return saran


def ringkasan(hasil):
    """Kumpulan analisis penting dalam satu dict."""
    return {
        "jam_tersibuk": jam_tersibuk(hasil),
        "halte_tersibuk": halte_tersibuk(hasil),
        "halte_tunggu_terlama": halte_tunggu_terlama(hasil),
        "rekomendasi": buat_rekomendasi(hasil),
    }


def buat_teks_laporan(data, hasil):
    """Membuat laporan dalam bentuk teks (bisa ditampilkan atau disimpan ke file)."""
    r = ringkasan(hasil)
    baris = []
    baris.append("=" * 60)
    baris.append(f"LAPORAN SIMULASI - {data['nama_layanan']}")
    baris.append("=" * 60)
    baris.append(f"Jam operasi        : {data['jam_operasi']['mulai']} - {data['jam_operasi']['selesai']}")
    baris.append(f"Jumlah bus         : {hasil['jumlah_bus']} (kapasitas {hasil['kapasitas']})")
    baris.append(f"Interval           : {hasil['interval_efektif']} menit")
    baris.append(f"Satu putaran       : {format_durasi(hasil['durasi_putaran'])}")
    baris.append(f"Jumlah perjalanan  : {hasil['jumlah_trip']}")
    baris.append("-" * 60)
    baris.append(f"Total penumpang    : {hasil['total_penumpang']}")
    baris.append(f"Terlayani          : {hasil['terlayani']} ({hasil['persen_terlayani']:.1f}%)")
    baris.append(f"Tertinggal         : {hasil['tertinggal']} ({hasil['persen_tertinggal']:.1f}%)")
    baris.append(f"Rata-rata tunggu   : {hasil['rata_tunggu']:.1f} menit")
    baris.append(f"Tunggu terlama     : {hasil['maks_tunggu']} menit")
    baris.append(f"Rata keterisian bus: {hasil['rata_keterisian']:.1f}%")
    baris.append("-" * 60)
    if r["jam_tersibuk"]:
        j = r["jam_tersibuk"]
        baris.append(f"Jam tersibuk       : {ke_jam(j['jam'] * 60)} ({j['datang']} penumpang)")
    if r["halte_tersibuk"]:
        baris.append(f"Halte tersibuk     : {r['halte_tersibuk']['nama']} ({r['halte_tersibuk']['datang']} penumpang)")
    baris.append("")
    baris.append(f"{'Halte':<24}{'Datang':>8}{'Tertinggal':>12}{'Rata tunggu':>13}")
    for h in hasil["per_halte"]:
        baris.append(f"{h['nama'][:23]:<24}{h['datang']:>8}{h['tertinggal']:>12}{h['rata_tunggu']:>10.1f} mnt")
    baris.append("")
    baris.append("Rekomendasi:")
    for i, s in enumerate(r["rekomendasi"], start=1):
        baris.append(f"  {i}. {s}")
    baris.append("=" * 60)
    return "\n".join(baris)
