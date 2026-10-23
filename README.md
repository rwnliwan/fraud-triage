# 🛡️ Fraud Triage — Aplikasi Triase Smishing (Streamlit)

**Siskamling Digital** — layanan publik **lapor & cek smishing** untuk
warga Indonesia, ditenagai mesin riset **Fraud Triage**: ensemble model
terkalibrasi + lapisan aturan deterministik, dievaluasi dengan gerbang
yang dikunci di muka dan **hasilnya dipublikasikan apa adanya —
termasuk kegagalannya**.

**Demo live: [fraud-triage-demo.streamlit.app](https://fraud-triage-demo.streamlit.app/)**
· Model: [Hugging Face `rwnliwan/fraud-triage-smishing`](https://huggingface.co/rwnliwan/fraud-triage-smishing)
· Notebook proyek: `fraud-triage-laya-vs-ml-dl.ipynb` (arsip riset lengkap Tahap 0–2D)
· 📄 Dokumen proyek (edisi terbaru: Laporan v3.3 · Presentasi v3.4): [Laporan Lengkap Proyek (PDF)](docs/laporan-lengkap-proyek.pdf) · [Presentasi LinkedIn (PDF)](docs/presentasi-linkedin.pdf)
· 📖 Rincian teknis & riset: [docs/RINCIAN.md](docs/RINCIAN.md) · 🚀 Panduan deploy: [docs/DEPLOY.md](docs/DEPLOY.md)
· 👤 Penulis: [Septian Panjaya — LinkedIn](https://www.linkedin.com/in/septian-panjaya)

## 🏘️ Siskamling Digital — layanan publik (live)

Tab pertama yang menyambut pengunjung app:

- **📮 Lapor & Cek** — tempel pesan mencurigakan (atau unggah
  tangkapan layar, teks dibaca OCR lalu diedit warga dulu) → vonis
  bahasa awam (🔴 polanya sangat mirip penipuan / 🟡 mencurigakan /
  🟢 kemungkinan aman — label tegas hanya bila aturan keras
  terpicu) + **kartu langkah darurat sesuai keadaan**
  (belum klik → uang sudah terkirim; tautan resmi
  [IASC OJK](https://iasc.ojk.go.id), [cekrekening.id](https://cekrekening.id),
  [aduannomor.id](https://aduannomor.id)) + lapor agar warga lain
  terlindungi. Setiap laporan punya **nomor lacak** untuk memeriksa
  status pemeriksaannya. Teks dibersihkan otomatis dari data pribadi
  sebelum disimpan; pengirim hanya disimpan sebagai hash satu arah.
  Kebijakan privasi & retensi mengacu UU PDP dan tertulis terbuka
  di tab ini (gambar tangkapan layar hanya diproses di memori
  untuk OCR — tidak disimpan).
- **🖼️ Galeri Modus** — modus terverifikasi yang bisa disaring per
  kategori, untuk mengenali pola sebelum jadi korban.
- **🔐 Verifikasi** (admin, gerbang kata sandi) — label akhir selalu
  diputuskan **manusia**; model hanya menyaring & memberi saran.
  Panel analitik + progres korpus menuju retrain di tab yang sama.
- **Perlindungan layanan** — Cloudflare Turnstile **aktif permanen**
  (sejak 23 Okt 2026), batas laju per pengirim/harian, pemutus
  antrean, kill switch intake, deteksi duplikat, monitor lonjakan,
  dan anti-racun korpus (batas per teks sama, jejak audit label,
  tinjauan kedua buta → subset emas). Domain dalam laporan dicek
  umurnya via RDAP sebagai info pendukung — tidak pernah menentukan
  label.
- **Pembaruan v6.1 (Okt 2026)** — tindak lanjut kritik eksternal:
  vonis di tab Perjalanan Riset kini tiga status berbasis CI Wilson
  95% (*lolos jelas / tidak meyakinkan / gagal jelas*), dan loading
  app jauh lebih cepat (engine model dibangun malas — saat analisis
  pertama, bukan saat halaman dibuka).

Misi datanya: membangun **korpus smishing Bahasa Indonesia berlabel
manusia** — riset proyek ini menemukan belum ada korpus publik
semacam itu.

## 🎬 Demo

![Demo Fraud Triage](docs/demo.gif)

*Alur demo: contoh smishing → kartu ESKALASI + panel sinyal → Mode Batch
(antrean prioritas) → Perjalanan Riset (alur 6 tahap + heatmap kategori).*

| Analisis Tunggal | Mode Batch |
|---|---|
| ![Analisis Tunggal](docs/app-analisis-tunggal.png) | ![Mode Batch](docs/app-mode-batch.png) |

| Perjalanan Riset | Heatmap kategori 2C vs 2D |
|---|---|
| ![Perjalanan Riset](docs/app-perjalanan-riset.png) | ![Heatmap](docs/app-heatmap.png) |

## 📊 Hasil kunci — klaim 9/10 diuji, dan gagal secara terhormat

Klaim "9/10" untuk triase smishing Indonesia diuji pada **set hakim
300 pesan** (150 sah / 150 smishing) yang tidak pernah jadi data
latih, dengan gerbang yang ditetapkan **sebelum** hasil diketahui:
sah ≥ 85% · smishing ≥ 95% · smishing AUTO-CLOSE = 0 · UCI PR-AUC ≥ 0,98.

| Tahap | Intervensi | Sah | Smishing | AUTO-CLOSE | UCI PR-AUC | Vonis |
|---|---|---|---|---|---|---|
| 0 | Baseline full-stack | 16,0% | 87,3% | 0 | 0,986 | Penyakit terdiagnosis: register formal-institusional ID tak dikenal model |
| 1 | Sinyal penenang (aturan) | 36,0% | 87,3% | 0 | 0,986 | Diterima sebagai app v4 — tambal terukur |
| 2C | Fine-tune dwibahasa DistilBERT | 84,0% | 94,7% | **3** | 0,986 | **DITOLAK** — SAH & SMISHING *tidak meyakinkan* (CI Wilson 95% bersinggungan gerbang), AUTO-CLOSE *gagal jelas* |
| 2D | Loop perbaikan data (satu-satunya) | **92,7%** | 88,7% | **2** | 0,988 | **DITOLAK** — SAH *lolos jelas*, SMISHING & AUTO-CLOSE *gagal jelas*; klaim 9/10 tidak tercapai |

*(Bingkai vonis tiga status — lolos jelas / tidak meyakinkan /
gagal jelas — berlaku sejak Laporan Edisi v3.3, berbasis CI Wilson 95%.)*

Sesuai doktrin yang dikunci di muka — satu loop perbaikan lalu
dokumentasikan apa adanya — **model app TIDAK ditukar** dan penalaan
dihentikan: menala ke set hakim yang sudah diamati berulang =
overfitting. Bottleneck-nya terbukti struktural: hanya ada **satu
korpus SMS Indonesia asli yang publik (1.143 baris, 3 kelas, era
±2012–2016)** dan **nol dataset smishing Indonesia publik**. Hasil
negatif ini disajikan apa adanya karena rigor evaluasinya adalah
nilai proyek ini. Panel evaluasi 16 pesan, uji float16 (tidak
diadopsi), dan kronik lengkapnya: [docs/RINCIAN.md](docs/RINCIAN.md).

## ⚙️ Cara kerja

- **Model operasional (CHOSEN): Ensemble Top-3 Terkalibrasi** —
  rata-rata probabilitas terkalibrasi tiga anggota (dua pipeline
  TF-IDF + LR dan DistilBERT), dipetakan ke zona kebijakan dua
  ambang: **t_close = 0,010** / **t_esc = 0,135**. PR-AUC test
  (UCI Inggris) **0,986**. Polanya: **mesin mengurutkan, manusia
  memutuskan** — skor mengurutkan antrean triase, manusia pemegang
  vonis. Bobot modelnya sendiri **belum siap produksi** (lihat
  hasil kunci di atas).
- **Lapisan aturan** (`rules.py`, regex murni): tiga sinyal kuat —
  **S1** tautan, **S2** permintaan OTP/PIN/kredensial, **S3** ancaman
  + urgensi. Terpicu hanya bila **≥ 2 sinyal bersamaan**, dan hanya
  **menaikkan** band ke ESKALASI; tidak pernah menurunkan, tidak
  mengubah skor. Kalimat pelindung khas bank ("JANGAN bagikan kode
  ini…") secara eksplisit **bukan** sinyal.
- **Sinyal penenang** (arah sebaliknya, sama konservatifnya): pola
  resmi berformat jelas (OTP standar tanpa tautan · domain resmi
  persis · notifikasi transaksi terstruktur) menurunkan band
  ESKALASI model **tepat satu tingkat** — tidak pernah AUTO-CLOSE,
  gugur total bila S2/S3 aktif.
- Tujuh tab: **Lapor & Cek** · **Galeri Modus** · **Analisis
  Tunggal** · **Mode Batch** (antrean prioritas + unduh laporan
  kasus) · **Evaluasi ID** · **Perjalanan Riset** · **Verifikasi**.

## 🔮 Tahap 3 & prinsip arena terbuka

Korpus yang tumbuh dari laporan warga adalah bahan **Tahap 3**:
pelatihan ulang kandidat model Indonesia pada **set hakim baru**,
dengan **gerbang dikunci di muka** — termasuk **Laya** (DistilBERT
dwibahasa proyek ini) dalam pertandingan ulang yang setara.
Prinsipnya: **gerbangnya tetap, modelnya berganti** — setiap model
baru berhak diuji dengan syarat yang sama persis; yang dipertahankan
bukan modelnya, melainkan standarnya. Posisi proyek di lanskap 13
pembanding (layanan resmi, pemeriksa global, korpus kerumunan,
model akademik): ringkasnya di
[docs/RINCIAN.md](docs/RINCIAN.md), lengkapnya di Bagian 13 Laporan.

## 💻 Menjalankan lokal

```bash
cd fraud-triage-laya/streamlit-app
../.venv/bin/streamlit run app.py
# tanpa konfigurasi apa pun, app otomatis memakai ../data/bert_snapshot
```

Deploy ke Streamlit Community Cloud (repo ini hanya berisi kode;
artefak model diunduh dari Hugging Face saat pertama jalan):
[docs/DEPLOY.md](docs/DEPLOY.md).

## 📁 Isi repo (ringkas)

| Berkas | Fungsi |
|---|---|
| `app.py` | Antarmuka Streamlit (Bahasa Indonesia, istilah teknis English): 7 tab + sidebar ringkas |
| `siskamling.py` · `scrubber.py` | Layanan warga: lapor & cek, galeri, verifikasi, analitik · pembersih data pribadi |
| `journey.py` + `results.json` | Tab 🧪 Perjalanan Riset — angka DIGENERATE dari file evaluasi terverifikasi, tidak diketik manual |
| `triage_core.py` | Logika model murni: ensemble, kalibrasi temperatur, kebijakan dua ambang, penjelasan faktor |
| `rules.py` | Lapisan aturan regex murni: sinyal kuat S1–S3 + sinyal penenang P1–P3 |
| `model/ensemble_spec.json` | Spesifikasi ensemble: anggota, temperatur per anggota, ambang kebijakan |
| `docs/` | Laporan & presentasi (PDF) · [RINCIAN.md](docs/RINCIAN.md) · [DEPLOY.md](docs/DEPLOY.md) · tangkapan layar & demo |

Tabel isi folder lengkap: [docs/RINCIAN.md](docs/RINCIAN.md).

---

*Model ini artefak proyek pembelajaran terpimpin (data SMS Inggris ±2011);
bukan sistem produksi perbankan. Vonis lengkap metode — termasuk posisi
Laya sebagai kandidat lapisan teks, bukan model operasional — ada di
notebook proyek.*
