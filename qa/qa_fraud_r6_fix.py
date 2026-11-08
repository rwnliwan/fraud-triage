"""QA eksekusi fix ronde 6 + ronde 7 + ronde 8 Fraud Triage (v6.1.6)
— M1/M2/S5 (R6) + M1–M4/S1–S10/N1–N3 (R7) + M1–M9/S1–S7/N1–N5 (R8)
+ susulan v6.1.6 (9 Nov 2026, tanpa naik versi): normalisasi kode
lacak + gap G4 (draf publik vs kode) + G5 (verify_report atomik) +
G6 (bukti gerbang) + G7 (sensus Turnstile).

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
import re
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
    sender_hash TEXT, text_hash TEXT, enrichment TEXT,
    via_ocr INTEGER NOT NULL DEFAULT 0);
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
FAIL_LOG = {"on": False}


def fake_batch_main(cfg, statements):
    """Simulasi turso_batch atas `con` (seksi awal guard): satu
    transaksi SQLite; satu langkah gagal -> SEMUA dibatalkan. Dipakai
    verify_report sejak gap G5 ronde 8 — tanpa stub ini seksi awal
    akan memanggil turso_batch asli (HTTP ke Turso)."""
    try:
        out = []
        for sql, args in statements:
            if FAIL_LOG["on"] and "INSERT INTO label_log" in sql:
                raise RuntimeError("simulasi: label_log gagal tulis")
            cur = con.execute(sql, args or [])
            if cur.description is None:
                out.append([])
            else:
                cols = [d[0] for d in cur.description]
                out.append([dict(zip(cols, r)) for r in cur.fetchall()])
        con.commit()
        return out
    except Exception:
        con.rollback()
        raise


sk.turso_batch = fake_batch_main
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

# --- Gap G5 ronde 8: verify_report atomik + gagal-jujur ---
# #2 sudah terverifikasi (tidak pending): verifikasi ulang langsung
# ke verify_report (tanpa unverify dulu) WAJIB gagal-jujur — bukan
# sukses diam-diam tanpa jejak.
_log_before = fake_turso(CFG, "SELECT COUNT(*) AS n FROM label_log")[0]["n"]
try:
    sk.verify_report(CFG, 2, "SAH", "blokir_akun", False)
    _g5_raise = False
except RuntimeError:
    _g5_raise = True
_log_after = fake_turso(CFG, "SELECT COUNT(*) AS n FROM label_log")[0]["n"]
check("R8-G5 verify atas laporan tak-pending -> RuntimeError",
      _g5_raise is True, str(_g5_raise))
check("R8-G5 verify gagal tidak menulis jejak palsu",
      _log_after == _log_before, f"{_log_before} -> {_log_after}")
# Kegagalan tulis log di tengah batch -> exception + baris tetap pending.
FAIL_LOG["on"] = True
try:
    sk.verify_report(CFG, 3, "SMISHING", "undian", False)
    _g5_logfail = False
except RuntimeError:
    _g5_logfail = True
FAIL_LOG["on"] = False
_row3 = fake_turso(CFG, "SELECT status FROM reports WHERE id = 3")[0]
check("R8-G5 gagal tulis log -> verify raise (bukan sukses)",
      _g5_logfail is True, str(_g5_logfail))
check("R8-G5 gagal tulis log -> baris tetap pending (batch batal)",
      _row3["status"] == "pending", str(_row3))

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
# Ronde 8, M2: "disepakati" mensyaratkan TIDAK ADA tinjauan berbeda
# yang masih terbuka — satu tinjauan cocok saja belum cukup bila ada
# tinjauan berbeda yang menggantung.
check("S5 gold_count = 1 sesudah cocok saja",
      sk.gold_count(CFG) == 1, str(sk.gold_count(CFG)))
res = sk.second_review(CFG, 2, "SAH", actor="peninjau-2")
check("S5 second_review beda", res == "beda", res)
check("S5 gold_count = 0 sesudah beda (sengketa terbuka)",
      sk.gold_count(CFG) == 0, str(sk.gold_count(CFG)))
check("S5 disputed_count = 1 sesudah beda",
      sk.disputed_count(CFG) == 1, str(sk.disputed_count(CFG)))
row = fake_turso(CFG, "SELECT label FROM reports WHERE id = 2")[0]
check("S5 label unchanged by second review", row["label"] == "SMISHING")
actors = fake_turso(CFG, "SELECT DISTINCT actor FROM label_log WHERE aksi = 'tinjauan_kedua'")
check("S5 actor peninjau-2 logged", [r["actor"] for r in actors] == ["peninjau-2"], str(actors))
check("S5 gold_count = 0 (sengketa #2 masih terbuka)", sk.gold_count(CFG) == 0, str(sk.gold_count(CFG)))

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
# Ronde 8, M2: #2 masih bersengketa terbuka (cocok + beda), jadi emas
# = 0 pada titik ini — bukan 1 seperti ekspektasi R7 lama (yang
# mengunci definisi emas yang cacat: cocok DAN beda sekaligus).
check("R7-M4 gold baseline = 0 (#2 bersengketa terbuka)",
      gold_before == 0, str(gold_before))
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
check("R7-M4 gold still 0 after adjudicating #5 (#2 still disputed)",
      sk.gold_count(CFG) == gold_before, str(sk.gold_count(CFG)))
check("R7-M4 adjudicate #2 closes the R6 leftover too",
      sk.adjudicate_report(CFG, 2, "pertahankan",
                           actor="verifikator") is True)
check("R7-M4 disputed_count = 0 after adjudicating #2",
      sk.disputed_count(CFG) == 0, str(sk.disputed_count(CFG)))
log5 = fake_turso(CFG, "SELECT aksi, label FROM label_log "
                       "WHERE report_id = 5")
check("R7-M4 adjudikasi logged as adjudikasi/pertahankan",
      ("adjudikasi", "pertahankan") in [(r["aksi"], r["label"])
                                        for r in log5], str(log5))
check("R7-M4 second adjudicate returns False",
      sk.adjudicate_report(CFG, 5, "diragukan") is False)
check("R7-M4 no 'paling tepercaya' claim left",
      "bahan korpus paling tepercaya" not in SRC)
# Ronde 8, M2: sesudah sengketa #2 diputuskan 'pertahankan', tinjauan
# cocoknya kembali dihitung — emas naik 0 -> 1 (bukan tetap 0).
check("R7-M4 gold = 1 after #2 dispute resolved",
      sk.gold_count(CFG) == 1, str(sk.gold_count(CFG)))

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
    sender_hash TEXT, text_hash TEXT, enrichment TEXT,
    via_ocr INTEGER NOT NULL DEFAULT 0);
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
check("R7-S10 app version v6.1.6", 'APP_VERSION = "v6.1.6"' in APP_SRC)

# ==================== RONDE 8 (v6.1.6) ====================
# Guard KELAS (GG-11..GG-13, GG-16 + kelas baru §6b enumerasi).
# Aturan Septian 2026-11-09 00:53 (self-learning loop permanen):
# tiap guard mengunci POLA UMUM kelas kesalahannya, bukan string /
# kasus spesifik yang muncul kali ini. Klasifikasi per guard ada di
# komentar "KELAS" / "KASUS" di bawah; yang hanya KASUS dicatat
# keterbatasannya di akhir seksi + laporan fix.
#
# Skema fixture R8 dibangun DARI berkas migrasi repo (0001+0002) —
# guard sekaligus mengunci bahwa migrasi bisa dieksekusi dan view
# hasil migrasi sama dengan view yang dipakai pengujian (R8 S3).
# Skenario pra-migrasi (kolom baru belum ada) diuji terpisah dengan
# fixture 0001-saja: kode WAJIB menurun grasi atau gagal JUJUR,
# tidak pernah diam-diam.
import inspect
import json as _json
from types import SimpleNamespace as _NS

MIG_DIR = REPO / "migrations"
MIG_FILES = sorted(p.name for p in MIG_DIR.glob("*.sql"))
check("R8-S3 migrasi ada + berurutan",
      MIG_FILES == ["0001_schema_baseline.sql",
                    "0002_r8_corpus_track_ocr.sql"], str(MIG_FILES))
MIG_SQL = "".join((MIG_DIR / n).read_text(encoding="utf-8") + "\n"
                  for n in MIG_FILES)


def _fresh_con8(sql=MIG_SQL):
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(sql)
    return c


try:
    con8 = _fresh_con8()
    _mig_ok, _mig_err = True, ""
except Exception as exc:  # noqa: BLE001 — bukti guard, bukan logika app
    con8, _mig_ok, _mig_err = None, False, str(exc)
check("R8-S3 migrasi 0001+0002 tereksekusi di SQLite", _mig_ok, _mig_err)


def _norm_sql(s):
    return re.sub(r"\s+", " ", s).strip().lower()


if _mig_ok:
    _mig_view = con8.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'view' "
        "AND name = 'corpus_export'").fetchone()[0]
    check("R8-S3 view hasil migrasi syarat corpus_excluded=0",
          "corpus_excluded = 0" in _norm_sql(_mig_view), _mig_view)
    check("R8-S3 view hasil migrasi syarat EXISTS consent_log",
          "exists (select 1 from consent_log" in _norm_sql(_mig_view))
    _cols = {r[1] for r in con8.execute("PRAGMA table_info(reports)")}
    check("R8-S3 kolom corpus_excluded/track_code/via_ocr ada",
          {"corpus_excluded", "track_code", "via_ocr"} <= _cols,
          str(sorted(_cols)))
    _lcols = {r[1] for r in con8.execute("PRAGMA table_info(label_log)")}
    check("R8-S3 kolom putusan ada di label_log",
          "putusan" in _lcols, str(sorted(_lcols)))
    _docs = (REPO / "docs" / "corpus_export.md").read_text(
        encoding="utf-8")
    check("R8-S3 docs tak lagi klaim view hanya hidup di Turso",
          "hanya hidup di Turso" not in _docs
          and "tidak ada migrasi SQL di repo" not in _docs)
    check("R8-S3 docs rujuk migrasi 0002",
          "0002" in _docs and "corpus_excluded" in _docs)


def fake8(cfg, sql, args=None):
    if FAIL_CONSENT["on"] and "INSERT INTO consent_log" in sql:
        raise RuntimeError("simulasi: consent_log gagal tulis")
    cur = con8.execute(sql, args or [])
    if cur.description is None:
        con8.commit()
        return []
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


FAIL_CONSENT = {"on": False}


def fake_batch(cfg, statements):
    """Simulasi turso_batch: satu transaksi SQLite; satu langkah gagal
    -> SEMUA dibatalkan (semantik batch pipeline yang diasumsikan;
    bentuk wire + error SUDAH diverifikasi ke Turso live read-only)."""
    try:
        out = []
        for sql, args in statements:
            if FAIL_CONSENT["on"] and "INSERT INTO consent_log" in sql:
                raise RuntimeError("simulasi: consent_log gagal tulis")
            cur = con8.execute(sql, args or [])
            if cur.description is None:
                out.append([])
            else:
                cols = [d[0] for d in cur.description]
                out.append([dict(zip(cols, r)) for r in cur.fetchall()])
        con8.commit()
        return out
    except Exception:
        con8.rollback()
        raise


def _safe_call(fn, *a, **k):
    """Panggil fungsi yang mungkin belum ada (pra-fix) tanpa
    menggagalkan seluruh guard: kembalikan ("ok", hasil) atau
    ("error", pesan). Check yang memakai ini GAGAL pra-fix (red)
    dan LOLOS pasca-fix (green) — sesuai urutan QA-dulu."""
    try:
        return ("ok", fn(*a, **k))
    except Exception as exc:  # noqa: BLE001 — bukti guard
        return ("error", f"{type(exc).__name__}: {exc}")


def _gate(*a, **k):
    """check_storage_gate bila ada; pra-fix kembalikan (None, alasan)
    supaya tiap check gate GAGAL bersih (bukan lolos vakum / crash)."""
    fn = getattr(sk, "check_storage_gate", None)
    if fn is None:
        return None, "check_storage_gate belum ada (pra-fix)"
    try:
        return fn(*a, **k)
    except Exception as exc:  # noqa: BLE001 — bukti guard
        return None, f"gate crash: {exc}"


def _fetch_by_code(code):
    fn = getattr(sk, "fetch_report_by_code", None)
    if fn is None:
        return None
    try:
        return fn(CFG, code)
    except Exception:  # noqa: BLE001 — bukti guard
        return None


sk.turso_execute = fake8
sk.turso_batch = fake_batch
if hasattr(sk, "_R8_COLS_CACHE"):
    sk._R8_COLS_CACHE.clear()

# --- GG-11 (KELAS): scrubber URL tidak lengkap -------------------------
# Pola umum: URL berbentuk apa pun (skema apa pun, TLD apa pun, ekor
# apa pun: path/query/fragment/IP) WAJIB kehilangan ekornya; host
# dipertahankan sebagai sinyal. Diuji atas matriks TLD (termasuk TLD
# inventaris .zzq/.foo yang TIDAK ADA di allowlist mana pun — guard
# ini GAGAL bila matcher kembali memakai allowlist) + IPv4.
_TLDS_ANY = ["com", "net", "org", "id", "co", "io", "dev", "ai", "gg",
             "xyz", "cc", "app", "me", "ly", "shop", "store", "online",
             "site", "top", "click", "link", "live", "fun", "buzz",
             "club", "vip", "icu", "rest", "best", "one", "space",
             "website", "work", "today", "gq", "tk", "ml", "ga", "cf",
             "foo", "zzq", "technology", "bank", "crypto"]
_bad11 = []
for _tld in _TLDS_ANY:
    for _text, _exp in (
            (f"cek https://contoh.{_tld}/jalur?token=abc#frag",
             f"cek [tautan: contoh.{_tld}]"),
            (f"cek https://contoh.{_tld}#token=rahasia",
             f"cek [tautan: contoh.{_tld}]"),
            (f"cek https://contoh.{_tld}?token=abc123",
             f"cek [tautan: contoh.{_tld}]"),
            (f"cek http://contoh.{_tld}/a/b?x=1#y",
             f"cek [tautan: contoh.{_tld}]"),
            (f"cek www.contoh.{_tld}/a?x=1#y",
             f"cek [tautan: contoh.{_tld}]"),
            (f"kunjungi contoh.{_tld}/jalur?token=x#frag",
             f"kunjungi [tautan: contoh.{_tld}]"),
            (f"kunjungi contoh.{_tld}#frag",
             f"kunjungi [tautan: contoh.{_tld}]")):
        _got, _ = scrub(_text)
        if _got != _exp:
            _bad11.append((_text, _got))
check("R8-M1/GG-11 scrub: TLD apa pun + ekor apa pun -> host saja",
      not _bad11, str(_bad11[:3]))
check("R8-M1/GG-11 scrub IPv4 ber-token",
      scrub("cek https://192.168.0.5/login?token=x")[0]
      == "cek [tautan: 192.168.0.5]",
      scrub("cek https://192.168.0.5/login?token=x")[0])
check("R8-M1/GG-11 scrub fragment + tanda baca akhir dipertahankan",
      scrub("cek https://example.com#token=rahasia.")[0]
      == "cek [tautan: example.com].")
check("R8-M1/GG-11 tidak ada lagi allowlist _TLDS di scrubber",
      "_TLDS" not in SCRUB_SRC if (SCRUB_SRC := (
          REPO / "scrubber.py").read_text(encoding="utf-8")) else False)
_bad11n = []
for _text, _exp in (
        ("saldo Rp50.000.000 cair", "saldo Rp50.000.000 cair"),
        ("hub 0812-3456-7890 ya", "hub [NOMOR] ya"),
        ("email saya a@b.com ya", "email saya [EMAIL] ya"),
        ("Jakarta. Besok saya pergi", "Jakarta. Besok saya pergi"),
        ("nilai 3.14 dan 2.0 saja", "nilai 3.14 dan 2.0 saja")):
    _got, _ = scrub(_text)
    if _got != _exp:
        _bad11n.append((_text, _got))
check("R8-M1/GG-11 negatif: uang/telepon/email/kalimat tak tersentuh",
      not _bad11n, str(_bad11n))
_bad_s1 = [t for t in _TLDS_ANY
           if not evaluate_rules(
               f"klik https://contoh.{t}/jalur?x=1")["strong"]["S1"]]
check("R8-M1/GG-11 rules S1 kenali TLD apa pun (skema)",
      not _bad_s1, str(_bad_s1))
from rules import _extract_domains as _ex_dom
check("R8-M1/GG-11 _extract_domains buang fragment",
      _ex_dom("klik https://foo.ai/a?x=1#y dan bca.co.id/z") ==
      ["foo.ai", "bca.co.id"], str(_ex_dom(
          "klik https://foo.ai/a?x=1#y dan bca.co.id/z")))

# --- GG-12 (KELAS): sinyal mesin bocor pra-label, pindah lokasi -------
# Pola umum: TIDAK ADA permukaan pra-label yang boleh merender
# band/skor/saran mesin — diuji (a) dieksekusi atas snapshot, (b)
# pindai segmen pra-label tab Verifikasi, (c) sensus SEMUA kemunculan
# pengenal band/skor di repo terhadap allowlist fungsi pasca-label /
# milik warga sendiri. Keterbatasan: pengenal BARU (mis. rename jadi
# risk_band) lolos sensus — mitigasi: frasa "sinyal mesin pra-label"
# masuk prompt review ronde berikut.
con8.execute(
    "INSERT INTO reports (channel, text_scrubbed, model_score,"
    " model_band, consent_data_use, created_at, status)"
    " VALUES ('sms', 'pesan pending', 0.99, 'ESKALASI', 1,"
    " datetime('now'), 'pending')")
con8.commit()
snap8 = sk.analytics_snapshot(CFG)
check("R8-M3/GG-12 snapshot band kosong bila hanya pending",
      snap8["band"] == {}, str(snap8["band"]))
con8.execute(
    "INSERT INTO reports (channel, text_scrubbed, model_score,"
    " model_band, consent_data_use, created_at, status, label)"
    " VALUES ('sms', 'pesan verif', 0.1, 'AMAN', 1, datetime('now'),"
    " 'verified', 'SAH')")
con8.execute(
    "INSERT INTO consent_log (report_id, consent_version,"
    " consent_text_hash) VALUES (2, 'v1', 'h')")
con8.commit()
snap8 = sk.analytics_snapshot(CFG)
check("R8-M3/GG-12 snapshot band hanya dari terverifikasi",
      snap8["band"] == {"AMAN": 1}, str(snap8["band"]))
check("R8-M3/GG-12 corpus_by_label hanya terverifikasi",
      snap8["corpus_by_label"] == {"SAH": 1},
      str(snap8["corpus_by_label"]))
_ana = SRC.split("def analytics_snapshot")[1].split(
    "def _render_analytics")[0]
_band_q = _ana.split('snap["band"]')[1].split("GROUP BY model_band")[0]
check("R8-M3/GG-12 kueri band snapshot filter status verified",
      "verified" in _band_q, _band_q)
_pend = SRC.split("# Pelabelan BUTA", 1)[1].split(
    "# Antrean triase", 1)[0]
_tri = SRC.split("# Antrean triase", 1)[1].split(
    "Terverifikasi terakhir", 1)[0]
_admin_pre = SRC.split("def render_admin_tab")[1].split(
    "# Pelabelan BUTA", 1)[0]
for _seg_name, _seg in (("kartu pending", _pend),
                        ("expander triase", _tri),
                        ("tab Verifikasi pra-antrean", _admin_pre)):
    for _ident in ("model_band", "model_score", "suggest_label",
                   "fetch_pending_triage"):
        check(f"R8-GG-12 segmen {_seg_name} tanpa '{_ident}'",
              _ident not in _seg)
check("R8-GG-12 fetch_pending tanpa kolom skor/band/sinyal",
      "model_score" not in _SRC_FP if (_SRC_FP := SRC.split(
          "def fetch_pending(cfg")[1].split(
          "def fetch_pending_triage")[0].split('"""')[-1]) else False)
