import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ChevronDown, X } from "lucide-react";

const WeatherSimulation = () => {
  const [selectedEvent, setSelectedEvent] = useState("hurricane-harvey");
  const [selectedVariables, setSelectedVariables] = useState<string[]>(["wind-speed", "surface-temp", "water-vapor"]);
  const [weatherVariable, setWeatherVariable] = useState("surface-temp");
  const [ensembleMember, setEnsembleMember] = useState("member-1");

  const removeVariable = (variable: string) => {
    setSelectedVariables(selectedVariables.filter(v => v !== variable));
  };

  const addVariable = (variable: string) => {
    if (!selectedVariables.includes(variable)) {
      setSelectedVariables([...selectedVariables, variable]);
    }
  };

  const variableLabels: Record<string, string> = {
    "wind-speed": "Wind Speed",
    "surface-temp": "Surface Temperature",
    "water-vapor": "Total Column Water Vapor"
  };

  const availableVariables = Object.keys(variableLabels).filter(
    v => !selectedVariables.includes(v)
  );

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Input Panel */}
      <Card className="p-6 bg-card border-border">
        <div className="space-y-6">
          <div>
            <h2 className="text-2xl font-bold text-foreground mb-2">Input</h2>
          </div>

          {/* Sample Weather Event */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground">Sample Weather Event</label>
            <Select value={selectedEvent} onValueChange={setSelectedEvent}>
              <SelectTrigger className="w-full bg-secondary border-border">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="amphan">Super Cyclonic Storm Amphan</SelectItem>
                <SelectItem value="hagibis">Typhoon Hagibis</SelectItem>
                <SelectItem value="atmospheric-river">Atmospheric River over California</SelectItem>
                <SelectItem value="hurricane-harvey">Category 4 Hurricane Harvey</SelectItem>
                <SelectItem value="kyrill">Cyclone Kyrill</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Weather Variable */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground">Weather Variable</label>
            <div className="space-y-2">
              <div className="flex flex-wrap gap-2 p-3 bg-secondary rounded-lg border border-border min-h-[60px]">
                {selectedVariables.map((variable) => (
                  <Badge key={variable} variant="secondary" className="pl-3 pr-1 py-1 flex items-center gap-1">
                    {variableLabels[variable]}
                    <button
                      onClick={() => removeVariable(variable)}
                      className="ml-1 hover:bg-background/50 rounded-full p-0.5"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </Badge>
                ))}
              </div>
              {availableVariables.length > 0 && (
                <Select value="" onValueChange={addVariable}>
                  <SelectTrigger className="w-full bg-secondary border-border">
                    <SelectValue placeholder="Add weather variable..." />
                  </SelectTrigger>
                  <SelectContent>
                    {availableVariables.map((variable) => (
                      <SelectItem key={variable} value={variable}>
                        {variableLabels[variable]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>
          </div>

          {/* Collapsible Sections */}
          <Collapsible defaultOpen className="border-t border-border pt-4">
            <CollapsibleTrigger className="flex items-center justify-between w-full text-left">
              <span className="font-medium text-foreground">About Sample Weather Events</span>
              <ChevronDown className="w-4 h-4 text-muted-foreground" />
            </CollapsibleTrigger>
            <CollapsibleContent className="pt-3">
              <div className="text-sm text-muted-foreground space-y-4">
                <p>Select from historical weather events to simulate various disaster scenarios and analyze their impact patterns.</p>

                <div className="space-y-6 pt-2">
                  <h3 className="font-semibold text-foreground text-base">Weather Events</h3>

                  <div className="space-y-3">
                    <h4 className="font-medium text-foreground">Super Cyclonic Storm Amphan</h4>
                    <div className="space-y-1">
                      <p><span className="font-medium">Forecast Date:</span> 2020/05/16</p>
                      <p><span className="font-medium">Region:</span> Eastern India</p>
                      <p><span className="font-medium">Damage:</span> $13.7 billion USD</p>
                    </div>
                    <p>One of the strongest Bay of Bengal cyclones, Amphan made landfall in May 2020 with winds up to 240 km/h (150 mph). It devastated India and Bangladesh, particularly the Sundarbans region, with heavy rainfall, storm surges, and powerful winds causing massive infrastructure and agricultural damage. Emergency response was complicated by the concurrent COVID-19 pandemic.</p>
                  </div>

                  <div className="space-y-3">
                    <h4 className="font-medium text-foreground">Typhoon Hagibis</h4>
                    <div className="space-y-1">
                      <p><span className="font-medium">Forecast Date:</span> 2019/10/10</p>
                      <p><span className="font-medium">Region:</span> Japan</p>
                      <p><span className="font-medium">Damage:</span> $17.3 billion USD</p>
                    </div>
                    <p>A powerful typhoon that struck Japan in October 2019 with wind speeds up to 195 km/h (121 mph). Heavy rainfall triggered widespread flooding and landslides across multiple regions, particularly affecting the Greater Tokyo Area and surrounding prefectures.</p>
                  </div>

                  <div className="space-y-3">
                    <h4 className="font-medium text-foreground">Atmospheric River over California</h4>
                    <div className="space-y-1">
                      <p><span className="font-medium">Forecast Date:</span> 2018/04/01</p>
                      <p><span className="font-medium">Region:</span> Western United States</p>
                    </div>
                    <p>Narrow corridors of concentrated moisture transporting vast amounts of water vapor across distances. These atmospheric rivers are crucial for California's water supply but pose significant risks of flooding, landslides, and other hazards, especially when interacting with mountain ranges.</p>
                  </div>

                  <div className="space-y-3">
                    <h4 className="font-medium text-foreground">Category 4 Hurricane Harvey</h4>
                    <div className="space-y-1">
                      <p><span className="font-medium">Forecast Date:</span> 2017/08/23</p>
                      <p><span className="font-medium">Region:</span> Southern United States</p>
                      <p><span className="font-medium">Damage:</span> $125 billion USD</p>
                    </div>
                    <p>A catastrophic hurricane that struck Texas and Louisiana in August 2017. While the initial landfall near Rockport brought destructive winds and storm surges, the prolonged record-breaking rainfall in Houston—over 40 inches in some areas—caused the most devastating flooding, inundating homes, businesses, and infrastructure.</p>
                  </div>

                  <div className="space-y-3">
                    <h4 className="font-medium text-foreground">Cyclone Kyrill</h4>
                    <div className="space-y-1">
                      <p><span className="font-medium">Forecast Date:</span> 2007/01/16</p>
                      <p><span className="font-medium">Region:</span> Western Europe</p>
                      <p><span className="font-medium">Damage:</span> $1.1 billion USD</p>
                    </div>
                    <p>An intense European windstorm that struck Western Europe in January 2007. With winds exceeding 225 km/h (140 mph), Kyrill devastated the British Isles, Netherlands, Belgium, and Germany, toppling trees, damaging buildings, causing widespread power outages, and disrupting thousands of flights and train services.</p>
                  </div>

                  <div className="space-y-3 pt-4 border-t border-border">
                    <h3 className="font-semibold text-foreground text-base">Weather Variables</h3>
                    <ul className="space-y-2 list-none">
                      <li><span className="font-medium">Surface Temperature:</span> Air temperature 2m above the ground.</li>
                      <li><span className="font-medium">Surface Wind Speed:</span> Wind speed 10m above the ground.</li>
                      <li><span className="font-medium">Total Column Water Vapor:</span> The integrated water vapour content of the atmosphere.</li>
                    </ul>
                  </div>
                </div>
              </div>
            </CollapsibleContent>
          </Collapsible>

          {/* <Collapsible className="border-t border-border pt-4">
            <CollapsibleTrigger className="flex items-center justify-between w-full text-left">
              <span className="font-medium text-foreground">View Parameters</span>
              <ChevronDown className="w-4 h-4 text-muted-foreground" />
            </CollapsibleTrigger>
            <CollapsibleContent className="pt-3">
              <p className="text-sm text-muted-foreground">
                Adjust simulation parameters including temporal resolution, spatial coverage, and ensemble configurations.
              </p>
            </CollapsibleContent>
          </Collapsible> */}

          {/* Action Buttons */}
          <div className="flex gap-3 pt-4">
            <Button variant="outline" className="flex-1">
              Reset
            </Button>
            <Button className="flex-1 bg-success hover:bg-success/90">
              Forecast
            </Button>
          </div>
        </div>
      </Card>

      {/* Output Panel */}
      <Card className="p-6 bg-card border-border">
        <div className="space-y-6">
          <div>
            <h2 className="text-2xl font-bold text-foreground mb-2">Output</h2>
          </div>

          {/* Weather Variable Output */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground">Weather Variable</label>
            <Select value={weatherVariable} onValueChange={setWeatherVariable}>
              <SelectTrigger className="w-full bg-secondary border-border">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="surface-temp">Surface Temperature</SelectItem>
                <SelectItem value="wind-speed">Wind Speed</SelectItem>
                <SelectItem value="water-vapor">Total Column Water Vapor</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Ensemble Member
          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground">Ensemble Member</label>
            <Select value={ensembleMember} onValueChange={setEnsembleMember}>
              <SelectTrigger className="w-full bg-secondary border-border">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="member-1">Member 1</SelectItem>
                <SelectItem value="member-2">Member 2</SelectItem>
                <SelectItem value="member-3">Member 3</SelectItem>
              </SelectContent>
            </Select>
          </div> */}

          {/* Visualization Area */}
          <div className="aspect-square bg-secondary rounded-lg flex items-center justify-center relative overflow-hidden border border-border">
            {/* Globe Placeholder */}
            <div className="relative w-full h-full flex items-center justify-center">
              <div className="absolute inset-0 opacity-20">
                <div className="w-full h-full" style={{
                  backgroundImage: `repeating-linear-gradient(0deg, hsl(var(--border)) 0px, transparent 1px, transparent 30px), 
                                  repeating-linear-gradient(90deg, hsl(var(--border)) 0px, transparent 1px, transparent 30px)`
                }} />
              </div>
              
              <div className="relative z-10 w-64 h-64 rounded-full border-4 border-primary/30 flex items-center justify-center bg-gradient-to-br from-warning/20 via-destructive/20 to-primary/20">
                <div className="text-center space-y-2">
                  <div className="text-sm font-medium text-muted-foreground">Globe Visualization</div>
                  <div className="text-xs text-muted-foreground">Weather data overlay</div>
                </div>
              </div>

              {/* Legend */}
              <div className="absolute right-4 top-1/2 -translate-y-1/2 space-y-1">
                <div className="text-xs font-medium text-foreground mb-2">°C</div>
                {[40, 30, 20, 10, 0, -10, -20, -30].map((temp) => (
                  <div key={temp} className="flex items-center gap-2">
                    <div className="w-6 h-3 rounded" style={{
                      background: temp > 20 ? 'hsl(var(--destructive))' : 
                                 temp > 0 ? 'hsl(var(--warning))' : 
                                 'hsl(var(--primary))'
                    }} />
                    <span className="text-xs text-muted-foreground">{temp}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default WeatherSimulation;
