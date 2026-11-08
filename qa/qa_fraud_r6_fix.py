"""QA eksekusi fix ronde 6 + ronde 7 Fraud Triage (v6.1.5) — M1/M2/S5 (R6)
+ M1–M4/S1–S10/N1–N3 (R7).

Mensimulasikan skema Turso live (reports + label_log + view
corpus_export, persis definisi sqlite_master live 2026-11-08) di
SQLite lokal, dengan siskamling.turso_execute di-stub ke sqlite3.
Tidak menyentuh DB live. Jalankan dari root repo ini:
  ~/workspace/fraud-triage-laya/.venv/bin/python qa/qa_fraud_r6_fix.py

Cek R7 terbagi dua: eksekusi (scrubber, rules, gold/adjudikasi,
consent, avg-verifikasi + tanggal WITA di DB bersih) dan struktural
(segmen kode kartu pending / expander triase + teks klaim di
siskamling.py/app.py/journey.py — pelabelan buta tidak bisa diuji
tanpa browser, jadi guard mengunci bahwa string sinyalnya memang
tidak lagi dirender di jalur itu).
"""
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Uji kode berversi di repo ini (root repo = parent dari qa/).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import siskamling as sk
from rules import evaluate_calm, evaluate_rules
from scrubber import scrub

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

# ==================== RONDE 7 (v6.1.5) ====================
REPO = Path(__file__).resolve().parent.parent
SRC = (REPO / "siskamling.py").read_text(encoding="utf-8")
APP_SRC = (REPO / "app.py").read_text(encoding="utf-8")
JRN_SRC = (REPO / "journey.py").read_text(encoding="utf-8")

# --- R7-M1: scrubber buang query URL tanpa path (dieksekusi) ---
got, _ = scrub("cek https://example.com?token=abc123 sekarang")
check("R7-M1 scrub drops query without path",
      got == "cek [tautan: example.com] sekarang", got)
got, _ = scrub("cek https://example.com/path?token=abc123 sekarang")
check("R7-M1 scrub drops query with path",
      got == "cek [tautan: example.com] sekarang", got)
got, _ = scrub("kunjungi bca.co.id.evil.com?token=secret")
check("R7-M1 scrub drops query on evil host",
      got == "kunjungi [tautan: bca.co.id.evil.com]", got)
got, _ = scrub("saldo Rp50.000.000 cair")
check("R7-M1 scrub leaves money untouched",
      got == "saldo Rp50.000.000 cair", got)
got, _ = scrub("hub 0812-3456-7890 ya")
check("R7-M1 scrub still scrubs phone",
      got == "hub [NOMOR] ya", got)

# --- R7-M2/M3/S3/S4: kartu pending + expander triase (struktural) ---
# Kartu pending = segmen antara penanda pelabelan-buta dan expander
# triase; expander triase = segmen sampai daftar terverifikasi.
pend = SRC.split("# Pelabelan BUTA", 1)[1].split("# Antrean triase", 1)[0]
tri = SRC.split("# Antrean triase", 1)[1].split("Terverifikasi terakhir", 1)[0]
check("R7-M2 no frozen-history caption rendered",
      "pernah terverifikasi sebelumnya" not in SRC)
check("R7-M2/S3/S4 pending card hides history + enrichment",
      "pernah terverifikasi" not in pend
      and "enrichment_summary" not in pend, pend[:80])
check("R7-S4 pending card uses blind meta",
      "blind=True" in pend)
check("R7-M3 triage expander shows no band",
      "band model:" not in tri)
check("R7-M3 triage expander has no per-report rows",
      "fetch_pending_triage" not in tri)
check("R7-M3 triage expander shows count only",
      "count_status" in tri)

# --- R7-M4: kesepakatan dua peninjau + adjudikasi (dieksekusi) ---
con.execute(
    "INSERT INTO reports (id, channel, text_scrubbed, model_score,"
    " model_band, consent_data_use, created_at)"
    " VALUES (5, 'sms', 'pesan 5', 0.4, 'ESKALASI', 1,"
    " '2026-11-08 05:00:00')")
con.commit()
eff5 = sk.verify_report(CFG, 5, "SAH", "undian", False)
check("R7-M4 verify #5 SAH", eff5 == "SAH", str(eff5))
gold_before = sk.gold_count(CFG)
check("R7-M4 gold baseline = 1", gold_before == 1, str(gold_before))
res5 = sk.second_review(CFG, 5, "SMISHING", actor="peninjau-2")
check("R7-M4 second_review beda", res5 == "beda", res5)
check("R7-M4 gold unchanged by beda",
      sk.gold_count(CFG) == gold_before, str(sk.gold_count(CFG)))
