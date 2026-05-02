import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PUBLIC_PATHS = ["/", "/login", "/register", "/_next", "/favicon", "/manifest.json", "/icons"];
const DOCTOR_PREFIX = "/dashboard/doctor";
const PATIENT_PREFIX = "/dashboard/patient";

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // Always allow public paths
  if (PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(p + "/"))) {
    return NextResponse.next();
  }

  const required = process.env.NEXT_PUBLIC_AUTH_REQUIRED === "true";
  const token = req.cookies.get("medverse_token")?.value;
  const role = req.cookies.get("aegis_role")?.value; // "doctor" | "patient" | "admin"

  // Not authenticated → go to login
  if (required && !token) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  // Role-based guards (only enforced when auth is on and role cookie is present)
  if (token && role) {
    if (pathname.startsWith(PATIENT_PREFIX) && role !== "patient" && role !== "admin") {
      const url = req.nextUrl.clone();
      url.pathname = role === "doctor" ? DOCTOR_PREFIX : "/login";
      return NextResponse.redirect(url);
    }
    if (pathname.startsWith(DOCTOR_PREFIX) && role !== "doctor" && role !== "admin") {
      const url = req.nextUrl.clone();
      url.pathname = role === "patient" ? PATIENT_PREFIX : "/login";
      return NextResponse.redirect(url);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
