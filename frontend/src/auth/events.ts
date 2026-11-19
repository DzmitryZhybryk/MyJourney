type AuthEventMap = {
  "auth-required": void;
};

type Listener<E extends keyof AuthEventMap> = (payload: AuthEventMap[E]) => void;

const listeners: { [E in keyof AuthEventMap]: Set<Listener<E>> } = {
  "auth-required": new Set(),
};

export function on<E extends keyof AuthEventMap>(event: E, listener: Listener<E>): () => void {
  listeners[event].add(listener);
  return () => {
    listeners[event].delete(listener);
  };
}

export function emit<E extends keyof AuthEventMap>(event: E, payload: AuthEventMap[E]): void {
  listeners[event].forEach((listener) => listener(payload));
}
