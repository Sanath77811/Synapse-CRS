const TOKEN_KEY = "synapse.session.token";
const MODE_KEY = "synapse.session.mode";

export type SessionMode = "live" | "demo";

export function readToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function writeToken(token: string | null): void {
  try {
    if (!token) {
      sessionStorage.removeItem(TOKEN_KEY);
      return;
    }
    sessionStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* private browsing */
  }
}

export function readMode(): SessionMode {
  try {
    return sessionStorage.getItem(MODE_KEY) === "live" ? "live" : "demo";
  } catch {
    return "demo";
  }
}

export function writeMode(mode: SessionMode): void {
  try {
    sessionStorage.setItem(MODE_KEY, mode);
  } catch {
    /* ignore */
  }
}

export function maskToken(token: string): string {
  if (token.length <= 8) {
    return "••••";
  }
  return `••••${token.slice(-4)}`;
}
