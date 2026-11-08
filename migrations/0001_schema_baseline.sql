-- Migrasi 0001 — skema baseline Siskamling Digital (v6.1.5).
--
-- Direkonstruksi VERBATIM dari `sqlite_master` basis data Turso live
-- (dibaca 2026-11-09, kueri baca-saja) + fixture QA
-- `qa/qa_fraud_r6_fix.py`. Sebelum ronde 8, skema + view corpus_export
-- HANYA hidup di Turso (Ronde 8, S3): repo ini tidak bisa membangun
-- ulang basis datanya sendiri. Mulai migrasi ini, repo adalah sumber
-- kebenaran skema.
--
-- Cara pakai: jalankan berkas ini (lalu 0002, dst. secara berurutan)
-- ke basis data Turso lewat pipeline / turso CLI. Semua statement
-- idempotent (IF NOT EXISTS) sehingga aman dijalankan ulang; pada
-- basis data live yang sudah punya tabel ini, migrasi ini no-op.
-- JANGAN jalankan ke basis data live tanpa cadangan.

CREATE TABLE IF NOT EXISTS app_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS consent_log (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id        INTEGER NOT NULL REFERENCES reports (id)
                     ON DELETE CASCADE,
    consent_version  TEXT    NOT NULL,
    consent_text_hash TEXT   NOT NULL,
    given_at         TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS label_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL,
    aksi TEXT NOT NULL,
    label TEXT,
    actor TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS reports (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    channel         TEXT    NOT NULL DEFAULT 'sms'
                    CHECK (channel IN ('sms', 'whatsapp', 'telegram',
                                      'lainnya')),
    text_scrubbed   TEXT    NOT NULL,
    category_modus  TEXT,
    model_score     REAL,
    model_band      TEXT
                    CHECK (model_band IN ('AMAN', 'REVIEW', 'ESKALASI')),
    rules_fired     TEXT,
    consent_data_use INTEGER NOT NULL DEFAULT 0
                    CHECK (consent_data_use IN (0, 1)),
    consent_at      TEXT,
    status          TEXT    NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'verified', 'rejected',
                                     'deleted')),
    label           TEXT
                    CHECK (label IN ('SAH', 'SMISHING', 'SPAM_PROMO')),
    verified_at     TEXT,
    gallery_visible INTEGER NOT NULL DEFAULT 0
                    CHECK (gallery_visible IN (0, 1)),
    sender_hash     TEXT,
    text_hash       TEXT,
    enrichment      TEXT
);

CREATE INDEX IF NOT EXISTS idx_consent_log_report
    ON consent_log (report_id);
CREATE INDEX IF NOT EXISTS idx_label_log_report
    ON label_log (report_id);
CREATE INDEX IF NOT EXISTS idx_reports_created_at
    ON reports (created_at);
CREATE INDEX IF NOT EXISTS idx_reports_label
    ON reports (label);
CREATE INDEX IF NOT EXISTS idx_reports_sender_created
    ON reports (sender_hash, created_at);
CREATE INDEX IF NOT EXISTS idx_reports_sender_hash
    ON reports (sender_hash);
CREATE INDEX IF NOT EXISTS idx_reports_status
    ON reports (status);
CREATE INDEX IF NOT EXISTS idx_reports_status_created
    ON reports (status, created_at);
CREATE INDEX IF NOT EXISTS idx_reports_text_hash
    ON reports (text_hash);

-- View korpus v6.1.5 (definisi live saat migrasi ini ditulis). Lihat
-- docs/corpus_export.md untuk arti tiap syarat. 0002 mengubah view
-- ini (pengecualian 'diragukan' + syarat bukti consent).
CREATE VIEW IF NOT EXISTS corpus_export AS
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
  AND label IS NOT NULL;