check("R8-GG-12 fetch_pending tanpa rules_fired",
      "rules_fired" not in _SRC_FP)
for _fname, _allow in (
        ("siskamling.py", {"submit_report", "suggest_label",
                           "analytics_snapshot", "_render_analytics",
                           "render_gallery_tab", "render_admin_tab",
                           "fetch_pending_triage", "fetch_gallery",
                           "fetch_verified", "fetch_pending"}),
        ("app.py", {"result_card_html"})):
    _lines = (REPO / _fname).read_text(encoding="utf-8").splitlines()
    _bad12 = []
    for _i, _ln in enumerate(_lines):
        if _ln.strip().startswith("#"):
            continue  # komentar modul (mis. peta BAND_STORE) bukan render
        if re.search(r"model_band|model_score|suggest_label|"
                     r"fetch_pending_triage", _ln):
            _fn = "<module>"
            for _j in range(_i, -1, -1):
                _m = re.match(r"def (\w+)\(", _lines[_j])
                if _m:
                    _fn = _m.group(1)
                    break
            if _fn not in _allow:
                _bad12.append((_i + 1, _fn, _ln.strip()[:60]))
    check(f"R8-GG-12 sensus band/skor {_fname} dalam allowlist",
          not _bad12, str(_bad12[:3]))

