-- Migrasi 0003 — atomicity sejati jalur tulis via trigger DB (susulan v6.1.6).
--
-- MASALAH: batch Turso TERBUKTI tidak atomik (tes live 9 Nov 2026: satu
-- langkah gagal, langkah sebelumnya TETAP tersimpan); pola CTE
-- single-statement (WITH + INSERT-di-dalam-WITH) DITOLAK parser SQLite
-- 3.45.1 lokal maupun server Turso (SQL_PARSE_ERROR). Sejak gap ronde 7
-- G7, jalur tulis memakai turso_execute berurutan + kompensasi +
-- gagal-jujur — menutup semua mode gagal yang terlihat, TETAPI crash
-- tepat di antara dua tulis masih bisa menyisakan parsial (baris
-- terverifikasi tanpa jejak, dsb.). Trigger AFTER INSERT / AFTER UPDATE
-- adalah satu-satunya atomicity sejati di SQLite: satu statement
-- aplikasi memicu tulis jejak DALAM transaksi yang sama — bila tulis
-- jejak gagal, statement aplikasi gagal seluruhnya (terbukti uji scratch
-- live 9 Nov 2026, test_trigger_0003_scratch.py, 37/37 PASS: sabotase
-- trigger dengan RAISE(ABORT) membuat INSERT/UPDATE gagal dan TIDAK
-- ADA baris parsial).
--
-- URUTAN DEPLOY — TERBALIK dari migrasi biasa (lihat docstring
-- submit_report/verify_report; migrasi biasa: migrasi dulu, baru kode):
--   1. Deploy kode app yang SADAR trigger (dengan fallback kompensasi
--      bila trigger belum ada).
--   2. REBOOT app Streamlit Cloud (kode baru termuat; masih jalur
--      kompensasi — belum ada trigger).
--   3. Terapkan migrasi ini (apply_migration_0003.py).
--   4. REBOOT app lagi (segarkan cache deteksi skema per proses).
-- Bila migrasi diterapkan SEBELUM kode baru: kode lama menulis jejak
-- sendiri DAN trigger juga menulis -> tulis ganda. Desain di bawah
-- membuat jendela itu AMAN: tiap trigger HANYA menyala bila kolom
-- staging-nya terisi (kode baru selalu mengisinya; kode lama tidak
-- pernah) — jadi statement kode lama LEWAT begitu saja tanpa jejak
-- ganda (terbukti uji scratch "kode lama ..."). Indeks UNIK di bawah
-- adalah backstop kedua: INSERT consent_log kedua untuk satu laporan
-- gagal jujur, bukan diam-diam.
--
-- Kolom staging (nilai yang hanya diketahui aplikasi dibawa ke trigger
-- lewat baris reports itu sendiri — trigger tidak bisa memanggil fungsi
-- Python):
--   * consent_version / consent_text_hash — versi + hash teks consent;
--     dipertahankan sebagai metadata per-laporan (bukan dibersihkan).
--   * log_label_attempt — label yang DICOBA saat verifikasi (jalur
--     label-beku: label baru yang dicoba, bukan label beku); trigger
--     membersihkannya sesudah dipakai.
--   * adj_actor — nama aktor adjudikasi (UI: reviewer2 atau
--     "verifikator"); trigger membersihkannya sesudah dipakai.
--
-- Perubahan:
--   * reports.consent_version, reports.consent_text_hash,
--     reports.log_label_attempt, reports.adj_actor (nullable).
--   * idx_consent_log_report_unique — SATU baris consent per laporan
--     (data live 9 Nov 2026: 4 baris atas 4 report_id berbeda —
--     indeks bisa dibuat tanpa tabrakan, terverifikasi uji scratch).
--   * trg_reports_after_insert_consent — INSERT reports consent=1
--     menulis consent_log dalam transaksi yang sama.
--   * trg_reports_after_verify — UPDATE pending->verified menulis
--     label_log ('verifikasi' pertama / 'revisi_pasca_paparan'
--     sesudahnya, label = label yang dicoba).
--   * trg_reports_after_adjudicate_diragukan — UPDATE
--     corpus_excluded 0->1 menulis label_log ('adjudikasi' /
--     'diragukan' + putusan + actor).
--
-- Terapkan: satu statement per request Hrana /v2/pipeline — JANGAN
-- pecah berkas per ';' (badan trigger mengandung ';'); pakai
-- apply_migration_0003.py (pecah via sqlite3.complete_statement).
-- Cadangkan dulu (backup_pre_migration_0003.json — dibuat applier
-- sebelum statement pertama).

ALTER TABLE reports ADD COLUMN consent_version TEXT;
ALTER TABLE reports ADD COLUMN consent_text_hash TEXT;
ALTER TABLE reports ADD COLUMN log_label_attempt TEXT;
ALTER TABLE reports ADD COLUMN adj_actor TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_consent_log_report_unique
    ON consent_log (report_id);

CREATE TRIGGER IF NOT EXISTS trg_reports_after_insert_consent
AFTER INSERT ON reports
WHEN NEW.consent_data_use = 1 AND NEW.consent_version IS NOT NULL
BEGIN
    INSERT INTO consent_log (report_id, consent_version, consent_text_hash)
    VALUES (NEW.id, NEW.consent_version, NEW.consent_text_hash);
END;

CREATE TRIGGER IF NOT EXISTS trg_reports_after_verify
AFTER UPDATE OF status ON reports
WHEN OLD.status = 'pending' AND NEW.status = 'verified'
    AND NEW.log_label_attempt IS NOT NULL
BEGIN
    INSERT INTO label_log (report_id, aksi, label, actor)
    SELECT NEW.id,
           CASE WHEN EXISTS (SELECT 1 FROM label_log
                             WHERE report_id = NEW.id AND aksi = 'verifikasi')
                THEN 'revisi_pasca_paparan' ELSE 'verifikasi' END,
           COALESCE(NEW.log_label_attempt, NEW.label),
           'verifikator';
    UPDATE reports SET log_label_attempt = NULL WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_reports_after_adjudicate_diragukan
AFTER UPDATE OF corpus_excluded ON reports
WHEN OLD.corpus_excluded = 0 AND NEW.corpus_excluded = 1
    AND NEW.adj_actor IS NOT NULL
BEGIN
    INSERT INTO label_log (report_id, aksi, label, actor, putusan)
    VALUES (NEW.id, 'adjudikasi', 'diragukan',
            COALESCE(NEW.adj_actor, 'verifikator'), 'diragukan');
    UPDATE reports SET adj_actor = NULL WHERE id = NEW.id;
END;
