# -*- coding: utf-8 -*-
"""Fraud Triage — konsol triase smishing (Streamlit), versi v5.1.

Menjalankan model CHOSEN proyek Fraud Triage: Ensemble (Top-3 Terkalibrasi)
dengan kebijakan dua ambang t_close=0,010 / t_esc=0,135 (Bagian 10 notebook),
dilengkapi LAPISAN ATURAN (rules.py): kombinasi >= 2 sinyal kuat memaksa
band naik ke ESKALASI — aturan tidak pernah mengubah skor. Logika model
ada di triage_core.py, logika aturan di rules.py; keduanya bisa diuji
tanpa Streamlit.

Baru di v5.1 (rapi-rapi UI): sidebar kini mulai tertutup (di HP sidebar
yang terbuka menekan konten utama sampai teks bertumpuk), dan tab
Perjalanan Riset dirapikan — kotak alur tahapan memakai vonis SINGKAT
(vonis lengkap tetap di bagian Detail), diagram skor diganti bar
horizontal per tahap (bar lama bertumpuk sampai >100%), CSS responsif
(di layar sempit kotak alur menumpuk vertikal penuh), metrik PR-AUC
memakai container horizontal, dan ada heatmap Altair per kategori
Tahap 2C vs 2D (target yang sembuh vs kategori yang regresi terlihat
sekali pandang). Simulator ambang dicatat sebagai bahan v5.2.

Baru di v5 (tab "🧪 Perjalanan Riset"): halaman dokumentasi riset yang
menampilkan SETIAP tahap percobaan proyek ini — Tahap 0 (baseline &
diagnosis), Tahap 1 (sinyal penenang), Tahap 2 (fine-tune dwibahasa),
dan loop perbaikan 2D — lengkap dengan diagram skor gerbang dan vonis
apa adanya, termasuk dua paket yang DITOLAK (2C gagal tipis; 2D lolos
2 dari 4 gerbang). Model yang berjalan TIDAK berubah: tetap ensemble
CHOSEN + rules Tahap 1. Angka di halaman itu dibaca dari results.json
yang dibangkitkan dari file evaluasi terverifikasi (gen_results.py);
logika halamannya ada di journey.py.

Baru di v4 (Tahap 1 perbaikan Indonesia — SINYAL PENENANG): baseline set
evaluasi Indonesia v1 (300 pesan berlabel) membuktikan model mengeskalasi
84% pesan SAH Indonesia (sah lolos hanya 16,0%) karena register formal
institusional tak pernah ada di data latihnya — lapisan aturan sendiri
0x salah tembak. rules.py kini punya arah sebaliknya yang SANGAT
terbatas: untuk pola resmi berformat sangat jelas (OTP standar tanpa
tautan; tautan hanya ke domain resmi persis; notifikasi transaksi
terstruktur tanpa tautan), band ESKALASI model boleh turun TEPAT satu
tingkat ke REVIEW ANALIS. Penenang tidak pernah menutup otomatis
(AUTO-CLOSE), tidak mengubah skor, dan gugur total bila sinyal kuat
S2/S3 aktif atau aturan keamanan terpicu. Detail & angka ukurnya di
README.md. Ini tambal terukur, bukan obat — perbaikan sejatinya adalah
fine-tune dwibahasa (Tahap 2).

Baru di v3 (menutup kritik atas v2):
  A. Ekspor CSV: hasil batch, riwayat sesi, dan log koreksi bisa diunduh.
  B. Batch layak kerja: bilah progres per pesan + batas 200 baris ditegakkan.
     (Engine publik hanya menyediakan penilaian per teks — triage() —
     jadi batch berjalan sekuensial dengan progres, bukan paralel.)
  C. Batas input: analisis tunggal maks 2.000 karakter (dipotong +
     peringatan), batch maks 200 baris (di luar itu ditolak jelas).
  D. Tombol koreksi: pengguna bisa menandai band yang benar menurutnya;
     tercatat sebagai log umpan balik DI SESI INI SAJA (demo).
  E. Tab "🇮🇩 Evaluasi ID": set uji kecil buatan 16 pesan Indonesia
     berlabel harapan, dijalankan apa adanya — BUKAN benchmark.
  F. Uji float16 DistilBERT dijalankan terpisah dan TIDAK diadopsi:
     latensi CPU memburuk +56% (melampaui batas adopsi +25%), jadi app
     tetap fp32. Detail di README.md.
  G. Kalimat penjelasan vonis di kartu hasil + footer versi.

Jalankan lokal:  streamlit run app.py
Deploy: lihat README.md (Streamlit Community Cloud).
"""

import os
from datetime import datetime

import pandas as pd
import streamlit as st

from triage_core import TriageEngine, ZONES
from rules import apply_rules_and_calm
from journey import render_journey

APP_VERSION = "v5.1"
MAX_SINGLE_CHARS = 2000   # butir C: batas analisis tunggal
MAX_BATCH_LINES = 200     # butir B/C: batas baris batch
CSV_TEXT_CHARS = 200      # teks dipotong aman di ekspor CSV

st.set_page_config(page_title="Fraud Triage — Konsol Triase Smishing",
                   page_icon="🛡️", layout="wide",
                   initial_sidebar_state="collapsed")

