# Tizen `net-config` — Graphify Knowledge Graph

Generated from the Tizen open-source `net-config` component
(`https://github.com/tizenorg/platform.core.connectivity.net-config`, commit `35f06ac8`)
using **Graphify v0.8.17** with local tree-sitter AST extraction.

**Build cost:** 0 LLM tokens, ~3 seconds wall-clock, fully local.

---

## What's in this folder

| File | Size | Purpose |
|---|---|---|
| `graph.html` | 165 KB | **Interactive visualization** — open in any browser. Click nodes, filter, search by name. |
| `graph.json` | 158 KB | Raw graph data (NetworkX node-link format). Programmatic access. |
| `GRAPH_REPORT.md` | 8 KB | Auto-generated analysis: god nodes, communities, surprising connections, suggested questions. |
| `query_netconfig.py` | 7 KB | Custom Python helper for text queries against the graph. |

---

## Graph summary

```
170 nodes  ·  306 edges  ·  23 communities
Confidence breakdown:  238 EXTRACTED (78%)  ·  68 INFERRED (22%)
Relations:             164 calls  ·  139 contains  ·  3 imports
```

### The 10 most-connected ("god") nodes

| Function | Edges | File |
|---|---|---|
| `__netconfig_wifi_try_to_load_driver()` | 16 | `src/wifi-power.c` |
| `__netconfig_wifi_get_bytes_statistics()` | 12 | — |
| `__netconfig_wifi_try_to_remove_driver()` | 10 | `src/wifi-power.c` |
| `netconfig_wifi_update_power_state()` | 10 | `src/wifi-power.c` |
| `main()` | 9 | `src/main.c` |
| `netconfig_invoke_dbus_method()` | 9 | `src/dbus/netdbus.c` |
| `__netconfig_wifi_service_state_signal_handler()` | 8 | `src/signal-handler.c` |
| `__netconfig_signal_filter_handler()` | 8 | `src/signal-handler.c` |
| `netconfig_wifi_bgscan_start()` | 7 | `src/wifi-background-scan.c` |
| `netconfig_iface_wifi_load_driver()` | 6 | `src/wifi-power.c` |

### Architecture communities discovered

Leiden community detection grouped functions into 23 cohesive clusters. The biggest:

- **Community 0** (27 nodes) — Error handling + WiFi driver lifecycle bridge
- **Community 1** (23 nodes) — DBus plumbing + `main()` setup
- **Community 2** (22 nodes) — Network statistics (bytes counters, reset/get)
- **Community 3** (14 nodes) — Background scan (`bgscan`)
- **Community 4** (13 nodes) — WiFi signal / RSSI from wpa_supplicant
- **Community 5** (12 nodes) — WiFi notifications + favorites
- **Community 6** (12 nodes) — Emulator + driver load/remove
- **Community 7** (12 nodes) — Device picker + WiFi indicator
- **Community 8** (11 nodes) — SSID scan + BSS handling

---

## How to run text queries

### Option A — Graphify's built-in CLI (recommended)

Install Graphify, point at the folder, and ask:

```bash
pip install graphifyy

# from the folder containing graphify-out/
graphify query "how does the wifi driver get loaded"
graphify explain "__netconfig_wifi_try_to_load_driver"
graphify path "main" "netconfig_invoke_dbus_method"
```

### Option B — The included Python helper (no install needed)

```bash
# graph stats
python3 query_netconfig.py stats

# find any node by substring
python3 query_netconfig.py find "driver"
python3 query_netconfig.py find "ssid_scan"

# who calls this function?
python3 query_netconfig.py callers netconfig_invoke_dbus_method

# what does this function call?
python3 query_netconfig.py callees __netconfig_wifi_try_to_load_driver

# impact analysis — what breaks if I change X? (2-hop transitive callers)
python3 query_netconfig.py impact __netconfig_wifi_load_driver

# list everything in a community
python3 query_netconfig.py community 1
```

### Option C — Interactive viz

Just open `graph.html` in any browser. Click any node to see its neighbors,
use the search box to find functions, filter by community.

### Option D — Hook into Claude Code / Cursor via MCP

