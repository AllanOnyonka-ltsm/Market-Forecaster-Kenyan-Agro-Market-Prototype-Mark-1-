#!/usr/bin/env python3
"""
Comprehensive test script for all API endpoints.
Tests basic functionality of each endpoint to ensure they are working correctly.
"""

import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

def test_endpoint(name: str, method: str, endpoint: str, data: Dict[str, Any] = None) -> None:
    """Test a single endpoint and print results."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")
    
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{endpoint}")
        elif method == "POST":
            response = requests.post(
                f"{BASE_URL}{endpoint}",
                json=data,
                headers={"Content-Type": "application/json"}
            )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code in [200, 201]:
            print(" SUCCESS")
            result = response.json()
            print(json.dumps(result, indent=2))
        else:
            print(" FAILED")
            print(response.text)
            
    except Exception as e:
        print(f" ERROR: {str(e)}")

def main():
    """Run all endpoint tests."""
    print("\n" + "="*60)
    print("KENYAN AGRO MARKET API - COMPREHENSIVE ENDPOINT TESTS")
    print("="*60)
    
    # Test 1: Root endpoint
    test_endpoint(
        "Root Endpoint",
        "GET",
        "/"
    )
    
    # Test 2: Predict endpoint
    test_endpoint(
        "Price Prediction",
        "POST",
        "/predict",
        {
            "date": "2025-12-05",
            "admin1": "Nairobi",
            "market": "Wakulima (Nairobi)",
            "commodity": "tomatoes",
            "pricetype": "retail",
            "previous_month_price": 58.2
        }
    )
    
    # Test 3: Recommendations endpoint
    test_endpoint(
        "Actionable Recommendations",
        "POST",
        "/recommendations",
        {
            "commodity": "cabbage",
            "market": "Wakulima (Nairobi)",
            "admin1": "Nairobi",
            "predicted_price": 120.0,
            "previous_price": 100.0,
            "pricetype": "retail"
        }
    )
    
    # Test 4: Micro-market endpoint
    test_endpoint(
        "Micro-Market Forecasting",
        "POST",
        "/micro-market",
        {
            "commodity": "tomatoes",
            "region": "Nairobi",
            "radius_km": 30.0,
            "date": "2025-12-05"
        }
    )
    
    # Test 5: Format endpoint - SMS
    test_endpoint(
        "Format for SMS",
        "POST",
        "/format",
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
    )
    
    # Test 6: Format endpoint - WhatsApp
    test_endpoint(
        "Format for WhatsApp",
        "POST",
        "/format",
        {
            "prediction_data": {
                "commodity": "cabbage",
                "market": "Wakulima (Nairobi)",
                "prediction_per_kg": 115.5,
                "date": "2025-12-05",
                "previous_month_price": 100.0,
                "confidence_pct": 90,
                "lower_bound": 105,
                "upper_bound": 125,
                "note": "Prediction within normal range."
            },
            "format_type": "whatsapp"
        }
    )
    
    # Test 7: Format endpoint - Bulletin
    test_endpoint(
        "Format for Bulletin",
        "POST",
        "/format",
        {
            "prediction_data": {
                "commodity": "cabbage",
                "market": "Wakulima (Nairobi)",
                "prediction_per_kg": 115.5,
                "date": "2025-12-05",
                "previous_month_price": 100.0,
                "confidence_pct": 90,
                "lower_bound": 105,
                "upper_bound": 125,
                "note": "Prediction within normal range."
            },
            "format_type": "bulletin"
        }
    )
    
    # Test 8: Explainability endpoint
    test_endpoint(
        "Explainability (XAI)",
        "POST",
        "/explainability",
        {
            "commodity": "tomatoes",
            "market": "Wakulima (Nairobi)",
            "predicted_price": 65.5,
            "features": {
                "previous_month_price": 58.2,
                "pricetype": "retail"
            }
        }
    )
    
    # Test 9: Feedback endpoint
    test_endpoint(
        "User Feedback Collection",
        "POST",
        "/feedback",
        {
            "user_id": "farmer123",
            "prediction_id": "pred_001",
            "actual_price": 67.0,
            "accuracy_rating": 4,
            "usefulness_rating": 5,
            "comments": "Very helpful prediction!"
        }
    )
    
    # Test 10: Impact stats endpoint
    test_endpoint(
        "Aggregated Impact Statistics",
        "GET",
        "/impact-stats"
    )
    
    # Test 11: Error handling - Invalid commodity
    test_endpoint(
        "Error Handling - Invalid Commodity",
        "POST",
        "/recommendations",
        {
            "commodity": "banana",
            "market": "Wakulima (Nairobi)",
            "admin1": "Nairobi",
            "predicted_price": 120.0,
            "previous_price": 100.0,
            "pricetype": "retail"
        }
    )
    
    # Test 12: Error handling - Zero previous price
    test_endpoint(
        "Error Handling - Zero Previous Price",
        "POST",
        "/recommendations",
        {
            "commodity": "cabbage",
            "market": "Wakulima (Nairobi)",
            "admin1": "Nairobi",
            "predicted_price": 120.0,
            "previous_price": 0.0,
            "pricetype": "retail"
        }
    )
    
    print("\n" + "="*60)
    print("TEST SUITE COMPLETED")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