# #2 dari seksi R6 sudah punya event tinjauan_kedua "beda" (SAH vs
# label beku SMISHING) — jadi disputed = 2 (#2 + #5), bukan 1.
check("R7-M4 disputed_count = 2 (#2 R6 + #5)",
      sk.disputed_count(CFG) == 2, str(sk.disputed_count(CFG)))
row5 = fake_turso(CFG, "SELECT label FROM reports WHERE id = 5")[0]
check("R7-M4 label still SAH after beda", row5["label"] == "SAH",
      str(row5))
check("R7-M4 adjudicate returns True",
      sk.adjudicate_report(CFG, 5, "pertahankan",
                           actor="verifikator") is True)
check("R7-M4 disputed_count = 1 after adjudicating #5 (#2 left)",
      sk.disputed_count(CFG) == 1, str(sk.disputed_count(CFG)))
check("R7-M4 adjudicate #2 closes the R6 leftover too",
      sk.adjudicate_report(CFG, 2, "pertahankan",
                           actor="verifikator") is True)
check("R7-M4 disputed_count = 0 after adjudicating #2",
      sk.disputed_count(CFG) == 0, str(sk.disputed_count(CFG)))
check("R7-M4 gold still unchanged after adjudication",
      sk.gold_count(CFG) == gold_before, str(sk.gold_count(CFG)))
log5 = fake_turso(CFG, "SELECT aksi, label FROM label_log "
                       "WHERE report_id = 5")
check("R7-M4 adjudikasi logged as adjudikasi/pertahankan",
      ("adjudikasi", "pertahankan") in [(r["aksi"], r["label"])
                                        for r in log5], str(log5))
check("R7-M4 second adjudicate returns False",
      sk.adjudicate_report(CFG, 5, "diragukan") is False)
check("R7-M4 no 'paling tepercaya' claim left",
      "bahan korpus paling tepercaya" not in SRC)

# --- R7-S1: consent hanya atas laporan dalam alur (dieksekusi) ---
con.execute(
    "INSERT INTO reports (id, channel, text_scrubbed, model_score,"
    " model_band, consent_data_use, created_at, status)"
    " VALUES (6, 'sms', 'pesan 6', 0.1, 'REVIEW', 1,"
    " '2026-11-08 06:00:00', 'rejected')")
con.execute(
    "INSERT INTO reports (id, channel, text_scrubbed, model_score,"
    " model_band, consent_data_use, created_at, status)"
    " VALUES (7, 'sms', 'pesan 7', 0.1, 'REVIEW', 1,"
    " '2026-11-08 07:00:00', 'deleted')")
con.execute(
    "INSERT INTO reports (id, channel, text_scrubbed, model_score,"
    " model_band, consent_data_use, created_at, status)"
    " VALUES (8, 'sms', 'pesan 8', 0.1, 'REVIEW', 0,"
    " '2026-11-08 08:00:00', 'pending')")
con.commit()
snap = sk.analytics_snapshot(CFG)
# Dalam alur: #1,#2,#3,#4,#5 consent=1 + #8 consent=0 -> 5/6.
check("R7-S1 consent_rate excludes rejected/deleted (5/6)",
      abs(snap["consent_rate"] - 100.0 * 5 / 6) < 0.01,
      str(snap["consent_rate"]))
check("R7-M4 snapshot disputed = 0", snap["disputed"] == 0,
      str(snap["disputed"]))

# --- R7-S2/N1/N3: DB bersih, tanggal relatif ke hari ini (WITA) ---
SCHEMA = """
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
"""
con2 = sqlite3.connect(":memory:")
con2.row_factory = sqlite3.Row
con2.executescript(SCHEMA)


def fake_turso2(cfg, sql, args=None):
    cur = con2.execute(sql, args or [])
    if cur.description is None:
        con2.commit()
        return []
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


now_utc = datetime.now(timezone.utc).replace(microsecond=0)
wita_today = (now_utc + timedelta(hours=8)).date()
midnight_utc = datetime(wita_today.year, wita_today.month,
                        wita_today.day, tzinfo=timezone.utc) \
    - timedelta(hours=8)


