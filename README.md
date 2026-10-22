# 🛡️ Fraud Triage — Aplikasi Triase Smishing (Streamlit)

Aplikasi penyaji model terpilih proyek **Fraud Triage**: **Ensemble (Top-3
Terkalibrasi)** dengan kebijakan dua ambang operasional **t_close = 0,010**
dan **t_esc = 0,135** (Bagian 10 notebook `fraud-triage-laya-vs-ml-dl.ipynb`).

Pengguna menempel teks SMS → app menampilkan probabilitas scam terkalibrasi,
keputusan triase (Tutup Otomatis / Review Analis / Eskalasi), skor per
anggota ensemble, dan penjelasan faktor teks (kata pendorong + fitur angka).

---

## Isi folder

| Berkas | Fungsi |
|---|---|
| `app.py` | Antarmuka Streamlit (Bahasa Indonesia, istilah teknis English) |
| `triage_core.py` | Logika model murni (tanpa Streamlit): ensemble, kalibrasi temperatur, kebijakan dua ambang, penjelasan faktor |
| `build_artifacts.py` | Skrip pembangunan artefak deploy dari resep notebook + verifikasi angka (sudah dijalankan; jalankan ulang hanya bila resep berubah) |
| `requirements.txt` | Dependensi (torch diarahkan ke wheel CPU) |
| `model/ensemble_spec.json` | Spesifikasi ensemble: anggota, temperatur per anggota, ambang kebijakan |
| `model/sklearn_members.joblib` | Dua anggota sklearn yang dilatih ulang persis dari resep notebook (pipeline LR + komponen model fitur) |
| `model/model_operasional.pkl` | Salinan artefak resmi proyek — isinya **spesifikasi** ensemble (nama anggota + temperatur), sumber kebenaran `ensemble_spec.json` |
| `model/bert/` | *(belum ada — lihat langkah bobot BERT di bawah)* tempat bobot DistilBERT fine-tune bila memakai jalur Git LFS |

## Cara model dimuat (penting, jujur apa adanya)

Artefak resmi proyek `data/model_operasional.pkl` **bukan** model yang bisa
dijalankan — sesuai desain Bagian 13.5 notebook, isinya hanya spesifikasi
ensemble karena di notebook ensemble "disajikan" dari anggota yang hidup di
memori kernel. Karena itu artefak deploy dibangun begini:

1. **Dua anggota sklearn** (TF-IDF + LR dan TF-IDF + Fitur Angka + LR)
   dilatih ulang oleh `build_artifacts.py` dari data & split yang **persis
   sama** dengan notebook (UCI SMS Spam, dedup, stratified 60/20/20,
   seed 42, resep hyperparameter identik; remediasi Bagian 4.7 terbukti
   tidak mengubah LR — yang dituning GBM dan tidak membaik).
2. **Anggota DistilBERT** tidak dilatih ulang: bobot fine-tune-nya memang
   sudah tersimpan sejak notebook di `data/bert_snapshot` (dibekukan di
   gerbang memori Bagian 7). App memuatnya dari salah satu sumber ini
   (urutan di `triage_core.resolve_bert_source`): variabel lingkungan
   `BERT_MODEL_PATH` → folder `model/bert/` → `data/bert_snapshot` proyek
   (mode dev lokal) → `BERT_MODEL_ID` (repo Hugging Face).
3. **Verifikasi pembangunan**: PR-AUC hasil bangun ulang cocok dengan
   angka resmi notebook — LR val 0,968 · Fitur val 0,969 · BERT val 0,978 ·
   Ensemble val 0,982 · **Ensemble test 0,986**.

Skor akhir = rata-rata probabilitas terkalibrasi ketiga anggota
(temperatur: BERT 1,184 · Fitur 0,926 · LR 0,614; temperatur ensemble 1,0
by design), lalu dipetakan ke zona kebijakan.

## Menjalankan lokal

