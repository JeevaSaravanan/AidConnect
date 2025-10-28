#!/usr/bin/env python3
"""
Lightweight FastAPI server exposing standardized endpoints that proxy
to existing helpers in this repository.

Endpoints:
 - GET  /health
 - POST /weather          { "city": "..." }
 - POST /disaster_plan    { "city": "...", "hazard": "..." }
 - POST /arcgis_query    { "data_api_url": "...", "where": "...", "fields": "...", "limit": 100 }
 - POST /fema_query      { "dataset": "...", ... }
 - POST /chat            { "messages": [{"role":"user","content":"..."}, ...] }

This server aims to standardize input shapes for local tooling and testing.
"""
from typing import List, Optional, Dict, Any
from pathlib import Path

import asyncio
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import existing helpers from the repo. These modules do not start servers at
# import-time (their mcp.run() is guarded by __main__), so safe to import.
import httpx
import json
from llm_utils import nv_chat, initialize_rag, nv_chat_rag
import uuid
from pathlib import Path as _Path

# Load default disaster context to use with assistant/chat endpoints
_DEFAULT_DISASTER_PATH = _Path(__file__).resolve().parent / "default_disaster.json"
try:
    if _DEFAULT_DISASTER_PATH.exists():
        with _DEFAULT_DISASTER_PATH.open("r", encoding="utf-8") as _dfh:
            _DEFAULT_DISASTER = json.load(_dfh)
    else:
        _DEFAULT_DISASTER = None
except Exception:
    _DEFAULT_DISASTER = None

# In-memory conversation store: session_id -> list[message]
CONVERSATIONS: Dict[str, List[Dict[str, str]]] = {}

# Global flag to track if RAG is available
RAG_ENABLED = False

# We'll implement small local wrappers that mirror the behavior of the
# decorated MCP tool functions in this repo. This avoids calling the
# non-callable FunctionTool objects returned by the FastMCP decorator.


_WEATHER_CACHE: Dict[str, tuple[float, str]] = {}
_WEATHER_TTL = 300  # seconds


def _cache_get(key: str) -> Optional[str]:
    v = _WEATHER_CACHE.get(key)
    if not v:
        return None
    ts, val = v
    if time.time() - ts > _WEATHER_TTL:
        del _WEATHER_CACHE[key]
        return None
    return val


def _cache_set(key: str, val: str) -> None:
    _WEATHER_CACHE[key] = (time.time(), val)


def call_weather_api(city: Optional[str] = None, lat: Optional[float] = None, lon: Optional[float] = None) -> str:
    """Call geocoding + open-meteo APIs and return JSON text.
    Accepts either city OR explicit lat/lon. Uses a small in-memory cache.
    """
    # If explicit coords provided, use them directly
    if lat is not None and lon is not None:
        key = f"{lat:.6f},{lon:.6f}"
        cached = _cache_get(key)
        if cached:
            return cached
        qlat, qlon = lat, lon
    else:
        if not city:
            return json.dumps({"error": "city or lat/lon required"}, indent=2)
        # Try multiple name variations to increase chances of matching the geocoder
        name = city.strip()
        candidates = [name]
        # remove commas
        no_comma = name.replace(",", "")
        if no_comma != name:
            candidates.append(no_comma)
        # take only portion before comma (e.g., "Washington" from "Washington, DC")
        if "," in name:
            before = name.split(",")[0].strip()
            if before and before not in candidates:
                candidates.append(before)
        # common DC variants
        if "washington" in name.lower() and "dc" not in name.lower():
            candidates.extend(["Washington DC", "Washington, D.C.", "Washington, District of Columbia"])
        # also try with/without periods
        if "d.c." in name.lower() and "dc" not in name.lower():
            candidates.append(name.lower().replace("d.c.", "DC"))

        seen = set()
        g = None
        qlat = qlon = None
        for cand in candidates:
            c = cand.strip()
            if not c or c in seen:
                continue
            seen.add(c)
            try:
                geo = httpx.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params={"name": c, "count": 1, "language": "en"},
                    timeout=10,
                )
                geo.raise_for_status()
                g = geo.json()
                if g.get("results"):
                    r0 = g["results"][0]
                    qlat, qlon = r0["latitude"], r0["longitude"]
                    break
            except Exception:
                # try next candidate
                g = None
                continue

        if (not g or not g.get("results")) and (qlat is None or qlon is None):
            # fallback: try Nominatim (OpenStreetMap)
            try:
                nom = httpx.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": city, "format": "json", "limit": 1},
                    headers={"User-Agent": "mcp-hub/1.0 (+https://example.local)"},
                    timeout=10,
                )
                nom.raise_for_status()
                arr = nom.json()
                if arr:
                    r0 = arr[0]
                    qlat, qlon = float(r0["lat"]), float(r0["lon"])
            except Exception:
                pass

        if qlat is None or qlon is None:
            return json.dumps({"error": f"City not found: {city}"}, indent=2)

        key = f"{qlat:.6f},{qlon:.6f}"

    # Use qlat/qlon for the weather API
    wx = httpx.get(
        "https://api.open-meteo.com/v1/forecast",
        params={"latitude": qlat, "longitude": qlon, "current_weather": "true"},
        timeout=10,
    )
    wx.raise_for_status()
    data = wx.json()
    # try to include a friendly _geo block
    try:
        name_label = r0.get("name") if 'r0' in locals() and isinstance(r0, dict) else city
    except Exception:
        name_label = city
    data["_geo"] = {
        "city": name_label,
        "lat": qlat,
        "lon": qlon,
        "country": r0.get("country") if 'r0' in locals() and isinstance(r0, dict) else None,
    }
    out = json.dumps(data, indent=2)
    _cache_set(key, out)
    return out


