import { NextResponse } from "next/server";

export const runtime = "nodejs";

/** ----- Env (server only) ----- */
const MUST = (k: string, v?: string) => { if (!v) throw new Error(`Missing env: ${k}`); return v; };
const OPENAI_API_KEY      = MUST("OPENAI_API_KEY", process.env.OPENAI_API_KEY);
const OPENAI_WORKFLOW_ID  = MUST("OPENAI_WORKFLOW_ID", process.env.OPENAI_WORKFLOW_ID);
const OPENAI_API_URL      = process.env.OPENAI_API_URL || "https://api.openai.com";

/** Optional: force a prefix like "/v1/agent-workflows" */
const WF_PREFIX_OVERRIDE  = process.env.WF_PREFIX || "";

/** Known REST mount points across tenants */
const CANDIDATE_PREFIXES = (WF_PREFIX_OVERRIDE
  ? [WF_PREFIX_OVERRIDE]
  : ["/v1/agent-workflows", "/v1/workflows", "/v1/agents/workflows"]
).map(p => p.replace(/\/+$/, "")); // trim trailing slash

const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));

type RunLike = {
  id: string;
  status: string;
  outputs?: any[];
  result?: any[];
  required_action?: { type?: string; node_id?: string };
};

/** Try a POST; if it returns 404 Invalid URL, move to next prefix */
async function tryPostJson<T>(url: string, body: any): Promise<{ ok: boolean; json?: T; status: number; text?: string }> {
  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${OPENAI_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  let json: any;
  try { json = JSON.parse(text); } catch { /* non-json */ }
  return { ok: res.ok, json, status: res.status, text: json ? undefined : text };
}

async function tryGetJson<T>(url: string): Promise<{ ok: boolean; json?: T; status: number; text?: string }> {
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${OPENAI_API_KEY}` },
  });
  const text = await res.text();
  let json: any;
  try { json = JSON.parse(text); } catch { /* non-json */ }
  return { ok: res.ok, json, status: res.status, text: json ? undefined : text };
}

/** Resolve the first working prefix by starting a dummy run */
async function resolvePrefix(): Promise<string> {
  const payload = { workflow_id: OPENAI_WORKFLOW_ID, input: {}, inputs: {}, attachments: [] };
  for (const prefix of CANDIDATE_PREFIXES) {
    const url = `${OPENAI_API_URL}${prefix}/runs`;
    const r = await tryPostJson<RunLike>(url, payload);
    // 401/403/422 means the path exists (auth/validation), 200-202 means started.
    if (r.ok || [401, 403, 422].includes(r.status)) return prefix;
    // 404 with message "Invalid URL" => wrong prefix, continue
  }
  throw new Error(
    `No valid Workflows endpoint found. Tried: ${CANDIDATE_PREFIXES.join(", ")} on ${OPENAI_API_URL}`
  );
}

export async function POST(req: Request) {
  try {
    const form = await req.formData();
    const file = form.get("file") as File | null;
    const approvedClick = (form.get("approved") as string) === "true";
    const isPublic = (form.get("isPublic") as string) === "true";

    if (!approvedClick) return NextResponse.json({ error: "Not approved" }, { status: 400 });
    if (!file) return NextResponse.json({ error: "No file" }, { status: 400 });

    // 0) Find the correct REST prefix for this tenant
    const PREFIX = await resolvePrefix();

    // 1) Upload file to Files API
    const fd = new FormData();
    fd.append("file", file, (file as any).name ?? "input.pdf");
    fd.append("purpose", "assistants");
    const upRes = await fetch(`${OPENAI_API_URL}/v1/files`, {
      method: "POST",
      headers: { Authorization: `Bearer ${OPENAI_API_KEY}` },
      body: fd,
    });
    if (!upRes.ok) {
      throw new Error(`File upload failed: ${upRes.status} ${await upRes.text()}`);
    }
    const uploaded = await upRes.json();

    // 2) Start workflow run
    const startUrl = `${OPENAI_API_URL}${PREFIX}/runs`;
    const startBody = {
      workflow_id: OPENAI_WORKFLOW_ID,
      input: {},
      inputs: {},
      attachments: [{ file_id: uploaded.id, name: (file as any).name ?? "input.pdf" }],
    };
    const start = await tryPostJson<RunLike>(startUrl, startBody);
    if (!start.ok || !start.json?.id) {
      throw new Error(`Run start failed (${start.status}): ${JSON.stringify(start.json ?? start.text)}`);
    }
    let run: RunLike = start.json;

    // 3) Poll; when approval is requested, submit user's choice
    const getUrl = (id: string) => `${OPENAI_API_URL}${PREFIX}/runs/${id}`;
    const approvalUrl = (id: string) => `${OPENAI_API_URL}${PREFIX}/runs/${id}/approval`;

    for (;;) {
      if (run.status === "requires_action" && run.required_action?.type === "user_approval") {
        const apr = await tryPostJson<any>(approvalUrl(run.id), {
          node_id: run.required_action.node_id,
          action: isPublic ? "approve" : "reject",
        });
        if (!apr.ok) {
          throw new Error(`Approval submit failed (${apr.status}): ${JSON.stringify(apr.json ?? apr.text)}`);
        }
      }

      if (run.status === "succeeded" || run.status === "completed") break;
      if (run.status === "failed" || run.status === "cancelled") {
        throw new Error(`Workflow ${run.status}`);
      }

      await sleep(900);
      const st = await tryGetJson<RunLike>(getUrl(run.id));
      if (!st.ok) {
        throw new Error(`Status fetch failed (${st.status}): ${JSON.stringify(st.json ?? st.text)}`);
      }
      run = st.json!;
    }

    // 4) Extract the PDF artifact from outputs and stream it
    const outputs = (run.outputs ?? run.result ?? []) as any[];
    const pdfOut =
      outputs.find?.((o: any) =>
        (o.type === "file" || o.kind === "file") &&
        (o.mime === "application/pdf" || o.file?.mime === "application/pdf")
      ) ??
      outputs.find?.((o: any) => o.pdf_file_id) ??
      outputs.find?.((o: any) => o.file?.id && o.file?.mime === "application/pdf");

    const pdfFileId: string | undefined = pdfOut?.file_id || pdfOut?.file?.id || pdfOut?.pdf_file_id;
    if (!pdfFileId) throw new Error("No PDF artifact found on workflow result.");

    const pdfRes = await fetch(`${OPENAI_API_URL}/v1/files/${pdfFileId}/content`, {
      headers: { Authorization: `Bearer ${OPENAI_API_KEY}` },
    });
    if (!pdfRes.ok) {
      throw new Error(`PDF download failed: ${pdfRes.status} ${await pdfRes.text()}`);
    }
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
    console.error("PROCESS_ERROR", e);
    return NextResponse.json({ error: e?.message ?? "Server error" }, { status: 500 });
  }
}