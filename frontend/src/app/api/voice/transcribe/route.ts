import { NextRequest, NextResponse } from "next/server";
import { API_BASE } from "@/lib/api";

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();
    const forwardHeaders: Record<string, string> = {};
    const mockHeader = req.headers.get("X-Mock-Transcription");
    if (mockHeader) {
      forwardHeaders["X-Mock-Transcription"] = mockHeader;
    }

    const res = await fetch(`${API_BASE}/voice/transcribe`, {
      method: "POST",
      headers: forwardHeaders,
      body: formData,
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error: any) {
    return NextResponse.json({ detail: error.message || "Transcription proxy failed" }, { status: 500 });
  }
}
