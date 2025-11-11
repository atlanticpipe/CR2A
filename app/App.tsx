import { useCallback } from "react";
import { ChatKitPanel, type FactAction } from "components/ChatKitPanel";  // if ChatKitPanel.tsx is at repo root
import { useColorScheme } from "hooks/useColorScheme";
import ExportPdfButton from "components/ExportPdfButton";

export default function App() {
  const { scheme, setScheme } = useColorScheme();

  const handleWidgetAction = useCallback(async (action: FactAction) => {
    if (import.meta.env.MODE !== "production") {
      console.info("[ChatKitPanel] widget action", action);
    }
  }, []);

  const handleResponseEnd = useCallback(() => {
    if (import.meta.env.MODE !== "production") {
      console.debug("[ChatKitPanel] response end");
    }
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-end bg-slate-100 dark:bg-slate-950">
      <div className="mx-auto w-full max-w-5xl">
        <ChatKitPanel
          theme={scheme}
          onWidgetAction={handleWidgetAction}
          onResponseEnd={handleResponseEnd}
          onThemeRequest={setScheme}
        />
        <div className="mt-4 flex justify-end">
          <ExportPdfButton filename="CR2A" />
        </div>
      </div>
    </main>
  );
}