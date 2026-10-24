import { NextResponse } from "next/server";

const API_BASE = process.env.CDSS_API_URL || "http://127.0.0.1:8000";

export async function fetchFromApi(path: string, init?: RequestInit & { timeoutMs?: number }) {
  const timeoutMs = init?.timeoutMs ?? 180000;
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers || {}),
      },
    });

    const text = await res.text();
    let data: any = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = text;
    }

    if (!res.ok) {
      return NextResponse.json({ detail: data?.detail || data || res.statusText }, { status: res.status });
    }

    return NextResponse.json(data, { status: res.status });
  } catch (err: any) {
    if (err?.name === "AbortError") {
      return NextResponse.json({ detail: "Request timed out" }, { status: 504 });
    }
    return NextResponse.json({ detail: err?.message || "Upstream error" }, { status: 502 });
  } finally {
    clearTimeout(id);
  }
}
