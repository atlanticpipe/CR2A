import { NextResponse } from "next/server";
import { getWorkflowId } from "@/lib/config";

export function GET() {
  try {
    const id = getWorkflowId();
    return NextResponse.json({ status: "ok", workflowIdTail: id.slice(-6) });
  } catch (e: any) {
    return NextResponse.json(
      { status: "error", message: e.message ?? "Workflow not configured" },
      { status: 500 }
    );
  }
}