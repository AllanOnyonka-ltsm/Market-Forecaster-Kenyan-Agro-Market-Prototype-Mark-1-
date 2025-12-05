# Market-Forecaster-Kenyan-Agro-Market-Prototype-Mark-1-

This is a forecasting system for farmers to predict next month's most likely pricing on their crop and provide actionable insights.

## Features

The API now includes the following endpoints:

1. **Price Prediction** (`/predict`) - Core ML-based price forecasting
2. **Actionable Recommendations** (`/recommendations`) - Get sell/hold/buy advice based on predictions
3. **Micro-Market Forecasting** (`/micro-market`) - Localized price forecasts for nearby markets
4. **User-Friendly Formatting** (`/format`) - Format predictions for SMS, WhatsApp, or bulletin
5. **Explainability (XAI)** (`/explainability`) - Understand which factors influenced predictions
6. **User Feedback** (`/feedback`) - Submit feedback on prediction accuracy
7. **Impact Statistics** (`/impact-stats`) - View system-wide metrics and impact

## Documentation

- See [price_api/API_ENDPOINTS.md](price_api/API_ENDPOINTS.md) for detailed endpoint documentation
- Interactive API docs available at `/docs` when server is running
- Test script available at [price_api/test_endpoints.py](price_api/test_endpoints.py)

## Getting Started

1. Install dependencies:
   ```bash
   pip install -r price_api/requirements.txt
   ```

2. Start the server:
   ```bash
   cd price_api
   uvicorn app:app --reload
   ```

3. Access the API:
   - API: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs
   - Alternative docs: http://localhost:8000/redoc

## Supported Commodities

- Cabbage
- Kale
- Onion
- Potatoes
- Tomatoes

