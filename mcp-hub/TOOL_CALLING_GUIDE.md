# Tool Calling Guide for AidConnect Assistant

## Overview
The AidConnect Assistant now supports tool calling, allowing the LLM to automatically invoke functions like `call_weather_api`, `search_volunteers`, and `search_shelters` to provide real-time data.

## How It Works

### 1. Tool Call Format
When the LLM needs to call a tool, it responds with:
```xml
<tool_call>{"name": "tool_name", "arguments": {"arg1": "value1"}}</tool_call>
```

### 2. Available Tools
- **call_weather_api(city: str)** - Get current weather for any city
- **search_volunteers(name, lat, lon, k)** - Search for volunteers by name or location
- **search_shelters(name, lat, lon, k)** - Search for shelters by name or location
- **call_fema_api(dataset, filter, top)** - Query FEMA datasets
- **call_arcgis_api(data_api_url, where, limit)** - Query ArcGIS services

### 3. Example Flow

**User Query:** "What's the weather in Georgetown DC today?"

**LLM Response 1 (Tool Call):**
```xml
<tool_call>{"name": "call_weather_api", "arguments": {"city": "Georgetown DC"}}</tool_call>
```

**System Response (Tool Result):**
```json
{
  "latitude": 38.9,
  "longitude": -77.06,
  "current_weather": {
    "temperature": 68,
    "windspeed": 10.5,
    "weathercode": 0
  },
  "_geo": {
    "city": "Georgetown",
    "lat": 38.9,
    "lon": -77.06
  }
}
```

**LLM Response 2 (Final Answer):**
"The current weather in Georgetown, DC shows a temperature of 68°F with wind speeds of 10.5 mph. Conditions are clear."

## Restarting the API Server

After making changes to `api_server.py`, restart the server:

### Option 1: Kill and restart
```bash
# Find the process
ps aux | grep api_server | grep -v grep

# Kill it (replace PID with actual process ID)
kill <PID>

# Start it again
cd /Users/jeevasaravanabhavanandam/Documents/AidConnect/mcp-hub
uvicorn api_server:app --host 127.0.0.1 --port 8000 --reload
```

### Option 2: Use reload mode (recommended for development)
```bash
cd /Users/jeevasaravanabhavanandam/Documents/AidConnect/mcp-hub
uvicorn api_server:app --host 127.0.0.1 --port 8000 --reload
```

The `--reload` flag automatically restarts the server when files change.

## Testing

### Test with curl:
```bash
curl -X POST http://127.0.0.1:8000/assistant/converse \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the weather in Georgetown DC today?"}'
```

### Test with Python:
```bash
cd /Users/jeevasaravanabhavanandam/Documents/AidConnect/mcp-hub
python test_weather_tool.py
```

## Troubleshooting

### Issue: LLM doesn't use tools
**Solution:** The model might need stronger prompting. The system prompt has been updated with explicit examples and instructions to ALWAYS use tools when available.

### Issue: Tool parsing fails
**Solution:** Check that the LLM generates the exact format: `<tool_call>{...}</tool_call>` with valid JSON inside.

### Issue: Server not picking up changes
**Solution:** Make sure to restart the server or use `--reload` mode.

## Frontend Integration

The ChatInterface component in the frontend automatically:
1. Parses `<think>` tags to show thinking process
2. Sends messages to `/assistant/converse`
3. Displays responses in the chat

The tool calls happen transparently on the backend - users just see the final results!
