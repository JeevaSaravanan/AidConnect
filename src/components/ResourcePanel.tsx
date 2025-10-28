import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Package, MapPin, Clock, AlertCircle } from "lucide-react";

const needs = [
  {
    shelter: "Riverside Community Center",
    location: "Downtown, Zone A",
    items: ["200 blankets", "100 meals", "Medical supplies"],
    priority: "high",
    eta: "25 min",
  },
  {
    shelter: "East Side School",
    location: "East District, Zone C",
    items: ["50 cots", "Water bottles (500)", "First aid kits"],
    priority: "medium",
    eta: "45 min",
  },
  {
    shelter: "Community Sports Complex",
    location: "North Side, Zone B",
    items: ["Generators (2)", "Portable toilets (5)", "Food supplies"],
    priority: "medium",
    eta: "60 min",
  },
];

const ResourcePanel = () => {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-foreground">Resource Allocation Queue</h2>
        <Button variant="outline" size="sm">
          View All Requests
        </Button>
      </div>

      {needs.map((need, index) => (
        <Card key={index} className="p-4 bg-card border-border">
          <div className="space-y-3">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-semibold text-foreground flex items-center gap-2">
                  {need.shelter}
                  <Badge
                    variant={need.priority === "high" ? "destructive" : "secondary"}
                    className="text-xs"
                  >
                    {need.priority === "high" ? "HIGH PRIORITY" : "MEDIUM"}
                  </Badge>
                </h3>
                <p className="text-sm text-muted-foreground flex items-center gap-1 mt-1">
                  <MapPin className="w-3 h-3" />
                  {need.location}
                </p>
              </div>
              <div className="text-right">
                <p className="text-xs text-muted-foreground flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  ETA: {need.eta}
                </p>
              </div>
            </div>

            <div className="space-y-1">
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                <Package className="w-3 h-3" />
                Requested Items:
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
                Allocate Resources
              </Button>
              <Button size="sm" variant="outline">
                View Details
              </Button>
            </div>
          </div>
        </Card>
      ))}

      <Card className="p-4 bg-secondary border-border">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-warning mt-0.5" />
          <div>
            <p className="text-sm font-medium text-foreground">AI Recommendation</p>
            <p className="text-xs text-muted-foreground mt-1">
              Priority alert: Riverside shelter at 95% capacity. Recommend opening backup
              facility within 2 hours and diverting 30% of incoming evacuees.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default ResourcePanel;
