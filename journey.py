# -*- coding: utf-8 -*-
"""Tab "🧪 Perjalanan Riset" (app v5) — dokumentasi jujur semua tahap.

Halaman ini menampilkan SETIAP percobaan proyek Fraud Triage, termasuk
yang DITOLAK, dengan angka persis dari file evaluasi terverifikasi.
Angka dibaca dari `results.json` (dibangkitkan oleh gen_results.py dari
../id-train/eval_*.json + tabel perbandingan laporan tahap).

Model triase yang live TIDAK berubah oleh halaman ini: tetap ensemble
CHOSEN + rules Tahap 1. Modul ini hanya memakai streamlit + pandas +
json (tanpa dependensi baru) dan bisa diuji tanpa app.py.
"""

import json
import os

import pandas as pd
import streamlit as st

_HERE = os.path.dirname(os.path.abspath(__file__))

_WARNA = {
    "hijau": "#22c55e",
    "kuning": "#eab308",
    "merah": "#ef4444",
    "netral": "#8fa1c0",
}


def _fmt_pct(v):
    """Format persen gaya Indonesia: 92.7 -> '92,7%'."""
    return f"{v:.1f}".replace(".", ",") + "%"


def _fmt_auc(v):
    """Format PR-AUC gaya Indonesia: 0.9882 -> '0,9882'."""
    return f"{v:.4f}".replace(".", ",")


def _load_results():
    with open(os.path.join(_HERE, "results.json"), encoding="utf-8") as f:
        return json.load(f)


def _gerbang_lines(stage, gates):
    """Baris vonis per gerbang (✅/❌) dihitung dari data vs ambang."""
    cek = [
        ("SAH (set 300)", stage["sah"] >= gates["sah"],
         f"{_fmt_pct(stage['sah'])} — gerbang ≥ {_fmt_pct(gates['sah'])}"),
        ("SMISHING dieskalasi (set 300)", stage["smishing"] >= gates["smishing"],
         f"{_fmt_pct(stage['smishing'])} — gerbang ≥ "
         f"{_fmt_pct(gates['smishing'])}"),
        ("PR-AUC Inggris (UCI test)", stage["uci_pr_auc"] >= gates["uci_pr_auc"],
         f"{_fmt_auc(stage['uci_pr_auc'])} — gerbang ≥ "
         f"{_fmt_auc(gates['uci_pr_auc'])}"),
        ("Smishing AUTO-CLOSE", stage["auto_close"] == gates["auto_close"],
         f"{stage['auto_close']} — gerbang = {gates['auto_close']}"),
    ]
    lines = []
    for nama, ok, nilai in cek:
        lines.append(f"- {'✅' if ok else '❌'} **{nama}:** {nilai}")
    lines.append(
        f"- ℹ️ Total lolos set 300: {_fmt_pct(stage['total'])} · "
        f"Panel 16: sah {_fmt_pct(stage['panel_sah'])}, "
        f"smishing {_fmt_pct(stage['panel_smishing'])} (bukan gerbang)")
    return lines


def _flow_html(stages):
    """Diagram alur tahapan: kotak bergaya .ft-card + panah, aksen vonis."""
    boxes = []
    for s in stages:
        warna = _WARNA.get(s["warna_vonis"], "#8fa1c0")
        boxes.append(
            '<div style="flex:1 1 0; min-width:150px; padding:0.9rem 1rem; '
            'border-radius:12px; background:#111a2e; '
            f'border:1px solid #2a3a5f; border-top:4px solid {warna};">'
            f'<div style="color:#8fa1c0; font-size:0.8rem;">'
            f'TAHAP {s["id"].upper()} · {s["tanggal"]}</div>'
            f'<div style="color:#f2f5fb; font-weight:700; margin:0.25rem 0;">'
            f'{s["nama"]}</div>'
            f'<div style="color:{warna}; font-size:0.85rem; font-weight:600;">'
            f'{s["vonis"]}</div>'
            f'<div style="color:#c6d0e4; font-size:0.85rem; '
            f'margin-top:0.4rem;">SAH {_fmt_pct(s["sah"])} · '
            f'SMISHING {_fmt_pct(s["smishing"])}</div></div>')
    panah = ('<div style="align-self:center; color:#8fa1c0; '
             'font-size:1.3rem; padding:0 0.3rem;">➜</div>')
    return ('<div style="display:flex; flex-wrap:wrap; align-items:stretch; '
            'gap:0.2rem;">' + panah.join(boxes) + "</div>")


