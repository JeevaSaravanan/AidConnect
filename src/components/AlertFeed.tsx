import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, Info, CheckCircle, Clock } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";

const alerts = [
  {
    type: "critical",
    title: "Storm surge peaked",
    message: "6.2ft surge recorded at 3:15 PM. Waters receding.",
    time: "5 min ago",
  },
  {
    type: "warning",
    title: "Shelter capacity warning",
    message: "Riverside Center at 95% capacity. Consider backup activation.",
    time: "12 min ago",
  },
  {
    type: "info",
    title: "Resource delivery complete",
    message: "200 blankets delivered to East Side School.",
    time: "23 min ago",
  },
  {
    type: "success",
    title: "Evacuation route opened",
    message: "Highway 101 South now accessible for emergency vehicles.",
    time: "34 min ago",
  },
  {
    type: "info",
    title: "Weather update",
    message: "Forecast shows improvement by 8 PM tonight.",
    time: "45 min ago",
  },
  {
    type: "warning",
    title: "Medical supplies low",
    message: "3 shelters reporting low medical supply inventory.",
    time: "1 hour ago",
  },
];

const getAlertIcon = (type: string) => {
  switch (type) {
    case "critical":
      return <AlertTriangle className="w-4 h-4 text-destructive" />;
    case "warning":
      return <AlertTriangle className="w-4 h-4 text-warning" />;
    case "success":
      return <CheckCircle className="w-4 h-4 text-success" />;
    default:
      return <Info className="w-4 h-4 text-primary" />;
  }
};

const getAlertBadgeVariant = (type: string) => {
  switch (type) {
    case "critical":
      return "destructive";
    case "warning":
      return "secondary";
    case "success":
      return "default";
    default:
      return "outline";
  }
};

const AlertFeed = () => {
  return (
    <Card className="bg-card border-border">
      <div className="p-4 border-b border-border">
        <h3 className="font-semibold text-foreground">Live Activity Feed</h3>
      </div>
      <ScrollArea className="h-[600px]">
        <div className="p-4 space-y-3">
          {alerts.map((alert, index) => (
            <div
              key={index}
              className="p-3 bg-secondary rounded-lg border border-border space-y-2"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-start gap-2 flex-1">
                  {getAlertIcon(alert.type)}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground">{alert.title}</p>
                    <p className="text-xs text-muted-foreground mt-1">{alert.message}</p>
                  </div>
                </div>
                <Badge variant={getAlertBadgeVariant(alert.type)} className="text-xs shrink-0">
                  {alert.type}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {alert.time}
              </p>
            </div>
          ))}
        </div>
      </ScrollArea>
    </Card>
  );
};

export default AlertFeed;
