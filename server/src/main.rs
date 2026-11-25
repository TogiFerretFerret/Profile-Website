use axum::{
    extract::{Path as AxumPath, Query, State},
    http::{header, HeaderMap, HeaderValue, StatusCode},
    response::{IntoResponse, Response},
    routing::{get, post},
    Router,
};
use mime_guess::from_path;
use rand::{distr::Alphanumeric, Rng};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{
    collections::HashMap,
    net::SocketAddr,
    path::{Path, PathBuf},
    sync::{Arc, Mutex},
    time::{SystemTime, UNIX_EPOCH},
};
use tower_http::cors::CorsLayer;

const MAX_PASTE: usize = 256 * 1024;
const LIMIT_PASTE: i64 = 30;
const LIMIT_GB_PER_HOUR: i64 = 3;
const LIMIT_GB_GLOBAL_HOUR: i64 = 100;
const LIMIT_GB_GAP_SECS: i64 = 30;
const RESERVED_NAMES: &[&str] = &["rivercodes", "riverc", "riverxia", "admin", "owner"];

#[derive(Clone)]
struct AppState {
    dist_dir: PathBuf,
    db: Arc<Mutex<Connection>>,
    local: bool, // true when LOCAL=1 env var is set (dev mode: use subpath routing)
}

fn now_millis() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis() as i64
}

fn now_secs() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs() as i64
}

fn sha256_hex(val: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(val.as_bytes());
    format!("{:x}", hasher.finalize())
}

fn random_id(len: usize) -> String {
    rand::rng()
        .sample_iter(&Alphanumeric)
        .take(len)
        .map(|c| c.to_ascii_lowercase() as char)
        .collect()
}

fn escape_html(s: &str) -> String {
    s.replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
        .replace('\'', "&#39;")
}

fn get_client_ip(headers: &HeaderMap) -> String {
    if let Some(val) = headers.get("cf-connecting-ip").or_else(|| headers.get("x-forwarded-for")) {
        if let Ok(s) = val.to_str() {
            return s.split(',').next().unwrap_or("?").trim().to_string();
        }
    }
    "?".to_string()
}

fn is_cli_request(headers: &HeaderMap) -> bool {
    let ua = headers
        .get(header::USER_AGENT)
        .and_then(|v| v.to_str().ok())
        .unwrap_or("")
        .to_lowercase();
    let accept = headers
        .get(header::ACCEPT)
        .and_then(|v| v.to_str().ok())
        .unwrap_or("")
        .to_lowercase();
    ua.starts_with("curl") || ua.starts_with("wget") || ua.contains("gnu wget") || accept.starts_with("text/plain")
}

fn wants_html(headers: &HeaderMap) -> bool {
    headers
        .get(header::ACCEPT)
        .and_then(|v| v.to_str().ok())
        .map(|v| v.contains("text/html"))
        .unwrap_or(false)
}

fn get_ttl_secs(key: &str) -> Option<i64> {
    match key {
        "1h" => Some(3600),
        "1d" => Some(86400),
        "7d" => Some(604800),
        "30d" => Some(2592000),
        _ => None,
    }
}

fn page(title: &str, body: &str, local: bool) -> Response {
    let home_href = if local { "/www/" } else { "https://riverxia.sh" };
    let html = format!(
        r#"<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>{}</title><link rel="stylesheet" href="/style.css"></head><body><main style="max-width:60rem;margin:0 auto"><div class="logo"><a href="{}">riverxia<span>.sh</span></a></div>{}</main></body></html>"#,
        escape_html(title),
        home_href,
        body
    );
    (
        StatusCode::OK,
        [
            (header::CONTENT_TYPE, "text/html; charset=utf-8"),
            (header::CACHE_CONTROL, "no-store"),
            (HeaderName::from_static("x-robots-tag"), "noindex"),
            (HeaderName::from_static("content-security-policy"), "default-src 'none'; style-src 'self'; form-action 'self'"),
        ],
        html,
    )
        .into_response()
}

use axum::http::header::HeaderName;

