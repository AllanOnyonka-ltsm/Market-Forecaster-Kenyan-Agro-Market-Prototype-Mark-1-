# API Endpoints Documentation

This document describes all available endpoints in the Kenyan Agro Market Price Prediction API.

## Base URL
`http://localhost:8000` (development)

## Endpoints

### 1. GET `/`
Root endpoint providing API information and available endpoints.

**Response:**
```json
{
  "message": "Kenyan Agro Market Price Prediction API",
  "endpoints": { ... },
  "example_request": { ... },
  "supported_commodities": ["kale", "tomatoes", "cabbage", "potatoes", "onion"]
}
```

---

### 2. POST `/predict`
Make price predictions for agricultural commodities.

**Request Body:**
```json
{
  "date": "2025-12-05",
  "admin1": "Nairobi",
  "market": "Wakulima (Nairobi)",
  "commodity": "tomatoes",
  "pricetype": "retail",
  "previous_month_price": 58.2
}
```

**Response:**
```json
{
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
  "unreasonable": true,
  "note": "⚠️ Unreasonable: exceeds normal threshold of 64 per kg."
}
```

---

### 3. POST `/recommendations`
Get actionable recommendations based on price predictions.

**Purpose:** Provides farmers with sell/hold/buy recommendations based on predicted price changes.

**Request Body:**
```json
{
  "commodity": "cabbage",
  "market": "Wakulima (Nairobi)",
  "admin1": "Nairobi",
  "predicted_price": 120.0,
  "previous_price": 100.0,
  "pricetype": "retail"
}
```

**Response:**
```json
{
  "commodity": "cabbage",
  "market": "Wakulima (Nairobi)",
  "recommendations": [
    "Predicted price increase of 20.0% - consider selling soon",
    "Market conditions favor sellers",
    "Retail prices are high - good time to market your produce"
  ],
  "action_type": "sell",
  "confidence": "high",
  "rationale": "Significant price increase predicted. Selling now or in the near future could maximize returns."
}
```

**Action Types:**
- `sell`: Price increasing, favorable to sell
- `hold`: Price decreasing or unstable, wait for better conditions
- `buy`: (Future use for traders)

---

### 4. POST `/micro-market`
Get localized/micro-market forecasting for specific regions.

**Purpose:** Provides price forecasts for nearby markets within a specified radius to help farmers find the best selling location.

**Request Body:**
```json
{
  "commodity": "tomatoes",
  "region": "Nairobi",
  "radius_km": 30.0,
  "date": "2025-12-05"
}
```

**Response:**
```json
{
  "commodity": "tomatoes",
  "region": "Nairobi",
  "nearby_markets": [
    {
      "market_name": "Nairobi Central Market",
      "distance_km": 0.0,
      "estimated_price": 57.6,
      "market_type": "wholesale"
    },
    {
      "market_name": "Nairobi Retail Hub",
      "distance_km": 9.0,
      "estimated_price": 70.4,
      "market_type": "retail"
    }
  ],
  "localized_forecast": {
    "average_price": 62.93,
    "min_price": 57.6,
    "max_price": 70.4,
    "price_variance": 12.8
  },
  "recommended_market": "Nairobi Central Market",
  "market_comparison": "High price variance (12.8 KES) across nearby markets. Shopping around could save money."
}
```

---

### 5. POST `/format`
Format predictions for non-technical users (SMS, WhatsApp, bulletin).

**Purpose:** Transforms technical prediction data into user-friendly formats for different communication channels.

**Request Body:**
```json
{
  "prediction_data": {
    "commodity": "cabbage",
    "market": "Wakulima (Nairobi)",
    "prediction_per_kg": 115.5,
    "date": "2025-12-05",
    "previous_month_price": 100.0,
    "confidence_pct": 90,
    "note": "Prediction within normal range."
  },
  "format_type": "sms"
}
```

**Format Types:**
- `sms`: Short format optimized for SMS (160 chars)
- `whatsapp`: Rich formatted message with emojis
- `bulletin`: Formal printed bulletin format

**Response (SMS):**
```json
{
  "format_type": "sms",
  "formatted_message": "cabbage @ Wakulima (Nairobi): KES 115.5/kg on 2025-12-05. Prev: KES 100.0/kg",
  "character_count": 76,
  "estimated_cost": 0.5
}
```

