import json
import os
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import uuid
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SCRAPER = ROOT / "batch_chasedream_scraper.py"
DEFAULT_OUTPUT = Path(r"C:\Users\Administrator\openclaw-output")
UPLOAD_DIR = ROOT / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
JOBS = {}
JOBS_LOCK = threading.Lock()


HTML_PAGE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>爬取小蜥蜴</title>
  <style>
    :root {
      --bg: #f6f2e8;
      --panel: #fffdf8;
      --ink: #211a14;
      --muted: #6f665e;
      --line: #ddd2c4;
      --accent: #df6d3c;
      --ok: #2f855a;
      --bad: #c53030;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font: 16px/1.5 "Microsoft YaHei", "PingFang SC", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(223,109,60,.16), transparent 28%),
        radial-gradient(circle at bottom right, rgba(34,124,157,.14), transparent 32%),
        linear-gradient(180deg, #efe8da 0%, var(--bg) 100%);
      min-height: 100vh;
      padding: 32px;
    }
    .wrap {
      max-width: 1080px;
      margin: 0 auto;
      display: grid;
      gap: 18px;
    }
    .hero, .card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      box-shadow: 0 18px 50px rgba(60, 35, 20, .08);
    }
    .hero {
      padding: 28px 30px;
      display: flex;
      justify-content: space-between;
      gap: 24px;
      align-items: center;
    }
    .title {
      margin: 0 0 8px;
      font-size: 34px;
      line-height: 1.15;
    }
    .sub {
      margin: 0;
      color: var(--muted);
    }
    .chipbar {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 14px;
    }
    .chip {
      border: 1px solid var(--line);
      background: #fff7f1;
      color: #b75228;
      padding: 8px 12px;
      border-radius: 999px;
      font-size: 14px;
    }
    .status-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
      padding: 22px;
    }
    .status {
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px 18px;
      background: #fffaf4;
    }
    .status h3 {
      margin: 0 0 10px;
      font-size: 16px;
    }
    .badge {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 13px;
      color: white;
      background: #999;
    }
    .badge.ok { background: var(--ok); }
    .badge.bad { background: var(--bad); }
    .status pre {
      margin: 12px 0 0;
      white-space: pre-wrap;
      color: var(--muted);
      font-size: 13px;
    }
    .card { padding: 24px; }
    .grid {
      display: grid;
      grid-template-columns: 1.1fr .9fr;
      gap: 18px;
    }
    label {
      display: block;
      font-weight: 700;
      margin-bottom: 8px;
    }
    .hint {
      margin-top: 6px;
      font-size: 13px;
      color: var(--muted);
    }
    textarea, input[type="text"], input[type="file"] {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px 14px;
      background: #fff;
      color: var(--ink);
      font: inherit;
    }
    textarea {
      min-height: 220px;
      resize: vertical;
    }
    .checks {
      display: grid;
      gap: 10px;
      margin-top: 10px;
    }
    .check {
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px;
      background: #fffaf4;
    }
    .actions {
      display: flex;
      gap: 12px;
      margin-top: 18px;
      align-items: center;
    }
    button {
      border: 0;
      border-radius: 14px;
      padding: 12px 18px;
      background: var(--accent);
      color: white;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }
    button.secondary {
      background: #efe4d6;
      color: var(--ink);
    }
    #result {
      margin-top: 18px;
      border-radius: 16px;
      padding: 16px;
      border: 1px solid var(--line);
      background: #fff;
      white-space: pre-wrap;
      min-height: 120px;
      font-family: Consolas, monospace;
      font-size: 13px;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div>
        <h1 class="title">爬取小蜥蜴</h1>
        <p class="sub">支持 URL 批量抓取，也支持通过关键词先搜索、再自动展开帖子链接。</p>
        <div class="chipbar">
          <span class="chip">上传 txt / csv 链接文件</span>
          <span class="chip">关键词模式支持 ChaseDream / 1point3acres</span>
          <span class="chip">可导出 HTML / JSON / DOCX / PDF</span>
        </div>
      </div>
    </section>

    <section class="card status-grid">
      <div class="status">
        <h3>OpenClaw Frontend</h3>
        <span id="frontend-badge" class="badge">Checking</span>
        <pre id="frontend-text">Checking...</pre>
      </div>
      <div class="status">
        <h3>OpenClaw Gateway</h3>
        <span id="gateway-badge" class="badge">Checking</span>
        <pre id="gateway-text">Checking...</pre>
      </div>
    </section>

    <section class="card">
      <div class="grid">
        <div>
          <label for="urls">URL List</label>
          <textarea id="urls" placeholder="一行一个链接"></textarea>
          <div class="hint">也可以直接上传 txt/csv 文件。</div>
          <div style="margin-top:14px;">
            <label for="file">Upload URL File</label>
            <input id="file" type="file" accept=".txt,.csv">
          </div>
          <div style="margin-top:14px;">
            <label for="keyword">Keyword Mode</label>
            <input id="keyword" type="text" placeholder="输入关键词后自动搜索并批量展开帖子链接">
            <div class="hint">当前关键词模式支持 ChaseDream 和 1point3acres。</div>
          </div>
        </div>
        <div>
          <label for="output">Output Folder</label>
          <input id="output" type="text" value="C:\\Users\\Administrator\\openclaw-output">
          <div style="margin-top:14px;">
            <label>Keyword Sites</label>
            <div class="checks">
              <div class="check"><input type="checkbox" id="site-chasedream" checked> ChaseDream</div>
              <div class="check"><input type="checkbox" id="site-1p3a" checked> 1point3acres</div>
            </div>
          </div>
          <div style="margin-top:14px;">
            <label for="keyword-limit">Keyword Limit / Site</label>
            <input id="keyword-limit" type="text" value="10">
          </div>
          <div class="checks">
            <div class="check"><input type="checkbox" id="fmt-html" checked> HTML</div>
            <div class="check"><input type="checkbox" id="fmt-json" checked> JSON</div>
            <div class="check"><input type="checkbox" id="fmt-docx"> DOCX</div>
            <div class="check"><input type="checkbox" id="fmt-pdf" checked> PDF</div>
          </div>
          <div class="actions">
            <button id="run-btn">Start</button>
            <button id="refresh-btn" class="secondary" type="button">Refresh Status</button>
          </div>
        </div>
      </div>
      <div id="result">等待开始…</div>
    </section>
  </div>

  <script>
    async function loadStatus() {
      const res = await fetch('/status');
      const data = await res.json();
      const fBadge = document.getElementById('frontend-badge');
      const gBadge = document.getElementById('gateway-badge');
      document.getElementById('frontend-text').textContent = data.frontend.text;
      document.getElementById('gateway-text').textContent = data.gateway.text;
      fBadge.textContent = data.frontend.ok ? 'RUNNING' : 'NOT DETECTED';
      gBadge.textContent = data.gateway.ok ? 'RESPONDED' : 'NOT DETECTED';
      fBadge.className = 'badge ' + (data.frontend.ok ? 'ok' : 'bad');
      gBadge.className = 'badge ' + (data.gateway.ok ? 'ok' : 'bad');
    }

    document.getElementById('refresh-btn').addEventListener('click', loadStatus);

    document.getElementById('file').addEventListener('change', async (ev) => {
      const file = ev.target.files[0];
      if (!file) return;
      document.getElementById('urls').value = await file.text();
    });

    let activeJob = null;

    async function pollJob(jobId) {
      const result = document.getElementById('result');
      while (activeJob === jobId) {
        try {
          const res = await fetch('/job/' + jobId, { cache: 'no-store' });
          const data = await res.json();
          result.textContent = (data.log || '').trim() || 'Running...';
          if (data.done) {
            result.textContent = JSON.stringify(data.result, null, 2);
            activeJob = null;
            break;
          }
        } catch (err) {
          result.textContent += '\\n[UI] 轮询任务状态失败：' + String(err);
          activeJob = null;
          break;
        }
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }

    document.getElementById('run-btn').addEventListener('click', async () => {
      const urls = document.getElementById('urls').value.trim();
      const keyword = document.getElementById('keyword').value.trim();
      const output = document.getElementById('output').value.trim();
      const keywordLimit = document.getElementById('keyword-limit').value.trim() || '10';
      const keywordSites = [
        ['chasedream', document.getElementById('site-chasedream').checked],
        ['1point3acres', document.getElementById('site-1p3a').checked],
      ].filter(x => x[1]).map(x => x[0]);
      const formats = [
        ['html', document.getElementById('fmt-html').checked],
        ['json', document.getElementById('fmt-json').checked],
        ['docx', document.getElementById('fmt-docx').checked],
        ['pdf', document.getElementById('fmt-pdf').checked],
      ].filter(x => x[1]).map(x => x[0]);

      if (!urls && !keyword) return alert('请至少提供 URL 或关键词。');
      if (keyword && !keywordSites.length) return alert('关键词模式至少选择一个站点。');
      if (!formats.length) return alert('至少选择一种输出格式。');

      const result = document.getElementById('result');
      result.textContent = 'Running...';
      try {
        const res = await fetch('/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          cache: 'no-store',
          body: JSON.stringify({ urls, keyword, keywordSites, keywordLimit, output, formats })
        });
        const data = await res.json();
        if (!data.ok) {
          result.textContent = JSON.stringify(data, null, 2);
          return;
        }
        activeJob = data.jobId;
        result.textContent = '任务已提交，正在启动...\\n';
        pollJob(data.jobId);
      } catch (err) {
        result.textContent = '[UI] 提交任务失败：' + String(err);
      }
    });

    loadStatus().catch((err) => {
      document.getElementById('frontend-text').textContent = 'Status check failed: ' + String(err);
      document.getElementById('gateway-text').textContent = 'Status check failed: ' + String(err);
    });
  </script>
