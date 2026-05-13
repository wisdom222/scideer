import { NextResponse, type NextRequest } from "next/server";

export function middleware(req: NextRequest) {
  const { pathname, search } = req.nextUrl;
  if (pathname === "/zh" || pathname.startsWith("/zh/")) {
    const target = pathname.replace(/^\/zh(\/|$)/, "/en$1") + search;
    return NextResponse.redirect(new URL(target, req.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/zh", "/zh/:path*"],
};
