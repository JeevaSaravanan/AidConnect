import { Card } from "@/components/ui/card";
import { Users, Home, Package, TrendingUp } from "lucide-react";

const metrics = [
  {
    label: "People Affected",
    value: "2,847",
    change: "+127 in last hour",
    icon: Users,
    color: "text-destructive",
  },
  {
    label: "Active Shelters",
    value: "12",
    change: "95% capacity",
    icon: Home,
    color: "text-warning",
  },
  {
    label: "Resources Deployed",
    value: "1,234",
    change: "87% of available",
    icon: Package,
    color: "text-primary",
  },
  {
    label: "Response Rate",
    value: "94%",
    change: "+8% from baseline",
    icon: TrendingUp,
    color: "text-success",
  },
];

const MetricsGrid = () => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
      {metrics.map((metric) => {
        const Icon = metric.icon;
        return (
          <Card key={metric.label} className="p-4 bg-card border-border">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-muted-foreground mb-1">{metric.label}</p>
                <p className="text-3xl font-bold text-foreground mb-1">{metric.value}</p>
                <p className="text-xs text-muted-foreground">{metric.change}</p>
              </div>
              <div className={`p-2 bg-secondary rounded ${metric.color}`}>
                <Icon className="w-5 h-5" />
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
};

export default MetricsGrid;