# --- GG-13 (KELAS): efek parsial dilaporkan lengkap --------------------
# Pola umum: putusan/penyimpanan yang diklaim selesai WAJIB berefek
# penuh sampai ke korpus — diuji atas EFEK (isi corpus_export +
# hitungan emas/sengketa), bukan atas ada-tidaknya pemanggilan.
con8.execute(
    "INSERT INTO reports (id, channel, text_scrubbed, model_score,"
    " model_band, consent_data_use, created_at, status, label)"
    " VALUES (21, 'sms', 'pesan 21', 0.9, 'ESKALASI', 1,"
    " '2026-11-08 01:00:00', 'verified', 'SMISHING')")
con8.execute(
    "INSERT INTO consent_log (report_id, consent_version,"
    " consent_text_hash) VALUES (21, 'v1', 'h')")
con8.execute("INSERT INTO label_log (report_id, aksi, label)"
             " VALUES (21, 'verifikasi', 'SMISHING')")
con8.execute("INSERT INTO label_log (report_id, aksi, label)"
             " VALUES (21, 'tinjauan_kedua', 'SAH')")
con8.commit()
check("R8-M2/GG-13 disputed=1 pra-adjudikasi",
      sk.disputed_count(CFG) == 1, str(sk.disputed_count(CFG)))
