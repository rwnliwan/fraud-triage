"""Scrubber PII untuk Siskamling Digital (Fase 0).

Satu-satunya gerbang sebelum teks pesan warga disimpan (kolom
``reports.text_scrubbed``) atau ditampilkan (galeri modus publik).
Fungsi publik:

    scrub(text) -> (clean_text, findings)
    hash_sender(raw_number, salt) -> sha256 hex / None

Yang dianonimkan oleh scrub():
    * nomor telepon Indonesia (+62 / 08xx, spasi/strip)  -> [NOMOR]
    * URL / tautan  -> [tautan: domain]   (domain DIPERTAHANKAN karena ia
      sinyal modus — mis. bit.ly, dana-undian2026.cc; path & query dibuang
      karena bisa memuat token/identitas)
    * email         -> [EMAIL]
    * nomor rekening / kartu (deret 10-16 digit) -> [REKENING]
    * NIK (16 digit) -> [NIK]

Keputusan yang disengaja (jangan "diperbaiki" tanpa membaca ini):

    * Kode OTP TIDAK dihapus. OTP adalah SINYAL KONTEN, bukan identitas:
      pola "minta kode OTP" adalah ciri smishing terkuat, dan OTP dari
      bank asli adalah ciri pesan sah. Menghapusnya akan merusak nilai
      triase dan nilai korpus. OTP juga pendek (4-8 digit) sehingga tidak
      tertangkap pola rekening (min. 10 digit).
    * Jumlah uang (Rp50.000.000) tidak disentuh: pemisah ribuan titik
      tidak dianggap pemisah deret digit.
    * Nama orang TIDAK di-scrub di sini — regex tidak bisa membedakan
      nama dari kata biasa secara andal. Mitigasinya proses, sesuai
      Rencana Konsep bagian 8: tinjau manual sebelum galeri tayang.
    * Deret digit yang ambigu diputuskan dengan urutan prioritas:
      pola telepon (awalan 62/0 + 8) menang atas rekening; 16 digit
      berkelompok 4-4-4-4 atau lolos uji Luhn dianggap kartu/rekening,
      16 digit rapat lainnya dianggap NIK.
    * Deret digit lebih panjang dari 16 digit tidak disentuh (di luar
      pola umum rekening/NIK Indonesia) — tertangkap tinjau manual.

findings adalah daftar jenis PII yang ditemukan, tanpa duplikat,
urut tahap pemrosesan (email, lalu tautan, lalu deret digit dari kiri
ke kanan): 'nomor_telepon', 'tautan', 'email', 'nomor_rekening',
'nik'. Dipakai untuk audit dan uji (lihat test_scrubber.py).

Modul ini murni pustaka standar Python — tanpa dependensi.
"""

from __future__ import annotations

import hashlib
import re

__all__ = ["scrub", "hash_sender", "FINDING_TELEPON", "FINDING_TAUTAN",
           "FINDING_EMAIL", "FINDING_REKENING", "FINDING_NIK"]

FINDING_TELEPON = "nomor_telepon"
FINDING_TAUTAN = "tautan"
FINDING_EMAIL = "email"
FINDING_REKENING = "nomor_rekening"
FINDING_NIK = "nik"

# ---------------------------------------------------------------- email
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# ------------------------------------------------------------------ url
# Label domain wajib mengandung huruf (dicek ulang di callback) agar
# angka berformat "50.000.000" tidak pernah terbaca sebagai domain.
_TLDS = (
    "com|net|org|info|xyz|top|click|link|online|site|cc|me|io|id|app|"
    "pro|vip|live|store|shop|today|best|win|icu|sbs|cfd|bond|quest|uno|"
    "finance|secure|loan|"
    "ly|gy|gl|gd"  # TLD pemendek tautan: bit.ly, rb.gy, goo.gl, is.gd
)
_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?"
    r"(?:[a-z0-9](?:[a-z0-9\-]*[a-z0-9])?\.)+"
    r"(?:" + _TLDS + r")"
    r"(?:/[^\s]*)?",
    re.IGNORECASE,
)
_URL_TRAILING_PUNCT = ".,!?;:'\")»>]}…"

# ----------------------------------------------------------- deret digit
# Calon deret 10-16 digit; pemisah yang diakui hanya spasi dan strip
# (titik adalah pemisah ribuan uang, bukan pemisah nomor). Lookaround
# mencegah pemotongan di tengah deret yang lebih panjang.
_DIGIT_RUN_RE = re.compile(
    r"(?<!\d)(?<![ \-]\d)"
    r"\+?\d(?:[ \-]*\d){9,15}"
    r"(?![ \-]?\d)"
)


