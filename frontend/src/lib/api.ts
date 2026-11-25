export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export async function fetchAPI(endpoint: string, options: RequestInit = {}) {
  // In App router server components, we might pass the token explicitly.
  // We'll manage this through cookies so next.js can read them.
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as any) || {}),
  };

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let message = "An error occurred";
    try {
      const data = await res.json();
      message = data.error?.message || data.detail || message;
    } catch (e) {}
    throw new Error(message);
  }

  // Handle 204 or empty
  if (res.status === 204) return null;
  
  const text = await res.text();
  if (!text) return null;
  return JSON.parse(text);
}