check("R8-M2/GG-13 di korpus pra-adjudikasi",
      len(fake8(CFG, "SELECT * FROM corpus_export WHERE "
                     "text_scrubbed = 'pesan 21'")) == 1)
check("R8-M2/GG-13 adjudikasi diragukan True",
      sk.adjudicate_report(CFG, 21, "diragukan",
                           actor="verifikator") is True)
check("R8-M2/GG-13 disputed=0 pasca-adjudikasi",
      sk.disputed_count(CFG) == 0, str(sk.disputed_count(CFG)))
check("R8-M2/GG-13 KELUAR dari corpus_export pasca-diragukan",
      fake8(CFG, "SELECT * FROM corpus_export WHERE "
                 "text_scrubbed = 'pesan 21'") == [])
check("R8-M2/GG-13 gold=0 pasca-diragukan",
      sk.gold_count(CFG) == 0, str(sk.gold_count(CFG)))
check("R8-S1/GG-13 putusan di kolom putusan juga",
      fake8(CFG, "SELECT putusan FROM label_log WHERE aksi = "
                 "'adjudikasi' AND report_id = 21")[0]["putusan"]
      == "diragukan")
con8.execute("INSERT INTO label_log (report_id, aksi, label)"
             " VALUES (21, 'tinjauan_kedua', 'SAH')")
con8.commit()
check("R8-S1/GG-13 tinjauan beda baru buka antrean lagi",
      sk.disputed_count(CFG) == 1, str(sk.disputed_count(CFG)))
check("R8-S1/GG-13 adjudikasi kedua mungkin",
      sk.adjudicate_report(CFG, 21, "pertahankan",
                           actor="verifikator") is True)
check("R8-S1/GG-13 disputed=0 sesudah adjudikasi kedua",
      sk.disputed_count(CFG) == 0, str(sk.disputed_count(CFG)))
con8.execute(
    "INSERT INTO reports (id, channel, text_scrubbed, model_score,"
    " model_band, consent_data_use, created_at, status, label)"
    " VALUES (22, 'sms', 'pesan 22', 0.9, 'ESKALASI', 1,"
    " '2026-11-08 02:00:00', 'verified', 'SMISHING')")
con8.execute("INSERT INTO label_log (report_id, aksi, label)"
             " VALUES (22, 'verifikasi', 'SMISHING')")
con8.execute("INSERT INTO label_log (report_id, aksi, label)"
             " VALUES (22, 'tinjauan_kedua', 'SMISHING')")
con8.execute("INSERT INTO label_log (report_id, aksi, label)"
             " VALUES (22, 'tinjauan_kedua', 'SAH')")
con8.commit()
check("R8-M2/GG-13 cocok+beda tanpa adjudikasi: gold=0 disputed=1",
      sk.gold_count(CFG) == 0 and sk.disputed_count(CFG) == 1,
      f"gold={sk.gold_count(CFG)} disputed={sk.disputed_count(CFG)}")
# M4: batch atomik (sukses + gagal) atas con8.
_n_before = fake8(CFG, "SELECT COUNT(*) AS n FROM reports")[0]["n"]
_st, _res = _safe_call(
    sk.submit_report,
    CFG, channel="sms", raw_text="pesan konsen ok",
    sender_raw=None, consent_data_use=True, score=0.5,
    band_final="REVIEW ANALIS", rules_fired=[])
_rid = _res[0] if _st == "ok" and isinstance(_res, tuple) else None
_code = _res[2] if _st == "ok" and isinstance(_res, tuple) \
    and len(_res) == 3 else None
check("R8-M4/GG-13 submit consent kembalikan id+kode",
      _st == "ok" and isinstance(_rid, int) and isinstance(_code, str)
      and len(_code) == 8, f"st={_st} res={_res}")
check("R8-M4/GG-13 consent_log tertulis untuk submit consent",
      _rid is not None and len(fake8(
          CFG, "SELECT * FROM consent_log WHERE report_id = ?",
          [_rid])) == 1)
check("R8-M4/GG-13 baris consent masuk korpus bila terverifikasi",
      _rid is not None and fake8(
          CFG, "SELECT consent_data_use FROM reports WHERE id = ?",
          [_rid])[0]["consent_data_use"] == 1)
FAIL_CONSENT["on"] = True
_st2, _res2 = _safe_call(
    sk.submit_report,
    CFG, channel="sms", raw_text="pesan konsen gagal",
    sender_raw=None, consent_data_use=True, score=0.5,
    band_final="REVIEW ANALIS", rules_fired=[])
_raised = _st2 == "error"
FAIL_CONSENT["on"] = False
_n_after = fake8(CFG, "SELECT COUNT(*) AS n FROM reports")[0]["n"]
check("R8-M4/GG-13 consent_log gagal -> submit raise + tanpa yatim",
      _raised and _n_after == _n_before + 1,
      f"raised={_raised} before={_n_before} after={_n_after}")

