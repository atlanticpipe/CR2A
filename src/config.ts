import type { StartScreenPrompt } from "@openai/chatkit";

export const STARTER_PROMPTS: StartScreenPrompt[] = [
  { label: "Summarize a PDF", prompt: "Summarize the attached PDF." },
  { label: "Draft an email",  prompt: "Draft a concise reply to this thread." },
];

export const PLACEHOLDER_INPUT = "Type a message…";
export const GREETING = "How can I help today?";

export const CREATE_SESSION_ENDPOINT =
  import.meta.env.VITE_CHATKIT_CREATE_SESSION_ENDPOINT ?? "";

export const WORKFLOW_ID =
  import.meta.env.VITE_CHATKIT_WORKFLOW_ID ?? "wf_replace_me";

export const getThemeConfig = (scheme: "light" | "dark") => ({ colorScheme: scheme });