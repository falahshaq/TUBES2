"""Smart Shuttle ITB Jatinangor - versi terminal.

Jalankan:  python main.py

File ini hanya mengurus tampilan (input/print). Semua perhitungan
ada di folder core/, sehingga bisa dipakai bersama oleh versi web.
"""

import copy

from core.adopsi import simulasi_adopsi
from core.data import daftar_nama_halte, durasi_putaran, jumlah_halte, validasi_data
from core.laporan import buat_teks_laporan
from core.optimasi import optimasi_jadwal
from core.penumpang import cari_bus_berikutnya, estimasi_perjalanan, jadwal_di_halte
from core.penyimpanan import muat_data, reset_data, simpan_data
from core.simulasi import simulasi_sehari
from core.waktu import format_durasi, ke_jam, ke_menit, menit_sekarang


# ====================== Fungsi bantu input ======================

def garis(judul=""):
    print()
    print("=" * 60)
    if judul:
        print(judul.center(60))
        print("=" * 60)


def jeda():
    input("\nTekan Enter untuk lanjut...")


def input_angka(pesan, minimum=None, maksimum=None, bawaan=None, desimal=False):
    """Meminta angka dari pengguna, diulang sampai valid."""
    while True:
        teks = input(pesan).strip()
        if teks == "" and bawaan is not None:
            return bawaan
        try:
            angka = float(teks.replace(",", ".")) if desimal else int(teks)
        except ValueError:
            print("  ! Masukkan angka yang benar.")
            continue
        if minimum is not None and angka < minimum:
            print(f"  ! Minimal {minimum}.")
        elif maksimum is not None and angka > maksimum:
            print(f"  ! Maksimal {maksimum}.")
        else:
            return angka


def input_jam(pesan, bawaan=None):
    """Meminta jam format HH:MM. Mengembalikan menit sejak 00:00."""
    while True:
        teks = input(pesan).strip()
        if teks == "" and bawaan is not None:
            return bawaan
        try:
            return ke_menit(teks)
        except ValueError as e:
            print(f"  ! {e}")


def pilih_halte(data, pesan="Pilih halte"):
    """Menampilkan daftar halte dan mengembalikan indeks yang dipilih."""
    nama = daftar_nama_halte(data)
    for i, n in enumerate(nama, start=1):
        print(f"  {i}. {n}")
    return input_angka(f"{pesan} (1-{len(nama)}): ", 1, len(nama)) - 1


def pilih_menu(pilihan):
    """Menampilkan menu dan mengembalikan kode pilihan."""
    for kode, teks in pilihan:
        print(f"  [{kode}] {teks}")
    kode_valid = [k for k, _ in pilihan]
    while True:
        p = input("Pilihan: ").strip()
        if p in kode_valid:
            return p
        print("  ! Pilihan tidak ada.")


# ====================== Layanan penumpang ======================

def menu_jadwal_halte(data):
    garis("JADWAL DI HALTE")
    h = pilih_halte(data)
    jadwal = jadwal_di_halte(data, h)
    print(f"\nBus tiba di {data['halte'][h]['nama']} ({len(jadwal)} kali sehari):")
    for i, k in enumerate(jadwal):
        print(f"  {ke_jam(k['waktu'])} (bus {k['bus']})", end="")
        print() if (i + 1) % 4 == 0 else print("   ", end="")
    print()


def menu_bus_berikutnya(data):
    garis("BUS BERIKUTNYA")
    h = pilih_halte(data)
    sekarang = menit_sekarang()
    sekarang = input_jam(f"Jam keberangkatan (HH:MM, Enter = sekarang {ke_jam(sekarang)}): ", sekarang)
    hasil = cari_bus_berikutnya(data, h, sekarang, 3)
    if not hasil:
        print("\nTidak ada bus lagi hari ini di halte ini.")
        return
    print(f"\nBus berikutnya di {data['halte'][h]['nama']} setelah {ke_jam(sekarang)}:")
    for k in hasil:
        print(f"  - {ke_jam(k['waktu'])}  bus {k['bus']}  (tunggu {format_durasi(k['tunggu'])})")


