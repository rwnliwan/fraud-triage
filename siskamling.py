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
terverifikasi — yang cocok masuk hitungan "disepakati dua peninjau"
(tampil di Analitik); yang berbeda menunggu adjudikasi peninjau utama.

Baru di v6.1.6 (perbaikan review ronde 8 Terra — fail-open intake
ditutup, adjudikasi berefek korpus, lacak berkode acak; model/skor/
ambang TIDAK berubah): (1) Scrubber: TIDAK ADA LAGI allowlist TLD —
TLD apa pun + fragment `#` + IPv4 ikut terscrub; aturan yang sama
di rules.py (S1). (2) Adjudikasi "diragukan" MENGELUARKAN baris dari
korpus (kolom corpus_excluded, migrasi 0002); emas mensyaratkan
tidak ada sengketa terbuka; tinjauan berbeda yang baru membuka lagi
antrean; putusan tercatat terverifikasi + di kolom putusan sendiri.
(3) Panel Analitik: distribusi band model hanya atas laporan
TERVERIFIKASI (pending tidak lagi bocor lewat agregat); caption
panel ditulis apa adanya. (4) Consent atomik: INSERT reports +
consent_log dalam SATU transaksi batch pipeline; view korpus kini
mensyaratkan bukti consent_log. (5) Token Turnstile diverifikasi
ulang TIAP pengiriman (tanpa cache sesi); widget di-reset tiap
submit sukses. (6) Intake gagal-ke-tertutup: kill switch/batas/hash
yang gagal dibaca TIDAK LAGI membuka simpan; gerbang simpan murni
(check_storage_gate) yang bisa diuji. (7) Batas harian memakai hari
WITA (bukan UTC). (8) Lacak laporan pakai KODE ACAK 8 karakter
(bukan nomor urut). (9) OCR membawa penanda provenance (via_ocr).
(10) Penjaga "jangan" S2 hanya menekan bila "jangan" mengikat verba
permintaan itu. (11) Migrasi SQL berversi di repo (migrations/).
Skema baru butuh migrasi 0002 di Turso live + reboot app.

Baru di v6.1.5 (perbaikan review ronde 7 Terra — independensi
pelabelan dikunci teknis, bukan prosedural; model/skor/ambang TIDAK
berubah): (1) Scrubber: query URL tanpa path ("https://host?token=x")
kini ikut dibuang — pola lama hanya menelan query sesudah "/".
(2) Kartu pending TIDAK LAGI membocorkan riwayat "pernah
terverifikasi", pengayaan intake, atau metadata pengirim/duplikasi —
ketiganya pindah ke daftar terverifikasi (pasca-label). (3) Expander
triase hanya menampilkan JUMLAH total laporan pending — tanpa ID,
urutan skor, atau band. (4) "Subset emas / paling tepercaya" diganti
klaim jujur "disepakati dua peninjau" (kesepakatan, bukan bukti label
benar) + jalur adjudikasi untuk tinjauan kedua yang berbeda.
(5) Analitik: consent dihitung atas laporan yang masih dalam alur
(pending/terverifikasi); rata-rata waktu verifikasi diukur sampai
verifikasi PERTAMA (label_log) dengan saring timestamp anomali;
grafik harian memakai tanggal WITA. (6) Aturan S2 kini menangkap
"berikan/bagikan/kasih/serahkan OTP" — penjaga "jangan" tetap
melindungi kalimat pelindung. (7) Panel evaluasi menampilkan kolom
"Catatan ambang" bila skor 4 desimal membulat tepat ke ambang.
(8) Narasi perjalanan riset: bahasa kausal "sembuh / membuat gagal"
diganti deskriptif.

Baru di v6.1.4 (perbaikan review ronde 6 Terra — independensi
pelabelan & kejujuran vonis; model/skor/ambang TIDAK berubah):
(1) Antrean pelabelan kini urut waktu masuk (created_at), BUKAN skor
model — urutan skor adalah sinyal ordinal yang membocorkan risiko
sebelum pelabelan. Antrean triase terurut skor tetap ada sebagai
expander terpisah yang tertutup + berperingatan, tanpa teks dan tanpa
tombol label. (2) Label pertama DIBEKUKAN sebagai label korpus:
unverify_report tidak lagi menghapus label (label = NULL, perilaku
lama); verifikasi ulang sesudah saran mesin terlihat hanya mencatat
revisi terpisah di label_log ('revisi_pasca_paparan') tanpa menimpa
label korpus — efektif sampai ekspor karena view corpus_export
membaca reports.label pada baris status='verified'. (3) Vonis warga
"HAMPIR PASTI PENIPUAN" diganti "SANGAT MENCURIGAKAN — kombinasi
tanda bahaya terkuat" (presisi aturan keras belum terukur) dan
"Kemungkinan besar aman" diganti "Risiko rendah menurut pemeriksa".
(4) Tinjauan kedua: pilihan label tanpa nilai awal (index=None),
ID/tanggal/kanal disembunyikan agar tak bisa dicocokkan ke daftar
terverifikasi, nama peninjau kedua dicatat di jejak audit. (5) Klaim
galeri dilunakkan: nama bebas masih bisa lolos dari scrub otomatis;
perlindungan nyata adalah tinjauan manusia. (6) Alasan saran "band
AMAN" menjadi "band RISIKO RENDAH" (nilai simpan DB tetap "AMAN").

Baru di v6.1.0 (tindak lanjut kritik eksternal atas laporan v3.2):
(1) label vonis warga tegas hanya tampil bila lapisan aturan keras
terpicu — band ESKALASI dari skor model saja memakai label yang
dilunakkan ("polanya sangat mirip penipuan") plus peringatan khusus
pesan berformat resmi untuk band menengah/atas tanpa sinyal aturan
(sejak v6.1.4 label tegasnya "SANGAT MENCURIGAKAN — kombinasi tanda
bahaya terkuat", bukan "HAMPIR PASTI PENIPUAN"); (2) expander
"Kebijakan privasi & retensi data" di tab Lapor (PRIVACY_TEXT_V1) — isinya diverifikasi dari kode:
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
import secrets
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
    "penghapusan mengeluarkannya dari galeri dan dari data latih yang "
    "dibuat sesudah penghapusan — salinan yang sudah diekspor atau "
    "sudah dipakai melatih model sebelum penghapusan tidak dapat "
    "ditarik kembali. Persetujuan ini sukarela — menolak tidak "
    "menghalangi Anda memakai fitur cek pesan.\n\n"
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
    "dari data pribadi yang terdeteksi) ditampilkan tanpa nama di "
    "galeri modus dan dipakai sebagai data latih untuk meningkatkan "
    "pendeteksi penipuan."
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
    "pribadi yang terdeteksi; pembersih otomatis bisa luput — nama "
    "bebas, kode OTP, dan deret digit panjang sengaja tidak dihapus "
    "(lihat 'Batas pembersihan otomatis' di bawah) — jadi jangan "
    "menganggap teks tersimpan pasti bebas identitas. Salinan "
    "cadangan berkala disimpan maksimal **8 minggu** untuk keamanan "
    "data.\n\n"
    "**Berapa lama disimpan (retensi):** laporan disimpan selama "
    "layanan berjalan atau sampai dihapus atas permintaan / "
    "keputusan pengelola; saat ini **belum ada penghapusan otomatis "
    "berdasarkan umur laporan**.\n\n"
    "**Hak Anda:** (1) mengetahui status laporan Anda — gunakan "
    "fitur **🔎 Lacak laporan saya** dengan kode lacak Anda; "
    "(2) meminta laporan Anda **dihapus** — sampaikan kode lacak "
    "Anda kepada pengelola layanan. Laporan yang dihapus tidak "
    "tampil di galeri dan tidak dipakai dalam data latih yang dibuat "
    "sesudah penghapusan; salinan yang sudah diekspor atau sudah "
    "dipakai melatih model sebelum penghapusan tidak dapat ditarik "
    "kembali. Jujur soal mekaniknya: penghapusan saat ini berupa "
    "**penandaan status** di basis data; penghapusan fisik permanen "
    "adalah penyempurnaan yang masih kami kerjakan.\n\n"
    "**Batas pembersihan otomatis:** pembersih bekerja dengan pola "
    "(regex) dan bisa luput pada nama atau alamat yang tertulis "
    "bebas di dalam teks. Jangan menambahkan data pribadi Anda "
    "sendiri ke kolom pesan, di luar isi pesan yang Anda terima."
)


# Peta band final app -> nilai kolom reports.model_band (CHECK di schema)
# dan label tampilnya. Nilai simpan "AMAN" dipertahankan (skema DB +
# suggest_label membacanya); yang dilunakkan hanya label tampilnya —
# skor rendah = risiko rendah menurut model, bukan jaminan aman. (R5, S2.)
BAND_STORE = {"AUTO-CLOSE": "AMAN", "REVIEW ANALIS": "REVIEW",
              "ESKALASI": "ESKALASI"}
