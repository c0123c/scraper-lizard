import argparse
import base64
import html
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)
NPM_BIN = Path.home() / "AppData" / "Roaming" / "npm"
OPENCLAW_BROWSER_CLI = NPM_BIN / "clawdbot.cmd"
DEFAULT_BROWSER_PROFILE = "user"
FALLBACK_BROWSER_PROFILES = ["user", "my-chrome"]
OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"
SEARCH_ENGINES = {
    "chasedream": "site:chasedream.com/article",
    "1point3acres": "site:1point3acres.com/home/pins",
}


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def dedupe_keep_order(items: list[str]) -> list[str]:
    seen = set()
    output: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def extract_duckduckgo_result_urls(page_html: str) -> list[str]:
    urls: list[str] = []
    matches = re.findall(
        r'class="result__a"[^>]*href="([^"]+)"|href="([^"]+)"[^>]*class="result__a"',
        page_html,
    )
    for pair in matches:
        raw = pair[0] or pair[1]
        href = html.unescape(raw)
        if href.startswith("//duckduckgo.com/l/?"):
            parsed = urlparse("https:" + href)
            uddg = parse_qs(parsed.query).get("uddg", [])
            if uddg:
                urls.append(unquote(uddg[0]))
                continue
        urls.append(href)
    return dedupe_keep_order(urls)


def normalize_keyword_sites(raw_sites: list[str] | None) -> list[str]:
    if not raw_sites:
        return ["chasedream", "1point3acres"]
    mapping = {
        "cd": "chasedream",
        "chasedream": "chasedream",
        "1point3acres": "1point3acres",
        "1p3a": "1point3acres",
        "yi-mu-san-fen-di": "1point3acres",
    }
    normalized: list[str] = []
    for item in raw_sites:
        key = mapping.get(item.strip().lower())
        if key and key not in normalized:
            normalized.append(key)
    if not normalized:
        raise RuntimeError("Keyword mode did not receive any supported site names.")
    return normalized


def expand_keyword_urls(keyword: str, sites: list[str], limit_per_site: int) -> list[str]:
    keyword = keyword.strip()
    if not keyword:
        raise RuntimeError("Keyword mode requires a non-empty keyword.")
    all_urls: list[str] = []
    for site in normalize_keyword_sites(sites):
        query = f"{SEARCH_ENGINES[site]} {keyword}"
        search_url = "https://html.duckduckgo.com/html/?q=" + quote(query)
        result_urls = extract_duckduckgo_result_urls(fetch_text(search_url))
        if site == "chasedream":
            result_urls = [url for url in result_urls if re.search(r"https://www\.chasedream\.com/article/\d+", url)]
        elif site == "1point3acres":
            result_urls = [url for url in result_urls if re.search(r"https://www\.1point3acres\.com/home/pins/\d+", url)]
        all_urls.extend(result_urls[:limit_per_site])
    return dedupe_keep_order(all_urls)


def load_gateway_token() -> str:
    if not OPENCLAW_CONFIG.exists():
        raise RuntimeError(f"Could not find OpenClaw config: {OPENCLAW_CONFIG}")
    data = json.loads(OPENCLAW_CONFIG.read_text(encoding="utf-8"))
    token = str(data.get("gateway", {}).get("auth", {}).get("token", "")).strip()
    if not token:
        raise RuntimeError("Could not find gateway.auth.token in OpenClaw config.")
    return token