def _fmt(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


# #9: verifikasi pertama +2j, verified_at +10j (verifikasi ulang) -> 2j.
# #10: verified_at SEBELUM created_at (anomali), tanpa label_log -> buang.
# #11: verifikasi pertama +1j, verified_at +5j -> 1j. Rata-rata = 1,5j
# (query lama atas verified_at memberi (10+5-1)/3 = 4,67j).
# #12: 23:30 WITA kemarin; #13: 00:30 WITA hari ini.
for rid, created, verified, label, status in (
        (9, midnight_utc, midnight_utc + timedelta(hours=10),
         "SAH", "verified"),
        (10, midnight_utc, midnight_utc - timedelta(hours=1),
         "SAH", "verified"),
        (11, midnight_utc, midnight_utc + timedelta(hours=5),
         "SMISHING", "verified"),
        (12, midnight_utc - timedelta(minutes=30), None, None, "pending"),
        (13, midnight_utc + timedelta(minutes=30), None, None, "pending")):
    con2.execute(
        "INSERT INTO reports (id, channel, text_scrubbed, model_score,"
        " model_band, consent_data_use, created_at, status, label,"
        " verified_at) VALUES (?, 'sms', ?, 0.3, 'ESKALASI', 1, ?, ?, ?, ?)",
        (rid, f"pesan {rid}", _fmt(created), status, label,
         _fmt(verified) if verified else None))
for rid, first_verified in ((9, midnight_utc + timedelta(hours=2)),
                            (11, midnight_utc + timedelta(hours=1))):
    con2.execute(
        "INSERT INTO label_log (report_id, aksi, label, actor,"
        " created_at) VALUES (?, 'verifikasi', ?, 'verifikator', ?)",
        (rid, "SAH" if rid == 9 else "SMISHING", _fmt(first_verified)))
con2.commit()
sk.turso_execute = fake_turso2
snap2 = sk.analytics_snapshot(CFG)
sk.turso_execute = fake_turso
check("R7-S2+N1 avg_verify_hours = first verification (1.5h)",
      snap2["avg_verify_hours"] is not None
      and abs(snap2["avg_verify_hours"] - 1.5) < 0.01,
      str(snap2["avg_verify_hours"]))
daily2 = dict(snap2["daily14"])
check("R7-N3 00:30 WITA counts as today",
      daily2.get(wita_today.isoformat()) == 4, str(daily2))
check("R7-N3 23:30 WITA counts as yesterday",
      daily2.get((wita_today - timedelta(days=1)).isoformat()) == 1,
      str(daily2))

# --- R7-S5: "berikan/bagikan/kasih/serahkan" jadi S2 (dieksekusi) ---
for verb_phrase in ("Berikan OTP Anda di bca-co-id.com",
                    "Bagikan kode OTP Anda di bca-co-id.com",
                    "Kasih kode OTP Anda di bca-co-id.com",
                    "Serahkan PIN Anda di bca-co-id.com"):
    check(f"R7-S5 S2 catches '{verb_phrase.split()[0]} …'",
          evaluate_rules(verb_phrase)["triggered"] is True,
          str(evaluate_rules(verb_phrase)["strong"]))
r = evaluate_rules("JANGAN bagikan kode OTP ini kepada siapa pun")
check("R7-S5 'JANGAN bagikan' stays S2 False",
      r["strong"]["S2"] is False, str(r["strong"]))
check("R7-S5 'JANGAN bagikan' still calm",
      evaluate_calm("JANGAN bagikan kode OTP ini kepada siapa pun")[0]
      is True)
r = evaluate_rules("JANGAN berikan kode OTP ini kepada siapa pun")
check("R7-S5 'JANGAN berikan' stays S2 False",
      r["strong"]["S2"] is False, str(r["strong"]))

# --- R7-S9/N2: narasi journey jujur (struktural) ---
check("R7-S9 no causal 'sembuh'", "sembuh" not in JRN_SRC)
check("R7-S9 no 'membuat gerbang'", "membuat gerbang" not in JRN_SRC)
check("R7-S9 honest wording present", "bukan bukti sebabnya" in JRN_SRC)
check("R7-N2 docstring three-status",
      "kuning: tidak" in JRN_SRC and "gagal jelas" in JRN_SRC)
check("R7-N2 no binary docstring",
      "hijau bila melewati gerbangnya" not in JRN_SRC)

# --- R7-S10: kolom Catatan ambang di panel evaluasi (struktural) ---
# app.py tidak diimpor (menjalankan Streamlit); yang dikunci adalah
# jalurnya: baris evaluasi membawa penanda + tabel menampilkannya.
check("R7-S10 eval rows carry boundary note",
      '"Catatan ambang": _score_boundary_note(' in APP_SRC)
check("R7-S10 eval table shows boundary column",
      '"Catatan ambang": r.get("Catatan ambang", "—")' in APP_SRC)
check("R7-S10 app version v6.1.5", 'APP_VERSION = "v6.1.5"' in APP_SRC)

print()
print("FAILURES:", fails if fails else "none — ALL PASS")
sys.exit(1 if fails else 0)