# --- GG-16 (KELAS): fail-open / kegagalan diam-diam --------------------
# Pola umum: tiap jalur kegagalan intake WAJIB gagal-ke-tertutup atau
# berteriak — diuji dieksekusi lewat gerbang simpan murni
# (check_storage_gate) + struktural atas fallback lama + sensus
# handler except. Keterbatasan: sensus hanya tripwire hitungan —
# fail-open BARU di dalam handler yang sudah ada tidak tertangkap
# hitungan; mitigasi: tiap handler baru WAJIB didaftarkan di guard.
# Catatan: pop("sk_ts_token") di _turnstile_passed adalah higiene
# (membersihkan kunci sesi lama), BUKAN cache — cache = membaca atau
# menulis session_state["sk_ts_token"] sebagai token tersimpan.
check("R8-M5/GG-16 tidak ada lagi cache token sesi",
      'session_state["sk_ts_token"]' not in SRC
      and "sk_ts_token =" not in SRC)
check("R8-M6/GG-16 fallback kill-switch fail-open hilang",
      "intake_is_open, queue_full, ts_active = True, False, False"
      not in SRC)
check("R8-M6/GG-16 ada jalur intake_unknown",
      "intake_unknown" in SRC)
check("R8-M7/GG-16 fallback can_store=True hilang",
      "can_store = True  # gagal cek batas" not in SRC)
check("R8-M8/GG-16 s_hash=None diam-diam hilang",
      "except Exception:\n                    s_hash = None" not in SRC)
check("R8-S5 angka 300 vs 500 beralasan di komentar",
      "pemutus antrean" in SRC and "batas intake harian" in SRC)
check("R8-S5 MAX_SUBMITS_PER_SESSION ada",
      "MAX_SUBMITS_PER_SESSION" in SRC)
sk.st = _NS(session_state={})
_calls = {"n": 0}


def _fake_verify(cfg, token):
    _calls["n"] += 1
    return True


sk.verify_turnstile = _fake_verify
check("R8-M5/GG-16 siteverify dipanggil TIAP submit (tanpa cache)",
      sk._turnstile_passed(CFG, "tok-1")
      and sk._turnstile_passed(CFG, "tok-1")
      and _calls["n"] == 2, f"calls={_calls['n']}")
check("R8-M5/GG-16 token kosong tetap False",
      sk._turnstile_passed(CFG, None) is False)

# Fixture segar (0001+0002) untuk gerbang + batas WITA — hitungan
# bersih tanpa baris con8 di atas.
con8b = _fresh_con8()
if hasattr(sk, "_R8_COLS_CACHE"): sk._R8_COLS_CACHE.clear()


def fake8b(cfg, sql, args=None):
    cur = con8b.execute(sql, args or [])
    if cur.description is None:
        con8b.commit()
        return []
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


sk.turso_execute = fake8b
sk.turso_batch = fake_batch  # menulis ke con8 — TIDAK dipakai di sini
CFG_SALT = {"salt": "uji-salt"}
_can, _rsn = _gate(
    CFG_SALT, db_ready=True, intake_open=True, queue_full=False,
    sender_raw=None, raw_text="pesan unik gate-1", session_submits=0)
check("R8-GG-16 gate lolos bila semua sehat", _can is True, str(_rsn))
_can, _rsn = _gate(
    CFG_SALT, db_ready=True, intake_open=False, queue_full=False,
    sender_raw=None, raw_text="pesan unik gate-2", session_submits=0)
check("R8-M6/GG-16 intake tertutup -> gate False", _can is False)
_can, _rsn = _gate(
    CFG_SALT, db_ready=True, intake_open=False, queue_full=False,
    sender_raw=None, raw_text="pesan unik gate-3", session_submits=0,
    intake_unknown=True)
check("R8-M6/GG-16 status intake tak diketahui -> False + alasan",
      _can is False and "tidak dapat dipastikan" in (_rsn or ""),
      str(_rsn))
_can, _rsn = _gate(
    CFG_SALT, db_ready=True, intake_open=True, queue_full=True,
    sender_raw=None, raw_text="pesan unik gate-4", session_submits=0)
check("R8-M6/GG-16 antrean penuh -> gate False", _can is False)


def _fake8b_raise_counts(cfg, sql, args=None):
    if "COUNT(*)" in sql:
        raise RuntimeError("simulasi: DB baca gagal")
    return fake8b(cfg, sql, args)


sk.turso_execute = _fake8b_raise_counts
_can, _rsn = _gate(
    CFG_SALT, db_ready=True, intake_open=True, queue_full=False,
    sender_raw=None, raw_text="pesan unik gate-5", session_submits=0)
check("R8-M7/GG-16 gagal cek batas -> gate False (bukan True)",
      _can is False, str(_rsn))
sk.turso_execute = fake8b
_can, _rsn = _gate(
    {}, db_ready=True, intake_open=True, queue_full=False,
    sender_raw="081234567890", raw_text="pesan unik gate-6",
    session_submits=0)
check("R8-M8/GG-16 hash gagal + sender terisi -> gate False",
      _can is False, str(_rsn))
_can, _rsn = _gate(
    {}, db_ready=True, intake_open=True, queue_full=False,
    sender_raw=None, raw_text="pesan unik gate-7", session_submits=0)
check("R8-M8/GG-16 anonim tanpa salt tetap lolos (batas global)",
      _can is True, str(_rsn))
_can, _rsn = _gate(
    CFG_SALT, db_ready=True, intake_open=True, queue_full=False,
    sender_raw=None, raw_text="pesan unik gate-8",
    session_submits=10)
check("R8-S5 gate tolak submit ke-11 dalam satu sesi",
      _can is False, str(_rsn))
# Batas per-pengirim: 9 lolos, 10 tertahan.
_h = __import__("scrubber").hash_sender("081234567890", "uji-salt")
for _i in range(9):
    con8b.execute(
        "INSERT INTO reports (channel, text_scrubbed, sender_hash,"
        " created_at) VALUES ('sms', ?, ?, datetime('now'))",
        (f"pesan batas {_i}", _h))
con8b.commit()
_can, _rsn = _gate(
    CFG_SALT, db_ready=True, intake_open=True, queue_full=False,
    sender_raw="081234567890", raw_text="pesan unik gate-9",
    session_submits=0)
check("R8-GG-16 9 laporan pengirim -> gate lolos", _can is True,
      str(_rsn))
con8b.execute(
    "INSERT INTO reports (channel, text_scrubbed, sender_hash,"
    " created_at) VALUES ('sms', 'pesan batas 9', ?,"
    " datetime('now'))", (_h,))
con8b.commit()
_can, _rsn = _gate(
    CFG_SALT, db_ready=True, intake_open=True, queue_full=False,
    sender_raw="081234567890", raw_text="pesan unik gate-10",
    session_submits=0)
check("R8-GG-16 10 laporan pengirim -> gate False", _can is False,
      str(_rsn))
