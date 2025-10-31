#!/usr/bin/env python3
"""
API endpoint for matching affected areas with best shelter resources using LLM.
"""
import json
from typing import List, Dict, Any
from pathlib import Path
from llm_utils import nv_chat

def load_shelters() -> List[Dict[str, Any]]:
    """Load all shelters from shelters_actual.jsonl"""
    shelters = []
    shelter_file = Path(__file__).parent / "shelters_actual.jsonl"
    
    if not shelter_file.exists():
        print(f"[ERROR] Shelter file not found: {shelter_file}")
        return []
    
    with open(shelter_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    shelters.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"[ERROR] Failed to parse line: {e}")
                    continue
    
    return shelters


def match_resources(affected_area: Dict[str, Any]) -> Dict[str, Any]:
    """
    Use LLM to find the best 3 shelter matches for an affected area.
    
    Args:
        affected_area: Dictionary containing:
            - location: str
            - required_resources: dict (e.g., {"water": 2000, "food_kits": 1500})
            - population_affected: int
            - priority_level: int
            - coordinates: [lat, lon]
    
    Returns:
        Dictionary with:
            - success: bool
            - matches: List of top 3 shelters
            - reasoning: str
    """
    print(f"[MATCH] Starting match for area: {affected_area.get('location', 'Unknown')}")
    
    shelters = load_shelters()
    
    if not shelters:
        print("[MATCH ERROR] No shelters available")
        return {
            "success": False,
            "error": "No shelters available",
            "matches": [],
            "reasoning": ""
        }
    
    print(f"[MATCH] Loaded {len(shelters)} shelters")
    
    # Prepare data for LLM
    shelters_summary = []
    for i, shelter in enumerate(shelters[:20], 1):  # Limit to 20 for token efficiency
        shelter_info = {
            "index": i,
            "name": shelter.get("shelter_name", "Unknown"),
            "location": shelter.get("location", "Unknown"),
            "capacity": shelter.get("capacity", "Unknown"),
            "available_items": shelter.get("available_items", []),
            "coordinates": [shelter.get("latitude"), shelter.get("longitude")],
            "details": shelter.get("details", "")
        }
        shelters_summary.append(shelter_info)
    
    # Build the prompt
    prompt = f"""You are an AI disaster response coordinator. Analyze shelters and provide the top 3 matches for this affected area.

AFFECTED AREA:
- Location: {affected_area.get('location', 'Unknown')}
- Population: {affected_area.get('population_affected', 0):,} people
- Priority: {affected_area.get('priority_level', 0)}/5 (CRITICAL)
- Needs: {json.dumps(affected_area.get('required_resources', {}))}
- Coordinates: {affected_area.get('coordinates', [])}

TOP 20 SHELTERS DATA:
{json.dumps(shelters_summary, indent=2)}

TASK: Select the 3 BEST shelters based on:
1. Resource availability (matches required items)
2. Capacity (can handle population)
3. Distance (closer is better)

RESPOND WITH ONLY THIS JSON (no other text):
{{
    "top_matches": [
        {{"index": <number>, "name": "<shelter>", "location": "<loc>", "match_score": <0-100>, "reason": "<why>"}},
        {{"index": <number>, "name": "<shelter>", "location": "<loc>", "match_score": <0-100>, "reason": "<why>"}},
        {{"index": <number>, "name": "<shelter>", "location": "<loc>", "match_score": <0-100>, "reason": "<why>"}}
    ],
    "overall_reasoning": "<brief summary>"
}}"""

    # Call LLM
    print("[MATCH] Calling LLM...")
    try:
        # Use system message to prevent thinking tags
        messages = [
            {
                "role": "system", 
                "content": "You are a disaster response AI. Respond ONLY with valid JSON. Do not include any thinking process, explanations, or markdown. Just the JSON object."
            },
            {
                "role": "user", 
                "content": prompt
            }
        ]
        response = nv_chat(
            messages=messages,
            max_tokens=2048,  # Increased for longer responses
            temperature=0.1,  # Very low temperature for focused, deterministic output
            use_cache=False
        )
        
        print(f"[MATCH] LLM Response length: {len(response)} chars")
        print(f"[MATCH] LLM Response preview: {response[:200]}...")
        
        # Check if response is an error message
        if response.startswith("[NV ERROR]") or response.startswith("[NV CONNECT ERROR]") or response.startswith("[NV HTTP ERROR]"):
            return {
                "success": False,
                "error": f"LLM API Error: {response}",
                "matches": [],
                "reasoning": ""
            }
        
        # Parse LLM response
        # Try to extract JSON from response
        response = response.strip()
        
        # If response is empty
        if not response:
            return {
                "success": False,
                "error": "LLM returned empty response. Please check API key and connectivity.",
                "matches": [],
                "reasoning": ""
            }
        
        # Remove thinking tags if present (some models include reasoning)
        if "<think>" in response:
            # Extract content after </think> tag
            think_end = response.find("</think>")
            if think_end != -1:
                response = response[think_end + 8:].strip()
                print(f"[MATCH] Removed thinking section, new length: {len(response)} chars")
            else:
                # If no closing tag, the thinking was cut off - return error
                print(f"[MATCH ERROR] Response contains unclosed <think> tag - likely truncated")
                return {
                    "success": False,
                    "error": "LLM response was truncated (thinking section not closed). Try again or increase max_tokens.",
                    "matches": [],
                    "reasoning": ""
                }
        
        # Remove markdown code blocks if present
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        try:
            result = json.loads(response)
            
            print(f"[MATCH] Successfully parsed JSON response")
            
            # Enhance with full shelter data
            matches = []
            for match in result.get("top_matches", [])[:3]:
                idx = match.get("index", 0) - 1
                if 0 <= idx < len(shelters_summary):
                    full_shelter = shelters[idx] if idx < len(shelters) else shelters_summary[idx]
                    matches.append({
                        **match,
                        "full_data": full_shelter
                    })
            
            return {
                "success": True,
                "matches": matches,
                "reasoning": result.get("overall_reasoning", ""),
                "affected_area": affected_area
            }
            
        except json.JSONDecodeError as e:
            # If JSON parsing fails, return raw response
            print(f"[MATCH ERROR] Failed to parse JSON: {e}")
            print(f"[MATCH ERROR] Raw response: {response}")
            return {
                "success": False,
                "error": f"Failed to parse LLM response: {e}",
                "raw_response": response,
                "matches": [],
                "reasoning": ""
            }
            
    except Exception as e:
        print(f"[MATCH ERROR] Exception: {e}")
        return {
            "success": False,
            "error": str(e),
            "matches": [],
            "reasoning": ""
        }


if __name__ == "__main__":
    # Test the matching
    test_area = {
        "id": "dc_southeast_001",
        "location": "Washington DC - Southeast",
        "coordinates": [38.8672, -76.9967],
        "disaster_type": "Hurricane Flood",
        "population_affected": 3100,
        "priority_level": 5,
        "required_resources": {
            "water": 2000,
            "food_kits": 1500,
            "blankets": 500,
            "medical_supplies": 200
        }
    }
    
    result = match_resources(test_area)
    print(json.dumps(result, indent=2))
