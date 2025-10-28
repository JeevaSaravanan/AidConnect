from fastmcp import FastMCP
import httpx, json

mcp = FastMCP("weather-mcp")

@mcp.tool
def weather_now(city: str) -> str:
    geo = httpx.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1, "language": "en"},
        timeout=10
    )
    geo.raise_for_status()
    g = geo.json()
    if not g.get("results"):
        return json.dumps({"error": f"City not found: {city}"}, indent=2)
    r0 = g["results"][0]; lat, lon = r0["latitude"], r0["longitude"]

    wx = httpx.get(
        "https://api.open-meteo.com/v1/forecast",
        params={"latitude": lat, "longitude": lon, "current_weather": "true"},
        timeout=10
    )
    wx.raise_for_status()
    data = wx.json()
    data["_geo"] = {"city": r0.get("name"), "lat": lat, "lon": lon, "country": r0.get("country")}
    return json.dumps(data, indent=2)

def main():
    mcp.run()

if __name__ == "__main__":
    main()
