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

    const res = await fetch(`${API_BASE}/voice/turn`, {
      method: "POST",
      headers: forwardHeaders,
      body: formData,
    });

    const text = await res.text();
    try {
      const data = JSON.parse(text);
      return NextResponse.json(data, { status: res.status });
    } catch {
      return NextResponse.json({ detail: text || "Upstream error" }, { status: res.status });
    }
  } catch (error: any) {
    return NextResponse.json({ detail: error.message || "Voice turn proxy failed" }, { status: 500 });
  }
}
