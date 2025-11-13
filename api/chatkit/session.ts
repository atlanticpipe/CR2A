export default async function handler(req: any, res: any) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    res.statusCode = 405;
    return res.end('Method Not Allowed');
  }

  try {
    const { OPENAI_WORKFLOW_ID, OPENAI_API_KEY } = process.env;
    if (!OPENAI_WORKFLOW_ID || !OPENAI_API_KEY) {
      res.statusCode = 500;
      return res.end('Server misconfigured');
    }

    // ... your existing session creation logic ...

    res.statusCode = 200;
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({ client_secret: { value: /* token */ '' } }));
  } catch (err: any) {
    res.statusCode = 500;
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({ error: err?.message || 'Internal error' }));
  }
}