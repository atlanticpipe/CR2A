"use client";
import { useEffect } from "react";

export default function ApprovalModal({
  open, onPublic, onPrivate, onCancel,
}: {
  open: boolean;
  onPublic: () => void;   // maps to APPROVE at the platform node
  onPrivate: () => void;  // maps to REJECT at the platform node
  onCancel: () => void;
}) {
  useEffect(() => {
    if (open) document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = ""; };
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl p-6 w-[460px] shadow-xl">
        <h2 className="text-xl font-semibold mb-2">Is this a Public Contract?</h2>
        <p className="text-sm mb-4">Choose the path. Public skips redlining; Private applies redlining.</p>
        <div className="flex justify-between">
          <button onClick={onCancel} className="px-3 py-2 rounded border">Cancel</button>
          <div className="flex gap-2">
            <button onClick={onPrivate} className="px-3 py-2 rounded border">Private</button>
            <button onClick={onPublic} className="px-3 py-2 rounded bg-black text-white">Public</button>
          </div>
        </div>
      </div>
    </div>
  );
}