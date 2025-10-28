#!/usr/bin/env python3
import os
import re
import sys
import json
import shlex
import signal
import httpx
import subprocess
from typing import Any, Dict, List, Optional
from llm_utils import nv_chat

# =========================
# Config via environment
# =========================
NV_URL     = os.getenv("NV_INVOKE_URL", "https://integrate.api.nvidia.com/v1/chat/completions")
NV_MODEL   = os.getenv("NV_MODEL", "meta/llama-4-maverick-17b-128e-instruct")
NV_KEY     = os.getenv("NV_API_KEY", "")
NV_TIMEOUT = float(os.getenv("HTTP_TIMEOUT_SEC", "25"))

HUB_CMD  = os.getenv("HUB_CMD", sys.executable)       # default: python
HUB_ARGS = os.getenv("HUB_ARGS", "hub_server.py")     # default: file in CWD

PROTOCOL_VERSION = "2024-11-05"

ALLOWED_TOOLS = {
    "get_weather": {"city": "string"},
    "disaster_plan": {"city": "string", "hazard": "string"},
    "fema_query": {"dataset": "string", "filter": "string", "select": "string", "orderby": "string", "top": "number", "skip": "number"},
    "arcgis_query": {"data_api_url": "string", "where": "string", "fields": "string", "limit": "number", "offset": "number", "bbox": "string"}
}

# =========================
# Minimal persistent MCP client (NDJSON over stdio)
# =========================
class MCPHub:
    def __init__(self, cmd: str, args: str) -> None:
        argv = [cmd, *shlex.split(args)]
        self.proc = subprocess.Popen(
            argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=sys.stderr, text=False, bufsize=0
        )
        if not self.proc.stdin or not self.proc.stdout:
            raise RuntimeError("Failed to open pipes to hub MCP server")
        self._id = 0
        self._send({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "assistant-auto", "version": "0.2.0"}
            }
        })
        _ = self._read()  # initialize response
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    def _send(self, obj: Dict[str, Any]) -> None:
        line = json.dumps(obj, separators=(",", ":")) + "\n"
        self.proc.stdin.write(line.encode("utf-8"))
        self.proc.stdin.flush()

    def _read(self) -> Dict[str, Any]:
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError("Hub MCP closed stdout")
        return json.loads(line.decode("utf-8"))

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        rid = self._next_id()
        self._send({"jsonrpc":"2.0","id":rid,"method":"tools/call","params":{"name":name,"arguments":arguments}})
        resp = self._read()
        # Extract text content(s)
        try:
            items = resp["result"]["content"]
            texts = [it.get("text","") for it in items if it.get("type")=="text"]
            return "\n".join(texts).strip() or json.dumps(resp, indent=2)
        except Exception:
            return json.dumps(resp, indent=2)

    def close(self) -> None:
        try:
            if self.proc and self.proc.stdin:
                self.proc.stdin.close()
        except Exception:
            pass
        try:
            if self.proc:
                self.proc.terminate()
        except Exception:
            pass

# =========================
# NVIDIA Integrate client
# =========================
# nv_chat now provided by llm_utils.nv_chat (cached wrapper)

