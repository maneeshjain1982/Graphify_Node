#!/usr/bin/env python3
"""
server.py - LLM-backed NL chat over the Tizen net-config knowledge graph.

Runs a tiny local HTTP server (Python stdlib only) that:
  - Serves chat.html and graph.json at /
  - Exposes POST /ask  -> forwards the question to Claude / Gemini / Gauss
                          with a compact graph context.
  - Exposes GET  /providers -> which providers are configured (have API keys)

No third-party Python packages required. Just set environment variables:

    # Claude (Anthropic)
    $env:ANTHROPIC_API_KEY = "sk-ant-..."

    # Gemini (Google AI Studio)
    $env:GEMINI_API_KEY = "AIza..."

    # Samsung Gauss (or any OpenAI-compatible endpoint)
    $env:GAUSS_API_KEY  = "..."
    $env:GAUSS_ENDPOINT = "https://your-gauss-host/v1/chat/completions"
    $env:GAUSS_MODEL    = "gauss-..."   # optional, defaults to 'gauss'

Then:
    py server.py
    # open http://localhost:8765/chat.html
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
import urllib.error
from collections import Counter, defaultdict
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

HERE = Path(__file__).parent
GRAPH_PATH = HERE / "graph.json"
PORT = int(os.environ.get("PORT", "8765"))

# ============================================================
# Graph
# ============================================================

def load_graph():
    if not GRAPH_PATH.exists():
        sys.exit(f"graph.json not found at {GRAPH_PATH}")
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

GRAPH = load_graph()
NODES = {n["id"]: n for n in GRAPH["nodes"]}
OUT = defaultdict(list)
IN = defaultdict(list)
for link in GRAPH["links"]:
    OUT[link["source"]].append((link["target"], link))
    IN[link["target"]].append((link["source"], link))


def compact_graph_context(max_edges_per_node=12):
    """
    Render the whole graph as a compact textual representation the LLM can
    reason about. ~10-20K tokens for a 170-node / 306-edge graph.
    """
    lines = []
    lines.append("# TIZEN NET-CONFIG CODE GRAPH (auto-extracted by Graphify)")
    lines.append(f"Nodes: {len(GRAPH['nodes'])}  Edges: {len(GRAPH['links'])}")
    rel = Counter(l["relation"] for l in GRAPH["links"])
    conf = Counter(l["confidence"] for l in GRAPH["links"])
    lines.append(f"Relations: {dict(rel)}   Confidence: {dict(conf)}")
    lines.append("")

    # Communities, ordered by size
    by_comm = defaultdict(list)
    for n in GRAPH["nodes"]:
        by_comm[n.get("community")].append(n)
    ordered = sorted(by_comm.items(), key=lambda x: -len(x[1]))

    for cid, members in ordered:
        files = [n for n in members if n.get("file_type") != "code"]
        code = [n for n in members if n.get("file_type") == "code"]
        lines.append(f"## Community {cid} ({len(members)} nodes)")
        if files:
            lines.append("Files: " + ", ".join(n["label"] for n in files))
        for n in code:
            loc = f"{n.get('source_file','?')}:{n.get('source_location','?')}"
            out_edges = OUT.get(n["id"], [])
            in_edges = IN.get(n["id"], [])
            calls = [NODES[t]["label"] for t, l in out_edges if l["relation"] == "calls"]
            called_by = [NODES[s]["label"] for s, l in in_edges if l["relation"] == "calls"]
            line = f"- {n['label']}  [{loc}]"
            if calls:
                shown = calls[:max_edges_per_node]
                more = f" (+{len(calls)-len(shown)})" if len(calls) > len(shown) else ""
                line += f"\n    calls: {', '.join(shown)}{more}"
            if called_by:
                shown = called_by[:max_edges_per_node]
                more = f" (+{len(called_by)-len(shown)})" if len(called_by) > len(shown) else ""
                line += f"\n    called by: {', '.join(shown)}{more}"
            lines.append(line)
        lines.append("")
    return "\n".join(lines)

GRAPH_CONTEXT = compact_graph_context()
print(f"[server] graph context: {len(GRAPH_CONTEXT)} chars (~{len(GRAPH_CONTEXT)//4} tokens)")


SYSTEM_PROMPT = """You are an expert assistant for the Tizen `net-config` codebase.
You answer questions by reasoning about a code-structure graph (functions, files,
call edges, communities) that the user provides as context.

Rules:
- Ground every claim in the graph data given to you. Cite function names and file paths.
- If the user asks about something not in the graph, say so explicitly — do not invent functions.
- Prefer concrete answers (file:line, exact function names) over generic prose.
- When asked "how does X work" or "how to do X", trace the actual call chains in the graph.
- Format function names in `backticks`. Keep answers crisp; bullets/short paragraphs.
- The graph was extracted from `net-config` (Tizen connectivity daemon). It sits on top
  of ConnMan and wpa_supplicant via D-Bus. If relevant context helps, mention it briefly.
