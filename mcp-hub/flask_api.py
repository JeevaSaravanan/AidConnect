#!/usr/bin/env python3
"""
Simple Flask API server for resource matching.
Run this server to provide HTTP endpoints for the frontend.
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from match_resources_api import match_resources
import json

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/api/match-resources', methods=['POST'])
def match_resources_endpoint():
    """
    POST endpoint to match affected area with best shelters.
    
    Expected JSON body:
    {
        "location": "Washington DC - Southeast",
        "population_affected": 3100,
        "priority_level": 5,
        "required_resources": {"water": 2000, "food_kits": 1500},
        "coordinates": [38.8672, -76.9967]
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400
        
        # Validate required fields
        required_fields = ['location', 'population_affected', 'priority_level', 'required_resources']
        missing = [f for f in required_fields if f not in data]
        if missing:
            return jsonify({
                "success": False,
                "error": f"Missing required fields: {', '.join(missing)}"
            }), 400
        
        # Call the matching function
        result = match_resources(data)
        
        return jsonify(result), 200 if result.get('success') else 500
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "service": "AidConnect Resource Matcher"}), 200

if __name__ == '__main__':
    print("Starting AidConnect Resource Matching API...")
    print("Server running on http://localhost:5002")
    print("CORS enabled for all origins")
    app.run(host='0.0.0.0', port=5002, debug=True)