def menu_estimasi(data):
    garis("ESTIMASI WAKTU TIBA")
    print("Halte asal:")
    asal = pilih_halte(data, "Asal")
    print("Halte tujuan:")
    tujuan = pilih_halte(data, "Tujuan")
    if asal == tujuan:
        print("\nAsal dan tujuan sama, tidak perlu naik shuttle.")
        return
    sekarang = menit_sekarang()
    sekarang = input_jam(f"Jam berangkat (HH:MM, Enter = sekarang {ke_jam(sekarang)}): ", sekarang)
    e = estimasi_perjalanan(data, asal, tujuan, sekarang)
    if e is None:
        print("\nTidak ada bus lagi hari ini.")
        return
    print(f"\nRute     : {' -> '.join(e['rute'])}")
    print(f"Bus      : {e['bus']} datang pukul {ke_jam(e['waktu_bus_datang'])}")
    print(f"Menunggu : {format_durasi(e['lama_tunggu'])}")
    print(f"Di bus   : {format_durasi(e['lama_perjalanan'])}")
    print(f"Tiba     : pukul {ke_jam(e['waktu_tiba'])} (total {format_durasi(e['total_waktu'])})")


def menu_penumpang(data):
    while True:
        garis("LAYANAN PENUMPANG")
        p = pilih_menu([("1", "Lihat jadwal di halte"), ("2", "Cari bus berikutnya"),
                        ("3", "Estimasi waktu tiba"), ("0", "Kembali")])
        if p == "0":
            return
        if p == "1":
            menu_jadwal_halte(data)
        elif p == "2":
            menu_bus_berikutnya(data)
        elif p == "3":
            menu_estimasi(data)
        jeda()


# ====================== Simulasi dan optimasi ======================

def input_skenario(data):
    """Meminta interval, jumlah bus, pengali permintaan, dan seed (Enter = pakai data)."""
    print("(Tekan Enter untuk memakai nilai dari data)")
    interval = input_angka(f"Interval menit [{data['interval_menit']}]: ", 1, 240, data["interval_menit"])
    bus = input_angka(f"Jumlah bus [{data['armada']['jumlah_bus']}]: ", 1, 50, data["armada"]["jumlah_bus"])
    pengali = input_angka("Pengali permintaan, 1 = normal [1]: ", 0.1, 10, 1.0, desimal=True)
    seed = input_angka("Seed acak [42]: ", 0, None, 42)
    return interval, bus, pengali, seed


def menu_simulasi(data):
    garis("SIMULASI SEHARI")
    interval, bus, pengali, seed = input_skenario(data)
    hasil = simulasi_sehari(data, interval, bus, pengali, seed)
    teks = buat_teks_laporan(data, hasil)
    print()
    print(teks)
    print("\nPanjang antrean total sepanjang hari:")
    tertinggi = max([g["antrean"] for g in hasil["grafik_antrean"]] + [1])
    for g in hasil["grafik_antrean"]:
        if (g["menit"] % 30) == 0:
            batang = "#" * int(g["antrean"] / tertinggi * 40)
            print(f"  {ke_jam(g['menit'])} |{batang} {g['antrean']}")
    if input("\nSimpan laporan ke file laporan_simulasi.txt? (y/n): ").strip().lower() == "y":
        with open("laporan_simulasi.txt", "w", encoding="utf-8") as f:
            f.write(teks)
        print("Tersimpan di laporan_simulasi.txt")


def menu_optimasi(data):
    garis("OPTIMASI JADWAL")
    o = data["optimasi"]
    print(f"Mencoba interval {o['interval_min']}-{o['interval_max']} menit (langkah {o['interval_langkah']}) "
          f"dan {o['bus_min']}-{o['bus_max']} bus.")
    print(f"Skor = {o['bobot_tunggu']} x rata tunggu + {o['bobot_tertinggal']} x % tertinggal "
          f"+ {o['biaya_per_bus']} x jumlah bus  (makin kecil makin baik)")
    hasil = optimasi_jadwal(data)
    print(f"\n{'#':>3} {'Interval':>9} {'Bus':>4} {'Tunggu':>8} {'Tertinggal':>11} {'Isi bus':>8} {'Skor':>7}")
    for i, h in enumerate(hasil["semua"][:10], start=1):
        print(f"{i:>3} {h['interval']:>6} mnt {h['jumlah_bus']:>4} {h['rata_tunggu']:>6.1f} m "
              f"{h['persen_tertinggal']:>10.1f}% {h['rata_keterisian']:>7.0f}% {h['skor']:>7.2f}")
    s = hasil["saat_ini"]
    t = hasil["terbaik"]
    print(f"\nJadwal saat ini : interval {s['interval']} mnt, {s['jumlah_bus']} bus, skor {s['skor']:.2f}")
    print(f"Jadwal terbaik  : interval {t['interval']} mnt, {t['jumlah_bus']} bus, skor {t['skor']:.2f}")
    if t["skor"] < s["skor"]:
        if input("\nPakai jadwal terbaik sebagai data baru? (y/n): ").strip().lower() == "y":
            data["interval_menit"] = t["interval"]
            data["armada"]["jumlah_bus"] = t["jumlah_bus"]
            print(simpan_data(data))
    else:
        print("Jadwal saat ini sudah yang terbaik.")


