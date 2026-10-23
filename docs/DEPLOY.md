# 🚀 Panduan Deploy — Streamlit Community Cloud

Seluruh artefak model sudah terunggah di repo Hugging Face publik
**`rwnliwan/fraud-triage-smishing`** dan repo GitHub hanya berisi kode —
jadi deploy tidak lagi butuh penempatan bobot manual.


## Konfigurasi secrets Siskamling Digital

Konfigurasi deploy (Streamlit Cloud → Settings → Secrets — nilai
**tidak pernah** masuk repo/git): `TURSO_DATABASE_URL`,
`TURSO_AUTH_TOKEN`, `SISKAMLING_SENDER_SALT`,
`SISKAMLING_ADMIN_PASSWORD`. Tanpa secrets Turso, tab Lapor & Cek
tetap bisa dipakai untuk cek, tetapi laporan tidak tersimpan dan
galeri tidak aktif; tanpa kata sandi admin, tab Verifikasi tidak
aktif.


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
