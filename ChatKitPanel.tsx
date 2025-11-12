"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ChatKit, useChatKit } from "@openai/chatkit-react";
import {
  STARTER_PROMPTS,
  PLACEHOLDER_INPUT,
  GREETING,
  CREATE_SESSION_ENDPOINT,
  WORKFLOW_ID,
  getThemeConfig,
} from "./config";
import { ErrorOverlay } from "./ErrorOverlay";
import type { ColorScheme } from "./useColorScheme";
import ExportPdfButton from "./ExportPdfButton";

export type WidgetAction =
  | { type: "downloadPdf"; data: { html: string } }
  | { type: "savePdf"; data: { html: string } };

export type ChatKitPanelProps = {
  theme: ColorScheme;
  onWidgetAction: (action: WidgetAction) => void;
  onResponseEnd: () => void;
  onThemeRequest: (scheme: ColorScheme) => void;
};

export type ErrorState = {
  script: string | null;
  session: string | null;
  integration: string | null;
  retryable: boolean;
};

const isBrowser = typeof window !== "undefined";
const isDev =
  (typeof import.meta !== "undefined" ? import.meta.env.MODE : "production") !==
  "production";

const createInitialErrors = (): ErrorState => ({
  script: null,
  session: null,
  integration: null,
  retryable: false,
});

