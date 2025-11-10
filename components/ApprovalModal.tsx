"use client";
import { useEffect } from "react";

export default function ApprovalModal({
  open, onApprove, onCancel,
}: { open: boolean; onApprove: () => void; onCancel: () => void }) {
  useEffect(() => {
    if (open) document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = ""; };
  }, [open]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl p-6 w-[420px] shadow-xl">
        <h2 className="text-xl font-semibold mb-2">Approve workflow</h2>
        <p className="text-sm mb-4">
          Confirm you approve processing this file. A PDF will be generated.
        </p>
        <div className="flex justify-end gap-2">
          <button onClick={onCancel} className="px-3 py-2 rounded border">Cancel</button>
          <button onClick={onApprove} className="px-3 py-2 rounded bg-black text-white">Approve</button>
        </div>
      </div>
    </div>
  );
}