def strip_tags(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"</p\s*>", "\n\n", value, flags=re.I)
    value = re.sub(r"</div\s*>", "\n", value, flags=re.I)
    value = re.sub(r"</blockquote\s*>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value)
    value = value.replace("\r", "")
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def html_to_paragraphs(article_html: str) -> list[str]:
    paragraphs = re.findall(r"<p>(.*?)</p>", article_html, flags=re.S | re.I)
    return [text for text in (strip_tags(part) for part in paragraphs) if text]


def cleanup_label_text(value: str) -> str:
    value = strip_tags(value)
    value = re.sub(r"^[^:：]+[:：]\s*", "", value)
    return value.strip()


def normalize_comment_text(message_raw: str, message_html: str) -> str:
    text = (message_raw or "").replace("\r", "").strip()
    if not text and 'data-md64="' in message_html:
        md64_match = re.search(r'data-md64="([^"]+)"', message_html)
        if md64_match:
            try:
                text = base64.b64decode(md64_match.group(1)).decode("utf-8", errors="replace").strip()
            except Exception:
                text = ""
    if not text:
        text = strip_tags(message_html)

    text = re.sub(r"\[quote\]", "引用内容开始\n", text, flags=re.I)
    text = re.sub(r"\[/quote\]", "\n引用内容结束", text, flags=re.I)
    text = re.sub(r"\[(?:/?size|/?color|/?url|/?img|/?attach)[^\]]*\]", "", text, flags=re.I)
    text = re.sub(r"\[(?:/?b|/?u|/?i|/?list|/?\*)[^\]]*\]", "", text, flags=re.I)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def build_html_doc(data: dict) -> str:
    title = html.escape(data["title"])
    url = html.escape(data["url"])
    author = html.escape(data.get("author", ""))
    date = html.escape(data.get("date", ""))
    article_html = "\n".join(
        f'      <p class="content-line">{html.escape(p)}</p>' for p in data["article_paragraphs"]
    )
    comments_html = "\n".join(
        (
            "      <article class=\"comment\">\n"
            f"        <p class=\"comment-line\"><strong>-作者：</strong>{html.escape(c['username'])}</p>\n"
            f"        <p class=\"comment-line\"><strong>-发布时间：</strong>{html.escape(c['time'])}</p>\n"
            f"        <p class=\"comment-line comment-message\"><strong>发布内容：</strong>{html.escape(c['message'])}</p>\n"
            "        <p class=\"comment-separator\">------</p>\n"
            "      </article>"
        )
        for c in data["comments"]
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} - 抓取结果</title>
  <style>
    :root {{
      --ink: #1f2329;
      --muted: #646a73;
      --line: #d9dde4;
      --accent: #1456f0;
    }}
    body {{
      margin: 0;
      padding: 0;
      background: #ffffff;
      color: var(--ink);
      font: 14px/1.8 "Microsoft YaHei", "PingFang SC", sans-serif;
    }}
    .wrap {{
      max-width: 820px;
      margin: 0 auto;
      padding: 40px 48px 56px;
    }}
    h1, h2 {{
      margin: 0;
      line-height: 1.45;
    }}
    h1 {{
      margin-bottom: 24px;
      font-size: 28px;
      font-weight: 700;
    }}
    h2 {{
      margin: 28px 0 14px;
      font-size: 20px;
      font-weight: 700;
    }}
    .info-block {{
      margin: 0 0 24px;
    }}
    .info-line {{
      margin: 0 0 8px;
      word-break: break-all;
    }}
    .info-line strong, .comment-line strong {{
      color: var(--muted);
      margin-right: 4px;
    }}
    .content-line {{
      margin: 0 0 14px;
      text-indent: 2em;
    }}
    .comment {{
      padding: 0 0 14px;
      margin-bottom: 14px;
      border-bottom: 1px solid var(--line);
    }}
    .comment-line {{
      margin: 0 0 6px;
      white-space: pre-wrap;
    }}
    .comment-message {{
      margin-bottom: 0;
    }}
    .comment-separator {{
      margin: 10px 0 0;
      color: var(--muted);
      letter-spacing: 1px;
    }}
    a {{
      color: var(--accent);
      text-decoration: none;
    }}
  </style>
</head>
<body>
  <main class="wrap">
    <h1>{title}</h1>
    <section class="info-block">
      <p class="info-line"><strong>网址:</strong><a href="{url}">{url}</a></p>
      <p class="info-line"><strong>标题：</strong>{title}</p>
      <p class="info-line"><strong>作者：</strong>{author}</p>
      <p class="info-line"><strong>日期:</strong>{date}</p>
      <p class="info-line"><strong>评论数：</strong>{len(data["comments"])}</p>
    </section>
    <section class="article">
      <h2>正文：</h2>
{article_html}
    </section>
    <section class="comments">
      <h2>评论内容：</h2>
{comments_html}
    </section>
  </main>
</body>
</html>
"""


def render_word_exports(html_path: Path, docx_path: Path | None, pdf_path: Path | None) -> dict:
    docx_target = f"'{str(docx_path)}'" if docx_path else "$null"
    pdf_target = f"'{str(pdf_path)}'" if pdf_path else "$null"
    ps = f"""
$src = '{str(html_path)}'
$docx = {docx_target}
$pdf = {pdf_target}
$wdFormatDocumentDefault = 16
$wdFormatPDF = 17
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$doc = $word.Documents.Open($src)
if ($docx) {{ $doc.SaveAs([ref]$docx, [ref]$wdFormatDocumentDefault) }}
if ($pdf) {{ $doc.SaveAs([ref]$pdf, [ref]$wdFormatPDF) }}
$doc.Close()
$word.Quit()
"""
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            check=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return {"docx": False, "pdf": False}
    return {
        "docx": bool(docx_path and docx_path.exists()),
        "pdf": bool(pdf_path and pdf_path.exists()),
    }


def extract_chasedream_article(page_html: str, url: str) -> dict:
    title_match = re.search(r'<meta property="og:title" content="([^"]+)"', page_html)
    author_match = re.search(r'<span class="desc-l1">(.*?)</span>', page_html, flags=re.S)
    date_match = re.search(r'<span class="desc-r1">(.*?)</span>', page_html, flags=re.S)
    markdown_match = re.search(
        r'<script type="application/json" id="article-markdown">(.*?)</script>',
        page_html,
        flags=re.S,
    )
    article_id_match = re.search(
        r'<script type="application/json" id="article-id-data">(\d+)</script>',
        page_html,
    )
    pagination_match = re.search(
        r'<script type="application/json" id="comments-pagination-data">(.*?)</script>',
        page_html,
        flags=re.S,
    )
    if not markdown_match or not article_id_match:
        raise RuntimeError("Could not locate ChaseDream article payload in page HTML.")

    article_html = json.loads(markdown_match.group(1))
    comments_pagination = json.loads(pagination_match.group(1)) if pagination_match else {}
    author_text = cleanup_label_text(author_match.group(1)) if author_match else ""
    date_text = cleanup_label_text(date_match.group(1)) if date_match else ""
    if not date_text:
        date_fallback = re.search(r"\b20\d{2}-\d{1,2}-\d{1,2}\b", page_html)
        if date_fallback:
            date_text = date_fallback.group(0)

    return {
        "site": "chasedream",
        "url": url,
        "title": html.unescape(title_match.group(1)).strip() if title_match else "Untitled",
        "author": author_text,
        "date": date_text,
        "article_id": int(article_id_match.group(1)),
        "article_paragraphs": html_to_paragraphs(article_html),
        "comments_pagination": comments_pagination,
    }


def fetch_chasedream_comments(article_id: int, total_pages: int) -> list[dict]:
    comments: list[dict] = []
    for page in range(1, max(total_pages, 1) + 1):
        comments_url = f"https://www.chasedream.com/article/{article_id}/comments?page={page}"
        payload = json.loads(fetch_text(comments_url))
        items = payload.get("data", {}).get("list", [])
        for item in items:
            message_html = item.get("messageHtml") or ""
            comments.append(
                {
                    "username": item.get("username", ""),
                    "time": item.get("timeStr", ""),
                    "pid": item.get("pid"),
                    "message": normalize_comment_text(item.get("messageRaw") or "", message_html),
                }
            )
        time.sleep(0.3)
    return comments


def run_node_script(script: str, timeout: int = 40000) -> str:
    proc = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "node helper failed").strip()
        raise RuntimeError(detail)
    return (proc.stdout or "").strip()


def cdp_evaluate_target(target_id: str, expression: str, timeout: int = 40000) -> object:
    relay_token = load_gateway_token()
    payload = json.dumps(expression, ensure_ascii=False)
    script = f"""
const ws = new WebSocket('ws://127.0.0.1:18792/cdp?token={relay_token}');
let seq = 0;
const pending = new Map();
function send(method, params, sessionId) {{
  const id = ++seq;
  const payload = {{ id, method, params }};
  if (sessionId) payload.sessionId = sessionId;
  ws.send(JSON.stringify(payload));
  return new Promise((resolve, reject) => pending.set(id, {{ resolve, reject }}));
}}
ws.onmessage = (ev) => {{
  const msg = JSON.parse(ev.data);
  if (!msg.id || !pending.has(msg.id)) return;
  const p = pending.get(msg.id);
  pending.delete(msg.id);
  if (msg.error) p.reject(new Error(typeof msg.error === 'string' ? msg.error : JSON.stringify(msg.error)));
  else p.resolve(msg.result);
}};
ws.onerror = () => {{
  console.error('WebSocket relay error');
  process.exit(1);
}};
ws.onopen = async () => {{
  try {{
    const attached = await send('Target.attachToTarget', {{ targetId: {json.dumps(target_id)}, flatten: true }});
    const sessionId = attached.sessionId;
    const result = await send('Runtime.evaluate', {{
      expression: {payload},
      returnByValue: true
    }}, sessionId);
    const value = result?.result?.value;
    if (typeof value === 'string') process.stdout.write(value);
    else process.stdout.write(JSON.stringify(value ?? null));
  }} catch (err) {{
    console.error(String(err));
    process.exitCode = 1;
  }} finally {{
    setTimeout(() => ws.close(), 100);
  }}
}};
"""
    raw = run_node_script(script, timeout=timeout)
    if not raw:
        raise RuntimeError("CDP evaluate returned empty output.")
    return json.loads(raw)


def run_browser_command(args: list[str], timeout: int = 30000) -> str:
    if not OPENCLAW_BROWSER_CLI.exists():
        raise RuntimeError("Could not find clawdbot browser CLI in AppData\\Roaming\\npm.")
    proc = subprocess.run(
        [str(OPENCLAW_BROWSER_CLI), "browser", "--timeout", "90000", *args],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "unknown browser error").strip()
        raise RuntimeError(detail)
    return (proc.stdout or "").strip()


def run_browser_command_utf8(args: list[str], timeout: int = 30000) -> str:
    if not OPENCLAW_BROWSER_CLI.exists():
        raise RuntimeError("Could not find clawdbot browser CLI in AppData\\Roaming\\npm.")
    quoted_args = ", ".join("'" + str(item).replace("'", "''") + "'" for item in args)
    script = (
        "$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
        f"$argsList = @('--timeout','90000',{quoted_args}); & '{str(OPENCLAW_BROWSER_CLI).replace("'", "''")}' browser @argsList"
    )
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "unknown browser error").strip()
        raise RuntimeError(detail)
    return (proc.stdout or "").strip()


def browser_open(url: str, profile: str) -> str:
    output = run_browser_command(["--browser-profile", profile, "open", url, "--json"])
    payload = json.loads(output)
    return payload["targetId"]


def browser_wait(profile: str, ms: int = 4000, target_id: str | None = None) -> None:
    args = ["--browser-profile", profile, "wait"]
    if target_id:
        args.extend(["--target-id", target_id])
    args.extend(["--time", str(ms)])
    run_browser_command(args, timeout=max(ms + 15000, 30000))


def browser_evaluate_json(profile: str, fn_source: str, target_id: str | None = None) -> dict:
    args = ["--browser-profile", profile, "evaluate"]
    if target_id:
        args.extend(["--target-id", target_id])
    args.extend(["--fn", fn_source])
    output = run_browser_command(args)
    return json.loads(output)


def browser_tabs(profile: str) -> list[dict]:
    output = run_browser_command(["--browser-profile", profile, "tabs", "--json"])
    return json.loads(output).get("tabs", [])


def browser_focus(profile: str, target_id: str) -> None:
    run_browser_command(["--browser-profile", profile, "focus", target_id])


def browser_snapshot_text(profile: str, target_id: str) -> str:
    return run_browser_command_utf8(
        ["--browser-profile", profile, "snapshot", "--target-id", target_id, "--format", "ai", "--limit", "180"],
        timeout=100000,
    )


def select_matching_tab(profile: str, url: str) -> str:
    tabs = browser_tabs(profile)
    exact_matches = [tab for tab in tabs if tab.get("url", "") == url]
    if exact_matches:
        return exact_matches[-1]["targetId"]
    id_match = re.search(r"thread-(\d+)-", url)
    if not id_match:
        id_match = re.search(r"/home/pins/(\d+)", url)
    if not id_match:
        id_match = re.search(r"/thread/(\d+)", url)
    if id_match:
        thread_id = id_match.group(1)
        thread_matches = [tab for tab in tabs if thread_id in tab.get("url", "")]
        if thread_matches:
            return thread_matches[-1]["targetId"]
    host = urlparse(url).netloc.lower()
    host_matches = [tab for tab in tabs if host in tab.get("url", "").lower()]
    if host_matches:
        return host_matches[-1]["targetId"]
    raise RuntimeError(f"Could not find a browser tab for {url}")


def parse_snapshot_label(line: str) -> str:
    match = re.search(r'"([^"]*)"', line)
    return match.group(1) if match else ""


def tokens_to_text(tokens: list[str]) -> str:
    parts: list[str] = []
    for token in tokens:
        if token == "\n":
            parts.append("\n")
        elif token:
            if not parts or parts[-1].endswith("\n"):
                parts.append(token)
            else:
                parts.append("\n" + token)
    text = "".join(parts)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_onepoint3acres_snapshot(snapshot_text: str, url: str) -> dict:
    if "Performing security verification" in snapshot_text or "Just a moment" in snapshot_text:
        raise RuntimeError(
            "1point3acres is still showing the Cloudflare verification page. "
            "Please open the thread in Chrome, finish the verification once, and run again."
        )

    lines = snapshot_text.splitlines()
    title = ""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('- heading "') and "注册一亩三分地论坛" not in stripped and "相关帖子" not in stripped:
            title = parse_snapshot_label(stripped)
            break
    if not title:
        raise RuntimeError("Could not locate the 1point3acres thread title in snapshot output.")

    posts: list[dict] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith('- link "'):
            username = parse_snapshot_label(stripped)
            if username and username not in {
                "返回列表", "发新帖", "上一主题", "下一主题", "只看该作者",
                "回复", "举报", "收藏 收藏2", "分享 淘帖",
            }:
                time_idx = None
                time_value = ""
                for j in range(i + 1, min(i + 18, len(lines))):
                    time_match = re.search(r'"(\d{4}-\d{1,2}-\d{1,2} \d{1,2}:\d{2}:\d{2})"', lines[j])
                    if time_match:
                        time_idx = j
                        time_value = time_match.group(1)
                        break
                if time_idx is not None:
                    global_idx = None
                    for j in range(time_idx, min(time_idx + 25, len(lines))):
                        if 'statictext "全局："' in lines[j]:
                            global_idx = j
                            break
                    if global_idx is not None:
                        tokens: list[str] = []
                        n = global_idx + 1
                        while n < len(lines):
                            current = lines[n].strip()
                            if current.startswith('- link "回复"') or current.startswith('- link "收藏') or current.startswith('- heading "相关帖子"'):
                                break
                            if current.startswith("- linebreak"):
                                tokens.append("\n")
                            elif current.startswith('- statictext "'):
                                text_value = parse_snapshot_label(current)
                                if text_value not in {"|", "全局：", "本楼：", "🔗", "👍", "👎", "楼主", "来自APP"}:
                                    tokens.append(text_value)
                            elif current.startswith('- link "') and "发表于" in current:
                                tokens.append(parse_snapshot_label(current))
                            n += 1
                        message = tokens_to_text(tokens)
                        if message:
                            posts.append(
                                {
                                    "username": username,
                                    "time": time_value,
                                    "message": message,
                                }
                            )
                            i = n
                            continue
        i += 1

    if not posts:
        raise RuntimeError("Could not parse any 1point3acres posts from browser snapshot.")

    main_post = posts[0]
    return {
        "site": "1point3acres",
        "url": url,
        "title": title,
        "author": main_post["username"],
        "date": main_post["time"],
        "article_paragraphs": [part for part in main_post["message"].split("\n") if part.strip()],
        "comments": posts[1:],
    }


RELATIVE_TIME_RE = re.compile(r"^\d+\s*(?:分钟|小时|天|个月|年)前$")
ABSOLUTE_TIME_RE = re.compile(r"^\d{4}-\d{1,2}-\d{1,2}(?: \d{1,2}:\d{2}(?::\d{2})?)?$")
NUMERIC_RE = re.compile(r"^\d+$")
REACTION_RE = re.compile(r"^[^\w\s]{1,3}$")


def is_time_line(value: str) -> bool:
    return bool(RELATIVE_TIME_RE.match(value) or ABSOLUTE_TIME_RE.match(value))


def is_comment_author_line(value: str) -> bool:
    value = value.strip()
    if not value or len(value) > 40:
        return False
    if is_time_line(value) or NUMERIC_RE.match(value):
        return False
    blocked = {"最早", "回复", "分享", "道具", "匿名", "查看更多回复", "只看作者"}
    return value not in blocked


def trim_comment_message(lines: list[str]) -> list[str]:
    cleaned = [line.strip() for line in lines if line.strip()]
    while cleaned and (
        NUMERIC_RE.match(cleaned[-1])
        or REACTION_RE.match(cleaned[-1])
        or cleaned[-1].startswith("已获得 ")
        or cleaned[-1] == "查看更多回复"
    ):
        cleaned.pop()
    return cleaned


def split_comment_block(text: str) -> list[dict]:
    lines = [line.strip() for line in text.replace("\r", "").splitlines() if line.strip()]
    comments: list[dict] = []
    idx = 0
    while idx < len(lines) - 1:
        if not is_comment_author_line(lines[idx]) or not is_time_line(lines[idx + 1]):
            idx += 1
            continue
        username = lines[idx]
        time_value = lines[idx + 1]
        j = idx + 2
        while j < len(lines):
            if j + 1 < len(lines) and is_comment_author_line(lines[j]) and is_time_line(lines[j + 1]):
                break
            j += 1
        message_lines = trim_comment_message(lines[idx + 2 : j])
        if message_lines:
            comments.append(
                {
                    "username": username,
                    "time": time_value,
                    "message": "\n".join(message_lines),
                }
            )
        idx = j
    return comments


def fetch_onepoint3acres_pin_payload(target_id: str) -> dict:
    expression = """
JSON.stringify((() => {
  const h1 = document.querySelector('h1');
  const mainCandidates = Array.from(document.querySelectorAll('main'));
  const main = mainCandidates.find(el => (el.innerText || '').includes('共') && (el.innerText || '').includes('条回复')) || mainCandidates[0] || document.body;
  const mainTime = main?.querySelector('time');
  const commentNodes = Array.from(document.querySelectorAll('div'))
    .filter(el => typeof el.className === 'string' && el.className.includes('flex flex-col py-2.5'))
    .map(el => (el.innerText || '').trim())
    .filter(Boolean);
  return {
    url: location.href,
    title: (h1?.innerText || document.title || '').trim(),
    pageTitle: (document.title || '').trim(),
    mainTimeText: (mainTime?.innerText || '').trim(),
    mainTimeTitle: (mainTime?.getAttribute('title') || '').trim(),
    mainText: (main?.innerText || document.body?.innerText || '').trim(),
    commentNodes,
  };
})())
"""
    payload = cdp_evaluate_target(target_id, expression, timeout=50000)
    if not isinstance(payload, dict):
        raise RuntimeError("Could not parse 1point3acres pin payload from browser.")
    return payload


def parse_onepoint3acres_pin(payload: dict, url: str) -> dict:
    main_text = str(payload.get("mainText", "")).replace("\r", "").strip()
    if not main_text:
        raise RuntimeError("1point3acres pin page did not expose readable text.")

    lines = [line.strip() for line in main_text.splitlines() if line.strip()]
    title = str(payload.get("title", "")).strip() or str(payload.get("pageTitle", "")).strip()
    if not title and lines:
        title = lines[0]
    if not title:
        raise RuntimeError("Could not determine 1point3acres pin title.")

    author = ""
    date_text = str(payload.get("mainTimeTitle", "")).strip() or str(payload.get("mainTimeText", "")).strip()
    board_line = ""
    title_idx = next((i for i, line in enumerate(lines) if title in line or line == title), 0)
    for i in range(title_idx + 1, min(title_idx + 8, len(lines))):
        line = lines[i]
        if not author and is_comment_author_line(line):
            author = line
            continue
        if author and not date_text and is_time_line(line):
            date_text = line
            continue
        if "发布于" in line:
            board_line = line
            break

    comments_count = 0
    comments_line_idx = None
    for i, line in enumerate(lines):
        match = re.search(r"共\s*(\d+)\s*条回复", line)
        if match:
            comments_count = int(match.group(1))
            comments_line_idx = i
            break

    body_start = 0
    if board_line:
        board_idx = lines.index(board_line)
        body_start = board_idx + 1
    else:
        body_start = title_idx + 1
    while body_start < len(lines) and (
        lines[body_start] in {"·", "回复", "分享", "道具", "匿名", "最早", "只看作者"}
        or NUMERIC_RE.match(lines[body_start])
        or is_time_line(lines[body_start])
    ):
        body_start += 1

    body_end = comments_line_idx if comments_line_idx is not None else len(lines)
    article_lines = trim_comment_message(lines[body_start:body_end])
    article_paragraphs: list[str] = []
    current: list[str] = []
    for line in article_lines:
        if line == "----":
            if current:
                article_paragraphs.append("\n".join(current))
                current = []
            continue
        if line.startswith("已获得 "):
            break
        current.append(line)
    if current:
        article_paragraphs.append("\n".join(current))

    comment_nodes = payload.get("commentNodes", [])
    comments: list[dict] = []
    seen = set()
    if isinstance(comment_nodes, list):
        for block in comment_nodes:
            for item in split_comment_block(str(block)):
                key = (item["username"], item["time"], item["message"])
                if key in seen:
                    continue
                seen.add(key)
                comments.append(item)

    if comments_count and len(comments) > comments_count:
        comments = comments[:comments_count]

    return {
        "site": "1point3acres",
        "url": url,
        "title": title,
        "author": author,
        "date": date_text,
        "article_paragraphs": article_paragraphs,
        "comments": comments,
    }


def scrape_onepoint3acres(url: str, browser_profile: str) -> dict:
    profiles_to_try = []
    for name in [browser_profile, *FALLBACK_BROWSER_PROFILES]:
        if name and name not in profiles_to_try:
            profiles_to_try.append(name)

    parsed = urlparse(url)
    last_error = None
    for profile_name in profiles_to_try:
        try:
            target_id = None
            try:
                target_id = select_matching_tab(profile_name, url)
            except RuntimeError:
                if "/home/pins/" in parsed.path:
                    target_id = browser_open(url, profile_name)
            if not target_id:
                raise RuntimeError(f"Could not find or open a browser tab for {url}")
            browser_focus(profile_name, target_id)
            browser_wait(profile_name, 1800, target_id)
            if "/home/pins/" in parsed.path:
                return parse_onepoint3acres_pin(fetch_onepoint3acres_pin_payload(target_id), url)
            snapshot_text = browser_snapshot_text(profile_name, target_id)
            return parse_onepoint3acres_snapshot(snapshot_text, url)
        except RuntimeError as exc:
            last_error = exc
            continue

    raise RuntimeError(
        "Please open this exact 1point3acres thread in Chrome first, finish any Cloudflare/remote-debugging prompts, "
        "keep the thread page visible, then run the scraper again."
    ) from last_error


def slug_from_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if "chasedream.com" in host:
        match = re.search(r"/article/(\d+)", url)
        return f"chasedream_{match.group(1) if match else 'unknown'}"
    if "1point3acres.com" in host:
        match = re.search(r"thread-(\d+)-", parsed.path)
        if not match:
            match = re.search(r"/home/pins/(\d+)", parsed.path)
        if not match:
            match = re.search(r"(?:tid=)(\d+)", parsed.query)
        return f"1point3acres_{match.group(1) if match else 'unknown'}"
    host_slug = re.sub(r"[^a-z0-9]+", "_", host).strip("_") or "site"
    return f"{host_slug}_page"


def scrape_url(url: str, browser_profile: str) -> dict:
    host = urlparse(url).netloc.lower()
    if "chasedream.com" in host:
        article = extract_chasedream_article(fetch_text(url), url)
        total_pages = int(article["comments_pagination"].get("total", 1) or 1)
        article["comments"] = fetch_chasedream_comments(article["article_id"], total_pages)
        return article
    if "1point3acres.com" in host or "1point3acres.cn" in host:
        return scrape_onepoint3acres(url, browser_profile)
    raise RuntimeError(f"Unsupported site for now: {host}")


def export_result(data: dict, output_dir: Path, formats: set[str]) -> dict:
    base_name = f"{slug_from_url(data['url'])}_article_comments"
    json_path = output_dir / f"{base_name}.json"
    html_path = output_dir / f"{base_name}.html"
    docx_path = output_dir / f"{base_name}.docx"
    pdf_path = output_dir / f"{base_name}.pdf"

    if "json" in formats:
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    if "html" in formats or "docx" in formats or "pdf" in formats:
        html_path.write_text(build_html_doc(data), encoding="utf-8")

    export_flags = {"docx": False, "pdf": False}
    if "docx" in formats or "pdf" in formats:
        export_flags = render_word_exports(
            html_path,
            docx_path if "docx" in formats else None,
            pdf_path if "pdf" in formats else None,
        )

    if "html" not in formats and html_path.exists():
        html_path.unlink()

    return {
        "url": data["url"],
        "title": data["title"],
        "site": data.get("site"),
        "json": str(json_path) if "json" in formats and json_path.exists() else None,
        "html": str(html_path) if "html" in formats and html_path.exists() else None,
        "docx": str(docx_path) if export_flags["docx"] else None,
        "pdf": str(pdf_path) if export_flags["pdf"] else None,
        "comments_count": len(data["comments"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch scrape supported forum/article pages.")
    parser.add_argument("--input", required=True, help="Path to URL list file")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--keyword", help="Keyword to expand into post URLs before scraping")
    parser.add_argument(
        "--keyword-sites",
        default="chasedream,1point3acres",
        help="Comma-separated site list for keyword mode: chasedream,1point3acres",
    )
    parser.add_argument(
        "--keyword-limit",
        type=int,
        default=10,
        help="Maximum number of URLs to collect per site in keyword mode",
    )
    parser.add_argument(
        "--formats",
        default="html,json,pdf",
        help="Comma-separated output formats: html,json,docx,pdf",
    )
    parser.add_argument(
        "--browser-profile",
        default=DEFAULT_BROWSER_PROFILE,
        help="OpenClaw browser profile for sites that require browser extraction",
    )
    args = parser.parse_args()

    formats = {item.strip().lower() for item in args.formats.split(",") if item.strip()}
    allowed = {"html", "json", "docx", "pdf"}
    unknown = formats - allowed
    if unknown:
        raise SystemExit(f"Unsupported formats: {', '.join(sorted(unknown))}")

    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    urls = [
        line.strip()
        for line in input_path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if args.keyword:
        keyword_sites = [item.strip() for item in args.keyword_sites.split(",") if item.strip()]
        expanded_urls = expand_keyword_urls(args.keyword, keyword_sites, max(args.keyword_limit, 1))
        print(f"[KEYWORD] {args.keyword}")
        print(f"[KEYWORD-SITES] {', '.join(normalize_keyword_sites(keyword_sites))}")
        print(f"[KEYWORD-EXPANDED] {len(expanded_urls)}")
        for item in expanded_urls:
            print(f"[URL] {item}")
        urls = dedupe_keep_order(urls + expanded_urls)

    results = []
    for url in urls:
        try:
            data = scrape_url(url, args.browser_profile)
            result = export_result(data, output_dir, formats)
            results.append({"ok": True, **result})
            print(f"[OK] {url}")
        except (
            urllib.error.URLError,
            RuntimeError,
            json.JSONDecodeError,
            subprocess.TimeoutExpired,
        ) as exc:
            results.append({"ok": False, "url": url, "error": str(exc)})
            print(f"[ERR] {url} -> {exc}", file=sys.stderr)

    return 0 if all(item.get("ok") for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
