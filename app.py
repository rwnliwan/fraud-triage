# -*- coding: utf-8 -*-
"""Fraud Triage — konsol triase smishing (Streamlit), versi v6.1.2.

Menjalankan model CHOSEN proyek Fraud Triage: Ensemble (Top-3 Terkalibrasi)
dengan kebijakan dua ambang t_close=0,010 / t_esc=0,135 (Bagian 10 notebook),
dilengkapi LAPISAN ATURAN (rules.py): kombinasi >= 2 sinyal kuat memaksa
band naik ke ESKALASI — aturan tidak pernah mengubah skor. Logika model
ada di triage_core.py, logika aturan di rules.py; keduanya bisa diuji
tanpa Streamlit.

Baru di v6.1.2 (tautan LinkedIn pembuat): sidebar "Tautan &
sumber" dan footer kini memuat tautan LinkedIn Septian Panjaya di
samping Repo GitHub & Model Hugging Face (diminta Septian — app
ini artefak portofolio). Tanpa perubahan perilaku lain.

Baru di v6.1.1 (penyelarasan vonis Perjalanan Riset): bingkai
vonis gerbang Tahap 2C & 2D di tab Perjalanan Riset kini memakai
tiga status berbasis CI Wilson 95% (lolos jelas / tidak
meyakinkan / gagal jelas) seperti Laporan Edisi v3.3, menggantikan
bingkai biner lama ("gagal tipis"). Kronologi, angka, dan
keputusan akhir tidak berubah. Perubahan di journey.py +
results.json (kolom vonis 2C/2D) — termuat pada reboot berikutnya.

Baru di v6.1.0 (SISKAMLING DIGITAL — kejujuran klaim & bahasa
layanan; tindak lanjut kritik eksternal atas Laporan v3.2): model,
skor, dan ambang TIDAK berubah sama sekali. (1) Vonis bahasa warga
di tab Lapor & Cek dilunakkan bila band ESKALASI hanya dipicu skor
model: label "HAMPIR PASTI PENIPUAN" kini khusus untuk pesan yang
memicu lapisan aturan keras (>= 2 sinyal kuat); selain itu labelnya
"POLANYA SANGAT MIRIP PENIPUAN" + anjuran verifikasi kanal resmi,
dan band menengah/atas tanpa sinyal aturan mendapat peringatan
khusus bahwa pemeriksa belum andal untuk pesan berformat resmi
bank/lembaga. (2) Tab Lapor mendapat expander "Kebijakan privasi &
retensi data" (UU PDP) yang isinya diverifikasi dari kode —
termasuk pernyataan bahwa gambar OCR hanya diproses di memori dan
tidak pernah disimpan, serta kejujuran bahwa hak hapus saat ini
berupa penandaan status. Semua perubahan di siskamling.py —
termuat pada reboot berikutnya.

Baru di v5.4.0 (Perjalanan Riset lengkap): Tahap 2A (korpus) & 2B
(fine-tune) kini berdiri sendiri di alur dan detail — sebelumnya
melebur di dalam entri 2C — dan SETIAP tahap kini memuat rincian
Perlakuan / Model / Data & sumber (dataset + asal-usulnya). 2A/2B
adalah tahap persiapan tanpa skor gerbang (kunci `persiapan` di
results.json, aditif: journey.py lama mengabaikannya dengan aman).
Tab ini termuat pada reboot berikutnya.

Baru di v6.0.0 (SISKAMLING DIGITAL — gelombang riset kompetitor):
(1) Kartu langkah darurat berbasis keadaan sesudah vonis 🔴/🟡 di tab
Lapor & Cek (siskamling.py): warga memilih keadaannya — belum klik /
sudah klik / sudah beri OTP-data / uang terkirim — dan menerima
langkah yang sesuai + tautan resmi cekrekening.id, aduannomor.id,
dan IASC OJK (iasc.ojk.go.id); keadaan terberat menaruh langkah
tercepat (hubungi bank + IASC untuk pembekuan) paling atas.
(2) Loop tertutup: nomor laporan dinyatakan sebagai NOMOR LACAK dan
tab Lapor & Cek mendapat expander "🔎 Lacak laporan saya" — warga
memasukkan nomor laporan dan melihat status pemeriksaan (menunggu /
sudah diperiksa + label bahasa warga) tanpa teks/hash/data lain
terekspos. (3) Intake tangkapan layar + OCR (pytesseract ind+eng;
packages.txt memasang tesseract-ocr + tesseract-ocr-ind di Streamlit
Cloud): teks bacaan tampil untuk diedit warga sebelum masuk alur
cek/lapor yang sama; OCR tidak tersedia/gagal -> warga diarahkan
tempel manual, tidak menggagalkan apa pun. (4) Pengayaan intake:
domain dari teks ter-scrub dicek umurnya via RDAP publik (tanpa
kunci API) dan disimpan di kolom baru reports.enrichment (migrasi
migrate_v6.py); tampil di kartu antrean Verifikasi sebagai info
pendukung, BUKAN penentu label; kegagalan lookup tidak pernah
menggagalkan laporan. (5) Pertahanan anti-racun korpus: batas maks
3 laporan per teks sama (text_hash) per hari — selebihnya tidak
tersimpan sebagai duplikat berlebih; tabel baru label_log mencatat
setiap aksi label (verifikasi / tinjauan kedua / kembalikan / tolak
/ hapus); tab Verifikasi mendapat alur TINJAUAN KEDUA buta atas
sampel acak laporan terverifikasi — hasil yang cocok masuk SUBSET
EMAS, hitungannya tampil di panel Analitik. Semua perubahan di modul
siskamling.py + migrasi DB aditif — termuat pada reboot berikutnya.

Baru di v5.9.1 (SISKAMLING DIGITAL — ketahanan integrasi Turnstile):
token Turnstile yang sudah lolos verifikasi dipakai ulang selama sesi
dari nilai komponen yang masih berlaku — klik kirim tidak perlu
memverifikasi ulang token sekali pakai ke Cloudflare.

Baru di v5.9.0 (SISKAMLING DIGITAL — UI/UX Opsi A + Turnstile dorman):
(1) Perjalanan warga dirapikan: tab 📮 Lapor & Cek menjadi tab pertama
(halaman mendarat) dan 🖼️ Galeri kedua, konsol riset menyusul; hero
"Cek dulu, sebelum klik" + 3 langkah + bukti sosial (modus
terverifikasi & laporan masuk) di tab Lapor; hasil cek kini membuka
dengan VONIS BAHASA WARGA (🔴 hampir pasti penipuan / 🟡 mencurigakan
/ 🟢 kemungkinan aman) + langkah tindakan konkret + tanda bahaya
dalam bahasa awam, sedangkan kartu teknis (skor & sinyal) dilipat ke
expander "Detail teknis"; galeri mendapat saringan kategori modus.
(2) Cloudflare Turnstile TERPASANG DORMAN (komponen
turnstile_component/ + verifikasi server siteverify di siskamling.py):
widget hanya tampil bila SISKAMLING_TURNSTILE_SITE_KEY +
SISKAMLING_TURNSTILE_SECRET terpasang di secrets DAN app_config
turnstile_on='1' — aktivasi cukup membalik flag (tab Verifikasi atau
asisten via basis data), tanpa deploy ulang. Tanpa kunci: formulir
warga tidak berubah. CATATAN QA: logika flag + siteverify teruji
penuh secara fungsi; jabat tangan widget di peramban TIDAK bisa
dibuktikan dari Chromium sandbox VM ini (komponen minimal kanonis
pun gagal identik di sandbox — batasan lingkungan uji, protokolnya
persis mengikuti kode host Streamlit), jadi verifikasi widget
dilakukan TERKENDALI di app live pasca-deploy sebelum flag boleh
dinyalakan untuk warga.

Baru di v5.8.0 (SISKAMLING DIGITAL — Fase 2.5 Hardening): pertahanan
formulir publik tanpa dependensi luar (siskamling.py + migrasi DB
migrate_fase25.py). Kill switch intake di tabel app_config
(intake_open): ditutup -> warga hanya bisa cek, laporan tidak
tersimpan; dapat dibalik dari tab Verifikasi atau langsung di basis
data sebagai jalur darurat. Batas laju: maks 10 laporan per pengirim
(sender_hash) per hari, maks 300 laporan per hari, pemutus antrean
saat pending >= 500, dan jeda 20 detik antar-kirim per sesi. Kolom
baru reports.text_hash (sidik teks ter-scrub ternormalisasi) untuk
deteksi duplikat lintas variasi penulisan di kartu verifikasi.
CAPTCHA Turnstile SENGAJA belum dipasang — eskalasi bila serangan
sungguhan muncul.

Baru di v5.7.0 (SISKAMLING DIGITAL — Analitik): panel "📊 Analitik
layanan" di dalam tab Verifikasi (siskamling.py, di bawah metrik
kepala): total laporan, masuk 7 hari terakhir, pengirim unik &
berulang, tingkat consent, rata-rata waktu verifikasi, corong status,
progres korpus corpus_export per label menuju target ±1.000 (retrain
Tahap 3), grafik laporan per hari (14 hari), distribusi band & kanal,
dan kategori modus terverifikasi terbanyak. Semua dari tabel reports
— jumlah views halaman SENGAJA tidak diklaim di sini (app tidak bisa
menghitung penontonnya sendiri secara akurat; statistik penonton ada
di dashboard Streamlit Cloud pemilik app).

Baru di v5.6.0 (SISKAMLING DIGITAL — Fase 2): tab ketujuh
"🔐 Verifikasi" — ruang kerja verifikasi admin di siskamling.py,
terkunci kata sandi (secret SISKAMLING_ADMIN_PASSWORD; tab hanya
menampilkan formulir kunci sampai sandi benar). Antrean pending
terurut skor risiko dengan SARAN mesin per laporan (label + kategori
dari band/sinyal model — saran, bukan keputusan: label hanya
ditentukan manusia, sesuai desain Fase 0, karena korpus harus berisi
penilaian manusia yang independen dari model). Aksi peninjau:
verifikasi (label SAH/SMISHING/SPAM_PROMO + kategori modus + opsi
tampil galeri), tolak, hapus lunak (status deleted — keluar dari
galeri & korpus), serta kelola yang sudah terverifikasi (tampil/
sembunyi galeri, kembalikan ke antrean, hapus). Metrik kepala:
pending / terverifikasi / baris corpus_export. Modul berubah
(siskamling.py) — termuat pada reboot berikutnya.

Baru di v5.5.0 (SISKAMLING DIGITAL — Fase 1): app menjadi layanan
publik "Siskamling Digital" (ronda warga untuk pesan penipuan) dengan
mesin Fraud Triage yang sama. Dua tab baru dari modul siskamling.py:
"📮 Lapor & Cek" — warga menempel pesan, menerima hasil cek awal, dan
dapat mengirim laporan yang tercatat di database Turso khusus
Siskamling (nomor laporan unik dari id basis data + tanggal submit
created_at; teks hanya disimpan hasil scrub PII scrubber.py; nomor
pengirim hanya sebagai hash bergaram; persetujuan dua tingkat
CONSENT.md v1 dengan jejak consent_log) — dan "🖼️ Galeri Modus",
menampilkan hanya laporan terverifikasi + gallery_visible. Kepala
halaman kini memakai nama Siskamling Digital; Fraud Triage tetap
dikreditkan sebagai mesin penilai. Modul baru (siskamling.py,
scrubber.py) termuat pada reboot berikutnya.

Baru di v5.3.4 (info tambahan hasil audit): glosarium kartu benchmark
(PR-AUC / Recall@FPR1% / ECE) di caption arena; caption expander skor
anggota menjelaskan skor mentah & temperatur; kunci baca +/- faktor
teks; help bawaan pada metrik batch "Kena aturan"/"Kena penenang";
definisi "full-stack" di tab Perjalanan Riset (journey.py — live pada
reboot berikutnya). Audit juga mengonfirmasi bagian lain sudah cukup
jelas (Evaluasi ID, simulator, dropdown komposisi/aturan/keterbatasan).

Baru di v5.3.3 (ikon bantuan "?"): label jargon kini ditemani ikon ?
dengan tooltip CSS satu-dua kalimat (hover desktop, sentuh/fokus di
HP) — empat statistik sidebar (t_close, t_esc, PR-AUC test, mesin
fp32) dan label skor P(scam) terkalibrasi; panel sinyal teks mendapat
baris penjelas S1–S3 vs penenang. Slider simulator sudah punya help
bawaan Streamlit. Murni app.py — termuat tanpa reboot.

Baru di v5.3.2 (paket responsif CSS): media query <=640px/<=480px —
padding konten dikencangkan dan font metrik/judul diturunkan
proporsional di mode phone (konten terasa "mengecil" karena padding
bawaan Streamlit memakan lebar); chart Vega dipastikan selebar
kontainer. Murni CSS di app.py — termuat tanpa reboot.

Baru di v5.3.1 (patch heatmap): facet Altair v5.2.2 terbukti
menyusutkan lebar heatmap di layar sempit (sel terdesak, teks persen
bertumpuk di HP) — grup SAH/SMISHING kini dirender sebagai dua chart
terpisah yang melebar penuh, bukan facet.

Baru di v5.3 (P1 — antrean batch kerja analis): hasil Mode Batch kini
ditampilkan sebagai ANTREAN PRIORITAS terurut skor tertinggi (cara
analis menatap antrean triase sesungguhnya), lengkap dengan peringkat,
pemilih detail per kasus (teks penuh, skor, band model vs final,
sinyal aturan & penenang), dan tombol unduh LAPORAN PER KASUS (.md).
CSV batch tetap tersedia dan kini ikut terurut prioritas.

Baru di v5.2.2 (P0 — heatmap & benchmark sidebar): heatmap kategori
di tab Perjalanan Riset kini memakai label PENDEK dan dua panel facet
terpisah SAH vs SMISHING (label v5.1 terpotong di layar sempit); panel
"Benchmark arena" di sidebar diganti daftar kartu ringkas (nama model
+ PR-AUC/recall/ECE) menggantikan dataframe lebar yang tidak terbaca
tanpa fullscreen.

Baru di v5.2.1 (patch spasi sidebar): kartu status, kotak peringatan,
dan dropdown detail kini dipisahkan margin eksplisit (0,9rem) — di
v5.2 ketiganya menempel karena jarak antarblok Streamlit tidak cukup
memberi napas visual.

Baru di v5.2 (sidebar ringkas + simulator ambang): sidebar tidak lagi
menampilkan semua dokumentasi sebagai paragraf terbuka. Yang tampil
langsung hanya kartu status model (CHOSEN, ambang, PR-AUC, mesin) dan
satu peringatan keterbatasan terpenting; komposisi model, aturan &
sinyal penenang, keterbatasan lengkap, benchmark, dan tautan dipindah
ke satu dropdown "Lihat detail" — satu topik tampil pada satu waktu.
Tab Evaluasi ID juga mendapat simulator ambang: skor panel 16 dihitung
sekali, lalu slider t_close/t_esc menunjukkan dampak kebijakan secara
langsung TANPA mengubah ambang live app. Panel 16 tetap set buatan
kecil untuk transparansi, bukan benchmark.

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

import json
import os
from datetime import datetime

import streamlit as st

from triage_core import TriageEngine, ZONES, resolve_bert_source
from rules import apply_rules_and_calm, _SIGNAL_NAMES
from journey import render_journey
from siskamling import render_lapor_tab, render_gallery_tab, \
    render_admin_tab

APP_VERSION = "v6.1.2"
MAX_SINGLE_CHARS = 2000   # butir C: batas analisis tunggal
MAX_BATCH_LINES = 200     # butir B/C: batas baris batch
CSV_TEXT_CHARS = 200      # teks dipotong aman di ekspor CSV

st.set_page_config(page_title="Siskamling Digital — Lapor & Cek Smishing",
                   page_icon="🛡️", layout="wide",
                   initial_sidebar_state="collapsed")

# PageSpeed (ACC 28 Okt 2026): preconnect origin komponen Turnstile +
# meta description. API Streamlit tak menyediakan meta description; meta di
# body tetap terbaca audit Lighthouse yang memindai seluruh dokumen.
st.markdown(
    '<link rel="preconnect" href="https://siskamling-ts.rwnliwan.workers.dev">'
    '<meta name="description" content="Siskamling Digital — laporkan dan cek '
    "pesan mencurigakan (smishing). Layanan publik berbasis laporan warga, "
    'diverifikasi manusia, bukan AI menilai AI.">',
    unsafe_allow_html=True,
)

# PageSpeed (ACC 28 Okt 2026, paket kontras + target sentuh): warna eksplisit
# pasangan depan/belakang + tinggi target minimum 48px untuk elemen yang
# gagal di audit Lighthouse. Latar footer dibuat eksplisit agar pasangan
# kontrasnya tidak bergantung pada tema (teks #E8EDF7 di #0B1120 ≈ 15:1).
st.markdown(
    """<style>
    .ft-footer, .ft-footer b {
      color: #E8EDF7 !important; background: #0B1120 !important;
    }
    .ft-footer a { color: #E8EDF7 !important; }
    .ft-footer { padding: 0.4rem 0.6rem; border-radius: 8px; }
    label p, label span, label div { color: #E8EDF7 !important; background: #0B1120 !important; }
    input::placeholder, textarea::placeholder { color: #C7D2E0 !important; opacity: 1 !important; }
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * { color: #C7D2E0 !important; }
    div.stMarkdown p { color: #E8EDF7 !important; }
    [data-testid="stExpandSidebarButton"] {
      min-width: 48px !important; min-height: 48px !important;
    }
    div[data-testid="stSelectbox"], div[data-testid="stSelectbox"] input {
      min-height: 48px !important;
    }
    input[aria-label="Nomor pengirim pesan (opsional)"] {
      min-height: 48px !important;
    }
    summary { min-height: 48px !important; }
    </style>""",
    unsafe_allow_html=True,
)

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
/* Sidebar v5.2: panel status ringkas, bukan dinding dokumentasi. */
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
  padding-top: 1.1rem;
}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
  gap: 0.65rem;
}
.ft-side-card {
  padding: 0.95rem; border-radius: 12px; margin-bottom: 0.9rem;
  background: linear-gradient(145deg, #111a2e 0%, #171126 100%);
  border: 1px solid #2a3a5f;
}
.ft-side-kicker {
  color: #8fa1c0; font-size: 0.68rem; font-weight: 700;
  letter-spacing: 0.11em;
}
.ft-side-title {
  color: #f2f5fb; font-size: 1.08rem; font-weight: 750;
  line-height: 1.25; margin-top: 0.3rem;
}
.ft-side-status {
  color: #86efac; font-size: 0.82rem; font-weight: 650;
  margin-top: 0.3rem;
}
.ft-side-stats {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: 0.45rem; margin-top: 0.75rem;
}
.ft-side-stat {
  background: #0d1526; border: 1px solid #2a3a5f;
  border-radius: 9px; padding: 0.5rem 0.55rem;
}
.ft-side-stat small {
  display: block; color: #8fa1c0; font-size: 0.66rem;
  font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
}
.ft-side-stat strong {
  color: #f2f5fb; font-size: 0.98rem; line-height: 1.35;
}
/* Ikon bantuan "?" + tooltip (v5.3.3): lingkaran kecil di samping label
   jargon; penjelasan satu-dua kalimat muncul saat hover (desktop) atau
   fokus/sentuh (keyboard & HP). Murni CSS — tanpa JavaScript. */
.ft-help {
  display: inline-flex; align-items: center; justify-content: center;
  width: 0.95rem; height: 0.95rem; border-radius: 999px;
  border: 1px solid #54678c; color: #9fb2d0; background: transparent;
  font-size: 0.62rem; font-weight: 700; line-height: 1;
  margin-left: 0.32rem; cursor: help; position: relative;
  vertical-align: 0.14em; text-transform: none; letter-spacing: 0;
}
.ft-help .ft-tip {
  display: none; position: absolute; z-index: 80;
  bottom: calc(100% + 0.45rem); left: 50%; transform: translateX(-50%);
  width: 13.5rem; max-width: 72vw; white-space: normal;
  background: #101b31; border: 1px solid #3b5280; border-radius: 9px;
  padding: 0.55rem 0.65rem;
  color: #dbe4f3; font-size: 0.74rem; font-weight: 500;
  line-height: 1.45; text-transform: none; letter-spacing: 0;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.5);
}
.ft-help:hover .ft-tip, .ft-help:focus .ft-tip,
.ft-help:active .ft-tip { display: block; }
.ft-side-note {
  color: #c6d0e4; font-size: 0.84rem; line-height: 1.45;
  margin: 0.75rem 0 0 0;
}
.ft-side-alert {
  padding: 0.7rem 0.75rem; border-radius: 10px; margin-bottom: 0.9rem;
  background: #2b2110; border: 1px solid #a16207;
  color: #fde68a; font-size: 0.84rem; line-height: 1.45;
}
.ft-bench-card {
  background: #0d1526; border: 1px solid #2a3a5f;
  border-radius: 9px; padding: 0.55rem 0.65rem; margin-bottom: 0.5rem;
}
.ft-bench-name {
  color: #f2f5fb; font-size: 0.85rem; font-weight: 650; line-height: 1.35;
}
.ft-bench-stats {
  color: #8fa1c0; font-size: 0.78rem; margin-top: 0.2rem; line-height: 1.4;
}
.ft-bench-stats b { color: #c6d0e4; }
[data-testid="stSidebar"] [data-testid="stSelectbox"] {
  margin-top: 0.1rem;
}
[data-testid="stSidebar"] [data-testid="stSelectbox"] label {
  color: #c6d0e4; font-weight: 650; margin-bottom: 0.3rem;
}
[data-testid="stSidebar"] [data-testid="stExpander"],
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
  margin-top: 0.15rem;
}
/* ===== Paket responsif (v5.3.2) — mode phone / layar sempit =====
   Padding bawaan Streamlit di HP memakan lebar yang seharusnya jadi
   milik konten (chart terdesak -> terasa "mengecil"). Di <=640px:
   padding dikencangkan, font metrik & judul diturunkan proporsional,
   chart Vega dipastikan selebar kontainer. Isi chart sendiri diatur
   spesifikasinya (dua chart terpisah di journey.py v5.3.1), bukan CSS. */
@media (max-width: 640px) {
  .block-container {
    padding-top: 1.1rem;
    padding-left: 0.65rem;
    padding-right: 0.65rem;
  }
  h1 { font-size: 1.55rem; }
  h2 { font-size: 1.28rem; }
  h3 { font-size: 1.1rem; }
  [data-testid="stMetricValue"] { font-size: 1.28rem; }
  [data-testid="stMetricLabel"] { font-size: 0.7rem; }
  [data-testid="stVegaLiteChart"] { width: 100%; }
  .ft-side-stats { gap: 0.35rem; }
  .ft-bench-stats { font-size: 0.74rem; }
}
@media (max-width: 480px) {
  [data-testid="stMetricValue"] { font-size: 1.1rem; }
  .block-container {
    padding-left: 0.5rem;
    padding-right: 0.5rem;
  }
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


def _engine_config():
    """Konfigurasi sumber model dari secrets/env (tanpa memuat model)."""
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
    return bert_source, artifact_repo_id


@st.cache_resource(show_spinner="Memuat ensemble (termasuk DistilBERT)…")
def load_engine():
    bert_source, artifact_repo_id = _engine_config()
    # Mesin tetap fp32: uji float16 (v3) gagal batas adopsi latensi —
    # lihat README.md bagian performa.
    return TriageEngine(bert_source=bert_source,
                        artifact_repo_id=artifact_repo_id)


def _engine_load_failed(exc):
    """Pesan gagal-muat yang sama seperti perilaku lama (gerbang awal)."""
    st.error(f"Model belum bisa dimuat: {exc}")
    st.info("Secara bawaan app mengunduh seluruh artefak model dari repo "
            "Hugging Face publik rwnliwan/fraud-triage-smishing — "
            "periksa koneksi keluar app, atau set secrets opsional "
            "ARTIFACT_REPO_ID / BERT_MODEL_ID ke repo lain. "
            "Lihat README.md.")
    st.stop()


_SPEC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "model", "ensemble_spec.json")


def _local_spec():
    """Spec ensemble dari berkas lokal (murah; tanpa memuat bobot)."""
    try:
        with open(_SPEC_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


class _LazyEngine:
    """Proxy mesin triase: bobot model TIDAK dimuat saat halaman dibuka.

    Profil lokal 2026-10-23: membangun TriageEngine sungguhan memakan
    ±10 dtk hangat (±40 dtk dingin: impor torch/transformers, unpickle
    anggota sklearn, muat DistilBERT) dan dulu terjadi SEBELUM tab
    pertama digambar — seluruh halaman menunggu model. Kini ambang
    dibaca dari spec lokal dan sumber bobot diresolusi tanpa memuat
    apa pun; TriageEngine asli (ter-cache_resource) baru dibangun pada
    analisis pertama, dengan spinner yang sama seperti sebelumnya.
    Atribut lain (members, spec, …) diteruskan ke mesin asli.
    """

    def __init__(self):
        self._real = None
        self._spec = _local_spec()

    def _load(self):
        if self._real is None:
            try:
                self._real = load_engine()
            except Exception as exc:
                _engine_load_failed(exc)
        return self._real

    @property
    def t_close(self):
        if self._spec:
            return float(self._spec["t_close"])
        return self._load().t_close

    @property
    def t_esc(self):
        if self._spec:
            return float(self._spec["t_esc"])
        return self._load().t_esc

    @property
    def bert_source(self):
        if self._real is not None:
            return self._real.bert_source
        bert_source, artifact_repo_id = _engine_config()
        return resolve_bert_source(bert_source, artifact_repo_id)

    def triage(self, text):
        return self._load().triage(text)

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self._load(), name)


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


def _zone_from_score(p, t_close, t_esc):
    """Band model dari skor dengan ambang simulasi (bukan ambang live)."""
    if p < t_close:
        return "AUTO-CLOSE"
    if p >= t_esc:
        return "ESKALASI"
    return "REVIEW ANALIS"


def _evaluate_thresholds(base_rows, t_close, t_esc):
    """Terapkan ambang simulasi + lapisan aturan/penenang ke panel.

    `base_rows` hanya membawa skor model yang sudah dihitung sekali;
    fungsi ini tidak memanggil model lagi, jadi slider bisa bergerak
    responsif. Aturan dan penenang tetap diterapkan persis seperti app
    live, hanya band model awalnya berasal dari ambang simulasi.
    """
    rows = []
    for base in base_rows:
        model_zone = _zone_from_score(base["score"], t_close, t_esc)
        final_zone, rule = apply_rules_and_calm(base["text"], model_zone)
        if base["label"] == "SAH":
            ok = final_zone in ("AUTO-CLOSE", "REVIEW ANALIS")
        else:
            ok = final_zone == "ESKALASI"
        rows.append({
            **base,
            "model_zone": model_zone,
            "final_zone": final_zone,
            "rule_triggered": bool(rule["triggered"]),
            "signals": list(rule["active_signals"]),
            "calm_applied": bool(rule.get("calm", {}).get("lowered")),
            "calm_reasons": list(rule.get("calm", {}).get("reasons", [])),
            "ok": ok,
        })
    return rows


def _threshold_summary(rows):
    """Ringkasan panel untuk satu pilihan ambang."""
    sah = [r for r in rows if r["label"] == "SAH"]
    smishing = [r for r in rows if r["label"] == "SMISHING"]
    return {
        "sah_ok": sum(1 for r in sah if r["ok"]),
        "sah_n": len(sah),
        "smishing_ok": sum(1 for r in smishing if r["ok"]),
        "smishing_n": len(smishing),
        "total_ok": sum(1 for r in rows if r["ok"]),
        "total_n": len(rows),
        "smishing_auto_close": sum(
            1 for r in smishing if r["final_zone"] == "AUTO-CLOSE"),
        "zones": {
            zone: sum(1 for r in rows if r["final_zone"] == zone)
            for zone in ("AUTO-CLOSE", "REVIEW ANALIS", "ESKALASI")
        },
    }


def _short(text, n):
    return text if len(text) <= n else text[:n] + "…"


def _export_csv(records, extra_key=None):
    """Bangun berkas CSV (bytes) dari rekaman standar — butir A.

    Kolom: Teks (dipotong aman), Skor, Band model, Band final,
    Aturan terpicu, Sinyal aktif (+ kolom ekstra bila diminta,
    mis. band koreksi pengguna pada log koreksi).
    """
    import pandas as pd  # malas: hanya untuk ekspor CSV & tabel hasil
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


def _case_report_md(rank, r, engine):
    """Laporan per kasus (Markdown) untuk unduhan dari antrean batch — P1.

    Semua angka diambil dari rekaman standar kasus itu sendiri; ambang
    dibaca dari engine live, bukan diketik ulang.
    """
    nama_final, emoji_final, _ = ZONE_DISPLAY[r["zone_final"]]
    if r["rule_triggered"]:
        sig = "; ".join(
            f"{s} ({_SIGNAL_NAMES.get(s, s)})" for s in r["signals"])
        aturan = f"**TERPICU** — sinyal aktif: {sig}"
    elif r["signals"]:
        sig = "; ".join(
            f"{s} ({_SIGNAL_NAMES.get(s, s)})" for s in r["signals"])
        aturan = (f"tidak terpicu (hanya 1 sinyal kuat aktif: {sig}; "
                  f"aturan butuh >= 2 sinyal bersamaan)")
    else:
        aturan = "tidak terpicu (tidak ada sinyal kuat aktif)"
    if r.get("calm_applied"):
        tenang = "**diterapkan** — " + "; ".join(r["calm_reasons"])
    else:
        tenang = "tidak diterapkan"
    return (
        f"# Laporan Kasus Triase — Peringkat #{rank}\n\n"
        f"Dihasilkan dari Mode Batch Fraud Triage app {APP_VERSION} "
        f"(model operasional: Ensemble Top-3 Terkalibrasi — CHOSEN).\n\n"
        f"## Pesan\n\n> {r['text']}\n\n"
        f"## Hasil\n\n"
        f"- Skor model (probabilitas scam terkalibrasi): "
        f"**{r['score']:.3f}**\n"
        f"- Ambang kebijakan: t_close = {engine.t_close:.3f} · "
        f"t_esc = {engine.t_esc:.3f}\n"
        f"- Band model: **{r['zone_model']}**\n"
        f"- Band final: **{r['zone_final']}** ({emoji_final} "
        f"{nama_final})\n\n"
        f"## Lapisan aturan\n\n"
        f"- Aturan keamanan (>= 2 sinyal kuat): {aturan}\n"
        f"- Sinyal penenang: {tenang}\n\n"
        f"## Catatan\n\n"
        f"Skor adalah perangkingan triase untuk antrean manusia, "
        f"bukan vonis akhir. Model adalah artefak pembelajaran "
        f"terpimpin (data latih utama SMS Inggris ±2011); pola "
        f"smishing Indonesia modern berada di luar distribusi itu.\n"
    )


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


def help_icon(tip):
    """Ikon "?" kecil dengan tooltip CSS (lihat .ft-help di blok gaya).

    Dipakai di samping label jargon (t_close, PR-AUC, dst.) agar pembaca
    awam tidak perlu menebak artinya. Teks tip tampil apa adanya —
    hindari karakter " di dalamnya.
    """
    return (f'<span class="ft-help" tabindex="0">?'
            f'<span class="ft-tip">{tip}</span></span>')


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
    <small>P(scam) terkalibrasi {help_icon('Peluang pesan ini smishing menurut model, sudah dikalibrasi: skor 0,42 berarti kira-kira 42 dari 100 pesan serupa benar-benar smishing pada data kalibrasi. Skor ini mengurutkan antrean triase — bukan vonis akhir.')}</small></div>
  <div class="ft-desc">{ZONES[zone]["desc_id"]}</div>
  <div class="ft-verdict">{verdict}</div>
  {model_band}{badge}
</div>"""


def signal_panel_md(rule):
    sig = rule["signals"]
    lines = ["#### 🛰️ Panel sinyal teks",
             "_Petunjuk tekstual dari lapisan aturan (terpisah dari skor "
             "model). Sinyal kuat S1–S3 adalah pola khas smishing; sinyal "
             "penenang menandai pola pesan resmi._"]
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
  <h1>🏘️ Siskamling Digital — Ronda Warga untuk Pesan Penipuan</h1>
  <p>Laporkan & cek pesan mencurigakan di tab <b>📮 Lapor & Cek</b>,
  kenali pola penipuan terbaru di <b>🖼️ Galeri Modus</b>. Mesin penilai:
  <b>Ensemble (Top-3 Terkalibrasi)</b> proyek Fraud Triage, kebijakan dua
  ambang <b>t_close = 0,010</b> · <b>t_esc = 0,135</b>, ditambah lapisan
  aturan kombinasi sinyal kuat yang menaikkan band ke ESKALASI dan
  sinyal penenang terbatas yang dapat menurunkan ESKALASI satu tingkat
  ke REVIEW ANALIS untuk pola resmi berformat jelas (tidak pernah
  menutup otomatis).</p>
</div>
""", unsafe_allow_html=True)

# Mesin dimuat MALAS lewat proxy: halaman + formulir warga tampil
# dulu; bobot ensemble baru dibangun pada analisis pertama (profil:
# ±10 dtk hangat / ±40 dtk dingin — dulu angka itu memblokir tab
# pertama). Bila pembangunan gagal, pesan galatnya sama seperti
# gerbang lama lewat _engine_load_failed().
engine = _LazyEngine()

# ---------------------------------------------------------------------------
# Sidebar v5.2: kartu status ringkas + dropdown detail
# ---------------------------------------------------------------------------
with st.sidebar:
    # Yang selalu tampil hanya status yang dibutuhkan untuk membaca app.
    # Semua dokumentasi panjang tinggal di balik satu dropdown.
    st.markdown(
        f"""
        <div class="ft-side-card">
          <div class="ft-side-kicker">MODEL OPERASIONAL</div>
          <div class="ft-side-title">Ensemble Top-3 Terkalibrasi</div>
          <div class="ft-side-status">● CHOSEN · app {APP_VERSION}</div>
          <div class="ft-side-stats">
            <div class="ft-side-stat">
              <small>t_close {help_icon('Ambang tutup otomatis: skor P(scam) di bawah nilai ini masuk AUTO-CLOSE — pesan dianggap sah tanpa eskalasi. Sengaja disetel sangat rendah supaya smishing hampir mustahil ikut tertutup.')}</small><strong>{engine.t_close:.3f}</strong>
            </div>
            <div class="ft-side-stat">
              <small>t_esc {help_icon('Ambang eskalasi: skor P(scam) di atas nilai ini masuk ESKALASI prioritas tinggi. Pada data validation, zona di atas ambang ini presisinya 90% atau lebih.')}</small><strong>{engine.t_esc:.3f}</strong>
            </div>
            <div class="ft-side-stat">
              <small>PR-AUC test {help_icon('Ukuran ketepatan perangkingan model pada data uji (skala 0 sampai 1, makin tinggi makin baik). 0,986 dicapai pada data uji Inggris UCI. Angka ini menilai kualitas urutan skor, bukan akurasi vonis per pesan.')}</small><strong>0,986</strong>
            </div>
            <div class="ft-side-stat">
              <small>Mesin {help_icon('Model dijalankan pada presisi penuh fp32 (floating point 32-bit), bukan hasil kuantisasi atau kompresi — skor yang tampil identik dengan saat model dievaluasi.')}</small><strong>fp32</strong>
            </div>
          </div>
          <p class="ft-side-note">Skor adalah <b>perangkingan triase</b>
          untuk antrean manusia — bukan vonis akhir.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="ft-side-alert">⚠️ <b>Penting:</b> data latih utama '
        'adalah SMS Inggris ±2011. Pola smishing Indonesia modern '
        'berada di luar distribusi itu.</div>',
        unsafe_allow_html=True,
    )

    sidebar_detail = st.selectbox(
        "Lihat detail",
        [
            "Komposisi model",
            "Aturan & sinyal penenang",
            "Keterbatasan",
            "Benchmark arena",
            "Tautan & sumber",
        ],
        index=None,
        placeholder="Pilih detail…",
        key="sidebar_detail",
    )

    if sidebar_detail == "Komposisi model":
        with st.container(border=True):
            st.markdown(
                "**Ensemble (Top-3 Terkalibrasi)** adalah rata-rata "
                "probabilitas terkalibrasi (temperature scaling) dari:\n"
                "1. DistilBERT multilingual (fine-tune)\n"
                "2. TF-IDF + Fitur Angka + Logistic Regression\n"
                "3. TF-IDF + Logistic Regression\n\n"
                f"Kebijakan live memakai **t_close = "
                f"{engine.t_close:.3f}** dan **t_esc = "
                f"{engine.t_esc:.3f}**. PR-AUC test ensemble adalah "
                "**0,986** pada arena final notebook."
            )
    elif sidebar_detail == "Aturan & sinyal penenang":
        with st.container(border=True):
            st.markdown(
                "**Lapisan aturan (hanya menaikkan):** kombinasi ≥ 2 "
                "sinyal kuat — tautan; permintaan kredensial/bertindak "
                "lewat tautan; ancaman + urgensi — memaksa band naik ke "
                "ESKALASI. Aturan tidak mengubah skor.\n\n"
                "**Sinyal penenang (v4, Tahap 1):** pola resmi "
                "berformat sangat jelas boleh menurunkan band ESKALASI "
                "model **satu tingkat** ke REVIEW ANALIS. Penenang "
                "**tidak pernah** menghasilkan AUTO-CLOSE dan **gugur "
                "total** bila sinyal kuat S2/S3 aktif atau aturan "
                "terpicu.\n\n"
                "Batasnya jujur: penenang hanya menolong pola "
                "berformat jelas; over-eskalasi model pada teks "
                "Indonesia bebas tetap menjadi keterbatasan model."
            )
    elif sidebar_detail == "Keterbatasan":
        with st.container(border=True):
            st.markdown(
                "Data latih adalah **UCI SMS Spam Collection** — SMS "
                "Inggris ±2011. Pola smishing Indonesia modern berada "
                "**di luar distribusi** itu (korpus mini ID di "
                "notebook menunjukkan drift besar), jadi perlakukan "
                "skor sebagai **perangkingan triase** untuk antrean "
                "manusia, bukan vonis akhir.\n\n"
                "Skor adalah probabilitas terkalibrasi — nilainya "
                "memang jarang mendekati 0 atau 1. Model ini artefak "
                "pembelajaran terpimpin, bukan sistem produksi bank."
            )
    elif sidebar_detail == "Benchmark arena":
        with st.container(border=True):
            # v5.2.2: kartu ringkas per model — dataframe lama terlalu
            # lebar untuk sidebar (kolom angka tak terbaca tanpa
            # fullscreen). Angka persis sama dengan BENCHMARK.
            def _fmt3(v):
                return f"{v:.3f}".replace(".", ",")
            st.markdown("".join(
                f'<div class="ft-bench-card">'
                f'<div class="ft-bench-name">{nama}</div>'
                f'<div class="ft-bench-stats">PR-AUC <b>{_fmt3(pr)}</b>'
                f' · Recall@FPR1% <b>{_fmt3(rec)}</b>'
                f' · ECE <b>{_fmt3(ece)}</b></div></div>'
                for nama, pr, rec, ece in BENCHMARK
            ), unsafe_allow_html=True)
            st.caption(
                "Arena test notebook Bagian 9 pada test set Inggris "
                "(UCI). Model operasional = peringkat pertama. "
                "Cara membaca angka di kartu: **PR-AUC** = ketepatan "
                "perangkingan skor (0–1, makin tinggi makin baik); "
                "**Recall@FPR1%** = dari semua smishing, persen yang "
                "tertangkap saat alarm palsu dibatasi 1% dari pesan sah; "
                "**ECE** = selisih rata-rata antara skor dan kenyataan "
                "(makin kecil, makin jujur skornya sebagai peluang).")
    elif sidebar_detail == "Tautan & sumber":
        with st.container(border=True):
            st.link_button(
                "Repo GitHub",
                "https://github.com/rwnliwan/fraud-triage",
                use_container_width=True,
            )
            st.link_button(
                "Model Hugging Face",
                "https://huggingface.co/rwnliwan/fraud-triage-smishing",
                use_container_width=True,
            )
            st.link_button(
                "LinkedIn — Septian Panjaya",
                "https://www.linkedin.com/in/septian-panjaya",
                use_container_width=True,
            )
            st.caption(
                "Detail metode, benchmark semua kandidat & vonis ada "
                "di notebook proyek "
                "`fraud-triage-laya-vs-ml-dl.ipynb`."
            )
            st.caption(f"Bobot DistilBERT dimuat dari: "
                       f"{engine.bert_source}")

for _key in ("history", "feedback"):
    if _key not in st.session_state:
        st.session_state[_key] = []

# Urutan tab (UI/UX Opsi A, v5.9.0): layanan WARGA dulu — Lapor & Cek
# adalah tab pertama (halaman mendarat) dan Galeri kedua; konsol riset
# analis menyusul; Verifikasi (admin) tetap terakhir.
tab_lapor, tab_gallery, tab_single, tab_batch, tab_eval, \
    tab_journey, tab_admin = st.tabs(
    ["📮 Lapor & Cek", "🖼️ Galeri Modus", "🔎 Analisis Tunggal",
     "🗂️ Mode Batch", "🇮🇩 Evaluasi ID", "🧪 Perjalanan Riset",
     "🔐 Verifikasi"])

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
        import pandas as pd  # malas: hanya saat ada hasil untuk ditabelkan
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
                           "design). **Skor mentah** = keluaran model "
                           "sebelum kalibrasi. **Temperatur** = pengatur "
                           "ketajaman kalibrasi (temperature scaling): "
                           "skor mentah diskalakan ulang agar nilainya "
                           "jujur dibaca sebagai peluang — temperatur "
                           "di atas 1 menghaluskan skor yang ekstrem.")
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
        st.caption("Cara membaca angka di samping kata: tanda **+** "
                   "mendorong skor naik (makin mencurigakan), tanda **−** "
                   "menekan skor turun. Angka itu adalah bobot kata pada "
                   "anggota Logistic Regression — salah satu dari tiga "
                   "anggota ensemble.")
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
        import pandas as pd  # malas: hanya saat riwayat tidak kosong
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
        import pandas as pd  # malas: hanya saat log koreksi tidak kosong
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
            # P1: antrean prioritas — skor tertinggi di atas, seperti
            # antrean kerja analis. Urutan ini dipakai tabel, CSV,
            # dan pemilih detail per kasus.
            rows.sort(key=lambda r: r["score"], reverse=True)
            st.session_state["batch_rows"] = rows

    rows = st.session_state.get("batch_rows")
    if rows:
        import pandas as pd  # malas: hanya saat hasil batch ada
        counts = {"AUTO-CLOSE": 0, "REVIEW ANALIS": 0, "ESKALASI": 0}
        for r in rows:
            counts[r["zone_final"]] += 1
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("🟢 AMAN", counts["AUTO-CLOSE"])
        m2.metric("🟡 REVIEW ANALIS", counts["REVIEW ANALIS"])
        m3.metric("🔴 ESKALASI", counts["ESKALASI"])
        m4.metric("⬆️ Kena aturan",
                  sum(1 for r in rows if r["rule_triggered"]),
                  help="Jumlah pesan yang band finalnya dipaksa naik ke "
                       "ESKALASI oleh lapisan aturan (≥ 2 sinyal kuat "
                       "bersamaan), berapa pun skor modelnya.")
        m5.metric("⬇️ Kena penenang",
                  sum(1 for r in rows if r.get("calm_applied")),
                  help="Jumlah pesan yang band-nya diturunkan tepat satu "
                       "tingkat oleh sinyal penenang (pola pesan resmi "
                       "berformat jelas). Penenang tidak pernah "
                       "menghasilkan AUTO-CLOSE.")
        st.markdown("#### Antrean prioritas — skor tertinggi di atas")
        df_rows = pd.DataFrame([{
            "#": i + 1,
            "Pesan": _short(r["text"], 60),
            "Skor": round(r["score"], 3),
            "Band model": r["zone_model"],
            "Band final": r["zone_final"],
            "Aturan terpicu": ("Ya — " + "+".join(r["signals"]))
            if r["rule_triggered"] else "Tidak",
            "Penenang": ("Ya — " + "; ".join(r["calm_reasons"]))
            if r.get("calm_applied") else "Tidak",
        } for i, r in enumerate(rows)])
        st.dataframe(df_rows, hide_index=True)
        st.download_button(
            "⬇️ Unduh hasil batch (CSV)", key="dl_batch",
            data=_export_csv(rows),
            file_name="fraud-triage-batch.csv", mime="text/csv")

        # P1: detail per kasus + laporan .md yang bisa diunduh.
        st.markdown("#### Detail kasus")
        case_labels = [
            f"#{i + 1} · {r['score']:.3f} · "
            f"{ZONE_DISPLAY[r['zone_final']][0]} · "
            f"{_short(r['text'], 48)}"
            for i, r in enumerate(rows)
        ]
        pick = st.selectbox(
            "Pilih kasus", case_labels, key="batch_case_pick")
        idx = case_labels.index(pick)
        r = rows[idx]
        nama_final, emoji_final, _ = ZONE_DISPLAY[r["zone_final"]]
        with st.container(border=True):
            st.markdown(f"**Pesan lengkap**\n\n> {r['text']}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Skor model", f"{r['score']:.3f}")
            c2.metric("Band model", r["zone_model"])
            c3.metric("Band final",
                      f"{emoji_final} {nama_final}")
            if r["rule_triggered"]:
                st.markdown(
                    "**Aturan keamanan: TERPICU** — sinyal aktif: "
                    + "; ".join(
                        f"{s} ({_SIGNAL_NAMES.get(s, s)})"
                        for s in r["signals"]))
            elif r["signals"]:
                st.markdown(
                    "**Aturan keamanan: tidak terpicu** — sinyal kuat "
                    "aktif: " + "; ".join(
                        f"{s} ({_SIGNAL_NAMES.get(s, s)})"
                        for s in r["signals"])
                    + " (aturan butuh >= 2 sinyal bersamaan).")
            else:
                st.markdown(
                    "**Aturan keamanan: tidak terpicu** — tidak ada "
                    "sinyal kuat aktif.")
            if r.get("calm_applied"):
                st.markdown(
                    "**Sinyal penenang: diterapkan** — "
                    + "; ".join(r["calm_reasons"]))
            st.download_button(
                "⬇️ Unduh laporan kasus (.md)", key="dl_case",
                data=_case_report_md(idx + 1, r, engine),
                file_name=f"kasus-{idx + 1:02d}.md",
                mime="text/markdown")

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
        import pandas as pd  # malas: hanya saat hasil evaluasi ada
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

    # -- Simulator ambang (v5.2) -------------------------------------------
    st.markdown("---")
    st.markdown("### 🎚️ Simulator ambang")
    st.markdown(
        "Geser ambang untuk melihat **apa yang akan berubah pada panel "
        "16 ini** bila kebijakan memakai t_close / t_esc lain. Skor "
        "model dihitung sekali; lapisan aturan dan sinyal penenang "
        "tetap diterapkan. **Ambang live app tidak berubah**, dan panel "
        "buatan kecil ini tetap **bukan benchmark** — alat ini hanya "
        "membuat trade-off kebijakan terlihat."
    )

    if "threshold_sim_base" not in st.session_state:
        st.info(
            "Skor panel belum dimuat untuk simulator. Klik tombol "
            "berikut untuk menghitung 16 skor model sekali saja; "
            "sesudah itu slider dapat digeser tanpa memanggil model "
            "lagi."
        )
        if st.button("🧮 Muat skor panel untuk simulator",
                     key="btn_load_threshold_sim"):
            progress = st.progress(
                0, text="Menghitung skor panel 0 dari "
                        f"{len(ID_EVAL_SET)} pesan…")
            base_rows = []
            for i, item in enumerate(ID_EVAL_SET):
                res = engine.triage(item["text"])
                base_rows.append({
                    "text": item["text"],
                    "label": item["label"],
                    "kategori": item["kategori"],
                    "score": float(res["p_scam"]),
                })
                progress.progress(
                    (i + 1) / len(ID_EVAL_SET),
                    text=f"Menghitung skor panel {i + 1} dari "
                         f"{len(ID_EVAL_SET)} pesan…")
            progress.empty()
            st.session_state["threshold_sim_base"] = base_rows
            st.rerun()

    sim_base = st.session_state.get("threshold_sim_base")
    if sim_base:
        import pandas as pd  # malas: hanya untuk tabel dampak simulator
        with st.container(border=True):
            c_close, c_esc = st.columns(2)
            sim_close = c_close.slider(
                "t_close simulasi",
                min_value=0.000,
                max_value=0.500,
                value=float(engine.t_close),
                step=0.005,
                format="%.3f",
                key="sim_t_close",
                help="Di bawah ambang ini band model menjadi AUTO-CLOSE.",
            )
            sim_esc = c_esc.slider(
                "t_esc simulasi",
                min_value=0.010,
                max_value=0.900,
                value=float(engine.t_esc),
                step=0.005,
                format="%.3f",
                key="sim_t_esc",
                help="Di atas ambang ini band model menjadi ESKALASI.",
            )

            if sim_close >= sim_esc:
                st.error(
                    "t_close harus lebih kecil daripada t_esc agar "
                    "zona REVIEW ANALIS tetap ada. Geser salah satu "
                    "slider."
                )
            else:
                live_rows = _evaluate_thresholds(
                    sim_base, engine.t_close, engine.t_esc)
                sim_rows = _evaluate_thresholds(
                    sim_base, sim_close, sim_esc)
                live_sum = _threshold_summary(live_rows)
                sim_sum = _threshold_summary(sim_rows)

                m1, m2, m3, m4 = st.columns(4)
                m1.metric(
                    "SAH sesuai",
                    f"{sim_sum['sah_ok']}/{sim_sum['sah_n']}",
                    delta=sim_sum["sah_ok"] - live_sum["sah_ok"],
                )
                m2.metric(
                    "SMISHING sesuai",
                    f"{sim_sum['smishing_ok']}/{sim_sum['smishing_n']}",
                    delta=sim_sum["smishing_ok"] - live_sum["smishing_ok"],
                )
                m3.metric(
                    "Total sesuai",
                    f"{sim_sum['total_ok']}/{sim_sum['total_n']}",
                    delta=sim_sum["total_ok"] - live_sum["total_ok"],
                )
                m4.metric(
                    "SMISHING → AUTO-CLOSE",
                    sim_sum["smishing_auto_close"],
                    delta=(sim_sum["smishing_auto_close"]
                           - live_sum["smishing_auto_close"]),
                    delta_color="inverse",
                )
                st.caption(
                    f"Perbandingan terhadap ambang live "
                    f"(t_close {engine.t_close:.3f} · t_esc "
                    f"{engine.t_esc:.3f}): total live "
                    f"{live_sum['total_ok']}/{live_sum['total_n']}; "
                    f"distribusi final simulasi — AUTO-CLOSE "
                    f"{sim_sum['zones']['AUTO-CLOSE']}, REVIEW ANALIS "
                    f"{sim_sum['zones']['REVIEW ANALIS']}, ESKALASI "
                    f"{sim_sum['zones']['ESKALASI']}. Delta metrik "
                    f"dihitung terhadap live; khusus AUTO-CLOSE "
                    f"smishing, naik berarti lebih buruk."
                )
                if sim_sum["smishing_auto_close"]:
                    st.warning(
                        "⚠️ Pilihan ambang ini membuat "
                        f"{sim_sum['smishing_auto_close']} pesan "
                        "SMISHING pada panel berakhir di AUTO-CLOSE — "
                        "persis risiko yang membuat gerbang Tahap 2D "
                        "gagal. Kesesuaian total tidak boleh dibaca "
                        "tanpa angka ini."
                    )

                with st.expander("Lihat dampak per pesan"):
                    df_sim = pd.DataFrame([{
                        "Pesan": _short(r["text"], 70),
                        "Kategori": r["kategori"],
                        "Label": r["label"],
                        "Skor": round(r["score"], 3),
                        "Band model simulasi": r["model_zone"],
                        "Band final simulasi": r["final_zone"],
                        "Aturan": "Ya" if r["rule_triggered"] else "Tidak",
                        "Penenang": "Ya" if r["calm_applied"] else "Tidak",
                        "Status": "✅ Sesuai" if r["ok"] else "❌ Tidak sesuai",
                    } for r in sim_rows])
                    st.dataframe(df_sim, hide_index=True)

# ---------------------------------------------------------------------------
# Tab 4 — perjalanan riset (v5): dokumentasi semua tahap percobaan,
# termasuk yang ditolak; model live tidak berubah.
# ---------------------------------------------------------------------------
with tab_journey:
    render_journey()

# ---------------------------------------------------------------------------
# Tab 5 — Siskamling Digital (Fase 1): lapor & cek pesan warga.
# Laporan tercatat di Turso khusus Siskamling dengan nomor laporan
# unik + tanggal submit; lihat siskamling.py.
# ---------------------------------------------------------------------------
with tab_lapor:
    render_lapor_tab(
        engine, analyze_one,
        lambda a: result_card_html(a, engine.t_close, engine.t_esc))

# ---------------------------------------------------------------------------
# Tab 6 — Siskamling Digital (Fase 1): galeri modus terverifikasi.
# ---------------------------------------------------------------------------
with tab_gallery:
    render_gallery_tab()

# ---------------------------------------------------------------------------
# Tab 7 — Siskamling Digital (Fase 2): verifikasi admin (terkunci
# kata sandi; label hanya ditentukan manusia, model hanya menyarankan).
# ---------------------------------------------------------------------------
with tab_admin:
    render_admin_tab()

# ---------------------------------------------------------------------------
# Footer (butir G)
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown(
    f'<div class="ft-footer">🏘️ <b>Siskamling Digital</b> · mesin: '
    f'<b>Fraud Triage</b> — app {APP_VERSION} '
    f'· berjalan di Streamlit Community Cloud · '
    f'<a href="https://github.com/rwnliwan/fraud-triage">Repo GitHub</a>'
    f' · <a href="https://huggingface.co/rwnliwan/fraud-triage-smishing">'
    f'Model Hugging Face</a>'
    f' · <a href="https://www.linkedin.com/in/septian-panjaya">'
    f'LinkedIn — Septian Panjaya</a> · Metode & vonis lengkap: '
    f'notebook proyek '
    f'`fraud-triage-laya-vs-ml-dl.ipynb`</div>',
    unsafe_allow_html=True)
