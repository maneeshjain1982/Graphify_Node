# Graph Report - .  (2026-05-24)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 170 nodes · 306 edges · 23 communities
- Extraction: 78% EXTRACTED · 22% INFERRED · 0% AMBIGUOUS · INFERRED: 68 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `35f06ac8`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]

## God Nodes (most connected - your core abstractions)
1. `__netconfig_wifi_try_to_load_driver()` - 16 edges
2. `__netconfig_wifi_get_bytes_statistics()` - 12 edges
3. `__netconfig_wifi_try_to_remove_driver()` - 10 edges
4. `netconfig_wifi_update_power_state()` - 10 edges
5. `main()` - 9 edges
6. `netconfig_invoke_dbus_method()` - 9 edges
7. `__netconfig_wifi_service_state_signal_handler()` - 8 edges
8. `__netconfig_signal_filter_handler()` - 8 edges
9. `netconfig_wifi_bgscan_start()` - 7 edges
10. `netconfig_iface_wifi_load_driver()` - 6 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `netconfig_network_state_create_and_init()`  [INFERRED]
  src/main.c → src/network-state.c
- `__netconfig_wifi_ssid_scan()` --calls--> `netconfig_wifi_get_supplicant_interface()`  [INFERRED]
  src/wifi-ssid-scan.c → src/dbus/netsupplicant.c
- `__netconfig_signal_filter_handler()` --calls--> `netconfig_wifi_get_ssid_scan_state()`  [INFERRED]
  src/signal-handler.c → src/wifi-ssid-scan.c
- `__netconfig_signal_filter_handler()` --calls--> `netconfig_wifi_bss_added()`  [INFERRED]
  src/signal-handler.c → src/wifi-ssid-scan.c
- `netconfig_iface_wifi_launch_direct()` --calls--> `netconfig_error_wifi_direct_failed()`  [INFERRED]
  src/utils/util.c → src/neterror.c

## Communities (23 total, 0 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.13
Nodes (20): netconfig_error_quark(), netconfig_error_security_restricted(), netconfig_error_wifi_direct_failed(), netconfig_error_wifi_driver_failed(), netconfig_wifi_statistics_update_powered_off(), netconfig_iface_wifi_load_driver(), netconfig_iface_wifi_remove_driver(), __netconfig_wifi_airplane_mode() (+12 more)

### Community 1 - "Community 1"
Cohesion: 0.13
Nodes (19): __netconfig_dbus_append_param(), netconfig_dbus_get_string(), netconfig_invoke_dbus_method(), netconfig_setup_dbus(), netconfig_wifi_get_connected_service_name(), main(), netconfig_deregister_signal(), __netconfig_get_property() (+11 more)

### Community 2 - "Community 2"
Cohesion: 0.15
Nodes (13): netconfig_iface_network_statistics_get_wifi_last_rx_bytes(), netconfig_iface_network_statistics_get_wifi_last_tx_bytes(), netconfig_iface_network_statistics_get_wifi_total_rx_bytes(), netconfig_iface_network_statistics_get_wifi_total_tx_bytes(), netconfig_iface_network_statistics_reset_wifi_last_rx_bytes(), netconfig_iface_network_statistics_reset_wifi_last_tx_bytes(), netconfig_iface_network_statistics_reset_wifi_total_rx_bytes(), netconfig_iface_network_statistics_reset_wifi_total_tx_bytes() (+5 more)

### Community 3 - "Community 3"
Cohesion: 0.34
Nodes (13): netconfig_iface_wifi_set_bgscan(), __netconfig_wifi_bgscan_get_bgscan_data(), __netconfig_wifi_bgscan_get_mode(), __netconfig_wifi_bgscan_mode(), __netconfig_wifi_bgscan_request_connman_scan(), __netconfig_wifi_bgscan_request_scan(), __netconfig_wifi_bgscan_set_mode(), netconfig_wifi_bgscan_start() (+5 more)

