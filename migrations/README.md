# Migrasi basis data Siskamling Digital

Skema + view `corpus_export` adalah bagian dari repo (bukan hanya
hidup di Turso) sejak ronde 8 (S3). Urutan penerapan: `0001`, lalu
`0002`, dst. — jangan loncat, jangan terapkan dua kali tanpa
memeriksa (semua statement idempotent kecuali `ALTER TABLE ...
ADD COLUMN`, yang gagal secara jujur bila kolom sudah ada — itu
tanda migrasi sudah diterapkan, bukan kesalahan).

## Menerapkan ke Turso live

Opsi A — Turso CLI (dari mesin yang memegang kredensial):

```sh
turso db shell siskamling-digital < migrations/0001_schema_baseline.sql
turso db shell siskamling-digital < migrations/0002_r8_corpus_track_ocr.sql
```

Opsi B — pipeline HTTP `/v2/pipeline` (satu statement per request;
pecah berkas per statement bila perlu). Kredensial di
`~/.config/turso/siskamling-digital.env` (mode 600).

## Aturan

- Cadangkan basis data dulu (`turso db shell ... ".dump"` / ekspor).
- Terapkan migrasi DULU, lalu deploy kode app yang memakainya, lalu
  **reboot app Streamlit Cloud** (cache deteksi skema per proses +
  modul impor hanya tersegarkan lewat reboot — sidebar versi BUKAN
  bukti kode live).
- Verifikasi sesudahnya (baca-saja): `SELECT sql FROM sqlite_master
  WHERE name = 'corpus_export'` harus sama dengan definisi di `0002`;
  `PRAGMA table_info(reports)` memuat `corpus_excluded`,
  `track_code`, `via_ocr`; `PRAGMA table_info(label_log)` memuat
  `putusan`.
- Migrasi baru: satu berkas per perubahan, nomor urut berikutnya,
  header menjelaskan ALASAN + dampak + apa yang gagal secara jujur
  bila migrasi belum diterapkan. Guard QA
  (`qa/qa_fraud_r6_fix.py`, seksi Ronde 8) mengeksekusi SEMUA berkas
  migrasi di SQLite lokal dan mengunci bahwa view hasil migrasi sama
  dengan view yang dipakai guard — migrasi yang tidak bisa dieksekusi
  di guard = migrasi yang tidak boleh di-commit.
