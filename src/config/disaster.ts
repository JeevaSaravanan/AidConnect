// Central disaster configuration used throughout the dashboard.
// Export typed shapes and a single DEFAULT_DISASTER object.

export type Area = {
  id: string;
  name: string;
  city: string;
  lat: number;
  lon: number;
  peopleAffected: number;
  resourcesNeeded: string[];
  notes?: string;
  severity?: "low" | "moderate" | "high" | "critical";
};

export type DisasterLocation = {
  id: string;
  name: string;
  description?: string;
  timestamp: string; // ISO string
  lat: number;
  lon: number;
  city: string;
  totalPeopleAffected: number;
  areasAffected: Area[];
  resourcesNeeded: string[]; // aggregated/priority resources
  severity: "low" | "moderate" | "high" | "critical";
  source?: string;
};

// Example: a simulated hurricane event centered on New Orleans with two areas.
export const DEFAULT_DISASTER: DisasterLocation = {
  id: "disaster-georgetown-va-1",
  name: "Severe Flooding — Georgetown, VA (simulated)",
  description:
    "Widespread riverine and flash flooding following heavy rainfall; road closures and localized infrastructure damage reported.",
  // Coordinates are approximate for Georgetown, VA — update to precise location if needed.
  timestamp: new Date().toISOString(),
  lat : 38.90155, 
  lon: -77.06059,
  city: "Georgetown, VA",
  totalPeopleAffected: 4200,
  areasAffected: [
    {
      id: "area-1",
      name: "Georgetown Central",
      city: "Georgetown, VA",
      lat: 38.302,
      lon: -77.298,
      peopleAffected: 2400,
      resourcesNeeded: ["shelter", "medical", "food", "water"],
      severity: "high",
      notes: "Residential flooding; primary bridge closed and power outages in several blocks.",
    },
    {
      id: "area-2",
      name: "Riverbend / Lowlands",
      city: "Georgetown, VA",
      lat: 38.295,
      lon: -77.310,
      peopleAffected: 1800,
      resourcesNeeded: ["evacuation-transport", "shelter", "generators", "water"],
      severity: "critical",
      notes: "Low-lying neighborhoods submerged; immediate evacuations recommended for vulnerable residents.",
    },
  ],
  resourcesNeeded: [
    "shelter",
    "evacuation-transport",
    "medical",
    "food",
    "water",
    "generators",
  ],
  severity: "high",
  source: "simulated/config",
};

export default DEFAULT_DISASTER;
