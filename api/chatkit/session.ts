export default async function handler(req: any, res: any) {
  try {
    if (req.method !== "POST") {
      res.setHeader("Allow", "POST");
      return res.status(405).json({ error: "Method Not Allowed" });
    }

    const id = process.env.OPENAI_WORKFLOW_ID; // may actually be a workflow *or* an assistant
    const apiKey = process.env.OPENAI_API_KEY;
    if (!id) return res.status(500).json({ error: "Missing OPENAI_WORKFLOW_ID" });
    if (!apiKey) return res.status(500).json({ error: "Missing OPENAI_API_KEY" });

    // Decide which parameter the OpenAI endpoint expects based on the ID prefix
    const isWorkflow = /^wf_/.test(id);
    const body =
      isWorkflow ? { workflow_id: id } : { assistant_id: id };

    // If your endpoint requires beta headers, include them.
    // Assistants v2 is common; add workflows if you're really using a workflow id.
    const beta = isWorkflow ? "assistants=v2,workflows=v1" : "assistants=v2";

    const resp = await fetch("https://api.openai.com/v1/chat/sessions", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${apiKey}`,
        "Content-Type": "application/json",
        "OpenAI-Beta": beta
      },
      body: JSON.stringify(body)
    });

    if (!resp.ok) {
      const detail = await resp.text().catch(() => "");
      return res.status(resp.status).json({ error: "OpenAI session create failed", detail });
    }

    const data: any = await resp.json();
    const value =
      (typeof data?.client_secret === "object"
        ? data?.client_secret?.value
        : data?.client_secret) ?? null;

    return res.status(200).json({ client_secret: { value } });
  } catch (err: any) {
    return res.status(500).json({
      error: "Server error creating ChatKit session",
      detail: err?.message ?? String(err),
    });
  }
}