# -*- coding: utf-8 -*-
"""Inti model Fraud Triage — dipakai app.py (Streamlit) dan uji lokal.

Menghidupkan kembali model CHOSEN notebook (fraud-triage-laya-vs-ml-dl.ipynb):

    Ensemble (Top-3 Terkalibrasi) = rata-rata probabilitas TERKALIBRASI
    (temperature scaling per anggota) dari:
      1. DistilBERT multilingual (fine-tune)   — bobot di model/bert/ atau
                                                 sumber yang dikonfigurasi
      2. TF-IDF + Fitur Angka + Logistic Regression
      3. TF-IDF + Logistic Regression

    Skor akhir -> kebijakan dua ambang (Bagian 10 notebook):
      p <  t_close (0,010)            -> AUTO-CLOSE (tutup otomatis / lolos)
      t_close <= p < t_esc (0,135)    -> REVIEW ANALIS (antrean manusia)
      p >= t_esc                      -> ESKALASI (prioritas tinggi)

Artefak resmi proyek (data/model_operasional.pkl) hanya berisi spesifikasi
ensemble ini; anggota sklearn-nya dibangun ulang persis dari resep notebook
oleh build_artifacts.py dan disimpan sebagai model/sklearn_members.joblib,
sedangkan bobot DistilBERT fine-tune memang tersimpan sejak notebook
(data/bert_snapshot, dibekukan di gerbang memori Bagian 7).

Modul ini TIDAK bergantung pada Streamlit agar bisa diuji berdiri sendiri.
"""

import json
import os
import re
from pathlib import Path

import joblib
import numpy as np

APP_DIR = Path(__file__).resolve().parent
MODEL_DIR = APP_DIR / "model"
SPEC_PATH = MODEL_DIR / "ensemble_spec.json"
SKLEARN_BUNDLE_PATH = MODEL_DIR / "sklearn_members.joblib"

MEMBER_BERT = "DistilBERT multilingual (fine-tune)"
MEMBER_FEATS = "TF-IDF + Fitur Angka + Logistic Regression"
MEMBER_LR = "TF-IDF + Logistic Regression"

FEAT_NAMES = ["n_chars", "n_words", "digit_ratio", "caps_ratio",
              "n_exclaim", "n_links", "n_currency", "n_digits"]
FEAT_LABELS_ID = {
    "n_chars": "panjang pesan (karakter)",
    "n_words": "jumlah kata",
    "digit_ratio": "rasio digit",
    "caps_ratio": "rasio huruf kapital",
    "n_exclaim": "jumlah tanda seru",
    "n_links": "jumlah tautan (http/www)",
    "n_currency": "simbol mata uang (£/$/€)",
    "n_digits": "jumlah digit mentah",
}

ZONES = {
    "AUTO-CLOSE": {
        "label_id": "Tutup Otomatis / Lolos (AUTO-CLOSE)",
        "desc_id": ("Skor di bawah t_close: risiko sangat rendah, pesan ditutup "
                    "tanpa review manusia (dengan QC sampling berkala)."),
    },
    "REVIEW ANALIS": {
        "label_id": "Review Analis — Antrean (REVIEW ANALIS)",
        "desc_id": ("Skor di zona abu-abu: pesan masuk antrean analis untuk "
                    "diputuskan manusia."),
    },
    "ESKALASI": {
        "label_id": "Eskalasi — Prioritas Tinggi (ESKALASI)",
        "desc_id": ("Skor di atas t_esc: presisi zona ini >= 90% di validation; "
                    "tangani sebagai dugaan scam kuat, dahulukan."),
    },
}


# ----------------------------------------------------------------------------
# Resep notebook (disalin persis): fitur angka Bagian 4.6 + temperatur Bagian 2
# ----------------------------------------------------------------------------
def numeric_features(texts):
    rows = []
    for t in texts:
        n = max(len(t), 1)
        rows.append([
            len(t),                                    # n_chars
            len(t.split()),                            # n_words
            sum(ch.isdigit() for ch in t) / n,         # digit_ratio
            sum(ch.isupper() for ch in t) / n,         # caps_ratio
            t.count("!"),                              # n_exclaim
            t.count("http") + t.count("www"),          # n_links
            sum(t.count(s) for s in ["£", "$", "€"]),  # n_currency_symbols
            sum(ch.isdigit() for ch in t),             # n_digits_raw
        ])
    return np.array(rows, dtype=float)


def apply_temperature(p, T):
    eps = 1e-7
    p_clip = np.clip(np.asarray(p, dtype=float), eps, 1 - eps)
    logits = np.log(p_clip / (1 - p_clip))
    return 1.0 / (1.0 + np.exp(-logits / T))


def resolve_bert_source(explicit=None):
    """Tentukan dari mana bobot DistilBERT fine-tune dimuat.

    Urutan: argumen eksplisit -> env BERT_MODEL_PATH -> folder model/bert/
    di app -> folder data/bert_snapshot proyek (mode dev lokal) ->
    env BERT_MODEL_ID (repo Hugging Face). None bila tak ditemukan.
    """
    if explicit:
        return explicit
    env_path = os.environ.get("BERT_MODEL_PATH")
    if env_path:
        return env_path
    local_bert = MODEL_DIR / "bert"
    if (local_bert / "config.json").exists():
        return str(local_bert)
    dev_snapshot = APP_DIR.parent / "data" / "bert_snapshot"
    if (dev_snapshot / "config.json").exists():
        return str(dev_snapshot)
    return os.environ.get("BERT_MODEL_ID")


