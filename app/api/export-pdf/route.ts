import { PDFDocument, StandardFonts } from "pdf-lib";
import type { NextRequest } from "next/server";

export const runtime = "nodejs";

type Payload = { content: string; title?: string; filename?: string };

export async function POST(req: NextRequest) {
  try {
    const body = (await req.json()) as Partial<Payload> | null;
    if (!body || typeof body.content !== "string" || body.content.trim() === "") {
      return Response.json(
        { type: "ValidationError", message: 'Missing "content" (string).' },
        { status: 422 }
      );
    }

    const safeFilename = `${(body.filename || "CR2A").replace(/[^-\w]/g, "")}.pdf`;

    // --- Build a simple PDF ---
    const pdf = await PDFDocument.create();
    const pageMargin = 36;
    const page = pdf.addPage();
    const font = await pdf.embedFont(StandardFonts.Helvetica);
    const bold = await pdf.embedFont(StandardFonts.HelveticaBold);
    const fontSize = 11;
    const lineHeight = fontSize + 4;

    let { width, height } = page.getSize();
    let y = height - pageMargin;

    const title = body.title || "CR2A Results";
    page.drawText(title, { x: pageMargin, y, size: 14, font: bold });
    y -= 26;

    const maxWidth = width - pageMargin * 2;
    const avgCharW = font.widthOfTextAtSize("ABCDEFGHIJKLMNOPQRSTUVWXYZ", fontSize) / 26;
    const maxChars = Math.max(20, Math.floor(maxWidth / avgCharW));

    const putLine = (text: string) => {
      if (y < pageMargin + lineHeight) {
        const p = pdf.addPage();
        ({ width, height } = p.getSize());
        y = height - pageMargin;
        p.drawText(text, { x: pageMargin, y, size: fontSize, font });
        y -= lineHeight;
        return;
      }
      page.drawText(text, { x: pageMargin, y, size: fontSize, font });
      y -= lineHeight;
    };

    for (const para of body.content.replace(/\r\n/g, "\n").split("\n")) {
      let i = 0;
      while (i < para.length) {
        const slice = para.slice(i, i + maxChars);
        let brk = slice.lastIndexOf(" ");
        if (brk === -1) brk = slice.length;
        putLine(slice.slice(0, brk));
        i += brk;
        while (para[i] === " ") i++;
      }
      y -= 4;
    }

    // --- This line is required before you construct the Blob/ArrayBuffer ---
    const bytes: Uint8Array = await pdf.save();

    const ab: ArrayBuffer = (bytes.buffer as ArrayBuffer).slice(
    bytes.byteOffset,
    bytes.byteOffset + bytes.byteLength
    );

    return new Response(ab, {
    status: 200,
    headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `attachment; filename="${safeFilename}"`,
        "Cache-Control": "no-store",
    },
    });
  } catch {
    return Response.json(
      { type: "ProcessingError", message: "Failed to generate PDF." },
      { status: 500 }
    );
  }
}