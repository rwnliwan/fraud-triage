# 🛡️ Fraud Triage — Aplikasi Triase Smishing (Streamlit)

Aplikasi penyaji model terpilih proyek **Fraud Triage**: **Ensemble (Top-3
Terkalibrasi)** dengan kebijakan dua ambang operasional **t_close = 0,010**
dan **t_esc = 0,135** (Bagian 10 notebook `fraud-triage-laya-vs-ml-dl.ipynb`).

Pengguna menempel teks SMS → app menampilkan probabilitas scam terkalibrasi,
keputusan triase (AMAN / Review Analis / Eskalasi) pada kartu hasil berwarna
dengan bilah skor visual terhadap kedua ambang, skor per anggota ensemble,
penjelasan faktor teks (kata pendorong + fitur angka), **panel sinyal** yang
terdeteksi dari teks, dan **lapisan aturan** keamanan di atas model.

Fitur app: analisis tunggal dengan contoh siap-klik (termasuk contoh OTP
bank asli), **mode batch** (satu pesan per baris → tabel + ringkasan per
band), **riwayat sesi**, dan sidebar info model dengan keterbatasan yang
jujur. Tema gelap "fraud ops console" diatur di `.streamlit/config.toml`
plus CSS kustom di `app.py`.

**Baru di v3** (menutup kritik atas v2):

- **Ekspor CSV** untuk tiga hal: hasil batch, riwayat sesi, dan log
  koreksi (kolom: teks dipotong aman, skor, band model, band final,
  aturan terpicu, sinyal aktif).
- **Batch yang layak kerja**: bilah progres per pesan ("Menilai i dari
  N"), batas **200 baris** ditegakkan (baris kosong dilewati; di luar
  batas ditolak dengan pesan jelas, tidak ada yang diproses diam-diam).
  Engine publik hanya menilai per teks, jadi batch berjalan sekuensial
  dengan progres.
- **Batas input tunggal 2.000 karakter** — teks lebih panjang dipotong
  dan peringatan ditampilkan.
- **Tombol koreksi** di bawah hasil tunggal: pengguna memilih band yang
  benar menurutnya; tercatat di **log koreksi sesi** (dengan unduh CSV).
  Jujur apa adanya: log ini hidup **hanya di sesi browser (demo)** —
  tidak ada penyimpanan permanen dan tidak terkirim ke mana pun.
- **Tab 🇮🇩 Evaluasi ID**: set uji kecil buatan 16 pesan Indonesia
  berlabel harapan yang dijalankan apa adanya — lihat hasilnya di bawah.
- **Kalimat penjelasan vonis** pada kartu hasil + footer berisi versi
  app dan tautan repo/model.

## Lapisan aturan (rules layer)

Di atas skor model ada lapisan aturan deterministik (`rules.py`, murni
regex, tanpa dependensi ML) yang dirancang konservatif:

- **Kombinasi, bukan kata tunggal.** Tiga sinyal kuat: **S1** ada tautan
  (URL) — terutama pemendek/domain tak resmi; **S2** permintaan memasukkan
  OTP/PIN/kredensial atau bertindak lewat tautan; **S3** ancaman
  blokir/suspensi/hangus **disertai** urgensi waktu. Aturan terpicu hanya
  bila **≥ 2 sinyal kuat hadir bersamaan**.
- **Hanya menaikkan.** Bila terpicu, band final dipaksa ke ESKALASI berapa
  pun skor modelnya. Aturan **tidak pernah menurunkan** band dan **tidak
  mengubah skor** — pesan yang model anggap berisiko tidak bisa ditutup
  oleh aturan.
- **Tidak salah tembak ke pesan sah.** Kalimat pelindung khas bank
  ("JANGAN bagikan/berikan kode ini kepada siapa pun") secara eksplisit
  bukan sinyal S2: kata kerja meminta-masukkan tidak mencakup
  "berikan/bagikan", dan kecocokan yang didahului "jangan" dibuang.
  Contoh "🏦 OTP bank asli (ID)" di app mendemonstrasikan ini: aturannya
  diam; apa pun band-nya datang murni dari model.
- **Transparan.** Bila aturan menaikkan band, kartu hasil menampilkan
  lencana "Aturan terpicu" berisi sinyal-sinyalnya; panel sinyal selalu
  menampilkan hitungan sinyal kuat yang aktif.

---

## Panel evaluasi Indonesia (v3) — hasil apa adanya

