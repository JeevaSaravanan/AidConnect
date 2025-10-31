# AidConnect Resource Matching Feature

## Overview
This feature uses NVIDIA's LLM (Llama 3.3 Nemotron) to intelligently match affected areas with the best shelter resources based on:
- Required resources and availability
- Shelter capacity
- Geographic proximity
- Priority levels

## Architecture

### Backend Components

1. **match_resources_api.py** - Core matching logic
   - Loads shelter data from `shelters_actual.jsonl`
   - Sends shelter + area data to NVIDIA LLM
   - Returns top 3 matched shelters with reasoning

2. **flask_api.py** - REST API server
   - Provides HTTP endpoint at `http://localhost:5002/api/match-resources`
   - Handles CORS for frontend integration
   - Validates input and returns JSON responses

3. **llm_utils.py** - LLM communication helper
   - Manages NVIDIA API calls
   - Implements caching for efficiency
   - Handles authentication and error handling

### Frontend Components

1. **MatchedSheltersDialog.tsx** - Modal dialog component
   - Displays top 3 matched shelters
   - Shows match scores, reasoning, and details
   - Provides action buttons for deployment

2. **AffectedAreaPanel.tsx** - Updated with match functionality
   - "Match Resources" button on each affected area card
   - Calls API and displays results in dialog

## Setup & Installation

### 1. Install Python Dependencies

```bash
cd mcp-hub
source venv/bin/activate  # or `.\venv\Scripts\activate` on Windows
pip install flask flask-cors
```

### 2. Configure Environment Variables

Make sure your `.env` file has the NVIDIA API key:

```bash
NV_API_KEY=your_nvidia_api_key_here
NV_INVOKE_URL=https://integrate.api.nvidia.com/v1/chat/completions
NV_MODEL=nvidia/llama-3.3-nemotron-super-49b-v1.5
```

### 3. Start the Backend API

```bash
cd mcp-hub
source venv/bin/activate
python flask_api.py
```

The API will start on `http://localhost:5001`

### 4. Start the Frontend

In a separate terminal:

```bash
npm run dev
```

The frontend will start (typically on `http://localhost:8080` or `http://localhost:8081`)

## Usage

1. Navigate to the **Resource Coordination** tab in the UI
2. In the left panel, you'll see affected areas needing help
3. Click the **"Match Resources"** button on any affected area
4. Wait for the AI to analyze shelters (takes 5-10 seconds)
5. View the top 3 matched shelters in the popup dialog with:
   - Match scores (0-100%)
   - AI reasoning for each match
   - Shelter capacity and available resources
   - Location information

## API Reference

### POST /api/match-resources

Match an affected area with best shelter resources.

**Request Body:**
```json
{
  "location": "Washington DC - Southeast",
  "population_affected": 3100,
  "priority_level": 5,
  "required_resources": {
    "water": 2000,
    "food_kits": 1500,
    "blankets": 500,
    "medical_supplies": 200
  },
  "coordinates": [38.8672, -76.9967]
}
```

**Response (Success):**
```json
{
  "success": true,
  "matches": [
    {
      "index": 1,
      "name": "Shelter Name",
      "location": "Location",
      "match_score": 95,
      "reason": "Explanation of why this is a good match",
      "full_data": { ... }
    },
    // ... 2 more matches
  ],
  "reasoning": "Overall matching strategy explanation",
  "affected_area": { ... }
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "Error message",
  "matches": [],
  "reasoning": ""
}
```

### GET /api/health

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "service": "AidConnect Resource Matcher"
}
```

## How It Works

1. **User clicks "Match Resources"** on an affected area
2. **Frontend sends POST request** with area details to `/api/match-resources`
3. **Backend loads shelters** from `shelters_actual.jsonl` (up to 20 for efficiency)
4. **Backend constructs LLM prompt** with:
   - Affected area requirements
   - All available shelter data
   - Instructions for matching
5. **LLM analyzes and returns** top 3 matches with reasoning
6. **Backend parses response** and enriches with full shelter data
7. **Frontend displays results** in an attractive modal dialog

## Troubleshooting

### API Connection Error
- Ensure Flask API is running on port 5001
- Check that CORS is enabled (should be by default)
- Verify no firewall blocking localhost:5001

### No Matches Returned
- Check that `shelters_actual.jsonl` exists in `mcp-hub/` directory
- Verify NVIDIA API key is valid
- Check Flask console for error messages

### LLM Response Parsing Error
- The system expects JSON output from the LLM
- If parsing fails, check the raw_response in the error
- May need to adjust temperature or prompt if LLM output format changes

### Import Errors
- Ensure all Python dependencies are installed: `pip install -r requirements.txt`
- Verify you're using the correct virtual environment

## Development

### Testing the API Directly

```bash
# Test health endpoint
curl http://localhost:5001/api/health

# Test matching endpoint
curl -X POST http://localhost:5001/api/match-resources \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Test Area",
    "population_affected": 1000,
    "priority_level": 4,
    "required_resources": {"water": 500, "food_kits": 300},
    "coordinates": [38.9, -77.0]
  }'
```

### Testing the Python Module

```bash
cd mcp-hub
source venv/bin/activate
python match_resources_api.py
```

This will run a test matching scenario and print the results.

## Future Enhancements

- [ ] Add caching for frequently matched areas
- [ ] Implement real-time distance calculations using routing APIs
- [ ] Add shelter availability status (open/closed/full)
- [ ] Support for multi-shelter deployments
- [ ] Historical matching performance analytics
- [ ] Integration with deployment tracking system

## License

Part of the AidConnect disaster response platform.
