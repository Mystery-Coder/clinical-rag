import { fetchFromApi } from "@/lib/api";
import { NextRequest } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    return fetchFromApi("/consult", {
      method: "POST",
      body: JSON.stringify(body),
      timeoutMs: 180000,
    });
  } catch (err: any) {
    return new Response(JSON.stringify({ detail: err?.message || "Invalid request" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }
}
