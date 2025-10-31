import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MapPin, Home, AlertTriangle } from "lucide-react";
import "leaflet/dist/leaflet.css";
import { MapContainer, TileLayer, CircleMarker, Popup, LayersControl } from "react-leaflet";
import DEFAULT_DISASTER from "@/config/disaster";
import { useEffect, useState } from "react";

const DEFAULT_API = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

const severityColor = (s?: string) => {
  switch (s) {
    case "critical":
      return "#b91c1c"; // red-700
    case "high":
      return "#f97316"; // orange-500
    case "moderate":
      return "#f59e0b"; // amber-500
    default:
      return "#10b981"; // green-500
  }
};

const MapView = () => {
  const disaster = DEFAULT_DISASTER;

  // compute bounds or center
  const center: [number, number] = [disaster.lat, disaster.lon];
  const [shelters, setShelters] = useState<any[]>([]);
  const [loadingShelters, setLoadingShelters] = useState(false);
  const [shelterError, setShelterError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    async function fetchShelters() {
      setLoadingShelters(true);
      setShelterError(null);
      try {
        const res = await fetch(`${DEFAULT_API}/shelters?limit=5`);
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        const body = await res.json();
        const data = body?.data || body || [];

        const mapped = data.map((s: any) => {
          const lat = s.latitude ?? s.lat ?? (s._geo && s._geo.lat) ?? null;
          const lon = s.longitude ?? s.lon ?? s.lng ?? (s._geo && s._geo.lon) ?? null;
          return {
            id: s.id || s._id || s.name || Math.random().toString(36).slice(2, 9),
            name: s.shelter_name || s.name || s.title || "Unknown shelter",
            address: s.location || s.address || s.city || "",
            phone: s.phone || s.contact_phone || s.contact || undefined,
            capacity: s.post_cap ?? s.evac_cap ?? s.capacity ?? undefined,
            lat: lat !== undefined && lat !== null ? Number(lat) : null,
            lon: lon !== undefined && lon !== null ? Number(lon) : null,
            details: s.details || s.requested_items || undefined,
          };
        });

        if (mounted) setShelters(mapped);
      } catch (e: any) {
        if (mounted) setShelterError(String(e?.message || e));
      } finally {
        if (mounted) setLoadingShelters(false);
      }
    }

    fetchShelters();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <Card className="p-4 bg-card border-border">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-foreground">Situation Map</h3>
        <div className="flex gap-2">
          <Badge variant="destructive" className="text-xs flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" />{disaster.areasAffected.filter(a => a.severity === 'high' || a.severity === 'critical').length} High-Risk Zones
          </Badge>
          <Badge variant="outline" className="text-xs flex items-center gap-1">
            <Home className="w-3 h-3" />
            {disaster.areasAffected.length} Affected Areas
          </Badge>
        </div>
      </div>

      <div className="aspect-video bg-secondary rounded-lg overflow-hidden">
        <MapContainer center={center} zoom={12} className="w-full h-full">
          <LayersControl position="topright">
            <LayersControl.BaseLayer checked name="OpenStreetMap">
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
            </LayersControl.BaseLayer>
          </LayersControl>

          {/* Disaster center */}
          <CircleMarker
            center={center}
            radius={12}
            pathOptions={{ color: severityColor(disaster.severity), fillOpacity: 0.6 }}
          >
            <Popup>
              <div className="text-sm">
                <strong>{disaster.name}</strong>
                <div>{disaster.city}</div>
                <div className="text-xs text-muted-foreground">Updated: {new Date(disaster.timestamp).toLocaleString()}</div>
                <div className="mt-1">Total people affected: {disaster.totalPeopleAffected}</div>
              </div>
            </Popup>
          </CircleMarker>

          {/* Areas affected as circle markers */}
          {disaster.areasAffected.map((area) => {
            const radius = Math.min(40, Math.max(6, Math.sqrt(area.peopleAffected) * 0.8));
            return (
              <CircleMarker
                key={area.id}
                center={[area.lat, area.lon]}
                radius={radius}
                pathOptions={{ color: severityColor(area.severity), fillOpacity: 0.45 }}
              >
                <Popup>
                  <div className="text-sm">
                    <strong>{area.name}</strong>
                    <div className="text-xs text-muted-foreground">People affected: {area.peopleAffected}</div>
                    <div className="text-xs">Severity: {area.severity}</div>
                    {area.notes && <div className="mt-1 text-xs">{area.notes}</div>}
                    {area.resourcesNeeded?.length > 0 && (
                      <div className="mt-1 text-xs">Needs: {area.resourcesNeeded.join(", ")}</div>
                    )}
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}

          {/* Shelters fetched from API (limit=5) */}
          {shelters.map((s) =>
            typeof s.lat === "number" && typeof s.lon === "number" ? (
              <CircleMarker
                key={s.id}
                center={[s.lat, s.lon]}
                radius={8}
                pathOptions={{ color: "#2563eb", fillOpacity: 0.8 }}
              >
                <Popup>
                  <div className="text-sm">
                    <strong>{s.name}</strong>
                    {s.address && <div className="text-xs text-muted-foreground">{s.address}</div>}
                    {s.capacity != null && <div className="text-xs">Capacity: {s.capacity}</div>}
                    {s.phone && <div className="text-xs">Phone: {s.phone}</div>}
                    {s.details && <div className="mt-1 text-xs">{String(s.details).slice(0, 140)}</div>}
                    <div className="mt-1 text-xs text-muted-foreground">(Source: API)</div>
                  </div>
                </Popup>
              </CircleMarker>
            ) : null
          )}
        </MapContainer>
      </div>
    </Card>
  );
};

export default MapView;
