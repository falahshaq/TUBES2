"""Smart Shuttle ITB Jatinangor - versi web (Flask).

Jalankan di laptop:   python api/index.py   lalu buka http://127.0.0.1:5000
Di Vercel file ini otomatis dipakai sebagai serverless function.

Sama seperti main.py, file ini hanya mengurus tampilan.
Semua perhitungan memanggil fungsi yang sama dari folder core/.
"""

import copy
import json
import os
import sys

FOLDER_PROYEK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, FOLDER_PROYEK)

from flask import Flask, Response, redirect, render_template, request, url_for  # noqa: E402

from core.adopsi import simulasi_adopsi  # noqa: E402
from core.data import buat_jadwal, daftar_nama_halte, durasi_putaran, validasi_data  # noqa: E402
from core.laporan import buat_teks_laporan, ringkasan  # noqa: E402
from core.optimasi import optimasi_jadwal  # noqa: E402
from core.penumpang import cari_bus_berikutnya, estimasi_perjalanan  # noqa: E402
from core.penyimpanan import bisa_disimpan, jenis_penyimpanan, muat_data, reset_data, simpan_data  # noqa: E402
from core.simulasi import simulasi_sehari  # noqa: E402
from core.waktu import format_durasi, ke_jam, ke_menit, menit_sekarang  # noqa: E402

app = Flask(__name__, template_folder=os.path.join(FOLDER_PROYEK, "templates"))
app.jinja_env.filters["jam"] = ke_jam
app.jinja_env.filters["durasi"] = format_durasi


# ====================== Fungsi bantu ======================

def ambil_int(nama, bawaan, minimum=None, maksimum=None):
    """Membaca angka bulat dari query/form, dengan batas aman."""
    try:
        nilai = int(request.values.get(nama, bawaan))
    except (TypeError, ValueError):
        nilai = bawaan
    if minimum is not None and nilai < minimum:
        nilai = minimum
    if maksimum is not None and nilai > maksimum:
        nilai = maksimum
    return nilai


def ambil_float(nama, bawaan, minimum=None, maksimum=None):
    try:
        nilai = float(str(request.values.get(nama, bawaan)).replace(",", "."))
    except (TypeError, ValueError):
        nilai = bawaan
    if minimum is not None and nilai < minimum:
        nilai = minimum
    if maksimum is not None and nilai > maksimum:
        nilai = maksimum
    return nilai


def ambil_jam(nama, bawaan):
    teks = request.values.get(nama, "").strip()
    if not teks:
        return bawaan
    try:
        return ke_menit(teks)
    except ValueError:
        return bawaan


def status_edit():
    """Apakah data boleh diedit dari web, dan apakah perlu kata sandi."""
    sandi = os.environ.get("ADMIN_PASSWORD", "")
    di_vercel = bool(os.environ.get("VERCEL"))
    return {
        "perlu_sandi": bool(sandi),
        # Di Vercel tanpa kata sandi, edit dimatikan supaya data tidak diubah sembarang orang.
        "dikunci": di_vercel and not sandi,
        "bisa_simpan": bisa_disimpan(),
        "penyimpanan": jenis_penyimpanan(),
    }


def sandi_benar():
    sandi = os.environ.get("ADMIN_PASSWORD", "")
    if not sandi:
        return not os.environ.get("VERCEL")
    return request.form.get("sandi", "") == sandi


@app.context_processor
def variabel_umum():
    return {"menu_aktif": request.endpoint}


# ====================== Halaman penumpang ======================

@app.route("/")
def beranda():
    data = muat_data()
    sekarang = menit_sekarang()
    papan = []
    for i, nama in enumerate(daftar_nama_halte(data)):
        pertama = cari_bus_berikutnya(data, i, 0, 1)
        papan.append({"indeks": i, "nama": nama, "bus": cari_bus_berikutnya(data, i, sekarang, 2),
                      "pertama": pertama[0]["waktu"] if pertama else None})
    return render_template("beranda.html", data=data, sekarang=sekarang, papan=papan,
                           halte=daftar_nama_halte(data))


