"""QA eksekusi fix ronde 6 Fraud Triage (v6.1.4) — M1/M2/S5.

Mensimulasikan skema Turso live (reports + label_log + view
corpus_export, persis definisi sqlite_master live 2026-11-08) di
SQLite lokal, dengan siskamling.turso_execute di-stub ke sqlite3.
Tidak menyentuh DB live. Jalankan dari root repo ini:
  ~/workspace/fraud-triage-laya/.venv/bin/python qa/qa_fraud_r6_fix.py
"""
import sqlite3
import sys
from pathlib import Path

# Uji kode berversi di repo ini (root repo = parent dari qa/).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import siskamling as sk

con = sqlite3.connect(":memory:")
con.row_factory = sqlite3.Row
con.executescript("""
CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    channel TEXT NOT NULL DEFAULT 'sms',
    text_scrubbed TEXT NOT NULL,
    category_modus TEXT,
    model_score REAL,
    model_band TEXT,
    rules_fired TEXT,
    consent_data_use INTEGER NOT NULL DEFAULT 0,
    consent_at TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    label TEXT,
    verified_at TEXT,
    gallery_visible INTEGER NOT NULL DEFAULT 0,
    sender_hash TEXT, text_hash TEXT, enrichment TEXT);
CREATE TABLE label_log (id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL, aksi TEXT NOT NULL, label TEXT,
    actor TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')));
CREATE VIEW corpus_export AS
SELECT text_scrubbed, label, category_modus, model_score, model_band,
    verified_at FROM reports
WHERE status = 'verified' AND consent_data_use = 1 AND label IS NOT NULL;
""")

CFG = {}


def fake_turso(cfg, sql, args=None):
    cur = con.execute(sql, args or [])
    if cur.description is None:
        con.commit()
        return []
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


sk.turso_execute = fake_turso
fails = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f" — {detail}" if detail else ""))
    if not cond:
        fails.append(name)


# Seed: 3 pending, skor TINGGI di laporan yang masuk TERAKHIR (jebakan
# urutan: bila antrean masih urut skor, #3 muncul pertama).
for rid, score, band, ts in (
        (1, 0.02, "REVIEW", "2026-11-08 01:00:00"),
        (2, 0.50, "ESKALASI", "2026-11-08 02:00:00"),
        (3, 0.99, "ESKALASI", "2026-11-08 03:00:00")):
    con.execute(
        "INSERT INTO reports (id, channel, text_scrubbed, model_score,"
        " model_band, consent_data_use, created_at)"
        " VALUES (?, 'sms', ?, ?, ?, 1, ?)",
        (rid, f"pesan {rid}", score, band, ts))
con.commit()

# --- M1: antrean pelabelan urut waktu masuk, triase urut skor ---
lab = [r["id"] for r in sk.fetch_pending(CFG)]
check("M1 labeling queue = created_at order [1,2,3]", lab == [1, 2, 3], str(lab))
tri = [r["id"] for r in sk.fetch_pending_triage(CFG)]
check("M1 triage queue = score order [3,2,1]", tri == [3, 2, 1], str(tri))

# --- M2: label pertama dibekukan ---
eff = sk.verify_report(CFG, 2, "SMISHING", "blokir_akun", False)
check("M2 first verify returns SMISHING", eff == "SMISHING", str(eff))
row = fake_turso(CFG, "SELECT label, status FROM reports WHERE id = 2")[0]
check("M2 label stored SMISHING", row["label"] == "SMISHING" and row["status"] == "verified")
corp = fake_turso(CFG, "SELECT label FROM corpus_export")
check("M2 corpus_export has SMISHING", [r["label"] for r in corp] == ["SMISHING"], str(corp))

sk.unverify_report(CFG, 2)
row = fake_turso(CFG, "SELECT label, status FROM reports WHERE id = 2")[0]
check("M2 unverify keeps label (not NULL)", row["label"] == "SMISHING" and row["status"] == "pending", str(row))
corp = fake_turso(CFG, "SELECT label FROM corpus_export")
check("M2 corpus_export empty while pending", corp == [], str(corp))

# Verifikasi ulang sesudah "melihat saran": label baru SAH ditolak
# sebagai label korpus, dicatat terpisah.
eff2 = sk.verify_report(CFG, 2, "SAH", "blokir_akun", False)
row = fake_turso(CFG, "SELECT label, status FROM reports WHERE id = 2")[0]
check("M2 re-verify returns frozen SMISHING", eff2 == "SMISHING", str(eff2))
check("M2 reports.label still SMISHING", row["label"] == "SMISHING", str(row))
corp = fake_turso(CFG, "SELECT label FROM corpus_export")
check("M2 corpus_export STILL SMISHING after re-verify", [r["label"] for r in corp] == ["SMISHING"], str(corp))
log = fake_turso(CFG, "SELECT aksi, label FROM label_log WHERE report_id = 2 ORDER BY id")
check("M2 revision logged separately as revisi_pasca_paparan/SAH",
      ("revisi_pasca_paparan", "SAH") in [(r["aksi"], r["label"]) for r in log], str(log))
check("M2 frozen_label() = SMISHING", sk.frozen_label(CFG, 2) == "SMISHING")

# --- M2 legacy: baris yang dikembalikan dengan perilaku lama
# (label NULL, tapi label_log punya 'verifikasi' pertama = SAH) ---
con.execute("INSERT INTO reports (id, channel, text_scrubbed, model_score,"
            " model_band, consent_data_use, created_at, status, label)"
            " VALUES (4, 'sms', 'pesan 4', 0.3, 'ESKALASI', 1,"
            " '2026-11-08 04:00:00', 'pending', NULL)")
con.execute("INSERT INTO label_log (report_id, aksi, label, actor)"
            " VALUES (4, 'verifikasi', 'SAH', 'verifikator')")
con.execute("INSERT INTO label_log (report_id, aksi, label, actor)"
            " VALUES (4, 'kembalikan', 'SAH', 'verifikator')")
con.commit()
eff4 = sk.verify_report(CFG, 4, "SMISHING", "undian", False)
row = fake_turso(CFG, "SELECT label FROM reports WHERE id = 4")[0]
check("M2 legacy row: frozen SAH restored, not overwritten",
      eff4 == "SAH" and row["label"] == "SAH", f"eff={eff4} row={row}")

# --- S5: second review tidak mengubah label, actor tercatat ---
res = sk.second_review(CFG, 2, "SMISHING", actor="peninjau-2")
check("S5 second_review cocok", res == "cocok", res)
res = sk.second_review(CFG, 2, "SAH", actor="peninjau-2")
check("S5 second_review beda", res == "beda", res)
row = fake_turso(CFG, "SELECT label FROM reports WHERE id = 2")[0]
check("S5 label unchanged by second review", row["label"] == "SMISHING")
actors = fake_turso(CFG, "SELECT DISTINCT actor FROM label_log WHERE aksi = 'tinjauan_kedua'")
check("S5 actor peninjau-2 logged", [r["actor"] for r in actors] == ["peninjau-2"], str(actors))
check("S5 gold_count = 1", sk.gold_count(CFG) == 1, str(sk.gold_count(CFG)))

print()
print("FAILURES:", fails if fails else "none — ALL PASS")
sys.exit(1 if fails else 0)
