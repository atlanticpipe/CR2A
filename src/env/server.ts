// src/env/server.ts
function required(key: string): string {
  const v = process.env[key];
  if (!v || v.trim() === "") {
    throw new Error(`Missing required server env var: ${key}`);
  }
  return v.trim();
}

// Guard: make sure nobody exposed the API key as a public var
if (process.env.NEXT_PUBLIC_OPENAI_API_KEY) {
  throw new Error(
    "Security error: NEXT_PUBLIC_OPENAI_API_KEY must not exist. Remove it; secrets cannot be public."
  );
}

export const SERVER_ENV = {
  OPENAI_API_KEY: required("OPENAI_API_KEY"),
} as const;