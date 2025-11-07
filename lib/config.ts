import { ColorScheme, StartScreenPrompt, ThemeOption } from "@openai/chatkit";

export const IS_SERVER = typeof window === "undefined";

function readEnv(name: string): string | undefined {
  return process.env[name];
}

// Prefer server-only ID; fall back to NEXT_PUBLIC_ only if needed on client.
export const CHATKIT_BASE_URL =
  readEnv("CHATKIT_BASE_URL") ?? "https://api.chatkit.run";

export const WORKFLOW_ID =
  (IS_SERVER ? readEnv("CHATKIT_WORKFLOW_ID") : undefined) ??
  readEnv("NEXT_PUBLIC_CHATKIT_WORKFLOW_ID") ??
  "";

/** Call this wherever you execute the workflow to fail fast if unset. */
export function getWorkflowId(): string {
  const id = WORKFLOW_ID?.trim();
  if (!id) {
    throw new Error(
      "[config] Workflow ID not set. Use CHATKIT_WORKFLOW_ID (server) " +
        "or NEXT_PUBLIC_CHATKIT_WORKFLOW_ID (client)."
    );
  }
  return id;
}

/** Guard against workflow/output drift so bugs are obvious. */
export function assertWorkflowResponseShape(
  x: unknown
): asserts x is { html: string } {
  if (typeof x !== "object" || x === null) {
    throw new Error("[config] Unexpected workflow output (not an object).");
  }
  const obj = x as Record<string, unknown>;
  if (typeof obj.html !== "string") {
    throw new Error(
      "[config] Unexpected workflow output (missing `html`). Check workflow ID or published version."
    );
  }
}

export const CREATE_SESSION_ENDPOINT = "/api/create-session";

export const STARTER_PROMPTS: StartScreenPrompt[] = [
  {
    label: "What can you do?",
    prompt: "What can you do?",
    icon: "circle-question",
  },
];

export const PLACEHOLDER_INPUT = "Ask anything...";

export const GREETING = "How can I help you today?";

export const getThemeConfig = (theme: ColorScheme): ThemeOption => ({
  color: {
    grayscale: {
      hue: 220,
      tint: 6,
      shade: theme === "dark" ? -1 : -4,
    },
    accent: {
      primary: theme === "dark" ? "#f1f5f9" : "#0f172a",
      level: 1,
    },
  },
  radius: "round",
  // Add other theme options here
  // chatkit.studio/playground to explore config options
});
