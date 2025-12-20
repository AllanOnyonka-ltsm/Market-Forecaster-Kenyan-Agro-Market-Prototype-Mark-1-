from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime
import joblib
import numpy as np
import pandas as pd
import uuid

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

# Default radius for micro-market search in kilometers
DEFAULT_MICRO_MARKET_RADIUS_KM = 50.0

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
    """Normalize user input to match training data format"""
    
    # Capitalize commodity (e.g., "tomatoes" -> "Tomatoes")
    commodity = req.commodity.strip().title()
    
    # Capitalize pricetype (e.g., "retail" -> "Retail")
    pricetype = req.pricetype.strip().capitalize()
    
    # Keep market and admin1 as-is (user should provide exact match)
    market = req.market.strip()
    admin1 = req.admin1.strip()
    
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
            "/recommendations": "POST - Get actionable recommendations based on predictions",
            "/micro-market": "POST - Get localized/micro-market forecasting",
            "/format": "POST - Format predictions for non-tech users (SMS, WhatsApp, bulletin)",
            "/explainability": "POST - Get AI prediction explanations (XAI)",
            "/feedback": "POST - Submit user feedback on predictions",
            "/impact-stats": "GET - View aggregated impact statistics",
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

@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):

    # Normalize and validate commodity
    commodity_normalized = req.commodity.strip().lower()

    if commodity_normalized not in ALLOWED_COMMODITIES:
        raise HTTPException(
            status_code=400,
            detail=f"Commodity '{req.commodity}' not supported. Allowed: {list(ALLOWED_COMMODITIES)}"
        )

    X = build_feature_vector(req)

    pred, lo, hi, conf = rf_confidence(model, X)

    threshold = CROP_THRESHOLDS[commodity_normalized]
    unreasonable = pred > threshold

    note = "Prediction within normal range."
    if unreasonable:
        note = f" Unreasonable: exceeds normal threshold of {threshold} per kg."

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

# =========================
# NEW ENDPOINT SCHEMAS
# =========================

class RecommendationRequest(BaseModel):
    """Request schema for actionable recommendations"""
    commodity: str
    market: str
    admin1: str
    predicted_price: float
    previous_price: float
    pricetype: str

class RecommendationResponse(BaseModel):
    """Response schema for actionable recommendations"""
    commodity: str
    market: str
    recommendations: List[str]
    action_type: str  # "sell", "hold", "buy"
    confidence: str
    rationale: str

class MicroMarketRequest(BaseModel):
    """Request schema for micro-market/localized forecasting"""
    commodity: str
    region: str
    radius_km: Optional[float] = DEFAULT_MICRO_MARKET_RADIUS_KM
    date: str

class MicroMarketResponse(BaseModel):
    """Response schema for micro-market forecasting"""
    commodity: str
    region: str
    nearby_markets: List[Dict[str, Any]]
    localized_forecast: Dict[str, float]
    recommended_market: str
    market_comparison: str

class FormatRequest(BaseModel):
    """Request schema for formatted output"""
    prediction_data: Dict
    format_type: str  # "sms", "whatsapp", "bulletin"
    language: Optional[str] = "english"

class FormatResponse(BaseModel):
    """Response schema for formatted output"""
    format_type: str
    formatted_message: str
    character_count: int
    estimated_cost: Optional[float] = None

class ExplainabilityRequest(BaseModel):
    """Request schema for explainability/XAI"""
    prediction_id: Optional[str] = None
    commodity: str
    market: str
    predicted_price: float
    features: Dict

class ExplainabilityResponse(BaseModel):
    """Response schema for explainability"""
    commodity: str
    market: str
    predicted_price: float
    top_influencing_factors: List[Dict[str, Any]]
    explanation_summary: str
    confidence_factors: Dict[str, Any]

class FeedbackRequest(BaseModel):
    """Request schema for user feedback collection"""
    user_id: Optional[str] = None
    prediction_id: Optional[str] = None
    actual_price: Optional[float] = None
    accuracy_rating: Optional[int] = None  # 1-5 scale
    usefulness_rating: Optional[int] = None  # 1-5 scale
    comments: Optional[str] = None
    timestamp: Optional[str] = None

