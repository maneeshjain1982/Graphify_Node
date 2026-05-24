#!/usr/bin/env python3
"""
query_netconfig.py — text query helper for the Tizen net-config Graphify graph

Usage:
    python query_netconfig.py find "wifi driver"
    python query_netconfig.py callers __netconfig_wifi_load_driver
    python query_netconfig.py callees __netconfig_wifi_try_to_load_driver
    python query_netconfig.py impact bundle_add_str       # what breaks if X changes
    python query_netconfig.py community 0                 # list a community
    python query_netconfig.py stats                       # overall graph stats
"""
import json
import sys
from collections import defaultdict, Counter
from pathlib import Path

GRAPH_PATH = Path(__file__).parent / "graphify-out" / "graph.json"


def load_graph():
    with open(GRAPH_PATH) as f:
        return json.load(f)


def index_graph(g):
    nodes = {n["id"]: n for n in g["nodes"]}
    out_edges = defaultdict(list)   # source -> [(target, link)]
    in_edges = defaultdict(list)    # target -> [(source, link)]
    for link in g["links"]:
        out_edges[link["source"]].append((link["target"], link))
        in_edges[link["target"]].append((link["source"], link))
    return nodes, out_edges, in_edges


def find_node(nodes, query):
    """Substring search across labels (case-insensitive)."""
    q = query.lower()
    hits = [n for n in nodes.values() if q in n["label"].lower()]
    return sorted(hits, key=lambda n: len(n["label"]))


def cmd_find(g, query):
    nodes, _, _ = index_graph(g)
    hits = find_node(nodes, query)
    print(f"Found {len(hits)} node(s) matching '{query}':\n")
    for n in hits[:25]:
        loc = f"{n.get('source_file', '?')}:{n.get('source_location', '?')}"
        print(f"  • {n['label']:60s}  community={n.get('community','?'):>3}  ({loc})")
    if len(hits) > 25:
        print(f"  ... and {len(hits)-25} more")


def cmd_callers(g, name):
    nodes, _, in_edges = index_graph(g)
    hits = [n for n in nodes.values() if name.lower() in n["label"].lower()
            and n.get("file_type") == "code"]
    if not hits:
        print(f"No code node matches '{name}'")
        return
    n = hits[0]
    print(f"Callers of {n['label']}  ({n['source_file']}:{n['source_location']}):\n")
    callers = [(s, l) for s, l in in_edges[n["id"]] if l["relation"] == "calls"]
    if not callers:
        print("  (no callers found)")
        return
    for src_id, link in callers:
        src = nodes[src_id]
        conf = link["confidence"]
        print(f"  <-- {src['label']:55s} [{conf}]  ({src.get('source_file', '?')})")


def cmd_callees(g, name):
    nodes, out_edges, _ = index_graph(g)
    hits = [n for n in nodes.values() if name.lower() in n["label"].lower()
            and n.get("file_type") == "code"]
    if not hits:
        print(f"No code node matches '{name}'")
        return
    n = hits[0]
    print(f"Callees of {n['label']}  ({n['source_file']}:{n['source_location']}):\n")
    callees = [(t, l) for t, l in out_edges[n["id"]] if l["relation"] == "calls"]
    if not callees:
        print("  (no outgoing calls)")
        return
    for tgt_id, link in callees:
        tgt = nodes[tgt_id]
        conf = link["confidence"]
        print(f"  --> {tgt['label']:55s} [{conf}]  ({tgt.get('source_file', '?')})")


def cmd_impact(g, name, hops=2):
    """Transitive callers up to `hops` levels."""
    nodes, _, in_edges = index_graph(g)
    hits = [n for n in nodes.values() if name.lower() in n["label"].lower()]
    if not hits:
        print(f"No node matches '{name}'")
        return
    n = hits[0]
    print(f"Impact analysis: what breaks if {n['label']} changes?\n")

    visited = {n["id"]: 0}
    frontier = [n["id"]]
    for depth in range(1, hops + 1):
        next_frontier = []
        for nid in frontier:
            for src_id, link in in_edges[nid]:
                if link["relation"] != "calls":
                    continue
                if src_id not in visited:
                    visited[src_id] = depth
                    next_frontier.append(src_id)
        frontier = next_frontier

    by_depth = defaultdict(list)
    for nid, d in visited.items():
        if d > 0:
            by_depth[d].append(nodes[nid])

    for d in sorted(by_depth):
        print(f"  {d}-hop callers ({len(by_depth[d])}):")
        for x in by_depth[d]:
            print(f"    • {x['label']:55s}  ({x.get('source_file', '?')})")
        print()
    affected_communities = Counter(nodes[nid].get("community")
                                    for nid in visited if nid != n["id"])
    print(f"Affected communities: {dict(affected_communities)}")


def cmd_community(g, comm_id):
    comm_id = int(comm_id)
    members = [n for n in g["nodes"] if n.get("community") == comm_id]
    print(f"Community {comm_id} — {len(members)} nodes:\n")
    code_nodes = [n for n in members if n.get("file_type") == "code"]
    file_nodes = [n for n in members if n.get("file_type") != "code"]
    if file_nodes:
        print("  Files:")
        for n in file_nodes:
            print(f"    • {n['label']}")
        print()
    if code_nodes:
        print("  Functions:")
        for n in code_nodes:
            print(f"    • {n['label']}  ({n['source_file']}:{n['source_location']})")


def cmd_stats(g):
    print(f"Nodes:     {len(g['nodes'])}")
    print(f"Links:     {len(g['links'])}")
    print(f"Commit:    {g.get('built_at_commit', '?')}")
    print()
    conf = Counter(l['confidence'] for l in g['links'])
    rel = Counter(l['relation'] for l in g['links'])
    comm = Counter(n.get('community') for n in g['nodes'])
    print("Confidence:", dict(conf))
    print("Relations: ", dict(rel))
    print(f"Communities: {len(comm)} total")
    print()
    print("Top 5 most-connected nodes (god nodes):")
    degree = Counter()
    for l in g['links']:
        degree[l['source']] += 1
        degree[l['target']] += 1
    nodes = {n['id']: n for n in g['nodes']}
    for nid, d in degree.most_common(10):
        n = nodes[nid]
        if n.get('file_type') == 'code':
            print(f"  • {n['label']:55s} {d:3d} edges")


COMMANDS = {
    "find": cmd_find,
    "callers": cmd_callers,
    "callees": cmd_callees,
    "impact": cmd_impact,
    "community": cmd_community,
    "stats": lambda g, *args: cmd_stats(g),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    g = load_graph()
    COMMANDS[sys.argv[1]](g, *sys.argv[2:])


if __name__ == "__main__":
    main()
