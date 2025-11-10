// next.config.ts
import type { NextConfig } from "next";

/**
 * Build‑time env validation (fail fast).
 * Runs when Next loads the config, before the app starts.
 */
const requiredServer = ["OPENAI_API_KEY"] as const;
const requiredPublic = ["NEXT_PUBLIC_CHATKIT_WORKFLOW_ID"] as const;

for (const key of requiredServer) {
  if (!process.env[key] || process.env[key]!.trim() === "") {
    throw new Error(`[env] Missing required server env var: ${key}`);
  }
}
for (const key of requiredPublic) {
  if (!process.env[key] || process.env[key]!.trim() === "") {
    throw new Error(`[env] Missing required public env var: ${key}`);
  }
}

// Extra guard: secrets must never be public
if (process.env.NEXT_PUBLIC_OPENAI_API_KEY) {
  throw new Error(
    "Security error: NEXT_PUBLIC_OPENAI_API_KEY must not exist. Remove it—secrets cannot be exposed to the browser."
  );
}

const required = ['OPENAI_API_KEY'];

if (!process.env.CI) {
  for (const key of required) {
    if (!process.env[key]) {
      throw new Error(`[env] Missing required server env var: ${key}`);
    }
  }
}

// export the config as usual
const nextConfig = {};
export default nextConfig;