```bash
cd fraud-triage-laya/streamlit-app
../.venv/bin/streamlit run app.py
# tanpa konfigurasi apa pun, app otomatis memakai ../data/bert_snapshot
```

Uji inti tanpa UI:

```bash
../.venv/bin/python -c "
from triage_core import TriageEngine
e = TriageEngine()
print(e.triage('URGENT: your account will be blocked today, verify PIN at secure-login-verify.xyz')['p_scam'])
"
```

## Deploy ke Streamlit Community Cloud (dilakukan bersama Septian)

### Langkah 1 — Siapkan bobot DistilBERT (±517 MB) di salah satu tempat

GitHub menolak berkas > 100 MB tanpa LFS, jadi pilih **satu** jalur:

**Jalur A — Hugging Face Hub (disarankan).**
1. Login ke huggingface.co (akun Septian) → *New Model*, buat repo model
   **publik**, mis. `<username>/fraud-triage-distilbert` (bobot ini hasil
   fine-tune sendiri dari base publik di data publik — aman dipublikkan).
2. Upload seluruh isi folder proyek `data/bert_snapshot/`
   (`config.json`, `model.safetensors`, berkas tokenizer).
3. Nanti di Langkah 3, isi Streamlit *Secrets*:
   `BERT_MODEL_ID = "<username>/fraud-triage-distilbert"`.

**Jalur B — Git LFS.**
Salin isi `data/bert_snapshot/` ke `streamlit-app/model/bert/`, lalu
`git lfs track "*.safetensors"` sebelum push. Catatan: kuota LFS gratis
GitHub 1 GB storage / 1 GB bandwidth per bulan — setiap deploy Streamlit
menarik bobot ini, jadi jalur A lebih longgar.

### Langkah 2 — Buat repo GitHub & push folder ini

1. Buat repo GitHub baru (mis. `fraud-triage-app`) dari akun Septian.
2. Jadikan **folder `streamlit-app/` ini sebagai root repo** lalu push
   (`app.py`, `triage_core.py`, `requirements.txt`, `README.md`,
   folder `model/` — termasuk `model/bert/` hanya bila Jalur B).
   Belum ada apa pun yang di-push pada tahap persiapan ini.

### Langkah 3 — Buat app di Streamlit Community Cloud

1. Buka **share.streamlit.io** → *Sign in with GitHub* (akun Septian).
2. Klik **New app** → pilih repo `fraud-triage-app`, branch `main`,
   *Main file path*: `app.py`.
3. (Opsional, di *Advanced settings*) Python 3.12.
4. Bila Jalur A: di *Secrets* tambahkan
   `BERT_MODEL_ID = "<username>/fraud-triage-distilbert"`.
5. Klik **Deploy** dan tunggu build pertama selesai (tarik torch CPU +
   transformers; beberapa menit).

### Langkah 4 — Verifikasi pasca-deploy

Klik contoh **"🎁 Undian palsu (ID)"** → keputusan harus **ESKALASI**
(skor ±0,65); contoh **"💬 Pesan sah (EN)"** → skor sangat rendah (±0,01).
Bila app gagal memuat model, pesan error di app menyebut sumber bobot
yang dicari — cocokkan dengan jalur yang dipilih di Langkah 1.

### Catatan sumber daya

Tier gratis Streamlit Cloud memberi RAM ±1 GB. DistilBERT multilingual
fp32 memakai ±517 MB bobot; app ini sudah teruji memuat & memprediksi di
CPU. Bila suatu saat deploy kena batas RAM, opsi tindak lanjutnya adalah
memuat bobot dalam float16 (±260 MB) — minta Chief menyiapkan variannya,
jangan mengubah sendiri angka modelnya.

---

*Model ini artefak proyek pembelajaran terpimpin (data SMS Inggris ±2011);
bukan sistem produksi perbankan. Vonis lengkap metode — termasuk posisi
Laya sebagai kandidat lapisan teks, bukan model operasional — ada di
notebook proyek.*