</body>
</html>
"""


def frontend_status():
    try:
        resp = urllib.request.urlopen("http://127.0.0.1:5173", timeout=3)
        return {"ok": True, "text": f"HTTP {resp.status} at http://127.0.0.1:5173"}
    except Exception as exc:
        return {"ok": False, "text": f"Optional UI not running on 5173. {exc}"}


def gateway_status():
    cli = shutil.which("clawdbot") or shutil.which("openclaw")
    if not cli:
        npm_bin = Path.home() / "AppData" / "Roaming" / "npm"
        for name in ("clawdbot.cmd", "clawdbot.ps1", "openclaw.cmd", "openclaw.ps1"):
            candidate = npm_bin / name
            if candidate.exists():
                cli = str(candidate)
                break
    if not cli:
        return {"ok": False, "text": "Could not find clawdbot/openclaw executable."}

    try:
        proc = subprocess.run(
            [cli, "gateway", "status"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
            shell=False,
        )
        raw = (proc.stdout or proc.stderr or "").strip()
        ok = proc.returncode == 0 or "RPC probe: ok" in raw or '"running": true' in raw
        if ok:
            lines = [line for line in raw.splitlines() if line.strip()]
            summary = []
            for line in lines:
                if any(token in line for token in ("Gateway:", "Port:", "RPC probe:", "Runtime:", "running", "port")):
                    summary.append(line)
            return {"ok": True, "text": "\n".join(summary[:6]) or "Gateway responded."}
        if "heap out of memory" in raw.lower():
            return {
                "ok": False,
                "text": "Gateway helper crashed with out-of-memory. Please restart the browser relay/gateway.",
            }
        return {"ok": False, "text": (raw[:600] + "...") if len(raw) > 600 else (raw or "No output")}
    except Exception as exc:
        return {"ok": False, "text": str(exc)}


def create_job(cmd, output):
    job_id = uuid.uuid4().hex
    with JOBS_LOCK:
        JOBS[job_id] = {
            "done": False,
            "log": "",
            "result": None,
            "command": cmd,
            "output": output,
            "started_at": time.time(),
        }
    return job_id


def append_job_log(job_id: str, chunk: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return
        job["log"] += chunk
        if len(job["log"]) > 50000:
            job["log"] = job["log"][-50000:]


def finish_job(job_id: str, result: dict):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return
        job["done"] = True
        job["result"] = result


def run_job(job_id: str, cmd: list[str], output: str, tmp_path: str):
    append_job_log(job_id, "$ " + " ".join(cmd) + "\n")
    try:
        child_env = os.environ.copy()
        child_env["PYTHONIOENCODING"] = "utf-8"
        child_env["PYTHONUTF8"] = "1"
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=str(ROOT),
            env=child_env,
        )
        lines: list[str] = []
        assert proc.stdout is not None
        for line in proc.stdout:
            lines.append(line)
            append_job_log(job_id, line)
        code = proc.wait()
        stdout_text = "".join(lines)
        finish_job(
            job_id,
            {
                "ok": code == 0,
                "command": cmd,
                "stdout": stdout_text,
                "stderr": "",
                "output": output,
            },
        )
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


class Handler(BaseHTTPRequestHandler):
    def _json(self, payload, status=HTTPStatus.OK):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/":
            raw = HTML_PAGE.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        if self.path == "/status":
            self._json({"frontend": frontend_status(), "gateway": gateway_status()})
            return
        if self.path.startswith("/job/"):
            job_id = self.path.split("/job/", 1)[1].strip()
            with JOBS_LOCK:
                job = JOBS.get(job_id)
            if not job:
                self._json({"ok": False, "error": "Job not found"}, HTTPStatus.NOT_FOUND)
                return
            self._json({"ok": True, "done": job["done"], "log": job["log"], "result": job["result"]})
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self):
        if self.path != "/run":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        length = int(self.headers.get("Content-Length", "0"))
        data = json.loads(self.rfile.read(length).decode("utf-8"))
        urls = data.get("urls", "").strip()
        keyword = data.get("keyword", "").strip()
        keyword_sites = [item.strip() for item in data.get("keywordSites", []) if item.strip()]
        keyword_limit = str(data.get("keywordLimit", "10")).strip() or "10"
        output = data.get("output", str(DEFAULT_OUTPUT)).strip() or str(DEFAULT_OUTPUT)
        formats = [item.strip().lower() for item in data.get("formats", []) if item.strip()]

        if not urls and not keyword:
            self._json({"ok": False, "error": "No URLs or keyword provided"}, HTTPStatus.BAD_REQUEST)
            return

        tmp = tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt", encoding="utf-8", dir=UPLOAD_DIR)
        try:
            tmp.write(urls)
            tmp.close()
            cmd = [
                sys.executable,
                "-u",
                str(SCRAPER),
                "--input",
                tmp.name,
                "--output",
                output,
                "--formats",
                ",".join(formats),
            ]
            if keyword:
                cmd.extend(["--keyword", keyword, "--keyword-limit", keyword_limit])
                if keyword_sites:
                    cmd.extend(["--keyword-sites", ",".join(keyword_sites)])

            job_id = create_job(cmd, output)
            threading.Thread(target=run_job, args=(job_id, cmd, output, tmp.name), daemon=True).start()
            self._json({"ok": True, "jobId": job_id, "command": cmd, "output": output})
        finally:
            pass


def main():
    port = 8765
    with socketserver.ThreadingTCPServer(("127.0.0.1", port), Handler) as httpd:
        threading.Timer(0.6, lambda: webbrowser.open(f"http://127.0.0.1:{port}/")).start()
        print(f"Batch Lizard UI running at http://127.0.0.1:{port}/")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