@app.route("/rute")
def rute():
    data = muat_data()
    halte = daftar_nama_halte(data)
    sekarang = menit_sekarang()
    asal = ambil_int("asal", 0, 0, len(halte) - 1)
    tujuan = ambil_int("tujuan", 1 if len(halte) > 1 else 0, 0, len(halte) - 1)
    jam = ambil_jam("jam", sekarang)
    hasil = None
    pesan = None
    if "asal" in request.args:
        if asal == tujuan:
            pesan = "Halte asal dan tujuan sama, tidak perlu naik shuttle."
        else:
            hasil = estimasi_perjalanan(data, asal, tujuan, jam)
            if hasil is None:
                pesan = f"Tidak ada bus lagi setelah pukul {ke_jam(jam)}. Shuttle beroperasi {data['jam_operasi']['mulai']} - {data['jam_operasi']['selesai']}."
    return render_template("rute.html", data=data, halte=halte, asal=asal, tujuan=tujuan,
                           jam=jam, hasil=hasil, pesan=pesan)


@app.route("/jadwal")
def jadwal():
    data = muat_data()
    return render_template("jadwal.html", data=data, halte=daftar_nama_halte(data),
                           jadwal=buat_jadwal(data), sekarang=menit_sekarang(),
                           putaran=durasi_putaran(data))


# ====================== Halaman pengelola ======================

def ambil_skenario(data):
    return {
        "interval": ambil_int("interval", data["interval_menit"], 1, 240),
        "jumlah_bus": ambil_int("bus", data["armada"]["jumlah_bus"], 1, 30),
        "pengali": ambil_float("pengali", 1.0, 0.1, 5.0),
        "seed": ambil_int("seed", 42, 0, 999999),
    }


@app.route("/simulasi")
def simulasi():
    data = muat_data()
    s = ambil_skenario(data)
    hasil = simulasi_sehari(data, s["interval"], s["jumlah_bus"], s["pengali"], s["seed"])
    if request.args.get("format") == "txt":
        return Response(buat_teks_laporan(data, hasil), mimetype="text/plain; charset=utf-8",
                        headers={"Content-Disposition": "attachment; filename=laporan_simulasi.txt"})
    maks_jam = max([j["datang"] for j in hasil["per_jam"]] + [1])
    maks_antrean = max([g["antrean"] for g in hasil["grafik_antrean"]] + [1])
    return render_template("simulasi.html", data=data, s=s, hasil=hasil, analisis=ringkasan(hasil),
                           maks_jam=maks_jam, maks_antrean=maks_antrean)