def menu_adopsi(data):
    garis("SIMULASI ADOPSI")
    a = data["adopsi"]
    print(f"Pengguna saat ini {a['persen_pengguna']}%. Dari yang belum memakai: "
          f"{a['persen_alasan_info']}% tidak tahu jadwal, {a['persen_alasan_tunggu']}% menunggu terlalu lama.")
    print("Skenario jadwal baru:")
    interval = input_angka(f"Interval menit [{data['interval_menit']}]: ", 1, 240, data["interval_menit"])
    bus = input_angka(f"Jumlah bus [{data['armada']['jumlah_bus']}]: ", 1, 50, data["armada"]["jumlah_bus"])
    info = input("Aplikasi info jadwal tersedia? (y/n) [y]: ").strip().lower() != "n"
    hasil = simulasi_adopsi(data, interval, bus, info)
    print(f"\n{'Putaran':>7} {'Penumpang':>10} {'Tunggu':>8} {'Pengguna':>9}")
    for r in hasil["riwayat"]:
        print(f"{r['putaran']:>7} {r['total_penumpang']:>10} {r['rata_tunggu']:>6.1f} m {r['persen_pengguna']:>8.1f}%")
    print(f"\nPengguna naik dari {hasil['persen_pengguna_awal']:.1f}% menjadi {hasil['persen_pengguna_akhir']:.1f}%")
    print(f"Jumlah penumpang naik sekitar {hasil['kenaikan_penumpang']:.0f}%")
    print(f"Rata-rata tunggu: {hasil['rata_tunggu_awal']:.1f} -> {hasil['rata_tunggu_akhir']:.1f} menit")


def menu_pengelola(data):
    while True:
        garis("SIMULASI & OPTIMASI (PENGELOLA)")
        p = pilih_menu([("1", "Simulasi sehari + laporan"), ("2", "Optimasi jadwal"),
                        ("3", "Simulasi adopsi pengguna"), ("0", "Kembali")])
        if p == "0":
            return
        if p == "1":
            menu_simulasi(data)
        elif p == "2":
            menu_optimasi(data)
        elif p == "3":
            menu_adopsi(data)
        jeda()


# ====================== Kelola data ======================

def tampilkan_data(data):
    garis("DATA SAAT INI")
    print(f"Jam operasi : {data['jam_operasi']['mulai']} - {data['jam_operasi']['selesai']}")
    print(f"Armada      : {data['armada']['jumlah_bus']} bus, kapasitas {data['armada']['kapasitas']}")
    print(f"Interval    : {data['interval_menit']} menit, waktu henti {data['waktu_henti']} menit")
    print(f"Satu putaran: {durasi_putaran(data)} menit")
    print("\nRute:")
    n = jumlah_halte(data)
    for i in range(n):
        berikut = data["halte"][(i + 1) % n]["nama"]
        print(f"  {i + 1}. {data['halte'][i]['nama']:<24} -> {berikut} ({data['waktu_tempuh'][i]} mnt)")
    print("\nPermintaan (penumpang per jam):")
    print("  Jam  " + " ".join(f"H{i + 1:<3}" for i in range(n)))
    for jam in sorted(data["permintaan"], key=int):
        print(f"  {int(jam):02d}   " + " ".join(f"{x:<4}" for x in data["permintaan"][jam]))


