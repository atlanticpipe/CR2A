const SESSIONS_URL =
  process.env.OPENAI_SESSIONS_URL?.trim() ||
  // If your account uses the Realtime Sessions API instead, set OPENAI_SESSIONS_URL to that.
  "https://api.openai.com/v1/chat/sessions";

export default async function handler(req: any, res: any) {
  try {
    if (req.method !== "POST") {
      res.setHeader("Allow", "POST");
      res.statusCode = 405;
      return res.end("Method Not Allowed");
    }

    const apiKey = process.env.OPENAI_API_KEY?.trim();
    const workflow = process.env.OPENAI_WORKFLOW_ID?.trim();

    if (!apiKey) {
      res.statusCode = 500;
      return res.end("Server misconfigured: missing OPENAI_API_KEY");
    }
    if (!workflow) {
      res.statusCode = 500;
      return res.end("Server misconfigured: missing OPENAI_WORKFLOW_ID");
    }

    // Build the request body: use the server’s workflow, not the client’s.
    const body = { workflow };

    const resp = await fetch(SESSIONS_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
        // Include Assistants v2; add workflows beta to be explicit.
        "OpenAI-Beta": "assistants=v2,workflows=v1",
      },
      body: JSON.stringify(body),
    });

    const text = await resp.text();
    if (!resp.ok) {
      // Bubble a concise error + detail for debugging in Network tab
      res.statusCode = resp.status;
      return res.end(
        JSON.stringify({
          error: "OpenAI session create failed",
          detail: text,
        })
      );
    }

    const data = JSON.parse(text);

    // Normalize the shape the widget expects
    const clientSecretValue =
      data?.client_secret?.value ?? data?.client_secret ?? null;

    res.setHeader("Content-Type", "application/json");
    res.statusCode = 200;
    return res.end(JSON.stringify({ client_secret: { value: clientSecretValue } }));
  } catch (err: any) {
    res.statusCode = 500;
    return res.end(
      JSON.stringify({
        error: "Server error creating ChatKit session",
        detail: err?.message ?? String(err),
      })
    );
  }
}