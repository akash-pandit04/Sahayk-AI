import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { API_BASE } from "@/lib/api";

export async function POST(req: NextRequest) {
  try {
    const token = cookies().get("admin_token")?.value;
    if (!token) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const contentType = req.headers.get("content-type") || "";
    let res: Response;

    if (contentType.includes("multipart/form-data")) {
      const incoming = await req.formData();
      const endpoint = incoming.get("endpoint");
      if (typeof endpoint !== "string" || !endpoint.startsWith("/")) {
        return NextResponse.json({ error: "Invalid endpoint" }, { status: 400 });
      }
      const forwardForm = new FormData();
      incoming.forEach((value, key) => {
        if (key !== "endpoint") {
          forwardForm.append(key, value);
        }
      });

      res = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: forwardForm,
      });
    } else {
      const { endpoint, method = "GET", body } = await req.json();

      res = await fetch(`${API_BASE}${endpoint}`, {
        method,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: body ? JSON.stringify(body) : undefined,
      });
    }

    const data = await res.json();

    if (!res.ok) {
      return NextResponse.json({ error: data.detail || data.error?.message || "Error" }, { status: res.status });
    }

    return NextResponse.json(data);
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
