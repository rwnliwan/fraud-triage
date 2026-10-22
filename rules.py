# -*- coding: utf-8 -*-
"""Lapisan aturan (rules layer) + deteksi sinyal teks untuk Fraud Triage.

Modul ini MELENGKAPI model ensemble di triage_core.py — ia TIDAK mengubah
skor model dan TIDAK mengubah ambang. Fungsinya dua:

1. ATURAN KEAMANAN (hard rules): pola smishing yang sangat khas dan hampir
   tidak pernah dilakukan pengirim sah dipaksa naik ke ESKALASI, berapa pun
   skor modelnya. Rancangan (disetujui Septian 2026-10-22):
   - Aturan memakai KOMBINASI sinyal kuat, BUKAN kata tunggal — kata seperti
     "OTP" atau "blokir" juga muncul di pesan bank yang sah.
   - Pemicu: minimal 2 dari 3 sinyal kuat (S1/S2/S3) hadir bersamaan.
   - Aturan hanya boleh MENAIKKAN band keputusan, tidak pernah menurunkan.
     Pesan yang oleh model sudah ESKALASI tetap ESKALASI; aturan tidak
     pernah menutup pesan yang model anggap berisiko.
   - Transparan: pemicu selalu dilaporkan beserta sinyal-sinyalnya agar
     bisa diaudit manusia (app menampilkannya sebagai lencana).

2. DETEKSI SINYAL (panel sinyal): daftar indikator yang terbaca dari teks
   (tautan, urgensi, permintaan kredensial, janji hadiah, dst.) supaya
   pengguna paham MENGAPA sebuah pesan terlihat berisiko — independen dari
   apakah aturan keamanan terpicu.

Tiga sinyal kuat aturan:
  S1 — Ada tautan (URL). Terutama kuat bila pemendek tautan (bit.ly, s.id,
       tinyurl, ...) atau domain berekstensi mencurigakan (.xyz, .top, .cc,
       .click, ...) — tetapi tautan apa pun dihitung sebagai S1; sendirian
       ia TIDAK cukup memicu (butuh pasangan sinyal).
  S2 — Permintaan bertindak lewat tautan / memasukkan kredensial: pola
       imperatif seperti "masukkan PIN", "verifikasi di <tautan>",
       "klik tautan ini", "verify your PIN at ...". Kalimat PELINDUNG khas
       pesan sah ("JANGAN bagikan kode ini kepada siapa pun") secara
       eksplisit BUKAN sinyal — kata kerja meminta-masukkan tidak mencakup
       "berikan/bagikan", dan kecocokan yang didahului kata "jangan" dalam
       jendela dekat dibuang (lihat _matches_s2).
  S3 — Ancaman + urgensi waktu: kata ancaman (diblokir, hangus, suspend,
       dibekukan, ...) DAN kata tekanan waktu (hari ini, segera, dalam
       24 jam, ...) harus hadir bersamaan; salah satu saja bukan S3.

Modul ini murni regex — tanpa dependensi selain pustaka standar — agar
bisa diuji berdiri sendiri seperti triage_core.
"""

import re

# ----------------------------------------------------------------------------
# Pola-pola dasar
# ----------------------------------------------------------------------------
# Domain pemendek tautan yang umum dipakai smishing (dan sebagian pemakai sah
# — karena itu ia detail S1, bukan pemicu tunggal).
SHORTENER_DOMAINS = {
    "bit.ly", "s.id", "tinyurl.com", "rb.gy", "cutt.ly", "is.gd", "t.co",
    "goo.gl", "ow.ly", "buff.ly", "shorturl.at", "rebrand.ly", "bl.ink",
    "short.io", "linktr.ee", "tribelio.page",
}

# Ekstensi domain yang murah/anonim dan lazim dipakai situs smishing.
SUSPICIOUS_TLDS = {
    "xyz", "top", "cc", "click", "link", "buzz", "club", "vip", "icu",
    "rest", "best", "live", "site", "online", "fun", "one", "space",
    "website", "work", "today", "gq", "tk", "ml", "ga", "cf",
}

# Tautan: skema http(s), awalan www., atau domain polos dengan TLD dikenal.
_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?"
    r"(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+"
    r"(?:com|net|org|info|biz|io|co|id|me|ly|app|dev|tv|"
    r"xyz|top|cc|click|link|site|online|live|buzz|club|vip|icu|rest|best|"
    r"one|space|website|work|today|shop|store|secure|gq|tk|ml|ga|cf)"
    r"(?:/[^\s]*)?",
    re.IGNORECASE,
)

