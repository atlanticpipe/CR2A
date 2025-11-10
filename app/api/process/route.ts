import { NextResponse } from "next/server";
import OpenAI from "openai";

export const runtime = "nodejs";

// ----- Env (server-only) -----
const MUST = (k: string, v?: string) => { if (!v) throw new Error(`Missing env: ${k}`); return v; };
const OPENAI_API_KEY     = MUST("OPENAI_API_KEY", process.env.OPENAI_API_KEY);
const OPENAI_WORKFLOW_ID = MUST("OPENAI_WORKFLOW_ID", process.env.OPENAI_WORKFLOW_ID);

// ----- SDK client -----
const client = new OpenAI({ apiKey: OPENAI_API_KEY });

// Resolve the Workflows surface regardless of SDK version
function getWfApi(c: any) {
  // known homes for the API across versions
  const wf =
    c.workflows ??
    c.beta?.workflows ??
    c.agentWorkflows ??          // some enterprise builds
    c.agents?.workflows ?? null; // very old previews

  if (!wf) {
    const available = Object.keys(c).join(", ");
    throw new Error(
      `Workflows API not available in this SDK build. Installed surfaces: [${available}]. ` +
      `Upgrade: npm i openai@latest`
    );
  }
  return wf;
}

// Submit approval across method variants
async function submitApproval(wf: any, runId: string, nodeId: string, action: "approve" | "reject") {
  // 1) .runs.approvals.create(runId, {...})
  if (wf.runs?.approvals?.create) {
    return wf.runs.approvals.create(runId, { node_id: nodeId, action });
  }
  // 2) .runs.submitApproval({ run_id, node_id, action })
  if (wf.runs?.submitApproval) {
    return wf.runs.submitApproval({ run_id: runId, node_id: nodeId, action });
  }
  // 3) Separate helpers (rare)
  if (action === "approve" && wf.runs?.approve) return wf.runs.approve(runId, { node_id: nodeId });
  if (action === "reject"  && wf.runs?.reject)  return wf.runs.reject(runId,  { node_id: nodeId });

  throw new Error("SDK lacks a known approval method. Update the openai package.");
}

const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));

export async function POST(req: Request) {
  try {
    const wf = getWfApi(client as any);

    const form = await req.formData();
    const file = form.get("file") as File | null;
    const approvedClick = (form.get("approved") as string) === "true";
    const isPublic = (form.get("isPublic") as string) === "true"; // Approve => public branch

    if (!approvedClick) return NextResponse.json({ error: "Not approved" }, { status: 400 });
    if (!file)          return NextResponse.json({ error: "No file" }, { status: 400 });

    // 1) Upload file
    const uploaded = await client.files.create({ file, purpose: "assistants" });

    // 2) Start workflow run (support both .create({}) and .create({ ...payload }))
    const startPayload = {
      workflow_id: OPENAI_WORKFLOW_ID,
      attachments: [{ file_id: uploaded.id, name: (file as any).name ?? "input.pdf" }],
      input: {},
      inputs: {}
    };

    const runStart =
      (await (wf.runs?.create?.(startPayload))) ??
      (await (wf.runs?.create?.call(wf.runs, startPayload)));

    if (!runStart?.id) {
      throw new Error("Workflows: run start returned no id (check SDK version).");
    }

    // 3) Poll and handle approval
    for (;;) {
      const cur = await wf.runs.retrieve(runStart.id);

      if (cur?.status === "requires_action" && cur.required_action?.type === "user_approval") {
        await submitApproval(wf, cur.id, cur.required_action.node_id, isPublic ? "approve" : "reject");
      }

      if (cur?.status === "succeeded" || cur?.status === "completed") {
        const outputs = cur.outputs ?? cur.result ?? [];
        const candidate =
          outputs.find?.((o: any) =>
            (o.type === "file" || o.kind === "file") &&
            (o.mime === "application/pdf" || o.file?.mime === "application/pdf")
          )
          ?? outputs.find?.((o: any) => o.pdf_file_id)
          ?? outputs.find?.((o: any) => o.file?.id && o.file?.mime === "application/pdf")
          ?? null;

        const pdfFileId: string | undefined =
          candidate?.file_id || candidate?.file?.id || candidate?.pdf_file_id;

        if (!pdfFileId) throw new Error("No PDF artifact found on workflow result.");

        const pdf = await client.files.content(pdfFileId);
        const buf = Buffer.from(await pdf.arrayBuffer());

        return new NextResponse(buf, {
          status: 200,
          headers: {
            "Content-Type": "application/pdf",
            "Content-Disposition": `attachment; filename="${isPublic ? "results.public.pdf" : "results.private.pdf"}"`,
            "Cache-Control": "no-store",
          },
        });
      }

      if (cur?.status === "failed" || cur?.status === "cancelled") {
        throw new Error(`Workflow ${cur.status}`);
      }

      await sleep(900);
    }
  } catch (e: any) {
    console.error("PROCESS_ERROR", e);
    return NextResponse.json({ error: e?.message ?? "Server error" }, { status: 500 });
  }
}