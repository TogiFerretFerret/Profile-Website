// riverxia.sh front door. only "/" runs through this worker (run_worker_first: ["/"]); everything else is a plain static asset.
//   curl/wget riverxia.sh -> the script itself: `curl -s riverxia.sh | bash`, or `wget riverxia.sh; bash index.html`
//                            (wget names the file after the URL you typed, so it is always index.html; no redirect can change that)
//   browsers              -> the normal homepage
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const ua = request.headers.get("user-agent") || "";
    if (url.pathname === "/" && request.method === "GET") {
      if (/^(curl\/|wget|gnu wget)/i.test(ua)) {
        const r = await env.ASSETS.fetch(new Request(new URL("/riverxia.sh", url), request));
        return new Response(r.body, { status: r.status, headers: { "content-type": "text/x-shellscript; charset=utf-8", vary: "user-agent", "cache-control": "no-store" } });
      }
    }
    const r = await env.ASSETS.fetch(request);
    if (url.pathname === "/") { const h = new Headers(r.headers); h.append("vary", "user-agent"); return new Response(r.body, { status: r.status, headers: h }); }
    return r;
  },
};
