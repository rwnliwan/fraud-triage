# View `corpus_export` — definisi & dampaknya pada korpus

> Catatan gap-build G3 (8 Nov 2026; diperbarui Ronde 8, app v6.1.6).
> View ini hidup di basis data Turso, tetapi definisinya kini
> **berversi di repo** sebagai migrasi (`migrations/0002_r8_corpus_track_ocr.sql`)
> — bukan lagi "tidak ada di kode repo". Definisi di bawah adalah
> versi 0002; versi aslinya (8 Nov 2026, verbatim dari `sqlite_master`
> live) tersimpan di `migrations/0001_schema_baseline.sql`.

## Definisi (migrasi 0002, app v6.1.6)

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
  AND corpus_excluded = 0
  AND EXISTS (SELECT 1 FROM consent_log c
              WHERE c.report_id = reports.id)
```

## Artinya

Satu baris masuk korpus ekspor **jika dan hanya jika**:

1. `status = 'verified'` — laporan sudah diverifikasi manusia;
2. `consent_data_use = 1` — pelapor menyetujui pemakaian data;
3. `label IS NOT NULL` — sudah berlabel (`SAH` / `SMISHING` /
   `SPAM_PROMO`, sesuai `CHECK` pada `reports.label`);
4. `corpus_excluded = 0` — tidak dikecualikan oleh adjudikasi
   'diragukan' (Ronde 8, M2; `migrations/0002`);
5. `EXISTS (consent_log)` — ada jejak persetujuan yang tersimpan
   (Ronde 8, M4; pertahanan kedua bila simpan consent gagal —
   baris consent=1 tanpa jejak consent tidak masuk korpus).

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
- Adjudikasi **'diragukan'** (Ronde 8, M2; app v6.1.6) menyetel
  `corpus_excluded = 1` sehingga baris keluar dari view — putusan
  yang tidak mengubah korpus adalah cacat yang sama. Catatan jujur:
  salinan korpus yang **sudah diekspor sebelum** putusan itu tidak
  bisa ditarik kembali; pengecualian hanya berlaku untuk ekspor
  sesudahnya. Adjudikasi 'pertahankan' tidak mengubah korpus.

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

Terapkan migrasi di `migrations/` secara berurutan: `0001_schema_baseline.sql`
(skema + view versi awal), lalu `0002_r8_corpus_track_ocr.sql` (kolom
baru + view versi di atas). Jangan membangun view dari catatan ini
saja — `migrations/` adalah sumber kebenaran berversi.

## Status live saat catatan ditulis (8 Nov 2026)

`reports` kosong (0 baris) — panel Analitik menampilkan status
kosong ("Belum ada data"). Angka 0 ini hasil kueri live, bukan
perkiraan. `turnstile_on = '1'`, `intake_open = '1'` di `app_config`.