# =========================
# Tool-calling protocol (model decides + retries)
# =========================
SYSTEM_TOOL_USE = """
You are a helpful assistant that can decide to call tools via an MCP hub.

TOOLS (choose at most one at a time; you may chain):
- get_weather(city: string) → current weather JSON (Open-Meteo via child MCP)
- fema_query(
    dataset: string,            # typically "DisasterDeclarationsSummaries"
    filter?: string,            # e.g., "state eq 'DC'"
    select?: string,            # CSV column list
    orderby?: string,           # e.g., "declarationDate desc"
    top?: number,               # page size (use 1..1000; prefer <= 50 unless user asks)
    skip?: number               # offset
  ) → OpenFEMA JSON
- arcgis_query(
    data_api_url: string,       # ArcGIS Hub Data API .../api endpoint
    where?: string,             # SQL-ish where, default "1=1"
    fields?: string,            # CSV field list or "*"
    limit?: number,             # use <= 100 unless user asks
    offset?: number,
    bbox?: string               # "minx,miny,maxx,maxy"
  ) → GeoJSON or JSON
- disaster_plan(city: string, hazard?: string) → synthesizes a response plan using weather + LLM
- nim_chat(...) → general LLM reasoning (use sparingly; prefer domain tools first)

PLANNING STEP (MANDATORY):
Before answering, produce a ONE-LINE JSON object describing your plan:
{"plan":{"need_tool": true|false, "tool": "<name or null>", "arguments": {…}, "intent": "<short intent>", "confidence": 0..1}}
Rules:
- If a tool clearly improves accuracy (fresh data), set need_tool=true.
- Choose the single best next tool; you may iterate (tool → TOOL_RESULT → new plan).
- Validate arguments are present and plausible. For counts like "last 10", set top=10 and orderby="declarationDate desc".
- FEMA: prefer dataset "DisasterDeclarationsSummaries" unless the user specifies another dataset.
- ARC/GIS: pass the exact dataset /api URL the user gives; otherwise ask for it.
- Weather/place names: attempt reasonable normalization yourself (e.g., "Washington, DC" / "Washington, District of Columbia").

EXECUTION PROTOCOL:
1) Output ONLY the planning JSON on one line when you want to call a tool (no prose).
2) After the tool result is provided back as: TOOL_RESULT(<tool>): <data>,
   either:
   - produce another planning JSON to refine/call again (up to 3 total tool calls), or
   - produce a final natural-language answer. Summarize, don’t dump raw JSON.
3) If no tool needed, skip planning JSON and answer naturally.

EXAMPLES:
User: "Show last 10 FEMA disaster declarations for DC"
Plan JSON:
{"plan":{"need_tool":true,"tool":"fema_query","arguments":{"dataset":"DisasterDeclarationsSummaries","filter":"state eq 'DC'","select":"disasterNumber,declarationDate,incidentType,declarationType,state,declaredCountyArea","orderby":"declarationDate desc","top":10},"intent":"recent FEMA declarations for DC","confidence":0.92}}

User: "Map shelters near Washington, DC from this dataset https://hub.arcgis.com/.../api"
Plan JSON:
{"plan":{"need_tool":true,"tool":"arcgis_query","arguments":{"data_api_url":"https://hub.arcgis.com/.../api","where":"1=1","fields":"*","limit":50},"intent":"list features from given ArcGIS dataset","confidence":0.83}}

User: "Is it safe to hold an outdoor event tomorrow afternoon in Miami?"
Plan JSON:
{"plan":{"need_tool":true,"tool":"get_weather","arguments":{"city":"Miami, FL"},"intent":"check current/local weather","confidence":0.78}}

OUTPUT CONSTRAINT:
- When emitting planning JSON or any subsequent tool-call JSON, output NOTHING else on that turn.
""".strip()


# Strict extractor for a one-line JSON tool call
TOOL_JSON_RE = re.compile(r'^\s*\{.*"call_tool"\s*:\s*\{.*\}\s*\}\s*$', re.DOTALL)

def maybe_parse_tool_call(text: str) -> Optional[Dict[str, Any]]:
    # Accept raw line or fenced block; choose the first valid JSON
    candidates = []
    for m in re.finditer(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL|re.IGNORECASE):
        candidates.append(m.group(1).strip())
    if TOOL_JSON_RE.match(text.strip()):
        candidates.append(text.strip())
    for c in candidates:
        try:
            obj = json.loads(c)
            if "call_tool" in obj and isinstance(obj["call_tool"], dict):
                print("call_tool", obj["call_tool"])
                return obj["call_tool"]
        except json.JSONDecodeError:
            continue
    return None

# =========================
# Chat loop (auto-tool + retries led by the LLM)
# =========================
def main() -> None:
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    hub = MCPHub(HUB_CMD, HUB_ARGS)
    history: List[Dict[str, str]] = [{"role":"system","content": SYSTEM_TOOL_USE.strip()}]

    while True:
        try:
            user = input().strip()
        except EOFError:
            print()
            break
        if not user:
            continue
        if user.lower() in ("/exit", "exit", "quit", ":q"):
            break

        # Step 1: Ask the model
        history.append({"role":"user","content": user})
        assistant_msg = nv_chat(history)

        # Try up to 3 tool-call cycles, but ONLY if the LLM chooses to call
        for _ in range(3):
            tool = maybe_parse_tool_call(assistant_msg)
            if not tool:
                # No tool call → final answer
                print(assistant_msg)
                history.append({"role":"assistant","content": assistant_msg})
                break

            name = str(tool.get("name",""))
            args = tool.get("arguments") or {}
            if name not in ALLOWED_TOOLS:
                # Not allowed → tell the user and fall back to direct answer
                history.append({"role":"assistant","content": f"(unsupported tool '{name}')"})
                assistant_msg = nv_chat(history)
                continue  # this will likely become a non-tool message

            # Execute tool
            try:
                tool_result = hub.call_tool(name, args)
            except Exception as e:
                tool_result = f"[TOOL ERROR] {e}"

            # Provide tool result and ask model what to do next (retry or finalize)
            history.append({"role":"assistant","content": f"(tool {name} called with {args})"})
            history.append({"role":"user","content": f"TOOL_RESULT({name}):\n{tool_result}"})
            assistant_msg = nv_chat(history)

            # Loop will check if the model wants to call another tool (retry) or finalize
        else:
            # Loop exhausted (model kept calling tools); print last model message
            print(assistant_msg)
            history.append({"role":"assistant","content": assistant_msg})

    hub.close()

if __name__ == "__main__":
    main()
