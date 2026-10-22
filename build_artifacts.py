# -*- coding: utf-8 -*-
"""Bangun artefak deploy untuk aplikasi Streamlit Fraud Triage.

Konteks (dari notebook fraud-triage-laya-vs-ml-dl.ipynb, Bagian 13.5):
artefak resmi proyek `data/model_operasional.pkl` BUKAN model yang bisa
dijalankan — isinya hanya spesifikasi ensemble (nama anggota + temperatur
anggota), karena ensemble notebook "disajikan" dari anggota yang hidup di
memori kernel. Skrip ini merekonstruksi anggota-anggotanya persis seperti
di notebook, lalu memverifikasi skornya terhadap angka resmi notebook:

  1. TF-IDF + Logistic Regression            (pipeline sklearn, dilatih ulang
                                              dari split yang sama persis)
  2. TF-IDF + Fitur Angka + Logistic Regression (dilatih ulang, resep sama)
  3. DistilBERT multilingual (fine-tune)     (bobot SUDAH tersimpan di
                                              data/bert_snapshot — dibekukan
                                              notebook di gerbang memori
                                              Bagian 7; skrip ini hanya
                                              memuat & memverifikasinya)

Verifikasi (PR-AUC validation / test, target dari output notebook):
  LR 0,968 | Fitur 0,969 | BERT 0,978 | Ensemble val 0,982 | Ensemble test 0,986

Keluaran (di folder streamlit-app/model/):
  sklearn_members.joblib  — lr_pipe + (feat_vec, scaler, feats_clf)
  ensemble_spec.json      — anggota, temperatur, ambang kebijakan, MAX_LEN
  model_operasional.pkl   — salinan spesifikasi resmi proyek (provenance)

Jalankan dari folder proyek:  ../.venv/bin/python build_artifacts.py
(butuh file data/sms_spam_collection.zip + data/bert_snapshot di proyek)
"""

import json
import pickle
import re
import sys
import zipfile
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
MODEL_DIR = APP_DIR / "model"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42
MAX_LEN = 64  # sama seperti notebook Bagian 5 (SMS pendek)

# Target verifikasi — angka resmi dari output notebook yang tereksekusi.
TARGETS = {
    "lr_val": 0.968,
    "feats_val": 0.969,
    "bert_val": 0.978,
    "ens_val": 0.982,
    "ens_test": 0.986,
}
TOL = 0.003  # toleransi selisih PR-AUC (perbedaan versi library yang wajar)


# ----------------------------------------------------------------------------
# Resep data — disalin persis dari notebook Bagian 1 (dedup + split 60/20/20)
# ----------------------------------------------------------------------------
def load_splits():
    with zipfile.ZipFile(PROJECT_DIR / "data" / "sms_spam_collection.zip") as z:
        with z.open("SMSSpamCollection") as f:
            df = pd.read_csv(f, sep="\t", header=None,
                             names=["label", "text"], encoding="utf-8")
    df["y"] = (df["label"] == "spam").astype(int)
    df_clean = df.drop_duplicates(subset="text").reset_index(drop=True)

    from sklearn.model_selection import train_test_split
    df_trainval, df_test = train_test_split(
        df_clean, test_size=0.20, random_state=SEED, stratify=df_clean["y"])
    df_train, df_val = train_test_split(
        df_trainval, test_size=0.25, random_state=SEED, stratify=df_trainval["y"])

    splits = {}
    for name, part in [("train", df_train), ("val", df_val), ("test", df_test)]:
        splits[f"X_{name}"] = part["text"].tolist()
        splits[f"y_{name}"] = part["y"].to_numpy()
    return splits


# ----------------------------------------------------------------------------
# Fitur angka — disalin persis dari notebook Bagian 4.6
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


# ----------------------------------------------------------------------------
# Kalibrasi temperatur — rumus yang sama seperti notebook Bagian 2
# ----------------------------------------------------------------------------
def apply_temperature(p, T):
    eps = 1e-7
    p_clip = np.clip(np.asarray(p, dtype=float), eps, 1 - eps)
    logits = np.log(p_clip / (1 - p_clip))
    return 1.0 / (1.0 + np.exp(-logits / T))


