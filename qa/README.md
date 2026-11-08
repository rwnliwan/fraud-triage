# QA guards — Fraud Triage

| Guard | Yang dicek |
|---|---|
| `qa_fraud_r6_fix.py` | Eksekusi fix ronde 6 (v6.1.4) M1/M2/S5 + ronde 7 (v6.1.5) M1–M4/S1–S10/N1–N3 di SQLite lokal dengan skema Turso live: antrean pelabelan urut waktu vs triase urut skor, label pertama dibekukan, revisi pasca-paparan dicatat terpisah, tinjauan kedua tidak mengubah label; R7: scrubber buang query tanpa path, kartu pending tanpa sinyal pra-label, expander triase hanya hitungan, kesepakatan dua peninjau + adjudikasi, consent dalam-alur, verifikasi pertama + tanggal WITA, S2 menangkap berikan/bagikan, narasi journey jujur, kolom Catatan ambang di panel evaluasi. Tidak menyentuh DB live. |

Jalankan dari root repo ini:

```sh
~/workspace/fraud-triage-laya/.venv/bin/python qa/qa_fraud_r6_fix.py
```

Exit 0 = ALL PASS.

Riwayat: dipindah ke repo 2026-11-08 dari `~/workspace/kelontong-review/qa_fraud_r6_fix.py`
(keputusan Septian: guard WAJIB berversi sebagai backup). Guard mengimpor `siskamling`
dari root repo ini (bukan dari working copy `streamlit-app/`).
