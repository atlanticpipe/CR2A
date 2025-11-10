import { NextResponse } from "next/server";
import { buildResultPdf } from "@/lib/pdf";

export const runtime = "nodejs";

export async function POST(req: Request) {
  try {
    const form = await req.formData();
    const file = form.get("file") as File | null;
    const approved = (form.get("approved") as string) === "true";

    if (!file) return NextResponse.json({ error: "No file" }, { status: 400 });
    if (!approved) return NextResponse.json({ error: "Not approved" }, { status: 400 });

    let extracted = "";
    if (file.type.startsWith("text/")) {
      extracted = (await file.text()).slice(0, 3000);
    } else {
      extracted = `Received ${file.name} (${file.type || "unknown type"})`;
    }

    const pdf = await buildResultPdf(file.name, extracted);

    return new NextResponse(pdf, {
      status: 200,
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `attachment; filename="results.pdf"`,
        "Cache-Control": "no-store",
      },
    });
  } catch (e) {
    console.error(e);
    return NextResponse.json({ error: "Server error" }, { status: 500 });
  }
}