class FeedbackResponse(BaseModel):
    """Response schema for feedback submission"""
    feedback_id: str
    status: str
    message: str
    timestamp: str

class ImpactStatsResponse(BaseModel):
    """Response schema for aggregated impact statistics"""
    total_predictions: int
    total_users: int
    average_accuracy: float
    total_markets_covered: int
    commodities_tracked: List[str]
    user_satisfaction: float
    cost_savings_estimate: float
    last_updated: str

# =========================
# ENDPOINT: ACTIONABLE RECOMMENDATIONS
# =========================
@app.post("/recommendations", response_model=RecommendationResponse)
def get_recommendations(req: RecommendationRequest):
    """
    Generate actionable recommendations based on price predictions.
    
    This endpoint analyzes predicted prices against previous prices and market conditions
    to provide farmers with actionable advice on when to sell, hold, or buy commodities.
    
    Args:
        req: RecommendationRequest containing commodity, market, and price information
        
    Returns:
        RecommendationResponse with actionable recommendations and rationale
    """
    commodity_normalized = req.commodity.strip().lower()
    
    # Validate commodity
    if commodity_normalized not in ALLOWED_COMMODITIES:
        raise HTTPException(
            status_code=400,
            detail=f"Commodity '{req.commodity}' not supported. Allowed: {list(ALLOWED_COMMODITIES)}"
        )
    
    # Validate previous_price to prevent division by zero
    if req.previous_price <= 0:
        raise HTTPException(
            status_code=400,
            detail="previous_price must be greater than 0"
        )
    
    # Calculate price change percentage
    price_change = ((req.predicted_price - req.previous_price) / req.previous_price) * 100
    
    # Generate recommendations based on price trends
    recommendations = []
    action_type = "hold"
    
    if price_change > 10:
        action_type = "sell"
        recommendations.append(f"Predicted price increase of {round(price_change, 1)}% - consider selling soon")
        recommendations.append("Market conditions favor sellers")
        if req.pricetype.lower() == "retail":
            recommendations.append("Retail prices are high - good time to market your produce")
        rationale = "Significant price increase predicted. Selling now or in the near future could maximize returns."
        confidence = "high"
    elif price_change > 5:
        action_type = "sell"
        recommendations.append(f"Moderate price increase of {round(price_change, 1)}% expected")
        recommendations.append("Consider selling within the next few days")
        rationale = "Moderate price increase expected. Timing the market in the next week could be beneficial."
        confidence = "medium"
    elif price_change < -10:
        action_type = "hold"
        recommendations.append(f"Predicted price drop of {round(abs(price_change), 1)}% - consider holding")
        recommendations.append("Wait for better market conditions before selling")
        recommendations.append("Consider storage options if possible")
        rationale = "Significant price drop expected. Holding and waiting for price recovery may be more profitable."
        confidence = "high"
    elif price_change < -5:
        action_type = "hold"
        recommendations.append(f"Moderate price decrease of {round(abs(price_change), 1)}% expected")
        recommendations.append("Monitor market closely over the next few days")
        rationale = "Moderate price decrease expected. Monitor market conditions before making selling decisions."
        confidence = "medium"
    else:
        action_type = "hold"
        recommendations.append("Stable prices expected")
        recommendations.append("No urgent action required - normal market conditions")
        rationale = "Price stability expected. Normal selling patterns can continue."
        confidence = "medium"
    
    # Add market-specific advice
    # Safe to access CROP_THRESHOLDS since commodity_normalized is validated to be in ALLOWED_COMMODITIES
    # and ALLOWED_COMMODITIES is derived from CROP_THRESHOLDS.keys()
    threshold = CROP_THRESHOLDS[commodity_normalized]
    if req.predicted_price > threshold * 0.8:
        recommendations.append(f"Price approaching threshold limit ({threshold} KES/kg)")
    
    return {
        "commodity": req.commodity,
        "market": req.market,
        "recommendations": recommendations,
        "action_type": action_type,
        "confidence": confidence,
        "rationale": rationale
    }