```bash
pip install "graphifyy[mcp]"
python -m graphify.serve graph.json
```

Then register the MCP server in your AI assistant's config. The assistant
gets these tools: `query_graph`, `get_node`, `get_neighbors`, `shortest_path`.

---

## Example query results

### "Path from `main()` to the DBus invoker"

```
$ graphify path "main" "netconfig_invoke_dbus_method"
Shortest path (3 hops):
  main() --calls [INFERRED]--> netconfig_setup_dbus()
        <--contains [EXTRACTED]-- netdbus.c
        --contains [EXTRACTED]--> netconfig_invoke_dbus_method()
```

### "What does `__netconfig_wifi_try_to_load_driver()` actually do?"

```
$ graphify explain "__netconfig_wifi_try_to_load_driver"
Source:    src/wifi-power.c L278
Community: 0
Degree:    16

Connections (16):
  --> __netconfig_wifi_try_to_remove_driver()   [EXTRACTED]
  --> netconfig_wifi_update_power_state()       [INFERRED]
  --> __netconfig_wifi_load_driver()            [EXTRACTED]
  --> netconfig_wifi_device_picker_service_start()  [INFERRED]
  --> __netconfig_wifi_enable_technology()      [EXTRACTED]
  --> netconfig_is_wifi_allowed()               [INFERRED]
  --> netconfig_is_wifi_tethering_on()          [INFERRED]
  --> netconfig_is_wifi_direct_on()             [INFERRED]
  --> __netconfig_wifi_direct_power_off()       [EXTRACTED]
  <-- netconfig_iface_wifi_load_driver()        [EXTRACTED]
  <-- __netconfig_wifi_airplane_mode()          [EXTRACTED]
  <-- __netconfig_wifi_power_configuration()    [EXTRACTED]
  <-- __netconfig_wifi_direct_state_cb()        [EXTRACTED]
```

**What this tells us:** before loading the driver, net-config checks airplane mode,
tethering, and Wi-Fi-direct state, then enables the connman technology, kicks off
the device picker service, and updates the power state. The same function is reached
from four entry points (the public load_driver iface, airplane mode toggle, power
config, and Wi-Fi-direct state change).

### "Impact: if I change `__netconfig_wifi_load_driver()`, what breaks?"

```
$ python3 query_netconfig.py impact __netconfig_wifi_load_driver

1-hop callers (1):
  • __netconfig_wifi_try_to_load_driver()  (src/wifi-power.c)

2-hop callers (4):
  • __netconfig_wifi_direct_state_cb()       (src/wifi-power.c)
  • __netconfig_wifi_airplane_mode()         (src/wifi-power.c)
  • __netconfig_wifi_power_configuration()   (src/wifi-power.c)
  • netconfig_iface_wifi_load_driver()       (src/wifi-power.c)

Affected communities: {0: 5}
```

---

## Surprising connections (the graph found these)

These cross-file relationships are often missed by grep:

- `main()` → `netconfig_network_state_create_and_init()`
  (`src/main.c` reaches into `src/network-state.c` during init)
- `__netconfig_wifi_ssid_scan()` → `netconfig_wifi_get_supplicant_interface()`
  (SSID scan crosses into `src/dbus/netsupplicant.c`)
- `__netconfig_signal_filter_handler()` → `netconfig_wifi_bss_added()`
  (DBus signal handler triggers the BSS-added scan callback)
- `netconfig_iface_wifi_launch_direct()` → `netconfig_error_wifi_direct_failed()`
  (Wi-Fi Direct launch wires up its own error reporter)

---

## Reproducing the build

```bash
git clone --depth 1 \
  https://github.com/tizenorg/platform.core.connectivity.net-config.git \
  tizen-netconfig

cd tizen-netconfig
pip install graphifyy
graphify update . --no-cluster   # AST extraction (no LLM)
graphify cluster-only .          # Leiden communities + HTML viz + report
```

Total time: ~3 seconds. Total LLM cost: $0.

For a richer graph including extracted "why" comments and design rationale,
set an `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` and run:

```bash
graphify extract . --backend claude
```

This adds semantic edges (LLM-extracted relationships) but costs API tokens.
