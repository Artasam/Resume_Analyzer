"""
re_save_models.py
─────────────────
Run this once to re-save your pickled models using the currently installed
scikit-learn version, eliminating InconsistentVersionWarning on every reload.

Usage:
    python re_save_models.py
"""

import pickle
import os

MODEL_DIR = "models"

files = {
    "lr_model.pkl": "Logistic Regression",
    "tfidf.pkl":    "TF-IDF Vectorizer",
    "encoder.pkl":  "Label Encoder",
}

print("Re-saving models with current scikit-learn version...\n")

for filename, label in files.items():
    path = os.path.join(MODEL_DIR, filename)
    if not os.path.exists(path):
        print(f"  ⚠  Skipped — not found: {path}")
        continue

    # Load with the old version (warnings expected here, only this once)
    with open(path, "rb") as f:
        obj = pickle.load(f)

    # Re-save in place using current sklearn
    with open(path, "wb") as f:
        pickle.dump(obj, f)

    print(f"  ✅  {label:30s} → {path}")

print("\nDone. Restart your Streamlit app — no more version warnings.")