import { NextRequest, NextResponse } from "next/server";
import { API_BASE } from "@/lib/api";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const res = await fetch(`${API_BASE}/voice/synthesize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({ detail: "Synthesis failed" }));
      return NextResponse.json(errData, { status: res.status });
    }

    const audioBuffer = await res.arrayBuffer();
    return new NextResponse(audioBuffer, {
      status: 200,
      headers: {
        "Content-Type": res.headers.get("Content-Type") || "audio/wav",
      },
    });
  } catch (error: any) {
    return NextResponse.json({ detail: error.message || "Synthesis proxy failed" }, { status: 500 });
  }
}
