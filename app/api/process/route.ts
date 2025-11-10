import { NextResponse } from "next/server";
import OpenAI from "openai";

export const runtime = "nodejs";

const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY! });
const WORKFLOW_ID = process.env.OPENAI_WORKFLOW_ID!;
const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));

export async function POST(req: Request) {
  try {
    const form = await req.formData();
    const file = form.get("file") as File | null;
    const approvedClick = (form.get("approved") as string) === "true";
    const isPublic = (form.get("isPublic") as string) === "true"; // Yes=>public lane, No=>private lane

    if (!approvedClick) return NextResponse.json({ error: "Not approved" }, { status: 400 });
    if (!file) return NextResponse.json({ error: "No file" }, { status: 400 });

    // 1) Upload to OpenAI Files
    const buf = Buffer.from(await file.arrayBuffer());
    const uploaded = await client.files.create({
      file: new File([buf], file.name, { type: file.type || "application/octet-stream" }) as any,
      purpose: "assistants",
    });

    // 2) Start workflow run (use exact method/fields from the Builder “Code” panel)
    let run = await client.workflows.runs.create({
      workflow_id: WORKFLOW_ID,
      input: { is_public: isPublic },
      attachments: [{ file_id: uploaded.id, name: file.name }],
    } as any);

    // 3) Poll; if the workflow pauses for user approval, submit decision
    for (;;) {
      if (run.status === "requires_action" && run.required_action?.type === "user_approval") {
        // Approve => public path (no redline). Reject => private path (redline).
        await client.workflows.runs.submitApproval({
          run_id: run.id,
          node_id: run.required_action.node_id,
          action: isPublic ? "approve" : "reject",
        } as any);
      }

      if (run.status === "succeeded" || run.status === "completed") break;
      if (run.status === "failed" || run.status === "cancelled") throw new Error(`Workflow ${run.status}`);

      await sleep(800);
      run = await client.workflows.runs.get({ run_id: run.id } as any);
    }

    // 4) Locate the PDF artifact in outputs and stream it
    const pdfId =
      run.result?.pdf_file_id ||
      run.outputs?.find((o: any) => o.type === "file" && o.mime === "application/pdf")?.file_id;

    if (!pdfId) throw new Error("No PDF artifact found in workflow result.");

    const pdfRes = await client.files.content(pdfId);
    const pdfBuf = Buffer.from(await pdfRes.arrayBuffer());

    return new NextResponse(pdfBuf, {
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