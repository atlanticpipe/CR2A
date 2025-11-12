export default async function handler(req: any, res: any) {
  try {
    if (req.method !== "POST") {
      res.status(405).json({ error: "Method Not Allowed" });
      return;
    }

    const workflow_id =
      process.env.VITE_CHATKIT_WORKFLOW_ID || process.env.OPENAI_WORKFLOW_ID;
    if (!workflow_id) {
      res.status(500).json({ error: "Missing workflow id" });
      return;
    }
    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) {
      res.status(500).json({ error: "Missing OPENAI_API_KEY" });
      return;
    }

    // Call the REST endpoint directly
    const r = await fetch("https://api.openai.com/v1/chatkit/sessions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
        // If you need to pin org/project, uncomment:
        // "OpenAI-Organization": process.env.OPENAI_ORG_ID ?? "",
        // "OpenAI-Project": process.env.OPENAI_PROJECT_ID ?? "",
      },
      body: JSON.stringify({ workflow_id }),
    });

    // Bubble up any non-200s as readable JSON
    if (!r.ok) {
      const text = await r.text().catch(() => "");
      res
        .status(r.status)
        .json({ error: "OpenAI session create failed", detail: text });
      return;
    }

    const json = await r.json(); // { client_secret: { value: "..." , ...}, ... }
    // Return only what the widget needs
    res.status(200).json({ client_secret: json.client_secret?.value ?? null });
  } catch (err: any) {
    res.status(500).json({
      error: "Server error creating ChatKit session",
      detail: err?.message ?? String(err),
    });
  }
}