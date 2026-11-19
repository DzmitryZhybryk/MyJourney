import * as z from "zod/mini";

const accessTokenClaimsSchema = z.object({
  sub: z.string(),
  email_verified: z.boolean(),
  exp: z.number(),
});

export type AccessTokenClaims = z.infer<typeof accessTokenClaimsSchema>;

function base64UrlDecode(segment: string): string {
  const padded = segment.replace(/-/gu, "+").replace(/_/gu, "/");
  const padding = padded.length % 4 === 0 ? "" : "=".repeat(4 - (padded.length % 4));
  return atob(padded + padding);
}

/**
 * Decodes the access token payload WITHOUT verifying the signature.
 *
 * UI logic only (show/hide the unverified-email banner, read `sub`/`exp`). All security
 * decisions stay on the backend.
 */
export function decodeAccessTokenClaims(token: string): AccessTokenClaims | null {
  const parts = token.split(".");
  if (parts.length !== 3) {
    return null;
  }

  try {
    const payloadJson = base64UrlDecode(parts[1]);
    const parsed = JSON.parse(payloadJson) as unknown;
    const result = accessTokenClaimsSchema.safeParse(parsed);
    return result.success ? result.data : null;
  } catch {
    return null;
  }
}