@app.route("/optimasi")
def optimasi():
    data = muat_data()
    pengaturan = copy.deepcopy(data["optimasi"])
    pengaturan["interval_min"] = ambil_int("imin", pengaturan["interval_min"], 1, 120)
    pengaturan["interval_max"] = ambil_int("imax", pengaturan["interval_max"], pengaturan["interval_min"], 120)
    pengaturan["interval_langkah"] = ambil_int("ilangkah", pengaturan["interval_langkah"], 1, 60)
    pengaturan["bus_min"] = ambil_int("bmin", pengaturan["bus_min"], 1, 20)
    pengaturan["bus_max"] = ambil_int("bmax", pengaturan["bus_max"], pengaturan["bus_min"], 20)
    pengaturan["bobot_tunggu"] = ambil_float("wtunggu", pengaturan["bobot_tunggu"], 0, 100)
    pengaturan["bobot_tertinggal"] = ambil_float("wtinggal", pengaturan["bobot_tertinggal"], 0, 100)
    pengaturan["biaya_per_bus"] = ambil_float("wbus", pengaturan["biaya_per_bus"], 0, 100)
    pengali = ambil_float("pengali", 1.0, 0.1, 5.0)

    # Batasi jumlah kombinasi supaya tidak melebihi batas waktu di Vercel.
    jumlah = ((pengaturan["interval_max"] - pengaturan["interval_min"]) // pengaturan["interval_langkah"] + 1) \
        * (pengaturan["bus_max"] - pengaturan["bus_min"] + 1)
    pesan = None
    if jumlah > 200:
        pesan = f"Terlalu banyak kombinasi ({jumlah}). Maksimal 200, perbesar langkah interval atau persempit rentang."
        hasil = None
    else:
        hasil = optimasi_jadwal(data, ambil_int("seed", 42, 0, 999999), pengali, pengaturan)
    return render_template("optimasi.html", data=data, p=pengaturan, pengali=pengali, hasil=hasil,
                           pesan=pesan, edit=status_edit())


@app.route("/optimasi/terapkan", methods=["POST"])
def terapkan_optimasi():
    data = muat_data()
    if not sandi_benar():
        return redirect(url_for("optimasi", pesan="sandi"))
    data["interval_menit"] = ambil_int("interval", data["interval_menit"], 1, 240)
    data["armada"]["jumlah_bus"] = ambil_int("bus", data["armada"]["jumlah_bus"], 1, 30)
    try:
        simpan_data(data)
    except Exception as e:  # noqa: BLE001
        return render_template("pesan.html", judul="Gagal menyimpan", isi=str(e))
    return redirect(url_for("data_page", ok="Jadwal terbaik sudah dipakai."))


@app.route("/adopsi")
def adopsi():
    data = muat_data()
    s = ambil_skenario(data)
    info = request.args.get("info", "1") == "1"
    hasil = simulasi_adopsi(data, s["interval"], s["jumlah_bus"], info, s["seed"])
    return render_template("adopsi.html", data=data, s=s, info=info, hasil=hasil)


# ====================== Kelola data ======================

def jam_operasi_list(data):
    mulai = ke_menit(data["jam_operasi"]["mulai"]) // 60
    selesai = ke_menit(data["jam_operasi"]["selesai"]) // 60
    return list(range(mulai, selesai + 1))


def data_dari_form(lama):
    """Menyusun data baru dari isi form halaman Kelola Data."""
    f = request.form
    data = copy.deepcopy(lama)
    data["nama_layanan"] = f.get("nama_layanan", lama["nama_layanan"]).strip() or lama["nama_layanan"]
    data["catatan"] = f.get("catatan", "").strip()
    data["jam_operasi"] = {"mulai": f.get("mulai", "").strip(), "selesai": f.get("selesai", "").strip()}
    data["interval_menit"] = ambil_int("interval_menit", lama["interval_menit"])
    data["waktu_henti"] = ambil_int("waktu_henti", lama["waktu_henti"])
    data["armada"] = {"jumlah_bus": ambil_int("jumlah_bus", lama["armada"]["jumlah_bus"]),
                      "kapasitas": ambil_int("kapasitas", lama["armada"]["kapasitas"])}

    # Halte: baris lama (punya indeks asal) + baris kosong untuk halte baru.
    halte_baru = []
    tempuh_baru = []
    asal_kolom = []
    jumlah_baris = ambil_int("jumlah_baris", 0, 0, 100)
    for i in range(jumlah_baris):
        nama = f.get(f"halte_nama_{i}", "").strip()
        if not nama or f.get(f"halte_hapus_{i}"):
            continue
        halte_baru.append({"nama": nama})
        tempuh_baru.append(ambil_int(f"halte_tempuh_{i}", 0))
        asal = f.get(f"halte_asal_{i}", "")
        asal_kolom.append(int(asal) if asal.isdigit() else None)
    data["halte"] = halte_baru
    data["waktu_tempuh"] = tempuh_baru

    # Permintaan per jam: ambil dari form, kolom mengikuti halte lama.
    permintaan = {}
    try:
        daftar_jam = jam_operasi_list(data)
    except (ValueError, KeyError):
        daftar_jam = jam_operasi_list(lama)
    for jam in daftar_jam:
        baris = []
        for asal in asal_kolom:
            if asal is None:
                baris.append(0)
            else:
                baris.append(ambil_int(f"minta_{jam}_{asal}", 0, 0))
        permintaan[str(jam)] = baris
    data["permintaan"] = permintaan

    data["optimasi"] = {
        "interval_min": ambil_int("o_imin", 5, 1), "interval_max": ambil_int("o_imax", 30, 1),
        "interval_langkah": ambil_int("o_ilangkah", 5, 1),
        "bus_min": ambil_int("o_bmin", 1, 1), "bus_max": ambil_int("o_bmax", 6, 1),
        "bobot_tunggu": ambil_float("o_wtunggu", 1.0, 0), "bobot_tertinggal": ambil_float("o_wtinggal", 0.5, 0),
        "biaya_per_bus": ambil_float("o_wbus", 2.0, 0),
    }
    data["adopsi"] = {
        "responden": ambil_int("a_responden", 52, 0),
        "persen_pengguna": ambil_float("a_pengguna", 51.9, 0.1, 100),
        "persen_alasan_info": ambil_float("a_info", 60.7, 0, 100),
        "persen_alasan_tunggu": ambil_float("a_tunggu", 42.9, 0, 100),
        "peluang_beralih": ambil_float("a_peluang", 50, 0, 100),
        "putaran": ambil_int("a_putaran", 6, 1, 20),
    }
    return data


@app.route("/data", methods=["GET", "POST"])
def data_page():
    data = muat_data()
    edit = status_edit()
    salah = []
    ok = request.args.get("ok")
    if request.method == "POST":
        if edit["dikunci"]:
            salah = ["Edit dimatikan. Atur ADMIN_PASSWORD di pengaturan Vercel dulu."]
        elif not sandi_benar():
            salah = ["Kata sandi salah."]
        else:
            aksi = request.form.get("aksi")
            try:
                if aksi == "reset":
                    data, ok = reset_data()
                else:
                    if aksi == "json":
                        baru = json.loads(request.form.get("json", ""))
                    else:
                        baru = data_dari_form(data)
                    salah = validasi_data(baru)
                    if salah:
                        data = baru
                    else:
                        ok = simpan_data(baru)
                        data = baru
            except json.JSONDecodeError as e:
                salah = [f"JSON tidak valid: {e}"]
            except Exception as e:  # noqa: BLE001
                salah = [str(e)]
    try:
        daftar_jam = jam_operasi_list(data)
    except (ValueError, KeyError):
        daftar_jam = []
    return render_template("data.html", data=data, edit=edit, salah=salah, ok=ok, daftar_jam=daftar_jam,
                           teks_json=json.dumps(data, indent=2, ensure_ascii=False))


@app.route("/tentang")
def tentang():
    return render_template("tentang.html", data=muat_data())


@app.errorhandler(404)
def tidak_ditemukan(e):
    return render_template("pesan.html", data=muat_data(), judul="Halaman tidak ditemukan",
                           isi="Alamat yang dibuka tidak ada."), 404


class PerbaikiPathVercel:
    """Di Vercel semua alamat diarahkan ke /api/index?__p=<alamat asli> (lihat vercel.json).
    Middleware ini mengembalikan alamat asli supaya route Flask bekerja normal."""

    def __init__(self, aplikasi):
        self.aplikasi = aplikasi

    def __call__(self, environ, start_response):
        from urllib.parse import parse_qsl, urlencode
        pasangan = parse_qsl(environ.get("QUERY_STRING", ""), keep_blank_values=True)
        sisa = []
        path_asli = None
        for k, v in pasangan:
            if k == "__p":
                path_asli = v
            else:
                sisa.append((k, v))
        if path_asli is not None:
            environ["PATH_INFO"] = "/" + path_asli.lstrip("/")
            environ["QUERY_STRING"] = urlencode(sisa)
        return self.aplikasi(environ, start_response)


app.wsgi_app = PerbaikiPathVercel(app.wsgi_app)


if __name__ == "__main__":
    app.run(debug=True)
