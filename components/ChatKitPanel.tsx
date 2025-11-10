"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChatKit, useChatKit } from "@openai/chatkit-react";
import {
  STARTER_PROMPTS,
  PLACEHOLDER_INPUT,
  GREETING,
  CREATE_SESSION_ENDPOINT,
  WORKFLOW_ID,
  getThemeConfig,
} from "@/lib/config";
import type { ColorScheme } from "@/hooks/useColorScheme";
import ExportPdfButton from "@/components/ExportPdfButton";

export type FactAction = {
  type: "save";
  factId: string;
  factText: string;
};

type ChatKitPanelProps = {
  theme: ColorScheme;
  onWidgetAction: (action: FactAction) => Promise<void>;
  onResponseEnd: () => void;
  onThemeRequest: (scheme: ColorScheme) => void;
};

type ErrorState = {
  script: string | null;
  session: string | null;
  integration: string | null;
  retryable: boolean;
};

const isBrowser = typeof window !== "undefined";
const isDev = process.env.NODE_ENV !== "production";

const createInitialErrors = (): ErrorState => ({
  script: null,
  session: null,
  integration: null,
  retryable: false,
});

// Local helper types (no `any`)
type UnknownParams = Record<string, unknown>;
type ClientInvocation = { name: string; params?: UnknownParams };
type ClientResult = { success?: boolean } | Record<string, unknown> | void;

