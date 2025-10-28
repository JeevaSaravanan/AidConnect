import { useState } from "react";
import Header from "@/components/Header";
import MetricsGrid from "@/components/MetricsGrid";
import ChatInterface from "@/components/ChatInterface";
import ResourcePanel from "@/components/ResourcePanel";
import AlertFeed from "@/components/AlertFeed";
import MapView from "@/components/MapView";
import WeatherSimulation from "@/components/WeatherSimulation";

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
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <ResourcePanel />
            </div>
            <div>
              <AlertFeed />
            </div>
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