BAND_BADGE = {"AMAN": "🟢 RISIKO RENDAH", "REVIEW": "🟡 REVIEW",
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
        stmt["args"] = [_stmt_arg(a) for a in args]
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


def _stmt_arg(a):
    """Satu nilai Python -> argumen statement pipeline Hrana."""
    if a is None:
        return {"type": "null", "value": None}
    if isinstance(a, int):
        return {"type": "integer", "value": str(a)}
    if isinstance(a, float):
        return {"type": "float", "value": a}
    return {"type": "text", "value": str(a)}


def _rows_of(result: dict) -> list:
    """Hasil execute mentah pipeline -> list[dict]."""
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


def turso_batch(cfg: dict, statements: list) -> list:
    """Jalankan beberapa statement dalam SATU transaksi pipeline.

    statements: list[(sql, args)]. Kembalikan list hasil per langkah
    (list[dict] untuk SELECT/RETURNING, [] untuk tulis). Bila SATU
    langkah gagal, SELURUH batch dibatalkan (semantik transaksi batch
    Hrana: step_errors terisi, step_results langkah itu null) — fungsi
    ini melempar RuntimeError dan pemanggil WAJIB menganggap TIDAK ADA
    langkah yang tersimpan.

    Bentuk wire + error SUDAH diverifikasi ke Turso live (baca-saja,
    2026-11-09): request {"type": "batch", "batch": {"steps": [...]}},
    respons result {"step_results": [...], "step_errors": [...]}.
    Yang BELUM bisa dibuktikan tanpa tulis live adalah rollback-nya
    atas tulis yang gagal di tengah batch — verifikasi live: submit
    pertama berkonsen pasca-deploy WAJIB dicek di DB (baris reports +
    baris consent_log sama-sama ada); kegagalan consent_log yang
    meninggalkan yatim = batch TIDAK atomik (laporkan, jangan diam).
    """
    base = cfg["url"].rstrip("/")
    if base.startswith("libsql://"):
        base = "https://" + base[len("libsql://"):]
    elif base.startswith("http://"):
        base = "https://" + base[len("http://"):]
    if not base.endswith("/v2/pipeline"):
        base += "/v2/pipeline"
    steps = [{"stmt": {"sql": sql,
                       "args": [_stmt_arg(a) for a in (args or [])]}}
             for sql, args in statements]
    body = json.dumps(
        {"requests": [{"type": "batch", "batch": {"steps": steps}}]}
    ).encode("utf-8")
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
    errors = result.get("step_errors") or []
    for i, err in enumerate(errors):
        if err:
            raise RuntimeError(
                f"turso batch step {i} gagal: "
                + json.dumps(err)[:300])
    out = []
    for step in result.get("step_results") or []:
        out.append([] if step is None else _rows_of(step))
    return out


# Deteksi skema migrasi 0002 (Ronde 8): kode v6.1.6 menurun grasi bila
# kolom baru belum ada (intake tidak boleh mati karena urutan deploy),
# TETAPI perilaku yang efeknya bergantung pada kolom itu gagal JUJUR
# (bukan diam-diam) — lihat pemakaiannya di submit_report /
# adjudicate_report. Hasil probe di-cache per URL selama proses
# berjalan; sesudah migrasi 0002 diterapkan, REBOOT app agar cache
# ini tersegarkan (alasan reboot kedua, selain modul impor).
_R8_COLS_CACHE: dict = {}


def _reports_has_r8_cols(cfg: dict) -> bool:
    """True bila migrasi 0002 sudah diterapkan (kolom track_code ada)."""
    key = cfg.get("url") or ""
    if key in _R8_COLS_CACHE:
        return _R8_COLS_CACHE[key]
    try:
        turso_execute(
            cfg,
            "SELECT track_code, via_ocr, corpus_excluded "
            "FROM reports LIMIT 0")
        ok = True
    except Exception:
        ok = False
    _R8_COLS_CACHE[key] = ok
    return ok


def _label_log_has_putusan(cfg: dict) -> bool:
    """True bila kolom label_log.putusan (migrasi 0002) sudah ada."""
    key = "putusan:" + (cfg.get("url") or "")
    if key in _R8_COLS_CACHE:
        return _R8_COLS_CACHE[key]
    try:
        turso_execute(cfg, "SELECT putusan FROM label_log LIMIT 0")
        ok = True
    except Exception:
        ok = False
    _R8_COLS_CACHE[key] = ok
    return ok


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
# Ronde 8, S5: batas per sesi — satu sesi browser (satu tab) boleh
# mengirim maks 10 laporan; sesi baru = hitungan baru, jadi ini
# HANYA hambatan kecepatan, bukan tembok. Kontrol anti-banjir yang
# sesungguhnya adalah Turnstile per-pengiriman (M5, token sekali
# pakai diverifikasi ulang tiap submit) + batas global 300/hari.
# Angka 300 vs 500 sengaja berbeda: 300 adalah batas intake harian
# (laporan BARU per hari), 500 adalah pemutus antrean (backlog boleh
# menumpuk lintas hari bila verifikasi lebih lambat dari intake) —
# antrean tidak pernah menjadi pengaman utama bila batas global
# dipatuhi, dan itu dinyatakan di sini supaya tidak "diselaraskan"
# tanpa alasan.
MAX_SUBMITS_PER_SESSION = 10


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
    """Verifikasi token Turnstile ke Cloudflare siteverify (server-side).

    `remoteip` TIDAK dikirim: app Streamlit tidak mengekspos IP klien
    ke kode ini (tidak ada REMOTE_ADDR / X-Forwarded-For yang bisa
    dibaca dari sini) — dan parameter itu opsional di API Cloudflare
    (Ronde 8, N5). Bila suatu hari IP tersedia lewat header proxy,
    kirimkan di sini.
    """
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
    # Ronde 8, M5: kunci widget memakai nonce sesi — sesudah satu
    # submit sukses, nonce naik (lihat render_lapor_tab) sehingga
    # widget me-render ulang dan mengeluarkan token BARU untuk
    # pengiriman berikutnya. Tanpa ini, widget mengembalikan token
    # lama yang sama dan siteverify kedua akan gagal ("duplicate").
    _nonce = st.session_state.get("sk_ts_nonce", 0)
    return _ts_component(sitekey=cfg.get("turnstile_site_key"),
                         default=None, key=f"sk_turnstile_{_nonce}")


def _turnstile_passed(cfg: dict, token) -> bool:
    """Verifikasi token Turnstile ke Cloudflare siteverify.

    Ronde 8, M5: token diverifikasi ulang pada setiap pengiriman —
    TIDAK ADA LAGI cache sesi (`sk_ts_token` dihapus). Token
    Turnstile sekali pakai di sisi Cloudflare: memakai token yang
    sama untuk pengiriman kedua adalah reuse kredensial sekali pakai,
    bukan "kenyamanan sesi". Kunci sesi lama yang tersisa dibersihkan
    di sini sebagai higiene.
    """
    st.session_state.pop("sk_ts_token", None)
    if not token:
        return False
    return verify_turnstile(cfg, token)


def sender_today_count(cfg: dict, sender_hash: str | None) -> int:
    # Ronde 8, S4: "hari ini" = hari WITA (UTC+8), konsisten dengan
    # semua tampilan waktu app (fmt_wita, grafik harian R7 N3).
    # date('now') lama memakai hari UTC yang berganti 07:00 WITA.
    if not sender_hash:
        return 0
    return turso_execute(
        cfg, "SELECT COUNT(*) AS n FROM reports WHERE sender_hash = ? "
             "AND date(created_at, '+8 hours') "
             ">= date('now', '+8 hours')", [sender_hash])[0]["n"]


def reports_today_count(cfg: dict) -> int:
    return turso_execute(
        cfg, "SELECT COUNT(*) AS n FROM reports "
             "WHERE date(created_at, '+8 hours') "
             ">= date('now', '+8 hours')")[0]["n"]


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
    """Berapa laporan dengan sidik teks sama sudah masuk HARI INI
    (hari WITA — Ronde 8, S4)."""
    if not th:
        return 0
    return turso_execute(
        cfg, "SELECT COUNT(*) AS n FROM reports WHERE text_hash = ? "
             "AND date(created_at, '+8 hours') "
             ">= date('now', '+8 hours')", [th])[0]["n"]


def check_storage_gate(cfg: dict, *, db_ready: bool,
                       intake_open: bool, queue_full: bool,
                       intake_unknown: bool = False,
                       sender_raw: str | None = None,
                       raw_text: str = "",
                       session_submits: int = 0) -> tuple[bool, str | None]:
    """Gerbang simpan murni (tanpa Streamlit) — Ronde 8, GG-16.

    Kembalikan (can_store, block_reason). ATURAN KERAS: kegagalan
    apa pun dalam pemeriksaan = TIDAK BOLEH SIMPAN (fail-closed).
    Ronde 8 menutup tiga fail-open berlapis yang dulu membuka intake
    tepat saat DB bermasalah: M6 (kill switch tak terbaca -> terbuka),
    M7 (cek batas gagal -> can_store=True), M8 (hash gagal -> sender
    diperlakukan anonim tanpa batas). Fungsi ini murni supaya gerbang
    bisa diuji di guard QA tanpa browser (lihat qa_r8 GG-16).

    Urutan: prasyarat -> sesi -> hash pengirim (gagal = tahan) ->
    batas per-pengirim -> batas global -> batas teks-sama (gagal =
    tahan — dulu `except: pass` membiarkan banjir duplikat lolos
    saat ceknya gagal). Pengirim anonim (tanpa nomor) memang tidak
    punya batas per-pengirim — penahannya batas global + Turnstile
    per-pengiriman (M5) + batas sesi.
    """
    if not db_ready:
        return False, "basis data belum terhubung"
    if intake_unknown:
        return False, ("status penerimaan laporan tidak dapat "
                       "dipastikan — coba lagi nanti")
    if not intake_open:
        return False, "penerimaan laporan sedang ditutup"
    if queue_full:
        return False, "antrean verifikasi sedang penuh"
    if session_submits >= MAX_SUBMITS_PER_SESSION:
        return False, (f"batas {MAX_SUBMITS_PER_SESSION} laporan per "
                       "sesi tercapai")
    s_hash = None
    if sender_raw:
        try:
            s_hash = hash_sender(sender_raw, cfg.get("salt"))
        except Exception:
            # M8: salt adalah prasyarat deployment, bukan kondisi
            # normal — sender terisi tapi hash gagal = tahan simpan +
            # beri tahu pengelola, JANGAN perlakukan sebagai anonim.
            return False, ("tidak dapat memverifikasi nomor pengirim "
                           "— coba lagi nanti")
    try:
        if s_hash and sender_today_count(
                cfg, s_hash) >= MAX_PER_SENDER_PER_DAY:
            return False, (f"batas {MAX_PER_SENDER_PER_DAY} laporan "
                           "per pengirim per hari tercapai")
        if reports_today_count(cfg) >= MAX_REPORTS_PER_DAY:
            return False, "batas laporan harian layanan tercapai"
    except Exception:
        # M7: gagal cek batas != blokir warga DULU — kini dibalik:
        # kuota yang tidak dapat diverifikasi = tahan simpan.
        return False, ("pemeriksaan batas gagal — laporan tidak "
                       "tersimpan sementara")
    if raw_text:
        try:
            clean_preview, _f = scrub(raw_text)
            if same_text_today_count(
                    cfg, text_hash_of(clean_preview)) \
                    >= MAX_SAME_TEXT_PER_DAY:
                return False, ("pesan yang sama persis sudah "
                               "dilaporkan 3 kali atau lebih hari "
                               "ini — kami anggap duplikat berlebih")
        except Exception:
            return False, ("pemeriksaan duplikat gagal — laporan "
                           "tidak tersimpan sementara")
    return True, None


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
# Ronde 8, M9: lacak memakai KODE ACAK per laporan, BUKAN nomor urut.
# Nomor urut (1, 2, 3, …) bisa ditebak siapa pun tanpa bukti
# kepemilikan — label hasil pemeriksaan orang lain bisa dienumerasi.
# Kode dibuat dari alfabet 32 karakter tanpa ambiguitas (tanpa 0/1/I/
# L/O), 8 karakter = 40 bit; tebak acak praktis tidak mungkin, dan
# kode TIDAK memberi akses ke isi laporan (hanya status + label).
TRACK_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
TRACK_CODE_LEN = 8


def new_track_code() -> str:
    """Kode lacak acak baru (secrets — bukan random modul biasa)."""
    return "".join(secrets.choice(TRACK_CODE_ALPHABET)
                   for _ in range(TRACK_CODE_LEN))


TRACK_LABEL_WARGA = {"SMISHING": "penipuan", "SAH": "bukan penipuan",
                     "SPAM_PROMO": "spam / promosi"}


def fetch_report_by_code(cfg: dict, track_code: str):
    """Status SATU laporan untuk fitur lacak warga, dicari dengan KODE
    LACAK acak. Yang diambil hanya status, label, dan tanggal — teks
    pesan, hash, dan data lain TIDAK pernah ikut, jadi tidak ada yang
    bisa bocor lewat kode lacak. Kode salah / kosong -> None."""
    code = (track_code or "").strip().upper()
    if not code:
        return None
    rows = turso_execute(
        cfg,
        "SELECT status, label, created_at, verified_at FROM reports "
        "WHERE track_code = ?", [code])
    return rows[0] if rows else None


# --- Jejak audit label + tinjauan kedua (label_log, migrasi v6.0) ------
def _log_label(cfg: dict, report_id: int, aksi: str,
               label: str | None = None,
               actor: str = "verifikator",
               putusan: str | None = None) -> None:
    """Catat satu aksi label ke label_log. Gagal catat TIDAK boleh
    menggagalkan aksi verifikasinya sendiri (jejak bersifat audit,
    bukan gerbang) — KECUALI adjudikasi, yang memakai
    _log_label_checked (Ronde 8, S1).

    putusan (Ronde 8, S1): putusan adjudikasi ('pertahankan' /
    'diragukan') ditulis di kolom `putusan` SENDIRI bila kolom itu
    ada (migrasi 0002); kolom `label` tetap membawa putusan yang sama
    demi kompatibilitas pembaca lama (semua pembaca memfilter aksi).
    Bila kolom putusan belum ada (pra-migrasi), tulis tanpa kolom itu
    — putusan tetap tercatat di `label`."""
    try:
        if putusan is not None and _label_log_has_putusan(cfg):
            turso_execute(
                cfg,
                "INSERT INTO label_log (report_id, aksi, label, actor,"
                " putusan) VALUES (?, ?, ?, ?, ?)",
                [int(report_id), aksi, label, actor, putusan])
        else:
            turso_execute(
                cfg,
                "INSERT INTO label_log (report_id, aksi, label, actor) "
                "VALUES (?, ?, ?, ?)",
                [int(report_id), aksi, label, actor])
    except Exception:
        pass


def _log_label_checked(cfg: dict, report_id: int, aksi: str,
                       label: str | None = None,
                       actor: str = "verifikator",
                       putusan: str | None = None):
    """Seperti _log_label, tetapi TERVERIFIKASI: kembalikan baris yang
    tertulis (INSERT ... RETURNING id) atau None bila gagal. Dipakai
    adjudikasi (Ronde 8, S1): sukses TIDAK BOLEH dilaporkan bila
    putusannya tidak tersimpan."""
    try:
        if putusan is not None and _label_log_has_putusan(cfg):
            rows = turso_execute(
                cfg,
                "INSERT INTO label_log (report_id, aksi, label, actor,"
                " putusan) VALUES (?, ?, ?, ?, ?) RETURNING id",
                [int(report_id), aksi, label, actor, putusan])
        else:
            rows = turso_execute(
                cfg,
                "INSERT INTO label_log (report_id, aksi, label, actor) "
                "VALUES (?, ?, ?, ?) RETURNING id",
                [int(report_id), aksi, label, actor])
        return rows[0] if rows else None
    except Exception:
        return None


def _open_dispute_sql() -> str:
    """Predikat SQL: ada tinjauan kedua yang BERBEDA dari label
    tercatat dan BELUM diputus adjudikasi SESUDAH tinjauan itu.

    Ronde 8, M2/S1: adjudikasi menutup sengketa HANYA sampai titik
    putusannya (a.id > l.id) — tinjauan berbeda yang masuk BELAKANGAN
    membuka lagi antrean. Predikat lama (NOT EXISTS adjudikasi apa
    pun) menutup antrean selamanya sejak satu putusan, apa pun yang
    terjadi sesudahnya."""
    return (
        "EXISTS (SELECT 1 FROM label_log l WHERE l.report_id = r.id "
        "AND l.aksi = 'tinjauan_kedua' AND l.label <> r.label "
        "AND NOT EXISTS (SELECT 1 FROM label_log a "
        "WHERE a.report_id = r.id AND a.aksi = 'adjudikasi' "
        "AND a.id > l.id))")


def gold_count(cfg: dict) -> int:
    """Jumlah laporan terverifikasi yang labelnya DISEPAKATI tinjauan
    kedua — ukuran KESEPAKATAN dua peninjau, BUKAN bukti label benar
    (Ronde 7, M4: label "subset emas / paling tepercaya" dulu melebihi
    yang diukur — bila kedua peninjau keliru sama, baris itu tetap
    masuk hitungan).

    Ronde 8, M2: "disepakati" mensyaratkan TIDAK ADA sengketa
    terbuka (satu tinjauan cocok + satu berbeda = BUKAN disepakati)
    dan TIDAK ADA putusan 'diragukan' — label yang diragukan bukan
    label yang disepakati, walau pernah ada tinjauan yang cocok."""
    try:
        return turso_execute(
            cfg,
            "SELECT COUNT(*) AS n FROM reports r "
            "WHERE r.status = 'verified' AND EXISTS ("
            "SELECT 1 FROM label_log l WHERE l.report_id = r.id "
            "AND l.aksi = 'tinjauan_kedua' AND l.label = r.label) "
            "AND NOT " + _open_dispute_sql() + " "
            "AND NOT EXISTS (SELECT 1 FROM label_log a "
            "WHERE a.report_id = r.id AND a.aksi = 'adjudikasi' "
            "AND a.label = 'diragukan')"
        )[0]["n"]
    except Exception:
        return 0


def disputed_count(cfg: dict) -> int:
    """Laporan terverifikasi yang tinjauan keduanya BERBEDA dari label
    tercatat dan BELUM diadjudikasi (Ronde 7, M4) — menunggu keputusan
    peninjau utama; label korpus belum berubah sampai diputuskan.
    Ronde 8, S1: sengketa yang masuk sesudah adjudikasi terakhir
    membuka lagi antrean (lihat _open_dispute_sql)."""
    try:
        return turso_execute(
            cfg,
            "SELECT COUNT(*) AS n FROM reports r "
            "WHERE r.status = 'verified' AND " + _open_dispute_sql()
        )[0]["n"]
    except Exception:
        return 0


def fetch_disputed(cfg: dict, limit: int = 10) -> list:
    """Daftar laporan yang menunggu adjudikasi (beda tinjauan kedua,
    belum ada putusan 'adjudikasi' sesudah tinjauan itu)."""
    try:
        return turso_execute(
            cfg,
            "SELECT * FROM reports r WHERE r.status = 'verified' "
            "AND " + _open_dispute_sql() + " "
            "ORDER BY verified_at ASC LIMIT ?",
            [int(limit)])
    except Exception:
        return []


def adjudicate_report(cfg: dict, report_id: int, putusan: str,
                      actor: str = "verifikator") -> bool:
    """Adjudikasi atas perbedaan tinjauan kedua (Ronde 7, M4).

    putusan 'pertahankan': label beku dipertahankan — perbedaan
    dinyatakan selesai. putusan 'diragukan': label beku diragukan —
    baris KELUAR DARI KORPUS (corpus_excluded=1, migrasi 0002) dan
    tidak lagi masuk hitungan disepakati. TIDAK mengubah reports.label
    (label pertama tetap beku); putusan tercatat di label_log sebagai
    'adjudikasi' (kolom putusan + kolom label demi kompatibilitas).
    Kembalikan False bila tidak ada perbedaan yang menunggu
    adjudikasi untuk laporan ini, bila putusan tidak tersimpan
    (Ronde 8, S1 — sukses tanpa jejak dilarang), atau bila migrasi
    0002 belum diterapkan untuk putusan 'diragukan' (Ronde 8, M2 —
    putusan tanpa efek korpus dilarang; gagal JUJUR, bukan diam-diam).
    """
    if putusan not in ("pertahankan", "diragukan"):
        return False
    rows = turso_execute(
        cfg, "SELECT label FROM reports WHERE id = ? "
             "AND status = 'verified'", [int(report_id)])
    if not rows:
        return False
    pending = turso_execute(
        cfg,
        "SELECT COUNT(*) AS n FROM reports r WHERE r.id = ? "
        "AND " + _open_dispute_sql(),
        [int(report_id)])
    if not pending or not pending[0]["n"]:
        return False
    if putusan == "diragukan":
        # Efek korpus WAJIB ikut putusan — tanpa kolomnya, putusan
        # ini tidak boleh dicatat sama sekali (GG-13).
        if not _reports_has_r8_cols(cfg):
            return False
        try:
            res = turso_batch(cfg, [
                ("UPDATE reports SET corpus_excluded = 1 WHERE id = ?",
                 [int(report_id)]),
                ("INSERT INTO label_log (report_id, aksi, label, actor,"
                 " putusan) VALUES (?, ?, ?, ?, ?) RETURNING id"
                 if _label_log_has_putusan(cfg) else
                 "INSERT INTO label_log (report_id, aksi, label, actor)"
                 " VALUES (?, ?, ?, ?) RETURNING id",
                 [int(report_id), "adjudikasi", putusan, actor, putusan]
                 if _label_log_has_putusan(cfg) else
                 [int(report_id), "adjudikasi", putusan, actor]),
            ])
        except Exception:
            return False
        return bool(res and len(res) > 1 and res[1])
    logged = _log_label_checked(cfg, report_id, "adjudikasi", putusan,
                                actor=actor, putusan=putusan)
    return logged is not None


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


def second_review(cfg: dict, report_id: int, label: str,
                  actor: str = "verifikator-2") -> str:
    """Catat tinjauan kedua atas satu laporan terverifikasi.

    Kembalikan 'cocok' (label sama -> masuk hitungan disepakati dua
    peninjau), 'beda' (dicatat sebagai perbedaan; label asli TIDAK
    diubah — mengubah label adalah keputusan peninjau utama, lewat
    adjudikasi; lihat adjudicate_report), atau 'hilang' (baris
    tidak lagi terverifikasi). `actor` dicatat di label_log supaya
    peninjau pertama dan kedua bisa dibedakan (Ronde 6, S5)."""
    rows = turso_execute(
        cfg, "SELECT label FROM reports WHERE id = ? "
             "AND status = 'verified'", [int(report_id)])
    if not rows:
        return "hilang"
    _log_label(cfg, report_id, "tinjauan_kedua", label, actor=actor)
    return "cocok" if rows[0]["label"] == label else "beda"


# ---------------------------------------------------------------------------
# Operasi basis data
# ---------------------------------------------------------------------------
def submit_report(cfg: dict, *, channel: str, raw_text: str,
                  sender_raw: str | None, consent_data_use: bool,
                  score: float, band_final: str,
                  rules_fired: list,
                  via_ocr: bool = False) -> tuple[int, str, str | None]:
    """Simpan satu laporan (status 'pending').

    Kembalikan (id, created_at, track_code). track_code None bila
    migrasi 0002 belum diterapkan (pra-migrasi: intake tetap jalan,
    resep menampilkan nomor laporan + catatan — lihat pemanggil).

    Teks yang ditulis HANYA hasil scrub; created_at diisi basis data
    (UTC) dan menjadi tanggal submit resmi pada log pencatatan.

    Ronde 8, M4: bila consent, INSERT reports + INSERT consent_log
    berjalan dalam SATU batch pipeline (turso_batch) — satu transaksi
    menurut dokumentasi Hrana: bila consent_log gagal, SELURUH simpan
    dibatalkan dan exception merambat (warga melihat "gagal tersimpan"
    dan TIDAK ADA baris yatim consent=1 tanpa bukti). Langkah kedua
    memakai last_insert_rowid() — id hasil langkah pertama pada
    koneksi yang sama — karena pipeline tidak punya variabel
    antar-langkah. CATATAN: semantik rollback-on-failure batch adalah
    asumsi dari dokumentasi Hrana (bentuk wire + error SUDAH
    diverifikasi ke Turso live read-only, tetapi rollback belum
    terbukti live) — smoke test WAJIB pada submit consent pertama
    pasca-deploy: reports + consent_log harus sama-sama tertulis.
    Sebagai pertahanan kedua, view corpus_export (migrasi 0002)
    mensyaratkan ADA baris consent_log.
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
    has_cols = _reports_has_r8_cols(cfg)
    track_code = new_track_code() if has_cols else None
    if has_cols:
        cols = ("channel, text_scrubbed, model_score, model_band, "
                "rules_fired, consent_data_use, consent_at, "
                "sender_hash, text_hash, enrichment, track_code, "
                "via_ocr")
        vals = ("?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?")
        args = [channel, clean_text, float(score),
                BAND_STORE[band_final], json.dumps(rules_fired),
                1 if consent_data_use else 0,
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                if consent_data_use else None,
                sender_hash, text_hash_of(clean_text), enrichment,
                track_code, 1 if via_ocr else 0]
    else:
        cols = ("channel, text_scrubbed, model_score, model_band, "
                "rules_fired, consent_data_use, consent_at, "
                "sender_hash, text_hash, enrichment")
        vals = ("?, ?, ?, ?, ?, ?, ?, ?, ?, ?")
        args = [channel, clean_text, float(score),
                BAND_STORE[band_final], json.dumps(rules_fired),
                1 if consent_data_use else 0,
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                if consent_data_use else None,
                sender_hash, text_hash_of(clean_text), enrichment]
    if consent_data_use:
        res = turso_batch(cfg, [(
            "INSERT INTO reports (" + cols + ") "
            "VALUES (" + vals + ") RETURNING id, created_at",
            args,
        ), (
            "INSERT INTO consent_log (report_id, consent_version, "
            "consent_text_hash) VALUES (last_insert_rowid(), ?, ?)",
            [CONSENT_VERSION, consent_text_hash()],
        )])
        row = res[0][0]
    else:
        rows = turso_execute(
            cfg,
            "INSERT INTO reports (" + cols + ") "
            "VALUES (" + vals + ") RETURNING id, created_at",
            args)
        row = rows[0]
    return row["id"], row["created_at"], track_code


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
    2.5): label tegas kini HANYA tampil bila lapisan aturan keras
    benar-benar terpicu (>= 2 sinyal kuat S1/S2/S3). Bila band
    ESKALASI datang dari skor model saja, labelnya dilunakkan — skor
    mesin bukan vonis pasti — dan untuk band menengah/atas tanpa
    sinyal aturan ditambah peringatan khusus pesan berformat resmi
    (model paling sering salah justru pada pesan resmi bank/lembaga).
    Sejak v6.1.4 label tegasnya "SANGAT MENCURIGAKAN — kombinasi
    tanda bahaya terkuat", bukan "HAMPIR PASTI PENIPUAN": jumlah
    sinyal bukan ukuran presisi — presisi aturan keras belum diukur
    pada populasi mana pun. Skor, ambang, dan band TIDAK berubah;
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
                "🔴 **SANGAT MENCURIGAKAN — kombinasi tanda bahaya "
                "terkuat.** Pesan ini memuat kombinasi tanda bahaya "
                "terkuat (lihat tanda bahaya di bawah). Jumlah sinyal "
                "bukan ukuran presisi — aturan keras ini belum diukur "
                "presisinya pada populasi mana pun — jadi verifikasi "
                "lewat kanal resmi sebelum bertindak. Jangan klik "
                "tautan apa pun di pesan ini dan jangan membalasnya.")
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
            "🟢 **Risiko rendah menurut pemeriksa.** Tidak ditemukan "
            "tanda penipuan yang kuat pada pesan ini.")
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
    """Loop tertutup (v6.0; kode lacak acak sejak v6.1.6): warga
    melacak status laporannya sendiri hanya dengan KODE LACAK yang
    diterima saat mengirim. Yang tampil status + label bahasa warga
    + tanggal — isi laporan dan data lain tidak ditampilkan.

    Ronde 8, M9: nomor laporan urut DIHAPUS sebagai kunci lacak —
    nomor urut bisa ditebak (1, 2, 3, …) dan label hasil pemeriksaan
    orang lain bisa dienumerasi. Kode lacak 8 karakter acak adalah
    bukti kepemilikan; tanpa kode yang benar, tidak ada yang tampil.
    Laporan lama (pra-migrasi 0002) mendapat kode lewat backfill —
    pengelola dapat menyampaikannya kepada pelapor bila diminta."""
    with st.expander("🔎 Lacak laporan saya"):
        st.caption(
            "Masukkan **kode lacak** yang kamu terima saat mengirim "
            "(contoh: K7M2-Q9XA). Yang tampil hanya status "
            "pemeriksaannya — isi laporanmu dan data lain tidak "
            "ditampilkan di sini.")
        if not db_ready:
            st.info("Pelacakan belum aktif pada deployment ini "
                    "(basis data belum terhubung).")
            return
        code = st.text_input(
            "Kode lacak", key="sk_track_code",
            placeholder="contoh: K7M2-Q9XA",
            help="Kode 8 karakter dari resep pengiriman laporanmu. "
                 "Kode ini acak dan hanya kamu yang tahu — jangan "
                 "dibagikan.")
        if st.button("Cek status laporan", key="btn_track"):
            if not (code or "").strip():
                st.warning("Isi dulu kode lacaknya.")
            else:
                try:
                    row = fetch_report_by_code(cfg, code)
                except Exception as exc:
                    st.error(f"Status belum bisa dimuat: {exc}")
                    row = None
                st.session_state["sk_track_row"] = row
                st.session_state["sk_track_for"] = (code or "").strip()
        row = st.session_state.get("sk_track_row")
        if row is None and st.session_state.get("sk_track_for"):
            st.warning(
                "Kode lacak tidak ditemukan. Periksa lagi kodenya — "
                "atau laporan mungkin sudah dihapus atas permintaan "
                "pelapor (hak hapus).")
        elif row is not None:
            if row["status"] == "deleted":
                st.warning(
                    "Kode lacak tidak ditemukan. Periksa lagi "
                    "kodenya — atau laporan mungkin sudah dihapus "
                    "atas permintaan pelapor (hak hapus).")
            elif row["status"] == "pending":
                st.info(
                    "⏳ **Masih menunggu pemeriksaan tim** — diterima "
                    f"{fmt_wita(row['created_at'])}. Label hanya "
                    "ditentukan manusia, jadi mohon ditunggu; cek "
                    "lagi nanti dengan kode yang sama.")
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
        "terlindungi. Setiap laporan tercatat dengan **kode lacak "
        "acak** dan **tanggal submit** sebagai bukti penerimaan.")
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

    # Hardening Fase 2.5 + Ronde 8, M6: status kill switch + pemutus
    # antrean. Gagal membaca status = intake_unknown -> gerbang
    # check_storage_gate MENUTUP simpan (fail-closed), bukan membuka
    # intake seperti dulu.
    intake_is_open = True
    queue_full = False
    ts_active = False
    intake_unknown = False
    if db_ready:
        try:
            state = fetch_lapor_state(cfg)
            intake_is_open = state["intake_open"]
            queue_full = state["pending"] >= MAX_PENDING_OPEN
            ts_active = (turnstile_keys_present(cfg)
                         and state["turnstile_on"])
        except Exception:
            intake_unknown = True
    if db_ready and intake_unknown:
        st.warning(
            "⚠️ **Status penerimaan laporan tidak dapat dipastikan** "
            "saat ini (basis data tidak menjawab) — laporan baru "
            "sementara tidak tersimpan. Fitur **cek tetap bisa "
            "dipakai**; coba lagi nanti.")
    elif db_ready and not intake_is_open:
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
            if len(st.session_state["sk_ocr_text"]) > 2000:
                st.warning(
                    "Teks hasil bacaan gambar lebih dari 2000 "
                    "karakter — yang bisa dipakai hanya 2000 karakter "
                    "pertama; sisanya terpotong. Bila pesannya panjang, "
                    "tempel teksnya manual di kolom **Isi pesan**.")
            ocr_edited = st.text_area(
                "Teks hasil bacaan gambar — periksa & betulkan dulu",
                value=st.session_state["sk_ocr_text"],
                key="sk_ocr_edit", height=110, max_chars=2000)
            if st.button("⬇️ Pakai teks ini sebagai isi pesan",
                         key="btn_ocr_use"):
                st.session_state["sk_text"] = ocr_edited
                # Ronde 8, S6: tandai asal teks (provenance OCR) —
                # disimpan sebagai via_ocr di basis data dan ditampilkan
                # di kartu peninjau supaya salah baca OCR bisa
                # dipertimbangkan sebelum memberi label.
                st.session_state["sk_text_via_ocr"] = True
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
            # Gerbang simpan (Ronde 8, GG-16): kill switch, pemutus
            # antrean, batas per pengirim & batas harian global, batas
            # teks-sama, batas sesi — SEMUA lewat check_storage_gate
            # yang fail-closed: kegagalan pemeriksaan apa pun = TIDAK
            # BOLEH SIMPAN. Hasil CEK tetap diberikan; yang ditahan
            # hanya penyimpanannya.
            sender_raw = (sender or "").strip() or None
            via_ocr = bool(st.session_state.get("sk_text_via_ocr"))
            can_store, block_reason = check_storage_gate(
                cfg, db_ready=db_ready, intake_open=intake_is_open,
                queue_full=queue_full, intake_unknown=intake_unknown,
                sender_raw=sender_raw, raw_text=raw,
                session_submits=st.session_state.get(
                    "sk_submits_count", 0))
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
                    report_id, created_at, track_code = submit_report(
                        cfg, channel=channel, raw_text=raw,
                        sender_raw=sender_raw,
                        consent_data_use=bool(consent),
                        score=analysis["res"]["p_scam"],
                        band_final=analysis["final_zone"],
                        rules_fired=rules_fired,
                        via_ocr=via_ocr)
                    st.session_state["sk_receipt"] = {
                        "id": report_id, "created_at": created_at,
                        "track_code": track_code,
                        "consent": bool(consent)}
                    st.session_state["sk_last_submit_ts"] = time.time()
                    # Ronde 8, S5: hitung pengiriman per sesi (batas
                    # 10 — lihat check_storage_gate).
                    st.session_state["sk_submits_count"] = \
                        st.session_state.get("sk_submits_count", 0) + 1
                    # Ronde 8, M5: naikkan nonce supaya widget
                    # Turnstile me-render ulang dan mengeluarkan token
                    # BARU untuk pengiriman berikutnya.
                    st.session_state["sk_ts_nonce"] = \
                        st.session_state.get("sk_ts_nonce", 0) + 1
                    st.session_state.pop("sk_text_via_ocr", None)
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
        # Ronde 8, M9: resep menampilkan KODE LACAK acak — bukan
        # nomor urut. Pra-migrasi 0002 (track_code None): tampilkan
        # nomor + catatan bahwa kode lacak belum aktif.
        if receipt.get("track_code"):
            code_line = (
                f"Kode lacak Anda: **{receipt['track_code']}** · "
                f"simpan kode ini — status pemeriksaannya bisa Anda "
                f"cek kapan saja di bagian **🔎 Lacak laporan saya** "
                f"di bawah.")
        else:
            code_line = (
                f"Nomor laporan Anda: **#{receipt['id']}** · simpan "
                f"nomor ini dan hubungi pengelola bila Anda ingin "
                f"mengetahui statusnya — kode lacak acak belum aktif "
                f"pada deployment ini.")
        st.success(
            f"✅ **Laporan terkirim & tercatat.** Diterima "
            f"**{fmt_wita(receipt['created_at'])}** · status awal: "
            f"menunggu verifikasi tim. {code_line}"
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
        "Teks sudah dibersihkan otomatis dari nomor/email/tautan dan "
        "ditinjau manusia sebelum tayang — tetapi nama bebas masih "
        "bisa lolos dari pembersih otomatis, jadi laporkan kepada "
        "pengelola bila Anda mengenali data pribadi di galeri. "
        "Kenali polanya sebelum jadi korban berikutnya.")
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
# MANUSIA — dan sejak v6.1.3 secara BUTA. Model ensemble sudah menilai
# tiap laporan saat masuk (skor, band, sinyal), tetapi saran itu TIDAK
# tampil di antrean pelabelan: peninjau membaca teksnya dulu, memilih
# label + kategori sendiri (tanpa nilai awal), baru menyimpan. Saran
# mesin baru tampil di daftar terverifikasi, sebagai pembanding
# pasca-label. Alasannya sama seperti dulu — memakai model sebagai
# penentu label akan merusak tujuan korpus: data latih baru harus
# berisi penilaian manusia yang independen, bukan pendapat model
# tentang datanya sendiri — dan saran yang dilihat SEBELUM memberi
# label sudah menggeser penilaian itu (anchoring), walau labelnya
# "tetap di tangan manusia".
#
# Sejak v6.1.4 (Ronde 6, M1) antrean pelabelan TIDAK LAGI terurut skor:
# urutan skor tertinggi dulu — yang dipakai v6.1.3 dengan komentar
# "fungsi triase antrean" — adalah kebocoran ordinal: posisi relatif
# saja sudah memberi tahu peninjau laporan mana yang dinilai model
# paling berisiko, tanpa satu angka pun tampil. Antrean pelabelan
# kini urut waktu masuk (created_at ASC, tanpa sinyal model apa pun);
# sejak v6.1.5 (Ronde 7, M3) expander triase HANYA menampilkan jumlah
# total laporan pending — tanpa ID, urutan, atau band — karena
# peringatan prosedural ("jangan dibuka dulu") terbukti bukan kontrol.
#
# Sejak v6.1.4 (Ronde 6, M2) label pertama DIBEKUKAN: unverify_report
# tidak lagi menghapus label, dan verify_report tidak menimpa label
# pertama bila laporan pernah diverifikasi sebelumnya — revisi
# pasca-paparan saran mesin hanya dicatat terpisah di label_log
# ('revisi_pasca_paparan'). Efektif sampai ekspor: view corpus_export
# (definisi di migrasi Turso, bukan di repo ini — diverifikasi
# 2026-11-08 dari sqlite_master live) membaca reports.label pada
# baris status='verified' + consent, jadi label korpus = label
# pertama selama kolom itu tak pernah ditulis ulang.
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

    Ini SARAN triase — bukan vonis; keputusan tetap di tangan
    peninjau. Kekuatan 'lemah' berarti zona abu-abu: baca teksnya
    sebelum memutuskan.

    Dipanggil HANYA sesudah label manusia tersimpan (daftar
    terverifikasi, sebagai pembanding pasca-label) — JANGAN dipakai
    untuk mengisi awal pilihan label di antrean pending (anchoring).
    (Ronde 5, M1.)
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
        return "SAH", "band RISIKO RENDAH (risiko rendah menurut model), tanpa sinyal kuat", "kuat"
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
    """Antrean PELABELAN: urut waktu masuk (created_at ASC).

    Sengaja TANPA sinyal model apa pun — bukan skor, bukan band,
    bukan urutan skor (Ronde 6, M1). Urutan skor tertinggi dulu
    adalah sinyal ordinal: peninjau belajar laporan mana yang dinilai
    model paling berisiko hanya dari posisinya. Antrean triase
    terurut skor ada terpisah (fetch_pending_triage) untuk
    perencanaan kapasitas — bukan untuk pelabelan.

    Ronde 8, GG-12: kolom yang diambil DIKUNCI eksplisit (bukan
    SELECT *) — skor/band/sinyal/pengayaan TIDAK PERNAH keluar dari
    basis data menuju kartu pelabelan, jadi kebocoran tidak lagi
    bergantung pada "UI tidak menampilkannya". Kartu pending hanya
    butuh id/teks/kanal/waktu/consent (+ via_ocr sebagai provenance
    teks, bukan sinyal mesin)."""
    return turso_execute(
        cfg,
        "SELECT id, channel, text_scrubbed, consent_data_use, "
        "created_at, via_ocr FROM reports WHERE status = 'pending' "
        "ORDER BY created_at ASC, id ASC LIMIT ?",
        [int(limit)])


def fetch_pending_triage(cfg: dict, limit: int = 50) -> list:
    """Antrean TRIASE operasional: skor model tertinggi dulu.

    Hanya untuk perencanaan kapasitas (berapa laporan berisiko
    menunggu) — JANGAN dipakai untuk memilih urutan pelabelan: urutan
    ini sendiri adalah sinyal mesin (Ronde 6, M1). Sejak v6.1.5
    (Ronde 7, M3) UI TIDAK LAGI menampilkan baris per laporan dari
    antrean ini — expander triase hanya menampilkan jumlah total —
    jadi fungsi ini dipertahankan sebagai helper data, bukan tampilan.
    """
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


def frozen_label(cfg: dict, report_id: int) -> str | None:
    """Label PERTAMA yang pernah diverifikasi untuk laporan ini.

    Dibaca dari label_log (aksi 'verifikasi' paling awal, ORDER BY
    id) — bukan dari reports.label — supaya label pertama tetap
    ditemukan walau barisnya pernah dikembalikan ke antrean dengan
    perilaku lama (label = NULL). None bila laporan belum pernah
    diverifikasi. (Ronde 6, M2.)"""
    try:
        rows = turso_execute(
            cfg,
            "SELECT label FROM label_log WHERE report_id = ? "
            "AND aksi = 'verifikasi' ORDER BY id ASC LIMIT 1",
            [int(report_id)])
    except Exception:
        return None
    return rows[0]["label"] if rows else None


def verify_report(cfg: dict, report_id: int, label: str, category: str,
                  gallery_visible: bool) -> str:
    """Verifikasi laporan; kembalikan label yang menjadi label korpus.

    LABEL PERTAMA DIBEKUKAN (Ronde 6, M2): label yang pertama kali
    diverifikasi adalah label korpus selamanya. Bila laporan ini
    pernah diverifikasi sebelumnya (mis. dikembalikan ke antrean
    sesudah saran mesin terlihat di daftar terverifikasi), label baru
    TIDAK menimpa label pertama: ia dicatat terpisah di label_log
    sebagai 'revisi_pasca_paparan' lengkap dengan nilai barunya, dan
    label korpus tetap label pertama. Efektif sampai ke ekspor: view
    corpus_export membaca reports.label pada baris status='verified'
    — dan kolom itu tidak pernah ditulis ulang sesudah verifikasi
    pertama. Kategori/galeri masih boleh berubah (bukan label)."""
    first = frozen_label(cfg, report_id)
    if first is None:
        # Pengaman kedua: label yang masih tersimpan di barisnya
        # sendiri (laporan yang dikembalikan pasca-v6.1.4 membawa
        # label pertamanya di kolom label).
        try:
            rows = turso_execute(
                cfg, "SELECT label FROM reports WHERE id = ?",
                [int(report_id)])
            first = rows[0]["label"] if rows else None
        except Exception:
            first = None
    if first is not None:
        # Tulis kembali label beku ke kolomnya juga: baris warisan yang
        # dikembalikan dengan perilaku lama (label = NULL) harus
        # mendapatkan kembali label pertamanya — bila tidak, view
        # corpus_export (label IS NOT NULL) akan kehilangan baris itu.
        turso_execute(
            cfg,
            "UPDATE reports SET status = 'verified', label = ?, "
            "category_modus = ?, gallery_visible = ?, "
            "verified_at = datetime('now') WHERE id = ? "
            "AND status = 'pending'",
            [first, category, 1 if gallery_visible else 0,
             int(report_id)])
        _log_label(cfg, report_id, "revisi_pasca_paparan", label)
        return first
    turso_execute(
        cfg,
        "UPDATE reports SET status = 'verified', label = ?, "
        "category_modus = ?, gallery_visible = ?, "
        "verified_at = datetime('now') WHERE id = ? AND status = 'pending'",
        [label, category, 1 if gallery_visible else 0, int(report_id)])
    _log_label(cfg, report_id, "verifikasi", label)
    return label


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
    """Kembalikan laporan terverifikasi ke antrean pending.

    Label TIDAK dihapus (Ronde 6, M2): label pertama dibekukan
    sebagai label korpus — menghapusnya (label = NULL, perilaku lama)
    membuat label kedua yang diberi sesudah saran mesin terlihat
    menjadi label korpus. Baris kembali pending dengan label
    pertamanya tetap tersimpan (tidak tampil di kartu pending);
    verifikasi ulang tidak menimpa label itu — revisinya dicatat
    terpisah di label_log ('revisi_pasca_paparan')."""
    try:
        rows = turso_execute(
            cfg, "SELECT label FROM reports WHERE id = ? "
                 "AND status = 'verified'", [int(report_id)])
        label = rows[0]["label"] if rows else None
    except Exception:
        label = None
    turso_execute(
        cfg,
        "UPDATE reports SET status = 'pending', "
        "verified_at = NULL, gallery_visible = 0 "
        "WHERE id = ? AND status = 'verified'",
        [int(report_id)])
    _log_label(cfg, report_id, "kembalikan", label)


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
    # Ronde 8, M3: distribusi band model HANYA atas laporan
    # TERVERIFIKASI. Agregat atas seluruh reports (termasuk pending)
    # adalah sinyal pra-label: dengan 1 laporan pending, "ESKALASI 1"
    # SAMA DENGAN band laporan itu — peninjau tahu bandnya sebelum
    # memberi label. Metrik lain (total/kanal/per hari) tetap atas
    # semua laporan: hitungan itu tidak mengungkap band per laporan.
    snap["band"] = {r["model_band"]: r["n"] for r in turso_execute(
        cfg, "SELECT model_band, COUNT(*) AS n FROM reports "
             "WHERE status = 'verified' GROUP BY model_band")}
    snap["channel"] = {r["channel"]: r["n"] for r in turso_execute(
        cfg, "SELECT channel, COUNT(*) AS n FROM reports "
             "GROUP BY channel")}
    # Ronde 7, S1: penyebut HANYA baris yang masih dalam alur
    # (pending/verified) — baris rejected/deleted tidak akan pernah
    # masuk korpus, jadi menghitungnya melesetkan "persen pelapor
    # yang menyetujui".
    row = turso_execute(
        cfg, "SELECT AVG(consent_data_use) AS r FROM reports "
             "WHERE status IN ('pending', 'verified')")[0]
    snap["consent_rate"] = (row["r"] or 0.0) * 100.0
    # Ronde 7, S2: durasi diukur sampai verifikasi PERTAMA (aksi
    # 'verifikasi' paling awal di label_log), bukan verified_at yang
    # tertimpa tiap verifikasi ulang sesudah unverify. Bila label_log
    # belum punya jejak itu (baris warisan), pakai verified_at.
    # Ronde 7, N1: saring timestamp anomali (verifikasi sebelum
    # submit) supaya satu baris rusak tidak menggeser rata-rata.
    row = turso_execute(
        cfg,
        "SELECT AVG((julianday(COALESCE(v.first_verified, "
        "r.verified_at)) - julianday(r.created_at)) * 24.0) AS h "
        "FROM reports r LEFT JOIN (SELECT report_id, "
        "MIN(created_at) AS first_verified FROM label_log "
        "WHERE aksi = 'verifikasi' GROUP BY report_id) v "
        "ON v.report_id = r.id "
        "WHERE COALESCE(v.first_verified, r.verified_at) IS NOT NULL "
        "AND COALESCE(v.first_verified, r.verified_at) "
        ">= r.created_at")[0]
    snap["avg_verify_hours"] = row["h"]
    snap["corpus_by_label"] = {r["label"]: r["n"] for r in turso_execute(
        cfg, "SELECT label, COUNT(*) AS n FROM corpus_export "
             "GROUP BY label")}
    snap["top_categories"] = turso_execute(
        cfg, "SELECT category_modus AS k, COUNT(*) AS n FROM reports "
             "WHERE status = 'verified' AND category_modus IS NOT NULL "
             "GROUP BY category_modus ORDER BY n DESC LIMIT 8")
    # Ronde 7, N3: kelompokkan per tanggal WITA (UTC+8), bukan UTC —
    # semua tampilan waktu lain di app memakai WITA; laporan dini hari
    # (00:00–07:59 WITA) sebelumnya terhitung di hari UTC sebelumnya.
    # Jendela 15 hari memberi ruang untuk pergeseran +8 jam.
    daily = {r["d"]: r["n"] for r in turso_execute(
        cfg, "SELECT date(created_at, '+8 hours') AS d, COUNT(*) AS n "
             "FROM reports "
             "WHERE created_at >= datetime('now', '-15 days') "
             "GROUP BY date(created_at, '+8 hours')")}
    today = (datetime.now(timezone.utc) + timedelta(hours=8)).date()
    snap["daily14"] = [
        ((today - timedelta(days=i)).isoformat(),
         daily.get((today - timedelta(days=i)).isoformat(), 0))
        for i in range(13, -1, -1)]
    snap["gold"] = gold_count(cfg)
    snap["disputed"] = disputed_count(cfg)  # Ronde 7, M4
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
                   "untuk galeri anonim + data latih — di antara laporan "
                   "yang masih dalam alur (pending/terverifikasi); yang "
                   "ditolak/dihapus tidak dihitung. (Ronde 7, S1.)")
    if s["avg_verify_hours"] is not None:
        st.caption(f"Rata-rata waktu verifikasi: "
                   f"{s['avg_verify_hours']:.1f} jam sejak submit "
                   f"sampai verifikasi pertama.")
    st.caption("Corong status: " + " · ".join(
        f"{k} {v}" for k, v in sorted(s["status"].items())))
    corpus_total = sum(s["corpus_by_label"].values())
    st.progress(min(corpus_total / 1000.0, 1.0),
                text=f"Korpus berlabel+consent: {corpus_total} / target "
                     f"±1.000 untuk retrain Tahap 3 ("
                     + ", ".join(f"{k} {v}" for k, v in
                                 sorted(s["corpus_by_label"].items()))
                     + ")")
    # Ronde 7, M4: klaim jujur — ini ukuran KESEPAKATAN dua peninjau,
    # bukan bukti label benar ("paling tepercaya" dulu melebihi yang
    # diukur). Perbedaan tinjauan kedua ditampilkan terpisah sebagai
    # antrean adjudikasi, bukan disembunyikan.
    st.caption(f"🥇 Disepakati dua peninjau: **{s.get('gold', 0)}** laporan — "
               "terverifikasi DAN tinjauan kedua memberi label yang sama. "
               "Ini ukuran kesepakatan dua peninjau, bukan bukti label "
               "benar: bila kedua peninjau keliru sama, baris itu tetap "
               "masuk hitungan.")
    if s.get("disputed"):
        st.caption(f"⚖️ {s['disputed']} laporan menunggu adjudikasi — "
                   "tinjauan kedua berbeda dari label tercatat; label "
                   "korpus belum berubah sampai peninjau utama "
                   "memutuskan di bagian tinjauan kedua di bawah.")
    c1, c2 = st.columns(2)
    with c1:
        st.caption("Laporan per hari (14 hari terakhir)")
        st.bar_chart({"Tanggal": [d for d, _ in s["daily14"]],
                      "Laporan": [n for _, n in s["daily14"]]},
                     x="Tanggal", y="Laporan")
        # Ronde 8, M3: distribusi ini HANYA atas laporan terverifikasi
        # (lihat analytics_snapshot) — dinyatakan eksplisit di label.
        st.caption("Distribusi band model (terverifikasi): "
                   + " · ".join(
                       f"{k} {v}" for k, v in sorted(s["band"].items()))
                   if s["band"] else
                   "Distribusi band model (terverifikasi): "
                   "belum ada laporan terverifikasi.")
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
        "app. Panel ini mencakup SEMUA laporan (termasuk yang masih "
        "menunggu verifikasi) — KECUALI distribusi band model dan "
        "progres korpus di atas, yang hanya atas laporan terverifikasi "
        "(band laporan pending tidak ditampilkan di mana pun sebelum "
        "pelabelan).")


def _report_meta(cfg: dict, r: dict, blind: bool = False) -> str:
    """Metadata kartu laporan. blind=True (Ronde 7, S4): kartu pending
    HANYA menampilkan kanal/waktu/consent — jumlah laporan pengirim
    yang sama dan jumlah teks identik adalah sinyal agregat di luar
    teks pesan dan tidak boleh dibaca sebelum label diputuskan."""
    parts = [
        f"kanal {CHANNELS.get(r['channel'], r['channel'])}",
        f"submit {fmt_wita(r['created_at'])}",
        "consent data: YA" if r["consent_data_use"]
        else "consent data: tidak",
    ]
    if blind:
        return " · ".join(parts)
    # Ronde 8, S6: penanda provenance OCR pada daftar terverifikasi.
    if r.get("via_ocr"):
        parts.append("📷 teks dari OCR")
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
        "Ruang kerja peninjau. **Label ditentukan manusia, secara "
        "buta**: saran mesin (skor, band, sinyal) disembunyikan sampai "
        "label tersimpan — baca teksnya dulu, putuskan sendiri, baru "
        "saran mesin tampil sebagai pembanding di daftar terverifikasi. "
        "Antrean pelabelan di bawah urut waktu masuk (tanpa sinyal "
        "model); expander triase di bawah hanya menampilkan JUMLAH "
        "total laporan menunggu (tanpa ID, urutan, atau band) dan bukan "
        "untuk pelabelan. Label pertama yang "
        "tersimpan **dibekukan** sebagai label korpus — bila laporan "
        "dikembalikan ke antrean lalu diverifikasi ulang, label korpus "
        "tetap label pertama dan revisinya hanya dicatat di jejak "
        "audit. Laporan terverifikasi + consent masuk korpus data "
        "latih; yang ditandai tampil galeri muncul di Galeri Modus "
        "publik.")
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

    st.markdown("#### Antrean pelabelan — urutan waktu masuk "
                "(tanpa sinyal model)")
    st.caption(
        "Antrean ini urut waktu masuk (paling lama menunggu di atas) — "
        "bukan urut skor model. Urutan skor adalah sinyal mesin, jadi "
        "tidak dipakai di sini. Perencanaan kapasitas ada di bawah "
        "(expander tertutup yang hanya menampilkan jumlah total, "
        "tanpa daftar terurut skor).")
    if not pending:
        st.info("Antrean kosong. Tidak ada laporan menunggu verifikasi.")
    # Pelabelan BUTA (Ronde 5, M1; diperkuat Ronde 6, M1): kartu pending
    # TIDAK menampilkan skor, band, sinyal, atau saran mesin apa pun —
    # dan pilihan label/kategori TANPA nilai awal (index=None +
    # placeholder), supaya tidak ada jangkar dari model sebelum
    # peninjau memutuskan sendiri dari teksnya. Antreannya pun kini
    # urut waktu masuk, bukan skor (urutan skor = sinyal ordinal).
    # Saran baru dihitung & ditampilkan di daftar terverifikasi di
    # bawah, sesudah label tersimpan.
    for r in pending:
        with st.container(border=True):
            st.markdown(f"**Laporan #{r['id']}**")
            st.markdown(f"> {r['text_scrubbed']}")
            # Kartu pending HANYA teks + metadata netral (Ronde 7):
            # M2 — peringatan riwayat verifikasi DIHAPUS: fakta
            # riwayat itu sendiri sinyal bahwa seseorang sudah pernah
            # menilai baris ini; jejak pembekuan label hanya ada di
            # log admin, bukan di kartu pelabelan. S3 — pengayaan
            # intake (umur domain) DIHAPUS dari kartu, tampil sesudah
            # label tersimpan di daftar terverifikasi. S4 — metadata
            # pengirim/duplikasi DIHAPUS via blind=True.
            st.caption(_report_meta(cfg, r, blind=True))
            # Ronde 8, S6: provenance OCR — peninjau tahu teks ini
            # dibaca dari gambar, jadi salah baca OCR (huruf tertukar)
            # bisa dipertimbangkan sebelum memberi label.
            if r.get("via_ocr"):
                st.caption("📷 Teks ini dibaca dari tangkapan layar "
                           "(OCR) — periksa ejaan: mesin OCR bisa "
                           "salah membaca huruf/angka.")
            st.caption("🤖 Saran mesin disembunyikan sampai label "
                       "tersimpan (pelabelan buta) — putuskan dari "
                       "teksnya.")
            c1, c2, c3 = st.columns([2, 2, 1])
            label = c1.selectbox(
                "Label", LABELS, index=None,
                placeholder="— pilih label —",
                key=f"adm_label_{r['id']}")
            category = c2.selectbox(
                "Kategori modus", CATEGORIES, index=None,
                placeholder="— pilih kategori —",
                key=f"adm_cat_{r['id']}")
            gallery = c3.checkbox(
                "Tampil di galeri", value=False,
                key=f"adm_gal_{r['id']}")
            b1, b2, b3 = st.columns(3)
            if b1.button("✅ Verifikasi", type="primary",
                         key=f"adm_verify_{r['id']}"):
                if label is None or category is None:
                    st.warning("Pilih label dan kategori dulu sebelum "
                               "menyimpan verifikasi.")
                else:
                    eff_label = verify_report(cfg, r["id"], label,
                                              category, gallery)
                    if eff_label != label:
                        st.success(
                            f"Laporan #{r['id']} terverifikasi kembali "
                            "— label korpus tetap label pertama "
                            "(dibekukan); label "
                            f"{label} yang Anda beri dicatat terpisah "
                            "sebagai revisi pasca-paparan di jejak "
                            "audit.")
                    else:
                        st.success(f"Laporan #{r['id']} terverifikasi "
                                   f"sebagai {label}.")
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

    # Antrean triase (Ronde 6, M1; dikunci teknis Ronde 7, M3) —
    # peringatan prosedural ("JANGAN dibuka sebelum selesai melabeli")
    # BUKAN kontrol: peninjau tetap bisa membukanya dan membaca urutan
    # skor + band. Sejak v6.1.5 expander ini HANYA menampilkan JUMLAH
    # total laporan pending — tanpa ID, tanpa urutan, tanpa band, tanpa
    # teks, tanpa tombol label — sehingga tidak ada lagi sinyal mesin
    # yang bisa terbaca sebelum pelabelan selesai. Helper triase
    # terurut skor tetap ada sebagai helper data di luar UI.
    with st.expander("📊 Antrean triase (opsional) — jumlah laporan "
                     "menunggu, BUKAN untuk pelabelan"):
        st.caption(
            "Hanya jumlah total laporan pending yang tampil di sini — "
            "tanpa ID, tanpa urutan skor, tanpa band — supaya tidak ada "
            "sinyal mesin yang terbaca sebelum pelabelan selesai. "
            "Antrean ini hanya untuk perencanaan kapasitas, bukan "
            "untuk memilih urutan pelabelan.")
        try:
            n_pending = count_status(cfg, "pending")
        except Exception as exc:
            st.caption(f"Antrean triase belum bisa dimuat: {exc}")
            n_pending = None
        if n_pending is None:
            pass
        elif not n_pending:
            st.caption("Tidak ada laporan pending.")
        else:
            st.caption(f"{n_pending} laporan menunggu verifikasi.")

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
            # Metadata lengkap + pengayaan intake baru tampil DI SINI
            # — sesudah label tersimpan (Ronde 7, S3/S4): di kartu
            # pending keduanya disembunyikan agar tidak menjadi sinyal
            # pra-label.
            st.caption(_report_meta(cfg, r))
            enr_v = enrichment_summary(r.get("enrichment"))
            if enr_v:
                st.caption(f"🌐 Pengayaan intake: {enr_v}")
            # Saran mesin baru tampil DI SINI — sesudah label manusia
            # tersimpan — sebagai pembanding pasca-label, bukan jangkar
            # sebelum pelabelan. (Ronde 5, M1.)
            sug_label, sug_reason, sug_strength = suggest_label(r)
            sug_cat = suggest_category(r)
            cocok = ("sama dengan saran" if sug_label == r["label"]
                     else "berbeda dari saran")
            st.caption(
                f"🤖 Saran mesin saat itu ({sug_strength}): "
                f"**{sug_label}** · kategori **{sug_cat}** — "
                f"{sug_reason}. Label manusia di atas: **{r['label']}**"
                f" — {cocok}.")
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
    # (buta): yang hasilnya sama masuk hitungan DISEPAKATI DUA
    # PENINJAU; yang berbeda hanya DICATAT di label_log — label asli
    # tidak berubah oleh tinjauan kedua. Sejak v6.1.5 (Ronde 7, M4)
    # perbedaan itu punya jalur ADJUDIKASI (adjudicate_report):
    # peninjau utama memutuskan "pertahankan" atau "diragukan", dan
    # putusan tercatat di label_log — tanpa adjudikasi, perbedaan
    # menggantung sebagai "menunggu adjudikasi" di Analitik.
    # Ronde 6, S5: pilihan label TANPA nilai awal (index=None —
    # sebelumnya default LABELS[0] = SMISHING, jangkar bawaan);
    # ID/tanggal/kanal disembunyikan agar sampel tak bisa dicocokkan
    # ke daftar terverifikasi di atas; nama peninjau kedua dicatat di
    # jejak audit supaya peninjau pertama dan kedua bisa dibedakan.
    # Sisa batasan yang jujur: teks yang sama juga tampil di daftar
    # terverifikasi, jadi pencocokan lewat teks masih mungkin —
    # tinjauan kedua sebaiknya dilakukan peninjau yang berbeda dari
    # peninjau pertama.
    st.markdown("#### 🥇 Disepakati dua peninjau — tinjauan kedua")
    st.caption(
        f"Disepakati dua peninjau saat ini: **{gold_count(cfg)}** "
        "laporan. "
        "Nilai ulang sampel acak di bawah ini dari teksnya saja — "
        "label tercatat sengaja tidak ditampilkan. Setiap tinjauan "
        "tercatat di jejak audit (label_log). Teks yang sama juga "
        "tampil di daftar terverifikasi di atas, jadi pencocokan "
        "lewat teks masih mungkin — sebaiknya peninjau kedua adalah "
        "orang yang berbeda dari peninjau pertama. Kesepakatan dua "
        "peninjau BUKAN bukti label benar — bila keduanya keliru sama, "
        "baris itu tetap masuk hitungan.")
    reviewer2 = st.text_input(
        "Nama/inisial peninjau kedua (opsional — dicatat di jejak "
        "audit; isi dengan nama berbeda dari peninjau pertama bila "
        "memungkinkan)",
        key="adm_second_actor")
    sample = fetch_second_review_sample(cfg, 3)
    if not sample:
        st.caption("Tidak ada sampel menunggu tinjauan kedua "
                   "(semua terverifikasi sudah ditinjau, atau belum "
                   "ada yang terverifikasi).")
    for i, r in enumerate(sample):
        with st.container(border=True):
            st.markdown(
                f"**Sampel tinjauan kedua #{i + 1}** · ID, tanggal, "
                "dan kanal disembunyikan agar sampel tidak bisa "
                "dicocokkan dengan daftar terverifikasi di atas.")
            st.markdown(f"> {r['text_scrubbed']}")
            sc1, sc2 = st.columns([2, 1])
            lab2 = sc1.selectbox(
                "Label menurut penilaianmu (tinjauan kedua)", LABELS,
                index=None, placeholder="— pilih label —",
                key=f"adm_second_{r['id']}")
            if sc2.button("✔️ Catat tinjauan kedua",
                          key=f"adm_second_btn_{r['id']}"):
                if lab2 is None:
                    st.warning("Pilih label dulu sebelum mencatat "
                               "tinjauan kedua.")
                    continue
                hasil = second_review(
                    cfg, r["id"], lab2,
                    actor=(reviewer2 or "").strip()
                    or "verifikator-2")
                if hasil == "cocok":
                    st.success(
                        f"Laporan #{r['id']}: tinjauan kedua COCOK "
                        "dengan label tercatat — masuk hitungan "
                        "disepakati dua peninjau.")
                elif hasil == "beda":
                    st.warning(
                        f"Laporan #{r['id']}: tinjauan kedua BERBEDA "
                        "dari label tercatat. Perbedaan dicatat di "
                        "label_log; label asli tidak berubah.")
                else:
                    st.info(f"Laporan #{r['id']} sudah tidak "
                            "terverifikasi — tinjauan dibatalkan.")
                st.rerun()

    # Adjudikasi (Ronde 7, M4): perbedaan tinjauan kedua tidak boleh
    # menggantung tanpa putusan. Peninjau utama memutuskan per laporan:
    # "pertahankan" (label beku dipertahankan) atau "diragukan" (label
    # beku diragukan — ditandai untuk ditinjau ulang di luar app).
    # Label korpus TIDAK berubah oleh adjudikasi; putusan hanya
    # tercatat di label_log sebagai 'adjudikasi' dan menutup antrean.
    disputed = fetch_disputed(cfg)
    if disputed:
        st.markdown("#### ⚖️ Menunggu adjudikasi")
        st.caption(
            f"{len(disputed)} laporan terverifikasi yang tinjauan "
            "keduanya BERBEDA dari label tercatat dan belum diputuskan. "
            "Label korpus tidak berubah apa pun putusannya; putusan "
            "hanya menutup antrean ini dan tercatat di jejak audit.")
        for r in disputed:
            with st.container(border=True):
                st.markdown(f"**Laporan #{r['id']}** · label tercatat "
                            f"**{r['label']}**")
                st.markdown(f"> {r['text_scrubbed']}")
                d1, d2 = st.columns(2)
                if d1.button("✅ Pertahankan label beku",
                             key=f"adm_adj_keep_{r['id']}"):
                    adjudicate_report(
                        cfg, r["id"], "pertahankan",
                        actor=(reviewer2 or "").strip() or "verifikator")
                    st.rerun()
                if d2.button("⚠️ Tandai label diragukan",
                             key=f"adm_adj_doubt_{r['id']}"):
                    adjudicate_report(
                        cfg, r["id"], "diragukan",
                        actor=(reviewer2 or "").strip() or "verifikator")
                    st.rerun()
