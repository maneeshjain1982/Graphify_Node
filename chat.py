#!/usr/bin/env python3
"""
chat.py - interactive natural-language chat over the Tizen net-config knowledge graph.

Run:
    python chat.py

Then type questions like:
    > what does main do?
    > who calls netconfig_invoke_dbus_method?
    > what does __netconfig_wifi_try_to_load_driver call?
    > path from main to netconfig_invoke_dbus_method
    > impact of changing __netconfig_wifi_load_driver
    > find driver
    > show community 1
    > stats
    > god nodes
    > help / quit
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

HERE = Path(__file__).parent
GRAPH_PATH = HERE / "graph.json"

# ---------- graph loading & indexing ----------

def load_graph():
    if not GRAPH_PATH.exists():
        print(f"graph.json not found at {GRAPH_PATH}")
        sys.exit(1)
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def index_graph(g):
    nodes = {n["id"]: n for n in g["nodes"]}
    out_edges = defaultdict(list)
    in_edges = defaultdict(list)
    for link in g["links"]:
        out_edges[link["source"]].append((link["target"], link))
        in_edges[link["target"]].append((link["source"], link))
    return nodes, out_edges, in_edges


def find_nodes(nodes, query, code_only=False):
    q = query.lower().strip().strip("`'\"").rstrip("()")
    hits = []
    for n in nodes.values():
        if code_only and n.get("file_type") != "code":
            continue
        label = n["label"].lower()
        if q == label.rstrip("()") or q in label:
            hits.append(n)
    # Prefer exact-ish matches: shorter labels first, then exact substring start.
    hits.sort(key=lambda n: (q != n["label"].lower().rstrip("()"), len(n["label"])))
    return hits


def pick_one(nodes_list, query):
    if not nodes_list:
        return None
    if len(nodes_list) == 1:
        return nodes_list[0]
    # If multiple, prefer the shortest label that contains query
    return nodes_list[0]


# ---------- answer renderers ----------

def fmt_node(n):
    loc = f"{n.get('source_file','?')}:{n.get('source_location','?')}"
    return f"{n['label']}  ({loc})"


def answer_find(g, query):
    nodes, _, _ = index_graph(g)
    hits = find_nodes(nodes, query)
    if not hits:
        return f"No nodes match '{query}'."
    out = [f"Found {len(hits)} node(s) matching '{query}':"]
    for n in hits[:20]:
        out.append(f"  - {fmt_node(n)}  [community {n.get('community','?')}]")
    if len(hits) > 20:
        out.append(f"  ... and {len(hits)-20} more.")
    return "\n".join(out)


def answer_callers(g, query):
    nodes, _, in_edges = index_graph(g)
    hits = find_nodes(nodes, query, code_only=True)
    n = pick_one(hits, query)
    if not n:
        return f"No code node matches '{query}'."
    callers = [(s, l) for s, l in in_edges[n["id"]] if l["relation"] == "calls"]
    header = f"Callers of {fmt_node(n)}:"
    if not callers:
        return header + "\n  (no callers found in the graph)"
    lines = [header]
    for src_id, link in callers:
        src = nodes[src_id]
        lines.append(f"  <-- {src['label']}  [{link['confidence']}]  ({src.get('source_file','?')})")
    return "\n".join(lines)


def answer_callees(g, query):
    nodes, out_edges, _ = index_graph(g)
    hits = find_nodes(nodes, query, code_only=True)
    n = pick_one(hits, query)
    if not n:
        return f"No code node matches '{query}'."
    callees = [(t, l) for t, l in out_edges[n["id"]] if l["relation"] == "calls"]
    header = f"{fmt_node(n)} calls:"
    if not callees:
        return header + "\n  (no outgoing calls)"
    lines = [header]
    for tgt_id, link in callees:
        tgt = nodes[tgt_id]
        lines.append(f"  --> {tgt['label']}  [{link['confidence']}]  ({tgt.get('source_file','?')})")
    return "\n".join(lines)


def answer_explain(g, query):
    nodes, out_edges, in_edges = index_graph(g)
    hits = find_nodes(nodes, query, code_only=True)
    n = pick_one(hits, query)
    if not n:
        return f"No code node matches '{query}'."
    out_links = out_edges[n["id"]]
    in_links = in_edges[n["id"]]
    degree = len(out_links) + len(in_links)
    lines = [
        f"{n['label']}",
        f"  Source:    {n.get('source_file','?')} {n.get('source_location','')}",
        f"  Community: {n.get('community','?')}",
        f"  Degree:    {degree}  ({len(out_links)} out, {len(in_links)} in)",
        "",
        "  Connections:",
    ]
    for tgt_id, link in out_links:
        tgt = nodes[tgt_id]
        lines.append(f"    --> {tgt['label']}  [{link['relation']}/{link['confidence']}]")
    for src_id, link in in_links:
        src = nodes[src_id]
        lines.append(f"    <-- {src['label']}  [{link['relation']}/{link['confidence']}]")
    return "\n".join(lines)


def answer_path(g, src_query, dst_query):
    nodes, out_edges, in_edges = index_graph(g)
    a = pick_one(find_nodes(nodes, src_query, code_only=True), src_query)
    b = pick_one(find_nodes(nodes, dst_query, code_only=True), dst_query)
    if not a:
        return f"No code node matches source '{src_query}'."
    if not b:
        return f"No code node matches target '{dst_query}'."

    # Undirected BFS using both incoming and outgoing edges.
    visited = {a["id"]: None}
    edge_used = {}  # node_id -> link that brought us here, plus direction
    q = deque([a["id"]])
    found = False
    while q:
        cur = q.popleft()
        if cur == b["id"]:
            found = True
            break
        for tgt, link in out_edges[cur]:
            if tgt not in visited:
                visited[tgt] = cur
                edge_used[tgt] = (link, "out")
                q.append(tgt)
        for src, link in in_edges[cur]:
            if src not in visited:
                visited[src] = cur
                edge_used[src] = (link, "in")
                q.append(src)
    if not found:
        return f"No path found between {a['label']} and {b['label']}."

    # Reconstruct
    path = []
    cur = b["id"]
    while cur is not None:
        path.append(cur)
        cur = visited[cur]
    path.reverse()

    lines = [f"Shortest path ({len(path)-1} hops): {a['label']}  ->  {b['label']}"]
    for i in range(1, len(path)):
        prev_id, nid = path[i-1], path[i]
        link, direction = edge_used[nid]
        arrow = "--" + link["relation"] + "-->" if direction == "out" else "<--" + link["relation"] + "--"
        lines.append(f"  {nodes[prev_id]['label']}  {arrow}  {nodes[nid]['label']}  [{link['confidence']}]")
    return "\n".join(lines)


def answer_impact(g, query, hops=2):
    nodes, _, in_edges = index_graph(g)
    n = pick_one(find_nodes(nodes, query, code_only=True), query)
    if not n:
        return f"No code node matches '{query}'."
    visited = {n["id"]: 0}
    frontier = [n["id"]]
    for depth in range(1, hops + 1):
        nxt = []
        for nid in frontier:
            for src_id, link in in_edges[nid]:
                if link["relation"] != "calls":
                    continue
                if src_id not in visited:
                    visited[src_id] = depth
                    nxt.append(src_id)
        frontier = nxt
    by_depth = defaultdict(list)
    for nid, d in visited.items():
        if d > 0:
            by_depth[d].append(nodes[nid])

    lines = [f"Impact analysis - what breaks if {n['label']} changes?"]
    if not by_depth:
        lines.append("  (no transitive callers found)")
    for d in sorted(by_depth):
        lines.append(f"  {d}-hop callers ({len(by_depth[d])}):")
        for x in by_depth[d]:
            lines.append(f"    - {x['label']}  ({x.get('source_file','?')})")
    communities = Counter(nodes[nid].get("community") for nid in visited if nid != n["id"])
    if communities:
        lines.append(f"  Affected communities: {dict(communities)}")
    return "\n".join(lines)


def answer_community(g, comm_id):
    try:
        comm_id = int(comm_id)
    except ValueError:
        return f"Community id must be a number, got '{comm_id}'."
    members = [n for n in g["nodes"] if n.get("community") == comm_id]
    if not members:
        return f"No nodes found in community {comm_id}."
    code_nodes = [n for n in members if n.get("file_type") == "code"]
    file_nodes = [n for n in members if n.get("file_type") != "code"]
    lines = [f"Community {comm_id} - {len(members)} nodes"]
    if file_nodes:
        lines.append("  Files:")
        for n in file_nodes:
            lines.append(f"    - {n['label']}")
    if code_nodes:
        lines.append("  Functions:")
        for n in code_nodes[:50]:
            lines.append(f"    - {n['label']}  ({n.get('source_file','?')}:{n.get('source_location','?')})")
        if len(code_nodes) > 50:
            lines.append(f"    ... and {len(code_nodes)-50} more.")
    return "\n".join(lines)


def answer_stats(g):
    rel = Counter(l["relation"] for l in g["links"])
    conf = Counter(l["confidence"] for l in g["links"])
    comm = Counter(n.get("community") for n in g["nodes"])
    lines = [
        f"Nodes:        {len(g['nodes'])}",
        f"Links:        {len(g['links'])}",
        f"Communities:  {len(comm)}",
        f"Relations:    {dict(rel)}",
        f"Confidence:   {dict(conf)}",
    ]
    return "\n".join(lines)


def answer_god_nodes(g, top=10):
    degree = Counter()
    for l in g["links"]:
        degree[l["source"]] += 1
        degree[l["target"]] += 1
    nodes = {n["id"]: n for n in g["nodes"]}
    lines = [f"Top {top} most-connected nodes:"]
    shown = 0
    for nid, d in degree.most_common():
        n = nodes[nid]
        if n.get("file_type") != "code":
            continue
        lines.append(f"  - {n['label']:55s}  {d:3d} edges  ({n.get('source_file','?')})")
        shown += 1
        if shown >= top:
            break
    return "\n".join(lines)


def answer_help():
    return (
        "Ask me anything about the Tizen net-config graph. Examples:\n"
        "  - find <keyword>            (or: search for X)\n"
        "  - who calls <function>      (or: callers of X)\n"
        "  - what does <function> call (or: callees of X)\n"
        "  - explain <function>        (or: what does X do, tell me about X)\n"
        "  - path from <A> to <B>\n"
        "  - impact of <function>      (or: what breaks if X changes)\n"
        "  - community <n>             (or: show community 3)\n"
        "  - stats                     (or: how big is the graph)\n"
        "  - god nodes                 (most connected functions)\n"
        "  - help, quit"
    )


# ---------- NL intent routing ----------

INTENT_PATTERNS = [
    # path A to B
    ("path", re.compile(r"^(?:show\s+)?(?:the\s+)?(?:shortest\s+)?path\s+(?:from\s+)?(?P<a>.+?)\s+(?:to|->|=>)\s+(?P<b>.+?)\s*\??$", re.I)),
    ("path", re.compile(r"^how\s+(?:does|do|can)\s+(?P<a>.+?)\s+(?:reach|get\s+to|connect\s+to)\s+(?P<b>.+?)\s*\??$", re.I)),

    # impact
    ("impact", re.compile(r"^(?:impact|blast\s*radius)\s+(?:of|for)\s+(?:changing\s+)?(?P<x>.+?)\s*\??$", re.I)),
    ("impact", re.compile(r"^what\s+(?:breaks|would\s+break|happens)\s+if\s+(?:i\s+)?(?:change|modify|edit|touch|refactor)\s+(?P<x>.+?)\s*\??$", re.I)),

    # callers
    ("callers", re.compile(r"^(?:who|what)\s+calls\s+(?:into\s+)?(?P<x>.+?)\s*\??$", re.I)),
    ("callers", re.compile(r"^callers\s+(?:of|for)\s+(?P<x>.+?)\s*\??$", re.I)),
    ("callers", re.compile(r"^(?:list|show|find)\s+callers\s+(?:of\s+)?(?P<x>.+?)\s*\??$", re.I)),

    # callees
    ("callees", re.compile(r"^what\s+does\s+(?P<x>.+?)\s+call\s*\??$", re.I)),
    ("callees", re.compile(r"^callees\s+(?:of|for)\s+(?P<x>.+?)\s*\??$", re.I)),
    ("callees", re.compile(r"^(?:list|show|find)\s+callees\s+(?:of\s+)?(?P<x>.+?)\s*\??$", re.I)),

    # explain
    ("explain", re.compile(r"^(?:explain|describe|tell\s+me\s+about)\s+(?P<x>.+?)\s*\??$", re.I)),
    ("explain", re.compile(r"^what\s+does\s+(?P<x>.+?)\s+do\s*\??$", re.I)),
    ("explain", re.compile(r"^(?:show|info|details)\s+(?:on|for|about)\s+(?P<x>.+?)\s*\??$", re.I)),

    # community
    ("community", re.compile(r"^(?:show\s+|list\s+|what(?:'s|\s+is)\s+in\s+)?community\s+(?P<x>\d+)\s*\??$", re.I)),

    # find
    ("find", re.compile(r"^(?:find|search(?:\s+for)?|look\s+(?:up|for))\s+(?P<x>.+?)\s*\??$", re.I)),
    ("find", re.compile(r"^(?:any|which|what)\s+(?:nodes?|functions?|files?)\s+(?:match|contain|have)\s+(?P<x>.+?)\s*\??$", re.I)),

    # god nodes / stats / help / quit
    ("god", re.compile(r"^(?:god\s+nodes|most\s+connected|hubs|hottest\s+(?:functions|nodes))\s*\??$", re.I)),
    ("stats", re.compile(r"^(?:stats|statistics|summary|overview|how\s+big\s+is\s+the\s+graph)\s*\??$", re.I)),
    ("help", re.compile(r"^(?:help|\?|commands|what\s+can\s+(?:you|i)\s+do)\s*\??$", re.I)),
    ("quit", re.compile(r"^(?:quit|exit|bye|q)\s*\??$", re.I)),
]


def route(question, g):
    q = question.strip()
    if not q:
        return None
    for intent, pat in INTENT_PATTERNS:
        m = pat.match(q)
        if not m:
            continue
        if intent == "path":
            return answer_path(g, m.group("a"), m.group("b"))
        if intent == "impact":
            return answer_impact(g, m.group("x"))
        if intent == "callers":
            return answer_callers(g, m.group("x"))
        if intent == "callees":
            return answer_callees(g, m.group("x"))
        if intent == "explain":
            return answer_explain(g, m.group("x"))
        if intent == "community":
            return answer_community(g, m.group("x"))
        if intent == "find":
            return answer_find(g, m.group("x"))
        if intent == "god":
            return answer_god_nodes(g)
        if intent == "stats":
            return answer_stats(g)
        if intent == "help":
            return answer_help()
        if intent == "quit":
            return "__QUIT__"

    # Fallback: treat the whole question as a substring search if it looks like an identifier.
    if re.search(r"[A-Za-z_]{3,}", q):
        return answer_find(g, q) + "\n\n(Try 'help' to see the supported question shapes.)"
    return "I didn't understand that. Type 'help' for examples."


# ---------- REPL ----------

def main():
    g = load_graph()
    nodes_count = len(g["nodes"])
    links_count = len(g["links"])
    print("=" * 64)
    print(f" Graphify NL chat - Tizen net-config")
    print(f" {nodes_count} nodes, {links_count} links loaded from graph.json")
    print(" Type a question in plain English. 'help' for examples, 'quit' to exit.")
    print("=" * 64)

    # Allow a one-shot query via CLI args.
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        result = route(question, g)
        if result and result != "__QUIT__":
            print(result)
        return

    while True:
        try:
            question = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question:
            continue
        result = route(question, g)
        if result == "__QUIT__":
            print("bye.")
            break
        print()
        print(result if result is not None else "")


if __name__ == "__main__":
    main()
