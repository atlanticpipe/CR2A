'use client';

import { useState } from 'react';

type Props = {
  content?: string;    // the final answer text to export
  title?: string;      // optional PDF doc title
  filename?: string;   // optional filename (no extension)
  className?: string;  // optional styling hook
};

// What the API may return on error
type ErrorPayload = { type?: string; message?: string };

export default function ExportPdfButton({
  content,
  title = 'CR2A Results',
  filename = 'CR2A',
  className,
}: Props) {
  const [busy, setBusy] = useState(false);

  // Fetch with a hard timeout so the UI never gets stuck.
  const postWithTimeout = async (
    url: string,
    body: unknown,
    ms = 20_000
  ): Promise<Response> => {
    const ctrl = new AbortController();
    const to = setTimeout(() => ctrl.abort(), ms);
    try {
      return await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: ctrl.signal,
      });
    } finally {
      clearTimeout(to);
    }
  };

  const onClick = async (): Promise<void> => {
    // Fallback: scrape the final answer from the DOM if no prop was given
    const node =
      typeof document !== 'undefined'
        ? (document.getElementById('cr2a-answer') as HTMLElement | null)
        : null;
    const scraped = node ? (node.innerText?.trimEnd() || node.textContent ||'') : '';
    const text = content && content.trim() ? content : scraped;
    if (!text || !text.trim()) {
      alert('ValidationError: Nothing to export yet.');
      return;
    }

    setBusy(true);
    try {
      const res = await postWithTimeout('/api/export-pdf', { content: text, title, filename });

      if (!res.ok) {
        // Parse an optional error body without using `any`
        let payload: ErrorPayload | null = null;
        try {
          const json: unknown = await res.json();
          if (json && typeof json === 'object') {
            payload = json as ErrorPayload;
          }
        } catch {
          // ignore parse errors
        }

        const t =
          payload?.type ??
          (res.status === 422
            ? 'ValidationError'
            : res.status === 408
            ? 'TimeoutError'
            : res.status >= 500
            ? 'ProcessingError'
            : 'NetworkError');

        const msg = payload?.message ?? `Export failed (HTTP ${res.status}).`;
        alert(`${t}: ${msg}`);
        console.error('[export-pdf]', t, res.status);
        return;
      }

      // Success: stream -> blob -> temporary link -> click -> revoke
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${filename.replace(/[^-\w]/g, '') || 'CR2A'}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      // Narrow unknown error without `any`
      const name = err instanceof Error ? err.name : undefined;
      const type = name === 'AbortError' ? 'TimeoutError' : 'NetworkError';
      alert(`${type}: Unable to reach /api/export-pdf.`);
      console.error('[export-pdf]', type);
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={busy}
      className={className}
      aria-busy={busy}
      title="Download PDF"
    >
      {busy ? 'Preparing…' : 'Download PDF'}
    </button>
  );
}