def render_journey():
    data = _load_results()
    gates = data["gates"]
    stages = data["stages"]

    st.markdown("### 🧪 Perjalanan Riset — semua tahap, termasuk yang ditolak")
    st.markdown(
        "Halaman ini mendokumentasikan **setiap percobaan** proyek Fraud "
        "Triage secara apa adanya — bukan hanya yang berhasil. Dua paket "
        "model yang diuji di sini **ditolak** dan **tidak pernah "
        "menggantikan** model live.\n\n"
        "**Model triase yang berjalan tetap sama:** ensemble CHOSEN + "
        "lapisan aturan Tahap 1 (sinyal penenang).\n\n"
        "**Gerbang klaim ditetapkan di muka** dan tidak pernah digeser "
        "sesudah hasil terlihat, diukur pada **set hakim 300 pesan "
        "Indonesia** (150 SAH / 150 SMISHING) yang tidak pernah dipakai "
        "melatih model mana pun:\n"
        f"- SAH lolos ≥ {_fmt_pct(gates['sah'])}\n"
        f"- SMISHING dieskalasi ≥ {_fmt_pct(gates['smishing'])}\n"
        f"- PR-AUC Inggris (UCI test) ≥ {_fmt_auc(gates['uci_pr_auc'])}\n"
        f"- Smishing AUTO-CLOSE = {gates['auto_close']}")

    st.markdown("#### Alur tahapan")
    st.markdown(_flow_html(stages), unsafe_allow_html=True)

    st.markdown("#### Skor gerbang per tahap (set hakim 300, full-stack)")
    df = pd.DataFrame(
        {
            "SAH (%)": [s["sah"] for s in stages],
            "SMISHING (%)": [s["smishing"] for s in stages],
        },
        index=[f"Tahap {s['id']}" for s in stages],
    )
    st.bar_chart(df)
    st.caption(
        f"Gerbang: SAH ≥ {_fmt_pct(gates['sah'])} · SMISHING ≥ "
        f"{_fmt_pct(gates['smishing'])} · PR-AUC ≥ "
        f"{_fmt_auc(gates['uci_pr_auc'])} · smishing AUTO-CLOSE = "
        f"{gates['auto_close']}.")

    st.markdown("#### PR-AUC Inggris (UCI test) per tahap")
    cols = st.columns(len(stages))
    for col, s in zip(cols, stages):
        col.metric(f"Tahap {s['id']}", _fmt_auc(s["uci_pr_auc"]),
                   help=f"Gerbang ≥ {_fmt_auc(gates['uci_pr_auc'])}")

    st.markdown("#### Detail per tahap")
    for s in stages:
        warna = _WARNA.get(s["warna_vonis"], "#8fa1c0")
        with st.expander(
                f"Tahap {s['id']} — {s['nama']} · {s['tanggal']}"):
            st.markdown(
                f'<div style="border-left:4px solid {warna}; '
                f'padding-left:0.8rem; margin-bottom:0.6rem;">'
                f'<b>Vonis: {s["vonis"]}</b></div>',
                unsafe_allow_html=True)
            st.markdown("\n".join(_gerbang_lines(s, gates)))
            st.markdown(f"**Hipotesis.** {s['hipotesis']}")
            st.markdown(f"**Metode.** {s['metode']}")
            st.markdown(f"**Hasil.** {s['hasil']}")
            st.markdown(f"**Pelajaran.** {s['pelajaran']}")

    st.caption(
        "Metode & angka lengkap: notebook proyek "
        "`fraud-triage-laya-vs-ml-dl.ipynb` dan laporan tahap di "
        "repo proyek (tahap2c_results.md · tahap2d_results.md · "
        "README_TAHAP2D.md). Sumber angka halaman ini: file evaluasi "
        "terverifikasi (eval_smoke_current.json · eval_tahap2c.json · "
        "eval_tahap2d.json) yang diringkas ke results.json oleh "
        "gen_results.py — tidak ada angka yang diketik tangan di "
        "halaman ini.")
