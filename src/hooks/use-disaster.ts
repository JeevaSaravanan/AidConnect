import DEFAULT_DISASTER, { DisasterLocation } from "../config/disaster";

// Lightweight accessor hook so components can import `useDisaster` and get
// the shared configuration object. This keeps the config easy to mock or
// later wire into context / state if you need runtime updates.
export function useDisaster(): { disaster: DisasterLocation } {
  return { disaster: DEFAULT_DISASTER };
}

export default useDisaster;