Tab 🇮🇩 Evaluasi ID menjalankan **16 pesan buatan** (8 sah, 8 smishing;
nama bank fiktif "Bank Nusantara"/"Bank Sentosa", domain mencurigakan
fiktif) yang **dikunci di kode sebelum pertama kali dijalankan**. Ini
**bukan benchmark** — hanya panel transparansi. Definisi "sesuai": sah →
band final AUTO-CLOSE/REVIEW; smishing → band final ESKALASI.

Hasil run pertama (dan run UI sesudahnya identik):

| Kelompok | Sesuai | Catatan |
|---|---|---|
| Pesan SAH | **1/8** | Hanya pesan pribadi (0,009 → AUTO-CLOSE) yang tidak dieskalasi. Tujuh pesan sah lain — OTP bank asli (0,462), notifikasi transaksi (0,729), tagihan telekomunikasi (0,546), kurir wajar (0,655), notifikasi keamanan bank (0,561), e-statement (0,682), undangan rapat (0,267) — semuanya di-ESKALASI **oleh model sendiri**; lapisan aturan tidak pernah memicu pada pesan sah. |
| SMISHING | **8/8** | Semua mencapai ESKALASI; 4 di antaranya dibantu lapisan aturan (S1+S2 atau S1+S2+S3), 4 sisanya murni skor model. |

**Bacaan jujurnya:** pada set kecil ini model sangat agresif terhadap
teks Indonesia — smishing tertangkap semua, tetapi presisi pada pesan
sah Indonesia buruk (over-eskalasi), konsisten dengan keterbatasan data
latih UCI SMS Inggris ±2011. Panel ini sengaja menampilkan kegagalan
itu, bukan menyembunyikannya; memperbaikinya butuh data latih/evaluasi
Indonesia berlabel yang sesungguhnya, bukan penyesuaian pesan uji.

## Uji float16 (v3) — TIDAK diadopsi

DistilBERT diuji dalam dua dtype (cast saat muat lokal, repo HF tidak
diubah; CPU, 4 probe resmi + latensi 5 pesan × 3 putaran):

| Ukuran | fp32 | fp16 (cast) |
|---|---|---|
| Skor probe (undian / ham / OTP / spam) | 0,652 / 0,012 / 0,293 / 0,220 | 0,652 / 0,012 / 0,293 / 0,220 (selisih maks **0,000053**) |
| Band probe | sama persis | sama persis |
| Bobot BERT | 541,3 MB | 270,7 MB |
| Latensi per pesan | **114,7 ms** | **179,5 ms (+56%)** |

Aturan adopsi yang ditetapkan sebelumnya: band probe sama DAN selisih
skor ≤ 0,005 DAN latensi tidak memburuk > 25%. fp16 lolos dua syarat
pertama tetapi **gagal syarat latensi** (CPU tidak punya akselerasi
fp16 untuk model ini), jadi **app tetap fp32**. Penghematan memori
271 MB tidak ditukar dengan inferensi 56% lebih lambat.

---

## Isi folder

| Berkas | Fungsi |
|---|---|
| `app.py` | Antarmuka Streamlit **v3** (Bahasa Indonesia, istilah teknis English): analisis tunggal (batas 2.000 char, kalimat vonis, tombol koreksi + log koreksi sesi), mode batch (progres per pesan, batas 200 baris), ekspor CSV (batch/riwayat/koreksi), tab evaluasi ID, riwayat sesi, panel sinyal, bilah skor |
| `triage_core.py` | Logika model murni (tanpa Streamlit): ensemble, kalibrasi temperatur, kebijakan dua ambang, penjelasan faktor |
| `rules.py` | Lapisan aturan murni regex (tanpa Streamlit): deteksi sinyal teks + aturan kombinasi ≥2 sinyal kuat yang memaksa ESKALASI (hanya menaikkan) |
| `.streamlit/config.toml` | Tema gelap "fraud ops console" (warna dasar, aksen amber) |
| `build_artifacts.py` | Skrip pembangunan artefak deploy dari resep notebook + verifikasi angka (sudah dijalankan; jalankan ulang hanya bila resep berubah) |
| `requirements.txt` | Dependensi (torch diarahkan ke wheel CPU) |
| `model/ensemble_spec.json` | Spesifikasi ensemble: anggota, temperatur per anggota, ambang kebijakan (salinan lokal; di cloud diunduh dari Hugging Face) |
| `model/sklearn_members.joblib` | Dua anggota sklearn yang dilatih ulang persis dari resep notebook (pipeline LR + komponen model fitur) — berkas biner, **tidak ikut repo GitHub**; di cloud diunduh dari Hugging Face |
| `model/model_operasional.pkl` | Salinan artefak resmi proyek — isinya **spesifikasi** ensemble (nama anggota + temperatur), sumber kebenaran `ensemble_spec.json` |
| `model/bert/` | *(opsional, lokal saja)* tempat bobot DistilBERT fine-tune bila ingin menimpa sumber cloud |

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
   (mode dev lokal) → `BERT_MODEL_ID` (repo Hugging Face) → repo artefak
   bawaan (di bawah).
