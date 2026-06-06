from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlparse

from .config import DATA_DIR, get_settings
from .evaluation import run_evaluation
from .graph import FinanceAutomationGraph


class AgentAPI(BaseHTTPRequestHandler):
    server_version = "FinanceAgentAPI/0.1"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._html(INDEX_HTML)
            return
        if path == "/health":
            self._json({"status": "ok"})
            return
        self._json({"error": "not found"}, status=404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        body = self._read_json()
        settings = get_settings()
        graph = FinanceAutomationGraph(settings)
        if path == "/run/bank":
            input_path = body.get("path") or str(DATA_DIR / "sample_bank_statement.txt")
            self._json(graph.run_bank_statement(Path(input_path)).to_dict())
        elif path == "/run/regulatory":
            input_path = body.get("path") or str(DATA_DIR / "sample_regulatory_news.json")
            self._json(graph.run_regulatory_digest(Path(input_path)).to_dict())
        elif path == "/run/demo":
            self._json(run_evaluation(settings))
        else:
            self._json({"error": "not found"}, status=404)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _json(self, payload: dict, status: int = 200) -> None:
        raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _html(self, html: str, status: int = 200) -> None:
        raw = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main() -> int:
    settings = get_settings()
    server = ThreadingHTTPServer((settings.app_host, settings.app_port), AgentAPI)
    print(f"API server running at http://{settings.app_host}:{settings.app_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


INDEX_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Finance Agent Console</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #17202a;
      --muted: #536271;
      --line: #d7dde3;
      --panel: #ffffff;
      --bg: #f6f8fa;
      --green: #1b7f5a;
      --blue: #2764b5;
      --red: #b83a3a;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, "Segoe UI", Arial, sans-serif;
      background: var(--bg);
      color: var(--ink);
    }
    header {
      padding: 22px 28px;
      border-bottom: 1px solid var(--line);
      background: #fff;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
    }
    h1 { font-size: 22px; margin: 0; letter-spacing: 0; }
    main {
      max-width: 1180px;
      margin: 0 auto;
      padding: 24px;
      display: grid;
      grid-template-columns: 320px 1fr;
      gap: 20px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }
    .actions { display: grid; gap: 10px; }
    button {
      width: 100%;
      min-height: 42px;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
      border-radius: 6px;
      cursor: pointer;
      font-size: 14px;
      text-align: left;
      padding: 10px 12px;
    }
    button:hover { border-color: var(--blue); color: var(--blue); }
    .status {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      color: var(--green);
      font-size: 14px;
    }
    .dot {
      width: 9px;
      height: 9px;
      border-radius: 50%;
      background: var(--green);
      display: inline-block;
    }
    pre {
      margin: 0;
      min-height: 520px;
      overflow: auto;
      white-space: pre-wrap;
      font-size: 13px;
      line-height: 1.5;
    }
    .muted { color: var(--muted); font-size: 13px; line-height: 1.5; }
    @media (max-width: 820px) {
      main { grid-template-columns: 1fr; padding: 14px; }
      header { align-items: flex-start; flex-direction: column; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Finance Agent Console</h1>
    <div class="status"><span class="dot"></span><span>API online</span></div>
  </header>
  <main>
    <section class="panel">
      <div class="actions">
        <button onclick="run('/run/bank')">Run Bank Statement Agent</button>
        <button onclick="run('/run/regulatory')">Run Regulatory Digest Agent</button>
        <button onclick="run('/run/demo')">Run Full Benchmark</button>
      </div>
      <p class="muted">Artifacts are written to the local outputs directory. The backend uses local deterministic logic unless OPENAI_API_KEY is configured.</p>
    </section>
    <section class="panel">
      <pre id="output">Ready.</pre>
    </section>
  </main>
  <script>
    async function run(path) {
      const output = document.getElementById('output');
      output.textContent = 'Running ' + path + ' ...';
      try {
        const res = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
        const data = await res.json();
        output.textContent = JSON.stringify(data, null, 2);
      } catch (error) {
        output.textContent = String(error);
      }
    }
  </script>
</body>
</html>"""