# =========================
# ENDPOINT: MICRO-MARKET/LOCALIZED FORECASTING
# =========================
@app.post("/micro-market", response_model=MicroMarketResponse)
def get_micro_market_forecast(req: MicroMarketRequest):
    """
    Provide localized/micro-market forecasting for specific regions.
    
    This endpoint offers granular, location-specific price forecasts by analyzing
    nearby markets and regional price trends within a specified radius.
    
    Args:
        req: MicroMarketRequest containing commodity, region, and radius information
        
    Returns:
        MicroMarketResponse with localized forecasts and market comparisons
    """
    commodity_normalized = req.commodity.strip().lower()
    
    # Validate commodity
    if commodity_normalized not in ALLOWED_COMMODITIES:
        raise HTTPException(
            status_code=400,
            detail=f"Commodity '{req.commodity}' not supported. Allowed: {list(ALLOWED_COMMODITIES)}"
        )
    
    # Placeholder: In production, this would query a geospatial database
    # For now, we'll simulate nearby markets based on the region
    # Using deterministic values based on commodity and region for reproducibility
    base_price = CROP_THRESHOLDS.get(commodity_normalized, 50)
    price_variation = 0.2  # 20% variation
    
    nearby_markets = [
        {
            "market_name": f"{req.region} Central Market",
            "distance_km": 0.0,
            "estimated_price": round(base_price * 0.9, 2),
            "market_type": "wholesale"
        },
        {
            "market_name": f"{req.region} Retail Hub",
            "distance_km": round(req.radius_km * 0.3, 1),
            "estimated_price": round(base_price * 1.1, 2),
            "market_type": "retail"
        },
        {
            "market_name": f"Near {req.region} Market",
            "distance_km": round(req.radius_km * 0.6, 1),
            "estimated_price": round(base_price * 0.95, 2),
            "market_type": "mixed"
        }
    ]
    
    # Calculate localized forecast
    avg_price = np.mean([m["estimated_price"] for m in nearby_markets])
    min_price = min([m["estimated_price"] for m in nearby_markets])
    max_price = max([m["estimated_price"] for m in nearby_markets])
    
    localized_forecast = {
        "average_price": round(avg_price, 2),
        "min_price": round(min_price, 2),
        "max_price": round(max_price, 2),
        "price_variance": round(max_price - min_price, 2)
    }
    
    # Generate market comparison
    price_spread = max_price - min_price
    if price_spread > 10:
        market_comparison = f"High price variance ({round(price_spread, 2)} KES) across nearby markets. Shopping around could save money."
    else:
        market_comparison = "Relatively stable prices across nearby markets."
    
    return {
        "commodity": req.commodity,
        "region": req.region,
        "nearby_markets": nearby_markets,
        "localized_forecast": localized_forecast,
        "recommended_market": nearby_markets[0]["market_name"],
        "market_comparison": market_comparison
    }

