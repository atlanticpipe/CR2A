import { NextResponse } from "next/server";
import OpenAI from "openai";

export const runtime = "nodejs";

// ----- Env (server-only) -----
const MUST = (k: string, v?: string) => { if (!v) throw new Error(`Missing env: ${k}`); return v; };
const OPENAI_API_KEY      = MUST("OPENAI_API_KEY", process.env.OPENAI_API_KEY);
const OPENAI_WORKFLOW_ID  = MUST("OPENAI_WORKFLOW_ID", process.env.OPENAI_WORKFLOW_ID);

// ----- SDK client -----
const client = new OpenAI({ apiKey: OPENAI_API_KEY });

// Small helper
const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));

export async function POST(req: Request) {
  try {
    const form = await req.formData();
    const file = form.get("file") as File | null;
    const approvedClick = (form.get("approved") as string) === "true";
    const isPublic = (form.get("isPublic") as string) === "true"; // Approve => public path; Reject => private path

    if (!approvedClick) return NextResponse.json({ error: "Not approved" }, { status: 400 });
    if (!file) return NextResponse.json({ error: "No file" }, { status: 400 });

    // 1) Upload file to Files API
    const upload = await client.files.create({
      file,
      purpose: "assistants",
    });
    // 2) Start the workflow run (no app-side logic; your builder controls branching)
    //    NOTE: Workflows are in the SDK (no REST needed for your tenant).
    //    The method names are available on the latest 'openai' package.
    //    If TS types lag, cast to any to avoid build-time friction.
    // @ts-ignore - accommodate SDK version drift
    const run = await (client as any).workflows.runs.create({
      workflow_id: OPENAI_WORKFLOW_ID,
      attachments: [{ file_id: upload.id, name: (file as any).name ?? "input.pdf" }],
      input: {},   // your graph doesn’t require explicit inputs
      inputs: {},  // keep both for forward-compat
    });

    let runId = run.id;

    // 3) Poll and submit the approval as soon as it’s requested
    // @ts-ignore
    const retrieve = (id: string) => (client as any).workflows.runs.retrieve(id);
    // @ts-ignore
    const approve = (id: string, node_id: string, action: "approve" | "reject") =>
      (client as any).workflows.runs.approvals.create(id, { node_id, action });

    for (;;) {
      const cur = await retrieve(runId);

      if (cur.status === "requires_action" && cur.required_action?.type === "user_approval") {
        await approve(cur.id, cur.required_action.node_id, isPublic ? "approve" : "reject");
      }

      if (cur.status === "succeeded" || cur.status === "completed") {
        // 4) Find the PDF artifact and stream it back
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

      if (cur.status === "failed" || cur.status === "cancelled") {
        throw new Error(`Workflow ${cur.status}`);
      }

      await sleep(900);
    }
  } catch (e: any) {
    console.error("PROCESS_ERROR", e);
    return NextResponse.json({ error: e?.message ?? "Server error" }, { status: 500 });
  }
}