#!/usr/bin/env python3
# build_people_volunteers_from_sources.py
# Deterministic ETL to build people_volunteers dataset from real CSV/TSV sources.
# Produces:
#   - people_volunteers.csv
#   - people_volunteers.jsonl
#   - people_volunteers_rag.jsonl

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

TARGET_STATES = {"DC","VA","MD","NY","FL"}

# Canonical output schema
OUT_FIELDS = [
    "resources_offered","location","details","posted_by",
    "contact_method","source_platform","source_post_id",
    "post_time","availability_window","skills","capacity_notes",
    "latitude","longitude","state","city"
]

# Column name aliases we’ll recognize from common sources (CrisisCleanup, VOAD, Google Forms, etc.)
ALIASES = {
    "resources_offered": {"resources_offered","resources","offer","offered","what_can_you_offer","capabilities"},
    "location": {"location","address","full_address","site","where"},
    "details": {"details","notes","description","summary","request_context","offer_details"},
    "posted_by": {"posted_by","name","contact_name","point_of_contact","poc"},
    "contact_method": {"contact_method","contact","phone_email","contact_info","phone","email"},
    "source_platform": {"source_platform","platform","source","origin"},
    "source_post_id": {"source_post_id","post_id","ticket_id","record_id","case_id","id"},
    "post_time": {"post_time","timestamp","submitted_at","created_at","date"},
    "availability_window": {"availability_window","availability","when_available","time_window"},
    "skills": {"skills","skillset","certifications"},
    "capacity_notes": {"capacity_notes","capacity","team_size","headcount","qty","quantity"},
    "latitude": {"latitude","lat"},
    "longitude": {"longitude","lon","lng","long"},
    "state": {"state","us_state","province"},
    "city": {"city","municipality","locality","town"}
}

# Helper to parse CSV/TSV with delimiter sniffing
def read_tabular(path: str) -> Tuple[List[str], List[Dict[str,str]]]:
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
        except csv.Error:
            class Simple(csv.Dialect):
                delimiter = ","
                quotechar = '"'
                doublequote = True
                lineterminator = "\n"
                escapechar = None
                quoting = csv.QUOTE_MINIMAL
            dialect = Simple()
        reader = csv.DictReader(f, dialect=dialect)
        rows = [ { (k or "").strip(): (v or "").strip() for k,v in row.items() } for row in reader ]
        return [h.strip() for h in reader.fieldnames or []], rows

def normalize_header_map(headers: List[str]) -> Dict[str,str]:
    # Map each canonical field to the best matching source column (if present)
    hset = {h.lower(): h for h in headers}
    mapping = {}
    for canonical, aliases in ALIASES.items():
        for a in aliases:
            if a.lower() in hset:
                mapping[canonical] = hset[a.lower()]
                break
    return mapping

def coalesce(row: Dict[str,str], mapping: Dict[str,str], key: str) -> Optional[str]:
    src = mapping.get(key)
    val = (row.get(src) if src else "") or ""
    val = val.strip()
    return val or None

def parse_iso(dt: Optional[str]) -> Optional[str]:
    if not dt: return None
    dt = dt.strip()
    if not dt: return None
    # Try a few common patterns -> ISO8601
    patterns = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y",
        "%d-%b-%Y %H:%M",
        "%d-%b-%Y",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d",
    ]
    for p in patterns:
        try:
            return datetime.strptime(dt, p).isoformat()
        except ValueError:
            continue
    # As-is if it already looks like ISO 8601
    try:
        return datetime.fromisoformat(dt.replace("Z","")).isoformat()
    except Exception:
        return dt  # keep original string; don’t invent

def parse_latlon(s: Optional[str]) -> Optional[str]:
    if s is None: return None
    s = s.strip()
    if not s: return None
    try:
        float(s)
        return s
    except Exception:
        return None

def infer_state(val: Optional[str]) -> Optional[str]:
    if not val: return None
    v = val.strip().upper()
    # Allow "District of Columbia" -> DC
    if v in {"DC","D.C.","DISTRICT OF COLUMBIA"}:
        return "DC"
    if v in {"VA","VIRGINIA"}:
        return "VA"
    if v in {"MD","MARYLAND"}:
        return "MD"
    if v in {"NY","NEW YORK"}:
        return "NY"
    if v in {"FL","FLORIDA"}:
        return "FL"
    # If state embedded in a location string: "... , VA" etc.
    for abbr in TARGET_STATES:
        token = f", {abbr}"
        if token in v:
            return abbr
    return None

def join_location(city: Optional[str], state: Optional[str], location: Optional[str]) -> Optional[str]:
    # Prefer a full location string from source; else synthesize "City, ST"
    if location and location.strip():
        return location.strip()
    parts = [ (city or "").strip(), (state or "").strip() ]
    if any(parts):
        return ", ".join([p for p in parts if p])
    return None

