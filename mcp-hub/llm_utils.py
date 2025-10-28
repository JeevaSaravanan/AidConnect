#!/usr/bin/env python3
"""
Central LLM helper with a small in-memory cache to deduplicate identical chat calls.

Usage: from llm_utils import nv_chat

This mirrors the previous nv_chat/_nim_call signatures and defaults.
"""
import os
import json
import hashlib
import threading
from typing import List, Dict, Optional

import httpx

# Config from environment (same defaults as existing files)
NV_URL = os.getenv("NV_INVOKE_URL", "https://integrate.api.nvidia.com/v1/chat/completions")
NV_MODEL = os.getenv("NV_MODEL", "meta/llama-4-maverick-17b-128e-instruct")
NV_KEY = os.getenv("NV_API_KEY", "")
NV_TIMEOUT = float(os.getenv("HTTP_TIMEOUT_SEC", "25"))

# Simple in-process cache
_CACHE: Dict[str, str] = {}
_LOCK = threading.Lock()


def _make_key(messages: List[Dict[str, str]], model: Optional[str], max_tokens: int, temperature: float, top_p: float) -> str:
    payload = {
        "model": model or NV_MODEL,
        "messages": messages,
        "max_tokens": int(max_tokens),
        "temperature": float(temperature),
        "top_p": float(top_p),
    }
    s = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def clear_cache() -> None:
    """Clear the in-memory cache."""
    with _LOCK:
        _CACHE.clear()


def nv_chat(messages: List[Dict[str, str]],
            model: Optional[str] = None,
            max_tokens: int = 512,
            temperature: float = 0.7,
            top_p: float = 1.0,
            use_cache: bool = True,
            force_refresh: bool = False,
            timeout: Optional[float] = None) -> str:
    """
    Call the NVIDIA Integrate chat completions endpoint.

    This function caches identical requests (messages + params) in-memory to avoid
    repeated identical LLM calls during a single process run.
    """
    if not NV_KEY:
        return "[NV ERROR] NV_API_KEY not set"
    key = _make_key(messages, model, max_tokens, temperature, top_p)
    if use_cache and not force_refresh:
        with _LOCK:
            if key in _CACHE:
                return _CACHE[key]

    used_model = model or NV_MODEL
    headers = {"Authorization": f"Bearer {NV_KEY}", "Accept": "application/json"}
    payload = {
        "model": used_model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
        "stream": False,
    }
    tout = timeout if timeout is not None else NV_TIMEOUT

    # Basic validation: NV_INVOKE_URL should be an HTTP(S) URL. If it's set to
    # something else (for example a transport indicator like "stdio"), fail
    # with a helpful message instead of raising a low-level connection error.
    if not isinstance(NV_URL, str) or not NV_URL.lower().startswith("http"):
        return f"[NV URL ERROR] NV_INVOKE_URL appears invalid: {NV_URL!r}"

    with httpx.Client(timeout=tout) as client:
        try:
            r = client.post(NV_URL, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPStatusError as e:
            return f"[NV HTTP ERROR] {e.response.status_code} {e.response.text}"
        except Exception as e:
            # Catch network/connect errors (httpx.RequestError / httpcore.ConnectError)
            return f"[NV CONNECT ERROR] {e}"

    try:
        out = data["choices"][0]["message"]["content"]
    except Exception:
        out = json.dumps(data, indent=2)

    if use_cache:
        with _LOCK:
            _CACHE[key] = out
    return out


if __name__ == "__main__":
    print("llm_utils: small helper module. Import nv_chat() in your scripts.")