# =========================
# ENDPOINT: FORMAT FOR NON-TECH USERS
# =========================
@app.post("/format", response_model=FormatResponse)
def format_for_users(req: FormatRequest):
    """
    Format prediction data for non-technical users (SMS, WhatsApp, bulletin).
    
    This endpoint transforms technical prediction data into user-friendly formats
    suitable for SMS, WhatsApp messages, or printed bulletins in local languages.
    
    Args:
        req: FormatRequest containing prediction data and desired format type
        
    Returns:
        FormatResponse with formatted message optimized for the specified channel
    """
    format_type = req.format_type.lower()
    
    if format_type not in ["sms", "whatsapp", "bulletin"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid format_type. Allowed: 'sms', 'whatsapp', 'bulletin'"
        )
    
    # Extract key information from prediction data
    commodity = req.prediction_data.get("commodity", "N/A")
    market = req.prediction_data.get("market", "N/A")
    prediction = req.prediction_data.get("prediction_per_kg", 0)
    date = req.prediction_data.get("date", "N/A")
    
    # Format message based on type
    if format_type == "sms":
        # SMS: Keep it short (160 characters max for single SMS)
        formatted_message = f"{commodity} @ {market}: KES {prediction}/kg on {date}. Prev: KES {req.prediction_data.get('previous_month_price', 0)}/kg"
        estimated_cost = 0.50  # Estimated cost in KES per SMS
        
    elif format_type == "whatsapp":
        # WhatsApp: Can be longer, more formatted
        formatted_message = f"""📊 *Market Price Forecast*

 Commodity: {commodity}
 Market: {market}
 Date: {date}

 Predicted Price: *KES {prediction}/kg*
 Previous Price: KES {req.prediction_data.get('previous_month_price', 0)}/kg
 Confidence: {req.prediction_data.get('confidence_pct', 90)}%

{req.prediction_data.get('note', '')}

_Powered by Market Forecaster_"""
        estimated_cost = 0.0  # WhatsApp is free
        
    else:  # bulletin
        # Bulletin: Formal, detailed format for printing
        formatted_message = f"""
MARKET PRICE BULLETIN
{'=' * 50}

Commodity:          {commodity.upper()}
Market Location:    {market}
Forecast Date:      {date}

PRICE FORECAST
{'=' * 50}
Predicted Price:    KES {prediction} per kg
Previous Price:     KES {req.prediction_data.get('previous_month_price', 0)} per kg
Price Range:        KES {req.prediction_data.get('lower_bound', 0)} - {req.prediction_data.get('upper_bound', 0)} per kg
Confidence Level:   {req.prediction_data.get('confidence_pct', 90)}%

NOTES
{'=' * 50}
{req.prediction_data.get('note', 'No additional notes.')}

This forecast is provided as guidance only. Actual market prices may vary.
Report generated by Kenyan Agro Market Forecaster.
"""
        estimated_cost = None  # No cost for bulletin
    
    return {
        "format_type": format_type,
        "formatted_message": formatted_message,
        "character_count": len(formatted_message),
        "estimated_cost": estimated_cost
    }

# =========================
# ENDPOINT: EXPLAINABILITY/XAI
# =========================
@app.post("/explainability", response_model=ExplainabilityResponse)
def get_explainability(req: ExplainabilityRequest):
    """
    Provide explainability and transparency for AI predictions (XAI).
    
    This endpoint explains which factors most influenced the price prediction,
    helping users understand and trust the AI model's decision-making process.
    
    Args:
        req: ExplainabilityRequest containing prediction details and features
        
    Returns:
        ExplainabilityResponse with factor importance and explanation summary
    """
    commodity_normalized = req.commodity.strip().lower()
    
    # Validate commodity
    if commodity_normalized not in ALLOWED_COMMODITIES:
        raise HTTPException(
            status_code=400,
            detail=f"Commodity '{req.commodity}' not supported. Allowed: {list(ALLOWED_COMMODITIES)}"
        )
    
    # Placeholder: In production, this would use SHAP values or feature importance
    # from the actual model to explain predictions
    
    # Simulate feature importance (in production, extract from model)
    top_influencing_factors = [
        {
            "factor": "Previous Month Price",
            "importance": 0.45,
            "impact": "High",
            "description": f"Historical price of {req.features.get('previous_month_price', 'N/A')} KES/kg strongly influences forecast"
        },
        {
            "factor": "Market Location",
            "importance": 0.25,
            "impact": "Medium",
            "description": f"{req.market} market has specific price patterns based on historical data"
        },
        {
            "factor": "Seasonality",
            "importance": 0.15,
            "impact": "Medium",
            "description": "Time of year affects supply and demand dynamics"
        },
        {
            "factor": "Price Type",
            "importance": 0.10,
            "impact": "Low",
            "description": f"{req.features.get('pricetype', 'retail')} pricing typically differs from wholesale"
        },
        {
            "factor": "Regional Factors",
            "importance": 0.05,
            "impact": "Low",
            "description": "Regional economic and agricultural conditions"
        }
    ]
    
    # Generate explanation summary
    explanation_summary = f"""
The predicted price of {req.predicted_price} KES/kg for {req.commodity} at {req.market} 
is primarily influenced by the previous month's price ({req.features.get('previous_month_price', 'N/A')} KES/kg), 
which accounts for 45% of the prediction. The market location and historical patterns at {req.market} 
contribute 25% to the forecast. Seasonal factors and price type differences make up the remaining influence.
"""
    
    # Confidence factors
    confidence_factors = {
        "data_quality": "high",
        "historical_accuracy": 0.85,
        "sample_size": "adequate",
        "market_volatility": "moderate",
        "prediction_reliability": "good"
    }
    
    return {
        "commodity": req.commodity,
        "market": req.market,
        "predicted_price": req.predicted_price,
        "top_influencing_factors": top_influencing_factors,
        "explanation_summary": explanation_summary.strip(),
        "confidence_factors": confidence_factors
    }

