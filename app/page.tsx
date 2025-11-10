"use client";
import { useState } from "react";
import FilePicker from "@/components/FilePicker";
import ApprovalModal from "@/components/ApprovalModal";

export default function Page() {
  const [file, setFile] = useState<File | null>(null);
  const [showApproval, setShowApproval] = useState(false);
  const [downloading, setDownloading] = useState(false);

  async function handleApprove() {
    if (!file) return;
    setShowApproval(false);
    setDownloading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("approved", "true");
      const res = await fetch("/api/process", { method: "POST", body: fd });
      if (!res.ok) throw new Error(await res.text());

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "results.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } finally {
      setDownloading(false);
    }
  }

  return (
    <main className="p-6">
      <h1 className="text-2xl font-bold mb-4">Minimal workflow</h1>
      <div className="flex flex-col gap-4 max-w-xl">
        <FilePicker onPick={setFile} />
        <button
          disabled={!file || downloading}
          onClick={() => setShowApproval(true)}
          className="px-4 py-2 rounded bg-black text-white disabled:opacity-50 w-fit"
        >
          {downloading ? "Processing…" : "Start workflow"}
        </button>
        {!file && <p className="text-sm text-gray-600">Choose a file to enable the button.</p>}
      </div>
      <ApprovalModal
        open={showApproval}
        onApprove={handleApprove}
        onCancel={() => setShowApproval(false)}
      />
    </main>
  );
}