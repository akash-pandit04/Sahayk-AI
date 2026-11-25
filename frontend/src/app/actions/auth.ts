"use server";

import { cookies } from "next/headers";
import { API_BASE } from "@/lib/api";
import { redirect } from "next/navigation";

export async function login(prevState: any, formData: FormData) {
  const email = formData.get("email") as string;
  const password = formData.get("password") as string;

  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ username: email, password }),
    });

    if (!res.ok) {
      const data = await res.json();
      return { error: data.detail || "Invalid login credentials" };
    }

    const data = await res.json();
    const token = data.access_token;
    
    cookies().set("admin_token", token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: 60 * 60 * 24 * 7, // 1 week
      path: "/",
    });
    
  } catch (error: any) {
    return { error: error.message || "Failed to connect to server" };
  }

  redirect("/admin");
}

export async function logout() {
  cookies().delete("admin_token");
  redirect("/admin/login");
}

export async function getToken() {
  return cookies().get("admin_token")?.value;
}
