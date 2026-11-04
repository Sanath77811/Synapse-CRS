import { createContext, useContext, type ReactNode } from "react";
import { usePlatform, type PlatformContextValue } from "../hooks/usePlatform";

const PlatformContext = createContext<PlatformContextValue | null>(null);

export function PlatformProvider({ children }: { children: ReactNode }) {
  const value = usePlatform();
  return <PlatformContext.Provider value={value}>{children}</PlatformContext.Provider>;
}

export function usePlatformContext(): PlatformContextValue {
  const value = useContext(PlatformContext);
  if (!value) {
    throw new Error("PlatformProvider is required");
  }
  return value;
}
