// src/env/public.ts
const requiredPublic = (key: `NEXT_PUBLIC_${string}`): string => {
  // Next replaces process.env.NEXT_PUBLIC_* at build time
  const v = (process.env as Record<string, string | undefined>)[key];
  if (!v || v.trim() === "") {
    throw new Error(`Missing required public env var: ${key}`);
  }
  return v.trim();
};

export const PUBLIC_ENV = {
  NEXT_PUBLIC_CHATKIT_WORKFLOW_ID: requiredPublic("NEXT_PUBLIC_CHATKIT_WORKFLOW_ID"),
} as const;