def call_arcgis_api(data_api_url: str, where: str = "1=1", fields: Optional[str] = None, limit: int = 100, offset: int = 0, bbox: Optional[str] = None) -> str:
    qurl = data_api_url.rstrip("/") + "/query"
    params = {
        "where": where,
        "limit": max(1, min(int(limit), 1000)),
        "offset": max(0, int(offset)),
        "f": "geojson",
    }
    if fields:
        params["outFields"] = fields
    if bbox:
        params["bbox"] = bbox

    headers = {"Accept": "application/geo+json, application/json"}
    with httpx.Client(timeout=20) as client:
        r = client.get(qurl, params=params, headers=headers)
        r.raise_for_status()
        try:
            data = r.json()
        except Exception:
            return r.text
    return json.dumps(data, indent=2)


def call_fema_api(dataset: str, filter: Optional[str] = None, select: Optional[str] = None, orderby: Optional[str] = None, top: int = 50, skip: int = 0) -> str:
    BASE = "https://www.fema.gov/api/open/v2"
    url = f"{BASE}/{dataset}"
    params = {
        "$format": "json",
        "$top": max(1, min(int(top), 1000)),
        "$skip": max(0, int(skip)),
    }
    if filter:
        params["$filter"] = filter
    if select:
        params["$select"] = select
    if orderby:
        params["$orderby"] = orderby

    with httpx.Client(timeout=20) as client:
        r = client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
    return json.dumps(data, indent=2)


