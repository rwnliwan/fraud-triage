# -*- coding: utf-8 -*-
"""Tab "🧪 Perjalanan Riset" (app v5) — dokumentasi jujur semua tahap.

Halaman ini menampilkan SETIAP percobaan proyek Fraud Triage, termasuk
yang DITOLAK, dengan angka persis dari file evaluasi terverifikasi.
Angka dibaca dari `results.json` (dibangkitkan oleh gen_results.py dari
../id-train/eval_*.json + tabel perbandingan laporan tahap).

Model triase yang live TIDAK berubah oleh halaman ini: tetap ensemble
CHOSEN + rules Tahap 1. Modul ini memakai streamlit + json, dan
pandas + altair hanya untuk heatmap kategori (keduanya sudah jadi
dependensi app — tanpa dependensi baru) dan bisa diuji tanpa app.py.

v5.1: kotak alur memakai vonis singkat + CSS responsif (layar sempit =
kotak menumpuk vertikal penuh), diagram skor diganti bar horizontal
HTML per ukuran (bar chart dua seri lama menumpuk SAH+SMISHING >100%),
metrik PR-AUC memakai container horizontal (anjuran docs Streamlit:
lebih adaptif daripada columns), dan ada heatmap Altair per kategori
Tahap 2C vs 2D dari `kategori_heatmap` di results.json.
"""

import json
import os

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


# Vonis SINGKAT khusus kotak alur — vonis lengkap (panjang) hanya tampil
# di bagian Detail per tahap, supaya kotak tidak sesak teks bertumpuk.
_VONIS_SINGKAT = {
    "0": "BASELINE",
    "1": "DITERIMA — app v4",
    "2c": "DITOLAK — gagal tipis",
    "2d": "DITOLAK — 2/4 gerbang",
}

_CSS = """
<style>
.jr-flow {display:flex; flex-wrap:wrap; align-items:stretch; gap:0.4rem;}
.jr-box {flex:1 1 170px; min-width:0; padding:0.85rem 0.95rem;
  border-radius:12px; background:#111a2e; border:1px solid #2a3a5f;
  overflow-wrap:break-word;}
.jr-arrow {align-self:center; color:#8fa1c0; font-size:1.25rem;
  padding:0 0.15rem;}
.jr-bar-row {display:flex; align-items:center; gap:0.6rem;
  margin:0.3rem 0;}
.jr-bar-label {flex:0 0 11.5rem; color:#c6d0e4; font-size:0.85rem;
  overflow-wrap:break-word;}
.jr-bar-track {flex:1 1 auto; height:0.95rem; border-radius:6px;
  background:#1a2742; overflow:hidden;}
.jr-bar-fill {height:100%; border-radius:6px;}
.jr-bar-val {flex:0 0 3.6rem; color:#f2f5fb; font-size:0.85rem;
  font-weight:600;}
@media (max-width: 700px) {
  .jr-box {flex:1 1 100%;}
  .jr-arrow {flex:1 1 100%; text-align:center; transform:rotate(90deg);
    padding:0.1rem 0;}
  .jr-bar-label {flex-basis:7.5rem; font-size:0.8rem;}
}
</style>
"""


def _flow_html(stages):
    """Diagram alur tahapan: kotak vonis singkat + panah, aksen vonis."""
    boxes = []
    for s in stages:
        warna = _WARNA.get(s["warna_vonis"], "#8fa1c0")
        singkat = _VONIS_SINGKAT.get(s["id"], s["vonis"])
        boxes.append(
            f'<div class="jr-box" style="border-top:4px solid {warna};">'
            f'<div style="color:#8fa1c0; font-size:0.78rem;">'
            f'TAHAP {s["id"].upper()} · {s["tanggal"]}</div>'
            f'<div style="color:#f2f5fb; font-weight:700; '
            f'margin:0.25rem 0;">{s["nama"]}</div>'
            f'<div style="color:{warna}; font-size:0.88rem; '
            f'font-weight:700;">{singkat}</div>'
            f'<div style="color:#c6d0e4; font-size:0.85rem; '
            f'margin-top:0.4rem;">SAH {_fmt_pct(s["sah"])} · '
            f'SMISHING {_fmt_pct(s["smishing"])}</div></div>')
    panah = '<div class="jr-arrow">➜</div>'
    return '<div class="jr-flow">' + panah.join(boxes) + "</div>"