def ubah_halte(data):
    p = pilih_menu([("1", "Tambah halte"), ("2", "Ubah nama / waktu tempuh"),
                    ("3", "Hapus halte"), ("0", "Batal")])
    if p == "1":
        nama = input("Nama halte baru: ").strip()
        print("Sisipkan setelah halte nomor berapa?")
        posisi = pilih_halte(data, "Setelah") + 1
        tempuh = input_angka("Waktu tempuh ke halte berikutnya (menit): ", 1, 120)
        data["halte"].insert(posisi, {"nama": nama})
        data["waktu_tempuh"].insert(posisi, tempuh)
        for jam in data["permintaan"]:
            data["permintaan"][jam].insert(posisi, 0)
        print("Permintaan untuk halte baru diisi 0, ubah lewat menu permintaan.")
    elif p == "2":
        h = pilih_halte(data)
        nama = input(f"Nama [{data['halte'][h]['nama']}]: ").strip()
        if nama:
            data["halte"][h]["nama"] = nama
        data["waktu_tempuh"][h] = input_angka(
            f"Waktu tempuh ke halte berikutnya [{data['waktu_tempuh'][h]}]: ", 1, 120, data["waktu_tempuh"][h])
    elif p == "3":
        h = pilih_halte(data, "Hapus halte")
        data["halte"].pop(h)
        data["waktu_tempuh"].pop(h)
        for jam in data["permintaan"]:
            data["permintaan"][jam].pop(h)


def ubah_permintaan(data):
    jam = str(input_angka("Jam berapa (0-23): ", 0, 23))
    n = jumlah_halte(data)
    lama = data["permintaan"].get(jam, [0] * n)
    baru = []
    for i in range(n):
        baru.append(input_angka(f"  {data['halte'][i]['nama']} [{lama[i]}]: ", 0, 10000, lama[i]))
    data["permintaan"][jam] = baru


def menu_data(data):
    """Mengubah data. Perubahan dikerjakan di salinan, baru disimpan kalau valid."""
    salinan = copy.deepcopy(data)
    while True:
        tampilkan_data(salinan)
        print()
        p = pilih_menu([("1", "Ubah jam operasi"), ("2", "Ubah armada & interval"),
                        ("3", "Kelola halte & waktu tempuh"), ("4", "Ubah permintaan per jam"),
                        ("5", "Simpan perubahan"), ("6", "Reset ke data contoh"),
                        ("0", "Kembali tanpa menyimpan")])
        if p == "0":
            return data
        if p == "1":
            mulai = input_jam(f"Jam mulai [{salinan['jam_operasi']['mulai']}]: ", ke_menit(salinan["jam_operasi"]["mulai"]))
            selesai = input_jam(f"Jam selesai [{salinan['jam_operasi']['selesai']}]: ", ke_menit(salinan["jam_operasi"]["selesai"]))
            salinan["jam_operasi"] = {"mulai": ke_jam(mulai), "selesai": ke_jam(selesai)}
        elif p == "2":
            a = salinan["armada"]
            a["jumlah_bus"] = input_angka(f"Jumlah bus [{a['jumlah_bus']}]: ", 1, 50, a["jumlah_bus"])
            a["kapasitas"] = input_angka(f"Kapasitas per bus [{a['kapasitas']}]: ", 1, 200, a["kapasitas"])
            salinan["interval_menit"] = input_angka(f"Interval menit [{salinan['interval_menit']}]: ", 1, 240, salinan["interval_menit"])
            salinan["waktu_henti"] = input_angka(f"Waktu henti di halte [{salinan['waktu_henti']}]: ", 0, 30, salinan["waktu_henti"])
        elif p == "3":
            ubah_halte(salinan)
        elif p == "4":
            ubah_permintaan(salinan)
        elif p == "5":
            salah = validasi_data(salinan)
            if salah:
                print("\nData belum bisa disimpan:")
                for s in salah:
                    print(f"  - {s}")
            else:
                print(simpan_data(salinan))
                return salinan
            jeda()
        elif p == "6":
            if input("Yakin reset semua data? (y/n): ").strip().lower() == "y":
                baru, pesan = reset_data()
                print(pesan)
                return baru


# ====================== Program utama ======================

def main():
    data = muat_data()
    while True:
        garis(data["nama_layanan"].upper())
        print(f"Sekarang pukul {ke_jam(menit_sekarang())} WIB")
        if data.get("catatan"):
            print(f"Catatan: {data['catatan']}")
        print()
        p = pilih_menu([("1", "Layanan penumpang"), ("2", "Simulasi & optimasi (pengelola)"),
                        ("3", "Kelola data"), ("0", "Keluar")])
        if p == "0":
            print("Terima kasih telah memakai Smart Shuttle!")
            break
        if p == "1":
            menu_penumpang(data)
        elif p == "2":
            menu_pengelola(data)
        elif p == "3":
            data = menu_data(data)


if __name__ == "__main__":
    main()