3. **Jalur cloud (bawaan deploy)**: seluruh artefak yang dibutuhkan app —
   `ensemble_spec.json`, `sklearn_members.joblib`, dan bobot DistilBERT
   (config + `model.safetensors` + tokenizer) — terunggah di repo model
   Hugging Face **publik** `rwnliwan/fraud-triage-smishing`. Resolusi
   selalu lokal-dulu; bila berkas lokal tidak ada (kondisi normal di
   Streamlit Cloud, karena repo GitHub hanya berisi kode), artefak
   diunduh dari repo itu tanpa token. Repo sumber bisa diganti lewat
   env/secrets `ARTIFACT_REPO_ID`.
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

## Deploy ke Streamlit Community Cloud

Seluruh artefak model sudah terunggah di repo Hugging Face publik
**`rwnliwan/fraud-triage-smishing`** dan repo GitHub hanya berisi kode —
jadi deploy tidak lagi butuh penempatan bobot manual.

### Langkah 1 — Repo GitHub

Repo GitHub berisi isi folder `streamlit-app/` ini sebagai root
(`app.py`, `triage_core.py`, `rules.py`, `build_artifacts.py`,
`requirements.txt`, `README.md`, `.streamlit/config.toml`,
`model/ensemble_spec.json`). Berkas biner
(`sklearn_members.joblib`, bobot BERT) **sengaja tidak** ikut repo —
app mengunduhnya dari Hugging Face saat pertama jalan.

### Langkah 2 — Buat app di Streamlit Community Cloud

1. Buka **share.streamlit.io** → *Sign in with GitHub*.
2. Klik **New app** → pilih repo GitHub itu, branch `main`,
   *Main file path*: `app.py`.
3. (Opsional, di *Advanced settings*) Python 3.12.
4. **Secrets TIDAK wajib diisi** — model otomatis diambil dari repo
   Hugging Face publik bawaan. Override hanya bila perlu mengganti
   sumber artefak: `ARTIFACT_REPO_ID = "<user>/<repo-model-lain>"`
   (atau `BERT_MODEL_ID` khusus untuk bobot DistilBERT saja).
5. Klik **Deploy** dan tunggu build pertama selesai (tarik torch CPU +
   transformers, lalu unduh model ±541 MB dari Hugging Face;
   beberapa menit).

### Langkah 3 — Verifikasi pasca-deploy

Klik contoh **"🎁 Undian palsu (ID)"** → keputusan harus **ESKALASI**
(skor ±0,65); contoh **"💬 Pesan sah (EN)"** → **REVIEW ANALIS**
(skor ±0,012). Bila app gagal memuat model, pesan error di app menyebut
sumber artefak yang dicari — periksa repo `ARTIFACT_REPO_ID` yang aktif
(bawaan: `rwnliwan/fraud-triage-smishing`).

### Catatan sumber daya

Tier gratis Streamlit Cloud memberi RAM ±1 GB. DistilBERT multilingual
fp32 memakai 541,3 MB bobot; app ini sudah teruji memuat & memprediksi
di CPU. Opsi float16 **sudah diuji di v3 dan tidak diadopsi** — bobot
memang separuh (270,7 MB) dan skor praktis identik, tetapi latensi CPU
memburuk +56% (lihat bagian "Uji float16" di atas). Bila suatu saat
deploy kena batas RAM, opsi tindak lanjutnya adalah membatasi beban
dengan cara lain (mis. antrean/pembatasan laju), bukan menurunkan
presisi angka model.

---

*Model ini artefak proyek pembelajaran terpimpin (data SMS Inggris ±2011);
bukan sistem produksi perbankan. Vonis lengkap metode — termasuk posisi
Laya sebagai kandidat lapisan teks, bukan model operasional — ada di
notebook proyek.*
