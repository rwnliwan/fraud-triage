# -*- coding: utf-8 -*-
"""Siskamling Digital — Fase 1: tab "Lapor & Cek" + "Galeri Modus".

Lapisan layanan publik di atas mesin Fraud Triage:

* Warga menempel pesan mencurigakan -> dinilai mesin yang sama dengan
  tab Analisis Tunggal (skor + band final termasuk lapisan aturan).
* Bila warga menekan kirim, laporan masuk database Turso KHUSUS
  Siskamling (terpisah dari Brain) sebagai baris `reports` berstatus
  'pending'. Yang disimpan HANYA teks hasil scrub PII (scrubber.py);
  teks mentah tidak pernah ditulis ke basis data. Nomor pengirim hanya
  disimpan sebagai hash bergaram (sender_hash) — tidak bisa dibalik.
* Persetujuan (consent) dua tingkat sesuai CONSENT.md v1: tanpa centang,
  laporan hanya untuk cek/verifikasi; dengan centang, consent_data_use=1
  dan jejaknya ditulis ke consent_log (versi + hash teks persetujuan).
  Hanya baris terverifikasi manusia + consent yang bisa keluar lewat
  view corpus_export dan tampil di galeri.
* Galeri Modus menampilkan laporan berstatus 'verified' +
  gallery_visible=1 saja — tidak ada jalan bagi baris pending tampil.

Konfigurasi (Streamlit secrets ATAU env; lokal: berkas mode 600
~/.config/turso/siskamling-digital.env):
    TURSO_DATABASE_URL, TURSO_AUTH_TOKEN, SISKAMLING_SENDER_SALT

Modul ini SENGAJA tidak mengimpor app.py (hindari sirkular): fungsi
render menerima engine + callback analisis dari app.py.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

import streamlit as st

from scrubber import scrub, hash_sender

CONSENT_VERSION = "v1"

# Teks persetujuan yang ditampilkan di formulir — versi polos dari bagian
# formulir CONSENT.md v1 (kata per kata sama; hanya format Markdown yang
# diratakan). consent_log.consent_text_hash = SHA-256 atas
# CONSENT_TEXT_V1 + "\n\n" + CONSENT_CHECKBOX_V1, persis seperti tampil.
CONSENT_TEXT_V1 = (
    "Siskamling Digital adalah layanan ronda warga untuk pesan penipuan "
    "(smishing). Anda menempel pesan yang Anda terima, sistem memberi "
    "hasil cek awal, dan — bila Anda berkenan — laporan Anda membantu "
    "melindungi orang lain.\n\n"
    "**Yang kami kumpulkan dari laporan Anda:** isi pesan yang Anda "
    "tempel, setelah dibersihkan otomatis dari nomor telepon, tautan "
    "pribadi, nomor rekening, dan data pribadi lain yang terdeteksi; "
    "kanal pesan (SMS/WhatsApp/Telegram/lainnya) dan tanggal laporan; "
    "skor penilaian otomatis atas pesan tersebut.\n\n"
    "**Yang TIDAK kami simpan:** nomor telepon Anda atau nomor pengirim "
    "pesan dalam bentuk asli — bila diperlukan untuk mencegah laporan "
    "palsu berulang, yang disimpan hanya kode acak satu arah (hash) "
    "yang tidak bisa dikembalikan menjadi nomor. Nama atau identitas "
    "Anda — formulir ini tidak memintanya.\n\n"
    "**Untuk apa laporan digunakan:** (1) diperiksa (diverifikasi) oleh "
    "tim kami sebagai laporan warga; (2) bila Anda menyetujui di bawah, "
    "versi bersihnya dapat tampil tanpa nama di galeri modus penipuan "
    "dan dipakai sebagai bahan ajar (data latih) agar sistem pendeteksi "
    "semakin akurat. Tanpa persetujuan itu, laporan Anda hanya dipakai "
    "untuk proses cek dan verifikasi — tidak tampil di galeri dan tidak "
    "dipakai sebagai data latih.\n\n"
    "**Hak Anda:** Anda boleh meminta laporan Anda dihapus kapan saja; "
    "penghapusan juga mengeluarkannya dari galeri dan dari data latih "
    "turunan. Persetujuan ini sukarela — menolak tidak menghalangi Anda "
    "memakai fitur cek pesan.\n\n"
    "**Penting — batas layanan ini:** hasil cek adalah triase awal, "
    "bukan vonis dan bukan jaminan sebuah pesan aman atau penipuan. "
    "Jangan pernah membagikan kode OTP, PIN, atau kata sandi kepada "
    "siapa pun, apa pun hasil ceknya. Layanan ini bukan penegak hukum "
    "dan tidak memproses pengembalian dana. Bila Anda sudah terlanjur "
    "menjadi korban, segera hubungi bank terkait dan kanal resmi OJK "
    "(Kontak 157) / IASC (Indonesia Anti-Scam Centre)."
)

CONSENT_CHECKBOX_V1 = (
    "Saya setuju isi pesan yang saya laporkan (setelah dibersihkan "
    "dari data pribadi) ditampilkan tanpa nama di galeri modus dan "
    "dipakai sebagai data latih untuk meningkatkan pendeteksi penipuan."
)


def consent_text_hash() -> str:
    """SHA-256 teks persetujuan persis seperti yang tampil di formulir."""
    payload = CONSENT_TEXT_V1 + "\n\n" + CONSENT_CHECKBOX_V1
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# Peta band final app -> nilai kolom reports.model_band (CHECK di schema)
# dan label tampilnya.
BAND_STORE = {"AUTO-CLOSE": "AMAN", "REVIEW ANALIS": "REVIEW",
              "ESKALASI": "ESKALASI"}
BAND_BADGE = {"AMAN": "🟢 AMAN", "REVIEW": "🟡 REVIEW",
              "ESKALASI": "🔴 ESKALASI"}

CHANNELS = {"sms": "SMS", "whatsapp": "WhatsApp",
            "telegram": "Telegram", "lainnya": "Lainnya"}

WITA = timezone(timedelta(hours=8))


# ---------------------------------------------------------------------------
# Konfigurasi & klien Turso (Hrana HTTP /v2/pipeline, satu statement)
# ---------------------------------------------------------------------------
def load_config() -> dict:
    """Ambil kredensial Turso dari secrets/env; lokal: berkas mode 600."""
    cfg = {"url": None, "token": None, "salt": None, "admin_password": None}
    try:
        cfg["url"] = st.secrets.get("TURSO_DATABASE_URL")
        cfg["token"] = st.secrets.get("TURSO_AUTH_TOKEN")
        cfg["salt"] = st.secrets.get("SISKAMLING_SENDER_SALT")
    except Exception:
        pass
    try:
        cfg["admin_password"] = st.secrets.get(
            "SISKAMLING_ADMIN_PASSWORD")
    except Exception:
        pass
    cfg["url"] = cfg["url"] or os.environ.get("TURSO_DATABASE_URL")
    cfg["token"] = cfg["token"] or os.environ.get("TURSO_AUTH_TOKEN")
    cfg["salt"] = cfg["salt"] or os.environ.get("SISKAMLING_SENDER_SALT")
    cfg["admin_password"] = cfg["admin_password"] or os.environ.get(
        "SISKAMLING_ADMIN_PASSWORD")
    if not (cfg["url"] and cfg["token"]):
        env_path = os.path.expanduser(
            "~/.config/turso/siskamling-digital.env")
        if os.path.exists(env_path):
            file_cfg = {}
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        file_cfg[k.strip()] = v.strip()
            cfg["url"] = cfg["url"] or file_cfg.get("TURSO_DATABASE_URL")
            cfg["token"] = cfg["token"] or file_cfg.get(
                "TURSO_AUTH_TOKEN")
            cfg["salt"] = cfg["salt"] or file_cfg.get(
                "SISKAMLING_SENDER_SALT")
    return cfg


def turso_execute(cfg: dict, sql: str, args: list | None = None) -> list:
    """Jalankan satu statement; kembalikan baris sebagai list[dict]."""
    base = cfg["url"].rstrip("/")
    if base.startswith("libsql://"):
        base = "https://" + base[len("libsql://"):]
    elif base.startswith("http://"):
        base = "https://" + base[len("http://"):]
    if not base.endswith("/v2/pipeline"):
        base += "/v2/pipeline"
    stmt = {"sql": sql}
    if args:
        stmt["args"] = [
            {"type": "null", "value": None} if a is None
            else {"type": "integer", "value": str(a)} if isinstance(a, int)
            else {"type": "float", "value": a} if isinstance(a, float)
            else {"type": "text", "value": str(a)}
            for a in args
        ]
    body = json.dumps(
        {"requests": [{"type": "execute", "stmt": stmt}]}).encode("utf-8")
    req = urllib.request.Request(
        base, data=body, method="POST",
        headers={"Authorization": "Bearer " + cfg["token"],
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode("utf-8"))
    item = res["results"][0]
    if item["type"] != "ok":
        raise RuntimeError("turso error: " + json.dumps(item)[:300])
    result = item["response"]["result"]
    cols = [c["name"] for c in result["cols"]]
    rows = []
    for row in result["rows"]:
        d = {}
        for c, cell in zip(cols, row):
            t, v = cell.get("type"), cell.get("value")
            if v is None or t == "null":
                d[c] = None
            elif t == "integer":
                d[c] = int(v)
            elif t == "float":
                d[c] = float(v)
            else:
                d[c] = v
        rows.append(d)
    return rows


# ---------------------------------------------------------------------------
# Operasi basis data
# ---------------------------------------------------------------------------
def submit_report(cfg: dict, *, channel: str, raw_text: str,
                  sender_raw: str | None, consent_data_use: bool,
                  score: float, band_final: str,
                  rules_fired: list) -> tuple[int, str]:
    """Simpan satu laporan (status 'pending'). Kembalikan (id, created_at).

    Teks yang ditulis HANYA hasil scrub; created_at diisi basis data
    (UTC) dan menjadi tanggal submit resmi pada log pencatatan.
    """
    clean_text, _findings = scrub(raw_text)
    sender_hash = hash_sender(sender_raw, cfg.get("salt")) \
        if sender_raw else None
    rows = turso_execute(
        cfg,
        "INSERT INTO reports (channel, text_scrubbed, model_score, "
        "model_band, rules_fired, consent_data_use, consent_at, "
        "sender_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
        "RETURNING id, created_at",
        [channel, clean_text, float(score), BAND_STORE[band_final],
         json.dumps(rules_fired), 1 if consent_data_use else 0,
         datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
         if consent_data_use else None,
         sender_hash])
    report_id = rows[0]["id"]
    created_at = rows[0]["created_at"]
    if consent_data_use:
        turso_execute(
            cfg,
            "INSERT INTO consent_log (report_id, consent_version, "
            "consent_text_hash) VALUES (?, ?, ?)",
            [report_id, CONSENT_VERSION, consent_text_hash()])
    return report_id, created_at


def fetch_gallery(cfg: dict, limit: int = 30) -> list:
    """Laporan terverifikasi yang boleh tampil di galeri publik."""
    return turso_execute(
        cfg,
        "SELECT id, created_at, verified_at, category_modus, "
        "text_scrubbed, model_band FROM reports "
        "WHERE status = 'verified' AND gallery_visible = 1 "
        "ORDER BY verified_at DESC LIMIT ?",
        [int(limit)])


def fetch_public_stats(cfg: dict) -> dict:
    """Agregat aman-publik untuk kepala galeri."""
    total = turso_execute(cfg, "SELECT COUNT(*) AS n FROM reports")[0]["n"]
    verified = turso_execute(
        cfg, "SELECT COUNT(*) AS n FROM reports "
             "WHERE status = 'verified'")[0]["n"]
    senders = turso_execute(
        cfg, "SELECT COUNT(DISTINCT sender_hash) AS n FROM reports "
             "WHERE sender_hash IS NOT NULL")[0]["n"]
    return {"total": total, "verified": verified, "senders": senders}


def fmt_wita(utc_text: str | None) -> str:
    """'YYYY-MM-DD HH:MM:SS' (UTC dari DB) -> tampilan WITA."""
    if not utc_text:
        return "-"
    try:
        dt = datetime.strptime(utc_text, "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc)
        return dt.astimezone(WITA).strftime("%d-%m-%Y %H:%M WITA")
    except ValueError:
        return utc_text


# ---------------------------------------------------------------------------
# Tab Lapor & Cek
# ---------------------------------------------------------------------------
def render_lapor_tab(engine, analyze_one, card_html) -> None:
    st.markdown("### 📮 Lapor & Cek Pesan Mencurigakan")
    st.markdown(
        "Tempel pesan yang Anda terima — sistem memberi **hasil cek "
        "awal** dari model pendeteksi yang sama dengan tab Analisis "
        "Tunggal, dan Anda dapat **melaporkannya** agar warga lain "
        "terlindungi. Setiap laporan tercatat dengan **nomor laporan "
        "unik** dan **tanggal submit** sebagai bukti penerimaan.")
    with st.expander("Baca dulu — cara kerja, data & persetujuan (v1)"):
        st.markdown(CONSENT_TEXT_V1)

    cfg = load_config()
    db_ready = bool(cfg.get("url") and cfg.get("token"))
    if not db_ready:
        st.warning(
            "Penyimpanan laporan belum aktif pada deployment ini "
            "(kredensial basis data belum dipasang) — fitur **cek** "
            "tetap bisa dipakai, laporan belum bisa dikirim.")

    channel_label = st.selectbox(
        "Kanal pesan", list(CHANNELS.values()), key="sk_channel")
    channel = [k for k, v in CHANNELS.items() if v == channel_label][0]
    sender = st.text_input(
        "Nomor pengirim pesan (opsional)",
        key="sk_sender",
        placeholder="cth. 0812xxxxxxx — hanya disimpan sebagai kode "
                    "hash satu arah, tidak pernah dalam bentuk asli")
    text = st.text_area(
        "Isi pesan", key="sk_text", height=130, max_chars=2000,
        placeholder="Tempel isi SMS / pesan persis seperti yang Anda "
                    "terima…")
    consent = st.checkbox(CONSENT_CHECKBOX_V1, key="sk_consent")
    st.caption(
        "Tanpa mencentang pun laporan tetap terkirim dan tercatat — "
        "hanya saja tidak tampil di galeri dan tidak dipakai sebagai "
        "data latih.")

    if st.button("🔍 Cek & Kirim Laporan", type="primary",
                 key="btn_sk_submit"):
        raw = (text or "").strip()
        if not raw:
            st.warning("Isi dulu teks pesannya.")
        else:
            with st.spinner("Menilai pesan…"):
                analysis = analyze_one(engine, raw)
            st.session_state["sk_last"] = analysis
            st.session_state["sk_receipt"] = None
            if db_ready:
                rule = analysis["rule"]
                rules_fired = list(rule["active_signals"])
                if rule.get("calm", {}).get("lowered"):
                    rules_fired.append("PENENANG")
                try:
                    report_id, created_at = submit_report(
                        cfg, channel=channel, raw_text=raw,
                        sender_raw=(sender or "").strip() or None,
                        consent_data_use=bool(consent),
                        score=analysis["res"]["p_scam"],
                        band_final=analysis["final_zone"],
                        rules_fired=rules_fired)
                    st.session_state["sk_receipt"] = {
                        "id": report_id, "created_at": created_at,
                        "consent": bool(consent)}
                except Exception as exc:
                    st.error(f"Laporan gagal tersimpan: {exc}")

    receipt = st.session_state.get("sk_receipt")
    if receipt:
        st.success(
            f"✅ **Laporan terkirim & tercatat.** Nomor laporan Anda: "
            f"**#{receipt['id']}** · diterima "
            f"**{fmt_wita(receipt['created_at'])}** · status awal: "
            f"menunggu verifikasi tim."
            + (" Persetujuan penggunaan data: **ya** (galeri anonim + "
               "data latih)." if receipt["consent"]
               else " Persetujuan penggunaan data: **tidak** (hanya "
                    "untuk cek & verifikasi)."))
    analysis = st.session_state.get("sk_last")
    if analysis:
        st.markdown("#### Hasil cek awal pesan ini")
        st.markdown(card_html(analysis), unsafe_allow_html=True)
        st.caption(
            "Hasil cek adalah triase awal, bukan vonis. Jangan pernah "
            "membagikan kode OTP, PIN, atau kata sandi kepada siapa "
            "pun, apa pun hasil ceknya.")


# ---------------------------------------------------------------------------
# Tab Galeri Modus
# ---------------------------------------------------------------------------
def render_gallery_tab() -> None:
    st.markdown("### 🖼️ Galeri Modus Penipuan")
    st.markdown(
        "Modus-modus yang **sudah diverifikasi** dari laporan warga. "
        "Semua teks tampil **tanpa nama dan tanpa data pribadi** "
        "(dibersihkan otomatis), agar Anda bisa mengenali polanya "
        "sebelum jadi korban berikutnya.")
    cfg = load_config()
    if not (cfg.get("url") and cfg.get("token")):
        st.info("Galeri belum aktif pada deployment ini (basis data "
                "belum terhubung).")
        return
    try:
        stats = fetch_public_stats(cfg)
        rows = fetch_gallery(cfg)
    except Exception as exc:
        st.error(f"Galeri belum bisa dimuat: {exc}")
        return
    c1, c2, c3 = st.columns(3)
    c1.metric("Laporan masuk", stats["total"])
    c2.metric("Modus terverifikasi", stats["verified"])
    c3.metric("Pengirim unik tercatat", stats["senders"])
    if not rows:
        st.info("Belum ada modus terverifikasi yang ditayangkan. "
                "Laporan warga yang masuk sedang menunggu verifikasi — "
                "galeri terisi dari tab **📮 Lapor & Cek**.")
        return
    for r in rows:
        with st.container(border=True):
            badge = BAND_BADGE.get(r["model_band"], r["model_band"] or "-")
            kategori = r["category_modus"] or "modus belum dikategorikan"
            st.markdown(f"**{badge}** · modus: *{kategori}* · "
                        f"Laporan #{r['id']}")
            st.markdown(f"> {r['text_scrubbed']}")
            st.caption(f"Diverifikasi {fmt_wita(r['verified_at'])} · "
                       f"dilaporkan {fmt_wita(r['created_at'])}")


# ---------------------------------------------------------------------------
# Fase 2 — Verifikasi admin (tab "🔐 Verifikasi")
#
# Pembagian kerja yang disepakati desain Fase 0: LABEL HANYA DITENTUKAN
# MANUSIA. Model ensemble sudah menilai tiap laporan saat masuk (skor,
# band, sinyal) dan di tab ini tampil sebagai SARAN — bukan keputusan.
# Memakai model sebagai penentu label akan merusak tujuan korpus: data
# latih baru harus berisi penilaian manusia yang independen, bukan
# pendapat model tentang datanya sendiri (apalagi kelemahan model yang
# terdokumentasi justru pada pesan Indonesia).
# ---------------------------------------------------------------------------
LABELS = ["SMISHING", "SAH", "SPAM_PROMO"]
CATEGORIES = ["blokir_akun", "otp_palsu", "resi_paket", "undian", "apk",
              "investasi", "tagihan", "lainnya"]
_STRONG = ("S1", "S2", "S3")

_PROMO_WORDS = ("promo", "diskon", "cashback", "gratis ongkir", "sale",
                "voucher", "bonus saldo")
_CATEGORY_HINTS = [
    ("resi_paket", ("paket", "resi", "antar ulang", "gudang", "kurir",
                    "tertahan")),
    ("blokir_akun", ("blokir", "diblokir", "dinonaktifkan",
                     "verifikasi akun", "akan hangus")),
    ("otp_palsu", ("otp", "kode verifikasi", "kode rahasia")),
    ("undian", ("undian", "memenangkan", "hadiah", "selamat! anda",
                "klaim")),
    ("apk", (".apk", "unduh aplikasi", "install aplikasi")),
    ("investasi", ("investasi", "profit", "grup vip", "trading",
                   "modal kembali")),
    ("tagihan", ("tagihan", "menunggak", "tunggakan", "pemutusan",
                 "jatuh tempo")),
]


def _fired_list(row: dict) -> list:
    try:
        return json.loads(row.get("rules_fired") or "[]")
    except (TypeError, ValueError):
        return []


def suggest_label(row: dict) -> tuple[str, str, str]:
    """Saran label dari band/sinyal model. (label, alasan, kekuatan).

    Ini SARAN triase untuk mempercepat review manusia — bukan vonis;
    keputusan tetap di tangan peninjau. Kekuatan 'lemah' berarti zona
    abu-abu: baca teksnya sebelum memutuskan.
    """
    band = row.get("model_band")
    fired = _fired_list(row)
    strong = [s for s in fired if s in _STRONG]
    if band == "ESKALASI" or len(strong) >= 2:
        alasan = f"band {band}"
        if strong:
            alasan += f" + sinyal kuat {'+'.join(strong)}"
        return "SMISHING", alasan, "kuat"
    if band == "AMAN" and not strong:
        return "SAH", "band AMAN, tanpa sinyal kuat", "kuat"
    text = (row.get("text_scrubbed") or "").lower()
    if any(w in text for w in _PROMO_WORDS):
        return "SPAM_PROMO", "pola promosi pada zona abu-abu", "lemah"
    return ("SMISHING",
            "zona abu-abu (band REVIEW / satu sinyal) — baca teksnya",
            "lemah")


def suggest_category(row: dict) -> str:
    text = (row.get("text_scrubbed") or "").lower()
    for kategori, kata in _CATEGORY_HINTS:
        if any(k in text for k in kata):
            return kategori
    return "lainnya"


def fetch_pending(cfg: dict, limit: int = 50) -> list:
    """Antrean verifikasi: skor tertinggi dulu (triase risiko)."""
    return turso_execute(
        cfg,
        "SELECT * FROM reports WHERE status = 'pending' "
        "ORDER BY model_score DESC, created_at ASC LIMIT ?",
        [int(limit)])


def fetch_verified(cfg: dict, limit: int = 20) -> list:
    return turso_execute(
        cfg,
        "SELECT * FROM reports WHERE status = 'verified' "
        "ORDER BY verified_at DESC LIMIT ?",
        [int(limit)])


def count_status(cfg: dict, status: str) -> int:
    return turso_execute(
        cfg, "SELECT COUNT(*) AS n FROM reports WHERE status = ?",
        [status])[0]["n"]


def corpus_count(cfg: dict) -> int:
    return turso_execute(
        cfg, "SELECT COUNT(*) AS n FROM corpus_export")[0]["n"]


def sender_report_count(cfg: dict, sender_hash: str | None) -> int:
    if not sender_hash:
        return 0
    return turso_execute(
        cfg, "SELECT COUNT(*) AS n FROM reports WHERE sender_hash = ?",
        [sender_hash])[0]["n"]


def duplicate_text_count(cfg: dict, text: str, exclude_id: int) -> int:
    return turso_execute(
        cfg, "SELECT COUNT(*) AS n FROM reports "
             "WHERE text_scrubbed = ? AND id <> ?",
        [text, int(exclude_id)])[0]["n"]


def verify_report(cfg: dict, report_id: int, label: str, category: str,
                  gallery_visible: bool) -> None:
    turso_execute(
        cfg,
        "UPDATE reports SET status = 'verified', label = ?, "
        "category_modus = ?, gallery_visible = ?, "
        "verified_at = datetime('now') WHERE id = ? AND status = 'pending'",
        [label, category, 1 if gallery_visible else 0, int(report_id)])


def reject_report(cfg: dict, report_id: int) -> None:
    turso_execute(
        cfg,
        "UPDATE reports SET status = 'rejected', "
        "verified_at = datetime('now') WHERE id = ? AND status = 'pending'",
        [int(report_id)])


def delete_report(cfg: dict, report_id: int) -> None:
    """Hapus lunak (hak hapus): baris keluar dari galeri & korpus."""
    turso_execute(
        cfg,
        "UPDATE reports SET status = 'deleted', gallery_visible = 0 "
        "WHERE id = ?",
        [int(report_id)])


def unverify_report(cfg: dict, report_id: int) -> None:
    turso_execute(
        cfg,
        "UPDATE reports SET status = 'pending', label = NULL, "
        "verified_at = NULL, gallery_visible = 0 "
        "WHERE id = ? AND status = 'verified'",
        [int(report_id)])


def set_gallery_visible(cfg: dict, report_id: int, visible: bool) -> None:
    turso_execute(
        cfg,
        "UPDATE reports SET gallery_visible = ? "
        "WHERE id = ? AND status = 'verified'",
        [1 if visible else 0, int(report_id)])


def _report_meta(cfg: dict, r: dict) -> str:
    parts = [
        f"kanal {CHANNELS.get(r['channel'], r['channel'])}",
        f"submit {fmt_wita(r['created_at'])}",
        "consent data: YA" if r["consent_data_use"]
        else "consent data: tidak",
    ]
    if r.get("sender_hash"):
        n = sender_report_count(cfg, r["sender_hash"])
        parts.append(f"pengirim {r['sender_hash'][:8]}… "
                     f"({n} laporan dari pengirim ini)")
    dup = duplicate_text_count(cfg, r["text_scrubbed"], r["id"])
    if dup:
        parts.append(f"⚠️ teks identik dengan {dup} laporan lain")
    return " · ".join(parts)


def render_admin_tab() -> None:
    st.markdown("### 🔐 Verifikasi Laporan")
    st.markdown(
        "Ruang kerja peninjau. **Label ditentukan manusia** — model "
        "hanya memberi saran dari skor & sinyalnya agar review cepat. "
        "Laporan terverifikasi + consent masuk korpus data latih; yang "
        "ditandai tampil galeri muncul di Galeri Modus publik.")
    cfg = load_config()
    if not (cfg.get("url") and cfg.get("token")):
        st.warning("Basis data belum terhubung pada deployment ini.")
        return
    if not cfg.get("admin_password"):
        st.info(
            "Tab verifikasi belum diaktifkan: secret "
            "`SISKAMLING_ADMIN_PASSWORD` belum dipasang di Streamlit "
            "Cloud. Pasang dulu, lalu reboot app.")
        return
    if not st.session_state.get("sk_admin_ok"):
        pw = st.text_input("Kata sandi verifikasi", type="password",
                           key="sk_admin_pw")
        if st.button("🔓 Masuk", key="btn_admin_login"):
            if hmac.compare_digest(pw or "", cfg["admin_password"]):
                st.session_state["sk_admin_ok"] = True
                st.rerun()
            else:
                st.error("Kata sandi salah.")
        return
    if st.button("🔒 Kunci lagi", key="btn_admin_logout"):
        st.session_state["sk_admin_ok"] = False
        st.rerun()

    try:
        n_pending = count_status(cfg, "pending")
        n_verified = count_status(cfg, "verified")
        n_corpus = corpus_count(cfg)
        pending = fetch_pending(cfg)
        verified = fetch_verified(cfg)
    except Exception as exc:
        st.error(f"Antrean belum bisa dimuat: {exc}")
        return
    m1, m2, m3 = st.columns(3)
    m1.metric("Menunggu verifikasi", n_pending)
    m2.metric("Sudah terverifikasi", n_verified)
    m3.metric("Baris korpus (corpus_export)", n_corpus)

    st.markdown("#### Antrean pending — risiko tertinggi di atas")
    if not pending:
        st.info("Antrean kosong. Tidak ada laporan menunggu verifikasi.")
    for r in pending:
        sug_label, sug_reason, sug_strength = suggest_label(r)
        sug_cat = suggest_category(r)
        badge = BAND_BADGE.get(r["model_band"], r["model_band"] or "-")
        fired = _fired_list(r)
        with st.container(border=True):
            st.markdown(
                f"**Laporan #{r['id']}** · {badge} · skor "
                f"**{r['model_score']:.3f}**"
                + (f" · sinyal: {'+'.join(fired)}" if fired else ""))
            st.markdown(f"> {r['text_scrubbed']}")
            st.caption(_report_meta(cfg, r))
            st.caption(
                f"🤖 Saran mesin ({sug_strength}): **{sug_label}** · "
                f"kategori **{sug_cat}** — {sug_reason}. Keputusan "
                f"tetap di tanganmu.")
            c1, c2, c3 = st.columns([2, 2, 1])
            label = c1.selectbox(
                "Label", LABELS, index=LABELS.index(sug_label),
                key=f"adm_label_{r['id']}")
            category = c2.selectbox(
                "Kategori modus", CATEGORIES,
                index=CATEGORIES.index(sug_cat),
                key=f"adm_cat_{r['id']}")
            gallery = c3.checkbox(
                "Tampil di galeri", value=False,
                key=f"adm_gal_{r['id']}")
            b1, b2, b3 = st.columns(3)
            if b1.button("✅ Verifikasi", type="primary",
                         key=f"adm_verify_{r['id']}"):
                verify_report(cfg, r["id"], label, category, gallery)
                st.success(f"Laporan #{r['id']} terverifikasi sebagai "
                           f"{label}.")
                st.rerun()
            if b2.button("❌ Tolak", key=f"adm_reject_{r['id']}"):
                reject_report(cfg, r["id"])
                st.success(f"Laporan #{r['id']} ditolak.")
                st.rerun()
            if b3.button("🗑️ Hapus", key=f"adm_delete_{r['id']}"):
                delete_report(cfg, r["id"])
                st.success(f"Laporan #{r['id']} dihapus (status "
                           f"deleted).")
                st.rerun()

    st.markdown("#### Terverifikasi terakhir")
    if not verified:
        st.caption("Belum ada laporan terverifikasi.")
    for r in verified:
        with st.container(border=True):
            gal = "tampil di galeri" if r["gallery_visible"] \
                else "tidak tampil di galeri"
            st.markdown(
                f"**#{r['id']}** · **{r['label']}** · "
                f"modus *{r['category_modus'] or '-'}* · {gal} · "
                f"diverifikasi {fmt_wita(r['verified_at'])}")
            st.markdown(f"> {r['text_scrubbed']}")
            b1, b2, b3 = st.columns(3)
            if r["gallery_visible"]:
                if b1.button("🙈 Sembunyikan dari galeri",
                             key=f"adm_hide_{r['id']}"):
                    set_gallery_visible(cfg, r["id"], False)
                    st.rerun()
            else:
                if b1.button("👁️ Tampilkan di galeri",
                             key=f"adm_show_{r['id']}"):
                    set_gallery_visible(cfg, r["id"], True)
                    st.rerun()
            if b2.button("↩️ Kembalikan ke antrean",
                         key=f"adm_unverify_{r['id']}"):
                unverify_report(cfg, r["id"])
                st.rerun()
            if b3.button("🗑️ Hapus", key=f"adm_vdelete_{r['id']}"):
                delete_report(cfg, r["id"])
                st.rerun()