def main():
    from scipy.sparse import csr_matrix, hstack
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import average_precision_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    print("== 1. Muat data & split (resep notebook Bagian 1) ==")
    s = load_splits()
    X_train, y_train = s["X_train"], s["y_train"]
    X_val, y_val, X_test, y_test = s["X_val"], s["y_val"], s["X_test"], s["y_test"]
    print(f"   train={len(X_train)} val={len(X_val)} test={len(X_test)}")

    print("== 2. Latih ulang dua anggota sklearn (resep notebook Bagian 3 & 4.6) ==")
    # Anggota A: TF-IDF + Logistic Regression (pipeline persis notebook).
    # (Remediasi Bagian 4.7 hanya menyentuh GBM dan tidak membaik -> LR asli.)
    lr_pipe = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)),
        ("clf", LogisticRegression(max_iter=1000, C=1.0)),
    ])
    lr_pipe.fit(X_train, y_train)
    p_val_lr = lr_pipe.predict_proba(X_val)[:, 1]

    # Anggota B: TF-IDF + Fitur Angka + Logistic Regression.
    feat_vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    Xtr_text = feat_vec.fit_transform(X_train)
    scaler = StandardScaler()
    Xtr_num = scaler.fit_transform(numeric_features(X_train))
    feats_clf = LogisticRegression(max_iter=1000, C=1.0)
    feats_clf.fit(hstack([Xtr_text, csr_matrix(Xtr_num)]).tocsr(), y_train)

    def feats_predict_proba(texts):
        Xt = feat_vec.transform(texts)
        Xn = scaler.transform(numeric_features(texts))
        return feats_clf.predict_proba(hstack([Xt, csr_matrix(Xn)]).tocsr())[:, 1]

    p_val_feats = feats_predict_proba(X_val)
    p_test_lr = lr_pipe.predict_proba(X_test)[:, 1]
    p_test_feats = feats_predict_proba(X_test)

    print("== 3. Muat DistilBERT fine-tune dari data/bert_snapshot ==")
    import torch
    from transformers import (AutoModelForSequenceClassification,
                              AutoTokenizer)
    bert_src = PROJECT_DIR / "data" / "bert_snapshot"
    bert_tok = AutoTokenizer.from_pretrained(str(bert_src))
    bert_model = AutoModelForSequenceClassification.from_pretrained(str(bert_src))
    bert_model.eval()

    def bert_predict_proba(texts, batch=32):
        probs = []
        with torch.no_grad():
            for i in range(0, len(texts), batch):
                enc = bert_tok(texts[i:i + batch], padding=True, truncation=True,
                               max_length=MAX_LEN, return_tensors="pt")
                logits = bert_model(**enc).logits
                probs.extend(torch.softmax(logits, dim=-1)[:, 1].tolist())
        return np.array(probs)

    p_val_bert = bert_predict_proba(X_val)
    p_test_bert = bert_predict_proba(X_test)

    print("== 4. Verifikasi terhadap angka resmi notebook ==")
    # Spesifikasi ensemble resmi: baca dari artefak proyek.
    with open(PROJECT_DIR / "data" / "model_operasional.pkl", "rb") as f:
        spec_official = pickle.load(f)
    temps = spec_official["temperatures"]
    members = spec_official["members"]
    print(f"   Anggota resmi: {members}")
    print(f"   Temperatur resmi: {temps}")

    raw_val = {
        "TF-IDF + Logistic Regression": p_val_lr,
        "TF-IDF + Fitur Angka + Logistic Regression": p_val_feats,
        "DistilBERT multilingual (fine-tune)": p_val_bert,
    }
    raw_test = {
        "TF-IDF + Logistic Regression": p_test_lr,
        "TF-IDF + Fitur Angka + Logistic Regression": p_test_feats,
        "DistilBERT multilingual (fine-tune)": p_test_bert,
    }
    ens_val = np.mean([apply_temperature(raw_val[n], temps[n]) for n in members], axis=0)
    ens_test = np.mean([apply_temperature(raw_test[n], temps[n]) for n in members], axis=0)

    got = {
        "lr_val": average_precision_score(y_val, p_val_lr),
        "feats_val": average_precision_score(y_val, p_val_feats),
        "bert_val": average_precision_score(y_val, p_val_bert),
        "ens_val": average_precision_score(y_val, ens_val),
        "ens_test": average_precision_score(y_test, ens_test),
    }
    ok = True
    for k, target in TARGETS.items():
        diff = abs(got[k] - target)
        flag = "OK " if diff <= TOL else "SELISIH BESAR"
        if diff > TOL:
            ok = False
        print(f"   {flag} {k:10s}: hitung={got[k]:.3f} target notebook={target:.3f} (selisih {diff:.4f})")
    if not ok:
        print("!! Verifikasi gagal — artefak TIDAK ditulis. Selidiki sebelum deploy.")
        sys.exit(1)

    print("== 5. Tulis artefak deploy ==")
    joblib.dump(
        {"lr_pipe": lr_pipe, "feat_vec": feat_vec,
         "scaler": scaler, "feats_clf": feats_clf},
        MODEL_DIR / "sklearn_members.joblib",
    )
    spec = {
        "kind": "ensemble",
        "chosen_name": "Ensemble (Top-3 Terkalibrasi)",
        "members": members,
        "temperatures": temps,
        "ensemble_temperature": 1.0,   # identitas by design (notebook Bagian 8.5)
        "t_close": 0.010,              # kebijakan Bagian 10 notebook
        "t_esc": 0.135,
        "max_len": MAX_LEN,
        "bert_base": "distilbert/distilbert-base-multilingual-cased",
    }
    (MODEL_DIR / "ensemble_spec.json").write_text(
        json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
    # Salinan spesifikasi resmi proyek untuk provenance.
    (MODEL_DIR / "model_operasional.pkl").write_bytes(
        (PROJECT_DIR / "data" / "model_operasional.pkl").read_bytes())
    print(f"   tertulis: {MODEL_DIR / 'sklearn_members.joblib'}")
    print(f"   tertulis: {MODEL_DIR / 'ensemble_spec.json'}")
    print(f"   tertulis: {MODEL_DIR / 'model_operasional.pkl'} (salinan spesifikasi resmi)")
    print("SELESAI — semua angka cocok dengan notebook.")


if __name__ == "__main__":
    main()
