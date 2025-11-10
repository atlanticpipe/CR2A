"use client";
export default function FilePicker({ onPick }:{ onPick: (file: File | null) => void }) {
  return (
    <input type="file" onChange={(e) => onPick(e.target.files?.[0] ?? null)} />
  );
}