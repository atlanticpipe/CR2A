import { useCallback } from "react";
import { ChatKitPanel, type WidgetAction } from "./ChatKitPanel";
import { useColorScheme } from "./useColorScheme";
import ExportPdfButton from "./ExportPdfButton";

export default function App() {
  const { scheme, setScheme } = useColorScheme();

  const handleWidgetAction = useCallback(async (action: WidgetAction) => {
    if (import.meta.env.MODE !== "production") console.info("[ChatKitPanel]", action);
  }, []);

  const handleResponseEnd = useCallback(() => {
    if (import.meta.env.MODE !== "production") console.debug("[ChatKitPanel] end");
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