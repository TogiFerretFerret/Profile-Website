// front door for sites that double as `curl site | bash` scripts (www -> /riverxia.sh, dots -> /dots.sh; env.SCRIPT picks which).
// only "/" runs through this worker (run_worker_first: ["/"]); everything else is a plain static asset.
//   curl/wget <site> -> the script itself: `curl -s riverxia.sh | bash`, or `wget riverxia.sh; bash index.html`
//                       (wget names the file after the URL you typed, so it is always index.html; no redirect can change that)
//   browsers         -> the normal page
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const ua = request.headers.get("user-agent") || "";
    if (url.pathname === "/" && request.method === "GET" && /^(curl\/|wget|gnu wget)/i.test(ua)) {
      const r = await env.ASSETS.fetch(new Request(new URL(env.SCRIPT, url), request));
      return new Response(r.body, { status: r.status, headers: { "content-type": "text/x-shellscript; charset=utf-8", vary: "user-agent", "cache-control": "no-store" } });
    }
    const r = await env.ASSETS.fetch(request);
    if (url.pathname === "/") { const h = new Headers(r.headers); h.append("vary", "user-agent"); return new Response(r.body, { status: r.status, headers: h }); }
    return r;
  },
};
