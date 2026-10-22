# -*- coding: utf-8 -*-
"""Fraud Triage — konsol triase smishing (Streamlit).

Menjalankan model CHOSEN proyek Fraud Triage: Ensemble (Top-3 Terkalibrasi)
dengan kebijakan dua ambang t_close=0,010 / t_esc=0,135 (Bagian 10 notebook),
dilengkapi LAPISAN ATURAN (rules.py): kombinasi >= 2 sinyal kuat memaksa
band naik ke ESKALASI — aturan tidak pernah mengubah skor dan tidak pernah
menurunkan band. Logika model ada di triage_core.py, logika aturan di
rules.py; keduanya bisa diuji tanpa Streamlit.

Jalankan lokal:  streamlit run app.py
Deploy: lihat README.md (Streamlit Community Cloud).
"""

import os
from datetime import datetime

import pandas as pd
import streamlit as st

from triage_core import TriageEngine, ZONES
from rules import apply_rules

st.set_page_config(page_title="Fraud Triage — Konsol Triase Smishing",
                   page_icon="🛡️", layout="wide")

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
.ft-badge {
  display: inline-block; margin-top: 0.6rem; padding: 0.45rem 0.7rem;
  border-radius: 8px; background: #3a1420; border: 1px solid #ef4444;
  color: #fecaca; font-size: 0.92rem;
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
    return TriageEngine(bert_source=bert_source,
                        artifact_repo_id=artifact_repo_id)


def analyze_one(engine, text):
    """Satu pemeriksaan lengkap: skor model + lapisan aturan."""
    res = engine.triage(text)
    final_zone, rule = apply_rules(text, res["zone"])
    return {"text": text, "res": res, "rule": rule, "final_zone": final_zone}


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


def result_card_html(analysis):
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
    model_band = ""
    if zone != res["zone"]:
        model_band = (f'<div class="ft-modelband">Band menurut model: '
                      f'{res["zone"]} → Band final: {zone}</div>')
    return f"""
<div class="ft-card" style="border-left: 6px solid {color}">
  <div class="ft-band">{icon} {name}
    <span class="ft-zone-key">— {ZONES[zone]["label_id"]}</span></div>
  <div class="ft-score">{res["p_scam"]:.3f}
    <small>P(scam) terkalibrasi</small></div>
  <div class="ft-desc">{ZONES[zone]["desc_id"]}</div>
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
  aturan kombinasi sinyal kuat yang hanya bisa menaikkan band ke
  ESKALASI.</p>
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
        "band naik ke ESKALASI. Aturan tidak mengubah skor dan tidak "
        "pernah menurunkan band."
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

if "history" not in st.session_state:
    st.session_state["history"] = []

tab_single, tab_batch = st.tabs(["🔎 Analisis Tunggal", "🗂️ Mode Batch"])

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

    run = st.button("🔎 Analisis Pesan", type="primary") \
        or st.session_state.pop("run_now", False)

    if run:
        if not text or not text.strip():
            st.warning("Isi dulu teks pesannya (atau klik salah satu "
                       "contoh).")
        else:
            with st.spinner("Menghitung skor ensemble…"):
                analysis = analyze_one(engine, text.strip())
            st.session_state["last"] = analysis
            st.session_state["history"].append({
                "Waktu": datetime.now().strftime("%H:%M:%S"),
                "Pesan": analysis["text"],
                "Skor": round(analysis["res"]["p_scam"], 3),
                "Band model": analysis["res"]["zone"],
                "Band final": analysis["final_zone"],
                "Aturan": "Ya" if analysis["rule"]["triggered"] else "Tidak",
            })

    analysis = st.session_state.get("last")
    if analysis:
        res = analysis["res"]
        col_main, col_sig = st.columns([3, 2])
        with col_main:
            st.markdown(result_card_html(analysis),
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
        df_hist = pd.DataFrame(history[::-1])
        df_hist["Pesan"] = df_hist["Pesan"].str.slice(0, 70) + "…"
        st.dataframe(df_hist, hide_index=True)
        if st.button("🗑️ Hapus riwayat"):
            st.session_state["history"] = []
            st.rerun()
    else:
        st.caption("Belum ada pemeriksaan pada sesi ini.")

# ---------------------------------------------------------------------------
# Tab 2 — mode batch
# ---------------------------------------------------------------------------
with tab_batch:
    st.markdown("Tempel banyak pesan sekaligus — **satu pesan per "
                "baris**. Setiap baris dinilai model + lapisan aturan.")
    batch_text = st.text_area(
        "Pesan-pesan (satu per baris)", key="batch_text", height=180,
        placeholder="Pesan pertama…\nPesan kedua…\nPesan ketiga…",
    )
    if st.button("🗂️ Analisis Batch", type="primary"):
        lines = [ln.strip() for ln in (batch_text or "").splitlines()
                 if ln.strip()]
        if not lines:
            st.warning("Isi dulu minimal satu baris pesan.")
        else:
            rows = []
            with st.spinner(f"Menilai {len(lines)} pesan…"):
                for ln in lines:
                    a = analyze_one(engine, ln)
                    sig = a["rule"]["active_signals"]
                    rows.append({
                        "Pesan": ln[:60] + ("…" if len(ln) > 60 else ""),
                        "Skor": round(a["res"]["p_scam"], 3),
                        "Band model": a["res"]["zone"],
                        "Band final": a["final_zone"],
                        "Aturan terpicu": ("Ya — " + "+".join(sig))
                        if a["rule"]["triggered"] else "Tidak",
                    })
            st.session_state["batch_rows"] = rows

    rows = st.session_state.get("batch_rows")
    if rows:
        counts = {"AUTO-CLOSE": 0, "REVIEW ANALIS": 0, "ESKALASI": 0}
        for r in rows:
            counts[r["Band final"]] += 1
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🟢 AMAN", counts["AUTO-CLOSE"])
        m2.metric("🟡 REVIEW ANALIS", counts["REVIEW ANALIS"])
        m3.metric("🔴 ESKALASI", counts["ESKALASI"])
        m4.metric("⬆️ Kena aturan", sum(
            1 for r in rows if r["Aturan terpicu"] != "Tidak"))
        st.dataframe(pd.DataFrame(rows), hide_index=True)
