import { NextResponse } from "next/server";
import { getWorkflowId } from "@/lib/config";

export function GET(): NextResponse {
  try {
    const id = getWorkflowId();
    return NextResponse.json({ status: "ok", workflowIdTail: id.slice(-6) });
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Workflow not configured";
    return NextResponse.json({ status: "error", message }, { status: 500 });
  }
}