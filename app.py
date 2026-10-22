# -*- coding: utf-8 -*-
"""Fraud Triage — aplikasi triase smishing (Streamlit).

Menjalankan model CHOSEN proyek Fraud Triage: Ensemble (Top-3 Terkalibrasi)
dengan kebijakan dua ambang t_close=0,010 / t_esc=0,135 (Bagian 10 notebook).
Logika model ada di triage_core.py agar bisa diuji tanpa Streamlit.

Jalankan lokal:  streamlit run app.py
Deploy: lihat README.md (Streamlit Community Cloud).
"""

import os

import pandas as pd
import streamlit as st

from triage_core import TriageEngine, ZONES

st.set_page_config(page_title="Fraud Triage — Triase Smishing",
                   page_icon="🛡️", layout="centered")

# ---------------------------------------------------------------------------
# Contoh pesan siap-klik (probe resmi notebook Bagian 13.5 + korpus mini ID)
# ---------------------------------------------------------------------------
SAMPLES = {
    "💬 Pesan sah (EN)":
        "Hi, running 10 mins late — start the meeting without me",
    "🔢 Pesan berkode OTP":
        "Kode OTP Anda 481920. JANGAN bagikan ke siapa pun.",
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


@st.cache_resource(show_spinner="Memuat ensemble (termasuk DistilBERT)…")
def load_engine():
    bert_source = None
    try:
        bert_source = st.secrets.get("BERT_MODEL_PATH") or st.secrets.get(
            "BERT_MODEL_ID")
    except Exception:
        bert_source = None
    bert_source = bert_source or os.environ.get("BERT_MODEL_PATH") \
        or os.environ.get("BERT_MODEL_ID")
    return TriageEngine(bert_source=bert_source)


st.title("🛡️ Fraud Triage — Triase Smishing")
st.markdown(
    "Tempel teks SMS / pesan mencurigakan, lalu jalankan analisis. "
    "Model yang dipakai adalah **Ensemble (Top-3 Terkalibrasi)** — model "
    "terpilih proyek Fraud Triage — dan keputusannya mengikuti kebijakan "
    "dua ambang operasional: **t_close = 0,010** dan **t_esc = 0,135**."
)

try:
    engine = load_engine()
except Exception as exc:  # bobot BERT belum tersedia di lingkungan ini
    st.error(f"Model belum bisa dimuat: {exc}")
    st.info("Untuk deploy: ikuti langkah penempatan bobot DistilBERT "
            "di README.md (folder model/bert/ via Git LFS, atau repo "
            "Hugging Face + secrets BERT_MODEL_ID).")
    st.stop()

st.subheader("Contoh pesan — klik untuk memakai")
cols = st.columns(2)
for i, (label, text) in enumerate(SAMPLES.items()):
    if cols[i % 2].button(label):
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
        st.warning("Isi dulu teks pesannya (atau klik salah satu contoh).")
    else:
        with st.spinner("Menghitung skor ensemble…"):
            res = engine.triage(text.strip())

        p = res["p_scam"]
        st.metric("P(scam) terkalibrasi", f"{p:.3f}")
        st.progress(min(max(p, 0.0), 1.0))

        zone = res["zone"]
        banner = {"AUTO-CLOSE": st.success, "REVIEW ANALIS": st.warning,
                  "ESKALASI": st.error}[zone]
        banner(f"**Keputusan: {res['zone_label']}**  \n"
               f"{res['zone_desc']}  \n"
               f"Posisi skor: t_close = {engine.t_close:.3f} · "
               f"t_esc = {engine.t_esc:.3f}")

        st.subheader("Skor per anggota ensemble")
        df_members = pd.DataFrame([
            {"Anggota": n,
             "Skor mentah": round(res["member_raw"][n], 3),
             "Temperatur": res["temperatures"][n],
             "Skor terkalibrasi": round(res["member_calibrated"][n], 3)}
            for n in engine.members
        ])
        st.dataframe(df_members, hide_index=True)
        st.caption("Skor akhir = rata-rata skor terkalibrasi ketiga anggota "
                   "(temperatur ensemble 1,0 by design).")

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

with st.expander("ℹ️ Tentang model & kebijakan"):
    st.markdown(
        "**Model:** Ensemble (Top-3 Terkalibrasi) — rata-rata probabilitas "
        "terkalibrasi (temperature scaling) dari DistilBERT multilingual "
        "fine-tune, TF-IDF + Fitur Angka + Logistic Regression, dan "
        "TF-IDF + Logistic Regression.\n\n"
        "**Data latih:** UCI SMS Spam Collection, duplikat dibuang, split "
        "stratified 60/20/20 (seed 42). Temperatur & ambang dipilih di "
        "validation; test disentuh sekali di arena final.\n\n"
        "**Kebijakan (Bagian 10 notebook):** skor < 0,010 ditutup otomatis; "
        "0,010–0,135 masuk antrean analis; ≥ 0,135 dieskalasi. Di simulasi "
        "10.000 pesan/hari kebijakan ini menghasilkan 0 fraud lolos dan "
        "±2.466 antrean analis.\n\n"
        "**Hasil benchmark (test set, PR-AUC):**"
    )
    df_b = pd.DataFrame(BENCHMARK, columns=[
        "Model", "PR-AUC", "Recall@FPR1%", "ECE kalibrasi"])
    st.dataframe(df_b, hide_index=True)
    st.markdown(
        "**Batasan jujur:** data latih adalah SMS Inggris ±2011 — pola "
        "smishing Indonesia modern terwakili terbatas (korpus mini ID di "
        "notebook menunjukkan drift besar). Model ini artefak pembelajaran "
        "terpimpin, bukan sistem produksi bank. Laya (agen RL) dinilai di "
        "notebook sebagai kandidat lapisan teks, bukan model operasional, "
        "jadi tidak ikut disajikan di sini."
    )
    st.caption(f"Bobot DistilBERT dimuat dari: {engine.bert_source}")
