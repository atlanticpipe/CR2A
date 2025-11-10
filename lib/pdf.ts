import { PDFDocument, StandardFonts, rgb } from "pdf-lib";

export async function buildResultPdf(inputName: string, extractedSummary: string) {
  const pdf = await PDFDocument.create();
  const page = pdf.addPage([612, 792]);
  const font = await page.doc.embedFont(StandardFonts.Helvetica);

  page.drawText("Workflow Results", { x: 50, y: 740, size: 20, font, color: rgb(0,0,0) });
  page.drawText(`Source file: ${inputName}`, { x: 50, y: 715, size: 10, font });
  page.drawText("Summary:", { x: 50, y: 680, size: 12, font });

  const text = extractedSummary || "No details provided.";
  const maxWidth = 500;
  const words = text.split(/\s+/);
  let y = 660, line = "";
  for (const w of words) {
    const next = line ? `${line} ${w}` : w;
    if (font.widthOfTextAtSize(next, 11) > maxWidth) {
      page.drawText(line, { x: 50, y, size: 11, font });
      y -= 14; line = w;
    } else line = next;
  }
  if (line) page.drawText(line, { x: 50, y, size: 11, font });

  const bytes = await pdf.save();
  return Buffer.from(bytes);
}