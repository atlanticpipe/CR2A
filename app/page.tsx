"use client";
import { useRef, useState } from "react";

export default function Page() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [isPublic, setIsPublic] = useState(true); // true => approve (public); false => reject (private)
  const [filename, setFilename] = useState<string>("");
  const [busy, setBusy] = useState<"idle" | "upload" | "running" | "downloading">("idle");
  const [msg, setMsg] = useState<string>("");

  async function run() {
    setMsg("");
    const file = fileRef.current?.files?.[0];
    if (!file) {
      setMsg("Select a file first.");
      return;
    }

    try {
      setBusy("upload");
      const fd = new FormData();
      fd.append("file", file);
      // We auto-approve here so your Builder “User approval” node receives the choice
      fd.append("approved", "true");
      fd.append("isPublic", String(isPublic));

      setBusy("running");
      const res = await fetch("/api/process", { method: "POST", body: fd });

      if (!res.ok) {
        const err = await safeJson(res);
        throw new Error(err?.error || `Server error ${res.status}`);
      }

      // Expecting application/pdf from the API
      setBusy("downloading");
      const blob = await res.blob();
      if (blob.type !== "application/pdf") {
        throw new Error("API did not return a PDF.");
      }

      // Download
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = isPublic ? "results.public.pdf" : "results.private.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setBusy("idle");
      setMsg("Done.");
    } catch (e: any) {
      setBusy("idle");
      setMsg(e?.message || "Failed.");
      alert(e?.message || "Failed.");
    }
  }

  return (
    <main className="min-h-screen bg-neutral-50 text-neutral-900">
      <div className="max-w-3xl mx-auto px-6 py-12">
        <header className="mb-8">
          <h1 className="text-3xl font-semibold tracking-tight">Minimal workflow</h1>
          <p className="text-sm text-neutral-500 mt-1">
            Upload a contract, choose Public/Private, run workflow, download PDF.
          </p>
        </header>

        <section className="rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <input
                ref={fileRef}
                type="file"
                accept="application/pdf"
                onChange={(e) => setFilename(e.target.files?.[0]?.name ?? "")}
                disabled={busy !== "idle"}
                className="block w-full text-sm file:mr-4 file:rounded-md file:border-0 file:bg-neutral-900 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-neutral-800"
              />
            </div>

            {filename && (
              <div className="text-xs text-neutral-500">Selected: {filename}</div>
            )}

            <div className="flex items-center gap-6">
              <label className="inline-flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="branch"
                  checked={isPublic}
                  onChange={() => setIsPublic(true)}
                  disabled={busy !== "idle"}
                />
                <span className="text-sm">Public (no redlines)</span>
              </label>
              <label className="inline-flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="branch"
                  checked={!isPublic}
                  onChange={() => setIsPublic(false)}
                  disabled={busy !== "idle"}
                />
                <span className="text-sm">Private (apply redlines)</span>
              </label>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={run}
                disabled={busy !== "idle"}
                className="rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
              >
                {busy === "idle" ? "Start workflow" :
                 busy === "upload" ? "Uploading…" :
                 busy === "running" ? "Running…" :
                 "Downloading…"}
              </button>
              {msg && <span className="text-sm text-neutral-500">{msg}</span>}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

async function safeJson(res: Response) {
  try { return await res.json(); } catch { return undefined; }
}