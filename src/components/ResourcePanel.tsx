import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Package, MapPin, Clock, AlertCircle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import useDisaster from "@/hooks/use-disaster";

type Need = {
  shelter: string;
  location: string;
  items: string[];
  priority: "high" | "medium" | "low";
  eta?: string;
  lat?: number | null;
  lon?: number | null;
  distance_km?: number | null;
  eta_minutes?: number | null;
  urgency?: number; // lower = more urgent
  capacity?: number;
  status?: string;
};

const DEFAULT_API = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

const ResourcePanel = () => {
  const [needs, setNeeds] = useState<Need[]>([]);
  const [sortBy, setSortBy] = useState<"urgency" | "eta" | "distance">("urgency");
  const [radiusKm, setRadiusKm] = useState<number | "">("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { disaster } = useDisaster();

  async function fetchNeeds() {
    setLoading(true);
    setError(null);
    try {
      // Fetch shelters from shelters_actual.jsonl
      const res = await fetch('/mcp-hub/shelters_actual.jsonl');
      if (!res.ok) {
        throw new Error(`Failed to load shelters: ${res.status} ${res.statusText}`);
      }
      const text = await res.text();
      const lines = text.trim().split('\n');
      const data = lines.map(line => JSON.parse(line));

      // Take first 10 shelters
      const shelters = data.slice(0, 10);

      const mapped: Need[] = shelters.map((s: any) => {
        // Parse details to extract capacity info
        let postCap = 0;
        let evacCap = 0;
        let status = "UNKNOWN";
        
        if (s.details && typeof s.details === "string") {
          const postCapMatch = s.details.match(/post_cap=(\d+)/);
          const evacCapMatch = s.details.match(/evac_cap=(\d+)/);
          const statusMatch = s.details.match(/Status=(\w+)/);
          
          if (postCapMatch) postCap = parseInt(postCapMatch[1]);
          if (evacCapMatch) evacCap = parseInt(evacCapMatch[1]);
          if (statusMatch) status = statusMatch[1];
        }

        // Determine priority based on capacity
        const totalCap = postCap + evacCap;
        const priority: Need["priority"] = totalCap > 400 ? "high" : totalCap > 200 ? "medium" : "low";

        // Use available_items from the shelter data
        let items: string[] = [];
        if (s.available_items && Array.isArray(s.available_items)) {
          items = s.available_items;
        } else if (s.available_items && typeof s.available_items === "string") {
          items = [s.available_items];
        } else {
          items = ["No items listed"];
        }

        // Get lat/lon
        const lat = s.latitude ?? null;
        const lon = s.longitude ?? null;

        return {
          shelter: s.shelter_name || "Unknown shelter",
          location: s.location || s.city || "",
          items,
          priority,
          eta: undefined,
          lat: lat !== null ? Number(lat) : null,
          lon: lon !== null ? Number(lon) : null,
          distance_km: null,
          eta_minutes: null,
          urgency: 9999,
          capacity: totalCap,
          status,
        } as Need;
      });

      // helper: haversine distance
      const haversineKm = (lat1: number, lon1: number, lat2: number, lon2: number) => {
        const toRad = (v: number) => (v * Math.PI) / 180.0;
        const R = 6371.0;
        const dLat = toRad(lat2 - lat1);
        const dLon = toRad(lon2 - lon1);
        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
      };

      // compute ETA minutes using simple heuristic
      const baseSpeedKmh = 80; // typical road speed (km/h) in good conditions
      const roadFactor = (() => {
        switch (disaster?.severity) {
          case "critical":
            return 0.85; // severe slowdown
          case "high":
            return 0.95;
          case "moderate":
            return 0.98;
          default:
            return 1;
        }
      })();

      const enriched = mapped.map((m) => {
        let distance_km: number | null = null;
        let eta_minutes: number | null = null;
        if (typeof m.lat === "number" && typeof m.lon === "number" && typeof disaster?.lat === "number" && typeof disaster?.lon === "number") {
          try {
            distance_km = Number(haversineKm(disaster.lat, disaster.lon, m.lat, m.lon).toFixed(3));
            // simple demand heuristic
            const demandOverlap = (m.items || []).some((it) => (disaster.resourcesNeeded || []).some((r) => String(it).toLowerCase().includes(String(r).toLowerCase())));
            const demandMultiplier = demandOverlap ? 1.25 : 1.0;
            const priorityMultiplier = m.priority === "high" ? 0.85 : m.priority === "low" ? 1.15 : 1.0;
            const deployOverheadMinutes = 20; // staging / prep time

            const travelHours = distance_km / (baseSpeedKmh * roadFactor);
            eta_minutes = Math.max(5, Math.round((travelHours * 60 + deployOverheadMinutes) * demandMultiplier * priorityMultiplier));
          } catch (e) {
            distance_km = null;
            eta_minutes = null;
          }
        }

        // urgency score: combine ETA (lower better) and priority
        const priorityScore = m.priority === "high" ? 0 : m.priority === "medium" ? 50 : 100;
        const etaScore = eta_minutes != null ? eta_minutes : 9999;
        const urgency = priorityScore + etaScore;

        return {
          ...m,
          distance_km,
          eta_minutes,
          eta: eta_minutes != null ? `${Math.floor(eta_minutes / 60)}h ${eta_minutes % 60}m` : m.eta ?? undefined,
          urgency,
        } as Need;
      });

      setNeeds(enriched);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchNeeds();
    // optionally poll every minute when in an active incident
    const id = setInterval(fetchNeeds, 60_000);
    return () => clearInterval(id);
  }, []);

  const sortedFiltered = useMemo(() => {
    let arr = [...needs];
    // apply radius filter
    const rkm = typeof radiusKm === "number" ? radiusKm : null;
    if (rkm != null && !Number.isNaN(rkm) && rkm > 0) {
      arr = arr.filter((n) => typeof n.distance_km === "number" && n.distance_km <= rkm);
    }

    // sorting
    arr.sort((a, b) => {
      if (sortBy === "eta") {
        const aa = a.eta_minutes != null ? a.eta_minutes : Number.POSITIVE_INFINITY;
        const bb = b.eta_minutes != null ? b.eta_minutes : Number.POSITIVE_INFINITY;
        return aa - bb;
      }
      if (sortBy === "distance") {
        const aa = a.distance_km != null ? a.distance_km : Number.POSITIVE_INFINITY;
        const bb = b.distance_km != null ? b.distance_km : Number.POSITIVE_INFINITY;
        return aa - bb;
      }
      // default: urgency (lower first)
      const ua = a.urgency ?? Number.POSITIVE_INFINITY;
      const ub = b.urgency ?? Number.POSITIVE_INFINITY;
      return ua - ub;
    });

    return arr;
  }, [needs, sortBy, radiusKm]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-foreground">Available Shelter Resources</h2>
          <p className="text-xs text-muted-foreground">Shelters with supplies ready for deployment</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => fetchNeeds()}>
          View All Shelters
        </Button>
      </div>



      {loading && <p className="text-sm text-muted-foreground">Loading shelters…</p>}
      {error && <p className="text-sm text-destructive">Error: {error}</p>}

      {needs.length === 0 && !loading && !error && (
        <Card className="p-4 bg-card border-border">
          <p className="text-sm text-muted-foreground">No shelters with available resources found.</p>
        </Card>
      )}

      {sortedFiltered.map((need, index) => (
        <Card key={index} className="p-4 bg-card border-border">
          <div className="space-y-3">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-semibold text-foreground flex items-center gap-2">
                  {need.shelter}
                  <Badge
                    variant={need.priority === "high" ? "default" : "secondary"}
                    className="text-xs"
                  >
                    {need.priority === "high" ? "HIGH CAPACITY" : need.priority.toUpperCase()}
                  </Badge>
                </h3>
                <p className="text-sm text-muted-foreground flex items-center gap-1 mt-1">
                  <MapPin className="w-3 h-3" />
                  {need.location}
                </p>
                {typeof need.distance_km === "number" && (
                  <p className="text-xs text-muted-foreground mt-1">Distance: {need.distance_km} km</p>
                )}
                {need.capacity && need.capacity > 0 && (
                  <p className="text-xs text-muted-foreground mt-1">
                    Total Capacity: {need.capacity} people | Status: {need.status}
                  </p>
                )}
              </div>
              <div className="text-right">
                <p className="text-xs text-muted-foreground flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  ETA: {need.eta ?? "—"}
                </p>
              </div>
            </div>

            <div className="space-y-1">
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                <Package className="w-3 h-3" />
                Resources Available:
              </p>
              <div className="flex flex-wrap gap-2">
                {need.items.map((item, i) => (
                  <Badge key={i} variant="outline" className="text-xs">
                    {item}
                  </Badge>
                ))}
              </div>
            </div>

            <div className="flex gap-2">
              <Button size="sm" className="flex-1">
                Deploy to Area
              </Button>
              <Button size="sm" variant="outline">
                Check Inventory
              </Button>
            </div>
          </div>
        </Card>
      ))}

      <Card className="p-4 bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-green-600 dark:text-green-400 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-foreground">💡 Resource Optimization Tip</p>
            <p className="text-xs text-muted-foreground mt-1">
              Riverside shelter approaching capacity (95%). Consider: <br/>
              • Open backup facility in Alexandria within 2 hours<br/>
              • Redistribute 30% of supplies to reduce congestion<br/>
              • Coordinate with volunteer teams for faster deployment
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default ResourcePanel;
