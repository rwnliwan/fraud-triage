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

Baru di v6.0.0 (gelombang riset kompetitor): (1) kartu langkah darurat
berbasis keadaan sesudah vonis — warga memilih keadaannya (belum klik /
sudah klik / sudah beri OTP-data / uang terkirim) dan menerima langkah
yang sesuai + tautan resmi cekrekening.id, aduannomor.id, IASC OJK.
(2) Loop tertutup: nomor laporan = nomor lacak; expander "Lacak
laporan saya" menampilkan status pemeriksaan tanpa data lain.
(3) Intake tangkapan layar + OCR (pytesseract ind+eng; biner dari
packages.txt di Streamlit Cloud) — teks bacaan diedit warga dulu,
lalu masuk alur yang sama; OCR absen/gagal tidak menggagalkan apa
pun. (4) Pengayaan intake: umur domain via RDAP publik disimpan di
reports.enrichment (info pendukung verifikasi, bukan penentu label).
(5) Anti-racun korpus: batas 3 laporan per teks sama per hari; tabel
label_log (jejak audit label) + tinjauan kedua buta atas sampel acak
terverifikasi — yang cocok menjadi "subset emas" (tampil di Analitik).

Baru di v6.1.0 (tindak lanjut kritik eksternal atas laporan v3.2):
(1) label vonis warga "HAMPIR PASTI PENIPUAN" hanya tampil bila
lapisan aturan keras terpicu — band ESKALASI dari skor model saja
memakai label yang dilunakkan ("polanya sangat mirip penipuan") plus
peringatan khusus pesan berformat resmi untuk band menengah/atas
tanpa sinyal aturan; (2) expander "Kebijakan privasi & retensi data"
di tab Lapor (PRIVACY_TEXT_V1) — isinya diverifikasi dari kode:
gambar OCR hanya diproses di memori dan tidak pernah disimpan,
hak hapus saat ini berupa penandaan status (dinyatakan apa adanya).

Konfigurasi (Streamlit secrets ATAU env; lokal: berkas mode 600
~/.config/turso/siskamling-digital.env):
    TURSO_DATABASE_URL, TURSO_AUTH_TOKEN, SISKAMLING_SENDER_SALT

Modul ini SENGAJA tidak mengimpor app.py (hindari sirkular): fungsi
render menerima engine + callback analisis dari app.py.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import os
import re
import time
import urllib.parse
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


