-- Migrasi 0002 — perbaikan review ronde 8 (app v6.1.6).
--
-- WAJIB diterapkan ke basis data Turso live SEBELUM (atau bersamaan
-- dengan) deploy app v6.1.6, lalu REBOOT app Streamlit Cloud.
-- Kode v6.1.6 mendeteksi keberadaan kolom baru dan menurun grasi
-- (graceful degradation) bila migrasi belum diterapkan — tetapi tiga
-- perilaku TIDAK bisa jalan tanpanya dan gagal secara JUJUR (bukan
-- diam-diam):
--   * adjudikasi 'diragukan' DITOLAK sampai kolom corpus_excluded ada
--     (putusan tanpa efek korpus = cacat R8 M2 — tidak boleh terulang);
--   * laporan baru TIDAK mendapat kode lacak sampai kolom track_code
--     ada (resep menampilkan nomor laporan + catatan);
--   * penanda OCR tidak tersimpan sampai kolom via_ocr ada.
-- Setelah migrasi diterapkan, reboot app agar cache deteksi skema
-- (per proses Streamlit) tersegarkan.
--
-- Perubahan:
--   R8 M2  reports.corpus_excluded — 1 bila putusan adjudikasi
--          'diragukan'; view corpus_export mengecualikannya. Tanpa
--          ini, baris yang labelnya diragukan tetap masuk korpus.
--   R8 M4  view corpus_export kini mensyaratkan ADA baris consent_log
--          untuk laporan itu (bukti persetujuan). Baris consent=1
--          yang jejak consent-nya gagal tersimpan (kegagalan M4)
--          tidak lagi bisa masuk korpus — kegagalan penyimpanan
--          menjadi aman (fail-closed), bukan korpus-tanpa-bukti.
--          CATATAN: salinan korpus yang SUDAH diekspor sebelum
--          migrasi ini tidak bisa ditarik kembali; syarat ini hanya
--          berlaku untuk ekspor sesudahnya.
--   R8 M9  reports.track_code — kode lacak ACAK per laporan (bukan
--          nomor urut yang bisa ditebak). Baris lama di-backfill
--          dengan 8 karakter heksadesimal acak.
--   R8 S1  label_log.putusan — putusan adjudikasi di kolom sendiri
--          ('pertahankan'/'diragukan'); kolom label tetap membawa
--          putusan yang sama demi kompatibilitas pembaca lama
--          (semua pembaca memfilter aksi='adjudikasi').
--   R8 S6  reports.via_ocr — 1 bila teks laporan berasal dari OCR.

ALTER TABLE reports ADD COLUMN corpus_excluded INTEGER NOT NULL
    DEFAULT 0 CHECK (corpus_excluded IN (0, 1));
ALTER TABLE reports ADD COLUMN track_code TEXT;
ALTER TABLE reports ADD COLUMN via_ocr INTEGER NOT NULL DEFAULT 0
    CHECK (via_ocr IN (0, 1));
ALTER TABLE label_log ADD COLUMN putusan TEXT;

-- Backfill kode lacak baris lama. 8 karakter heksadesimal dari
-- randomblob (32 bit) — cukup untuk skala layanan ini; tabrakan
-- praktis tidak mungkin pada jumlah baris saat ini (1 baris live),
-- dan indeks UNIK di bawah akan menggagalkan migrasi secara jujur
-- bila tabrakan benar-benar terjadi (bukan diam-diam).
-- BEDAKAN GENERASI: backfill 32-bit ini BUKAN kode baru aplikasi —
-- kode baru memakai alfabet 31 karakter x 8 = 39,63 bit (dikoreksi
-- ronde 9, S1 dari angka lama).
UPDATE reports SET track_code = substr(hex(randomblob(4)), 1, 8)
    WHERE track_code IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_reports_track_code
    ON reports (track_code);

DROP VIEW IF EXISTS corpus_export;
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
              WHERE c.report_id = reports.id);
