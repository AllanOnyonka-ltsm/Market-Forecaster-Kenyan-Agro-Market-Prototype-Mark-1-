from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import numpy as np
import pandas as pd

# =========================
# LOAD ARTIFACTS
# =========================
MODEL_PATH = "artifacts/random_forest_price_model.pkl"
ENCODER_PATH = "artifacts/label_encoders.pkl"
FEATURES_PATH = "artifacts/feature_columns.pkl"
PREPROCESS_PATH = "artifacts/preprocessing_info.pkl"

model = joblib.load(MODEL_PATH)
label_encoders = joblib.load(ENCODER_PATH)
feature_columns = joblib.load(FEATURES_PATH)
preprocess_info = joblib.load(PREPROCESS_PATH)

# =========================
# BUSINESS RULES (LOCKED)
# =========================
CROP_THRESHOLDS = {
    "cabbage": 126,
    "kale": 50,
    "onion": 13,
    "potatoes": 50,
    "tomatoes": 64
}

ALLOWED_COMMODITIES = set(CROP_THRESHOLDS.keys())

# =========================
# API SCHEMA
# =========================
class PredictRequest(BaseModel):
    date: str
    admin1: str
    market: str
    commodity: str
    pricetype: str   # retail or wholesale
    previous_month_price: float

class PredictResponse(BaseModel):
    commodity: str
    market: str
    date: str
    prediction_per_kg: float
    unit: str
    market_type: str
    previous_month_price: float
    confidence_pct: float
    error_margin: str
    lower_bound: float
    upper_bound: float
    unreasonable: bool
    note: str

# =========================
# INIT APP
# =========================
app = FastAPI(title="Hackathon Price Prediction API")

# =========================
# HELPER: BUILD FEATURE VECTOR
# =========================
def build_feature_vector(req: PredictRequest):
    data = {}

    # Rebuild minimum core features (extend if needed)
    data["price_lag_1"] = req.previous_month_price

    data["commodity"] = req.commodity
    data["market"] = req.market
    data["admin1"] = req.admin1
    data["pricetype"] = req.pricetype

    # Apply label encoding
    for col in preprocess_info["categorical_columns"]:
        if col in data:
            encoder = label_encoders[col]
            data[col] = int(encoder.transform([data[col]])[0])

    # Build final vector in correct order
    final_vector = []
    for col in feature_columns:
        final_vector.append(data.get(col, 0))

    return np.array(final_vector).reshape(1, -1)

# =========================
# HELPER: RF CONFIDENCE
# =========================
def rf_confidence(model, X):
    tree_preds = np.array([tree.predict(X)[0] for tree in model.estimators_])
    mean = tree_preds.mean()
    low = np.percentile(tree_preds, 5)
    high = np.percentile(tree_preds, 95)
    confidence = 0.90
    return mean, low, high, confidence

# =========================
# MAIN ENDPOINT
# =========================
@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):

    commodity = req.commodity.lower()

    if commodity not in ALLOWED_COMMODITIES:
        raise HTTPException(
            status_code=400,
            detail=f"Commodity '{commodity}' not supported."
        )

    X = build_feature_vector(req)

    pred, lo, hi, conf = rf_confidence(model, X)

    threshold = CROP_THRESHOLDS[commodity]
    unreasonable = pred > threshold

    note = "Prediction within normal range."
    if unreasonable:
        note = f"⚠️ Unreasonable: exceeds normal threshold of {threshold} per kg."

    return {
        "commodity": req.commodity,
        "market": req.market,
        "date": req.date,
        "prediction_per_kg": round(pred, 2),
        "unit": "kg",
        "market_type": req.pricetype,
        "previous_month_price": req.previous_month_price,
        "confidence_pct": conf * 100,
        "error_margin": f"+-{round((hi - pred), 2)}",
        "lower_bound": round(lo, 2),
        "upper_bound": round(hi, 2),
        "unreasonable": unreasonable,
        "note": note
    }
