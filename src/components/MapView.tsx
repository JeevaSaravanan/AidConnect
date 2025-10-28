import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MapPin, Home, AlertTriangle } from "lucide-react";

const MapView = () => {
  return (
    <Card className="p-4 bg-card border-border">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-foreground">Situation Map</h3>
        <div className="flex gap-2">
          <Badge variant="destructive" className="text-xs flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" />3 High-Risk Zones
          </Badge>
          <Badge variant="outline" className="text-xs flex items-center gap-1">
            <Home className="w-3 h-3" />
            12 Active Shelters
          </Badge>
        </div>
      </div>
      
      <div className="aspect-video bg-secondary rounded-lg flex items-center justify-center relative overflow-hidden">
        {/* Placeholder map with styled elements */}
        <div className="absolute inset-0 opacity-10">
          <div className="w-full h-full" style={{
            backgroundImage: `repeating-linear-gradient(0deg, hsl(var(--border)) 0px, transparent 1px, transparent 20px), 
                            repeating-linear-gradient(90deg, hsl(var(--border)) 0px, transparent 1px, transparent 20px)`
          }} />
        </div>
        
        <div className="relative z-10 text-center space-y-2">
          <MapPin className="w-12 h-12 text-primary mx-auto" />
          <p className="text-sm text-muted-foreground">Interactive map with real-time overlay</p>
          <p className="text-xs text-muted-foreground">Weather data • Traffic routes • Affected areas</p>
        </div>

        {/* Example markers */}
        <div className="absolute top-1/4 left-1/3 w-3 h-3 bg-destructive rounded-full animate-pulse" />
        <div className="absolute top-1/2 right-1/3 w-3 h-3 bg-warning rounded-full animate-pulse" />
        <div className="absolute bottom-1/3 left-1/2 w-3 h-3 bg-success rounded-full animate-pulse" />
      </div>
    </Card>
  );
};

export default MapView;