- EXTRACTED edges came from AST parsing (high confidence). INFERRED edges are heuristic
  (lower confidence) — mention this when relevant.
"""


# ============================================================
# LLM providers
# ============================================================

def http_json(url, headers, payload, timeout=60):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} from {url}: {body[:500]}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error calling {url}: {e}") from None


def call_claude(question, history):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    messages = []
    for turn in history:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({
        "role": "user",
        "content": (
            f"Here is the code graph you must reason about:\n\n{GRAPH_CONTEXT}\n\n"
            f"---\nUser question: {question}"
        ),
    })
    payload = {
        "model": model,
        "max_tokens": 1500,
        "system": SYSTEM_PROMPT,
        "messages": messages,
    }
    resp = http_json(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        payload=payload,
    )
    parts = resp.get("content", [])
    return "".join(p.get("text", "") for p in parts if p.get("type") == "text")


def call_gemini(question, history):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set")
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    contents = []
    for turn in history:
        role = "user" if turn["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": turn["content"]}]})
    contents.append({
        "role": "user",
        "parts": [{"text":
            f"Here is the code graph you must reason about:\n\n{GRAPH_CONTEXT}\n\n"
            f"---\nUser question: {question}"
        }],
    })
    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 1500, "temperature": 0.2},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    resp = http_json(url, headers={"content-type": "application/json"}, payload=payload)
    cands = resp.get("candidates", [])
    if not cands:
        return f"(empty response from Gemini: {json.dumps(resp)[:400]})"
    parts = cands[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts)


def call_gauss(question, history):
    """
    Samsung Gauss / generic OpenAI-compatible endpoint.
    Configure with GAUSS_API_KEY, GAUSS_ENDPOINT, optionally GAUSS_MODEL.
    """
    key = os.environ.get("GAUSS_API_KEY")
    endpoint = os.environ.get("GAUSS_ENDPOINT")
    if not key or not endpoint:
        raise RuntimeError("GAUSS_API_KEY and GAUSS_ENDPOINT must be set")
    model = os.environ.get("GAUSS_MODEL", "gauss")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in history:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({
        "role": "user",
        "content": (
            f"Here is the code graph you must reason about:\n\n{GRAPH_CONTEXT}\n\n"
            f"---\nUser question: {question}"
        ),
    })
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 1500,
        "temperature": 0.2,
    }
    resp = http_json(
        endpoint,
        headers={"authorization": f"Bearer {key}", "content-type": "application/json"},
        payload=payload,
    )
    # OpenAI-style response
    choices = resp.get("choices", [])
    if not choices:
        return f"(empty response from Gauss: {json.dumps(resp)[:400]})"
    msg = choices[0].get("message", {})
    return msg.get("content", "")


PROVIDERS = {
    "claude": call_claude,
    "gemini": call_gemini,
    "gauss": call_gauss,
}


def available_providers():
    out = {}
    out["claude"] = bool(os.environ.get("ANTHROPIC_API_KEY"))
    out["gemini"] = bool(os.environ.get("GEMINI_API_KEY"))
    out["gauss"] = bool(os.environ.get("GAUSS_API_KEY") and os.environ.get("GAUSS_ENDPOINT"))
    return out


# ============================================================
# HTTP handler
# ============================================================

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(HERE), **kw)

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[server] {self.address_string()} {fmt % args}\n")

    def _json(self, status, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "content-type")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "content-type")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.end_headers()

    def do_GET(self):
        if self.path == "/providers":
            return self._json(200, {"providers": available_providers()})
        if self.path == "/" or self.path == "":
            self.path = "/chat.html"
        return super().do_GET()

    def do_POST(self):
        if self.path != "/ask":
            return self._json(404, {"error": "not found"})

        length = int(self.headers.get("Content-Length", "0"))
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            return self._json(400, {"error": "invalid json"})

        provider = (body.get("provider") or "").lower().strip()
        question = (body.get("question") or "").strip()
        history = body.get("history") or []
        if provider not in PROVIDERS:
            return self._json(400, {"error": f"unknown provider '{provider}'. Use one of: {list(PROVIDERS)}"})
        if not question:
            return self._json(400, {"error": "empty question"})

        try:
            answer = PROVIDERS[provider](question, history)
            return self._json(200, {"answer": answer, "provider": provider})
        except RuntimeError as e:
            return self._json(502, {"error": str(e)})
        except Exception as e:
            return self._json(500, {"error": f"{type(e).__name__}: {e}"})


def main():
    avail = available_providers()
    print(f"[server] providers available: {[k for k,v in avail.items() if v] or '(none — set API keys!)'}")
    print(f"[server] listening on http://localhost:{PORT}")
    print(f"[server] open    http://localhost:{PORT}/chat.html")
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[server] bye.")


if __name__ == "__main__":
    main()