def _heatmap_chart(rows, grup=None):
    """Heatmap Altair: % lolos per kategori, Tahap 2C vs 2D.

    grup=None -> satu chart semua kategori. grup="SAH"/"SMISHING" ->
    chart khusus grup itu (dipakai pemanggil untuk dua chart terpisah).
    Mengembalikan chart Altair, atau None bila altair tak tersedia /
    data kosong — pemanggil menampilkan tabel sebagai cadangan.
    """
    if not rows:
        return None
    try:
        import altair as alt
        import pandas as pd
    except Exception:
        return None
    # Altair 6 menolak list-of-dicts mentah sebagai `data` (harus
    # DataFrame / Mapping) — bungkus jadi DataFrame lebih dulu.
    data = pd.DataFrame([dict(r, teks=_fmt_pct(r["lolos"])) for r in rows])
    if grup is not None and "grup" in data.columns:
        data = data[data["grup"] == grup]
        if data.empty:
            return None
    label_order = list(dict.fromkeys(data["label"]))
    base = alt.Chart(data).encode(
        x=alt.X("tahap:N", title=None,
                axis=alt.Axis(labelAngle=0, labelFontSize=12)),
        y=alt.Y("label:N", title=None, sort=label_order,
                axis=alt.Axis(labelFontSize=11, labelLimit=220)),
        tooltip=[alt.Tooltip("kategori:N", title="Kategori"),
                 alt.Tooltip("tahap:N", title="Tahap"),
                 alt.Tooltip("teks:N", title="Lolos")],
    )
    rect = base.mark_rect(cornerRadius=3).encode(
        color=alt.Color(
            "lolos:Q",
            scale=alt.Scale(domain=[50, 75, 100],
                            range=["#ef4444", "#eab308", "#22c55e"]),
            legend=alt.Legend(title="% lolos")))
    text = base.mark_text(fontWeight="bold", fontSize=11).encode(
        text="teks:N",
        color=alt.condition(alt.datum.lolos >= 65,
                            alt.value("#0b1220"), alt.value("#f8fafc")))
    layered = rect + text
    # v5.3.1: facet Altair ternyata menyusutkan lebar chart di layar
    # sempit (sel terdesak, teks persen bertumpuk — terlihat di HP).
    # Grup kini dirender sebagai DUA CHART TERPISAH oleh pemanggil;
    # tiap chart tunggal melebar penuh seperti v5.1 yang terbukti.
    return layered.properties(height=300 if grup else 560)


def _bars_html(stages, gates):
    """Bar horizontal per tahap — SAH & SMISHING terpisah (tidak ditumpuk).

    Bar lama (st.bar_chart dua seri) menumpuk kedua persen sampai >100%
    dan sulit dibaca; di sini tiap ukuran punya bar sendiri, hijau bila
    melewati gerbangnya, merah bila belum.
    """
    rows = []
    for s in stages:
        for kunci, label, gerbang in (
                ("sah", "SAH", gates["sah"]),
                ("smishing", "SMISHING", gates["smishing"])):
            v = s[kunci]
            warna = "#22c55e" if v >= gerbang else "#ef4444"
            rows.append(
                '<div class="jr-bar-row">'
                f'<div class="jr-bar-label">Tahap {s["id"]} · {label}</div>'
                f'<div class="jr-bar-track"><div class="jr-bar-fill" '
                f'style="width:{v:.1f}%; background:{warna};"></div></div>'
                f'<div class="jr-bar-val">{_fmt_pct(v)}</div></div>')
    return "".join(rows)


def render_journey():
    data = _load_results()
    gates = data["gates"]
    stages = data["stages"]

    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown("### 🧪 Perjalanan Riset — semua tahap, termasuk yang ditolak")
    st.markdown(
        "Halaman ini mendokumentasikan **setiap percobaan** proyek Fraud "
        "Triage secara apa adanya — bukan hanya yang berhasil. Dua paket "
        "model yang diuji di sini **ditolak** dan **tidak pernah "
        "menggantikan** model live.\n\n"
        "**Model triase yang berjalan tetap sama:** ensemble CHOSEN + "
        "lapisan aturan Tahap 1 (sinyal penenang).\n\n"
        "**Full-stack** di halaman ini berarti konfigurasi lengkap "
        "persis app live: model + lapisan aturan + sinyal penenang "
        "diterapkan bersama, bukan modelnya saja.\n\n"
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
    st.markdown(_bars_html(stages, gates), unsafe_allow_html=True)
    st.caption(
        f"Gerbang: SAH ≥ {_fmt_pct(gates['sah'])} · SMISHING ≥ "
        f"{_fmt_pct(gates['smishing'])} · PR-AUC ≥ "
        f"{_fmt_auc(gates['uci_pr_auc'])} · smishing AUTO-CLOSE = "
        f"{gates['auto_close']}.")

    st.markdown("#### PR-AUC Inggris (UCI test) per tahap")
    with st.container(horizontal=True):
        for s in stages:
            st.metric(f"Tahap {s['id']}", _fmt_auc(s["uci_pr_auc"]),
                      help=f"Gerbang ≥ {_fmt_auc(gates['uci_pr_auc'])}")

    st.markdown("#### Peta kategori — Tahap 2C vs 2D (full-stack)")
    hm_rows = data.get("kategori_heatmap", [])
    if hm_rows and "grup" in hm_rows[0]:
        # Dua chart terpisah per grup (v5.3.1) — lihat _heatmap_chart.
        for grup in ("SAH", "SMISHING"):
            st.markdown(f"**{grup}**")
            chart = _heatmap_chart(hm_rows, grup=grup)
            if chart is not None:
                st.altair_chart(chart, use_container_width=True)
            else:
                st.dataframe([r for r in hm_rows
                              if r.get("grup") == grup])
    else:
        chart = _heatmap_chart(hm_rows)
        if chart is not None:
            st.altair_chart(chart, use_container_width=True)
        else:
            st.dataframe(hm_rows)
    st.caption(
        "Warna = persen pesan lolos per kategori (15 pesan per kategori). "
        "Bandingkan kolom 2C → 2D: kategori yang ditargetkan data 2D "
        "sembuh (keamanan_bank_resmi 60,0% → 93,3%; apk_malware 73,3% → "
        "100%), tetapi beberapa kategori smishing non-target mundur "
        "(mis. investasi_bodong 93,3% → 73,3%) — trade-off yang membuat "
        "gerbang SMISHING 2D gagal.")

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
