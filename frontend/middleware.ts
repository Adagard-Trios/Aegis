import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Auth gate. Activates when NEXT_PUBLIC_AUTH_REQUIRED=true. Reads the
// medverse_token cookie set by the login flow (mirror of localStorage)
// to gate page renders. The actual API enforcement happens server-side
// via MEDVERSE_AUTH_ENABLED + JWT bearer tokens.
const PUBLIC_PATHS = ["/login", "/_next", "/favicon", "/manifest.json", "/icons"];

export function middleware(req: NextRequest) {
  const required = process.env.NEXT_PUBLIC_AUTH_REQUIRED === "true";
  if (!required) return NextResponse.next();

  const { pathname } = req.nextUrl;
  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  const token = req.cookies.get("medverse_token")?.value;
  if (!token) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
