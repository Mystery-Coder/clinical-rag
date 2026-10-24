import { fetchFromApi } from "@/lib/api";
import { NextRequest } from "next/server";

export async function GET() {
  return fetchFromApi("/patients");
}