# Kebijakan privasi & retensi (v6.1.0, tindak lanjut kritik eksternal
# butir 2.7). SETIAP klaim di teks ini diverifikasi dari kode layanan
# sendiri (submit_report, ocr_image_to_text, skema basis data) —
# jangan mengubah isinya tanpa memeriksa kode lagi:
#   * yang ditulis ke basis data HANYA teks ter-scrub (submit_report
#     menjalankan scrub() sebelum INSERT; teks mentah tidak pernah
#     ditulis), kanal, tanggal, skor/band model, sinyal aktif,
#     sender_hash (hash bergaram satu arah), text_hash, dan ringkasan
#     pengayaan domain.
#   * gambar OCR diproses di memori saja (io.BytesIO di
#     ocr_image_to_text) dan tidak pernah ditulis ke cakram / basis
#     data; yang mengalir lanjut hanya teks bacaannya.
#   * pengayaan RDAP hanya mengirim NAMA DOMAIN ke rdap.org.
#   * hak hapus saat ini = hapus lunak (delete_report: status
#     'deleted' + gallery_visible=0) — baris keluar dari galeri dan
#     view corpus_export, tetapi penghapusan fisik permanen BELUM
#     terimplementasi; teks di bawah menyatakannya apa adanya.
PRIVACY_TEXT_V1 = (
    "**Ringkasan kebijakan privasi & retensi** — ditulis merujuk "
    "UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP), "
    "dan isinya adalah keadaan layanan yang sebenarnya:\n\n"
    "**Yang disimpan dari laporan Anda:** isi pesan **setelah "
    "dibersihkan otomatis** dari data pribadi yang terdeteksi "
    "(nomor telepon, tautan pribadi, nomor rekening, dan sejenisnya) "
    "— teks asli sebelum dibersihkan **tidak pernah ditulis** ke "
    "basis data; kanal pesan dan tanggal laporan; skor serta band "
    "penilaian otomatis; dan sinyal aturan yang aktif. Bila Anda "
    "mengisi nomor pengirim, yang disimpan hanya **kode hash satu "
    "arah bergaram** — bukan nomornya, dan tidak bisa dikembalikan "
    "menjadi nomor. Formulir ini tidak meminta nama atau identitas "
    "Anda.\n\n"
    "**Gambar tangkapan layar TIDAK disimpan.** Fitur baca gambar "
    "(OCR) memproses gambar hanya di memori server untuk membaca "
    "teksnya, lalu gambar dibuang — tidak ditulis ke cakram maupun "
    "basis data. Yang masuk ke alur laporan hanyalah teks hasil "
    "bacaan, sesudah Anda periksa dan betulkan sendiri.\n\n"
    "**Pengayaan domain:** umur domain tautan di dalam pesan "
    "diperiksa ke layanan RDAP publik (rdap.org). Yang dikirim ke "
    "layanan itu **hanya nama domainnya** — bukan isi pesan, bukan "
    "nomor Anda, bukan konteks laporan.\n\n"
    "**Dasar pemrosesan:** persetujuan Anda. Mencari hasil cek dan "
    "mengirim laporan adalah permintaan Anda sendiri; pemakaian "
    "laporan untuk galeri anonim dan data latih hanya berjalan bila "
    "Anda mencentang persetujuan pada formulir (tercatat versinya di "
    "log persetujuan). Menolak tidak menghalangi Anda memakai fitur "
    "cek.\n\n"
    "**Lokasi penyimpanan:** basis data layanan berada di **Tokyo, "
    "Jepang** (layanan basis data Turso) — artinya isi laporan "
    "tersimpan di luar Indonesia. Isinya sudah dibersihkan dari data "
    "pribadi yang terdeteksi dan tidak memuat identitas Anda. Salinan "
    "cadangan berkala disimpan maksimal **8 minggu** untuk keamanan "
    "data.\n\n"
    "**Berapa lama disimpan (retensi):** laporan disimpan selama "
    "layanan berjalan atau sampai dihapus atas permintaan / "
    "keputusan pengelola; saat ini **belum ada penghapusan otomatis "
    "berdasarkan umur laporan**.\n\n"
    "**Hak Anda:** (1) mengetahui status laporan Anda — gunakan "
    "fitur **🔎 Lacak laporan saya** dengan nomor laporan Anda; "
    "(2) meminta laporan Anda **dihapus** — sampaikan nomor laporan "
    "Anda kepada pengelola layanan. Laporan yang dihapus tidak "
    "tampil di galeri dan tidak pernah masuk data latih. Jujur soal "
    "mekaniknya: penghapusan saat ini berupa **penandaan status** di "
    "basis data; penghapusan fisik permanen adalah penyempurnaan "
    "yang masih kami kerjakan.\n\n"
    "**Batas pembersihan otomatis:** pembersih bekerja dengan pola "
    "(regex) dan bisa luput pada nama atau alamat yang tertulis "
    "bebas di dalam teks. Jangan menambahkan data pribadi Anda "
    "sendiri ke kolom pesan, di luar isi pesan yang Anda terima."
)


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
    cfg = {"url": None, "token": None, "salt": None, "admin_password": None,
           "turnstile_site_key": None, "turnstile_secret": None}
    try:
        cfg["url"] = st.secrets.get("TURSO_DATABASE_URL")
        cfg["token"] = st.secrets.get("TURSO_AUTH_TOKEN")
        cfg["salt"] = st.secrets.get("SISKAMLING_SENDER_SALT")
    except Exception:
        pass
    try:
        cfg["admin_password"] = st.secrets.get(
            "SISKAMLING_ADMIN_PASSWORD")
        cfg["turnstile_site_key"] = st.secrets.get(
            "SISKAMLING_TURNSTILE_SITE_KEY")
        cfg["turnstile_secret"] = st.secrets.get(
            "SISKAMLING_TURNSTILE_SECRET")
    except Exception:
        pass
    cfg["url"] = cfg["url"] or os.environ.get("TURSO_DATABASE_URL")
    cfg["token"] = cfg["token"] or os.environ.get("TURSO_AUTH_TOKEN")
    cfg["salt"] = cfg["salt"] or os.environ.get("SISKAMLING_SENDER_SALT")
    cfg["admin_password"] = cfg["admin_password"] or os.environ.get(
        "SISKAMLING_ADMIN_PASSWORD")
    cfg["turnstile_site_key"] = cfg["turnstile_site_key"] or os.environ.get(
        "SISKAMLING_TURNSTILE_SITE_KEY")
    cfg["turnstile_secret"] = cfg["turnstile_secret"] or os.environ.get(
        "SISKAMLING_TURNSTILE_SECRET")
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
# Hardening (Fase 2.5) — batas laju, kill switch, sidik teks
#
# Pertahanan berlapis untuk formulir publik, tanpa dependensi luar:
#   * Kill switch intake di tabel app_config (kunci 'intake_open'):
#     ditutup -> warga hanya bisa cek, laporan tidak tersimpan. Bisa
#     dibalik dari tab Verifikasi ATAU langsung di basis data (jalur
#     darurat via pengelola), tanpa deploy ulang.
#   * Batas laju: per pengirim (sender_hash) per hari, total laporan
#     per hari, dan pemutus antrean (pending menumpuk -> intake jeda).
#     Jeda antar-kirim per sesi memperlambat klik beruntun.
#   * text_hash: sidik teks ter-scrub ternormalisasi (huruf kecil,
#     spasi dirapikan) untuk deteksi duplikat lintas variasi penulisan.
# CAPTCHA (Turnstile) SENGAJA belum dipasang: eskalasi bila serangan
# sungguhan muncul, agar formulir warga tetap mulus selama aman.
# ---------------------------------------------------------------------------
MAX_PER_SENDER_PER_DAY = 10
MAX_REPORTS_PER_DAY = 300
MAX_PENDING_OPEN = 500
SESSION_COOLDOWN_SEC = 20


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def text_hash_of(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def _config_value(cfg: dict, key: str):
    """Nilai app_config; None bila baris tak ada / baca gagal."""
    try:
        rows = turso_execute(
            cfg, "SELECT value FROM app_config WHERE key = ?", [key])
        return rows[0]["value"] if rows else None
    except Exception:
        return None


def _set_config(cfg: dict, key: str, value: str) -> None:
    turso_execute(
        cfg,
        "INSERT INTO app_config (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        [key, value])


def intake_open(cfg: dict) -> bool:
    """Baca kill switch; gagal baca / belum ada baris = TERBUKA."""
    return _config_value(cfg, "intake_open") != "0"


def set_intake_open(cfg: dict, open_: bool) -> None:
    _set_config(cfg, "intake_open", "1" if open_ else "0")


# ---------------------------------------------------------------------------
# Cloudflare Turnstile (anti-bot) — DORMAN secara desain.
#
# Widget hanya aktif bila KEDUA kunci terpasang di secrets/env
# (SISKAMLING_TURNSTILE_SITE_KEY + SISKAMLING_TURNSTILE_SECRET)
# DAN app_config 'turnstile_on' = '1'. Membalik flag tidak butuh
# deploy/reboot modul — jadi aktivasi saat ada indikasi serangan cukup
# satu flip (oleh pengelola dari tab Verifikasi, oleh asisten via basis
# data, atau otomatis oleh cron monitor pada lonjakan pertama).
# Tanpa kunci, flag tidak berpengaruh: formulir warga tidak berubah.
# ---------------------------------------------------------------------------
def turnstile_keys_present(cfg: dict) -> bool:
    return bool(cfg.get("turnstile_site_key")
                and cfg.get("turnstile_secret"))


def turnstile_active(cfg: dict) -> bool:
    return (turnstile_keys_present(cfg)
            and _config_value(cfg, "turnstile_on") == "1")


def set_turnstile_on(cfg: dict, on: bool) -> None:
    _set_config(cfg, "turnstile_on", "1" if on else "0")


def verify_turnstile(cfg: dict, token) -> bool:
    """Verifikasi token Turnstile ke Cloudflare siteverify (server-side)."""
    if not token:
        return False
    data = urllib.parse.urlencode(
        {"secret": cfg.get("turnstile_secret") or "",
         "response": token}).encode("utf-8")
    req = urllib.request.Request(
        "https://challenges.cloudflare.com/turnstile/v0/siteverify",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "User-Agent": "Mozilla/5.0 (Siskamling Digital)"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return bool(json.loads(
                resp.read().decode("utf-8")).get("success"))
    except Exception:
        return False


_ts_component = None


def _render_turnstile(cfg: dict):
    """Tampilkan widget Turnstile; mengembalikan token (atau None)."""
    global _ts_component
    import streamlit.components.v1 as components
    if _ts_component is None:
        # Di Streamlit Cloud, aset komponen via `path` tidak terlayani
        # (terverifikasi di perangkat asli 2026-10-23: widget error
        # "having trouble loading the component"), dan static serving
        # /app/static/ ternyata mengembalikan app shell Streamlit
        # (bukan berkas komponen) sehingga sinyal componentReady tidak
        # pernah terkirim. Halaman komponen yang sama kini dilayani
        # Worker Cloudflare `siskamling-ts` dan dideklarasikan via url.
        # Override lokal: SISKAMLING_TS_URL / SISKAMLING_TS_PATH.
        _ts_url = os.environ.get(
            "SISKAMLING_TS_URL",
            "https://siskamling-ts.rwnliwan.workers.dev/turnstile.html")
        _ts_path = os.environ.get("SISKAMLING_TS_PATH")
        if _ts_path:
            _ts_component = components.declare_component(
                "siskamling_turnstile", path=_ts_path)
        else:
            _ts_component = components.declare_component(
                "siskamling_turnstile", url=_ts_url)
    return _ts_component(sitekey=cfg.get("turnstile_site_key"),
                         default=None, key="sk_turnstile")


def _turnstile_passed(cfg: dict, token) -> bool:
    """Token lolos siteverify; token yang sama tidak diverifikasi ulang
    dalam satu sesi (token Turnstile sekali pakai di sisi Cloudflare)."""
    if not token:
        return False
    if st.session_state.get("sk_ts_token") == token:
        return True
    if verify_turnstile(cfg, token):
        st.session_state["sk_ts_token"] = token
        return True
    return False


def sender_today_count(cfg: dict, sender_hash: str | None) -> int:
    if not sender_hash:
        return 0
    return turso_execute(
        cfg, "SELECT COUNT(*) AS n FROM reports WHERE sender_hash = ? "
             "AND created_at >= date('now')", [sender_hash])[0]["n"]


def reports_today_count(cfg: dict) -> int:
    return turso_execute(
        cfg, "SELECT COUNT(*) AS n FROM reports "
             "WHERE created_at >= date('now')")[0]["n"]


# ---------------------------------------------------------------------------
# v6.0 — pengayaan intake, OCR, lacak laporan, jejak label, anti-racun
#
# Dari riset kompetitor (ScamShield SG, SmishTank, IASC): yang membuat
# layanan anti-penipuan terasa hidup bagi warga adalah (a) langkah
# darurat yang sesuai KEADAAN korban, bukan vonis generik; (b) laporan
# yang bisa DILACAK balik (loop tertutup); (c) pengayaan konteks saat
# laporan masuk, sebelum tautan penipu mati. Ditambah pertahanan
# korpus: korpus dari laporan publik adalah permukaan serangan
# (peracunan data latih), jadi teks-sama dibatasi per hari dan setiap
# keputusan label punya jejak audit + tinjauan kedua.
# ---------------------------------------------------------------------------
CEKREKENING_URL = "https://cekrekening.id"
ADUANNOMOR_URL = "https://aduannomor.id"
IASC_URL = "https://iasc.ojk.go.id"
MAX_SAME_TEXT_PER_DAY = 3
MAX_ENRICH_DOMAINS = 3


def same_text_today_count(cfg: dict, th: str | None) -> int:
    """Berapa laporan dengan sidik teks sama sudah masuk HARI INI."""
    if not th:
        return 0
    return turso_execute(
        cfg, "SELECT COUNT(*) AS n FROM reports WHERE text_hash = ? "
             "AND created_at >= date('now')", [th])[0]["n"]


# --- Pengayaan: umur domain via RDAP publik (tanpa kunci API) --------
_LINK_MARK_RE = re.compile(r"\[tautan:\s*([^\]]+)\]")


def extract_domains(clean_text: str) -> list:
    """Domain dari penanda [tautan: host] pada teks TER-SCRUB — urutan
    kemunculan, tanpa duplikat. Scrubber memang mempertahankan domain
    sebagai sinyal modus, jadi pengayaan bekerja di atas teks bersih
    yang sama dengan yang tersimpan."""
    seen, out = set(), []
    for m in _LINK_MARK_RE.finditer(clean_text or ""):
        host = m.group(1).strip().lower()
        if host and host not in seen:
            seen.add(host)
            out.append(host)
    return out


def _rdap_lookup(domain: str) -> dict | None:
    """Satu lookup RDAP (rdap.org mengalihkan ke registri berwenang).

    Kembalikan {domain, registered, age_days, registrar?} atau None
    bila gagal — pengayaan TIDAK BOLEH menggagalkan laporan warga."""
    url = "https://rdap.org/domain/" + urllib.parse.quote(domain)
    req = urllib.request.Request(
        url, headers={
            "User-Agent": "Mozilla/5.0 (Siskamling Digital)",
            "Accept": "application/rdap+json, application/json"})
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None
    info = {"domain": domain}
    for ev in data.get("events") or []:
        if ev.get("eventAction") in ("registration", "registered"):
            raw = (ev.get("eventDate") or "")[:10]
            try:
                born = datetime.strptime(raw, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc)
                info["registered"] = raw
                info["age_days"] = (
                    datetime.now(timezone.utc) - born).days
            except ValueError:
                pass
            break
    for ent in data.get("entities") or []:
        if "registrar" in (ent.get("roles") or []):
            vcard = ent.get("vcardArray") or [None, []]
            for item in (vcard[1] if len(vcard) > 1 else []) or []:
                if item and item[0] == "fn" and len(item) > 3:
                    info["registrar"] = str(item[3])[:80]
            break
    return info


def build_enrichment(clean_text: str) -> str | None:
    """Ringkasan pengayaan intake sebagai string JSON (atau None bila
    teks tak memuat domain / semua lookup gagal total)."""
    domains = extract_domains(clean_text)[:MAX_ENRICH_DOMAINS]
    if not domains:
        return None
    items = []
    for d in domains:
        info = _rdap_lookup(d)
        items.append(info if info else {"domain": d})
    return json.dumps(
        {"domains": items,
         "checked_at": datetime.now(timezone.utc).strftime(
             "%Y-%m-%d %H:%M:%S")},
        ensure_ascii=False)


def enrichment_summary(enrichment_json) -> str:
    """Ringkas pengayaan untuk kartu verifikasi — selalu dibingkai
    sebagai info pendukung, bukan penentu label."""
    if not enrichment_json:
        return ""
    try:
        data = json.loads(enrichment_json)
    except (TypeError, ValueError):
        return ""
    parts = []
    for it in data.get("domains") or []:
        s = it.get("domain") or "?"
        if it.get("age_days") is not None:
            days = it["age_days"]
            umur = (f"±{days} hari" if days < 730
                    else f"±{max(days // 365, 1)} tahun")
            s += f" (terdaftar {it.get('registered', '?')}, umur {umur}"
            if it.get("registrar"):
                s += f", registrar {it['registrar']}"
            s += ")"
        else:
            s += " (umur domain tidak terbaca)"
        parts.append(s)
    return " · ".join(parts)


# --- OCR tangkapan layar (pytesseract; biner dari packages.txt) -------
def ocr_image_to_text(image_bytes: bytes) -> tuple[str, str]:
    """Baca teks pesan dari tangkapan layar (bahasa ind+eng).

    Kembalikan (teks, status): 'ok' (ada teks), 'empty' (tak terbaca
    teks), 'unavailable' (mesin OCR/pustaka tidak ada di server ini),
    'error' (berkas bukan gambar yang bisa dibuka). Status apa pun
    selain 'ok' ditangani UI dengan arahan tempel manual — OCR yang
    gagal tidak pernah menggagalkan warga."""
    try:
        import pytesseract
        from PIL import Image
    except Exception:
        return "", "unavailable"
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.load()
    except Exception:
        return "", "error"
    try:
        try:
            text = pytesseract.image_to_string(img, lang="ind+eng")
        except Exception:
            text = pytesseract.image_to_string(img, lang="eng")
    except Exception:
        return "", "unavailable"
    text = (text or "").strip()
    return (text, "ok") if text else ("", "empty")


# --- Lacak laporan (loop tertutup) ------------------------------------
TRACK_LABEL_WARGA = {"SMISHING": "penipuan", "SAH": "bukan penipuan",
                     "SPAM_PROMO": "spam / promosi"}


def fetch_report_status(cfg: dict, report_id: int):
    """Status SATU laporan untuk fitur lacak warga. Yang diambil hanya
    status, label, dan tanggal — teks pesan, hash, dan data lain TIDAK
    pernah ikut, jadi tidak ada yang bisa bocor lewat nomor lacak."""
    rows = turso_execute(
        cfg,
        "SELECT status, label, created_at, verified_at FROM reports "
        "WHERE id = ?", [int(report_id)])
    return rows[0] if rows else None


# --- Jejak audit label + subset emas (label_log, migrasi v6.0) --------
def _log_label(cfg: dict, report_id: int, aksi: str,
               label: str | None = None,
               actor: str = "verifikator") -> None:
    """Catat satu aksi label ke label_log. Gagal catat TIDAK boleh
    menggagalkan aksi verifikasinya sendiri (jejak bersifat audit,
    bukan gerbang)."""
    try:
        turso_execute(
            cfg,
            "INSERT INTO label_log (report_id, aksi, label, actor) "
            "VALUES (?, ?, ?, ?)",
            [int(report_id), aksi, label, actor])
    except Exception:
        pass


def gold_count(cfg: dict) -> int:
    """Jumlah laporan terverifikasi yang LOLOS tinjauan kedua dengan
    label yang sama — definisi 'subset emas' korpus."""
    try:
        return turso_execute(
            cfg,
            "SELECT COUNT(*) AS n FROM reports r "
            "WHERE r.status = 'verified' AND EXISTS ("
            "SELECT 1 FROM label_log l WHERE l.report_id = r.id "
            "AND l.aksi = 'tinjauan_kedua' AND l.label = r.label)"
        )[0]["n"]
    except Exception:
        return 0


def fetch_second_review_sample(cfg: dict, limit: int = 3) -> list:
    """Sampel ACAK laporan terverifikasi yang belum ditinjau kedua."""
    try:
        return turso_execute(
            cfg,
            "SELECT * FROM reports r WHERE r.status = 'verified' "
            "AND NOT EXISTS (SELECT 1 FROM label_log l "
            "WHERE l.report_id = r.id AND l.aksi = 'tinjauan_kedua') "
            "ORDER BY RANDOM() LIMIT ?", [int(limit)])
    except Exception:
        return []


def second_review(cfg: dict, report_id: int, label: str) -> str:
    """Catat tinjauan kedua atas satu laporan terverifikasi.

    Kembalikan 'cocok' (label sama -> masuk subset emas), 'beda'
    (dicatat sebagai perbedaan; label asli TIDAK diubah — mengubah
    label adalah keputusan peninjau utama), atau 'hilang' (baris
    tidak lagi terverifikasi)."""
    rows = turso_execute(
        cfg, "SELECT label FROM reports WHERE id = ? "
             "AND status = 'verified'", [int(report_id)])
    if not rows:
        return "hilang"
    _log_label(cfg, report_id, "tinjauan_kedua", label)
    return "cocok" if rows[0]["label"] == label else "beda"


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
    # Pengayaan intake (v6.0): umur domain dari teks ter-scrub via RDAP
    # publik. Best-effort — kegagalan lookup TIDAK menggagalkan simpan.
    try:
        enrichment = build_enrichment(clean_text)
    except Exception:
        enrichment = None
    rows = turso_execute(
        cfg,
        "INSERT INTO reports (channel, text_scrubbed, model_score, "
        "model_band, rules_fired, consent_data_use, consent_at, "
        "sender_hash, text_hash, enrichment) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "RETURNING id, created_at",
        [channel, clean_text, float(score), BAND_STORE[band_final],
         json.dumps(rules_fired), 1 if consent_data_use else 0,
         datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
         if consent_data_use else None,
         sender_hash, text_hash_of(clean_text), enrichment])
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
    """Agregat aman-publik untuk kepala galeri.

    Dulu tiga statement terpisah = tiga perjalanan HTTP ke Turso
    (±0,9–1,2 dtk per perjalanan secara lokal); kini SATU statement
    dengan subquery skalar — hasil identik, satu perjalanan."""
    row = turso_execute(
        cfg,
        "SELECT (SELECT COUNT(*) FROM reports) AS total, "
        "(SELECT COUNT(*) FROM reports WHERE status = 'verified') "
        "AS verified, "
        "(SELECT COUNT(DISTINCT sender_hash) FROM reports "
        "WHERE sender_hash IS NOT NULL) AS senders")[0]
    return {"total": row["total"], "verified": row["verified"],
            "senders": row["senders"]}


# Cache pendek untuk data publik: statistik & galeri dibaca pada
# SETIAP run penuh (hero tab Lapor + tab Galeri mengeksekusi walau
# tidak sedang dibuka), dan isinya hanya berubah saat ada laporan /
# verifikasi baru — TTL 60 dtk membuat rerun interaksi warga tidak
# membayar ulang perjalanan Turso yang sama. Kunci cache = URL basis
# data (bukan kredensial); cfg diteruskan sebagai argumen tak-terhash.
@st.cache_data(ttl=60, show_spinner=False)
def _cached_public_stats(_cfg: dict, scope: str) -> dict:
    return fetch_public_stats(_cfg)


@st.cache_data(ttl=60, show_spinner=False)
def _cached_gallery(_cfg: dict, scope: str, limit: int = 30) -> list:
    return fetch_gallery(_cfg, limit)


def fetch_lapor_state(cfg: dict) -> dict:
    """Status intake tab Lapor dalam SATU statement: kill switch,
    flag Turnstile, dan jumlah pending (dulu 3 statement terpisah =
    3 perjalanan HTTP sebelum formulir warga selesai digambar)."""
    rows = turso_execute(
        cfg,
        "SELECT (SELECT value FROM app_config WHERE key = "
        "'intake_open') AS intake_open, "
        "(SELECT value FROM app_config WHERE key = 'turnstile_on') "
        "AS turnstile_on, "
        "(SELECT COUNT(*) FROM reports WHERE status = 'pending') "
        "AS pending_count")
    row = rows[0] if rows else {}
    return {"intake_open": row.get("intake_open") != "0",
            "pending": int(row.get("pending_count") or 0),
            "turnstile_on": row.get("turnstile_on") == "1"}


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
def _render_hero(cfg: dict, db_ready: bool) -> None:
    """Hero warga (UI/UX Opsi A): janji + 3 langkah + bukti sosial."""
    st.markdown("### 🛡️ Cek dulu, sebelum klik.")
    st.markdown(
        "**1.** Tempel pesan mencurigakan di bawah → **2.** Lihat "
        "vonisnya → **3.** Laporkan, supaya warga lain tidak kena "
        "modus yang sama.")
    if db_ready:
        try:
            stats = _cached_public_stats(cfg, cfg.get("url") or "")
            if stats["verified"] or stats["total"]:
                st.caption(
                    f"🏘️ Sudah ada **{stats['verified']} modus "
                    f"terverifikasi** di galeri dan **{stats['total']} "
                    "laporan warga** masuk. Setiap laporan diverifikasi "
                    "manual oleh pengelola sebelum tampil ke publik.")
        except Exception:
            pass


SIGNAL_WARGA = {
    "S1": "ada tautan di dalam pesan",
    "S2": "meminta memasukkan kata sandi / kode OTP / data pribadi "
          "lewat tautan",
    "S3": "mengancam akun diblokir atau hangus disertai desakan waktu",
}


def render_citizen_verdict(analysis: dict) -> None:
    """Vonis bahasa warga + langkah tindakan (UI/UX Opsi A).

    Zona model dipetakan ke tiga tingkat (merah/kuning/hijau) dengan
    tindakan konkret; bahasanya awam dan tidak melebih-lebihkan —
    detail teknis (skor, sinyal) tersedia di expander sesudahnya.

    v6.1.0 (tindak lanjut kritik eksternal atas laporan v3.2, butir
    2.5): label tegas "HAMPIR PASTI PENIPUAN" kini HANYA tampil bila
    lapisan aturan keras benar-benar terpicu (>= 2 sinyal kuat S1/S2/
    S3). Bila band ESKALASI datang dari skor model saja, labelnya
    dilunakkan — skor mesin bukan vonis pasti — dan untuk band
    menengah/atas tanpa sinyal aturan ditambah peringatan khusus
    pesan berformat resmi (model paling sering salah justru pada
    pesan resmi bank/lembaga). Skor, ambang, dan band TIDAK berubah;
    yang berubah hanya bahasanya.
    """
    zone = analysis["final_zone"]
    rule = analysis["rule"]
    hard_fired = bool(rule["triggered"])
    signals = [SIGNAL_WARGA[s] for s in rule["active_signals"]
               if s in SIGNAL_WARGA]
    if zone == "ESKALASI":
        if hard_fired:
            st.error(
                "🔴 **HAMPIR PASTI PENIPUAN.** Pesan ini memuat "
                "kombinasi tanda bahaya terkuat (lihat tanda bahaya "
                "di bawah). Jangan klik tautan apa pun di pesan ini "
                "dan jangan membalasnya.")
        else:
            st.error(
                "🔴 **POLANYA SANGAT MIRIP PENIPUAN.** Penilaian "
                "otomatis atas pesan ini sangat tinggi — tetapi ini "
                "skor mesin, bukan vonis pasti. Perlakukan seperti "
                "penipuan: jangan klik tautan apa pun di pesan ini, "
                "jangan membalasnya, dan verifikasi lewat kanal resmi "
                "(lihat catatan di bawah).")
        st.markdown(
            "- ⛔ **Jangan pernah berikan kode OTP, PIN, atau kata "
            "sandi** — bank dan e-wallet TIDAK PERNAH memintanya lewat "
            "pesan.\n"
            "- 🚫 **Blokir dan laporkan pengirimnya** di aplikasi "
            "pesanmu.\n"
            "- 📞 **Bila kamu sempat mengklik atau mengisi data:** "
            "segera hubungi bank/e-wallet lewat nomor resmi di kartumu, "
            "ganti kata sandi, dan pantau mutasi rekeningmu.")
    elif zone == "REVIEW ANALIS":
        st.warning(
            "🟡 **MENCURIGAKAN — anggap penipuan sampai terbukti "
            "sebaliknya.** Pesan ini punya tanda bahaya, meski "
            "buktinya belum cukup untuk vonis pasti.")
        st.markdown(
            "- Jangan bertindak dari pesan ini. **Buka aplikasi resmi "
            "sendiri** (ketik manual), jangan lewat tautan di pesan.\n"
            "- Bila mengaku dari bank/instansi, **telepon nomor "
            "resmi** di kartu atau situs resmi mereka — bukan nomor "
            "yang ada di pesan.")
    else:
        st.success(
            "🟢 **Kemungkinan besar aman.** Tidak ditemukan tanda "
            "penipuan yang kuat pada pesan ini.")
        st.markdown(
            "Tetap waspada: ini penilaian otomatis, **bukan jaminan**. "
            "Jangan kirim uang atau kode hanya karena sebuah pesan "
            "lolos cek — penipu terus berganti modus. Bila ragu, "
            "tanyakan dulu ke orang yang kamu percaya.")
    if zone in ("ESKALASI", "REVIEW ANALIS") and not hard_fired:
        st.info(
            "⚠️ **Catatan pesan berformat resmi:** pemeriksa ini "
            "belum andal menilai pesan resmi bank/lembaga — modelnya "
            "justru paling sering salah pada pesan berformat resmi. "
            "Bila pesan ini mengaku dari bank atau instansi Anda, "
            "jangan putuskan hanya dari hasil ini: buka aplikasi "
            "resminya sendiri (ketik manual) atau telepon nomor resmi "
            "di kartu / situs resmi lembaga tersebut.")
    if signals:
        st.markdown("**Tanda bahaya yang ditemukan:** "
                    + "; ".join(signals) + ".")


def render_emergency_card(analysis: dict) -> None:
    """Kartu langkah darurat berbasis KEADAAN (v6.0).

    Vonis saja tidak cukup bagi warga yang SUDAH berinteraksi dengan
    pesan penipuan — yang mereka butuhkan langkah sesuai keadaannya,
    sekarang juga. Hanya tampil untuk vonis 🔴/🟡 (pada vonis 🟢 warga
    bukan korban; kartu darurat hanya jadi kebisingan). Keadaan
    terberat (uang terkirim) menaruh langkah tercepat paling atas:
    hubungi bank + lapor IASC agar rekening penipu bisa dibekukan.
    """
    if analysis["final_zone"] not in ("ESKALASI", "REVIEW ANALIS"):
        return
    st.markdown("#### ⚠️ Sudah terlanjur melakukan sesuatu "
                "dari pesan ini?")
    st.caption("Jangan panik — pilih keadaanmu; langkahnya menyesuaikan. "
               "Bertindak cepat membuat perbedaan besar.")
    state = st.radio(
        "Keadaan saya saat ini:",
        ["Belum — saya belum mengklik apa pun",
         "Sudah klik tautan, tapi belum memasukkan data apa pun",
         "Sudah memasukkan kode OTP / kata sandi / data pribadi",
         "Uang sudah terkirim / saldo sudah berkurang"],
        key="sk_em_state", index=None)
    if state is None:
        return
    if state.startswith("Belum"):
        st.success(
            "✅ **Kamu masih aman.** Pesannya belum sempat menyentuhmu. "
            "Lakukan ini:\n"
            "- **Jangan klik** tautan di pesan itu dan jangan membalas.\n"
            "- **Blokir + hapus** pesan dan pengirimnya.\n"
            f"- Laporkan nomor pengirimnya ke [aduannomor.id]"
            f"({ADUANNOMOR_URL}) agar nomor itu diperiksa petugas dan "
            "bisa diblokir untuk semua orang.")
    elif state.startswith("Sudah klik"):
        st.warning(
            "🟡 **Tutup halamannya sekarang**, lalu:\n"
            "- Bila ada berkas/aplikasi (APK) yang terunduh, **jangan "
            "dibuka — hapus** dari ponselmu.\n"
            "- Bila kamu sempat masuk (login) di halaman itu, **ganti "
            "kata sandi akun tersebut lewat aplikasi resminya** — "
            "bukan lewat tautan tadi.\n"
            "- Pantau aktivitas akun & mutasi rekeningmu beberapa "
            "hari ke depan; ada yang janggal, segera hubungi bank.")
    elif state.startswith("Sudah memasukkan"):
        st.error(
            "🔴 **Anggap datamu sudah di tangan penipu — bertindak "
            "sekarang:**\n"
            "1. **Hubungi bank / e-wallet lewat nomor resmi** di "
            "kartumu: minta blokir akses dan ganti kata sandi & PIN.\n"
            "2. Ganti juga kata sandi akun lain yang memakai kata "
            "sandi yang sama.\n"
            f"3. Bila ada rekening tujuan penipu, laporkan ke "
            f"[IASC OJK]({IASC_URL}) dan cek rekeningnya di "
            f"[cekrekening.id]({CEKREKENING_URL}).\n"
            f"4. Laporkan nomor pengirimnya di [aduannomor.id]"
            f"({ADUANNOMOR_URL}).\n"
            "Ingat: kode OTP berikutnya yang masuk **jangan pernah "
            "diberikan ke siapa pun**.")
    else:
        st.error(
            "🔴 **Bertindak CEPAT — peluang dana kembali paling besar "
            "di jam-jam pertama:**\n"
            "1. **Telepon bankmu SEKARANG** (nomor resmi di kartu): "
            "minta dana ditahan/diblokir dan catat nomor laporan dari "
            "bank.\n"
            f"2. **Lapor ke [IASC OJK]({IASC_URL})** — Indonesia "
            "Anti-Scam Centre bisa mengupayakan **pembekuan rekening "
            "penipu**.\n"
            f"3. Cek & laporkan rekening tujuan di "
            f"[cekrekening.id]({CEKREKENING_URL}) agar warga lain "
            "terlindungi.\n"
            f"4. Laporkan nomor pengirimnya di [aduannomor.id]"
            f"({ADUANNOMOR_URL}).\n"
            "5. **Simpan semua bukti**: tangkapan layar pesan, nomor "
            "pengirim, rekening tujuan, dan jam kejadian — dibutuhkan "
            "untuk laporan ke bank, IASC, dan polisi.")


def _render_track_expander(cfg: dict, db_ready: bool) -> None:
    """Loop tertutup (v6.0): warga melacak status laporannya sendiri
    hanya dengan nomor laporan. Yang tampil status + label bahasa
    warga + tanggal — isi laporan dan data lain tidak ditampilkan."""
    with st.expander("🔎 Lacak laporan saya"):
        st.caption(
            "Masukkan **nomor laporan** yang kamu terima saat "
            "mengirim (contoh: 12). Yang tampil hanya status "
            "pemeriksaannya — isi laporanmu dan data lain tidak "
            "ditampilkan di sini.")
        if not db_ready:
            st.info("Pelacakan belum aktif pada deployment ini "
                    "(basis data belum terhubung).")
            return
        num = st.number_input(
            "Nomor laporan", min_value=1, step=1, value=None,
            key="sk_track_num", placeholder="contoh: 12")
        if st.button("Cek status laporan", key="btn_track"):
            if not num:
                st.warning("Isi dulu nomor laporannya.")
            else:
                try:
                    row = fetch_report_status(cfg, int(num))
                except Exception as exc:
                    st.error(f"Status belum bisa dimuat: {exc}")
                    row = None
                st.session_state["sk_track_row"] = row
                st.session_state["sk_track_for"] = int(num)
        row = st.session_state.get("sk_track_row")
        if row is None and st.session_state.get("sk_track_for"):
            st.warning(
                "Nomor laporan tidak ditemukan. Periksa lagi "
                "nomornya — atau laporan mungkin sudah dihapus atas "
                "permintaan pelapor (hak hapus).")
        elif row is not None:
            if row["status"] == "deleted":
                st.warning(
                    "Nomor laporan tidak ditemukan. Periksa lagi "
                    "nomornya — atau laporan mungkin sudah dihapus "
                    "atas permintaan pelapor (hak hapus).")
            elif row["status"] == "pending":
                st.info(
                    "⏳ **Masih menunggu pemeriksaan tim** — diterima "
                    f"{fmt_wita(row['created_at'])}. Label hanya "
                    "ditentukan manusia, jadi mohon ditunggu; cek "
                    "lagi nanti dengan nomor yang sama.")
            elif row["status"] == "verified":
                label_w = TRACK_LABEL_WARGA.get(
                    row["label"], row["label"] or "-")
                st.success(
                    "✅ **Sudah diperiksa** "
                    f"({fmt_wita(row['verified_at'])}) — hasil "
                    f"pemeriksaan manusia: **{label_w}**.")
            elif row["status"] == "rejected":
                st.info(
                    "Laporan ini **ditutup** oleh tim — tidak lolos "
                    "pemeriksaan (misalnya bukan pesan yang bisa "
                    "diverifikasi, atau duplikat). Terima kasih "
                    "sudah melapor.")


def render_lapor_tab(engine, analyze_one, card_html) -> None:
    st.markdown("## 📮 Lapor & Cek Pesan Mencurigakan")
    st.markdown(
        "Tempel pesan yang Anda terima — sistem memberi **hasil cek "
        "awal** dari model pendeteksi yang sama dengan tab Analisis "
        "Tunggal, dan Anda dapat **melaporkannya** agar warga lain "
        "terlindungi. Setiap laporan tercatat dengan **nomor laporan "
        "unik** dan **tanggal submit** sebagai bukti penerimaan.")
    cfg = load_config()
    db_ready = bool(cfg.get("url") and cfg.get("token"))
    _render_hero(cfg, db_ready)
    with st.expander("Baca dulu — cara kerja, data & persetujuan (v1)"):
        st.markdown(CONSENT_TEXT_V1)
    with st.expander("🔐 Kebijakan privasi & retensi data"):
        st.markdown(PRIVACY_TEXT_V1)

    if not db_ready:
        st.warning(
            "Penyimpanan laporan belum aktif pada deployment ini "
            "(kredensial basis data belum dipasang) — fitur **cek** "
            "tetap bisa dipakai, laporan belum bisa dikirim.")

    # Hardening Fase 2.5: status kill switch + pemutus antrean.
    intake_is_open = True
    queue_full = False
    ts_active = False
    if db_ready:
        try:
            state = fetch_lapor_state(cfg)
            intake_is_open = state["intake_open"]
            queue_full = state["pending"] >= MAX_PENDING_OPEN
            ts_active = (turnstile_keys_present(cfg)
                         and state["turnstile_on"])
        except Exception:
            intake_is_open, queue_full, ts_active = True, False, False
    if db_ready and not intake_is_open:
        st.warning(
            "⏸️ **Penerimaan laporan sedang ditutup sementara** oleh "
            "pengelola. Fitur **cek tetap bisa dipakai** — hasil cek "
            "tampil seperti biasa, hanya saja laporan tidak tersimpan.")
    elif db_ready and queue_full:
        st.warning(
            "⏸️ **Antrean verifikasi sedang penuh** — perlindungan "
            "anti-banjir aktif. Fitur cek tetap bisa dipakai; laporan "
            "baru sementara tidak tersimpan.")

    channel_label = st.selectbox(
        "Kanal pesan", list(CHANNELS.values()), key="sk_channel")
    channel = [k for k, v in CHANNELS.items() if v == channel_label][0]
    sender = st.text_input(
        "Nomor pengirim pesan (opsional)",
        key="sk_sender",
        placeholder="cth. 0812xxxxxxx — hanya disimpan sebagai kode "
                    "hash satu arah, tidak pernah dalam bentuk asli")
    with st.expander("📷 Punya tangkapan layar pesannya? "
                     "Baca teksnya dari gambar"):
        st.caption(
            "Unggah tangkapan layar (screenshot) pesan — teksnya "
            "dibaca otomatis (OCR), lalu bisa Anda periksa & betulkan "
            "sebelum dipakai. Gambar TIDAK disimpan; yang diproses "
            "hanya teks hasil bacaannya.")
        up = st.file_uploader(
            "Unggah gambar tangkapan layar (PNG/JPG)",
            type=["png", "jpg", "jpeg"], key="sk_ocr_file")
        if up is not None and st.button(
                "🔎 Baca teks dari gambar", key="btn_ocr_run"):
            with st.spinner("Membaca teks pada gambar…"):
                ocr_text, ocr_status = ocr_image_to_text(up.getvalue())
            if ocr_status == "ok":
                st.session_state["sk_ocr_text"] = ocr_text
            elif ocr_status == "unavailable":
                st.warning(
                    "Fitur baca gambar belum aktif di server ini — "
                    "tidak apa-apa: salin teks pesannya secara manual "
                    "ke kolom **Isi pesan** di bawah.")
            elif ocr_status == "empty":
                st.warning(
                    "Tidak terbaca teks pada gambar itu. Coba "
                    "tangkapan layar yang lebih jelas/terang, atau "
                    "tempel teksnya manual di kolom **Isi pesan**.")
            else:
                st.warning(
                    "Gambar tidak bisa dibuka. Coba berkas PNG/JPG "
                    "lain, atau tempel teksnya manual di bawah.")
        if st.session_state.get("sk_ocr_text"):
            ocr_edited = st.text_area(
                "Teks hasil bacaan gambar — periksa & betulkan dulu",
                value=st.session_state["sk_ocr_text"],
                key="sk_ocr_edit", height=110, max_chars=2000)
            if st.button("⬇️ Pakai teks ini sebagai isi pesan",
                         key="btn_ocr_use"):
                st.session_state["sk_text"] = ocr_edited
                st.session_state.pop("sk_ocr_text", None)
                st.rerun()
    text = st.text_area(
        "Isi pesan", key="sk_text", height=130, max_chars=2000,
        placeholder="Tempel isi SMS / pesan persis seperti yang Anda "
                    "terima…")
    consent = st.checkbox(CONSENT_CHECKBOX_V1, key="sk_consent")
    st.caption(
        "Tanpa mencentang pun laporan tetap terkirim dan tercatat — "
        "hanya saja tidak tampil di galeri dan tidak dipakai sebagai "
        "data latih.")

    ts_token = None
    if ts_active:
        st.markdown(
            "**Verifikasi anti-bot aktif** — selesaikan uji singkat "
            "berikut sebelum mengirim (melindungi layanan dari bot):")
        ts_token = _render_turnstile(cfg)

    if st.button("🔍 Cek & Kirim Laporan", type="primary",
                 key="btn_sk_submit"):
        raw = (text or "").strip()
        if not raw:
            st.warning("Isi dulu teks pesannya.")
        elif time.time() - st.session_state.get(
                "sk_last_submit_ts", 0) < SESSION_COOLDOWN_SEC:
            st.warning(
                f"Baru saja mengirim — tunggu ±{SESSION_COOLDOWN_SEC} "
                "detik sebelum mengirim lagi (perlindungan anti-banjir).")
        elif ts_active and not _turnstile_passed(cfg, ts_token):
            st.warning(
                "Verifikasi anti-bot belum selesai atau gagal — "
                "selesaikan uji singkatnya di atas, lalu klik "
                "**Cek & Kirim Laporan** sekali lagi. Cek belum "
                "dijalankan agar layanan terlindung dari bot.")
        else:
            # Gerbang simpan (hardening): kill switch, pemutus antrean,
            # batas per pengirim & batas harian global. Hasil CEK tetap
            # diberikan; yang ditahan hanya penyimpanannya.
            sender_raw = (sender or "").strip() or None
            can_store = db_ready and intake_is_open and not queue_full
            block_reason = None
            if db_ready and can_store:
                try:
                    s_hash = hash_sender(sender_raw, cfg.get("salt")) \
                        if sender_raw else None
                except Exception:
                    s_hash = None
                try:
                    if s_hash and sender_today_count(
                            cfg, s_hash) >= MAX_PER_SENDER_PER_DAY:
                        can_store = False
                        block_reason = (
                            f"batas {MAX_PER_SENDER_PER_DAY} laporan "
                            "per pengirim per hari tercapai")
                    elif reports_today_count(cfg) >= MAX_REPORTS_PER_DAY:
                        can_store = False
                        block_reason = ("batas laporan harian layanan "
                                         "tercapai")
                except Exception:
                    can_store = True  # gagal cek batas != blokir warga
                if can_store:
                    # Anti-racun korpus (v6.0): teks yang sama persis
                    # dibatasi per hari — banjir salinan adalah pola
                    # peracunan data latih, bukan antusiasme warga.
                    try:
                        clean_preview, _f = scrub(raw)
                        if same_text_today_count(
                                cfg, text_hash_of(clean_preview)) \
                                >= MAX_SAME_TEXT_PER_DAY:
                            can_store = False
                            block_reason = (
                                "pesan yang sama persis sudah "
                                "dilaporkan 3 kali atau lebih hari "
                                "ini — kami anggap duplikat berlebih")
                    except Exception:
                        pass  # gagal cek != blokir warga
            with st.spinner("Menilai pesan…"):
                analysis = analyze_one(engine, raw)
            st.session_state["sk_last"] = analysis
            st.session_state["sk_receipt"] = None
            if can_store:
                rule = analysis["rule"]
                rules_fired = list(rule["active_signals"])
                if rule.get("calm", {}).get("lowered"):
                    rules_fired.append("PENENANG")
                try:
                    report_id, created_at = submit_report(
                        cfg, channel=channel, raw_text=raw,
                        sender_raw=sender_raw,
                        consent_data_use=bool(consent),
                        score=analysis["res"]["p_scam"],
                        band_final=analysis["final_zone"],
                        rules_fired=rules_fired)
                    st.session_state["sk_receipt"] = {
                        "id": report_id, "created_at": created_at,
                        "consent": bool(consent)}
                    st.session_state["sk_last_submit_ts"] = time.time()
                except Exception as exc:
                    st.error(f"Laporan gagal tersimpan: {exc}")
            elif db_ready:
                st.info(
                    "Hasil cek tampil di bawah, tetapi laporan ini "
                    "**tidak tersimpan**: "
                    + (block_reason
                       or "penerimaan laporan sedang ditutup/"
                          "antrean penuh")
                    + " (perlindungan anti-banjir). Terima kasih — "
                      "hasil ceknya tetap berlaku untukmu.")

    receipt = st.session_state.get("sk_receipt")
    if receipt:
        st.success(
            f"✅ **Laporan terkirim & tercatat.** Nomor laporan Anda: "
            f"**#{receipt['id']}** · diterima "
            f"**{fmt_wita(receipt['created_at'])}** · status awal: "
            f"menunggu verifikasi tim. **Simpan nomor ini sebagai "
            f"nomor lacak** — status pemeriksaannya bisa Anda cek "
            f"kapan saja di bagian **🔎 Lacak laporan saya** di "
            f"bawah."
            + (" Persetujuan penggunaan data: **ya** (galeri anonim + "
               "data latih)." if receipt["consent"]
               else " Persetujuan penggunaan data: **tidak** (hanya "
                    "untuk cek & verifikasi)."))
    analysis = st.session_state.get("sk_last")
    if analysis:
        st.markdown("#### Hasil cek pesan ini")
        render_citizen_verdict(analysis)
        with st.expander("🔬 Detail teknis — skor model & sinyal",
                         expanded=False):
            st.markdown(card_html(analysis), unsafe_allow_html=True)
        st.caption(
            "Hasil cek adalah triase awal, bukan vonis. Jangan pernah "
            "membagikan kode OTP, PIN, atau kata sandi kepada siapa "
            "pun, apa pun hasil ceknya.")
        render_emergency_card(analysis)
    _render_track_expander(cfg, db_ready)


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
        stats = _cached_public_stats(cfg, cfg.get("url") or "")
        rows = _cached_gallery(cfg, cfg.get("url") or "")
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
    cat_labels = {
        "blokir_akun": "Ancaman blokir akun", "otp_palsu": "OTP palsu",
        "resi_paket": "Resi / paket", "undian": "Undian / hadiah",
        "apk": "Suruh pasang APK", "investasi": "Investasi bodong",
        "tagihan": "Tagihan palsu", "lainnya": "Lainnya"}
    choice = st.selectbox(
        "Saring menurut kategori modus",
        options=["semua"] + CATEGORIES,
        format_func=lambda s: "Semua kategori" if s == "semua"
        else cat_labels.get(s, s),
        key="gal_filter")
    if choice != "semua":
        rows = [r for r in rows if r.get("category_modus") == choice]
        if not rows:
            st.info("Belum ada modus terverifikasi pada kategori ini.")
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


def duplicate_text_count(cfg: dict, row: dict) -> int:
    """Laporan lain dengan teks sama — via text_hash ternormalisasi
    (tahan variasi huruf besar/spasi); baris lama tanpa hash memakai
    pencocokan teks persis."""
    if row.get("text_hash"):
        return turso_execute(
            cfg, "SELECT COUNT(*) AS n FROM reports "
                 "WHERE text_hash = ? AND id <> ?",
            [row["text_hash"], int(row["id"])])[0]["n"]
    return turso_execute(
        cfg, "SELECT COUNT(*) AS n FROM reports "
             "WHERE text_scrubbed = ? AND id <> ?",
        [row["text_scrubbed"], int(row["id"])])[0]["n"]


def verify_report(cfg: dict, report_id: int, label: str, category: str,
                  gallery_visible: bool) -> None:
    turso_execute(
        cfg,
        "UPDATE reports SET status = 'verified', label = ?, "
        "category_modus = ?, gallery_visible = ?, "
        "verified_at = datetime('now') WHERE id = ? AND status = 'pending'",
        [label, category, 1 if gallery_visible else 0, int(report_id)])
    _log_label(cfg, report_id, "verifikasi", label)


def reject_report(cfg: dict, report_id: int) -> None:
    turso_execute(
        cfg,
        "UPDATE reports SET status = 'rejected', "
        "verified_at = datetime('now') WHERE id = ? AND status = 'pending'",
        [int(report_id)])
    _log_label(cfg, report_id, "tolak")


def delete_report(cfg: dict, report_id: int) -> None:
    """Hapus lunak (hak hapus): baris keluar dari galeri & korpus."""
    turso_execute(
        cfg,
        "UPDATE reports SET status = 'deleted', gallery_visible = 0 "
        "WHERE id = ?",
        [int(report_id)])
    _log_label(cfg, report_id, "hapus")


def unverify_report(cfg: dict, report_id: int) -> None:
    turso_execute(
        cfg,
        "UPDATE reports SET status = 'pending', label = NULL, "
        "verified_at = NULL, gallery_visible = 0 "
        "WHERE id = ? AND status = 'verified'",
        [int(report_id)])
    _log_label(cfg, report_id, "kembalikan")


def set_gallery_visible(cfg: dict, report_id: int, visible: bool) -> None:
    turso_execute(
        cfg,
        "UPDATE reports SET gallery_visible = ? "
        "WHERE id = ? AND status = 'verified'",
        [1 if visible else 0, int(report_id)])


def analytics_snapshot(cfg: dict) -> dict:
    """Agregat analitik layanan dari tabel reports + corpus_export.

    Semua angka berasal dari data laporan sendiri (akurat, bukan
    perkiraan). Jumlah *views* halaman TIDAK bisa dihitung dari dalam
    app — itu ranah statistik Streamlit Cloud milik pemilik app, atau
    penghitung sesi terpisah (tidak dipasang: menghitung bot & kunjungan
    sendiri, jadi menyesatkan bila dibaca sebagai penonton).
    """
    snap = {}
    snap["total"] = turso_execute(
        cfg, "SELECT COUNT(*) AS n FROM reports")[0]["n"]
    snap["last7"] = turso_execute(
        cfg, "SELECT COUNT(*) AS n FROM reports "
             "WHERE created_at >= datetime('now', '-7 days')")[0]["n"]
    snap["status"] = {r["status"]: r["n"] for r in turso_execute(
        cfg, "SELECT status, COUNT(*) AS n FROM reports GROUP BY status")}
    snap["band"] = {r["model_band"]: r["n"] for r in turso_execute(
        cfg, "SELECT model_band, COUNT(*) AS n FROM reports "
             "GROUP BY model_band")}
    snap["channel"] = {r["channel"]: r["n"] for r in turso_execute(
        cfg, "SELECT channel, COUNT(*) AS n FROM reports "
             "GROUP BY channel")}
    row = turso_execute(
        cfg, "SELECT AVG(consent_data_use) AS r FROM reports")[0]
    snap["consent_rate"] = (row["r"] or 0.0) * 100.0
    row = turso_execute(
        cfg, "SELECT AVG((julianday(verified_at) - "
             "julianday(created_at)) * 24.0) AS h FROM reports "
             "WHERE verified_at IS NOT NULL")[0]
    snap["avg_verify_hours"] = row["h"]
    snap["corpus_by_label"] = {r["label"]: r["n"] for r in turso_execute(
        cfg, "SELECT label, COUNT(*) AS n FROM corpus_export "
             "GROUP BY label")}
    snap["top_categories"] = turso_execute(
        cfg, "SELECT category_modus AS k, COUNT(*) AS n FROM reports "
             "WHERE status = 'verified' AND category_modus IS NOT NULL "
             "GROUP BY category_modus ORDER BY n DESC LIMIT 8")
    daily = {r["d"]: r["n"] for r in turso_execute(
        cfg, "SELECT date(created_at) AS d, COUNT(*) AS n FROM reports "
             "WHERE created_at >= datetime('now', '-14 days') "
             "GROUP BY date(created_at)")}
    today = datetime.now(timezone.utc).date()
    snap["daily14"] = [
        ((today - timedelta(days=i)).isoformat(),
         daily.get((today - timedelta(days=i)).isoformat(), 0))
        for i in range(13, -1, -1)]
    snap["gold"] = gold_count(cfg)
    snap["unique_senders"] = turso_execute(
        cfg, "SELECT COUNT(DISTINCT sender_hash) AS n FROM reports "
             "WHERE sender_hash IS NOT NULL")[0]["n"]
    snap["repeat_senders"] = turso_execute(
        cfg, "SELECT COUNT(*) AS n FROM (SELECT sender_hash FROM reports "
             "WHERE sender_hash IS NOT NULL GROUP BY sender_hash "
             "HAVING COUNT(*) > 1)")[0]["n"]
    return snap


def _render_analytics(cfg: dict) -> None:
    """Panel 📊 Analitik di tab Verifikasi (data laporan, bukan views)."""
    st.markdown("#### 📊 Analitik layanan")
    try:
        s = analytics_snapshot(cfg)
    except Exception as exc:
        st.caption(f"Analitik belum bisa dimuat: {exc}")
        return
    if not s["total"]:
        st.caption("Belum ada data — analitik terisi begitu laporan "
                   "warga mulai masuk.")
        return
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Total laporan masuk", s["total"])
    a2.metric("Masuk 7 hari terakhir", s["last7"])
    a3.metric("Pengirim unik", s["unique_senders"],
              help="Jumlah sender_hash berbeda. Pengirim berulang "
                   f"(>1 laporan): {s['repeat_senders']}.")
    a4.metric("Tingkat consent data", f"{s['consent_rate']:.0f}%",
              help="Persen pelapor yang menyetujui laporannya dipakai "
                   "untuk galeri anonim + data latih.")
    if s["avg_verify_hours"] is not None:
        st.caption(f"Rata-rata waktu verifikasi: "
                   f"{s['avg_verify_hours']:.1f} jam sejak submit.")
    st.caption("Corong status: " + " · ".join(
        f"{k} {v}" for k, v in sorted(s["status"].items())))
    corpus_total = sum(s["corpus_by_label"].values())
    st.progress(min(corpus_total / 1000.0, 1.0),
                text=f"Korpus berlabel+consent: {corpus_total} / target "
                     f"±1.000 untuk retrain Tahap 3 ("
                     + ", ".join(f"{k} {v}" for k, v in
                                 sorted(s["corpus_by_label"].items()))
                     + ")")
    st.caption(f"🥇 Subset emas: **{s.get('gold', 0)}** laporan — "
               "terverifikasi DAN lolos tinjauan kedua dengan label "
               "yang sama (bahan korpus paling tepercaya).")
    c1, c2 = st.columns(2)
    with c1:
        st.caption("Laporan per hari (14 hari terakhir)")
        st.bar_chart({"Tanggal": [d for d, _ in s["daily14"]],
                      "Laporan": [n for _, n in s["daily14"]]},
                     x="Tanggal", y="Laporan")
        st.caption("Distribusi band model: " + " · ".join(
            f"{k} {v}" for k, v in sorted(s["band"].items())))
    with c2:
        st.caption("Kanal: " + " · ".join(
            f"{CHANNELS.get(k, k)} {v}"
            for k, v in sorted(s["channel"].items())))
        if s["top_categories"]:
            st.caption("Kategori modus terverifikasi terbanyak:")
            st.bar_chart(
                {"Kategori": [r["k"] for r in s["top_categories"]],
                 "Jumlah": [r["n"] for r in s["top_categories"]]},
                x="Kategori", y="Jumlah")
    st.caption(
        "Catatan: jumlah *views* halaman tidak tampil di sini — app "
        "tidak bisa menghitung penontonnya sendiri secara akurat. "
        "Statistik penonton ada di dashboard Streamlit Cloud pemilik "
        "app; panel ini khusus data laporan yang terverifikasi.")


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
    dup = duplicate_text_count(cfg, r)
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
    # Kill switch intake (Fase 2.5) — juga bisa dibalik langsung di
    # basis data oleh pengelola sebagai jalur darurat.
    intake_now = intake_open(cfg)
    ic1, ic2 = st.columns([3, 1])
    ic1.caption(
        "Penerimaan laporan (intake): **TERBUKA**" if intake_now
        else "Penerimaan laporan (intake): **DITUTUP** — warga hanya "
             "bisa cek, laporan tidak tersimpan.")
    if intake_now:
        if ic2.button("🔴 Tutup intake", key="btn_intake_close"):
            set_intake_open(cfg, False)
            st.rerun()
    else:
        if ic2.button("🟢 Buka intake", key="btn_intake_open"):
            set_intake_open(cfg, True)
            st.rerun()
    # Kontrol Turnstile (dorman): status + saklar flag. Widget hanya
    # benar-benar tampil bila kunci juga terpasang di secrets.
    ts_keys = turnstile_keys_present(cfg)
    ts_on = _config_value(cfg, "turnstile_on") == "1"
    tc1, tc2 = st.columns([3, 1])
    if ts_keys and ts_on:
        tc1.caption("Anti-bot Turnstile: **AKTIF** di formulir warga.")
        if tc2.button("🛡️ Matikan Turnstile", key="btn_ts_off"):
            set_turnstile_on(cfg, False)
            st.rerun()
    elif ts_keys:
        tc1.caption("Anti-bot Turnstile: kunci terpasang, **siaga** "
                    "(belum aktif).")
        if tc2.button("🛡️ Aktifkan Turnstile", key="btn_ts_on"):
            set_turnstile_on(cfg, True)
            st.rerun()
    else:
        tc1.caption("Anti-bot Turnstile: **dorman** — kunci belum "
                    "terpasang di secrets; formulir warga berjalan "
                    "tanpa CAPTCHA.")
    _render_analytics(cfg)

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
            enr = enrichment_summary(r.get("enrichment"))
            if enr:
                st.caption(
                    f"🌐 Pengayaan intake (info pendukung, **bukan** "
                    f"penentu label): {enr}")
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

    # Tinjauan kedua (v6.0) — pertahanan mutu korpus. Sampel ACAK
    # laporan terverifikasi dinilai ulang TANPA melihat label tercatat
    # (buta): yang hasilnya sama masuk SUBSET EMAS; yang berbeda hanya
    # DICATAT di label_log — label asli tidak berubah oleh tinjauan
    # kedua, mengubahnya keputusan peninjau utama.
    st.markdown("#### 🥇 Subset emas — tinjauan kedua")
    st.caption(
        f"Subset emas saat ini: **{gold_count(cfg)}** laporan. "
        "Nilai ulang sampel acak di bawah ini dari teksnya saja — "
        "label tercatat sengaja tidak ditampilkan. Setiap tinjauan "
        "tercatat di jejak audit (label_log).")
    sample = fetch_second_review_sample(cfg, 3)
    if not sample:
        st.caption("Tidak ada sampel menunggu tinjauan kedua "
                   "(semua terverifikasi sudah ditinjau, atau belum "
                   "ada yang terverifikasi).")
    for r in sample:
        with st.container(border=True):
            st.markdown(
                f"**Laporan #{r['id']}** · submit "
                f"{fmt_wita(r['created_at'])} · kanal "
                f"{CHANNELS.get(r['channel'], r['channel'])}")
            st.markdown(f"> {r['text_scrubbed']}")
            sc1, sc2 = st.columns([2, 1])
            lab2 = sc1.selectbox(
                "Label menurut penilaianmu (tinjauan kedua)", LABELS,
                key=f"adm_second_{r['id']}")
            if sc2.button("✔️ Catat tinjauan kedua",
                          key=f"adm_second_btn_{r['id']}"):
                hasil = second_review(cfg, r["id"], lab2)
                if hasil == "cocok":
                    st.success(
                        f"Laporan #{r['id']}: tinjauan kedua COCOK "
                        "dengan label tercatat — masuk subset emas.")
                elif hasil == "beda":
                    st.warning(
                        f"Laporan #{r['id']}: tinjauan kedua BERBEDA "
                        "dari label tercatat. Perbedaan dicatat di "
                        "label_log; label asli tidak berubah.")
                else:
                    st.info(f"Laporan #{r['id']} sudah tidak "
                            "terverifikasi — tinjauan dibatalkan.")
                st.rerun()