# Sensus handler except: tripwire — handler baru WAJIB didaftarkan.
# Audit 2026-11-09 (33 handler): semua fail-closed/jujur/UI-only —
# gate (3x False), schema-probe (2x ok=False), Turnstile (False),
# config (None -> db_ready False), adjudikasi batch (False),
# submit/lacak/galeri/analitik/antrean (pesan error + return/None),
# metrik (0/[]), enrichment/OCR (None/"unavailable", best-effort).
# Audit susulan 2026-11-09 (36 handler, +3): verify_report jalur
# label-beku + verifikasi-pertama (2x DELETE kompensasi jejak hantu —
# gagal hapus DIBAWA dalam RuntimeError, bukan ditelan) dan pemanggil
# UI tombol Verifikasi (1x st.error + tanpa rerun, gagal-jujur).
# Keterbatasan: sensus hanya hitungan — fail-open BARU di dalam
# handler yang sudah ada tidak tertangkap; tiap handler baru WAJIB
# didaftarkan di sini + alasan fail-closed-nya.
_n_except = SRC.count("except Exception")
check("R8-GG-16 sensus except-Exception (tripwire hitungan)",
      _n_except == 36, f"count={_n_except} (daftarkan handler baru)")

# --- S4 (KELAS): batas harian UTC vs WITA ------------------------------
# Pola umum: "per hari" = hari WITA di SEMUA penghitung batas — diuji
# dua arah terhadap batas (baris lama WITA-kemarin tidak terhitung,
# baris saat ini terhitung) dengan oracle yang dihitung di Python
# (bukan tanggal-hardcode, supaya guard lolos jam berapa pun).
_now_utc = datetime.now(timezone.utc).replace(microsecond=0)
_mid_utc = _now_utc.replace(hour=0, minute=0, second=0)
_now_wita = (_now_utc + timedelta(hours=8)).date()


def _wita_date(txt):
    return (datetime.strptime(txt, "%Y-%m-%d %H:%M:%S").replace(
        tzinfo=timezone.utc) + timedelta(hours=8)).date()


_rows4 = (
    ("wita-a", (_mid_utc - timedelta(minutes=30)).strftime(
        "%Y-%m-%d %H:%M:%S")),   # 23:30 UTC kemarin = 07:30 WITA hari ini
    ("wita-b", (_mid_utc - timedelta(hours=9)).strftime(
        "%Y-%m-%d %H:%M:%S")),   # 15:00 UTC kemarin = 23:00 WITA kemarin
    ("wita-c", _now_utc.strftime("%Y-%m-%d %H:%M:%S")),
    # 00:30 UTC hari ini = 08:30 WITA hari ini. Baris A dan D ini
    # SALING MELENGKAPI jam berapa pun guard dijalankan: pagi UTC
    # (WITA = hari UTC yang sama) A yang membedakan UTC vs WITA,
    # sore UTC (WITA = besok) D yang membedakan — salah satu SELALU
    # gagal pada kode UTC-lama, dan keduanya lolos pada kode WITA.
    ("wita-d", (_mid_utc + timedelta(minutes=30)).strftime(
        "%Y-%m-%d %H:%M:%S")))
for _tag, _ts in _rows4:
    con8b.execute(
        "INSERT INTO reports (channel, text_scrubbed, sender_hash,"
        " text_hash, created_at) VALUES ('sms', ?, 'h-wita', ?, ?)",
        (f"pesan {_tag}", f"t-{_tag}", _ts))
con8b.commit()
_exp4 = sum(1 for _tag, _ts in _rows4 if _wita_date(_ts) >= _now_wita)
_exp4a = 1 if _wita_date(_rows4[0][1]) >= _now_wita else 0
check("R8-S4/GG-15 batas harian = hari WITA (dua arah)",
      sk.sender_today_count(CFG, "h-wita") == _exp4
      and sk.same_text_today_count(CFG, "t-wita-a") == _exp4a,
      f"got={sk.sender_today_count(CFG, 'h-wita')} exp={_exp4}")
check("R8-S4 baris 23:00 WITA kemarin TIDAK terhitung",
      sk.same_text_today_count(CFG, "t-wita-b") == 0)
check("R8-S4 kueri batas pakai date(..., '+8 hours')",
      SRC.count("date(created_at, '+8 hours')") >= 3
      and "date('now', '+8 hours')" in SRC)

# --- §6b (KELAS BARU): enumerasi ID berurutan --------------------------
# Pola umum: lacak laporan WAJIB butuh rahasia yang tak bisa ditebak
# (kode acak per laporan), bukan nomor urut — diuji atas sifatnya
# (acak, unik, alfabet tak-ambigu, tebak acak gagal), bukan atas satu
# nilai kode. Keterbatasan: kode 8 karakter/40 bit masih bisa
# ditebak brute-force bila tanpa batas laju — mitigasi: lacak adalah
# baca-saja + kode tidak memberi akses ke isi laporan.
sk.turso_execute = fake8
sk.turso_batch = fake_batch
if hasattr(sk, "_R8_COLS_CACHE"): sk._R8_COLS_CACHE.clear()
_st, _res = _safe_call(
    sk.submit_report,
    CFG, channel="sms", raw_text="pesan lacak 1", sender_raw=None,
    consent_data_use=False, score=0.5, band_final="REVIEW ANALIS",
    rules_fired=[])
_r1, _c1, _code1 = _res if _st == "ok" and isinstance(_res, tuple) \
    and len(_res) == 3 else (None, None, None)
_st, _res = _safe_call(
    sk.submit_report,
    CFG, channel="sms", raw_text="pesan lacak 2", sender_raw=None,
    consent_data_use=False, score=0.5, band_final="REVIEW ANALIS",
    rules_fired=[])
_r2, _c2, _code2 = _res if _st == "ok" and isinstance(_res, tuple) \
    and len(_res) == 3 else (None, None, None)
check("R8-M9/§6b submit kembalikan kode lacak 8 karakter",
      isinstance(_code1, str) and len(_code1) == 8, str(_code1))
check("R8-M9/§6b dua laporan -> kode berbeda (acak)",
      _code1 != _code2, f"{_code1} vs {_code2}")
check("R8-M9/§6b kode dari alfabet tanpa ambiguitas (tanpa 0/1/I/L/O)",
      isinstance(_code1, str)
      and all(c in "ABCDEFGHJKMNPQRSTUVWXYZ23456789" for c in _code1))
_row = _fetch_by_code(_code1) if _code1 else None
check("R8-M9/§6b lacak pakai kode kembalikan status",
      _row is not None and _row["status"] == "pending", str(_row))
check("R8-M9/§6b tebak kode acak -> None",
      _fetch_by_code("ZZZZZZZZ") is None)
check("R8-M9/§6b tidak ada lagi fetch_report_status bernomor",
      "fetch_report_status" not in SRC)
check("R8-M9/§6b tidak ada lagi number_input lacak",
      "number_input" not in SRC)
check("R8-M9/§6b expander lacak pakai kode (text input)",
      "Kode lacak" in SRC)

