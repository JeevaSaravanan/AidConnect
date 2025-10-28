#!/usr/bin/env python3
"""
Test script to verify the assistant can call weather API tools.
"""
import requests
import json

API_URL = "http://127.0.0.1:8000"

def test_weather_query():
    """Test asking about weather - should trigger tool call"""
    response = requests.post(
        f"{API_URL}/assistant/converse",
        json={
            "message": "What does the weather look like in Georgetown today?"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Success!")
        print(f"Session ID: {data.get('session_id')}")
        print(f"\nReply:\n{data.get('reply')}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)

def test_simple_query():
    """Test a simple query without tools"""
    response = requests.post(
        f"{API_URL}/assistant/converse",
        json={
            "message": "Hi"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Success!")
        print(f"Session ID: {data.get('session_id')}")
        print(f"\nReply:\n{data.get('reply')}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    print("Testing simple query...")
    print("-" * 60)
    test_simple_query()
    print("\n" + "=" * 60 + "\n")
    
    print("Testing weather query (should use call_weather_api)...")
    print("-" * 60)
    test_weather_query()
