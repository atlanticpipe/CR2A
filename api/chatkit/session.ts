export default async function handler(req: any, res: any) {
  try {
    if (req.method !== "POST") {
      res.status(405).json({ error: "Method Not Allowed" });
      return;
    }

    // Use server envs only
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

    // Correct endpoint: Realtime Sessions
    const r = await fetch("https://api.openai.com/v1/realtime/sessions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
        // "OpenAI-Organization": process.env.OPENAI_ORG_ID ?? "",
        // "OpenAI-Project": process.env.OPENAI_PROJECT_ID ?? "",
      },
      body: JSON.stringify({ workflow_id }),
    });

    if (!r.ok) {
      const text = await r.text().catch(() => "");
      res.status(r.status).json({ error: "OpenAI session create failed", detail: text });
      return;
    }

    const json = await r.json(); // { client_secret: { value: "..." }, ... }
    res.status(200).json({ client_secret: json.client_secret?.value ?? null });
  } catch (err: any) {
    res.status(500).json({
      error: "Server error creating ChatKit session",
      detail: err?.message ?? String(err),
    });
  }
}