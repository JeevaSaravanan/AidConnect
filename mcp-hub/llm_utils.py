#!/usr/bin/env python3
"""
Central LLM helper with a small in-memory cache to deduplicate identical chat calls.
Now includes RAG (Retrieval Augmented Generation) support for document-based Q&A.

Usage: 
    from llm_utils import nv_chat, nv_chat_rag, initialize_rag
    
    # Initialize RAG (call once at startup)
    initialize_rag()
    
    # Use RAG-enabled chat
    answer = nv_chat_rag("What are the shelter policies?")

This mirrors the previous nv_chat/_nim_call signatures and defaults.
"""
import os
import json
import hashlib
import threading
from typing import List, Dict, Optional
from pathlib import Path

import httpx

# Config from environment (same defaults as existing files)
NV_URL = os.getenv("NV_INVOKE_URL", "https://integrate.api.nvidia.com/v1/chat/completions")
NV_MODEL = os.getenv("NV_MODEL", "nvidia/llama-3.3-nemotron-super-49b-v1.5")
NV_KEY = os.getenv("NV_API_KEY", "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")
NV_TIMEOUT = float(os.getenv("HTTP_TIMEOUT_SEC", "25"))

# Simple in-process cache
_CACHE: Dict[str, str] = {}
_LOCK = threading.Lock()

# RAG components (initialized by initialize_rag())
_VECTOR_STORE = None
_RAG_INITIALIZED = False


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


def initialize_rag(pdf_dir: str = "../data", chunk_size: int = 700, chunk_overlap: int = 50) -> bool:
    """
    Initialize RAG by loading PDFs, creating embeddings, and building vector store.
    
    Args:
        pdf_dir: Directory containing PDF files (relative to this script or absolute)
        chunk_size: Size of text chunks for splitting
        chunk_overlap: Overlap between chunks
    
    Returns:
        True if successful, False otherwise
    """
    global _VECTOR_STORE, _RAG_INITIALIZED
    
    try:
        from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
        from langchain_community.document_loaders import PyPDFDirectoryLoader
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        from langchain_community.vectorstores import FAISS
    except ImportError as e:
        print(f"[RAG ERROR] Missing dependencies: {e}")
        print("Install with: pip install langchain langchain-nvidia-ai-endpoints langchain-community faiss-cpu pypdf")
        return False
    
    if not NV_KEY:
        print("[RAG ERROR] NV_API_KEY not set")
        return False
    
    # Resolve PDF directory path
    script_dir = Path(__file__).parent
    pdf_path = Path(pdf_dir)
    if not pdf_path.is_absolute():
        pdf_path = (script_dir / pdf_path).resolve()
    
    if not pdf_path.exists():
        print(f"[RAG ERROR] PDF directory not found: {pdf_path}")
        return False
    
    print(f"[RAG] Loading PDFs from: {pdf_path}")
    
    try:
        # Load PDFs
        loader = PyPDFDirectoryLoader(str(pdf_path))
        docs = loader.load()
        
        if not docs:
            print(f"[RAG ERROR] No PDFs found in {pdf_path}")
            return False
        
        print(f"[RAG] Loaded {len(docs)} document pages")
        
        # Split documents
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        split_docs = text_splitter.split_documents(docs)
        print(f"[RAG] Created {len(split_docs)} text chunks")
        
        # Create embeddings and vector store
        embeddings = NVIDIAEmbeddings(nvidia_api_key=NV_KEY)
        _VECTOR_STORE = FAISS.from_documents(split_docs, embeddings)
        _RAG_INITIALIZED = True
        
        print(f"[RAG] Vector store initialized successfully")
        return True
        
    except Exception as e:
        print(f"[RAG ERROR] Failed to initialize: {e}")
        return False


def nv_chat_rag(question: str,
                model: Optional[str] = None,
                max_tokens: int = 512,
                temperature: float = 0.7,
                top_p: float = 1.0,
                k: int = 4,
                timeout: Optional[float] = None) -> str:
    """
    RAG-enabled chat: retrieves relevant document chunks and uses them as context.
    
    Args:
        question: User's question
        model: LLM model to use
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature
        top_p: Nucleus sampling parameter
        k: Number of relevant documents to retrieve
        timeout: Request timeout in seconds
    
    Returns:
        LLM response based on retrieved context
    """
    global _VECTOR_STORE, _RAG_INITIALIZED
    
    if not _RAG_INITIALIZED or _VECTOR_STORE is None:
        return "[RAG ERROR] RAG not initialized. Call initialize_rag() first."
    
    try:
        # Retrieve relevant documents
        relevant_docs = _VECTOR_STORE.similarity_search(question, k=k)
        
        if not relevant_docs:
            context = "No relevant documents found."
        else:
            context = "\n\n".join([doc.page_content for doc in relevant_docs])
        
        # Build RAG prompt
        rag_prompt = f"""Answer the question based on the provided context only.
Please provide the most accurate response based on the question.

<context>
{context}
</context>

Question: {question}

Answer:"""
        
        # Call LLM with context
        messages = [{"role": "user", "content": rag_prompt}]
        
        return nv_chat(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            use_cache=False,  # Don't cache RAG responses as context may change
            timeout=timeout
        )
        
    except Exception as e:
        return f"[RAG ERROR] {e}"


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
