# fema_server.py
from fastmcp import FastMCP
import httpx, json
from typing import Optional

mcp = FastMCP("fema-mcp")

BASE = "https://www.fema.gov/api/open/v2"

@mcp.tool
def fema_query(
    dataset: str,
    filter: Optional[str] = None,     # e.g., "state eq 'DC'"
    select: Optional[str] = None,     # e.g., "disasterNumber,state,declarationDate"
    orderby: Optional[str] = None,    # e.g., "declarationDate desc"
    top: int = 50,                    # 1..1000 (OpenFEMA caps)
    skip: int = 0                     # offset
) -> str:
    """
    Query an OpenFEMA dataset. Returns JSON text.

    Example:
      fema_query(dataset="DisasterDeclarationsSummaries",
                 filter="state eq 'DC'",
                 select="disasterNumber,state,declarationDate,incidentType",
                 orderby="declarationDate desc",
                 top=25)
    """
    url = f"{BASE}/{dataset}"
    # OpenFEMA uses OData-like params
    params = {
        "$format": "json",
        "$top": max(1, min(int(top), 1000)),
        "$skip": max(0, int(skip)),
    }
    if filter:  params["$filter"]  = filter
    if select:  params["$select"]  = select
    if orderby: params["$orderby"] = orderby

    with httpx.Client(timeout=20) as client:
        r = client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
    return json.dumps(data, indent=2)

def main():
    mcp.run()

if __name__ == "__main__":
    main()