# S2a — imperatif memasukkan kredensial (ID + EN).
_S2A_RE = re.compile(
    r"\b(?:masukkan|memasukkan|inputkan|input|ketik|ketikkan|enter|submit|"
    r"type)\b[^.]{0,30}?\b(?:otp|pin|password|kata sandi|sandi|kode|"
    r"credential|kredensial)\b",
    re.IGNORECASE,
)
# S2b — imperatif verifikasi/kredensial ala Inggris.
_S2B_RE = re.compile(
    r"\b(?:verify|confirm|validate|update)\b[^.]{0,30}?\b(?:pin|password|"
    r"otp|code|account|identity|credential|credentials|details)\b",
    re.IGNORECASE,
)
# S2c — imperatif bertindak LEWAT tautan: kata kerja + penanda arah +
# tautan/link. Penanda arah ("di", "melalui", ...) harus diikuti token yang
# tampak seperti domain (mengandung titik) atau kata link/tautan itu sendiri.
_DOMAIN_TOKEN = r"(?:https?://|www\.|[a-z0-9-]+\.[a-z]{2,})"
_S2C_RE = re.compile(
    r"\b(?:verifikasi|konfirmasi|validasi|login|masuk|klaim|bayar|cek|"
    r"lanjutkan|akses|buka|verify|claim|pay|login|check)\b[^.]{0,45}?"
    r"\b(?:di|melalui|lewat|via|pada|at)\b\s*(?:tautan|link|sini|disini)?\s*"
    + _DOMAIN_TOKEN,
    re.IGNORECASE,
)
# S2d — "klik/tekan tautan/link ini" dan sejenisnya.
_S2D_RE = re.compile(
    r"\b(?:klik|tekan|tap|click|press)\b[^.]{0,20}?\b(?:tautan|link|disini|"
    r"di sini|berikut|ini|here)\b",
    re.IGNORECASE,
)
_S2_PATTERNS = [_S2A_RE, _S2B_RE, _S2C_RE, _S2D_RE]

# S3 — ancaman & urgensi (keduanya wajib hadir).
_THREAT_RE = re.compile(
    r"\b(?:diblokir|blokir|terblokir|pemblokiran|suspend|ditangguhkan|"
    r"hangus|dibekukan|beku|ditutup|dinonaktifkan|nonaktif|dihapus|"
    r"blocked|suspended|terminated|deactivated|expired|kadaluwarsa|"
    r"kedaluwarsa|dicabut)\b",
    re.IGNORECASE,
)
_URGENCY_RE = re.compile(
    r"\b(?:hari ini|malam ini|sekarang juga|sekarang|segera|secepatnya|"
    r"darurat|urgent|important|penting|dalam\s+\d+\s*(?:jam|menit)|"
    r"24\s*jam|1x24|today|now|immediately|sebelum\s+(?:pukul|jam|tanggal)|"
    r"batas\s*(?:waktu|akhir))\b",
    re.IGNORECASE,
)

# Pola panel sinyal (informatif, bukan pemicu aturan).
_PRIZE_RE = re.compile(
    r"\b(?:memenangkan|pemenang|undian|hadiah|menang|saldo\s*gratis|"
    r"bonus|promo|cashback|gratis|winner|won|prize|giveaway|klaim\s*hadiah)\b",
    re.IGNORECASE,
)
_MONEY_RE = re.compile(
    r"(?:rp\s?\d|\d[\d.]*\s*(?:juta|ribu|miliar|rb|jt)\b|\$\s?\d|£\s?\d|"
    r"usd\s?\d)",
    re.IGNORECASE,
)
_PHONE_RE = re.compile(
    r"(?:\+?\d[\d\s-]{8,}\d|08\d{8,12})",
)
_OTP_MENTION_RE = re.compile(
    r"\b(?:otp|kode\s*(?:verifikasi|rahasia|keamanan|akses|otp)|"
    r"one[- ]?time\s*(?:password|code)|verification\s*code)\b",
    re.IGNORECASE,
)


def _extract_domains(text):
    """Semua domain dari tautan yang terdeteksi (tanpa skema/jalur)."""
    domains = []
    for m in _URL_RE.finditer(text):
        raw = m.group(0)
        host = re.sub(r"^https?://", "", raw, flags=re.IGNORECASE)
        host = host.split("/")[0].lower()
        if host.startswith("www."):
            host = host[4:]
        # Alamat email juga cocok dengan pola domain; itu wajar — domainnya
        # tetap ditampilkan apa adanya di panel sinyal.
        if host not in domains:
            domains.append(host)
    return domains


def _domain_tld(domain):
    return domain.rsplit(".", 1)[-1] if "." in domain else ""


def _matches_s2(text):
    """True bila ada permintaan memasukkan kredensial / bertindak via tautan.

    Penjaga kalimat pelindung: kecocokan pola yang dalam 30 karakter
    sebelumnya didahului kata "jangan" dibuang — pesan sah menulis
    "JANGAN bagikan/masukkan kode ini kepada siapa pun", dan kalimat
    semacam itu adalah tanda pesan AMAN, bukan permintaan kredensial.
    """
    for pat in _S2_PATTERNS:
        for m in pat.finditer(text):
            window = text[max(0, m.start() - 30):m.start()].lower()
            if "jangan" in window:
                continue
            return True
    return False