fn text_response(status: StatusCode, s: String, extra_headers: Vec<(&'static str, String)>) -> Response {
    let mut resp = (status, s).into_response();
    let h = resp.headers_mut();
    h.insert(header::CONTENT_TYPE, HeaderValue::from_static("text/plain; charset=utf-8"));
    h.insert(header::CACHE_CONTROL, HeaderValue::from_static("no-store"));
    h.insert(HeaderName::from_static("x-content-type-options"), HeaderValue::from_static("nosniff"));
    h.insert(HeaderName::from_static("content-security-policy"), HeaderValue::from_static("sandbox; default-src 'none'"));
    for (k, v) in extra_headers {
        if let Ok(val) = HeaderValue::from_str(&v) {
            h.insert(HeaderName::from_static(k), val);
        }
    }
    resp
}

fn init_db(db_path: &Path) -> Connection {
    if let Some(parent) = db_path.parent() {
        std::fs::create_dir_all(parent).ok();
    }
    let conn = Connection::open(db_path).expect("failed to open sqlite database");
    conn.execute_batch(
        r#"
        CREATE TABLE IF NOT EXISTS pastes (
            id TEXT PRIMARY KEY,
            body TEXT NOT NULL,
            d TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            t INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS paste_hits (
            ip TEXT NOT NULL,
            t INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS guestbook_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            message TEXT NOT NULL,
            website TEXT,
            t INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS guestbook_hits (
            h TEXT NOT NULL,
            t INTEGER NOT NULL
        );
        "#,
    )
    .expect("failed to initialize sqlite schema");
    conn
}

// Static asset server with multi-subdomain and fallback logic
async fn serve_static_or_dynamic(
    State(state): State<AppState>,
    headers: HeaderMap,
    AxumPath(path): AxumPath<String>,
) -> Response {
    let host = headers
        .get(header::HOST)
        .and_then(|v| v.to_str().ok())
        .unwrap_or("")
        .to_lowercase();
    let clean_path = path.trim_start_matches('/');

    // Handle subdomain routing
    let (sub, file_req) = if host.starts_with("paste.") {
        ("paste", clean_path)
    } else if host.starts_with("guestbook.") {
        ("guestbook", clean_path)
    } else if host.starts_with("blog.") {
        ("blog", clean_path)
    } else if host.starts_with("projects.") {
        ("projects", clean_path)
    } else if host.starts_with("uses.") {
        ("uses", clean_path)
    } else if host.starts_with("dots.") {
        ("dots", clean_path)
    } else {
        // Path-based: e.g. /www/..., /blog/..., /paste/..., or top-level /
        if let Some((first, rest)) = clean_path.split_once('/') {
            if matches!(first, "www" | "blog" | "projects" | "uses" | "dots" | "paste" | "guestbook") {
                (first, rest)
            } else {
                ("www", clean_path)
            }
        } else if matches!(clean_path, "www" | "blog" | "projects" | "uses" | "dots" | "paste" | "guestbook") {
            (clean_path, "")
        } else {
            ("www", clean_path)
        }
    };

    // Front script responder for curl/wget on www or dots or guestbook terminal
    if is_cli_request(&headers) && file_req.is_empty() {
        if sub == "guestbook" {
            return handle_guestbook_terminal(State(state), headers).await;
        } else if sub == "dots" {
            let script = state.dist_dir.join("dots").join("dots.sh");
            if let Ok(bytes) = tokio::fs::read(script).await {
                return (StatusCode::OK, [(header::CONTENT_TYPE, "text/plain; charset=utf-8")], bytes).into_response();
            }
        } else if sub == "www" {
            let script = state.dist_dir.join("www").join("riverxia.sh");
            if let Ok(bytes) = tokio::fs::read(script).await {
                return (StatusCode::OK, [(header::CONTENT_TYPE, "text/plain; charset=utf-8")], bytes).into_response();
            }
        }
    }

    // Try serving file
    let sub_dir = state.dist_dir.join(sub);
    let target = if file_req.is_empty() {
        sub_dir.join("index.html")
    } else {
        sub_dir.join(file_req)
    };

    if target.is_file() {
        return serve_file(&target).await;
    }

    // Try target + .html
    let html_target = sub_dir.join(format!("{}.html", file_req));
    if html_target.is_file() {
        return serve_file(&html_target).await;
    }

    // Root shared assets like style.css or button
    let root_asset = state.dist_dir.join(clean_path);
    if root_asset.is_file() {
        return serve_file(&root_asset).await;
    }

    // 404 fallback
    let not_found_page = sub_dir.join("404.html");
    if not_found_page.is_file() {
        if let Ok(content) = tokio::fs::read(not_found_page).await {
            return (StatusCode::NOT_FOUND, [(header::CONTENT_TYPE, "text/html; charset=utf-8")], content).into_response();
        }
    }

    (StatusCode::NOT_FOUND, "not found\n").into_response()
}

async fn serve_file(path: &Path) -> Response {
    match tokio::fs::read(path).await {
        Ok(bytes) => {
            let mime = from_path(path).first_or_octet_stream();
            (
                StatusCode::OK,
                [(header::CONTENT_TYPE, mime.as_ref())],
                bytes,
            )
                .into_response()
        }
        Err(_) => (StatusCode::NOT_FOUND, "not found\n").into_response(),
    }
}

// Paste Handler: Create
async fn handle_paste_create(
    State(state): State<AppState>,
    headers: HeaderMap,
    Query(params): Query<HashMap<String, String>>,
    body_bytes: axum::body::Bytes,
) -> Response {
    let ip = get_client_ip(&headers);
    let now = now_millis();
    let now_s = now / 1000;

    // Rate limit check
    {
        let conn = state.db.lock().unwrap();
        conn.execute("DELETE FROM paste_hits WHERE t < ?", params![now - 3600 * 1000]).ok();
        conn.execute("DELETE FROM pastes WHERE expires_at < ?", params![now_s]).ok();
        let hits: i64 = conn
            .query_row("SELECT COUNT(*) FROM paste_hits WHERE ip = ?", params![ip], |r| r.get(0))
            .unwrap_or(0);
        if hits >= LIMIT_PASTE {
            return text_response(StatusCode::TOO_MANY_REQUESTS, "slow down: 30 pastes/hour\n".into(), vec![]);
        }
    }

    if body_bytes.len() > MAX_PASTE + 4096 {
        return text_response(StatusCode::PAYLOAD_TOO_LARGE, "too big (256 KiB max)\n".into(), vec![]);
    }

    let ct = headers
        .get(header::CONTENT_TYPE)
        .and_then(|v| v.to_str().ok())
        .unwrap_or("");
    let mut paste_text = String::new();
    let mut form_ttl: Option<String> = None;

    if ct.contains("application/x-www-form-urlencoded") {
        if let Ok(parsed) = serde_urlencoded::from_bytes::<HashMap<String, String>>(&body_bytes) {
            if let Some(t) = parsed.get("c").or_else(|| parsed.get("content")).or_else(|| parsed.get("text")) {
                paste_text = t.clone();
                form_ttl = parsed.get("ttl").cloned();
            }
        }
    } else {
        match String::from_utf8(body_bytes.to_vec()) {
            Ok(s) => paste_text = s,
            Err(_) => return text_response(StatusCode::UNSUPPORTED_MEDIA_TYPE, "text only\n".into(), vec![]),
        }
    }

    if paste_text.contains('\0') {
        return text_response(StatusCode::UNSUPPORTED_MEDIA_TYPE, "text only\n".into(), vec![]);
    }
    if paste_text.trim().is_empty() {
        return text_response(StatusCode::BAD_REQUEST, "empty paste\n".into(), vec![]);
    }
    if paste_text.len() > MAX_PASTE {
        return text_response(StatusCode::PAYLOAD_TOO_LARGE, "too big (256 KiB max)\n".into(), vec![]);
    }

    let ttl_key = params
        .get("ttl")
        .cloned()
        .or_else(|| headers.get("x-ttl").and_then(|v| v.to_str().ok()).map(String::from))
        .or(form_ttl)
        .unwrap_or_else(|| "7d".to_string());

    let secs = match get_ttl_secs(&ttl_key) {
        Some(s) => s,
        None => return text_response(StatusCode::BAD_REQUEST, "ttl must be one of 1h 1d 7d 30d\n".into(), vec![]),
    };

    let id = random_id(8);
    let token = random_id(24);
    let expires_at = now_s + secs;
    let d = sha256_hex(&token);

    {
        let conn = state.db.lock().unwrap();
        conn.execute("INSERT INTO paste_hits (ip, t) VALUES (?, ?)", params![ip, now]).ok();
        conn.execute(
            "INSERT INTO pastes (id, body, d, expires_at, t) VALUES (?, ?, ?, ?, ?)",
            params![id, paste_text, d, expires_at, now],
        )
        .expect("insert paste failed");
    }

    let link = if state.local {
        let host = headers
            .get(header::HOST)
            .and_then(|v| v.to_str().ok())
            .unwrap_or("localhost");
        format!("http://{}/paste/{}", host, id)
    } else {
        format!("https://paste.riverxia.sh/{}", id)
    };

    if wants_html(&headers) {
        let body = format!(
            r#"<h1>pasted!</h1><section class="box"><p><a href="{0}">{0}</a> <span class="dim">(expires in {1})</span></p>
<p class="dim">delete it with:</p><pre class="wrap"><code>curl -X DELETE -H 'x-delete-token: {2}' {0}</code></pre><p class="dim">that token is shown once.</p></section>"#,
            link, escape_html(&ttl_key), token
        );
        return page("pasted", &body, state.local);
    }

    text_response(StatusCode::CREATED, format!("{}\n", link), vec![("x-delete-token", token)])
}

// Paste Handler: Get raw / html
async fn handle_paste_get(
    State(state): State<AppState>,
    headers: HeaderMap,
    AxumPath(path): AxumPath<String>,
) -> Response {
    let clean = path.trim_start_matches('/');
    if clean.is_empty() || clean == "index.html" {
        return serve_static_or_dynamic(State(state), headers, AxumPath("paste/index.html".to_string())).await;
    }
    let (is_raw, id) = if let Some(rest) = clean.strip_prefix("raw/") {
        (true, rest)
    } else {
        (false, clean)
    };

    let now_s = now_secs();
    let row: Option<(String, String, i64, i64)> = {
        let conn = state.db.lock().unwrap();
        conn.query_row(
            "SELECT body, d, expires_at, t FROM pastes WHERE id = ?",
            params![id],
            |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?)),
        )
        .ok()
    };

    match row {
        Some((body, _d, expires_at, t)) if expires_at >= now_s => {
            if is_raw || !wants_html(&headers) {
                text_response(StatusCode::OK, body, vec![])
            } else {
                let when = chrono_format(t);
                let prefix = if state.local { "/paste" } else { "" };
                let html_body = format!(
                    r#"<h1>paste {}</h1><p class="dim">{} utc &middot; <a href="{}/raw/{}">raw</a> &middot; <a href="{}/">new paste</a></p><pre class="wrap"><code>{}</code></pre>"#,
                    escape_html(id),
                    when,
                    prefix,
                    escape_html(id),
                    prefix,
                    escape_html(&body)
                );
                page(&format!("paste {}", id), &html_body, state.local)
            }
        }
        _ => {
            if wants_html(&headers) {
                page("gone", "<h1>404</h1><p>no such paste. it expired or never existed.</p>", state.local)
            } else {
                text_response(StatusCode::NOT_FOUND, "not found\n".into(), vec![])
            }
        }
    }
}

// Paste Handler: Delete
async fn handle_paste_delete(
    State(state): State<AppState>,
    headers: HeaderMap,
    AxumPath(id): AxumPath<String>,
) -> Response {
    let token = headers
        .get("x-delete-token")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("");
    if token.is_empty() {
        return text_response(StatusCode::FORBIDDEN, "bad delete token\n".into(), vec![]);
    }
    let token_hash = sha256_hex(token);
    let now_s = now_secs();

    let conn = state.db.lock().unwrap();
    let row: Option<(String, i64)> = conn
        .query_row("SELECT d, expires_at FROM pastes WHERE id = ?", params![id], |r| {
            Ok((r.get(0)?, r.get(1)?))
        })
        .ok();

    match row {
        Some((d, expires_at)) if expires_at >= now_s => {
            if d != token_hash {
                text_response(StatusCode::FORBIDDEN, "bad delete token\n".into(), vec![])
            } else {
                conn.execute("DELETE FROM pastes WHERE id = ?", params![id]).ok();
                text_response(StatusCode::OK, "deleted\n".into(), vec![])
            }
        }
        _ => text_response(StatusCode::NOT_FOUND, "not found\n".into(), vec![]),
    }
}

fn chrono_format(ts_millis: i64) -> String {
    let secs = ts_millis / 1000;
    let days = secs / 86400;
    // Simple naive UTC time representation
    let rem = secs % 86400;
    let h = rem / 3600;
    let m = (rem % 3600) / 60;
    format!("day {} {:02}:{:02}", days, h, m)
}

#[derive(Serialize)]
struct GuestbookEntry {
    id: i64,
    name: String,
    message: String,
    website: Option<String>,
    t: i64,
}

#[derive(Serialize)]
struct GuestbookListResponse {
    entries: Vec<GuestbookEntry>,
    cursor: Option<i64>,
}

#[derive(Deserialize)]
struct GuestbookSignPayload {
    name: Option<String>,
    message: Option<String>,
    website: Option<String>,
    hp: Option<String>,
}

// Guestbook Handler: List
async fn handle_guestbook_list(
    State(state): State<AppState>,
    Query(params): Query<HashMap<String, String>>,
) -> Response {
    let before: i64 = params
        .get("cursor")
        .and_then(|v| v.parse().ok())
        .unwrap_or(i64::MAX);
    let limit = 40;

    let conn = state.db.lock().unwrap();
    let mut stmt = conn
        .prepare("SELECT id, name, message, website, t FROM guestbook_entries WHERE id < ? ORDER BY id DESC LIMIT ?")
        .unwrap();
    let rows = stmt
        .query_map(params![before, limit + 1], |r| {
            Ok(GuestbookEntry {
                id: r.get(0)?,
                name: r.get(1)?,
                message: r.get(2)?,
                website: r.get(3)?,
                t: r.get(4)?,
            })
        })
        .unwrap();

    let mut entries = Vec::new();
    for row in rows.flatten() {
        entries.push(row);
    }

    let cursor = if entries.len() > limit as usize {
        entries.pop();
        entries.last().map(|e| e.id)
    } else {
        None
    };

    axum::Json(GuestbookListResponse { entries, cursor }).into_response()
}

// Guestbook Handler: Sign
async fn handle_guestbook_sign(
    State(state): State<AppState>,
    headers: HeaderMap,
    body_bytes: axum::body::Bytes,
) -> Response {
    let ip = get_client_ip(&headers);
    let hash_ip = sha256_hex(&format!("gb:{}", ip))[..16].to_string();
    let now = now_millis();

    let ct = headers
        .get(header::CONTENT_TYPE)
        .and_then(|v| v.to_str().ok())
        .unwrap_or("");

    let payload: GuestbookSignPayload = if ct.contains("application/json") {
        serde_json::from_slice(&body_bytes).unwrap_or(GuestbookSignPayload {
            name: None,
            message: None,
            website: None,
            hp: None,
        })
    } else {
        serde_urlencoded::from_bytes(&body_bytes).unwrap_or(GuestbookSignPayload {
            name: None,
            message: None,
            website: None,
            hp: None,
        })
    };

    if payload.hp.as_ref().map(|s| !s.trim().is_empty()).unwrap_or(false) {
        return axum::Json(serde_json::json!({ "ok": true })).into_response();
    }

    let name = payload.name.unwrap_or_default().trim().to_string();
    let message = payload.message.unwrap_or_default().trim().to_string();
    let website = payload.website.map(|s| s.trim().to_string()).filter(|s| !s.is_empty());

    if name.is_empty() || name.len() > 49 {
        return (StatusCode::BAD_REQUEST, axum::Json(serde_json::json!({ "error": "name is required (max 49 characters)" }))).into_response();
    }
    if message.is_empty() || message.len() > 499 {
        return (StatusCode::BAD_REQUEST, axum::Json(serde_json::json!({ "error": "message is required (max 499 characters)" }))).into_response();
    }
    if RESERVED_NAMES.iter().any(|r| name.to_lowercase().contains(r)) {
        return (StatusCode::BAD_REQUEST, axum::Json(serde_json::json!({ "error": "that name is reserved" }))).into_response();
    }

    let conn = state.db.lock().unwrap();
    conn.execute("DELETE FROM guestbook_hits WHERE t < ?", params![now - 3600 * 1000]).ok();

    let global_count: i64 = conn
        .query_row("SELECT COUNT(*) FROM guestbook_hits", [], |r| r.get(0))
        .unwrap_or(0);
    if global_count >= LIMIT_GB_GLOBAL_HOUR {
        return (StatusCode::TOO_MANY_REQUESTS, axum::Json(serde_json::json!({ "error": "the guestbook is getting a lot of traffic. try again in a bit." }))).into_response();
    }

    let (my_count, last_t): (i64, Option<i64>) = conn
        .query_row(
            "SELECT COUNT(*), MAX(t) FROM guestbook_hits WHERE h = ?",
            params![hash_ip],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .unwrap_or((0, None));

    if my_count >= LIMIT_GB_PER_HOUR {
        return (StatusCode::TOO_MANY_REQUESTS, axum::Json(serde_json::json!({ "error": format!("you can sign {} times an hour.", LIMIT_GB_PER_HOUR) }))).into_response();
    }
    if let Some(lt) = last_t {
        if now - lt < LIMIT_GB_GAP_SECS * 1000 {
            return (StatusCode::TOO_MANY_REQUESTS, axum::Json(serde_json::json!({ "error": "slow down, wait a few seconds." }))).into_response();
        }
    }

    conn.execute("INSERT INTO guestbook_hits (h, t) VALUES (?, ?)", params![hash_ip, now]).ok();
    conn.execute(
        "INSERT INTO guestbook_entries (name, message, website, t) VALUES (?, ?, ?, ?)",
        params![name, message, website, now],
    )
    .expect("insert guestbook failed");
    let id = conn.last_insert_rowid();

    (StatusCode::CREATED, axum::Json(serde_json::json!({ "ok": true, "id": id }))).into_response()
}

// Guestbook Handler: Delete
async fn handle_guestbook_delete(
    State(state): State<AppState>,
    AxumPath(id): AxumPath<i64>,
) -> Response {
    let conn = state.db.lock().unwrap();
    conn.execute("DELETE FROM guestbook_entries WHERE id = ?", params![id]).ok();
    axum::Json(serde_json::json!({ "ok": true })).into_response()
}

// Terminal view for guestbook root
async fn handle_guestbook_terminal(State(state): State<AppState>, headers: HeaderMap) -> Response {
    let conn = state.db.lock().unwrap();
    let mut stmt = conn
        .prepare("SELECT id, name, message, website, t FROM guestbook_entries ORDER BY id DESC LIMIT 20")
        .unwrap();
    let rows = stmt
        .query_map([], |r| {
            Ok(GuestbookEntry {
                id: r.get(0)?,
                name: r.get(1)?,
                message: r.get(2)?,
                website: r.get(3)?,
                t: r.get(4)?,
            })
        })
        .unwrap();

    let mut lines = Vec::new();
    for e in rows.flatten() {
        let site = e.website.map(|w| format!("  <{}>", w)).unwrap_or_default();
        let msg = e.message.replace('\n', "\n  ");
        lines.push(format!("date  {}{}\n  {}", e.name, site, msg));
    }

    let body = if lines.is_empty() {
        "nobody yet. be the first!".to_string()
    } else {
        lines.join("\n\n")
    };

    let sign_url = if state.local {
        let host = headers
            .get(header::HOST)
            .and_then(|v| v.to_str().ok())
            .unwrap_or("localhost:8000");
        format!("http://{}/guestbook/", host)
    } else {
        "https://guestbook.riverxia.sh/".to_string()
    };
    let txt = format!(
        "~*~ guestbook ~*~\n\n{}\n\nsign it: curl -d name=you -d message='hi!' {}\n",
        body, sign_url
    );
    text_response(StatusCode::OK, txt, vec![])
}

// Root router
pub fn app(dist_dir: PathBuf, db: Connection, local: bool) -> Router {
    let state = AppState {
        dist_dir,
        db: Arc::new(Mutex::new(db)),
        local,
    };

    Router::new()
        // API routes
        .route("/paste", post(handle_paste_create))
        .route("/paste/", post(handle_paste_create))
        .route("/paste/{*path}", get(handle_paste_get).delete(handle_paste_delete))
        .route("/api/entries", get(handle_guestbook_list).post(handle_guestbook_sign))
        .route("/api/entries/{id}", axum::routing::delete(handle_guestbook_delete))
        .route("/guestbook/api/entries", get(handle_guestbook_list).post(handle_guestbook_sign))
        .route("/guestbook/api/entries/{id}", axum::routing::delete(handle_guestbook_delete))
        // Root fallback routes
        .route(
            "/",
            get(|state: State<AppState>, headers: HeaderMap| async move {
                let host = headers
                    .get(header::HOST)
                    .and_then(|v| v.to_str().ok())
                    .unwrap_or("")
                    .to_lowercase();
                if host.starts_with("guestbook.") && is_cli_request(&headers) {
                    return handle_guestbook_terminal(state, headers).await;
                }
                serve_static_or_dynamic(state, headers, AxumPath(String::new())).await
            })
            .post(handle_paste_create),
        )
        .route("/{*path}", get(serve_static_or_dynamic))
        .layer(CorsLayer::permissive())
        .with_state(state)
}

#[tokio::main]
async fn main() {
    let port = std::env::var("PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(8000);
    let dist_dir = std::env::var("DIST_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("dist"));
    let db_path = std::env::var("DB_PATH")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from(".data/riverxia.db"));

    let db = init_db(&db_path);
    let local = std::env::var("LOCAL").as_deref() == Ok("1");
    let router = app(dist_dir, db, local);

    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    println!("riverxia-server listening on http://{}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await.expect("bind failed");
    axum::serve(listener, router).await.expect("server failed");
}
