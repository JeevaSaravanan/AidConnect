# hub_server.py
import os
import json
import asyncio
import shlex
from typing import Any, Dict, List, Optional

import httpx
from fastmcp import FastMCP
from dotenv import load_dotenv

# ── Setup ──────────────────────────────────────────────────────────────────────
load_dotenv()
mcp = FastMCP("hub-mcp")

# Child (weather) MCP command from .env
def _weather_cmd() -> list[str]:
    cmd = os.getenv("WEATHER_CMD", "python")
    args = os.getenv("WEATHER_ARGS", "weather_server.py")
    return [cmd, *shlex.split(args)]

# NVIDIA Integrate settings
NV_URL = os.getenv("NV_INVOKE_URL", "https://integrate.api.nvidia.com/v1/chat/completions")
NV_MODEL = os.getenv("NV_MODEL", "meta/llama-4-maverick-17b-128e-instruct")
NV_KEY = os.getenv("NV_API_KEY", "")
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT_SEC", "20"))

from llm_utils import nv_chat as _nim_call
# ── Minimal async NDJSON JSON-RPC to a child MCP over stdio ────────────────────
async def _send(proc: asyncio.subprocess.Process, obj: Dict[str, Any]) -> None:
    line = json.dumps(obj, separators=(",", ":")) + "\n"
    assert proc.stdin is not None
    proc.stdin.write(line.encode("utf-8"))
    await proc.stdin.drain()

async def _recv(proc: asyncio.subprocess.Process) -> Dict[str, Any]:
    assert proc.stdout is not None
    line = await proc.stdout.readline()
    if not line:
        raise RuntimeError("child MCP closed stdout")
    return json.loads(line.decode("utf-8"))

async def _mcp_call_tool(cmd: list[str], tool: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Spawn a child MCP, do handshake, call a tool, return the JSON-RPC 'result'.
    """
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        # initialize
        await _send(proc, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "hub-client", "version": "0.1.0"}
            }
        })
        init = await _recv(proc)
        if "error" in init:
            raise RuntimeError(f"child init error: {init}")

        # notifications/initialized
        await _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

        # tools/call
        await _send(proc, {
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": tool, "arguments": arguments}
        })
        call = await _recv(proc)
        if "error" in call:
            raise RuntimeError(f"child call error: {call}")
        return call["result"]
    finally:
        if proc.stdin:
            proc.stdin.close()
        try:
            await asyncio.wait_for(proc.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            proc.kill()

# ── Internal helpers ───────────────────────────────────────────────────────────
async def _get_weather_text(city: str) -> str:
    """
    Talk to the child weather MCP and return the text content.
    """
    result = await _mcp_call_tool(_weather_cmd(), "weather_now", {"city": city})
    parts = [it.get("text", "") for it in result.get("content", []) if it.get("type") == "text"]
    return "\n".join(parts) if parts else json.dumps(result, indent=2)

def _fema_cmd() -> list[str]:
    cmd = os.getenv("FEMA_CMD", "python")
    args = os.getenv("FEMA_ARGS", "fema_server.py")
    return [cmd, *shlex.split(args)]

def _arcgis_cmd() -> list[str]:
    cmd = os.getenv("ARCGIS_CMD", "python")
    args = os.getenv("ARCGIS_ARGS", "arcgis_server.py")
    return [cmd, *shlex.split(args)]


# _nim_call is an alias to llm_utils.nv_chat (cached)

# ── MCP tools ──────────────────────────────────────────────────────────────────
@mcp.tool
async def get_weather(city: str) -> str:
    """Proxy to the weather MCP; returns textified weather JSON."""
    return await _get_weather_text(city)

@mcp.tool
def nim_chat(messages: List[Dict[str, str]],
             model: Optional[str] = None,
             max_tokens: int = 512,
             temperature: float = 0.7,
             top_p: float = 1.0) -> str:
    """
    Call NVIDIA Integrate chat completions (NIM). messages=[{role, content}, ...].
    """
    return _nim_call(messages, model=model, max_tokens=max_tokens, temperature=temperature, top_p=top_p)

@mcp.tool
async def fema_query(
    dataset: str,
    filter: str | None = None,
    select: str | None = None,
    orderby: str | None = None,
    top: int = 50,
    skip: int = 0
) -> str:
    """
    Proxy to child FEMA MCP: OpenFEMA datasets.
    """
    args = {
        "dataset": dataset,
        "top": top,
        "skip": skip,
    }
    if filter:  args["filter"]  = filter
    if select:  args["select"]  = select
    if orderby: args["orderby"] = orderby

    result = await _mcp_call_tool(_fema_cmd(), "fema_query", args)
    parts = [it.get("text","") for it in result.get("content", []) if it.get("type")=="text"]
    return "\n".join(parts) if parts else json.dumps(result, indent=2)

@mcp.tool
async def arcgis_query(
    data_api_url: str,
    where: str = "1=1",
    fields: str | None = None,
    limit: int = 100,
    offset: int = 0,
    bbox: str | None = None
) -> str:
    """
    Proxy to child ArcGIS MCP: Hub Data API (GeoJSON).
    """
    args = {
        "data_api_url": data_api_url,
        "where": where,
        "limit": limit,
        "offset": offset,
    }
    if fields: args["fields"] = fields
    if bbox:   args["bbox"]   = bbox

    result = await _mcp_call_tool(_arcgis_cmd(), "arcgis_query", args)
    parts = [it.get("text","") for it in result.get("content", []) if it.get("type")=="text"]
    return "\n".join(parts) if parts else json.dumps(result, indent=2)

@mcp.tool
async def disaster_plan(city: str, hazard: str = "flood") -> str:
    """
    Compose weather + LLM guidance into a concise, actionable disaster plan.
    """
    wx_text = await _get_weather_text(city)
    sys_msg = (
        "You are a disaster response planner. Produce a concise, actionable plan "
        "with: Situation Summary, Risks, 6-Hour Actions, 24-Hour Actions, "
        "Resources (teams/equipment), and Public Messaging. Use the provided weather JSON."
    )
    user_msg = f"City: {city}\nHazard: {hazard}\nWeather JSON:\n{wx_text}"
    return _nim_call(
        messages=[{"role": "system", "content": sys_msg},
                  {"role": "user", "content": user_msg}],
        max_tokens=700,
        temperature=0.2
    )

@mcp.tool
async def match_shelter_resources(
    location: str,
    population_affected: int,
    priority_level: int,
    required_resources: Dict[str, int],
    coordinates: List[float]
) -> str:
    """
    Use LLM to match an affected area with the best 3 shelter resources.
    Returns JSON with top 3 shelter matches and reasoning.
    """
    from match_resources_api import match_resources
    
    affected_area = {
        "location": location,
        "population_affected": population_affected,
        "priority_level": priority_level,
        "required_resources": required_resources,
        "coordinates": coordinates
    }
    
    result = match_resources(affected_area)
    return json.dumps(result, indent=2)


@mcp.resource("hub://about")
def about() -> str:
    return "hub-mcp: proxies to a child weather MCP and to NVIDIA Integrate for disaster planning."

# ── Entrypoint ─────────────────────────────────────────────────────────────────
def main():
    mcp.run()  # stdio transport

if __name__ == "__main__":
    main()
