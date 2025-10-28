# arcgis_server.py
from fastmcp import FastMCP
import httpx, json
from typing import Optional

mcp = FastMCP("arcgis-mcp")

@mcp.tool
def arcgis_query(
    data_api_url: str,                # e.g., "https://hub.arcgis.com/datasets/414412681d0248988cdd9f2e8e34bc39_2/api"
    where: str = "1=1",               # standard SQL-ish clause
    fields: Optional[str] = None,     # e.g., "NAME,STATE,STATUS"
    limit: int = 100,
    offset: int = 0,
    bbox: Optional[str] = None        # "minx,miny,maxx,maxy"
) -> str:
    """
    Query an ArcGIS Hub Data API dataset via /query (GeoJSON).
    The URL should be the dataset's /api endpoint. We'll call {url}/query.

    Example:
      arcgis_query(
        data_api_url="https://hub.arcgis.com/datasets/414412681d0248988cdd9f2e8e34bc39_2/api",
        where="STATE='DC'",
        fields="NAME,STATUS",
        limit=50
      )
    """
    qurl = data_api_url.rstrip("/") + "/query"
    params = {
        "where": where,
        "limit": max(1, min(int(limit), 1000)),
        "offset": max(0, int(offset)),
        "f": "geojson",
    }
    if fields: params["outFields"] = fields
    if bbox:   params["bbox"] = bbox

    headers = {"Accept": "application/geo+json, application/json"}
    with httpx.Client(timeout=20) as client:
        r = client.get(qurl, params=params, headers=headers)
        r.raise_for_status()
        # Hub Data API often returns GeoJSON
        try:
            data = r.json()
        except Exception:
            return r.text  # fallback if not JSON
    return json.dumps(data, indent=2)

def main():
    mcp.run()

if __name__ == "__main__":
    main()