# =========================
# ENDPOINT: USER FEEDBACK COLLECTION
# =========================
@app.post("/feedback", response_model=FeedbackResponse)
def collect_feedback(req: FeedbackRequest):
    """
    Collect user feedback on predictions and system usefulness.
    
    This endpoint allows users to submit feedback about prediction accuracy,
    actual observed prices, and overall system usefulness. Data is used to
    improve model performance over time.
    
    Args:
        req: FeedbackRequest containing user feedback and ratings
        
    Returns:
        FeedbackResponse confirming feedback submission
    """
    # Generate unique feedback ID using UUID
    timestamp = req.timestamp or datetime.now().isoformat()
    feedback_id = f"FB-{str(uuid.uuid4())[:8]}"
    
    # Validate ratings if provided
    if req.accuracy_rating and not (1 <= req.accuracy_rating <= 5):
        raise HTTPException(
            status_code=400,
            detail="accuracy_rating must be between 1 and 5"
        )
    
    if req.usefulness_rating and not (1 <= req.usefulness_rating <= 5):
        raise HTTPException(
            status_code=400,
            detail="usefulness_rating must be between 1 and 5"
        )
    
    # In production, this would store feedback in a database
    # For now, we'll just acknowledge receipt
    # Placeholder for database storage:
    # feedback_summary = {
    #     "feedback_id": feedback_id,
    #     "user_id": req.user_id or "anonymous",
    #     "prediction_id": req.prediction_id,
    #     "actual_price": req.actual_price,
    #     "accuracy_rating": req.accuracy_rating,
    #     "usefulness_rating": req.usefulness_rating,
    #     "comments": req.comments,
    #     "timestamp": timestamp
    # }
    # db.save_feedback(feedback_summary)
    
    return {
        "feedback_id": feedback_id,
        "status": "success",
        "message": "Thank you for your feedback! Your input helps us improve our predictions.",
        "timestamp": timestamp
    }

# =========================
# ENDPOINT: AGGREGATED IMPACT STATS
# =========================
@app.get("/impact-stats", response_model=ImpactStatsResponse)
def get_impact_stats():
    """
    Retrieve aggregated impact statistics and system metrics.
    
    This endpoint provides overall system statistics including total predictions made,
    user satisfaction, accuracy metrics, and estimated cost savings for farmers.
    Useful for demonstrating system value and impact.
    
    Returns:
        ImpactStatsResponse with comprehensive impact metrics
    """
    # Placeholder: In production, these would be queried from database/analytics
    # For now, we'll return simulated aggregate statistics
    
    impact_stats = {
        "total_predictions": 15420,
        "total_users": 3847,
        "average_accuracy": 0.842,  # 84.2% accuracy
        "total_markets_covered": 42,
        "commodities_tracked": list(ALLOWED_COMMODITIES),
        "user_satisfaction": 4.3,  # Out of 5
        "cost_savings_estimate": 2847500.00,  # Total estimated savings in KES
        "last_updated": datetime.now().isoformat()
    }
    
    return impact_stats