# --- Susulan v6.1.6: normalisasi kode lacak (temuan verifikasi live) ---
# Contoh UI memakai hubung ("K7M2-Q9XA") sementara kode tersimpan
# tanpa hubung — warga yang mengetik mengikuti contoh WAJIB ketemu.
if _code1:
    _hyph = _code1[:4] + "-" + _code1[4:]
    check("R8-M9/susulan lacak berhubung ketemu baris yang sama",
          _fetch_by_code(_hyph) is not None
          and _fetch_by_code(_hyph)["status"] == "pending",
          _hyph)
    check("R8-M9/susulan lacak huruf-kecil ketemu baris yang sama",
          _fetch_by_code(_code1.lower()) is not None, _code1.lower())
    check("R8-M9/susulan lacak berhubung+huruf-kecil ketemu",
          _fetch_by_code(_hyph.lower()) is not None, _hyph.lower())
    check("R8-M9/susulan lacak berspasi ketemu",
          _fetch_by_code(" " + _code1 + " ") is not None)
    check("R8-M9/susulan kode salah tetap None (normalisasi tak "
          "melonggarkan)",
          _fetch_by_code("ZZZZ-ZZZZ") is None)
    check("R8-M9/susulan resep tampilkan kode berhubung (format contoh)",
          "_fmt_track_code(receipt['track_code'])" in SRC)
else:
    check("R8-M9/susulan (dilewati: submit lacak gagal)", False, "no code")

# --- S2 (KASUS + daftar tumbuh): klaim absolut persetujuan/privasi -----
# Keterbatasan jujur: guard string tidak menangkap frasa absolut BARU
# — kelasnya hanya terkunci sebagian. Mitigasi: daftar terlarang di
# bawah TUMBUH tiap ronde + disertakan ke prompt review berikut.
FORBIDDEN_ABSOLUT = [
    "tidak pernah masuk data latih",
    "tidak memuat identitas Anda",
    "dari data latih turunan",
    "tidak pernah dipakai sebagai data latih",
]
for _ph in FORBIDDEN_ABSOLUT:
    check(f"R8-S2 frasa absolut hilang: '{_ph}'",
          _ph not in sk.CONSENT_TEXT_V1
          and _ph not in sk.PRIVACY_TEXT_V1)
check("R8-S2 klaim hapus terkualifikasi (ekspor lampau tak bisa ditarik)",
      "tidak dapat ditarik kembali" in sk.CONSENT_TEXT_V1)
check("R8-S2 checkbox terkualifikasi 'yang terdeteksi'",
      "yang terdeteksi" in sk.CONSENT_CHECKBOX_V1)
check("R8-S2 privasi akui batas (OTP/nama bisa lolos)",
      "kode OTP" in sk.PRIVACY_TEXT_V1)

# --- S6 (KELAS data): provenance OCR ------------------------------------
sk.turso_execute = fake8
sk.turso_batch = fake_batch
_st, _res = _safe_call(
    sk.submit_report,
    CFG, channel="sms", raw_text="pesan ocr 1", sender_raw=None,
    consent_data_use=False, score=0.5, band_final="REVIEW ANALIS",
    rules_fired=[], via_ocr=True)
_r3 = _res[0] if _st == "ok" and isinstance(_res, tuple) else None
check("R8-S6 via_ocr=True tersimpan 1",
      _r3 is not None and fake8(
          CFG, "SELECT via_ocr FROM reports WHERE id = ?",
          [_r3])[0]["via_ocr"] == 1)
_st, _res = _safe_call(
    sk.submit_report,
    CFG, channel="sms", raw_text="pesan ocr 0", sender_raw=None,
    consent_data_use=False, score=0.5, band_final="REVIEW ANALIS",
    rules_fired=[], via_ocr=False)
_r4 = _res[0] if _st == "ok" and isinstance(_res, tuple) else None
check("R8-S6 via_ocr=False tersimpan 0",
      _r4 is not None and fake8(
          CFG, "SELECT via_ocr FROM reports WHERE id = ?",
          [_r4])[0]["via_ocr"] == 0)
_pend8 = SRC.split("# Pelabelan BUTA", 1)[1].split(
    "# Antrean triase", 1)[0]
check("R8-S6 kartu pending tampilkan penanda OCR",
      "OCR" in _pend8)

# --- S7 (KELAS): penjaga "jangan" over-supresi --------------------------
# Pola umum: larangan ("jangan") hanya menekan bila ia MENGIKAT kata
# kerja permintaan itu (jangan + [penguat] + [kata ganti] + verba +
# kredensial) — diuji atas matriks verba x penguat x penerima (yang
# harus tetap ditekan) vs awalan bukan-larangan (yang harus menembus).
_PROT_FAIL = []
for _verb in ("bagikan", "berikan", "masukkan", "memberikan", "kasih",
              "serahkan"):
    for _intens in ("", "pernah ", "sekali-kali ", "sampai "):
        for _tail in ("kepada siapa pun", "ke siapa pun", "ini"):
            _t = f"JANGAN {_intens}{_verb} kode OTP {_tail}"
            if evaluate_rules(_t)["strong"]["S2"]:
                _PROT_FAIL.append(_t)
check("R8-S7/GG-7 kalimat pelindung tetap BUKAN S2 (matriks)",
      not _PROT_FAIL, str(_PROT_FAIL[:3]))
check("R8-S7 'Jangan sampai Anda memberikan kode OTP' tetap pelindung",
      evaluate_rules(
          "Jangan sampai Anda memberikan kode OTP ini kepada siapa pun"
          )["strong"]["S2"] is False)
_LEAD_FAIL = []
for _lead in ("lupa", "sampai ketinggalan", "khawatir", "takut",
              "ragu", "lewatkan", "sampai lupa"):
    for _req in ("berikan OTP Anda di bca-co-id.com",
                 "berikan kode OTP Anda sekarang",
                 "bagikan PIN Anda di link ini"):
        _t = f"Jangan {_lead}, {_req}"
        if not evaluate_rules(_t)["strong"]["S2"]:
            _LEAD_FAIL.append(_t)
check("R8-S7/GG-7 'Jangan <bukan-larangan>' + permintaan -> S2 (matriks)",
      not _LEAD_FAIL, str(_LEAD_FAIL[:3]))
check("R8-S7 S2C 'Jangan lupa, verifikasi PIN Anda di …' -> S2",
      evaluate_rules(
          "Jangan lupa, verifikasi PIN Anda di bca-co-id.com"
          )["strong"]["S2"] is True)
check("R8-S7 kontrol 'Berikan OTP Anda di …' tetap S2",
      evaluate_rules(
          "Berikan OTP Anda di bca-co-id.com")["strong"]["S2"] is True)

# --- N1/N2/N3/N4/N5 ------------------------------------------------------
check("R8-N1 'terurut skor' hilang dari pengantar tab Verifikasi",
      "Antrean triase terurut skor ada terpisah" not in SRC)
check("R8-N2 caption lama 'khusus terverifikasi' hilang",
      "panel ini khusus data laporan yang terverifikasi" not in SRC)
check("R8-N2 caption baru: band (terverifikasi) dinyatakan",
      "Distribusi band model (terverifikasi)" in SRC)
check("R8-N3 docstring 'tidak diverifikasi ulang' hilang",
      "tidak diverifikasi ulang" not in SRC)
check("R8-N3 docstring Turnstile nyatakan verifikasi tiap submit",
      "setiap pengiriman" in SRC)
