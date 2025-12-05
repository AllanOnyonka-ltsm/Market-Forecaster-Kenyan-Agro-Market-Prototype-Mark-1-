from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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

# Mapping for common variations and plurals
COMMODITY_ALIASES = {
    "onions": "onion",
    "potato": "potatoes",
    "irish potato": "potatoes",
    "irish potatoes": "potatoes",
    "tomato": "tomatoes",
    "cabbage": "cabbage",
    "cabbages": "cabbage",
    "kale": "kale",
    "kales": "kale",
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

# Add CORS middleware to allow requests from web browsers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins - restrict this in production
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Allows all headers
)

# =========================
# HELPER: NORMALIZE INPUT
# =========================
def normalize_input(req: PredictRequest):
    """Normalize user input to match training data format (case-insensitive)"""
    
    # Capitalize commodity (e.g., "tomatoes" -> "Tomatoes", "TOMATOES" -> "Tomatoes")
    commodity = req.commodity.strip().title()
    
    # Capitalize pricetype (e.g., "retail" -> "Retail", "RETAIL" -> "Retail")
    pricetype = req.pricetype.strip().capitalize()
    
    # Normalize market: try to find case-insensitive match from label encoders
    market = req.market.strip()
    encoder_market = label_encoders.get("market")
    if encoder_market:
        # Find case-insensitive match
        for valid_market in encoder_market.classes_:
            if valid_market.lower() == market.lower():
                market = valid_market
                break
    
    # Normalize admin1: try to find case-insensitive match from label encoders
    admin1 = req.admin1.strip()
    encoder_admin1 = label_encoders.get("admin1")
    if encoder_admin1:
        # Find case-insensitive match
        for valid_admin1 in encoder_admin1.classes_:
            if valid_admin1.lower() == admin1.lower():
                admin1 = valid_admin1
                break
    
    return commodity, market, admin1, pricetype

# =========================
# HELPER: BUILD FEATURE VECTOR
# =========================
def build_feature_vector(req: PredictRequest):
    data = {}

    # Normalize inputs
    commodity, market, admin1, pricetype = normalize_input(req)
    
    # Rebuild minimum core features (extend if needed)
    data["price_lag_1"] = req.previous_month_price

    data["commodity"] = commodity
    data["market"] = market
    data["admin1"] = admin1
    data["pricetype"] = pricetype

    # Apply label encoding with error handling
    for col in preprocess_info["categorical_columns"]:
        if col in data:
            encoder = label_encoders[col]
            try:
                data[col] = int(encoder.transform([data[col]])[0])
            except ValueError:
                valid_values = list(encoder.classes_)
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid {col}: '{data[col]}'. Valid values: {valid_values}"
                )

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
# ROOT ENDPOINT
# =========================
@app.get("/")
def root():
    return {
        "message": "Kenyan Agro Market Price Prediction API",
        "endpoints": {
            "/predict": "POST - Make price predictions",
            "/docs": "GET - Interactive API documentation",
            "/redoc": "GET - Alternative API documentation"
        },
        "example_request": {
            "date": "2025-12-05",
            "admin1": "Nairobi",
            "market": "Gikomba",
            "commodity": "cabbage",
            "pricetype": "retail",
            "previous_month_price": 100.0
        },
        "supported_commodities": list(ALLOWED_COMMODITIES)
    }

# =========================
# MAIN ENDPOINT
# =========================
@app.get("/predict")
def predict_info():
    """GET request to /predict - shows how to use the endpoint"""
    return {
        "error": "Method Not Allowed",
        "message": "This endpoint only accepts POST requests",
        "usage": {
            "method": "POST",
            "url": "/predict",
            "content_type": "application/json",
            "example_request": {
                "date": "2025-12-05",
                "admin1": "Nairobi",
                "market": "Wakulima (Nairobi)",
                "commodity": "cabbage",
                "pricetype": "retail",
                "previous_month_price": 100.0
            }
        },
        "interactive_docs": "/docs",
        "supported_commodities": list(ALLOWED_COMMODITIES)
    }

# =========================
# MAIN ENDPOINT
# =========================
@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    # Fallback: If request is missing or missing fields, return dummy data and example
    import inspect
    from fastapi import Request
    from fastapi.responses import JSONResponse
    import typing

    # Check for missing fields
    required_fields = ["date", "admin1", "market", "commodity", "pricetype", "previous_month_price"]
    missing_fields = []
    example_input = {
        "date": "2025-12-05",
        "admin1": "Nairobi",
        "market": "Wakulima (Nairobi)",
        "commodity": "tomatoes",
        "pricetype": "retail",
        "previous_month_price": 58.2
    }
    example_output = {
        "commodity": "tomatoes",
        "market": "Wakulima (Nairobi)",
        "date": "2025-12-05",
        "prediction_per_kg": 163.64,
        "unit": "kg",
        "market_type": "retail",
        "previous_month_price": 58.2,
        "confidence_pct": 90.0,
        "error_margin": "+-342.74",
        "lower_bound": 5.0,
        "upper_bound": 506.38,
        "unreasonable": True,
        "note": "\u26a0\ufe0f Unreasonable: exceeds normal threshold of 64 per kg."
    }

    # If req is None (shouldn't happen in FastAPI), or is missing fields, fallback
    if req is None or any(getattr(req, f, None) is None for f in required_fields):
        return JSONResponse(
            status_code=422,
            content={
                "error": "Missing required fields in request body.",
                "required_fields": required_fields,
                "example_input": example_input,
                "example_output": example_output,
                "message": "Please provide all required fields as shown in example_input to get a valid prediction."
            }
        )

    # Normalize and validate commodity (with alias support for plurals)
    commodity_normalized = req.commodity.strip().lower()
    
    # Check if it's an alias (e.g., "onions" -> "onion")
    if commodity_normalized in COMMODITY_ALIASES:
        commodity_normalized = COMMODITY_ALIASES[commodity_normalized]

    if commodity_normalized not in ALLOWED_COMMODITIES:
        return JSONResponse(
            status_code=400,
            content={
                "error": f"Commodity '{req.commodity}' not supported.",
                "allowed": list(ALLOWED_COMMODITIES),
                "aliases": COMMODITY_ALIASES,
                "note": "Plurals and common variations are automatically handled (e.g., 'onions' → 'onion')",
                "example_input": example_input
            }
        )

    X = build_feature_vector(req)

    pred, lo, hi, conf = rf_confidence(model, X)

    threshold = CROP_THRESHOLDS[commodity_normalized]
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
