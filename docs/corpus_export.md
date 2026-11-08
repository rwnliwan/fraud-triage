# View `corpus_export` — definisi & dampaknya pada korpus

> Catatan gap-build G3 (8 Nov 2026). View ini **tidak ada di kode repo**
> (tidak ada `CREATE VIEW` di `siskamling.py`/`app.py`/mana pun) —
> ia hidup di basis data Turso saja. Definisi di bawah diambil
> **verbatim dari `sqlite_master` live** (8 Nov 2026, kueri baca saja),
> supaya dampak perubahan kode pada korpus bisa dilacak dari repo.

## Definisi verbatim (Turso, `sqlite_master`)

```sql
CREATE VIEW corpus_export AS
SELECT
    text_scrubbed,
    label,
    category_modus,
    model_score,
    model_band,
    verified_at
FROM reports
WHERE status = 'verified'
  AND consent_data_use = 1
  AND label IS NOT NULL
```

## Artinya

Satu baris masuk korpus ekspor **jika dan hanya jika**:

1. `status = 'verified'` — laporan sudah diverifikasi manusia;
2. `consent_data_use = 1` — pelapor menyetujui pemakaian data;
3. `label IS NOT NULL` — sudah berlabel (`SAH` / `SMISHING` /
   `SPAM_PROMO`, sesuai `CHECK` pada `reports.label`).

Yang **tidak** menjadi syarat view: `gallery_visible` (galeri publik
adalah soal tampil, bukan soal masuk korpus) dan `category_modus`
(boleh NULL).

## Kaitan dengan pembekuan label (Ronde 6, M2 — app v6.1.4)

View membaca `reports.label` pada baris `status = 'verified'`.
Karena itu yang menentukan isi korpus adalah **nilai kolom `label`
pada saat baris berstatus verified** — dan kode menjamin nilai itu
adalah label pertama:

- `verify_report()` menulis `label` **hanya bila laporan belum pernah
  diverifikasi** (cek `frozen_label()` dari `label_log` aksi
  `verifikasi` paling awal, plus pengaman kedua dari kolom `label`
  baris itu sendiri). Verifikasi ulang sesudah laporan dikembalikan
  ke antrean hanya mengubah `status`/`category_modus`/
  `gallery_visible`/`verified_at` dan mencatat
  `revisi_pasca_paparan` di `label_log` — `reports.label` tidak
  ditulis ulang.
- `unverify_report()` **tidak menghapus label** (perilaku lama
  `label = NULL` sudah dihapus): baris kembali `pending` dengan label
  pertamanya tetap tersimpan, jadi saat diverifikasi ulang ia kembali
  masuk view dengan label pertama itu.
- `reject_report()` (`status = 'rejected'`) dan `delete_report()`
  (`status = 'deleted'`) mengeluarkan baris dari view.
- `second_review()` tidak mengubah `label` apa pun — ia hanya
  mencatat `tinjauan_kedua` di `label_log`.

Konsekuensi: **label korpus = label pertama yang diverifikasi**,
bukan label terakhir. Revisi pasca-paparan saran mesin hanya ada di
`label_log`, tidak pernah sampai ke ekspor.

## Dipakai di mana

- `corpus_count()` (`SELECT COUNT(*) FROM corpus_export`) — metrik
  "Baris korpus (corpus_export)" di tab Verifikasi.
- `analytics_snapshot()` (`SELECT label, COUNT(*) ... FROM
  corpus_export GROUP BY label`) — progres korpus menuju target
  **±1.000 baris untuk retrain Tahap 3** dan rincian per label di
  panel 📊 Analitik. Teks panel "Korpus berlabel+consent" merujuk
  persis ke ketiga syarat view di atas.
- Ekspor korpus latih Tahap 3 (di luar app) membaca view ini.

## Bila basis data dibangun ulang

Buat ulang view dengan SQL verbatim di atas. Skema tabel terkait
(`reports`, `label_log`, `app_config`) juga hanya hidup di Turso;
tidak ada migrasi SQL di repo saat catatan ini ditulis.

## Status live saat catatan ditulis (8 Nov 2026)

`reports` kosong (0 baris) — panel Analitik menampilkan status
kosong ("Belum ada data"). Angka 0 ini hasil kueri live, bukan
perkiraan. `turnstile_on = '1'`, `intake_open = '1'` di `app_config`.
