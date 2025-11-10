import { NextResponse } from "next/server";

export const runtime = "nodejs";

// ----- REST endpoints (confirm against the Builder "Code" panel) -----
const API_BASE = "https://api.openai.com";
const FILES_CREATE   = `${API_BASE}/v1/files`;
const FILES_CONTENT  = (id: string) => `${API_BASE}/v1/files/${id}/content`;
const RUNS_CREATE    = `${API_BASE}/v1/workflows/runs`;
const RUNS_GET       = (id: string) => `${API_BASE}/v1/workflows/runs/${id}`;
const RUNS_APPROVAL  = (id: string) => `${API_BASE}/v1/workflows/runs/${id}/approval`;

// ----- Env (provided by Vercel dashboard; not in repo) -----
const MUST = (k: string, v?: string) => { if (!v) throw new Error(`Missing env: ${k}`); return v; };
const OPENAI_API_KEY   = MUST("OPENAI_API_KEY", process.env.OPENAI_API_KEY);
const OPENAI_WORKFLOW_ID = MUST("OPENAI_WORKFLOW_ID", process.env.OPENAI_WORKFLOW_ID);

const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));

export async function POST(req: Request) {
  try {
    const form = await req.formData();
    const file = form.get("file") as File | null;
    const approvedClick = (form.get("approved") as string) === "true";
    const isPublic = (form.get("isPublic") as string) === "true"; // Yes=public (Approve), No=private (Reject)

    if (!approvedClick) return NextResponse.json({ error: "Not approved" }, { status: 400 });
    if (!file) return NextResponse.json({ error: "No file" }, { status: 400 });

    // 1) Upload file to OpenAI Files (multipart)
    const uploadFd = new FormData();
    uploadFd.append("file", file, file.name);
    uploadFd.append("purpose", "assistants"); // accepted for workflow attachments

    const upRes = await fetch(FILES_CREATE, {
      method: "POST",
      headers: { Authorization: `Bearer ${OPENAI_API_KEY}` },
      body: uploadFd,
    });
    if (!upRes.ok) throw new Error(`File upload failed: ${upRes.status} ${await upRes.text()}`);
    const uploaded = await upRes.json(); // { id, ... }

    // 2) Start workflow run (no app-side logic; just attach the file)
    const startRes = await fetch(RUNS_CREATE, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${OPENAI_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        workflow_id: OPENAI_WORKFLOW_ID,
        attachments: [{ file_id: uploaded.id, name: file.name }],
        // no input payload needed; your approval node drives the branch
      }),
    });
    if (!startRes.ok) throw new Error(`Run start failed: ${startRes.status} ${await startRes.text()}`);
    let run = await startRes.json();

    // 3) Poll; when the User approval node is hit, submit the user's choice
    for (;;) {
      if (run.status === "requires_action" && run.required_action?.type === "user_approval") {
        const apr = await fetch(RUNS_APPROVAL(run.id), {
          method: "POST",
          headers: {
            Authorization: `Bearer ${OPENAI_API_KEY}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            node_id: run.required_action.node_id,
            action: isPublic ? "approve" : "reject", // Approve => public path; Reject => private path
          }),
        });
        if (!apr.ok) throw new Error(`Approval submit failed: ${apr.status} ${await apr.text()}`);
      }

      if (run.status === "succeeded" || run.status === "completed") break;
      if (run.status === "failed" || run.status === "cancelled") {
        throw new Error(`Workflow ${run.status}`);
      }

      await sleep(900);
      const st = await fetch(RUNS_GET(run.id), {
        headers: { Authorization: `Bearer ${OPENAI_API_KEY}` },
      });
      if (!st.ok) throw new Error(`Status fetch failed: ${st.status} ${await st.text()}`);
      run = await st.json();
    }

    // 4) Find the PDF artifact in the outputs and stream it back
    const outputs = run.outputs || run.result || [];
    const pdfOut =
      outputs.find?.((o: any) =>
        (o.type === "file" || o.kind === "file") &&
        (o.mime === "application/pdf" || o.file?.mime === "application/pdf")
      ) ||
      outputs.find?.((o: any) => o.pdf_file_id);

    const pdfFileId =
      pdfOut?.file_id || pdfOut?.file?.id || pdfOut?.pdf_file_id;

    if (!pdfFileId) throw new Error("No PDF artifact found on workflow result.");

    const pdfRes = await fetch(FILES_CONTENT(pdfFileId), {
      headers: { Authorization: `Bearer ${OPENAI_API_KEY}` },
    });
    if (!pdfRes.ok) throw new Error(`PDF download failed: ${pdfRes.status} ${await pdfRes.text()}`);
    const buf = Buffer.from(await pdfRes.arrayBuffer());

    return new NextResponse(buf, {
      status: 200,
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `attachment; filename="${isPublic ? "results.public.pdf" : "results.private.pdf"}"`,
        "Cache-Control": "no-store",
      },
    });
  } catch (e: any) {
    console.error(e);
    return NextResponse.json({ error: e.message || "Server error" }, { status: 500 });
  }
}