import journey as _jrn
check("R8-N4 _status_tiga: n wajib (tanpa default)",
      "n" in inspect.signature(_jrn._status_tiga).parameters
      and inspect.signature(_jrn._status_tiga).parameters["n"].default
      is inspect.Parameter.empty)
check("R8-N4 pemanggil _status_tiga teruskan n eksplisit",
      '_status_tiga(v, gerbang, s["n"])' in JRN_SRC
      and '_status_tiga(stage["sah"], gates["sah"], stage["n"])'
      in JRN_SRC)
_res8 = _json.loads((REPO / "results.json").read_text(encoding="utf-8"))
check("R8-N4 tiap stage results.json punya n int > 0",
      all(isinstance(s.get("n"), int) and s["n"] > 0
          for s in _res8["stages"]),
      str([(s["id"], s.get("n")) for s in _res8["stages"]]))


def _pct_ok(pct, n):
    k = int(round(pct / 100.0 * n))
    return abs(round(k / n * 100.0, 1) - pct) < 0.05


check("R8-N4 persen SAH/SMISHING konsisten dengan k/n per stage",
      all(s.get("n") and _pct_ok(s["sah"], s["n"])
          and _pct_ok(s["smishing"], s["n"])
          for s in _res8["stages"]))
check("R8-N5 remoteip didokumentasikan tak tersedia (opsional API)",
      "remoteip" in SRC and "tidak mengekspos IP klien" in SRC)
check("R8 app version v6.1.6", 'APP_VERSION = "v6.1.6"' in APP_SRC)

# --- Gap G5 ronde 8: verify_report atomik + gagal-jujur --------------
# (cek struktural — SRC baru terdefinisi di titik ini)
_vrf = SRC.split("def verify_report(cfg")[1].split("def reject_report")[0]
check("R8-G5 verify_report memakai turso_batch (bukan dua execute)",
      "turso_batch(cfg" in _vrf)
check("R8-G5 pemanggil UI tangkap gagal verify (st.error)",
      "Verifikasi gagal tersimpan" in SRC)
check("R8-G5 jejak hantu dihapus kompensasi bila UPDATE tak mengenai",
      "DELETE FROM label_log WHERE id = ?" in _vrf)

# --- Gap G6 ronde 8: bukti gerbang klaim ------------------------------
import json as _json
_gen_src = (REPO / "gen_results.py").read_text(encoding="utf-8")
_m = re.search(r"GERBANG\s*=\s*\{([^}]*)\}", _gen_src)
_g = {}
if _m:
    for _kv in _m.group(1).split(","):
        _k, _v = _kv.split(":")
        _g[_k.strip().strip("\"'")] = float(_v.strip())
check("R8-G6 GERBANG gen_results.py = gates results.json",
      _g.get("sah") == _res8["gates"]["sah"]
      and _g.get("smishing") == _res8["gates"]["smishing"]
      and _g.get("uci_pr_auc") == _res8["gates"]["uci_pr_auc"]
      and _g.get("auto_close") == _res8["gates"]["auto_close"],
      str(_g))
check("R8-G6 GERBANG satu konstanta (bukan per tahap)",
      _gen_src.count("GERBANG = ") == 1
      and '"gates": GERBANG' in _gen_src)
_id_train = REPO.parent / "id-train"
if _id_train.is_dir():
    _ev_ok, _ev_bad = True, []
    for _f in ("eval_smoke_current.json", "eval_tahap2c.json",
               "eval_tahap2d.json"):
        _ev = _json.loads((_id_train / _f).read_text(encoding="utf-8"))
        _thr = {g["ukuran"]: g["nilai"] for g in _ev.get("gerbang", [])}
        _same = (any("85%" in k for k in _thr)
                 and any("95%" in k for k in _thr)
                 and any("0,98" in k for k in _thr))
        if not _same:
            _ev_ok, _ev_bad = False, _ev_bad + [_f]
    check("R8-G6 ambang sama tercatat di ketiga file evaluasi",
          _ev_ok, str(_ev_bad))
else:
    print("SKIP R8-G6 file evaluasi (id-train tak ada di mesin ini)")
check("R8-G6 journey.py merujuk bukti gerbang + batasnya",
      "di dalam ketiga" in JRN_SRC
      and "file evaluasi itu sendiri" in JRN_SRC
      and "tak berubah sejak commit" in JRN_SRC
      and "pertamanya (23 Okt 2026)" in JRN_SRC
      and "Batas bukti ini" in JRN_SRC)

# --- Gap G7 ronde 8: sensus Turnstile ----------------------------------
_turn_doc = REPO / "docs" / "turnstile.md"
check("R8-G7 dokumen sensus Turnstile ada",
      _turn_doc.is_file())
if _turn_doc.is_file():
    _td = _turn_doc.read_text(encoding="utf-8")
    for _jalur in ("Jalur 1", "Jalur 2", "Jalur 3", "Jalur 4",
                   "Jalur 5", "Jalur 6"):
        check(f"R8-G7 sensus memuat {_jalur}", _jalur in _td)
    check("R8-G7 sensus nyatakan intake satu-satunya jalur tulis publik",
          "SATU-SATUNYA jalur tulis publik" in _td)
    check("R8-G7 sensus catat helper turnstile_active tak terpakai",
          "turnstile_active" in _td)
_calls = [ln for ln in SRC.splitlines()
          if "_turnstile_passed(cfg" in ln and "def " not in ln]
check("R8-G7 siteverify hanya dipanggil dari jalur intake (1 call-site)",
      len(_calls) == 1, str(_calls))
check("R8-G7 app.py tak panggil verify_turnstile langsung",
      "verify_turnstile(" not in APP_SRC
      and "_turnstile_passed(" not in APP_SRC)
check("R8-G7 verify_turnstile didefinisikan sekali di siskamling.py",
      SRC.count("def verify_turnstile") == 1)

# --- Gap G4 ronde 8: draf publik vs kode v6.1.6 ------------------------
_p2 = REPO.parent / "p2-assets"
if _p2.is_dir():
    _art = (_p2 / "artikel-medium-substack-v2.md").read_text(
        encoding="utf-8") if (_p2 / "artikel-medium-substack-v2.md").exists() else ""
    check("R8-G4 Artikel v2 tak lagi klaim daftar triase terurut skor ada",
          "daftar triase terurut skor ada terpisah" not in _art)
    check("R8-G4 Artikel v2 sebut kode lacak acak (bukan nomor lacak)",
          "kode lacak acak" in _art and "nomor lacak" not in _art)
    _red = (_p2 / "draf-reddit-v1.md").read_text(
        encoding="utf-8") if (_p2 / "draf-reddit-v1.md").exists() else ""
    check("R8-G4 Reddit v1 tanpa klaim nomor/antrean yang kedaluwarsa",
          "nomor lacak" not in _red and "terurut skor" not in _red)
else:
    print("SKIP R8-G4 draf publik (p2-assets tak ada di mesin ini)")

print()
print("FAILURES:", fails if fails else "none — ALL PASS")
sys.exit(1 if fails else 0)