class TriageEngine:
    """Ensemble terkalibrasi + kebijakan dua ambang, siap saji."""

    def __init__(self, bert_source=None):
        self.spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        self.temps = self.spec["temperatures"]
        self.members = self.spec["members"]
        self.t_close = float(self.spec["t_close"])
        self.t_esc = float(self.spec["t_esc"])
        self.max_len = int(self.spec.get("max_len", 64))

        bundle = joblib.load(SKLEARN_BUNDLE_PATH)
        self.lr_pipe = bundle["lr_pipe"]
        self.feat_vec = bundle["feat_vec"]
        self.scaler = bundle["scaler"]
        self.feats_clf = bundle["feats_clf"]

        src = resolve_bert_source(bert_source)
        if not src:
            raise FileNotFoundError(
                "Bobot DistilBERT fine-tune tidak ditemukan. Taruh di "
                "streamlit-app/model/bert/ (salinan data/bert_snapshot), "
                "atau set BERT_MODEL_PATH / BERT_MODEL_ID. Lihat README.md.")
        self.bert_source = src
        import torch
        from transformers import (AutoModelForSequenceClassification,
                                  AutoTokenizer)
        self._torch = torch
        self.bert_tok = AutoTokenizer.from_pretrained(src)
        self.bert_model = AutoModelForSequenceClassification.from_pretrained(src)
        self.bert_model.eval()

    # -- skor mentah per anggota -------------------------------------------
    def _bert_proba(self, texts, batch=32):
        torch = self._torch
        probs = []
        with torch.no_grad():
            for i in range(0, len(texts), batch):
                enc = self.bert_tok(texts[i:i + batch], padding=True,
                                    truncation=True, max_length=self.max_len,
                                    return_tensors="pt")
                logits = self.bert_model(**enc).logits
                probs.extend(torch.softmax(logits, dim=-1)[:, 1].tolist())
        return np.array(probs)

    def _feats_proba(self, texts):
        from scipy.sparse import csr_matrix, hstack
        Xt = self.feat_vec.transform(texts)
        Xn = self.scaler.transform(numeric_features(texts))
        return self.feats_clf.predict_proba(
            hstack([Xt, csr_matrix(Xn)]).tocsr())[:, 1]

    def member_probs(self, text):
        """Probabilitas mentah (belum dikalibrasi) dari ketiga anggota."""
        return {
            MEMBER_BERT: float(self._bert_proba([text])[0]),
            MEMBER_FEATS: float(self._feats_proba([text])[0]),
            MEMBER_LR: float(self.lr_pipe.predict_proba([text])[0, 1]),
        }

    # -- keputusan lengkap ---------------------------------------------------
    def triage(self, text):
        raw = self.member_probs(text)
        calibrated = {n: float(apply_temperature(np.array([raw[n]]),
                                                 self.temps[n])[0])
                      for n in self.members}
        p = float(np.mean([calibrated[n] for n in self.members]))
        # Temperatur ensemble = 1,0 by design (identitas) — tetap diterapkan
        # lewat spec agar setia pada definisi notebook.
        p = float(apply_temperature(np.array([p]),
                                    float(self.spec.get(
                                        "ensemble_temperature", 1.0)))[0])
        zone = ("AUTO-CLOSE" if p < self.t_close
                else "ESKALASI" if p >= self.t_esc else "REVIEW ANALIS")
        return {
            "text": text,
            "p_scam": p,
            "zone": zone,
            "zone_label": ZONES[zone]["label_id"],
            "zone_desc": ZONES[zone]["desc_id"],
            "member_raw": raw,
            "member_calibrated": calibrated,
            "temperatures": dict(self.temps),
            "factors": self.explain(text),
        }

    # -- penjelasan faktor teks ----------------------------------------------
    def explain(self, text):
        """Faktor yang bisa diaudit: kata pendorong (dari LR) + fitur angka."""
        vec = self.lr_pipe.named_steps["tfidf"]
        clf = self.lr_pipe.named_steps["clf"]
        X = vec.transform([text])
        names = np.array(vec.get_feature_names_out())
        contrib = X.toarray()[0] * clf.coef_[0]
        present = np.nonzero(X.toarray()[0])[0]
        ranked = sorted(present, key=lambda i: contrib[i], reverse=True)
        top_risk = [(names[i], float(contrib[i])) for i in ranked
                    if contrib[i] > 0][:6]
        top_safe = [(names[i], float(contrib[i])) for i in ranked[::-1]
                    if contrib[i] < 0][:6]

        feats = numeric_features([text])[0]
        feat_dict = {n: float(v) for n, v in zip(FEAT_NAMES, feats)}
        notes = []
        if feat_dict["n_links"] > 0:
            notes.append("Mengandung tautan — pola khas smishing.")
        if feat_dict["n_digits"] >= 7:
            notes.append("Banyak digit (nomor telepon / nominal / kode).")
        if feat_dict["digit_ratio"] > 0.15:
            notes.append("Rasio digit tinggi untuk ukuran pesan.")
        if feat_dict["caps_ratio"] > 0.25:
            notes.append("Banyak huruf kapital — gaya 'berteriak' / urgensi.")
        if feat_dict["n_exclaim"] >= 2:
            notes.append("Tanda seru berulang — tekanan urgensi buatan.")
        if re.search(r"(blokir|hangus|sekarang juga|24 jam|menang|undian|"
                     r"hadiah|verifikasi|klaim)", text, re.IGNORECASE):
            notes.append("Ada kata pemicu urgensi / iming-iming / ancaman.")
        return {
            "top_risk_words": top_risk,
            "top_safe_words": top_safe,
            "numeric": feat_dict,
            "numeric_labels": FEAT_LABELS_ID,
            "notes": notes,
        }


def load_engine(bert_source=None):
    return TriageEngine(bert_source=bert_source)