# ---------------------------------------------------------------------------
# Gaya: tema "fraud ops console" (pelengkap .streamlit/config.toml)
# ---------------------------------------------------------------------------
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
.ft-header {
  padding: 1.1rem 1.3rem; border-radius: 12px; margin-bottom: 0.4rem;
  background: linear-gradient(120deg, #141c30 0%, #1b1030 100%);
  border: 1px solid #2a3a5f;
}
.ft-header h1 {margin: 0; font-size: 1.65rem; color: #f2f5fb;}
.ft-header p {margin: 0.35rem 0 0 0; color: #aebad2; font-size: 0.95rem;}
.ft-card {
  padding: 1rem 1.2rem; border-radius: 12px; margin: 0.6rem 0 0.8rem 0;
  background: #111a2e; border: 1px solid #2a3a5f;
}
.ft-band {font-size: 1.3rem; font-weight: 700; color: #f2f5fb;}
.ft-zone-key {font-size: 0.85rem; font-weight: 400; color: #aebad2;}
.ft-score {
  font-size: 2.6rem; font-weight: 800; line-height: 1.05; color: #ffffff;
}
.ft-score small {font-size: 0.9rem; font-weight: 400; color: #aebad2;}
.ft-desc {color: #c6d0e4; margin-top: 0.3rem;}
.ft-verdict {
  color: #e8edf7; margin-top: 0.55rem; padding: 0.5rem 0.7rem;
  background: #0d1526; border: 1px solid #2a3a5f; border-radius: 8px;
  font-size: 0.93rem;
}
.ft-badge {
  display: inline-block; margin-top: 0.6rem; padding: 0.45rem 0.7rem;
  border-radius: 8px; background: #3a1420; border: 1px solid #ef4444;
  color: #fecaca; font-size: 0.92rem;
}
.ft-badge-calm {
  display: inline-block; margin-top: 0.6rem; padding: 0.45rem 0.7rem;
  border-radius: 8px; background: #0f2e1d; border: 1px solid #22c55e;
  color: #bbf7d0; font-size: 0.92rem;
}
.ft-modelband {color: #aebad2; font-size: 0.9rem; margin-top: 0.45rem;}
.ft-bar-wrap {margin: 0.4rem 0 1.1rem 0;}
.ft-bar {
  position: relative; display: flex; height: 16px; border-radius: 8px;
  overflow: visible; margin-top: 26px;
}
.ft-seg-close {background: #22c55e; width: 20%; border-radius: 8px 0 0 8px;}
.ft-seg-review {background: #eab308; width: 40%;}
.ft-seg-esc {background: #ef4444; width: 40%; border-radius: 0 8px 8px 0;}
.ft-marker {
  position: absolute; top: -7px; width: 3px; height: 30px;
  background: #ffffff; border-radius: 2px;
  box-shadow: 0 0 6px rgba(255,255,255,0.8);
}
.ft-marker-label {
  position: absolute; top: -30px; transform: translateX(-50%);
  color: #ffffff; font-weight: 700; font-size: 0.95rem; white-space: nowrap;
}
.ft-bar-labels {position: relative; height: 1.1rem; color: #8fa1c0;
  font-size: 0.78rem; margin-top: 4px;}
.ft-bar-labels span {position: absolute; transform: translateX(-50%);}
.ft-footer {
  text-align: center; color: #8fa1c0; font-size: 0.85rem;
  margin-top: 2.2rem;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Contoh pesan siap-klik (probe resmi notebook Bagian 13.5 + korpus mini ID)
# ---------------------------------------------------------------------------
SAMPLES = {
    "💬 Pesan sah (EN)":
        "Hi, running 10 mins late — start the meeting without me",
    "🔢 Pesan berkode OTP":
        "Kode OTP Anda 481920. JANGAN bagikan ke siapa pun.",
    "🏦 OTP bank asli (ID)":
        "BCA: Kode OTP Anda 739201 berlaku 5 menit. JANGAN berikan kode "
        "ini kepada siapa pun, termasuk pihak yang mengaku dari BCA. "
        "Abaikan bila Anda tidak merasa melakukan transaksi.",
    "🎁 Undian palsu (ID)":
        "Selamat! Anda memenangkan undian Rp25.000.000, klaim di "
        "dana-undian2026.cc",
    "🚨 Spam pemblokiran akun (EN)":
        "URGENT: your account will be blocked today, verify PIN at "
        "secure-login-verify.xyz",
    "🏦 Smishing bank (ID)":
        "PENTING! Rekening BCA Anda akan DIBLOKIR hari ini karena aktivitas "
        "mencurigakan. Verifikasi sekarang di bit.ly/verif-bca-sekarang "
        "atau dana Anda hangus.",
    "📦 Smishing paket (ID)":
        "Paket J&T Anda TERTAHAN di gudang karena alamat tidak lengkap. "
        "Bayar biaya antar ulang Rp15.000 di jnt-kirimulang.top agar paket "
        "tidak dikembalikan.",
}

# Hasil arena test notebook (Bagian 9) — PR-AUC, jangan diubah tanpa rerun.
BENCHMARK = [
    ("Ensemble (Top-3 Terkalibrasi) — CHOSEN", 0.986, 0.947, 0.026),
    ("DistilBERT multilingual (fine-tune)", 0.985, 0.947, 0.010),
    ("TF-IDF + Fitur Angka + Logistic Regression", 0.980, 0.924, 0.009),
    ("TF-IDF + Naive Bayes", 0.970, 0.916, 0.013),
    ("TF-IDF + Logistic Regression", 0.959, 0.893, 0.039),
    ("TF-IDF + Gradient Boosting", 0.933, 0.863, 0.010),
]

# Tampilan band final: nama ramah + warna kartu.
ZONE_DISPLAY = {
    "AUTO-CLOSE": ("AMAN", "🟢", "#22c55e"),
    "REVIEW ANALIS": ("REVIEW ANALIS", "🟡", "#eab308"),
    "ESKALASI": ("ESKALASI", "🔴", "#ef4444"),
}

# ---------------------------------------------------------------------------
# Set evaluasi Indonesia (butir E) — DIKUNCI sebelum dijalankan.
# 16 pesan BUATAN meniru gaya umum; bank memakai nama FIKTIF ("Bank
# Nusantara" / "Bank Sentosa") dan tautan mencurigakan memakai domain
# fiktif. Ini BUKAN benchmark — hanya panel transparansi kecil.
# Definisi "sesuai": SAH -> band final AUTO-CLOSE atau REVIEW ANALIS;
# SMISHING -> band final ESKALASI.
# ---------------------------------------------------------------------------
ID_EVAL_SET = [
    # --- 8 pesan SAH -------------------------------------------------------
    {"label": "SAH", "kategori": "OTP bank asli",
     "text": "Bank Nusantara: Kode OTP Anda 582914 berlaku 5 menit. "
             "JANGAN berikan kode ini kepada siapa pun, termasuk pihak "
             "yang mengaku dari bank. Abaikan bila Anda tidak melakukan "
             "transaksi ini."},
    {"label": "SAH", "kategori": "Notifikasi transaksi bank",
     "text": "Bank Sentosa: Transaksi debit Rp250.000 di Indomaret "
             "pada 22/10 pukul 13.02. Saldo akhir Rp3.412.000. Bukan "
             "Anda? Hubungi call center resmi 1500999."},
    {"label": "SAH", "kategori": "Pengingat tagihan telekomunikasi resmi",
     "text": "Halo, tagihan pascabayar Anda sebesar Rp189.000 jatuh "
             "tempo 25 Oktober. Bayar melalui aplikasi MyTelco atau "
             "gerai resmi terdekat. Abaikan pesan ini bila sudah "
             "membayar."},
    {"label": "SAH", "kategori": "Pesan kurir wajar",
     "text": "Paket Anda sedang diantar kurir hari ini antara pukul "
             "09.00-17.00. Mohon siapkan uang pas Rp75.000 untuk COD. "
             "Terima kasih."},
    {"label": "SAH", "kategori": "Pesan pribadi",
     "text": "Mak, aku sudah sampai kos dengan selamat. Nanti malam "
             "aku telepon ya. Jangan lupa makan dan istirahat."},
    {"label": "SAH", "kategori": "Notifikasi keamanan bank (domain resmi)",
     "text": "Bank Nusantara: Kami mendeteksi login dari perangkat "
             "baru pada 22/10 pukul 08.14. Bila bukan Anda, segera ubah "
             "kata sandi melalui aplikasi resmi atau kunjungi "
             "nusantarabank.co.id/keamanan."},
    {"label": "SAH", "kategori": "Info tagihan e-statement",
     "text": "E-statement kartu kredit Anda periode Oktober telah "
             "terbit di aplikasi. Total tagihan Rp1.240.000, pembayaran "
             "minimum Rp124.000, jatuh tempo 10 November."},
    {"label": "SAH", "kategori": "Undangan rapat kantor",
     "text": "Reminder: rapat koordinasi besok pukul 10.00 di ruang "
             "Melati. Mohon bawa laporan mingguan masing-masing. "
             "Terima kasih. - Sekretariat"},
    # --- 8 pesan SMISHING --------------------------------------------------
    {"label": "SMISHING", "kategori": "Blokir akun + tautan aneh",
     "text": "PENTING! Rekening Bank Nusantara Anda akan DIBLOKIR "
             "hari ini. Verifikasi sekarang di nusantara-aman.xyz "
             "sebelum dana Anda hangus."},
    {"label": "SMISHING", "kategori": "Undian palsu",
     "text": "Selamat! Nomor Anda memenangkan undian Rp50.000.000 "
             "dari program loyalitas. Klaim hadiah Anda sekarang di "
             "bit.ly/klaim-undi50 sebelum berakhir!"},
    {"label": "SMISHING", "kategori": "Kurir palsu + tautan",
     "text": "Paket Anda TERTAHAN di gudang. Bayar biaya antar ulang "
             "Rp15.000 melalui kurir-cepat.top/bayar agar paket tidak "
             "dikembalikan hari ini."},
    {"label": "SMISHING", "kategori": "Tagihan palsu + suruh unduh APK",
     "text": "Tagihan listrik Anda menunggak Rp312.000. Unduh aplikasi "
             "pembayaran resmi di tagihan-listrik.ceklis.click/app.apk "
             "dan bayar sekarang juga untuk menghindari pemutusan."},
    {"label": "SMISHING", "kategori": "CS palsu minta OTP",
     "text": "CS Bank Sentosa: Kami mendeteksi transaksi mencurigakan "
             "di akun Anda. Masukkan kode OTP yang baru kami kirim "
             "kepada petugas kami melalui chat untuk membatalkannya "
             "sekarang."},
    {"label": "SMISHING", "kategori": "Investasi bodong",
     "text": "Investasi aman profit 30% per minggu, modal kembali "
             "dijamin! Gabung grup VIP kami di t.me/investcuan88 dan "
             "mulai dengan Rp100.000 saja. Kuota terbatas!"},
    {"label": "SMISHING", "kategori": "Hadiah e-wallet + pemendek tautan",
     "text": "Selamat! Anda mendapat saldo e-wallet gratis Rp300.000. "
             "Klaim sekarang di s.id/saldo-gratis300 sebelum hangus "
             "malam ini!"},
    {"label": "SMISHING", "kategori": "Verifikasi akun + urgensi",
     "text": "Akun marketplace Anda akan dinonaktifkan dalam 24 jam "
             "karena pelanggaran kebijakan. Lakukan verifikasi data di "
             "akun-aman.click/login untuk memulihkannya."},
]


@st.cache_resource(show_spinner="Memuat ensemble (termasuk DistilBERT)…")
def load_engine():
    bert_source = None
    artifact_repo_id = None
    try:
        bert_source = st.secrets.get("BERT_MODEL_PATH") or st.secrets.get(
            "BERT_MODEL_ID")
        artifact_repo_id = st.secrets.get("ARTIFACT_REPO_ID")
    except Exception:
        bert_source = None
        artifact_repo_id = None
    bert_source = bert_source or os.environ.get("BERT_MODEL_PATH") \
        or os.environ.get("BERT_MODEL_ID")
    artifact_repo_id = artifact_repo_id or os.environ.get("ARTIFACT_REPO_ID")
    # Mesin tetap fp32: uji float16 (v3) gagal batas adopsi latensi —
    # lihat README.md bagian performa.
    return TriageEngine(bert_source=bert_source,
                        artifact_repo_id=artifact_repo_id)


def analyze_one(engine, text):
    """Satu pemeriksaan lengkap: skor model + aturan + sinyal penenang."""
    res = engine.triage(text)
    final_zone, rule = apply_rules_and_calm(text, res["zone"])
    return {"text": text, "res": res, "rule": rule, "final_zone": final_zone}


def _std_record(analysis):
    """Rekaman standar satu pemeriksaan (untuk tabel & ekspor CSV)."""
    calm = analysis["rule"].get("calm", {})
    return {
        "text": analysis["text"],
        "score": analysis["res"]["p_scam"],
        "zone_model": analysis["res"]["zone"],
        "zone_final": analysis["final_zone"],
        "rule_triggered": bool(analysis["rule"]["triggered"]),
        "signals": list(analysis["rule"]["active_signals"]),
        "calm_applied": bool(calm.get("lowered")),
        "calm_reasons": list(calm.get("reasons", [])),
    }


def _short(text, n):
    return text if len(text) <= n else text[:n] + "…"


def _export_csv(records, extra_key=None):
    """Bangun berkas CSV (bytes) dari rekaman standar — butir A.

    Kolom: Teks (dipotong aman), Skor, Band model, Band final,
    Aturan terpicu, Sinyal aktif (+ kolom ekstra bila diminta,
    mis. band koreksi pengguna pada log koreksi).
    """
    rows = []
    for r in records:
        row = {
            "Teks": _short(r["text"], CSV_TEXT_CHARS),
            "Skor": round(r["score"], 3),
            "Band model": r["zone_model"],
            "Band final": r["zone_final"],
            "Aturan terpicu": "Ya" if r["rule_triggered"] else "Tidak",
            "Sinyal aktif": "+".join(r["signals"]),
            "Sinyal penenang": ("Ya — " + "; ".join(r["calm_reasons"]))
            if r.get("calm_applied") else "Tidak",
        }
        if extra_key and extra_key in r:
            row[extra_key[0]] = r[extra_key[1]]
        rows.append(row)
    return pd.DataFrame(rows).to_csv(index=False).encode("utf-8")


def _bar_position(p, t_close, t_esc):
    """Posisi penanda pada bilah skor (skala keping-linear).

    Sumbu 0..1 diperas keping demi keping — [0, t_close] -> 0-20%,
    [t_close, t_esc] -> 20-60%, [t_esc, 1] -> 60-100% — agar ketiga zona
    kebijakan terlihat jelas; pada sumbu linear murni zona AUTO-CLOSE
    (lebar 0,010) tidak akan kelihatan sama sekali.
    """
    anchors = [(0.0, 0.0), (t_close, 20.0), (t_esc, 60.0), (1.0, 100.0)]
    for (x0, y0), (x1, y1) in zip(anchors, anchors[1:]):
        if p <= x1:
            if x1 == x0:
                return y1
            return y0 + (y1 - y0) * (p - x0) / (x1 - x0)
    return 100.0


def score_bar_html(p, t_close, t_esc):
    pos = _bar_position(p, t_close, t_esc)
    return f"""
<div class="ft-bar-wrap">
  <div class="ft-bar">
    <div class="ft-seg-close"></div><div class="ft-seg-review"></div>
    <div class="ft-seg-esc"></div>
    <div class="ft-marker" style="left:{pos:.1f}%"></div>
    <div class="ft-marker-label" style="left:{pos:.1f}%">{p:.3f}</div>
  </div>
  <div class="ft-bar-labels">
    <span style="left:0%; transform:none">0</span>
    <span style="left:20%">t_close {t_close:.3f}</span>
    <span style="left:60%">t_esc {t_esc:.3f}</span>
    <span style="left:100%; transform:translateX(-100%)">1</span>
  </div>
</div>"""


def verdict_sentence(analysis, t_close, t_esc):
    """Kalimat penjelasan vonis (butir G) — satu-dua kalimat, apa adanya."""
    res, rule = analysis["res"], analysis["rule"]
    p = res["p_scam"]
    if rule["raised"]:
        return (
            f"⬆️ Lapisan aturan memaksa ESKALASI: kombinasi "
            f"{' + '.join(rule['active_signals'])} terdeteksi "
            f"({'; '.join(rule['reasons'])}). Skor model {p:.3f} sendiri "
            f"berada di zona {res['zone']} — aturan menaikkannya karena "
            f"pola ini hampir tidak pernah dilakukan pengirim sah."
        )
    calm = rule.get("calm", {})
    if calm.get("lowered"):
        return (
            f"⬇️ Sinyal penenang menurunkan band satu tingkat ke "
            f"REVIEW ANALIS: {'; '.join(calm['reasons'])}. Skor model "
            f"{p:.3f} sendiri melewati ambang eskalasi {t_esc:.3f}, "
            f"tetapi pola pesan ini sangat khas pengirim resmi "
            f"berformat jelas — analis tetap memeriksanya di antrean "
            f"biasa; penenang tidak pernah menutup pesan otomatis."
        )
    if p >= t_esc:
        txt = (f"Skor {p:.3f} melewati ambang eskalasi {t_esc:.3f} → "
               f"pesan diprioritaskan sebagai dugaan scam kuat.")
        if rule["triggered"]:
            txt += (f" Lapisan aturan juga terpicu "
                    f"({'+'.join(rule['active_signals'])}) — sejalan "
                    f"dengan keputusan model.")
        return txt
    if p >= t_close:
        return (f"Skor {p:.3f} berada di antara ambang tutup "
                f"{t_close:.3f} dan ambang eskalasi {t_esc:.3f} → zona "
                f"abu-abu; analis manusia yang memutuskan.")
    return (f"Skor {p:.3f} di bawah ambang tutup {t_close:.3f} → risiko "
            f"sangat rendah; pesan ditutup otomatis (dengan QC sampling "
            f"berkala).")


def result_card_html(analysis, t_close, t_esc):
    res, rule, zone = analysis["res"], analysis["rule"], analysis["final_zone"]
    name, icon, color = ZONE_DISPLAY[zone]
    badge = ""
    if rule["raised"]:
        badge = (
            f'<div class="ft-badge">⬆️ <b>Aturan terpicu:</b> '
            f'{" + ".join(rule["active_signals"])} — '
            f'{"; ".join(rule["reasons"])}. Band dinaikkan oleh lapisan '
            f'aturan; skor model tidak berubah.</div>'
        )
    calm = rule.get("calm", {})
    if calm.get("lowered"):
        badge = (
            f'<div class="ft-badge-calm">⬇️ <b>Sinyal penenang:</b> '
            f'{"; ".join(calm["reasons"])}. Band diturunkan tepat satu '
            f'tingkat oleh sinyal penenang (ESKALASI → REVIEW ANALIS); '
            f'skor model tidak berubah dan pesan tidak ditutup '
            f'otomatis.</div>'
        )
    model_band = ""
    if zone != res["zone"]:
        model_band = (f'<div class="ft-modelband">Band menurut model: '
                      f'{res["zone"]} → Band final: {zone}</div>')
    verdict = verdict_sentence(analysis, t_close, t_esc)
    return f"""
<div class="ft-card" style="border-left: 6px solid {color}">
  <div class="ft-band">{icon} {name}
    <span class="ft-zone-key">— {ZONES[zone]["label_id"]}</span></div>
  <div class="ft-score">{res["p_scam"]:.3f}
    <small>P(scam) terkalibrasi</small></div>
  <div class="ft-desc">{ZONES[zone]["desc_id"]}</div>
  <div class="ft-verdict">{verdict}</div>
  {model_band}{badge}
</div>"""


def signal_panel_md(rule):
    sig = rule["signals"]
    lines = ["#### 🛰️ Panel sinyal teks"]
    for it in sig["items"]:
        mark = "✅" if it["detected"] else "▫️"
        detail = f" — {it['detail']}" if it["detected"] and it["detail"] \
            else ""
        lines.append(f"{mark} {it['label']}{detail}")
    strong = rule["strong"]
    n_strong = sum(1 for v in strong.values() if v)
    s_txt = " · ".join(
        f"{k} {'✅' if v else '▫️'}" for k, v in strong.items())
    lines.append(f"**Sinyal kuat aturan:** {s_txt} → {n_strong}/3 aktif "
                 f"(lapisan aturan memaksa ESKALASI bila ≥ 2 aktif).")
    calm = rule.get("calm", {})
    if calm.get("lowered"):
        lines.append(
            f"⬇️ **Sinyal penenang aktif:** {'; '.join(calm['reasons'])} "
            f"→ band diturunkan satu tingkat ke REVIEW ANALIS "
            f"(tidak pernah AUTO-CLOSE).")
    elif calm.get("applies"):
        lines.append(
            f"⬇️ **Sinyal penenang terdeteksi:** "
            f"{'; '.join(calm['reasons'])} — tetapi band model bukan "
            f"ESKALASI, jadi tidak ada perubahan.")
    else:
        lines.append("⬇️ **Sinyal penenang:** tidak ada (atau gugur "
                     "oleh sinyal kuat S2/S3).")
    return "  \n".join(lines)


# ---------------------------------------------------------------------------
# Kepala halaman
# ---------------------------------------------------------------------------
st.markdown("""
<div class="ft-header">
  <h1>🛡️ Fraud Triage — Konsol Triase Smishing</h1>
  <p>Tempel teks SMS / pesan mencurigakan dan jalankan analisis. Model:
  <b>Ensemble (Top-3 Terkalibrasi)</b> proyek Fraud Triage, kebijakan dua
  ambang <b>t_close = 0,010</b> · <b>t_esc = 0,135</b>, ditambah lapisan
  aturan kombinasi sinyal kuat yang menaikkan band ke ESKALASI dan
  sinyal penenang terbatas yang dapat menurunkan ESKALASI satu tingkat
  ke REVIEW ANALIS untuk pola resmi berformat jelas (tidak pernah
  menutup otomatis).</p>
</div>
""", unsafe_allow_html=True)

try:
    engine = load_engine()
except Exception as exc:  # bobot BERT belum tersedia di lingkungan ini
    st.error(f"Model belum bisa dimuat: {exc}")
    st.info("Secara bawaan app mengunduh seluruh artefak model dari repo "
            "Hugging Face publik rwnliwan/fraud-triage-smishing — "
            "periksa koneksi keluar app, atau set secrets opsional "
            "ARTIFACT_REPO_ID / BERT_MODEL_ID ke repo lain. "
            "Lihat README.md.")
    st.stop()

# ---------------------------------------------------------------------------
# Sidebar: info model
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ℹ️ Info model")
    st.markdown(
        "**Ensemble (Top-3 Terkalibrasi)** — rata-rata probabilitas "
        "terkalibrasi (temperature scaling) dari:\n"
        "1. DistilBERT multilingual (fine-tune)\n"
        "2. TF-IDF + Fitur Angka + Logistic Regression\n"
        "3. TF-IDF + Logistic Regression\n\n"
        f"**Ambang kebijakan:** t_close = {engine.t_close:.3f} · "
        f"t_esc = {engine.t_esc:.3f}\n\n"
        "**PR-AUC test: 0,986** (arena final notebook).\n\n"
        "**Lapisan aturan:** kombinasi ≥ 2 sinyal kuat (tautan; permintaan "
        "kredensial/bertindak lewat tautan; ancaman + urgensi) memaksa "
        "band naik ke ESKALASI. Aturan tidak mengubah skor.\n\n"
        "**Sinyal penenang (v4, Tahap 1):** pola resmi berformat sangat "
        "jelas — format OTP standar tanpa tautan, tautan hanya ke domain "
        "resmi persis, atau notifikasi transaksi terstruktur tanpa "
        "tautan — boleh menurunkan band ESKALASI model **satu tingkat** "
        "ke REVIEW ANALIS. Penenang **tidak pernah** menghasilkan "
        "AUTO-CLOSE dan **gugur total** bila sinyal kuat S2/S3 aktif "
        "atau aturan terpicu. Batasnya jujur: ia hanya menolong pola "
        "berformat jelas; over-eskalasi model pada teks Indonesia bebas "
        "tetap ada sampai model di-fine-tune ulang (Tahap 2)."
    )
    st.markdown("### ⚠️ Keterbatasan (jujur)")
    st.markdown(
        "Data latih adalah **UCI SMS Spam Collection** — SMS Inggris "
        "±2011. Pola smishing Indonesia modern berada **di luar "
        "distribusi** itu (korpus mini ID di notebook menunjukkan drift "
        "besar), jadi perlakukan skor sebagai **perangkingan triase** "
        "untuk antrean manusia, bukan vonis akhir. Skor adalah "
        "probabilitas terkalibrasi — nilainya memang jarang mendekati "
        "0 atau 1. Model ini artefak pembelajaran terpimpin, bukan "
        "sistem produksi bank."
    )
    st.markdown(
        "**Tautan:** [Repo GitHub]"
        "(https://github.com/rwnliwan/fraud-triage) · "
        "[Model Hugging Face]"
        "(https://huggingface.co/rwnliwan/fraud-triage-smishing) · "
        "Detail metode, benchmark semua kandidat & vonis: notebook "
        "proyek `fraud-triage-laya-vs-ml-dl.ipynb`."
    )
    with st.expander("Benchmark arena (test, PR-AUC)"):
        df_b = pd.DataFrame(BENCHMARK, columns=[
            "Model", "PR-AUC", "Recall@FPR1%", "ECE kalibrasi"])
        st.dataframe(df_b, hide_index=True)
    st.caption(f"Bobot DistilBERT dimuat dari: {engine.bert_source}")
    st.caption(f"Versi app: {APP_VERSION} · Mesin: fp32 (uji float16 "
               f"tidak diadopsi — lihat README)")

for _key in ("history", "feedback"):
    if _key not in st.session_state:
        st.session_state[_key] = []

tab_single, tab_batch, tab_eval, tab_journey = st.tabs(
    ["🔎 Analisis Tunggal", "🗂️ Mode Batch", "🇮🇩 Evaluasi ID",
     "🧪 Perjalanan Riset"])

# ---------------------------------------------------------------------------
# Tab 1 — analisis tunggal
# ---------------------------------------------------------------------------
with tab_single:
    st.markdown("**Contoh pesan — klik untuk memakai & langsung analisis**")
    cols = st.columns(3)
    for i, (label, text) in enumerate(SAMPLES.items()):
        if cols[i % 3].button(label, key=f"sample_{i}"):
            st.session_state["sms_text"] = text
            st.session_state["run_now"] = True

    text = st.text_area(
        "Teks pesan", key="sms_text", height=110,
        placeholder="Tempel teks SMS di sini…",
    )

    run = st.button("🔎 Analisis Pesan", type="primary",
                    key="btn_analyze") \
        or st.session_state.pop("run_now", False)

    if run:
        raw = (text or "").strip()
        if not raw:
            st.warning("Isi dulu teks pesannya (atau klik salah satu "
                       "contoh).")
        else:
            effective, was_truncated = raw, False
            if len(raw) > MAX_SINGLE_CHARS:
                effective = raw[:MAX_SINGLE_CHARS]
                was_truncated = True
            with st.spinner("Menghitung skor ensemble…"):
                analysis = analyze_one(engine, effective)
            if was_truncated:
                st.warning(
                    f"Teks sepanjang {len(raw):,} karakter melebihi "
                    f"batas {MAX_SINGLE_CHARS:,} karakter — yang "
                    f"dianalisis hanya {MAX_SINGLE_CHARS:,} karakter "
                    f"pertama.".replace(",", "."))
            st.session_state["last"] = analysis
            st.session_state["show_correction"] = False
            rec = _std_record(analysis)
            rec["Waktu"] = datetime.now().strftime("%H:%M:%S")
            st.session_state["history"].append(rec)

    analysis = st.session_state.get("last")
    if analysis:
        res = analysis["res"]
        col_main, col_sig = st.columns([3, 2])
        with col_main:
            st.markdown(result_card_html(analysis, engine.t_close,
                                         engine.t_esc),
                        unsafe_allow_html=True)
            st.markdown(score_bar_html(res["p_scam"], engine.t_close,
                                       engine.t_esc),
                        unsafe_allow_html=True)
            with st.expander("Skor per anggota ensemble"):
                df_members = pd.DataFrame([
                    {"Anggota": n,
                     "Skor mentah": round(res["member_raw"][n], 3),
                     "Temperatur": res["temperatures"][n],
                     "Skor terkalibrasi":
                         round(res["member_calibrated"][n], 3)}
                    for n in engine.members
                ])
                st.dataframe(df_members, hide_index=True)
                st.caption("Skor akhir = rata-rata skor terkalibrasi "
                           "ketiga anggota (temperatur ensemble 1,0 by "
                           "design).")
        with col_sig:
            st.markdown(signal_panel_md(analysis["rule"]))

        # -- Koreksi pengguna (butir D) -----------------------------------
        st.markdown("#### ✍️ Koreksi penilaian")
        st.caption("Tidak setuju dengan band final di atas? Catat band "
                   "yang benar menurut Anda. Koreksi tersimpan **hanya "
                   "di sesi ini (demo)** — tidak terkirim ke server mana "
                   "pun dan hilang saat sesi berakhir.")
        if st.button("⚠️ Penilaian ini kurang tepat", key="btn_flag"):
            st.session_state["show_correction"] = True
        if st.session_state.get("show_correction"):
            choice = st.radio(
                "Band yang benar menurut Anda",
                options=list(ZONE_DISPLAY.keys()),
                index=list(ZONE_DISPLAY.keys()).index(
                    analysis["final_zone"]),
                format_func=lambda z: f"{ZONE_DISPLAY[z][1]} "
                                      f"{ZONE_DISPLAY[z][0]} ({z})",
                key="correction_choice",
            )
            if st.button("💾 Simpan koreksi", key="btn_save_correction"):
                rec = _std_record(analysis)
                rec["Waktu"] = datetime.now().strftime("%H:%M:%S")
                rec["correction"] = choice
                st.session_state["feedback"].append(rec)
                st.session_state["show_correction"] = False
                st.success("Koreksi tercatat di log koreksi sesi ini "
                           "(lihat bagian 📝 Log koreksi di bawah).")
                st.rerun()

        st.subheader("Mengapa skornya begitu — faktor teks")
        fac = res["factors"]
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Kata/frasa pendorong risiko** (dari anggota "
                        "Logistic Regression)")
            if fac["top_risk_words"]:
                for w, v in fac["top_risk_words"]:
                    st.write(f"- `{w}` (+{v:.2f})")
            else:
                st.write("- (tidak ada kata pendorong risiko yang dikenal)")
        with c2:
            st.markdown("**Kata/frasa penurun risiko**")
            if fac["top_safe_words"]:
                for w, v in fac["top_safe_words"]:
                    st.write(f"- `{w}` ({v:.2f})")
            else:
                st.write("- (tidak ada kata penurun risiko yang dikenal)")

        st.markdown("**Fitur angka pesan ini**")
        num = fac["numeric"]
        df_num = pd.DataFrame([
            {"Fitur": fac["numeric_labels"][k], "Nilai": round(v, 3)}
            for k, v in num.items()
        ])
        st.dataframe(df_num, hide_index=True)
        for note in fac["notes"]:
            st.write(f"⚠️ {note}")

    # Riwayat sesi (hanya pemeriksaan tunggal)
    st.markdown("### 🕘 Riwayat sesi")
    history = st.session_state["history"]
    if history:
        df_hist = pd.DataFrame([{
            "Waktu": r["Waktu"],
            "Pesan": _short(r["text"], 70),
            "Skor": round(r["score"], 3),
            "Band model": r["zone_model"],
            "Band final": r["zone_final"],
            "Aturan": "Ya" if r["rule_triggered"] else "Tidak",
            "Penenang": "Ya" if r.get("calm_applied") else "Tidak",
        } for r in history[::-1]])
        st.dataframe(df_hist, hide_index=True)
        b1, b2 = st.columns(2)
        with b1:
            st.download_button(
                "⬇️ Unduh riwayat (CSV)", key="dl_history",
                data=_export_csv(history),
                file_name="fraud-triage-riwayat.csv", mime="text/csv")
        with b2:
            if st.button("🗑️ Hapus riwayat", key="btn_clear_history"):
                st.session_state["history"] = []
                st.rerun()
    else:
        st.caption("Belum ada pemeriksaan pada sesi ini.")

    # Log koreksi sesi (butir D) — tampil ringkas + unduh CSV (butir A3)
    st.markdown("### 📝 Log koreksi sesi ini")
    feedback = st.session_state["feedback"]
    if feedback:
        df_fb = pd.DataFrame([{
            "Waktu": r["Waktu"],
            "Pesan": _short(r["text"], 60),
            "Skor": round(r["score"], 3),
            "Band final (app)": r["zone_final"],
            "Band koreksi (Anda)": r["correction"],
        } for r in feedback[::-1]])
        st.dataframe(df_fb, hide_index=True)
        st.download_button(
            "⬇️ Unduh log koreksi (CSV)", key="dl_feedback",
            data=_export_csv(
                feedback,
                extra_key=("Band koreksi pengguna", "correction")),
            file_name="fraud-triage-log-koreksi.csv", mime="text/csv")
        st.caption("Log ini hidup hanya di sesi browser ini (demo "
                   "loop umpan balik) — belum ada penyimpanan permanen.")
    else:
        st.caption("Belum ada koreksi pada sesi ini.")

# ---------------------------------------------------------------------------
# Tab 2 — mode batch
# ---------------------------------------------------------------------------
with tab_batch:
    st.markdown("Tempel banyak pesan sekaligus — **satu pesan per "
                "baris**. Setiap baris dinilai model + lapisan aturan. "
                f"Batas: **{MAX_BATCH_LINES} pesan** per batch; baris "
                "kosong dilewati.")
    batch_text = st.text_area(
        "Pesan-pesan (satu per baris)", key="batch_text", height=180,
        placeholder="Pesan pertama…\nPesan kedua…\nPesan ketiga…",
    )
    if st.button("🗂️ Analisis Batch", type="primary", key="btn_batch"):
        lines = [ln.strip() for ln in (batch_text or "").splitlines()
                 if ln.strip()]
        if not lines:
            st.warning("Isi dulu minimal satu baris pesan.")
        elif len(lines) > MAX_BATCH_LINES:
            st.error(
                f"Terlalu banyak pesan: {len(lines)} baris non-kosong "
                f"(batas {MAX_BATCH_LINES}). Kurangi jumlah baris lalu "
                f"jalankan lagi — tidak ada yang diproses.")
        else:
            st.info(f"Memproses {len(lines)} pesan…")
            bar = st.progress(0, text="Menilai 0 dari "
                                      f"{len(lines)} pesan…")
            rows = []
            for i, ln in enumerate(lines):
                a = analyze_one(engine, ln)
                rows.append(_std_record(a))
                bar.progress((i + 1) / len(lines),
                             text=f"Menilai {i + 1} dari {len(lines)} "
                                  f"pesan…")
            bar.empty()
            st.session_state["batch_rows"] = rows

    rows = st.session_state.get("batch_rows")
    if rows:
        counts = {"AUTO-CLOSE": 0, "REVIEW ANALIS": 0, "ESKALASI": 0}
        for r in rows:
            counts[r["zone_final"]] += 1
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("🟢 AMAN", counts["AUTO-CLOSE"])
        m2.metric("🟡 REVIEW ANALIS", counts["REVIEW ANALIS"])
        m3.metric("🔴 ESKALASI", counts["ESKALASI"])
        m4.metric("⬆️ Kena aturan",
                  sum(1 for r in rows if r["rule_triggered"]))
        m5.metric("⬇️ Kena penenang",
                  sum(1 for r in rows if r.get("calm_applied")))
        df_rows = pd.DataFrame([{
            "Pesan": _short(r["text"], 60),
            "Skor": round(r["score"], 3),
            "Band model": r["zone_model"],
            "Band final": r["zone_final"],
            "Aturan terpicu": ("Ya — " + "+".join(r["signals"]))
            if r["rule_triggered"] else "Tidak",
            "Penenang": ("Ya — " + "; ".join(r["calm_reasons"]))
            if r.get("calm_applied") else "Tidak",
        } for r in rows])
        st.dataframe(df_rows, hide_index=True)
        st.download_button(
            "⬇️ Unduh hasil batch (CSV)", key="dl_batch",
            data=_export_csv(rows),
            file_name="fraud-triage-batch.csv", mime="text/csv")

# ---------------------------------------------------------------------------
# Tab 3 — panel evaluasi Indonesia (butir E)
# ---------------------------------------------------------------------------
with tab_eval:
    st.markdown("### 🇮🇩 Panel evaluasi pesan Indonesia")
    st.warning(
        "⚠️ **Set uji kecil BUATAN (16 pesan) untuk transparansi — "
        "BUKAN benchmark.** Pesan-pesan ini ditulis tangan meniru gaya "
        "umum pesan sah & smishing Indonesia (nama bank fiktif), lalu "
        "dijalankan apa adanya ke model + lapisan aturan. Hasil "
        "ditampilkan **apa adanya, termasuk yang gagal** — jangan "
        "dibaca sebagai angka performa model di dunia nyata.")
    st.markdown(
        "**Definisi \"sesuai\" di panel ini (sederhana & jujur):** "
        "pesan **SAH** dihitung sesuai bila band finalnya **AUTO-CLOSE "
        "atau REVIEW ANALIS** (tidak sampai eskalasi); pesan "
        "**SMISHING** dihitung sesuai bila band finalnya **ESKALASI**. "
        "Ingat konteksnya: data latih model adalah SMS Inggris ±2011, "
        "jadi panel ini memang mengekspos seberapa jauh pesan Indonesia "
        "berada di luar distribusi itu.")
    if st.button("▶️ Jalankan evaluasi", type="primary", key="btn_eval"):
        bar = st.progress(0, text="Mengevaluasi 0 dari "
                                  f"{len(ID_EVAL_SET)} pesan…")
        eval_rows = []
        for i, item in enumerate(ID_EVAL_SET):
            a = analyze_one(engine, item["text"])
            final = a["final_zone"]
            if item["label"] == "SAH":
                ok = final in ("AUTO-CLOSE", "REVIEW ANALIS")
            else:
                ok = final == "ESKALASI"
            eval_rows.append({
                "Pesan": item["text"],
                "Kategori": item["kategori"],
                "Label harapan": item["label"],
                "Skor": round(a["res"]["p_scam"], 3),
                "Band model": a["res"]["zone"],
                "Band final": final,
                "Aturan": ("Ya — " + "+".join(
                    a["rule"]["active_signals"]))
                if a["rule"]["triggered"] else "Tidak",
                "Penenang": ("Ya ⬇️ — " + "; ".join(
                    a["rule"]["calm"]["reasons"]))
                if a["rule"].get("calm", {}).get("lowered") else "Tidak",
                "Sesuai": ok,
                "Status": "✅ Sesuai" if ok else "❌ Tidak sesuai",
            })
            bar.progress((i + 1) / len(ID_EVAL_SET),
                         text=f"Mengevaluasi {i + 1} dari "
                              f"{len(ID_EVAL_SET)} pesan…")
        bar.empty()
        st.session_state["id_eval_rows"] = eval_rows

    eval_rows = st.session_state.get("id_eval_rows")
    if eval_rows:
        sah = [r for r in eval_rows if r["Label harapan"] == "SAH"]
        smi = [r for r in eval_rows if r["Label harapan"] == "SMISHING"]
        sah_ok = sum(1 for r in sah if r["Sesuai"])
        smi_ok = sum(1 for r in smi if r["Sesuai"])
        tot_ok = sah_ok + smi_ok
        e1, e2, e3 = st.columns(3)
        e1.metric("Pesan SAH sesuai", f"{sah_ok}/{len(sah)}")
        e2.metric("SMISHING sesuai", f"{smi_ok}/{len(smi)}")
        e3.metric("Total sesuai", f"{tot_ok}/{len(eval_rows)}")
        df_eval = pd.DataFrame([{
            "Pesan": _short(r["Pesan"], 70),
            "Kategori": r["Kategori"],
            "Label harapan": r["Label harapan"],
            "Skor": r["Skor"],
            "Band model": r["Band model"],
            "Band final": r["Band final"],
            "Aturan": r["Aturan"],
            "Penenang": r["Penenang"],
            "Status": r["Status"],
        } for r in eval_rows])
        st.dataframe(df_eval, hide_index=True)
        concl = [
            f"**Kesimpulan otomatis (dari angka di atas, apa "
            f"adanya):** {tot_ok} dari {len(eval_rows)} band final "
            f"sesuai harapan — {sah_ok}/{len(sah)} pesan sah dan "
            f"{smi_ok}/{len(smi)} smishing."
        ]
        if sah_ok < len(sah):
            concl.append(
                f"Model + aturan masih mengeskalasi "
                f"{len(sah) - sah_ok} pesan sah pada set kecil ini — "
                f"konsisten dengan keterbatasan data latih Inggris "
                f"±2011; skor untuk pesan Indonesia adalah perangkingan "
                f"triase, bukan vonis.")
        if smi_ok < len(smi):
            concl.append(
                f"{len(smi) - smi_ok} smishing tidak mencapai "
                f"ESKALASI pada set kecil ini — lihat kolom skor & "
                f"band modelnya: pola yang tidak memuat kombinasi "
                f"sinyal kuat aturan hanya bergantung pada skor model.")
        if sah_ok == len(sah) and smi_ok == len(smi):
            concl.append(
                "Semua sesuai **pada set buatan kecil ini saja** — "
                "bukan bukti performa dunia nyata.")
        st.markdown("  \n".join(concl))

# ---------------------------------------------------------------------------
# Tab 4 — perjalanan riset (v5): dokumentasi semua tahap percobaan,
# termasuk yang ditolak; model live tidak berubah.
# ---------------------------------------------------------------------------
with tab_journey:
    render_journey()

# ---------------------------------------------------------------------------
# Footer (butir G)
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown(
    f'<div class="ft-footer">🛡️ <b>Fraud Triage</b> — app {APP_VERSION} '
    f'· berjalan di Streamlit Community Cloud · '
    f'<a href="https://github.com/rwnliwan/fraud-triage">Repo GitHub</a>'
    f' · <a href="https://huggingface.co/rwnliwan/fraud-triage-smishing">'
    f'Model Hugging Face</a> · Metode & vonis lengkap: notebook proyek '
    f'`fraud-triage-laya-vs-ml-dl.ipynb`</div>',
    unsafe_allow_html=True)