def normalize_row(row: Dict[str,str], mapping: Dict[str,str]) -> Dict[str,Optional[str]]:
    state = infer_state(coalesce(row, mapping, "state"))
    if state is None:
        # Try to extract from free-text location if provided
        state = infer_state(coalesce(row, mapping, "location"))
    city = coalesce(row, mapping, "city")
    location = join_location(city, state, coalesce(row, mapping, "location"))

    out = {
        "resources_offered": coalesce(row, mapping, "resources_offered"),
        "location": location,
        "details": coalesce(row, mapping, "details"),
        "posted_by": coalesce(row, mapping, "posted_by"),
        "contact_method": coalesce(row, mapping, "contact_method"),
        "source_platform": coalesce(row, mapping, "source_platform"),
        "source_post_id": coalesce(row, mapping, "source_post_id"),
        "post_time": parse_iso(coalesce(row, mapping, "post_time")),
        "availability_window": coalesce(row, mapping, "availability_window"),
        "skills": coalesce(row, mapping, "skills"),
        "capacity_notes": coalesce(row, mapping, "capacity_notes"),
        "latitude": parse_latlon(coalesce(row, mapping, "latitude")),
        "longitude": parse_latlon(coalesce(row, mapping, "longitude")),
        "state": state,
        "city": city
    }
    return out

def row_is_useful(r: Dict[str,Optional[str]]) -> bool:
    # Require at least resources_offered OR details, and some location signal in target states
    if not (r.get("resources_offered") or r.get("details")):
        return False
    st = r.get("state")
    if st not in TARGET_STATES:
        return False
    return True

def dedupe(rows: List[Dict[str,Optional[str]]]) -> List[Dict[str,Optional[str]]]:
    # Key on (posted_by, details, location, post_time); stable, deterministic
    seen = set()
    out = []
    for r in rows:
        key = (
            (r.get("posted_by") or "").lower(),
            (r.get("details") or "").lower(),
            (r.get("location") or "").lower(),
            (r.get("post_time") or "").lower()
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out

def enforce_fields(row: Dict[str,Optional[str]]) -> Dict[str,Optional[str]]:
    # Ensure every output row has all fields (even if None)
    return {k: row.get(k) for k in OUT_FIELDS}

def process_file(path: str) -> List[Dict[str,Optional[str]]]:
    headers, rows = read_tabular(path)
    if not rows:
        return []
    mapping = normalize_header_map(headers)
    normalized = [normalize_row(r, mapping) for r in rows]
    filtered = [r for r in normalized if row_is_useful(r)]
    return [enforce_fields(r) for r in filtered]

def write_csv(rows: List[Dict[str,Optional[str]]], out_path: str):
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: (r[k] if r[k] is not None else "") for k in OUT_FIELDS})

def write_jsonl(rows: List[Dict[str,Optional[str]]], out_path: str):
    with open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def write_rag_jsonl(rows: List[Dict[str,Optional[str]]], out_path: str):
    with open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            text = (
                f"Volunteer Offer | Resources: {r.get('resources_offered') or 'N/A'} | "
                f"Location: {r.get('location') or 'N/A'} | "
                f"Details: {r.get('details') or 'N/A'} | "
                f"Posted By: {r.get('posted_by') or 'N/A'} | "
                f"Contact: {r.get('contact_method') or 'N/A'} | "
                f"Skills: {r.get('skills') or 'N/A'} | "
                f"Availability: {r.get('availability_window') or 'N/A'}"
            )
            doc = {
                "id": "|".join([
                    (r.get("posted_by") or "unknown"),
                    (r.get("location") or "unknown"),
                    (r.get("post_time") or "unknown")
                ]),
                "text": text,
                "metadata": r
            }
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

def main():
    ap = argparse.ArgumentParser(description="Build people_volunteers dataset from real CSV/TSV inputs.")
    ap.add_argument("--inputs", nargs="+", required=True, help="One or more CSV/TSV files (CrisisCleanup, VOAD, Google Form exports, etc.).")
    ap.add_argument("--outdir", default=".", help="Output directory (default: current).")
    args = ap.parse_args()

    all_rows: List[Dict[str,Optional[str]]] = []
    for p in args.inputs:
        if not os.path.exists(p):
            print(f"[WARN] Missing input: {p}", file=sys.stderr)
            continue
        rows = process_file(p)
        print(f"[INFO] {p}: {len(rows)} usable rows after filtering/normalization.")
        all_rows.extend(rows)

    if not all_rows:
        print("[INFO] No usable rows found in provided inputs. Nothing to write.", file=sys.stderr)
        sys.exit(0)

    # Deduplicate and sort (by state, city, posted_by, post_time) for determinism
    all_rows = dedupe(all_rows)
    all_rows.sort(key=lambda r: (
        r.get("state") or "",
        r.get("city") or "",
        r.get("posted_by") or "",
        r.get("post_time") or ""
    ))

    os.makedirs(args.outdir, exist_ok=True)
    csv_out = os.path.join(args.outdir, "people_volunteers.csv")
    jsonl_out = os.path.join(args.outdir, "people_volunteers.jsonl")
    rag_out = os.path.join(args.outdir, "people_volunteers_rag.jsonl")

    write_csv(all_rows, csv_out)
    write_jsonl(all_rows, jsonl_out)
    write_rag_jsonl(all_rows, rag_out)

    print(f"[DONE] Wrote {len(all_rows)} rows:")
    print(f"  - {csv_out}")
    print(f"  - {jsonl_out}")
    print(f"  - {rag_out}")

if __name__ == "__main__":
    main()