def _read_jsonl_file(fname: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Read a JSONL file located next to this module and return a slice as Python objects.

    Args:
        fname: filename (relative to this file's directory)
        limit: maximum number of items to return
        offset: number of items to skip from the start

    Returns:
        list of parsed JSON objects
    """
    base = Path(__file__).resolve().parent
    path = base / fname
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")

    results: List[Dict[str, Any]] = []
    # Read lazily but collect only requested slice to avoid memory pressure for huge files
    start = max(0, int(offset))
    maxn = max(0, int(limit))
    idx = 0
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            if idx < start:
                idx += 1
                continue
            try:
                obj = json.loads(line)
            except Exception:
                # skip malformed lines but continue
                idx += 1
                continue
            results.append(obj)
            idx += 1
            if maxn and len(results) >= maxn:
                break
    return results


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in kilometers between two points using the Haversine formula."""
    from math import radians, sin, cos, asin, sqrt

    # convert degrees to radians
    rlat1, rlon1, rlat2, rlon2 = map(radians, (lat1, lon1, lat2, lon2))
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = sin(dlat / 2) ** 2 + cos(rlat1) * cos(rlat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    R = 6371.0
    return R * c


def _extract_latlon(item: Dict[str, Any]) -> Optional[tuple[float, float]]:
    """Try common keys to find latitude/longitude in a record.

    This is defensive: JSONL records in this repo may store coords under
    different keys (lat/lon, latitude/longitude, geometry, _geo).
    """
    # direct lat/lon
    for plat in ("lat", "latitude"):
        for plon in ("lon", "lng", "longitude"):
            if plat in item and plon in item:
                try:
                    return float(item[plat]), float(item[plon])
                except Exception:
                    pass

    # nested _geo or geometry {lat, lon} or geometry.coordinates [lon, lat]
    geo = item.get("_geo") or item.get("geo") or item.get("geometry")
    if isinstance(geo, dict):
        if "lat" in geo and "lon" in geo:
            try:
                return float(geo["lat"]), float(geo["lon"])
            except Exception:
                pass
        if "latitude" in geo and "longitude" in geo:
            try:
                return float(geo["latitude"]), float(geo["longitude"])
            except Exception:
                pass
        # GeoJSON geometry: {"type":"Point","coordinates": [lon, lat]}
        if "coordinates" in geo and isinstance(geo["coordinates"], (list, tuple)) and len(geo["coordinates"]) >= 2:
            try:
                lon, lat = geo["coordinates"][0], geo["coordinates"][1]
                return float(lat), float(lon)
            except Exception:
                pass

    # fallback: try top-level coordinates as list
    for key in ("coordinates", "loc"):
        val = item.get(key)
        if isinstance(val, (list, tuple)) and len(val) >= 2:
            try:
                # assume [lon, lat] or [lat, lon] - try both
                a, b = float(val[0]), float(val[1])
                # crude heuristic: lat in [-90,90]
                if -90 <= a <= 90 and -180 <= b <= 180:
                    return a, b
                if -90 <= b <= 90 and -180 <= a <= 180:
                    return b, a
            except Exception:
                pass

    return None


def _get_resources_from_item(item: Dict[str, Any]) -> List[str]:
    """Extract a list of resource strings from item, handling common shapes."""
    res = item.get("resources") or item.get("resource") or item.get("skills")
    if res is None:
        return []
    if isinstance(res, list):
        return [str(x).strip() for x in res if x is not None]
    if isinstance(res, str):
        # split on commas or pipes
        parts = [p.strip() for p in res.replace("|", ",").split(",") if p.strip()]
        return parts
    # unknown type
    try:
        return [str(res)]
    except Exception:
        return []


def _filter_and_rank(items: List[Dict[str, Any]], name: Optional[str] = None, lat: Optional[float] = None, lon: Optional[float] = None, max_distance_km: Optional[float] = None, k: Optional[int] = None) -> List[Dict[str, Any]]:
    """Filter items by name and optionally compute distance to lat/lon and return ranked list.

    - name: substring match against common fields (name, title, address)
    - lat/lon: if provided, compute distance and add 'distance_km' to items and sort ascending
    - max_distance_km: if provided, filter to items within this radius
    - k: if provided with lat/lon, return top-k nearest after filtering
    """
    filtered: List[Dict[str, Any]] = []
    lname = name.lower() if name else None
    # If caller provided k (top-k) along with lat/lon, treat k as a request
    # for the nearest k items regardless of max_distance_km. In that case,
    # we will compute distances for all items and defer radius filtering.
    use_k_override = (lat is not None and lon is not None and k is not None and int(k) > 0)

    for it in items:
        if lname:
            found = False
            for key in ("name", "title", "address", "label"):
                v = it.get(key)
                if isinstance(v, str) and lname in v.lower():
                    found = True
                    break
            if not found:
                # also check nested _geo.city
                geo = it.get("_geo")
                if geo and isinstance(geo, dict):
                    city = geo.get("city")
                    if isinstance(city, str) and lname in city.lower():
                        found = True
            if not found:
                continue

        # attach coordinate if available
        if lat is not None and lon is not None:
            pair = _extract_latlon(it)
            if pair:
                lat2, lon2 = pair
                try:
                    d = _haversine_km(lat, lon, lat2, lon2)
                    it = dict(it)  # shallow copy so we don't mutate original
                    it["distance_km"] = round(d, 3)
                except Exception:
                    it["distance_km"] = None
            else:
                it = dict(it)
                it["distance_km"] = None

            # Apply radius filtering only when max_distance_km is provided and
            # we're NOT in top-k override mode. If k is requested, we'll
            # return the nearest k items regardless of distance.
            if (not use_k_override) and max_distance_km is not None:
                if it.get("distance_km") is None or it.get("distance_km") > float(max_distance_km):
                    continue

        filtered.append(it)

    # if distances present, sort by distance
    if lat is not None and lon is not None:
        filtered.sort(key=lambda x: (float(x["distance_km"]) if x.get("distance_km") is not None else float("inf")))
        if k is not None and int(k) > 0:
            return filtered[: int(k)]

    return filtered

app = FastAPI(title="mcp-hub API", version="0.1.0")

# Allow CORS from local dev frontends (vite dev server). Add other origins as needed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize RAG system at server startup."""
    global RAG_ENABLED
    print("[STARTUP] Initializing RAG system...")
    try:
        # Initialize RAG with PDFs from data folder
        success = initialize_rag(pdf_dir="../data")
        if success:
            RAG_ENABLED = True
            print("[STARTUP] ✓ RAG system initialized successfully!")
            print("[STARTUP] Documents loaded: shelter policies, homeless services, donation info")
        else:
            print("[STARTUP] ⚠ RAG initialization failed - chat will work without document context")
    except Exception as e:
        print(f"[STARTUP] ⚠ RAG initialization error: {e}")
        print("[STARTUP] Chat will continue without RAG functionality")


@app.get("/health")
def health():
    """Health check endpoint with RAG status."""
    return {
        "ok": True,
        "service": "mcp-hub API",
        "rag_enabled": RAG_ENABLED,
        "features": ["weather", "disaster_plan", "arcgis", "fema", "chat", "rag" if RAG_ENABLED else None]
    }


class WeatherRequest(BaseModel):
    city: str


class DisasterPlanRequest(BaseModel):
    city: str
    hazard: Optional[str] = "flood"


class ArcGISRequest(BaseModel):
    data_api_url: str
    where: Optional[str] = "1=1"
    fields: Optional[str] = None
    limit: Optional[int] = 100
    offset: Optional[int] = 0
    bbox: Optional[str] = None


class FEMARequest(BaseModel):
    dataset: str
    filter: Optional[str] = None
    select: Optional[str] = None
    orderby: Optional[str] = None
    top: Optional[int] = 50
    skip: Optional[int] = 0


class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    max_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.7
    use_rag: Optional[bool] = True  # Enable RAG by default if available
    rag_k: Optional[int] = 4  # Number of document chunks to retrieve


@app.post("/weather")
def api_weather(req: WeatherRequest):
    try:
        # weather_now returns JSON text; try to parse to structured JSON when possible
        txt = call_weather_api(req.city)
        try:
            import json
            data = json.loads(txt)
            return {"ok": True, "data": data}
        except Exception:
            return {"ok": True, "data": txt}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/disaster_plan")
async def api_disaster_plan(req: DisasterPlanRequest):
    try:
        # Compose weather + LLM guidance into a concise, actionable disaster plan.
        wx_text = call_weather_api(req.city)
        sys_msg = (
            "You are a disaster response planner. Produce a concise, actionable plan "
            "with: Situation Summary, Risks, 6-Hour Actions, 24-Hour Actions, "
            "Resources (teams/equipment), and Public Messaging. Use the provided weather JSON."
        )
        user_msg = f"City: {req.city}\nHazard: {req.hazard}\nWeather JSON:\n{wx_text}"
        out = nv_chat(messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": user_msg}], max_tokens=700, temperature=0.2)
        return {"ok": True, "plan": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/arcgis_query")
def api_arcgis(req: ArcGISRequest):
    try:
        out = call_arcgis_api(
            data_api_url=req.data_api_url,
            where=req.where,
            fields=req.fields,
            limit=req.limit,
            offset=req.offset,
            bbox=req.bbox,
        )
        # arcgis_query returns JSON text; try to parse
        try:
            import json
            return {"ok": True, "data": json.loads(out)}
        except Exception:
            return {"ok": True, "data": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/fema_query")
def api_fema(req: FEMARequest):
    try:
        out = call_fema_api(
            dataset=req.dataset,
            filter=req.filter,
            select=req.select,
            orderby=req.orderby,
            top=req.top or 50,
            skip=req.skip or 0,
        )
        try:
            import json
            return {"ok": True, "data": json.loads(out)}
        except Exception:
            return {"ok": True, "data": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/volunteers")
def api_volunteers(
    limit: int = 100,
    offset: int = 0,
    name: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    max_distance_km: Optional[float] = None,
    k: Optional[int] = None,
    group_by_resources: Optional[bool] = False,
):
    """Return volunteers with advanced query options:

    - name: substring match against name/title/address
    - lat, lon: compute distance to each record and optionally rank/filter
    - max_distance_km: filter to items within this radius
    - k: when lat/lon provided, return top-k nearest
    - group_by_resources: if true, return grouping by resource types
    """
    try:
        items = _read_jsonl_file("people_volunteers.jsonl", limit=1000000000, offset=0)

        # Apply name / distance / k filters
        results = _filter_and_rank(items, name=name, lat=lat, lon=lon, max_distance_km=max_distance_km, k=k)

        # apply offset/limit only when not ranking by nearest (i.e., lat/lon given with k)
        if not (lat is not None and lon is not None and k is not None):
            # apply offset+limit on the filtered results
            start = max(0, int(offset))
            end = start + max(0, int(limit)) if limit and limit > 0 else None
            results = results[start:end]

        if group_by_resources:
            groups: Dict[str, Dict[str, Any]] = {}
            for it in results:
                for r in _get_resources_from_item(it):
                    g = groups.setdefault(r, {"count": 0, "items": []})
                    g["count"] += 1
                    g["items"].append(it)
            return {"ok": True, "count": len(results), "groups": groups}

        return {"ok": True, "count": len(results), "data": results}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/shelters")
def api_shelters(
    limit: int = 100,
    offset: int = 0,
    name: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    max_distance_km: Optional[float] = None,
    k: Optional[int] = None,
):
    """Return shelters with optional name filtering and nearby/top-k options.

    Same semantics as /volunteers for name/lat/lon/max_distance_km/k.
    """
    try:
        items = _read_jsonl_file("shelters_actual.jsonl", limit=1000000000, offset=0)
        results = _filter_and_rank(items, name=name, lat=lat, lon=lon, max_distance_km=max_distance_km, k=k)

        if not (lat is not None and lon is not None and k is not None):
            start = max(0, int(offset))
            end = start + max(0, int(limit)) if limit and limit > 0 else None
            results = results[start:end]

        return {"ok": True, "count": len(results), "data": results}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
def api_chat(req: ChatRequest):
    """
    Chat endpoint with optional RAG support.
    
    If use_rag=True and RAG is enabled, the last user message will be enhanced
    with relevant context from PDF documents about shelters, homeless services, and donations.
    """
    try:
        # Check if we should use RAG
        should_use_rag = req.use_rag and RAG_ENABLED
        
        if should_use_rag:
            # Extract the last user message for RAG query
            user_message = None
            for msg in reversed(req.messages):
                if msg.get("role") == "user":
                    user_message = msg.get("content", "")
                    break
            
            if user_message:
                # Check if the query is relevant to our documents (shelters, homeless services, donations)
                relevant_keywords = [
                    "shelter", "homeless", "donate", "donation", "volunteer",
                    "service", "housing", "emergency", "food", "clothing",
                    "charity", "help", "assistance", "resource", "facility"
                ]
                
                query_lower = user_message.lower()
                is_relevant = any(keyword in query_lower for keyword in relevant_keywords)
                
                if is_relevant:
                    # Use RAG-enabled chat
                    out = nv_chat_rag(
                        question=user_message,
                        max_tokens=req.max_tokens,
                        temperature=req.temperature,
                        k=req.rag_k
                    )
                    return {"ok": True, "response": out, "rag_used": True}
        
        # Fall back to regular chat (no RAG)
        out = nv_chat(req.messages, max_tokens=req.max_tokens, temperature=req.temperature)
        return {"ok": True, "response": out, "rag_used": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AssistantRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None


@app.post("/assistant")
def api_assistant(req: AssistantRequest):
    """A helpful interactive assistant endpoint that injects the default disaster context
    into the LLM system prompt. Returns the assistant's text reply.
    """
    try:
        system = (
            "You are AidConnect Assistant — a helpful, concise, and interactive disaster response assistant. "
            "You have access to a `disaster` JSON object describing the current incident (location, areas affected, resources needed). "
            "When answering, prioritize safety, urgent needs, suggested actions with ETA estimates, and concise lists of next steps."
        )

        messages = [
            {"role": "system", "content": system},
        ]

        # attach default disaster context if available
        if _DEFAULT_DISASTER is not None:
            messages.append({"role": "system", "content": f"disaster_context: {json.dumps(_DEFAULT_DISASTER)}"})

        # add user's query
        messages.append({"role": "user", "content": req.query})

        out = nv_chat(messages, max_tokens=700, temperature=0.2)
        return {"ok": True, "reply": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AssistantConverseRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    max_history: Optional[int] = 8


def _execute_tool_call(tool_name: str, tool_args: Dict[str, Any]) -> str:
    """Execute a tool function by name and return its result as a string."""
    try:
        if tool_name == "call_weather_api":
            city = tool_args.get("city")
            lat = tool_args.get("lat")
            lon = tool_args.get("lon")
            return call_weather_api(city=city, lat=lat, lon=lon)
        elif tool_name == "call_arcgis_api":
            return call_arcgis_api(**tool_args)
        elif tool_name == "call_fema_api":
            return call_fema_api(**tool_args)
        elif tool_name == "search_volunteers":
            items = _read_jsonl_file("people_volunteers.jsonl", limit=1000000000, offset=0)
            results = _filter_and_rank(items, **tool_args)
            return json.dumps({"count": len(results), "data": results[:10]}, indent=2)
        elif tool_name == "search_shelters":
            items = _read_jsonl_file("shelters_actual.jsonl", limit=1000000000, offset=0)
            results = _filter_and_rank(items, **tool_args)
            return json.dumps({"count": len(results), "data": results[:10]}, indent=2)
        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


def _parse_tool_calls(text: str) -> List[Dict[str, Any]]:
    """Parse tool calls from LLM response text in the format: <tool_call>{"name":"...", "arguments":{...}}</tool_call>"""
    import re
    tool_calls = []
    pattern = r'<tool_call>(.*?)</tool_call>'
    matches = re.findall(pattern, text, re.DOTALL)
    for match in matches:
        try:
            call_data = json.loads(match.strip())
            tool_calls.append(call_data)
        except Exception:
            continue
    return tool_calls


def _should_use_rag(message: str) -> bool:
    """
    Determine if a message is relevant to RAG documents.
    Returns True if the message asks about shelters, homeless services, donations, etc.
    """
    if not RAG_ENABLED:
        return False
    
    relevant_keywords = [
        "shelter", "homeless", "donate", "donation", "volunteer",
        "service", "housing", "emergency housing", "food", "clothing",
        "charity", "help", "assistance", "resource", "facility",
        "sop", "policy", "policies", "procedure", "operating",
        "alexandria", "dc area", "washington", "give away", "stuff"
    ]
    
    query_lower = message.lower()
    return any(keyword in query_lower for keyword in relevant_keywords)


def _enhance_message_with_rag(message: str, max_tokens: int = 400) -> str:
    """
    Use RAG to enhance a message with relevant document context.
    Returns the RAG-enhanced response.
    """
    if not RAG_ENABLED:
        return message
    
    try:
        return nv_chat_rag(
            question=message,
            max_tokens=max_tokens,
            temperature=0.2,
            k=4
        )
    except Exception as e:
        print(f"[RAG ERROR] Failed to enhance message: {e}")
        return message


def _detect_and_inject_tool_call(user_message: str) -> Optional[str]:
    """Detect common query patterns and inject appropriate tool calls.
    
    This helps when the LLM doesn't naturally generate tool calls.
    Returns a synthetic assistant message with tool call, or None if no pattern matches.
    """
    import re
    
    msg_lower = user_message.lower()
    
    # Weather patterns
    weather_patterns = [
        r'weather.*in\s+([a-zA-Z\s,]+)',
        r'what.*weather.*([a-zA-Z\s,]+)',
        r'how.*weather.*([a-zA-Z\s,]+)',
        r'temperature.*in\s+([a-zA-Z\s,]+)',
        r'forecast.*for\s+([a-zA-Z\s,]+)',
    ]
    
    for pattern in weather_patterns:
        match = re.search(pattern, msg_lower)
        if match:
            city = match.group(1).strip()
            # Clean up common words
            city = re.sub(r'\b(today|now|currently|the)\b', '', city).strip()
            if city:
                tool_call = f'<tool_call>{{"name": "call_weather_api", "arguments": {{"city": "{city}"}}}}</tool_call>'
                return tool_call
    
    # Volunteer patterns
    volunteer_patterns = [
        r'find.*volunteers?.*in\s+([a-zA-Z\s,]+)',
        r'volunteers?.*near\s+([a-zA-Z\s,]+)',
        r'list.*volunteers?',
    ]
    
    for pattern in volunteer_patterns:
        match = re.search(pattern, msg_lower)
        if match:
            location = match.group(1).strip() if match.lastindex else None
            args = {"name": location} if location else {}
            tool_call = f'<tool_call>{{"name": "search_volunteers", "arguments": {json.dumps(args)}}}</tool_call>'
            return tool_call
    
    # Shelter patterns
    shelter_patterns = [
        r'find.*shelters?.*in\s+([a-zA-Z\s,]+)',
        r'shelters?.*near\s+([a-zA-Z\s,]+)',
        r'list.*shelters?',
    ]
    
    for pattern in shelter_patterns:
        match = re.search(pattern, msg_lower)
        if match:
            location = match.group(1).strip() if match.lastindex else None
            args = {"name": location} if location else {}
            tool_call = f'<tool_call>{{"name": "search_shelters", "arguments": {json.dumps(args)}}}</tool_call>'
            return tool_call
    
    return None


@app.post("/assistant/converse")
def api_assistant_converse(req: AssistantConverseRequest):
    """Sessioned conversational assistant with RAG support. 
    
    Provide session_id to continue a conversation; when omitted a new session_id is returned.
    The assistant can call tools like call_weather_api, search_volunteers, search_shelters, etc.
    For questions about shelter policies, homeless services, or donations, RAG is automatically used to provide accurate information from documents.
    """
    try:
        sid = req.session_id or str(uuid.uuid4())
        # retrieve or create conversation
        conv = CONVERSATIONS.setdefault(sid, [])

        # Check if this message should use RAG (shelter/homeless/donation queries)
        if _should_use_rag(req.message):
            # Use RAG to answer directly from documents
            rag_response = _enhance_message_with_rag(req.message, max_tokens=700)
            
            # Append user message and RAG response to conversation
            conv.append({"role": "assistant", "content": rag_response})
            
            # Keep conversation bounded
            if len(conv) > 500:
                del conv[0: len(conv) - 200]
            
            return {"ok": True, "session_id": sid, "reply": rag_response, "rag_used": True}

        # append the new user message
        conv.append({"role": "user", "content": req.message})
        
        # Try to detect if this is a tool-requiring query and inject a tool call
        injected_tool_call = _detect_and_inject_tool_call(req.message)

        # build messages for LLM: system prompt that enforces weather-tool-first behavior
        system = (
            "You are AidConnect Assistant — a concise disaster/weather assistant.\n"
            "When a user asks about weather or mentions weather-related terms (weather, forecast, temperature, precipitation, rain, snow, windy, wind, humidity, conditions), YOU MUST call the tool `call_weather_api(city: str)` to retrieve current weather.\n"
            "Do NOT guess or invent weather details; rely only on the tool output for weather answers.\n"
            "After the tool returns results, format a brief, actionable summary (1-3 sentences) and any important values (temperature, wind, precipitation).\n\n"
            "If the user's query is not about weather, continue normal behavior but do not call the weather tool.\n\n"
            "TOOL USAGE (required):\n"
            "- For any user query mentioning weather terms, respond with EXACTLY: <tool_call>{\"name\": \"call_weather_api\", \"arguments\": {\"city\": \"<City Name>\"}}</tool_call>\n"
            "- Example: User asks: \"What's the weather in Georgetown DC today?\"\n"
            "  Assistant should respond: <tool_call>{\"name\": \"call_weather_api\", \"arguments\": {\"city\": \"Georgetown DC\"}}</tool_call>\n\n"
            "After the tool result is supplied, produce the final answer based only on that result."
        )

        messages: List[Dict[str, str]] = [{"role": "system", "content": system}]
        if _DEFAULT_DISASTER is not None:
            messages.append({"role": "system", "content": f"disaster_context: {json.dumps(_DEFAULT_DISASTER)}"})

        # include last N messages (user+assistant pairs) up to max_history
        max_hist = int(req.max_history or 8)
        recent = conv[-max_hist:]
        messages.extend(recent)

        # If we detected a tool-requiring query, skip LLM and use the injected tool call directly
        if injected_tool_call:
            out = injected_tool_call
            # Execute the tool immediately
            tool_calls = _parse_tool_calls(out)
            if tool_calls:
                tool_results = []
                for tool_call in tool_calls:
                    tool_name = tool_call.get("name")
                    tool_args = tool_call.get("arguments", {})
                    result = _execute_tool_call(tool_name, tool_args)
                    tool_results.append({"tool": tool_name, "result": result})
                
                # Now ask LLM to format the response based on tool results
                messages.append({"role": "user", "content": f"Tool results:\n{json.dumps(tool_results, indent=2)}\n\nPlease provide a helpful response to the user based on these results. Be concise and actionable."})
                final_response = nv_chat(messages, max_tokens=700, temperature=0.2)
                
                conv.append({"role": "assistant", "content": final_response})
                if len(conv) > 500:
                    del conv[0: len(conv) - 200]
                
                return {"ok": True, "session_id": sid, "reply": final_response}

        # Multi-turn tool calling loop (max 3 iterations to prevent infinite loops)
        max_iterations = 3
        for iteration in range(max_iterations):
            out = nv_chat(messages, max_tokens=700, temperature=0.2)

            # Check if the response contains tool calls
            tool_calls = _parse_tool_calls(out)
            
            if not tool_calls:
                # No tool calls, this is the final response
                # append assistant reply to conversation
                conv.append({"role": "assistant", "content": out})
                
                # keep conversation bounded
                if len(conv) > 500:
                    del conv[0: len(conv) - 200]
                
                return {"ok": True, "session_id": sid, "reply": out}
            
            # Execute tool calls and add results to messages
            tool_results = []
            for tool_call in tool_calls:
                tool_name = tool_call.get("name")
                tool_args = tool_call.get("arguments", {})
                result = _execute_tool_call(tool_name, tool_args)
                tool_results.append({"tool": tool_name, "result": result})
            
            # Add assistant's tool call request and tool results to messages
            messages.append({"role": "assistant", "content": out})
            tool_results_text = json.dumps(tool_results, indent=2)
            messages.append({"role": "user", "content": f"Tool results:\n{tool_results_text}\n\nPlease provide your response based on these results."})

        # If we exhausted iterations, return the last response
        conv.append({"role": "assistant", "content": out})
        if len(conv) > 500:
            del conv[0: len(conv) - 200]
        
        return {"ok": True, "session_id": sid, "reply": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    # Run with reload False by default; let users run via uvicorn for dev reloads
    uvicorn.run("api_server:app", host="127.0.0.1", port=8000, log_level="info")