export function ChatKitPanel({
  theme,
  onWidgetAction,
  onResponseEnd,
  onThemeRequest,
}: ChatKitPanelProps) {
  const processedFacts = useRef(new Set<string>());
  const [errors, setErrors] = useState<ErrorState>(() => createInitialErrors());
  const [isInitializingSession, setIsInitializingSession] = useState(true);
  const isMountedRef = useRef(true);
  const [scriptStatus, setScriptStatus] = useState<
    "pending" | "ready" | "error"
  >(() => {
    if (!isBrowser) {
      return "error";
    }
    return isBrowser && window.customElements?.get("openai-chatkit")
      ? "ready"
      : "pending";
  });

  const [widgetInstanceKey, setWidgetInstanceKey] = useState(0);

  const setErrorState = useCallback((updates: Partial<ErrorState>) => {
    setErrors((current) => ({ ...current, ...updates }));
  }, []);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    if (!isBrowser) {
      return;
    }

    let timeoutId: number | undefined;

    const handleLoaded = () => {
      if (!isMountedRef.current) {
        return;
      }
      setScriptStatus("ready");
      setErrorState({ script: null });
    };

    const handleError = (event: Event) => {
      console.error("Failed to load chatkit.js for some reason", event);
      if (!isMountedRef.current) {
        return;
      }
      setScriptStatus("error");
      setErrorState({
        script:
          "Failed to load ChatKit web component script. Check the network tab and script URL.",
        retryable: false,
      });
    };

    window.addEventListener("chatkit-script-loaded", handleLoaded);
    window.addEventListener(
      "chatkit-script-error",
      handleError as EventListener
    );

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
      window.removeEventListener(
        "chatkit-script-error",
        handleError as EventListener
      );
      if (timeoutId) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [scriptStatus, setErrorState]);

  const isWorkflowConfigured = Boolean(
    WORKFLOW_ID && !WORKFLOW_ID.startsWith("wf_replace")
  );

  useEffect(() => {
    if (!isWorkflowConfigured && isMountedRef.current) {
      setErrorState({
        session: "Set NEXT_PUBLIC_CHATKIT_WORKFLOW_ID in your .env.local file.",
        retryable: false,
      });
      setIsInitializingSession(false);
    }
  }, [isWorkflowConfigured, setErrorState]);

  const handleResetChat = useCallback(() => {
    processedFacts.current.clear();
    if (isBrowser) {
      setScriptStatus(
        window.customElements?.get("openai-chatkit") ? "ready" : "pending"
      );
    }
    setIsInitializingSession(true);
    setErrors(createInitialErrors());
    setWidgetInstanceKey((prev) => prev + 1);
  }, []);

  const getClientSecret = useCallback(
    async (currentSecret: string | null) => {
      const isMissing = !currentSecret || currentSecret.trim().length === 0;
      if (!isWorkflowConfigured) {
        if (isMountedRef.current) {
          setErrorState({
            session: "Set NEXT_PUBLIC_CHATKIT_WORKFLOW_ID in your .env.local.",
            retryable: false,
          });
        }
        return null;
      }

      if (isDev) {
        console.info("[ChatKitPanel] getClientSecret invoked", {
          currentSecretPresent: Boolean(currentSecret),
          workflowId: WORKFLOW_ID,
          endpoint: CREATE_SESSION_ENDPOINT,
        });
      }

      if (!isWorkflowConfigured) {
        const detail =
          "Set NEXT_PUBLIC_CHATKIT_WORKFLOW_ID in your .env.local file.";
        if (isMountedRef.current) {
          setErrorState({ session: detail, retryable: false });
          setIsInitializingSession(false);
        }
        throw new Error(detail);
      }

      try {
        const res = await fetch(CREATE_SESSION_ENDPOINT, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            workflow_id: WORKFLOW_ID,
          }),
        });

        if (!res.ok) {
          const text = await res.text().catch(() => "");
          const detail =
            extractErrorDetail(
              (text ? (JSON.parse(text) as any) : undefined) ?? undefined,
              `Session init failed with ${res.status}.`
            ) ?? `Session init failed with ${res.status}.`;
          throw new Error(detail);
        }

        const json = (await res.json()) as any;
        const secret = json?.client_secret?.value ?? null;

        if (secret && isMissing) {
          if (isMountedRef.current) {
            setIsInitializingSession(false);
            setErrors((e) => ({ ...e, session: null }));
          }
        }
        return secret;
      } catch (err) {
        if (isDev) {
          console.error("Error creating session", err);
        }
        const detail = extractErrorDetail(
          (err && typeof err === "object" ? (err as any) : undefined) ?? undefined,
          "Failed to initialize session."
        );
        if (isMountedRef.current) {
          setErrorState({
            session: detail,
            retryable: /timeout|temporary|again|network/i.test(detail ?? ""),
          });
          if (isMissing) {
            setIsInitializingSession(false);
          }
        }
        return null;
      } finally {
        if (isMountedRef.current && !currentSecret) {
          setIsInitializingSession(false);
        }
      }
    },
    [isWorkflowConfigured, setErrorState]
  );

  const chatkit = useChatKit({
    api: { getClientSecret },
    theme: {
      ...getThemeConfig(theme),
    },
    startScreen: {
      greeting: GREETING,
      prompts: STARTER_PROMPTS,
    },
    composer: {
      placeholder: PLACEHOLDER_INPUT,
      attachments: {
        // Enable attachments
        enabled: true,
      },
    },
    threadItemActions: {
      feedback: false,
    },
    onClientTool: async (toolCall: {
      name: string;
      params: Record<string, unknown>;
    }) => {
      try {
        if (toolCall.name === "save_pdf") {
          const html = String(toolCall.params?.html ?? "");
          onWidgetAction({ type: "savePdf", data: { html } });
          return { ok: true };
        }

        if (toolCall.name === "download_pdf") {
          const html = String(toolCall.params?.html ?? "");
          onWidgetAction({ type: "downloadPdf", data: { html } });
          return { ok: true };
        }
        
        if (toolCall.name === "persist_fact") {
          const factId = String(toolCall.params?.factId ?? "");
          const factText = String(toolCall.params?.factText ?? "");

          if (factText && !processedFacts.current.has(factId || factText)) {
            processedFacts.current.add(factId || factText);
            // No transcript insertion here—useChatKit() does not expose an append API.
            // If you want the app UI to react, trigger your own handler instead.
            // e.g., onWidgetAction({ type: "persistedFactNotice", data: { factId, factText } });
          }

          return { ok: true };
        }
      } catch (e) {
        if (isDev) console.error("onClientTool handler error", e);
      }
      return { ok: false };
    },
    onResponseEnd: () => {
      onResponseEnd();
    },
    onError: (payload: Record<string, unknown>) => {
      const detail = extractErrorDetail(payload, "Unknown error");
      setErrorState({
        integration:
          isDev && /CORS|fetch|network/i.test(detail ?? "")
            ? `${detail} — In development, ensure your local dev server allows CORS from the app origin.`
            : detail,
        retryable: /timeout|temporary|again/i.test(detail ?? ""),
      });
    },
  });

  useEffect(() => {
    const handler = (e: Event) => {
      const ce = e as CustomEvent;
      if (!ce?.detail || typeof ce.detail !== "object") return;

      const detail = ce.detail as any;

      if (detail.type === "response_end") {
        onResponseEnd();
        return;
      }

      if (detail.type === "theme_request" && detail.scheme) {
        onThemeRequest(detail.scheme as ColorScheme);
        return;
      }

      if (detail.type === "widget_action" && detail.action) {
        onWidgetAction(detail.action as WidgetAction);
        return;
      }
    };

    const el = document.querySelector("openai-chatkit");
    if (!el) return;
    el.addEventListener("chatkit", handler as EventListener);
    return () => el.removeEventListener("chatkit", handler as EventListener);
  }, [onResponseEnd, onThemeRequest, onWidgetAction]);

  return (
    <div className="flex h-full w-full flex-col">
      <div className="flex items-center justify-between border-b px-4 py-2">
        <div className="text-sm font-medium">ChatKit Demo</div>
        <div className="flex items-center gap-2">
          <ExportPdfButton filename="CR2A" />
        </div>
      </div>

      {scriptStatus !== "ready" ? (
        <div className="relative flex-1">
          <ErrorOverlay
            error={
              errors.script ??
              "Loading ChatKit component… If this takes more than a few seconds, check your network tab."
            }
            onRetry={
              errors.retryable
                ? () => {
                    setErrors(createInitialErrors());
                    setScriptStatus(
                      window.customElements?.get("openai-chatkit")
                        ? "ready"
                        : "pending"
                    );
                  }
                : null
            }
            retryLabel="Retry"
          />
        </div>
      ) : errors.session ? (
        <div className="relative flex-1">
          <ErrorOverlay
            error={errors.session}
            onRetry={
              errors.retryable
                ? () => {
                    setErrors(createInitialErrors());
                    setIsInitializingSession(true);
                  }
                : null
            }
            retryLabel="Restart chat"
          />
        </div>
      ) : errors.integration ? (
        <div className="relative flex-1">
          <ErrorOverlay
            error={errors.integration}
            onRetry={
              errors.retryable
                ? () => {
                    setErrors(createInitialErrors());
                    setIsInitializingSession(true);
                  }
                : null
            }
            retryLabel="Restart chat"
          />
        </div>
      ) : (
        <div className="relative flex-1">
          <ChatKit
            key={widgetInstanceKey}
            control={chatkit.control}
          />
        </div>
      )}

      <div className="flex items-center justify-between border-t px-4 py-2">
        <button
          className="rounded border px-2 py-1 text-xs"
          onClick={handleResetChat}
        >
          Reset chat
        </button>
        <div className="flex items-center justify-end">
          <ExportPdfButton filename="CR2A" />
        </div>
      </div>
    </div>
  );
}

function extractErrorDetail(
  payload: Record<string, unknown> | undefined,
  fallback: string
): string {
  if (!payload) {
    return fallback;
  }

  const error = payload.error;
  if (typeof error === "string") {
    return error;
  }

  if (error && typeof error === "object") {
    if ("message" in error && typeof (error as any).message === "string") {
      return (error as any).message;
    }
  }

  if ("detail" in payload) {
    const nestedError = (payload as { detail?: unknown }).detail;
    if (typeof nestedError === "string" && nestedError.trim().length > 0) {
      return nestedError;
    }
    if (
      nestedError &&
      typeof nestedError === "object" &&
      "message" in nestedError &&
      typeof (nestedError as { message?: unknown }).message === "string"
    ) {
      return (nestedError as { message: string }).message;
    }
  }

  if (typeof payload.message === "string") {
    return payload.message;
  }

  return fallback;
}