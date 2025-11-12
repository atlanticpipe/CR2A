export default async function handler(req: any, res: any) {
  try {
    if (req.method !== "POST") {
      res.status(405).json({ error: "Method Not Allowed" });
      return;
    }

    const workflow_id = process.env.OPENAI_WORKFLOW_ID;
    if (!workflow_id) {
      res.status(500).json({ error: "Missing OPENAI_WORKFLOW_ID" });
      return;
    }

    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) {
      res.status(500).json({ error: "Missing OPENAI_API_KEY" });
      return;
    }

    // Create short-lived client secret via Realtime Sessions
    const resp = await fetch("https://api.openai.com/v1/realtime/sessions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
        // "OpenAI-Organization": process.env.OPENAI_ORG_ID ?? "",
        // "OpenAI-Project": process.env.OPENAI_PROJECT_ID ?? "",
      },
      body: JSON.stringify({ workflow_id }),
    });

    if (!resp.ok) {
      const text = await resp.text().catch(() => "");
      res
        .status(resp.status)
        .json({ error: "OpenAI session create failed", detail: text });
      return;
    }

    const data: any = await resp.json();
    const value =
      (typeof data?.client_secret === "object"
        ? data?.client_secret?.value
        : data?.client_secret) ?? null;

    res.status(200).json({ client_secret: { value } });
  } catch (err: any) {
    res.status(500).json({
      error: "Server error creating ChatKit session",
      detail: err?.message ?? String(err),
    });
  }
}