def detect_signals(text):
    """Deteksi sinyal terbaca dari teks — untuk panel sinyal & aturan.

    Mengembalikan dict:
      domains        : list domain yang ditemukan di tautan
      strong         : {"S1": bool, "S2": bool, "S3": bool}
      items          : list dict {key, label, detected, detail} untuk panel
    """
    text = text or ""
    domains = _extract_domains(text)
    shorteners = [d for d in domains if d in SHORTENER_DOMAINS]
    suspicious = [d for d in domains
                  if _domain_tld(d) in SUSPICIOUS_TLDS]

    s1 = len(domains) > 0
    s2 = _matches_s2(text)
    threat = bool(_THREAT_RE.search(text))
    urgency = bool(_URGENCY_RE.search(text))
    s3 = threat and urgency

    prize = bool(_PRIZE_RE.search(text))
    money = bool(_MONEY_RE.search(text))
    phone = bool(_PHONE_RE.search(text))
    otp_mentioned = bool(_OTP_MENTION_RE.search(text))
    caps_ratio = (sum(ch.isupper() for ch in text) / max(len(text), 1))
    loud = caps_ratio > 0.25 or text.count("!") >= 2

    items = [
        {"key": "url", "label": "Tautan (URL) terdeteksi",
         "detected": s1,
         "detail": ", ".join(domains) if domains else ""},
        {"key": "shortener", "label": "Pemendek tautan (bit.ly, s.id, dll.)",
         "detected": bool(shorteners),
         "detail": ", ".join(shorteners)},
        {"key": "suspicious_tld",
         "label": "Domain berekstensi mencurigakan (.xyz/.top/.cc/dll.)",
         "detected": bool(suspicious),
         "detail": ", ".join(suspicious)},
        {"key": "s2",
         "label": "Permintaan memasukkan OTP / PIN / kredensial atau "
                  "bertindak lewat tautan (sinyal kuat S2)",
         "detected": s2, "detail": ""},
        {"key": "threat",
         "label": "Ancaman blokir / suspensi / hangus (bagian S3)",
         "detected": threat, "detail": ""},
        {"key": "urgency",
         "label": "Tekanan urgensi / batas waktu (bagian S3)",
         "detected": urgency, "detail": ""},
        {"key": "prize", "label": "Janji hadiah / undian / uang",
         "detected": prize, "detail": ""},
        {"key": "otp", "label": "Kode OTP / verifikasi disebut dalam teks",
         "detected": otp_mentioned, "detail": ""},
        {"key": "money", "label": "Nominal uang disebut",
         "detected": money, "detail": ""},
        {"key": "phone", "label": "Nomor telepon disebut dalam teks",
         "detected": phone, "detail": ""},
        {"key": "loud",
         "label": "Gaya menekan: banyak huruf kapital / tanda seru",
         "detected": loud,
         "detail": f"rasio kapital {caps_ratio:.0%}, "
                   f"tanda seru {text.count('!')}" if loud else ""},
    ]
    return {
        "domains": domains,
        "strong": {"S1": s1, "S2": s2, "S3": s3},
        "threat": threat,
        "urgency": urgency,
        "items": items,
    }


_SIGNAL_NAMES = {
    "S1": "tautan (URL) dalam pesan",
    "S2": "permintaan memasukkan kredensial / bertindak lewat tautan",
    "S3": "ancaman blokir/suspensi disertai urgensi waktu",
}


def evaluate_rules(text):
    """Nilai aturan keamanan atas teks.

    Mengembalikan dict:
      triggered      : True bila >= 2 sinyal kuat hadir bersamaan
      strong         : {"S1": bool, "S2": bool, "S3": bool}
      active_signals : list kode sinyal kuat yang aktif, mis. ["S1", "S3"]
      reasons        : list nama sinyal (Bahasa Indonesia) untuk lencana
      signals        : hasil detect_signals() lengkap (untuk panel)
    """
    sig = detect_signals(text)
    active = [k for k in ("S1", "S2", "S3") if sig["strong"][k]]
    return {
        "triggered": len(active) >= 2,
        "strong": sig["strong"],
        "active_signals": active,
        "reasons": [_SIGNAL_NAMES[k] for k in active],
        "signals": sig,
    }


def apply_rules(text, model_zone):
    """Terapkan aturan di atas band model. HANYA menaikkan, tak pernah turun.

    Mengembalikan (final_zone, rule_info) dengan rule_info hasil
    evaluate_rules() ditambah:
      raised : True bila aturan benar-benar menaikkan band model
               (terpicu DAN band model belum ESKALASI).
    """
    info = evaluate_rules(text)
    info["raised"] = bool(info["triggered"] and model_zone != "ESKALASI")
    final_zone = "ESKALASI" if info["triggered"] else model_zone
    return final_zone, info