export function ChatKitPanel({
  theme,
  onWidgetAction,
  onResponseEnd,
  onThemeRequest,
}: ChatKitPanelProps) {
  const processedFacts = useRef(new Set<string>());
  const clientSecretRef = useRef<string | null>(null);

  const [errors, setErrors] = useState<ErrorState>(() => createInitialErrors());
  const [isInitializingSession, setIsInitializingSession] = useState(true);
  const isMountedRef = useRef(true);
  const [scriptStatus, setScriptStatus] = useState<"pending" | "ready" | "error">(
    () => (isBrowser && window.customElements?.get("openai-chatkit") ? "ready" : "pending")
  );
  const [widgetInstanceKey] = useState(0);

  const setErrorState = useCallback((updates: Partial<ErrorState>) => {
    setErrors((current) => ({ ...current, ...updates }));
  }, []);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  // chatkit.js presence
  useEffect(() => {
    if (!isBrowser) return;

    let timeoutId: number | undefined;

    const handleLoaded = () => {
      if (!isMountedRef.current) return;
      setScriptStatus("ready");
      setErrorState({ script: null });
    };

    const handleError = (event: Event) => {
      console.error("Failed to load chatkit.js for some reason", event);
      if (!isMountedRef.current) return;
      setScriptStatus("error");
      const detail = (event as CustomEvent<unknown>)?.detail ?? "unknown error";
      setErrorState({ script: `Error: ${detail}`, retryable: false });
      setIsInitializingSession(false);
    };

    window.addEventListener("chatkit-script-loaded", handleLoaded);
    window.addEventListener("chatkit-script-error", handleError as EventListener);

    if (window.customElements?.get("openai-chatkit")) {
      handleLoaded();
    } else if (scriptStatus === "pending") {
      timeoutId = window.setTimeout(() => {
        if (!window.customElements?.get("openai-chatkit")) {
          handleError(
            new CustomEvent("chatkit-script-error", {
              detail:
                "ChatKit web component is unavailable. Verify that the script URL is reachable.",
            })
          );
        }
      }, 5000);
    }

    return () => {
      window.removeEventListener("chatkit-script-loaded", handleLoaded);
      window.removeEventListener("chatkit-script-error", handleError as EventListener);
      if (timeoutId) window.clearTimeout(timeoutId);
    };
  }, [scriptStatus, setErrorState]);

  // Health-check once
  useEffect(() => {
    (async () => {
      if (!isMountedRef.current) return;
      try {
        const r = await fetch("/api/health", { cache: "no-store" });
        const j = await r.json();
        if (j.status !== "ok") {
          setErrorState({
            session:
              "Workflow not configured. Set CHATKIT_WORKFLOW_ID on the server (or NEXT_PUBLIC_CHATKIT_WORKFLOW_ID if you intentionally expose it).",
            retryable: false,
          });
          setIsInitializingSession(false);
          return;
        }
        setErrorState({ session: null, retryable: false });
        setIsInitializingSession(false);
      } catch {
        setErrorState({
          session:
            "Could not verify workflow configuration. Ensure CHATKIT_WORKFLOW_ID is set on the server.",
          retryable: false,
        });
        setIsInitializingSession(false);
      }
    })();
  }, [setErrorState]);

  // Create/reuse client secret (cached)
  const getClientSecret = useCallback(
    async (currentSecret: string | null) => {
      if (process.env.NODE_ENV !== "production") {
        console.count("[ChatKitPanel] getClientSecret");
        console.log(
          "[ChatKitPanel] currentSecret:",
          !!currentSecret,
          "cached:",
          !!clientSecretRef.current
        );
      }

      // Reuse if already provided by ChatKit
      if (currentSecret) {
        if (isDev) console.info("[ChatKitPanel] reusing current clientSecret");
        return currentSecret;
      }
      // Or reuse cached one
      if (clientSecretRef.current) {
        if (isDev) console.info("[ChatKitPanel] reusing cached clientSecret");
        return clientSecretRef.current;
      }

      if (isDev) {
        console.info("[ChatKitPanel] getClientSecret invoked", {
          currentSecretPresent: Boolean(currentSecret),
          workflowId: WORKFLOW_ID,
          endpoint: CREATE_SESSION_ENDPOINT,
        });
      }

      const healthy = await fetch("/api/health", { cache: "no-store" })
        .then((r) => r.json())
        .catch(() => ({ status: "error" }));

      if (healthy.status !== "ok") {
        const detail =
          "Workflow not configured. Set CHATKIT_WORKFLOW_ID on the server (or NEXT_PUBLIC_CHATKIT_WORKFLOW_ID if needed on the client).";
        if (isMountedRef.current) {
          setErrorState({ session: detail, retryable: false });
          setIsInitializingSession(false);
        }
        throw new Error(detail);
      }

      if (isMountedRef.current) {
        setErrorState({ session: null, integration: null, retryable: false });
      }

      try {
        const response = await fetch(CREATE_SESSION_ENDPOINT, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            // Server injects the workflow id; do not send it from the client
            chatkit_configuration: { file_upload: { enabled: true } },
          }),
        });

        const raw = await response.text();

        if (isDev) {
          console.info("[ChatKitPanel] createSession response", {
            status: response.status,
            ok: response.ok,
            bodyPreview: raw.slice(0, 1600),
          });
        }

        let data: Record<string, unknown> = {};
        if (raw) {
          try {
            data = JSON.parse(raw) as Record<string, unknown>;
          } catch (parseError) {
            console.error("Failed to parse create-session response", parseError);
          }
        }

        if (!response.ok) {
          const detail = extractErrorDetail(data, response.statusText);
          console.error("Create session request failed", {
            status: response.status,
            body: data,
          });
          throw new Error(detail);
        }

        const clientSecret = data?.client_secret as string | undefined;
        if (!clientSecret) throw new Error("Missing client secret in response");

        // Cache for future calls
        clientSecretRef.current = clientSecret;

        if (isMountedRef.current) {
          setErrorState({ session: null, integration: null });
        }

        return clientSecret;
      } catch (error) {
        console.error("Failed to create ChatKit session", error);
        const detail =
          error instanceof Error ? error.message : "Unable to start ChatKit session.";
        if (isMountedRef.current) {
          setErrorState({ session: detail, retryable: false });
        }
        throw error instanceof Error ? error : new Error(detail);
      } finally {
        if (isMountedRef.current) {
          setIsInitializingSession(false);
        }
      }
    },
    [setErrorState, setIsInitializingSession]
  );

  // Stable callbacks
  const onRespEndCb = useCallback(() => {
    onResponseEnd();
  }, [onResponseEnd]);

  const onRespStartCb = useCallback(() => {
    setErrorState({ integration: null, retryable: false });
  }, [setErrorState]);

  const onThreadChangeCb = useCallback(() => {
    processedFacts.current.clear();
  }, []);

  const onErrCb = useCallback(({ error }: { error: unknown }) => {
    console.error("ChatKit error", error);
  }, []);

  // Minimal client-tool handler: handle ours; ACK everything else.
  // NOTE: return type is always a Record<string, unknown>.
  const onClientToolCb = useCallback(
    async (
      invocation: { name: string; params: Record<string, unknown> }
    ): Promise<Record<string, unknown>> => {
      const params = invocation.params ?? {};

      if (invocation.name === "switch_theme") {
        const raw = params["theme"];
        const requested = typeof raw === "string" ? raw : undefined;
        if (requested === "light" || requested === "dark") {
          if (process.env.NODE_ENV !== "production") {
            console.debug("[ChatKitPanel] switch_theme", requested);
          }
          onThemeRequest(requested);
          return { success: true };
        }
        // Known tool but unsupported value – still return a record
        return { success: false };
      }

      if (invocation.name === "record_fact") {
        const idRaw = params["fact_id"];
        const textRaw = params["fact_text"];
        const id = typeof idRaw === "string" ? idRaw : String(idRaw ?? "");
        const text = typeof textRaw === "string" ? textRaw : String(textRaw ?? "");
        if (!id || processedFacts.current.has(id)) {
          return { success: true };
        }
        processedFacts.current.add(id);
        void onWidgetAction({
          type: "save",
          factId: id,
          factText: text.replace(/\s+/g, " ").trim(),
        });
        return { success: true };
      }

      // 🔑 Fallback for built-ins like user_approval:
      // Acknowledge with an empty object so ChatKit doesn't retry.
      if (process.env.NODE_ENV !== "production") {
        console.debug("[ChatKitPanel] ack unknown client tool", invocation.name, params);
      }
      return {}; // <- MUST be a record, not void
    },
    [onThemeRequest, onWidgetAction]
  );

  // Memoized theme + full options (prevents re-inits)
  const themeCfg = useMemo(() => getThemeConfig(theme), [theme]);

  const chatkitOptions = useMemo(
    () => ({
      api: { getClientSecret },
      theme: { colorScheme: theme, ...themeCfg },
      startScreen: { greeting: GREETING, prompts: STARTER_PROMPTS },
      composer: { placeholder: PLACEHOLDER_INPUT, attachments: { enabled: true } },
      threadItemActions: { feedback: false },
      onClientTool: onClientToolCb, // explicit ACK fallback
      onResponseEnd: onRespEndCb,
      onResponseStart: onRespStartCb,
      onThreadChange: onThreadChangeCb,
      onError: onErrCb,
    }),
    [
      getClientSecret,
      theme,
      themeCfg,
      onClientToolCb,
      onRespEndCb,
      onRespStartCb,
      onThreadChangeCb,
      onErrCb,
    ]
  );

  const chatkit = useChatKit(chatkitOptions);

  const blockingError = scriptStatus === "error";

  // Observe ChatKit iframe messages (no `any`)
  useEffect(() => {
    function onMessage(ev: MessageEvent) {
      const origin = String(ev.origin || "");
      if (!origin.includes("openai.com")) return;
      const data = ev.data;
      if (typeof data !== "object" || data === null) return;

      const hasType = (d: unknown): d is { type: unknown } =>
        typeof d === "object" && d !== null && "type" in (d as Record<string, unknown>);
      const hasEvent = (d: unknown): d is { event: unknown } =>
        typeof d === "object" && d !== null && "event" in (d as Record<string, unknown>);
      const hasAction = (d: unknown): d is { action: unknown } =>
        typeof d === "object" && d !== null && "action" in (d as Record<string, unknown>);

      let kind = "message";
      if (hasType(data) && typeof (data as { type: unknown }).type === "string") {
        kind = (data as { type: string }).type;
      } else if (hasEvent(data) && typeof (data as { event: unknown }).event === "string") {
        kind = (data as { event: string }).event;
      } else if (
        hasAction(data) &&
        typeof (data as { action: unknown }).action === "string"
      ) {
        kind = (data as { action: string }).action;
      }

      const summary = JSON.stringify(data).slice(0, 300);
      console.log("[ChatKit iframe]", origin, kind, summary);
    }

    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  if (isDev) {
    console.debug("[ChatKitPanel] render state", {
      isInitializingSession,
      hasControl: Boolean(chatkit.control),
      scriptStatus,
      hasError: Boolean(blockingError || errors.session || errors.integration),
      workflowId: WORKFLOW_ID,
    });
  }

  return (
    <>
      {/* Fixed header */}
      <div
        className="fixed inset-x-0 top-0 z-50 flex justify-end gap-3
                    border-b border-slate-200/60 dark:border-slate-800/60
                    bg-white/80 dark:bg-slate-900/80 backdrop-blur px-4 py-3"
      >
        <ExportPdfButton filename="CR2A" />
      </div>

      {/* Panel */}
      <div
        className="relative pt-14 flex h-[90vh] w-full rounded-2xl flex-col
                    bg-white shadow-sm transition-colors dark:bg-slate-900"
      >
        <div id="cr2a-answer" className="flex-1 min-h-0">
          <ChatKit
            key={widgetInstanceKey}
            control={chatkit.control}
            className={
              blockingError || isInitializingSession
                ? "pointer-events-none opacity-0"
                : "block h-full w-full"
            }
          />
        </div>
      </div>
    </>
  );
}

function extractErrorDetail(
  payload: Record<string, unknown> | undefined,
  fallback: string
): string {
  if (!payload) return fallback;

  const error = payload.error;
  if (typeof error === "string") return error;

  if (
    error &&
    typeof error === "object" &&
    "message" in error &&
    typeof (error as { message?: unknown }).message === "string"
  ) {
    return (error as { message: string }).message;
  }

  const details = payload.details;
  if (typeof details === "string") return details;

  if (details && typeof details === "object" && "error" in details) {
    const nestedError = (details as { error?: unknown }).error;
    if (typeof nestedError === "string") return nestedError;
    if (
      nestedError &&
      typeof nestedError === "object" &&
      "message" in nestedError &&
      typeof (nestedError as { message?: unknown }).message === "string"
    ) {
      return (nestedError as { message: string }).message;
    }
  }

  if (typeof payload.message === "string") return payload.message;

  return fallback;
}