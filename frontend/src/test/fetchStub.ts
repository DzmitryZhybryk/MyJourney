/**
 * Shared seam of unit tests that stub `fetch` directly (bypassing MSW, see client.test.ts).
 * The single source of truth for the stub signature and JSON responses.
 */

export type FetchSignature = (input: string | Request, init?: RequestInit) => Promise<Response>;

/** A JSON response with the given status. */
export function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
