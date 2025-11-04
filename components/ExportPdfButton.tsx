'use client';

import { useState } from 'react';

type Props = {
    content?: string;          // the final answer text to export
    title?: string;           // optional PDF doc title
    filename?: string;        // optional filename (no extension)
    className?: string;       // optional styling hook
};

export default function ExportPdfButton({
    content,
    title = 'CR2A Results',
    filename = 'CR2A',
    className,
}: Props) {
    const [busy, setBusy] = useState(false);

    // Small helper: fetch with a hard timeout so the UI never gets stuck.
    const postWithTimeout = async (url: string, body: unknown, ms = 20000) => {
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

  const onClick = async () => {
    // Fallback: scrape the final answer from the DOM if no prop was given
    const scraped =
        typeof document !== 'undefined'
            ? (document.getElementById('cr2a-answer')?.textContent ?? '')
            : '';
    const text = content && content.trim() ? content : scraped;
    if (!text || !text.trim()) {
        alert('ValidationError: Nothing to export yet.');
        return;
    }

    setBusy(true);
    try {
        // Call our minimal API -> may fail due to env, auth, or server error
        const res = await postWithTimeout('/api/export-pdf', { content: text, title, filename });

      if (!res.ok) {
        // Try to classify the failure for a clear, actionable message
        let payload: any = null;
        try { payload = await res.json(); } catch { /* ignore */ }
        const t =
            payload?.type ||
            (res.status === 422
                ? 'ValidationError'
                : res.status === 408
                ? 'TimeoutError'
                : res.status >= 500
                ? 'ProcessingError'
                : 'NetworkError');

        const msg = payload?.message || `Export failed (HTTP ${res.status}).`;
        alert(`${t}: ${msg}`);
        console.error('[export-pdf]', t, res.status); // terse; no secrets
        return;
        // Busy flag is cleared in finally
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
    } catch (err: any) {
        // AbortError = timeout; otherwise treat as network
        const type = err?.name === 'AbortError' ? 'TimeoutError' : 'NetworkError';
        alert(`${type}: Unable to reach /api/export-pdf.`);
        console.error('[export-pdf]', type); // terse, no details
    } finally {
        setBusy(false); // always clear busy state
    }
};

return (
    <button
        type="button"
        onClick={onClick}
        disabled={busy || !content?.trim()}
        className={className}
        aria-busy={busy}
        title="Download PDF"
    >
        {busy ? 'Preparing…' : 'Download PDF'}
    </button>
  );
}