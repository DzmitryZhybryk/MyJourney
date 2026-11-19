const STORAGE_KEY = "access_token";

type Listener = (token: string | null) => void;

const listeners = new Set<Listener>();
let memoryToken: string | null = readFromSession();

function readFromSession(): string | null {
  try {
    return sessionStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function writeToSession(token: string | null): void {
  try {
    if (token === null) {
      sessionStorage.removeItem(STORAGE_KEY);
    } else {
      sessionStorage.setItem(STORAGE_KEY, token);
    }
  } catch {
    // sessionStorage unavailable (private mode / disabled): keep the token in memory only.
  }
}

export function getAccessToken(): string | null {
  return memoryToken;
}

export function setAccessToken(token: string): void {
  memoryToken = token;
  writeToSession(token);
  listeners.forEach((listener) => listener(token));
}

export function clearAccessToken(): void {
  memoryToken = null;
  writeToSession(null);
  listeners.forEach((listener) => listener(null));
}

export function subscribeAccessToken(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