**Response (WhatsApp):**
```json
{
  "format_type": "whatsapp",
  "formatted_message": "📊 *Market Price Forecast*\n\n🌾 Commodity: cabbage\n...",
  "character_count": 244,
  "estimated_cost": 0.0
}
```

---

### 6. POST `/explainability`
Get AI prediction explanations (XAI - Explainable AI).

**Purpose:** Explains which factors influenced the price prediction to build user trust and understanding.

**Request Body:**
```json
{
  "commodity": "tomatoes",
  "market": "Wakulima (Nairobi)",
  "predicted_price": 65.5,
  "features": {
    "previous_month_price": 58.2,
    "pricetype": "retail"
  }
}
```

**Response:**
```json
{
  "commodity": "tomatoes",
  "market": "Wakulima (Nairobi)",
  "predicted_price": 65.5,
  "top_influencing_factors": [
    {
      "factor": "Previous Month Price",
      "importance": 0.45,
      "impact": "High",
      "description": "Historical price of 58.2 KES/kg strongly influences forecast"
    },
    {
      "factor": "Market Location",
      "importance": 0.25,
      "impact": "Medium",
      "description": "Wakulima (Nairobi) market has specific price patterns"
    }
  ],
  "explanation_summary": "The predicted price of 65.5 KES/kg for tomatoes...",
  "confidence_factors": {
    "data_quality": "high",
    "historical_accuracy": 0.85,
    "sample_size": "adequate",
    "market_volatility": "moderate",
    "prediction_reliability": "good"
  }
}
```

---

### 7. POST `/feedback`
Submit user feedback on predictions.

**Purpose:** Collects user feedback about prediction accuracy and usefulness to improve the model over time.

**Request Body:**
```json
{
  "user_id": "farmer123",
  "prediction_id": "pred_001",
  "actual_price": 67.0,
  "accuracy_rating": 4,
  "usefulness_rating": 5,
  "comments": "Very helpful prediction!"
}
```

**Fields:**
- `accuracy_rating`: 1-5 scale (1=very inaccurate, 5=very accurate)
- `usefulness_rating`: 1-5 scale (1=not useful, 5=very useful)
- All fields are optional except for the request body itself

**Response:**
```json
{
  "feedback_id": "FB-0439bf62",
  "status": "success",
  "message": "Thank you for your feedback! Your input helps us improve our predictions.",
  "timestamp": "2025-12-05T11:08:32.393791"
}
```

---

### 8. GET `/impact-stats`
View aggregated impact statistics.

**Purpose:** Provides system-wide metrics demonstrating the API's reach and impact.

**Response:**
```json
{
  "total_predictions": 15420,
  "total_users": 3847,
  "average_accuracy": 0.842,
  "total_markets_covered": 42,
  "commodities_tracked": ["onion", "potatoes", "cabbage", "kale", "tomatoes"],
  "user_satisfaction": 4.3,
  "cost_savings_estimate": 2847500.0,
  "last_updated": "2025-12-05T11:04:25.446844"
}
```

---

## Supported Commodities
- `cabbage`
- `kale`
- `onion`
- `potatoes`
- `tomatoes`

## Error Responses

### 400 Bad Request
Returned when:
- Invalid commodity specified
- Invalid format_type
- Invalid rating values (must be 1-5)
- Division by zero (previous_price <= 0)

```json
{
  "detail": "Commodity 'banana' not supported. Allowed: ['cabbage', 'kale', 'onion', 'potatoes', 'tomatoes']"
}
```

### 422 Validation Error
Returned when request body doesn't match the expected schema:
```json
{
  "detail": [
    {
      "loc": ["body", "commodity"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## Interactive Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Notes

### Production Considerations
1. **Micro-market endpoint**: Currently returns deterministic placeholder data. In production, integrate with a geospatial database for real market locations and prices.

2. **Explainability endpoint**: Uses simulated feature importance. In production, integrate SHAP values or actual model feature importance.

3. **Feedback endpoint**: Currently just acknowledges receipt. In production, persist to database for model retraining and analytics.

4. **Impact-stats endpoint**: Returns static placeholder data. In production, query from analytics database with real aggregated metrics.

### Security
- All endpoints validate input data using Pydantic schemas
- No security vulnerabilities detected by CodeQL analysis
- CORS is currently set to allow all origins - restrict in production
- No authentication/authorization implemented - add in production
