# -*- coding: utf-8 -*-
"""Pembangkit `results.json` untuk tab "🧪 Perjalanan Riset" (app v5;
v5.1 menambah `kategori_heatmap` — per-kategori full-stack Tahap 2C
dan 2D dari file evaluasi yang sama, untuk heatmap Altair).

Sumber angka (file evaluasi terverifikasi di ../id-train/):
  - Tahap 1  : eval_smoke_current.json  (paket app live: model CHOSEN +
               rules Tahap 1, dinilai full-stack pada set hakim 300)
  - Tahap 2C : eval_tahap2c.json        (paket fine-tune dwibahasa)
  - Tahap 2D : eval_tahap2d.json        (paket loop perbaikan 2D, epoch-1)

Tahap 0 (baseline) TIDAK punya file evaluasi JSON — angkanya di-hardcode
di bawah dengan sumber: tabel "Perbandingan vs baseline" pada
id-train/tahap2c_results.md (kolom "Tahap 0 awal") yang identik dengan
tabel perbandingan di id-train/tahap2d_results.md (kolom "Tahap 0"):
SAH 16,0% · SMISHING 87,3% · Total 51,7% · AUTO-CLOSE 0 · UCI 0,986 ·
Panel 1/8 · 8/8.

Narasi per tahap didistilasi setia dari tahap2c_results.md,
tahap2d_results.md, dan README_TAHAP2D.md §1/§7. Vonis ditulis apa
adanya — termasuk dua paket yang DITOLAK.

v5.4.0: Tahap 2A (korpus) & 2B (fine-tune) kini berdiri sendiri di
kunci `persiapan` — keduanya tahap persiapan TANPA skor gerbang
(gerbang hanya menilai paket model utuh), didistilasi dari
README_TAHAP2.md + corpus_stats.json + training_log.json. Semua tahap
juga membawa `perlakuan` / `model` / `data` (apa yang diubah, paket
modelnya, dataset + sumbernya). Desain aditif disengaja: kode
journey.py lama mengabaikan kunci baru sehingga app live tidak rusak
sebelum reboot memuat journey.py baru.

Jalankan:  python gen_results.py   (menulis results.json di folder ini)
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ID_TRAIN = os.path.join(HERE, "..", "id-train")
OUT = os.path.join(HERE, "results.json")

GERBANG = {"sah": 85, "smishing": 95, "uci_pr_auc": 0.98, "auto_close": 0}


def _load(name):
    with open(os.path.join(ID_TRAIN, name), encoding="utf-8") as f:
        return json.load(f)


def _metrik(ev):
    """Ekstrak metrik full-stack (lolos_final) dari satu file evaluasi."""
    lab = ev["id300"]["per_label"]
    panel = ev["panel16"]["per_label"]
    return {
        "sah": round(lab["sah"]["lolos_final"] * 100, 1),
        "smishing": round(lab["smishing"]["lolos_final"] * 100, 1),
        "total": round(ev["id300"]["total"]["lolos_final"] * 100, 1),
        "auto_close": int(lab["smishing"]["auto_close_final"]),
        "uci_pr_auc": round(ev["uci_test_pr_auc"], 4),
        "panel_sah": round(panel["SAH"]["lolos_final"] * 100, 1),
        "panel_smishing": round(panel["SMISHING"]["lolos_final"] * 100, 1),
    }


# ---------------------------------------------------------------------------
# Tahap 0 — BASELINE (hardcode; sumber: tabel perbandingan
# tahap2c_results.md "Perbandingan vs baseline", kolom "Tahap 0 awal",
# terkonfirmasi identik di tahap2d_results.md kolom "Tahap 0").
# Panel 1/8 = 12,5% dan 8/8 = 100%.
# ---------------------------------------------------------------------------
TAHAP_0 = {
    "id": "0",
    "nama": "Baseline & diagnosis",
    "tanggal": "2026-10-22",
    "sah": 16.0,
    "smishing": 87.3,
    "total": 51.7,
    "auto_close": 0,
    "uci_pr_auc": 0.986,
    "panel_sah": 12.5,
    "panel_smishing": 100.0,
    "vonis": "BASELINE — titik berangkat; penyakit terdiagnosis, "
             "bukan kandidat pengganti model",
    "warna_vonis": "netral",
    "hipotesis": (
        "Model CHOSEN (ensemble Top-3 terkalibrasi yang dilatih pada SMS "
        "Inggris UCI ±2011) cukup baik untuk triase SMS Indonesia, karena "
        "pola smishing dianggap bersifat lintas bahasa."),
    "metode": (
        "Dibangun set hakim Indonesia: 300 pesan berlabel (150 SAH / 150 "
        "SMISHING, 20 kategori) yang tidak pernah dipakai melatih model. "
        "Model live dinilai apa adanya pada set itu. Gerbang klaim "
        "ditetapkan di muka: SAH ≥ 85%, SMISHING ≥ 95%, PR-AUC UCI ≥ 0,98, "
        "smishing AUTO-CLOSE = 0."),
    "hasil": (
        "SAH hanya 16,0% — 84% pesan sah Indonesia dieskalasi; median skor "
        "SAH (0,471) bahkan lebih tinggi dari SMISHING (0,402). SMISHING "
        "87,3%, total 51,7%, smishing AUTO-CLOSE 0, dan PR-AUC Inggris "
        "tetap 0,986."),
    "pelajaran": (
        "Penyakitnya bukan model yang lemah, melainkan register: pesan "
        "resmi formal-institusional Indonesia tidak pernah ada di data "
        "latih Inggris, sehingga pesan yang 'terdengar resmi' terbaca "
        "sebagai mencurigakan. Perbaikan harus menyentuh data dan "
        "representasi bahasa Indonesia — bukan sekadar menggeser ambang."),
    "perlakuan": (
        "Tidak ada perlakuan — model live dinilai apa adanya sebagai "
        "titik berangkat (baseline)."),
    "model": (
        "Ensemble Top-3 Terkalibrasi CHOSEN: DistilBERT multilingual "
        "fine-tune UCI + TF-IDF/Fitur Angka/Logistic Regression + "
        "TF-IDF/Logistic Regression; ambang live t_close 0,010 · "
        "t_esc 0,135."),
    "data": (
        "Data latih model: UCI SMS Spam Collection (SMS Inggris "
        "±2011). Data nilai: set hakim Indonesia 300 pesan (150 SAH / "
        "150 SMISHING, 20 kategori) yang tidak pernah dipakai melatih "
        "model mana pun."),
}

NARASI = {
    "1": {
        "nama": "Sinyal penenang (aturan)",
        "tanggal": "2026-10-22",
        "vonis": "DITERIMA — app v4 (tambal terukur, bukan obat)",
        "warna_vonis": "kuning",
        "hipotesis": (
            "Sebagian pesan sah yang dieskalasi punya pola resmi yang "
            "sangat khas. Aturan penenang yang sangat terbatas — turun "
            "tepat satu tingkat, tidak pernah menutup otomatis, dan gugur "
            "bila ada sinyal kuat — bisa menyelamatkan sebagian pesan sah "
            "tanpa menyentuh satu pun smishing."),
        "metode": (
            "Lapisan rules.py diberi arah sebaliknya (sinyal penenang): "
            "untuk pola resmi berformat sangat jelas — OTP standar tanpa "
            "tautan, tautan hanya ke domain resmi persis, notifikasi "
            "transaksi terstruktur tanpa tautan — band ESKALASI model "
            "boleh turun tepat satu tingkat ke REVIEW ANALIS. Penenang "
            "tidak pernah mengubah skor dan gugur total bila sinyal kuat "
            "S2/S3 aktif. Paket app (model lama + rules baru) dinilai "
            "ulang full-stack pada set hakim 300 yang sama."),
        "hasil": (
            "SAH 16,0% → 36,0%, SMISHING tetap 87,3%, smishing AUTO-CLOSE "
            "tetap 0 — lapisan aturan 0× salah tembak ke smishing. Total "
            "naik ke 61,7% dan panel sah 1/8 → 3/8."),
        "pelajaran": (
            "Tambal aturan bekerja dan terbukti aman, tetapi plafonnya "
            "rendah: 36,0% masih jauh dari gerbang SAH 85%. Ini tambal "
            "terukur, bukan obat — perbaikan sejatinya adalah fine-tune "
            "dwibahasa (Tahap 2)."),
        "perlakuan": (
            "Model TIDAK diubah sama sekali. Yang berubah hanya "
            "lapisan aturan: ditambah sinyal penenang satu arah "
            "(menurunkan band tepat satu tingkat, bersyarat ketat, "
            "gugur bila ada sinyal kuat)."),
        "model": (
            "Sama persis dengan Tahap 0 (ensemble CHOSEN) + rules.py "
            "dengan sinyal penenang (app v4)."),
        "data": (
            "Tidak ada data latih baru. Paket dinilai ulang pada set "
            "hakim 300 yang sama dengan Tahap 0."),
    },
    "2c": {
        "nama": "Perakitan & penilaian paket dwibahasa",
        "tanggal": "2026-10-22",
        "vonis": "DITOLAK — gagal tipis: SAH 84,0% (kurang 2 pesan), "
                 "SMISHING 94,7% (kurang 1 pesan), AUTO-CLOSE 3",
        "warna_vonis": "merah",
        "hipotesis": (
            "Fine-tune DistilBERT multilingual pada korpus dwibahasa "
            "(Inggris UCI + Indonesia) mengajarkan register resmi "
            "Indonesia, sehingga SAH naik drastis tanpa mengorbankan "
            "deteksi smishing maupun kemampuan Inggris."),
        "metode": (
            "Korpus latih Indonesia dibangun dari nol (2.512 baris) dan "
            "digabung UCI; split FIT 5.831 / KALIBRASI 816. DistilBERT "
            "multilingual di-fine-tune 2 epoch di Colab T4, anggota "
            "sklearn dilatih ulang, dan ambang diturunkan dari split "
            "kalibrasi (t_close 0,2930 · t_esc 0,3516). Paket dinilai "
            "full-stack pada set hakim 300 yang sama."),
        "hasil": (
            "Lompatan besar: SAH 36,0% → 84,0%, SMISHING 87,3% → 94,7%, "
            "total 89,3%, panel 7/8 · 8/8, PR-AUC UCI 0,9862 ✅. Tetapi 3 "
            "smishing masuk zona AUTO-CLOSE — satu-satunya regresi "
            "keamanan — karena t_close turunan kalibrasi (0,2930) jauh "
            "lebih longgar daripada t_close app lama (0,010)."),
        "pelajaran": (
            "Gagal tipis di 3 dari 4 gerbang: SAH kurang 2 pesan, "
            "SMISHING kurang 1 pesan, ditambah regresi AUTO-CLOSE. "
            "Penyakit register sebagian besar sembuh; masalah berpindah "
            "ke titik operasi (kriteria derivasi t_close) dan tiga "
            "kategori terlemah: keamanan_bank_resmi 60,0%, "
            "telco_tagihan_pulsa 66,7%, apk_malware 73,3%. Perbaikan "
            "berikutnya harus memperbaiki data + kriteria derivasi — "
            "bukan melonggarkan gerbang."),
        "perlakuan": (
            "Merakit hasil 2A + 2B menjadi paket kandidat utuh: BERT "
            "fine-tune + anggota sklearn dilatih ulang + ambang "
            "diturunkan ulang dari split kalibrasi, lalu paket dinilai "
            "gerbang full-stack."),
        "model": (
            "Ensemble dwibahasa BARU (bukan model live): DistilBERT "
            "fine-tune 2B (temperatur kalibrasi 2,0129) + 2 anggota "
            "sklearn yang dilatih ulang pada data dwibahasa."),
        "data": (
            "Data latih sama dengan 2B (UCI + korpus 2A; FIT 5.831 / "
            "KALIBRASI 816). Ambang dari split kalibrasi: t_close "
            "0,2930 · t_esc 0,3516. Data nilai: set hakim 300 yang sama."),
    },
    "2d": {
        "nama": "Loop perbaikan 2D",
        "tanggal": "2026-10-23",
        "vonis": "DITOLAK — 2/4 gerbang; SAH sembuh 92,7% tetapi "
                 "SMISHING mundur 88,7% dan AUTO-CLOSE 2; model app "
                 "tidak ditukar",
        "warna_vonis": "merah",
        "hipotesis": (
            "Menambah data latih tepat pada tiga kategori terlemah 2C — "
            "dipilih dari pola kategori, ditulis dari nol, bukan menyalin "
            "set hakim — plus memperketat kriteria derivasi t_close "
            "menjadi toleransi-nol akan menutup ketiga gerbang yang gagal "
            "tanpa merusak gerbang yang sudah lolos."),
        "metode": (
            "980 baris baru dari 7 keluarga templat (FIT +600; 380 baris "
            "dari 3 keluarga ditahan utuh untuk kalibrasi); gerbang "
            "kemiripan terukur: Jaccard maksimum yang lolos vs set hakim "
            "0,50 (< 0,80). Derivasi ambang diganti ke toleransi-nol "
            "(max_missed_frac = 0,0). Checkpoint epoch-1 disimpan dan "
            "pemilihan epoch mengikuti aturan yang ditetapkan di muka — "
            "PR-AUC kalibrasi mentah tertinggi menang: epoch-1 0,9673 "
            "mengalahkan epoch-2 0,9288. Split baru FIT 6.431 / KALIBRASI "
            "1.196; hanya kandidat menang yang dievaluasi ke gerbang."),
        "hasil": (
            "SAH 92,7% ✅ — kategori target sembuh: keamanan_bank_resmi "
            "60,0% → 93,3% dan apk_malware 73,3% → 100%. PR-AUC UCI "
            "0,9882 ✅, tertinggi sejauh ini; panel 16 sempurna 16/16 "
            "untuk pertama kalinya; total 90,7%. Tetapi SMISHING mundur "
            "94,7% → 88,7% (kurang 9 pesan) dan smishing AUTO-CLOSE "
            "masih 2."),
        "pelajaran": (
            "Loop ini berhasil pada sasaran yang ditargetkan tetapi "
            "menukar masalah: 300 baris SAH formal baru menekan skor "
            "smishing non-target (model-saja 94,7% → 88,0%) dan t_esc "
            "naik 0,3516 → 0,4092 sehingga 15 smishing berhenti di REVIEW "
            "alih-alih ESKALASI. Kriteria toleransi-nol terpenuhi di "
            "kalibrasi, tetapi 2 smishing set hakim tetap lolos ke bawah "
            "t_close — celah generalisasi, karena 52% kalibrasi adalah "
            "keluarga templat penahan. Harga lainnya: pesan SAH yang "
            "berhenti di REVIEW naik 23 → 47, beban analis naik. Tidak "
            "ada satu pun angka yang digeser sesudah melihat set hakim."),
        "perlakuan": (
            "Satu loop perbaikan terukur dari 2C: data baru tepat pada "
            "kategori terlemah + kriteria derivasi t_close diganti "
            "toleransi-nol + aturan pemilihan epoch ditetapkan di muka. "
            "Arsitektur model tidak berubah."),
        "model": (
            "Arsitektur sama dengan paket 2C, dilatih ulang dari awal; "
            "checkpoint epoch-1 yang menang (PR-AUC kalibrasi mentah "
            "0,9673 vs epoch-2 0,9288). Ambang hasil derivasi baru: "
            "t_close 0,1422 · t_esc 0,4092."),
        "data": (
            "Korpus 2A ditambah 980 baris baru dari 7 keluarga templat "
            "(FIT +600; 380 baris dari 3 keluarga ditahan utuh untuk "
            "kalibrasi). Split baru FIT 6.431 / KALIBRASI 1.196. "
            "Gerbang kemiripan vs set hakim: Jaccard maksimum yang "
            "lolos 0,50. Data nilai: set hakim 300 yang sama."),
    },
}

# ---------------------------------------------------------------------------
# Tahap 2A & 2B — tahap PERSIAPAN (data & fine-tune). Keduanya tidak
# dinilai gerbang klaim: gerbang hanya menilai paket model utuh (2C).
# Sumber: README_TAHAP2.md, corpus_stats.json, training_log.json.
# ---------------------------------------------------------------------------
TAHAP_2A = {
    "id": "2a",
    "nama": "Korpus latih Indonesia",
    "tanggal": "2026-10-22",
    "vonis": "SELESAI — korpus 2.512 baris lolos gerbang anti-bocor; "
             "tahap data, bukan paket model",
    "warna_vonis": "netral",
    "hipotesis": (
        "Register resmi Indonesia bisa diajarkan lewat korpus campuran: "
        "sisa dataset publik Indonesia + keluarga templat baru yang "
        "ditulis menargetkan wilayah lemah Tahap 1 — asalkan korpus "
        "terbukti terpisah dari set hakim."),
    "metode": (
        "Korpus dibangun dari dua sumber lalu disaring gerbang "
        "anti-bocor 3 lapis terhadap set hakim: teks persis sama "
        "dibuang, kerangka sama (digit & domain ditopeng) dibuang, "
        "Jaccard token ≥ 0,80 dibuang. Semua nomor & domain disamarkan "
        "ke fiktif. Label publik dipetakan: penipuan → 1, promo → 1, "
        "normal → 0."),
    "hasil": (
        "2.512 baris lolos semua gerbang: 1.096 baris publik (dari "
        "1.143; dibuang 15 persis + 11 kerangka + 20 Jaccard + 1 "
        "duplikat) + 1.416 baris templat. Komposisi hampir seimbang: "
        "1.255 positif / 1.257 negatif, 0 duplikat, QA baca acak "
        "30/30 wajar. Jaccard maksimum yang lolos vs set hakim 0,793 "
        "(baris publik) dan 0,55 (baris templat)."),
    "pelajaran": (
        "Dataset SMS Indonesia yang publik & tersisa memang sangat "
        "kecil dan tua — sebagian besar korpus harus dibuat sendiri. "
        "Korpus templat membawa risiko artefak yang harus diingat "
        "saat membaca hasil 2C/2D: 1.258 pasangan sekeluarga hanya "
        "berbeda digit/domain tertopeng (Jaccard tertopeng 1,0)."),
    "perlakuan": (
        "Membangun DATA latih Indonesia dari nol — belum ada model "
        "baru di tahap ini. Perlakuan murni di sisi data: kumpulkan, "
        "pulihkan label, buat keluarga templat baru, saring, samarkan."),
    "model": (
        "— (tahap data; model belum dilatih)"),
    "data": (
        "2.512 baris = 1.096 publik: Kaggle gevabriel/indonesian-sms-"
        "spam (CC0; keturunan korpus GitHub agtbaskara, SMS Indonesia "
        "±2012–2016), label 3-kelasnya dipulihkan lewat Kaggle "
        "crystalbaby (Apache 2.0) + 1.416 baris generate: 25 keluarga "
        "templat (12 sah / 13 smishing) dengan institusi & domain "
        "fiktif yang berbeda dari set evaluasi."),
}

TAHAP_2B = {
    "id": "2b",
    "nama": "Fine-tune DistilBERT dwibahasa",
    "tanggal": "2026-10-22",
    "vonis": "SELESAI — fine-tune tereksekusi; overfit epoch 2 "
             "terdeteksi di kalibrasi; belum berupa paket",
    "warna_vonis": "kuning",
    "hipotesis": (
        "DistilBERT multilingual yang di-fine-tune pada campuran UCI "
        "+ korpus 2A akan belajar register Indonesia tanpa melupakan "
        "Inggris."),
    "metode": (
        "Fine-tune di Colab GPU T4 (VM proyek punya riwayat OOM): "
        "base distilbert-base-multilingual-cased, max_len 64, batch "
        "16, 2 epoch, AdamW lr 5e-5, seed 42, loop manual. Sesudah "
        "latih, temperatur kalibrasi BERT diturunkan dari split "
        "kalibrasi."),
    "hasil": (
        "Fine-tune selesai dalam ±90 detik/epoch. PR-AUC kalibrasi "
        "mentah: epoch 1 = 0,9746, epoch 2 = 0,9115 — epoch 2 OVERFIT "
        "(loss turun 0,109 → 0,041 tetapi PR-AUC kalibrasi jatuh). "
        "Temperatur kalibrasi BERT: 2,0129."),
    "pelajaran": (
        "Sinyal overfit sudah muncul di epoch 2 — pelajaran ini yang "
        "kemudian membuat 2D menetapkan aturan pemilihan epoch di "
        "muka. Dan fine-tune mentah belum bisa dinilai gerbang: ia "
        "harus dirakit menjadi ensemble + dikalibrasi dulu (Tahap "
        "2C)."),
    "perlakuan": (
        "Melatih MODEL bahasa dwibahasa di GPU — perlakuan murni di "
        "sisi model. Ambang, ensemble, dan penilaian gerbang belum "
        "terjadi di tahap ini."),
    "model": (
        "distilbert/distilbert-base-multilingual-cased, fine-tune "
        "klasifikasi biner (sah vs spam/smishing), 2 epoch."),
    "data": (
        "FIT 5.831 baris (UCI 3.722 + gevabriel 931 + templat 1.178) "
        "/ KALIBRASI 816 baris (UCI 413 + gevabriel 165 + templat "
        "238) — korpus 2A digabung data latih UCI."),
}

PERSIAPAN = [TAHAP_2A, TAHAP_2B]

SUMBER = {
    "1": "eval_smoke_current.json",
    "2c": "eval_tahap2c.json",
    "2d": "eval_tahap2d.json",
}


def _per_kategori(ev, tahap_label):
    """Baris heatmap kategori untuk satu tahap (full-stack, lolos_final).

    Urutan mengikuti urutan kategori di file evaluasi (SAH dulu, lalu
    SMISHING) supaya heatmap mengelompok secara alami.
    """
    rows = []
    for kat, v in ev["id300"]["per_kategori"].items():
        grup, _, nama = kat.partition("/")
        rows.append({
            "kategori": kat,
            "grup": grup.upper(),
            # Label PENDEK untuk sumbu heatmap (v5.2.2): tanpa prefiks
            # grup (grup jadi panel facet sendiri) dan underscore ->
            # spasi, supaya tidak terpotong di layar sempit.
            "label": nama.replace("_", " "),
            "tahap": tahap_label,
            "lolos": round(v["lolos_final"] * 100, 1),
        })
    return rows


def main():
    stages = [TAHAP_0]
    evs = {}
    for sid in ("1", "2c", "2d"):
        evs[sid] = _load(SUMBER[sid])
        m = _metrik(evs[sid])
        stages.append({"id": sid, **m, **NARASI[sid]})

    # Heatmap kategori: hanya 2C vs 2D yang punya per-kategori lengkap
    # dan memang itu perbandingan yang bercerita (target sembuh vs regresi).
    heatmap = (_per_kategori(evs["2c"], "Tahap 2C")
               + _per_kategori(evs["2d"], "Tahap 2D"))

    data = {"gates": GERBANG, "stages": stages, "persiapan": PERSIAPAN,
            "kategori_heatmap": heatmap}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    print(f"results.json ditulis: {OUT}")
    print(f"{'Tahap':<6}{'SAH':>7}{'SMISH':>8}{'Total':>8}"
          f"{'A-CLOSE':>9}{'PR-AUC':>9}  Vonis")
    for s in stages:
        print(f"{s['id']:<6}{s['sah']:>7.1f}{s['smishing']:>8.1f}"
              f"{s['total']:>8.1f}{s['auto_close']:>9}"
              f"{s['uci_pr_auc']:>9.4f}  {s['vonis'][:52]}")


if __name__ == "__main__":
    main()