### Community 4 - "Community 4"
Cohesion: 0.31
Nodes (10): netconfig_supplicant_invoke_dbus_method(), netconfig_wifi_get_ifname(), netconfig_wifi_get_supplicant_interface(), setup_input_args(), netconfig_wifi_get_rssi(), __netconfig_wifi_get_rssi_from_supplicant(), __netconfig_wifi_get_rssi_from_system(), __netconfig_wifi_get_signal() (+2 more)

### Community 5 - "Community 5"
Cohesion: 0.27
Nodes (10): __netconfig_wifi_add_network_notification(), netconfig_wifi_check_network_notification(), __netconfig_wifi_del_network_notification(), __netconfig_wifi_get_connman_favorite_service(), netconfig_wifi_get_favorite_service(), __netconfig_wifi_get_profiles_count(), __netconfig_wifi_set_profiles_count(), __netconfig_wifi_state_changed() (+2 more)

### Community 6 - "Community 6"
Cohesion: 0.26
Nodes (11): __netconfig_wifi_load_driver(), __netconfig_wifi_remove_driver(), __netconfig_emulator_config_emul_env(), netconfig_emulator_is_emulated(), __netconfig_emulator_set_ip(), __netconfig_emulator_set_network_state(), __netconfig_emulator_set_proxy(), netconfig_emulator_test_and_start() (+3 more)

### Community 7 - "Community 7"
Cohesion: 0.29
Nodes (11): netconfig_wifi_indicator_start(), __netconfig_pop_device_picker(), netconfig_start_timer(), netconfig_start_timer_seconds(), __netconfig_test_device_picker(), __netconfig_wifi_device_picker_get_timer_id(), netconfig_wifi_device_picker_service_start(), netconfig_wifi_device_picker_service_stop() (+3 more)

### Community 8 - "Community 8"
Cohesion: 0.33
Nodes (10): netconfig_iface_wifi_request_specific_scan(), netconfig_wifi_bss_added(), __netconfig_wifi_check_security(), netconfig_wifi_get_ssid_scan_state(), __netconfig_wifi_invoke_ssid_scan(), __netconfig_wifi_notify_ssid_scan_done(), __netconfig_wifi_parse_keymgmt_message(), __netconfig_wifi_ssid_scan() (+2 more)

### Community 9 - "Community 9"
Cohesion: 0.29
Nodes (3): netconfig_iface_network_state_update_default_connection_info(), netconfig_network_state_create_and_init(), __netconfig_pop_3g_alert_syspoppup()

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `main()` connect `Community 1` to `Community 0`, `Community 9`, `Community 2`, `Community 6`?**
  _High betweenness centrality (0.138) - this node is a cross-community bridge._
- **Why does `__netconfig_wifi_try_to_remove_driver()` connect `Community 0` to `Community 1`, `Community 6`, `Community 7`?**
  _High betweenness centrality (0.129) - this node is a cross-community bridge._
- **Why does `__netconfig_wifi_try_to_load_driver()` connect `Community 0` to `Community 1`, `Community 6`, `Community 7`?**
  _High betweenness centrality (0.104) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `__netconfig_wifi_try_to_load_driver()` (e.g. with `netconfig_is_wifi_allowed()` and `netconfig_is_wifi_tethering_on()`) actually correct?**
  _`__netconfig_wifi_try_to_load_driver()` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `__netconfig_wifi_try_to_remove_driver()` (e.g. with `netconfig_wifi_device_picker_service_stop()` and `netconfig_wifi_statistics_update_powered_off()`) actually correct?**
  _`__netconfig_wifi_try_to_remove_driver()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `netconfig_wifi_update_power_state()` (e.g. with `__netconfig_wifi_try_to_load_driver()` and `__netconfig_wifi_try_to_remove_driver()`) actually correct?**
  _`netconfig_wifi_update_power_state()` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `main()` (e.g. with `netconfig_setup_dbus()` and `netconfig_network_state_create_and_init()`) actually correct?**
  _`main()` has 8 INFERRED edges - model-reasoned connections that need verification._