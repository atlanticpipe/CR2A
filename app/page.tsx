"use client";

import { useState } from "react";
import FilePicker from "@/components/FilePicker";
import ApprovalModal from "@/components/ApprovalModal";
import styles from "./page.module.css";

export default function Page() {
  const [file, setFile] = useState<File | null>(null);
  const [showApproval, setShowApproval] = useState(false);
  const [running, setRunning] = useState(false);

  async function run(isPublic: boolean) {
    if (!file) return;
    setShowApproval(false);
    setRunning(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("approved", "true");            // gate
      fd.append("isPublic", String(isPublic));  // decision => APPROVE/REJECT at platform node

      // add ?debug=1 to see server logs in Vercel (optional)
      const res = await fetch("/api/process", { method: "POST", body: fd });

      if (!res.ok) {
        let msg: string;
        try { msg = (await res.json()).error; } catch { msg = await res.text(); }
        alert(msg || "Workflow failed");
        return;
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = isPublic ? "results.public.pdf" : "results.private.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error(e);
      alert("Unexpected error running workflow");
    } finally {
      setRunning(false);
    }
  }

  return (
    <main className={styles.main}>
      <h1 className="text-2xl font-bold mb-4">Minimal workflow</h1>
      <div className="flex flex-col gap-4 max-w-xl">
        <FilePicker onPick={setFile} />
        <button
          disabled={!file || running}
          onClick={() => setShowApproval(true)}
          className="px-4 py-2 rounded bg-black text-white disabled:opacity-50 w-fit"
        >
          {running ? "Running…" : "Start workflow"}
        </button>
      </div>

      <ApprovalModal
        open={showApproval}
        onCancel={() => setShowApproval(false)}
        onPublic={() => run(true)}    // Public lane (Approve)
        onPrivate={() => run(false)}  // Private lane (Reject)
      />
    </main>
  );
}