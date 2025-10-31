import { useState } from "react";
import Header from "@/components/Header";
import MetricsGrid from "@/components/MetricsGrid";
import ChatInterface from "@/components/ChatInterface";
import ResourcePanel from "@/components/ResourcePanel";
import AffectedAreaPanel from "@/components/AffectedAreaPanel";
import AlertFeed from "@/components/AlertFeed";
import MapView from "@/components/MapView";
import WeatherSimulation from "@/components/WeatherSimulation";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Clock } from "lucide-react";

const Index = () => {
  const [activeTab, setActiveTab] = useState<"overview" | "resources" | "chat" | "weather">("overview");

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Header />
      
      <main className="container mx-auto px-4 py-6 space-y-6">
        {/* Tab Navigation */}
        <div className="flex gap-2 border-b border-border pb-2">
          <button
            onClick={() => setActiveTab("overview")}
            className={`px-4 py-2 font-medium transition-colors ${
              activeTab === "overview"
                ? "text-primary border-b-2 border-primary"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Situation Overview
          </button>
          <button
            onClick={() => setActiveTab("resources")}
            className={`px-4 py-2 font-medium transition-colors ${
              activeTab === "resources"
                ? "text-primary border-b-2 border-primary"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Resource Coordination
          </button>
          <button
            onClick={() => setActiveTab("chat")}
            className={`px-4 py-2 font-medium transition-colors ${
              activeTab === "chat"
                ? "text-primary border-b-2 border-primary"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            AI Assistant
          </button>
          <button
            onClick={() => setActiveTab("weather")}
            className={`px-4 py-2 font-medium transition-colors ${
              activeTab === "weather"
                ? "text-primary border-b-2 border-primary"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Weather Forecast Simulation
          </button>
        </div>

        {/* Overview Tab */}
        {activeTab === "overview" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <MetricsGrid />
              <MapView />
            </div>
            <div>
              <AlertFeed />
            </div>
          </div>
        )}

        {/* Resources Tab */}
        {activeTab === "resources" && (
          <div className="space-y-6">
            {/* Mission Control Header */}
            <Card className="p-6 bg-gradient-to-r from-blue-600 to-blue-800 text-white border-0">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold">Resource Allocation Mission Control</h2>
                  <p className="text-blue-100 mt-1">Match shelter resources with affected area needs</p>
                </div>
                <div className="flex gap-4">
                  <div className="text-center">
                    <div className="text-3xl font-bold">20</div>
                    <div className="text-xs text-blue-200">Affected Areas</div>
                  </div>
                  <div className="text-center">
                    <div className="text-3xl font-bold">10</div>
                    <div className="text-xs text-blue-200">Available Shelters</div>
                  </div>
                  <div className="text-center">
                    <div className="text-3xl font-bold">5</div>
                    <div className="text-xs text-blue-200">Critical Priority</div>
                  </div>
                </div>
              </div>
            </Card>

            {/* Main Allocation Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Left: Affected Areas Needing Resources */}
              <div>
                <AffectedAreaPanel />
              </div>
              
              {/* Right: Available Shelter Resources */}
              <div>
                <ResourcePanel />
              </div>
            </div>

            {/* Active Allocations / In-Transit Resources */}
            <Card className="p-6 bg-card border-border">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Clock className="w-5 h-5 text-blue-500" />
                Active Resource Deployments
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="p-4 bg-secondary border-border">
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant="default" className="text-xs">En Route</Badge>
                    <span className="text-xs text-muted-foreground">ETA: 1h 20m</span>
                  </div>
                  <p className="text-sm font-medium">Georgetown → DC Southeast</p>
                  <p className="text-xs text-muted-foreground mt-1">Water: 500, Food: 400, Blankets: 200</p>
                </Card>
                <Card className="p-4 bg-secondary border-border">
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant="default" className="text-xs">En Route</Badge>
                    <span className="text-xs text-muted-foreground">ETA: 45m</span>
                  </div>
                  <p className="text-sm font-medium">Arlington → Alexandria</p>
                  <p className="text-xs text-muted-foreground mt-1">Medical: 150, Tarps: 200</p>
                </Card>
                <Card className="p-4 bg-secondary border-border">
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant="secondary" className="text-xs">Preparing</Badge>
                    <span className="text-xs text-muted-foreground">Deploy in: 15m</span>
                  </div>
                  <p className="text-sm font-medium">DC Central → Anacostia</p>
                  <p className="text-xs text-muted-foreground mt-1">Water: 800, Food: 600</p>
                </Card>
              </div>
            </Card>
          </div>
        )}

        {/* Chat Tab */}
        {activeTab === "chat" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <ChatInterface />
            </div>
            <div>
              <AlertFeed />
            </div>
          </div>
        )}

        {/* Weather Tab */}
        {activeTab === "weather" && (
          <WeatherSimulation />
        )}
      </main>
    </div>
  );
};

export default Index;