def _luhn_ok(digits: str) -> bool:
    """Uji Luhn — pembeda kartu (16 digit) dari NIK."""
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _grouped_4x4(raw: str) -> bool:
    """True bila deret tertulis berkelompok 4-4-4-4 (kebiasaan kartu)."""
    parts = re.split(r"[ \-]+", raw.strip())
    return len(parts) == 4 and all(len(p) == 4 and p.isdigit() for p in parts)


def _classify_digit_run(raw: str) -> str | None:
    """Kembalikan jenis temuan untuk satu deret digit, atau None."""
    digits = re.sub(r"\D", "", raw)
    n = len(digits)
    if n < 10 or n > 16:
        return None
    # Telepon Indonesia: +62/62/0 diikuti 8 (seluler).
    if digits.startswith("62") and n >= 11 and digits[2] == "8":
        return FINDING_TELEPON
    if digits.startswith("0") and digits[1] == "8":
        return FINDING_TELEPON
    if n == 16:
        # Kartu lazim ditulis berkelompok / lolos Luhn; sisanya NIK.
        if _grouped_4x4(raw) or _luhn_ok(digits):
            return FINDING_REKENING
        return FINDING_NIK
    return FINDING_REKENING


_REPLACEMENT = {
    FINDING_TELEPON: "[NOMOR]",
    FINDING_EMAIL: "[EMAIL]",
    FINDING_REKENING: "[REKENING]",
    FINDING_NIK: "[NIK]",
}


def scrub(text: str) -> tuple[str, list[str]]:
    """Anonimkan PII dari teks pesan. Kembalikan (teks_bersih, findings)."""
    findings: list[str] = []

    def note(kind: str) -> None:
        if kind not in findings:
            findings.append(kind)

    if not text:
        return text, findings

    # 1) Email — lebih dulu, agar domain email tidak terbaca sebagai URL.
    def _email_sub(_m: re.Match) -> str:
        note(FINDING_EMAIL)
        return _REPLACEMENT[FINDING_EMAIL]

    out = _EMAIL_RE.sub(_email_sub, text)

    # 2) URL — pertahankan domain sebagai sinyal modus, buang path/query.
    def _url_sub(m: re.Match) -> str:
        raw = m.group(0)
        core = raw.rstrip(_URL_TRAILING_PUNCT)
        suffix = raw[len(core):]
        host = re.sub(r"^(?:https?://)?(?:www\.)?", "", core,
                      flags=re.IGNORECASE).split("/")[0].lower()
        if not any(ch.isalpha() for ch in host):
            return raw  # bukan domain sungguhan; jangan sentuh
        note(FINDING_TAUTAN)
        return f"[tautan: {host}]" + suffix

    out = _URL_RE.sub(_url_sub, out)

    # 3) Deret digit — klasifikasi telepon / NIK / rekening.
    def _digit_sub(m: re.Match) -> str:
        kind = _classify_digit_run(m.group(0))
        if kind is None:
            return m.group(0)
        note(kind)
        return _REPLACEMENT[kind]

    out = _DIGIT_RUN_RE.sub(_digit_sub, out)

    return out, findings


def hash_sender(raw: str | None, salt: str | None) -> str | None:
    """Hash nomor pengirim untuk disimpan di reports.sender_hash.

    Nomor TIDAK PERNAH disimpan mentah. Nomor dinormalisasi dulu
    (buang selain digit; 0xxx -> 62xxx; 8xxx -> 62xxx) agar format
    penulisan berbeda atas nomor yang sama menghasilkan hash yang sama.

    ``salt`` WAJIB berasal dari env (mis. SISKAMLING_SENDER_SALT) dan
    tidak pernah di-hardcode / ditulis ke repo. Salt kosong ditolak:
    hash tanpa garam atas ruang nomor Indonesia mudah ditebak balik
    dengan daftar nomor (rainbow table).
    """
    if raw is None or not str(raw).strip():
        return None
    if not salt:
        raise ValueError(
            "salt kosong: hash_sender menolak berjalan tanpa garam dari env")
    digits = re.sub(r"\D", "", str(raw))
    if not digits:
        return None
    if digits.startswith("0"):
        digits = "62" + digits[1:]
    elif digits.startswith("8"):
        digits = "62" + digits
    return hashlib.sha256(f"{salt}:{digits}".encode("utf-8")).hexdigest()
