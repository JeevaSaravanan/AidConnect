# How to Restart API Server

## Quick Restart

The API server needs to be restarted to pick up the latest changes. Here's how:

### Step 1: Stop the Current Server

Find and kill the running process:

```bash
# Find the process ID
ps aux | grep api_server | grep -v grep

# You should see output like:
# jeevasaravanabhavanandam 21534  0.1  0.4 ... uvicorn api_server:app

# Kill it using the PID (first number after username)
kill 21534
```

### Step 2: Start the Server with Auto-Reload

Navigate to the mcp-hub directory and start with reload mode:

```bash
cd /Users/jeevasaravanabhavanandam/Documents/AidConnect/mcp-hub
uvicorn api_server:app --host 127.0.0.1 --port 8000 --reload
```

The `--reload` flag will automatically restart the server when you make changes to the code!

## What Changed?

### ✅ Pattern-Based Tool Detection
The server now **automatically detects** weather, volunteer, and shelter queries and calls the appropriate tools, even if the LLM doesn't generate the tool call format.

**Example patterns that trigger tools:**
- "What's the weather in Georgetown DC?" → calls `call_weather_api`
- "Weather in Boston today?" → calls `call_weather_api`
- "Find volunteers in Alexandria" → calls `search_volunteers`
- "List shelters near me" → calls `search_shelters`

### How It Works

1. **User asks:** "What is the weather in Georgetown DC?"
2. **Pattern detector:** Recognizes this as a weather query
3. **Auto-injection:** Creates tool call: `call_weather_api(city="Georgetown DC")`
4. **Execute tool:** Calls the actual weather API
5. **LLM formats:** Takes the weather data and creates a nice response
6. **User sees:** "The current temperature in Georgetown, DC is 68°F with clear skies..."

## Testing

### Test 1: Simple Weather Query
```bash
curl -X POST http://127.0.0.1:8000/assistant/converse \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the weather in Georgetown DC?"}'
```

### Test 2: Using Python Script
```bash
python test_weather_tool.py
```

### Test 3: In the Frontend
Just open your app at http://localhost:5173 and ask in the chat:
- "What's the weather in Georgetown DC today?"
- "How's the weather in Boston?"
- "Find volunteers near Alexandria"

## Troubleshooting

### "Connection refused" error
Server isn't running. Start it with the command above.

### Still not working?
1. Make sure you killed the old process completely
2. Check that you're in the right directory when starting
3. Look at the terminal output for any errors
4. Verify the port 8000 isn't being used by something else

### Want to see the logs?
The uvicorn server will show all requests and responses in the terminal where it's running.
