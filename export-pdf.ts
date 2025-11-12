import { PDFDocument, StandardFonts } from "pdf-lib";

/** Payload contract */
export type Payload = { content: string; title?: string; filename?: string };

/** Core: pure PDF generator (no Node/req/res) */
export async function generatePdf(payload: Payload): Promise<Uint8Array> {
  const { content, title } = payload;

  const pdf = await PDFDocument.create();
  const pageMargin = 36; // ~0.5"
  let page = pdf.addPage();
  const font = await pdf.embedFont(StandardFonts.Helvetica);
  const bold = await pdf.embedFont(StandardFonts.HelveticaBold);
  const fontSize = 11;
  const lineHeight = fontSize + 4;

  let { width, height } = page.getSize();
  let y = height - pageMargin;

  const header = title?.trim() || "CR2A Results";
  page.drawText(header, { x: pageMargin, y, size: 14, font: bold });
  y -= 26;

  // Simple text wrapping tuned by average character width
  const maxWidth = width - pageMargin * 2;
  const avgCharW =
    font.widthOfTextAtSize("ABCDEFGHIJKLMNOPQRSTUVWXYZ", fontSize) / 26;
  const maxChars = Math.max(20, Math.floor(maxWidth / avgCharW));

  const putLine = (text: string) => {
    if (y < pageMargin + lineHeight) {
      page = pdf.addPage();
      ({ width, height } = page.getSize());
      y = height - pageMargin;
    }
    page.drawText(text, { x: pageMargin, y, size: fontSize, font });
    y -= lineHeight;
  };

  const addParagraph = (para: string) => {
    let i = 0;
    while (i < para.length) {
      const slice = para.slice(i, i + maxChars);
      let brk = slice.lastIndexOf(" ");
      if (brk === -1) brk = slice.length;
      putLine(slice.slice(0, brk));
      i += brk;
      while (para[i] === " ") i++; // skip extra spaces
    }
    y -= 4; // paragraph spacing
  };

  String(content)
    .replace(/\r\n/g, "\n")
    .split("\n")
    .forEach((line) => {
      if (line.trim() === "") {
        y -= lineHeight; // blank line -> vertical space
      } else {
        addParagraph(line);
      }
    });

  return pdf.save(); // Uint8Array
}

/** Safe filename builder (server + browser) */
function sanitizeFilename(name: string | undefined): string {
  const base = (name && name.trim()) || "CR2A";
  const cleaned = base.replace(/\s+/g, "-").replace(/[^A-Za-z0-9._-]/g, "");
  return `${cleaned || "document"}.pdf`;
}

/**
 * Server adapter (Vercel/Node-like). No external types to keep this file portable.
 * `req`/`res` are intentionally `any` to avoid bringing in Node typings.
 */
export default async function handler(req: any, res: any) {
  if (req?.method !== "POST") {
    res?.setHeader?.("Allow", "POST");
    return res?.status?.(405)?.send?.("Method Not Allowed");
  }

  let body: Partial<Payload> = {};
  try {
    body =
      typeof req.body === "string" ? JSON.parse(req.body) : (req.body ?? {});
  } catch {
    return res.status(400).send("Invalid JSON body");
  }

  if (!body || typeof body.content !== "string" || body.content.trim() === "") {
    return res.status(400).send("Missing required field: content");
  }

  try {
    const bytes = await generatePdf({
      content: body.content,
      title: body.title,
      filename: body.filename,
    });

    const filename = sanitizeFilename(body.filename);
    res.setHeader("Content-Type", "application/pdf");
    res.setHeader(
      "Content-Disposition",
      `attachment; filename="${filename}"`
    );
    res.setHeader("Cache-Control", "no-store");

    // Avoid Buffer to keep Node typings optional; most frameworks accept Uint8Array.
    return res.status(200).send(bytes as unknown as any);
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error("export-pdf error:", err);
    return res.status(500).send("Failed to generate PDF");
  }
}