# Authenticated — Home Assistant Custom Component

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A Home Assistant custom component that tracks successful logins and notifies you when one comes from a **new IP address**. Each login is enriched with geolocation data (country, region, city, ASN, organisation) and the **client** used to authenticate (e.g. the mobile companion app vs. a web browser).

> **Maintained fork of [rarosalion/authenticated](https://github.com/rarosalion/authenticated)**, with fixes for Home Assistant 2024.9+ / 2026.3+ compatibility and the ability to identify the client behind each login.

## Why this fork

The upstream repository called `async_create()` from `homeassistant.components.persistent_notification` in a synchronous (worker thread) context. Since HA 2024.9 this raises:

- `RuntimeError: Detected code that calls async_create from a thread`
- `AttributeError: module has no attribute async_create` (HA 2025.x+)

This fork fixes it with the thread-safe `hass.loop.call_soon_threadsafe(hass.async_create_task, ...)` pattern (required for HA 2026.3+).

**Also new:** the `client_id` of each login is now stored and shown in the sensor attributes and the notification, so you can recognise a login from your phone’s companion app versus a browser session.

## Installation

### HACS (custom repository)

1. Open **HACS** in Home Assistant.
1. Top-right menu (⋮) → **Custom repositories**.
1. Add `https://github.com/rjullien/ha-authenticated` with category **Integration**.
1. Search for **Authenticated** and install it.
1. **Restart** Home Assistant.
1. Add the configuration below to `configuration.yaml` and restart again.

### Manual

1. Copy the `custom_components/authenticated` folder into your HA `config/custom_components/` directory.
1. **Restart** Home Assistant.
1. Add the configuration below and restart again.

## Configuration

```yaml
sensor:
  - platform: authenticated
    provider: ipinfo
    enable_notification: true
    notify_exclude_asns: []
    notify_exclude_hostnames: []
    exclude: []
    exclude_clients: []
```

### Options

|Option                    |Default |Description                                                                                       |
|--------------------------|--------|--------------------------------------------------------------------------------------------------|
|`provider`                |`ipinfo`|Geolocation provider. One of `ipinfo`, `ipapi`.                                                   |
|`enable_notification`     |`true`  |Create a persistent notification on a login from a new IP.                                        |
|`notify_exclude_asns`     |`[]`    |List of ASNs to **skip** for notifications (e.g. your mobile carrier, to silence cellular logins).|
|`notify_exclude_hostnames`|`[]`    |List of hostnames to skip for notifications.                                                      |
|`exclude`                 |`[]`    |List of IPs/CIDR ranges to ignore entirely (e.g. your home `192.168.0.0/16`).                     |
|`exclude_clients`         |`[]`    |List of `client_id` values to ignore entirely.                                                    |

## Identifying logins from your phone

This component works at the **IP level**: “a login from a new IP” is what triggers an alert. A few things to know to use it well for phones:

- **Cellular (4G/5G):** your phone’s public IP rotates constantly, so it will generate many “new IP” alerts. Add your **carrier’s ASN** to `notify_exclude_asns` to silence them.
- **Home Wi‑Fi:** your phone shares your home’s public IP, so it is indistinguishable from any other device at home (use `exclude` for your home range).
- **The `client_id` attribute** tells you which application was used to log in (the companion app reports a different client than the web frontend), which is the most reliable in-app signal for “this came from my phone.”
- **MAC address is not available** for login events — it is a link-layer identifier that never crosses a router, so it cannot be captured or stored here. For device-level tracking by MAC, use Home Assistant’s presence detection / device trackers instead.

## What you get

- **Sensor** `sensor.last_successful_authentication` — state is the last successful login IP, with attributes:
  `hostname`, `country`, `region`, `city`, `asn`, `org`, `client_id`, `username`, `new_ip`, `last_authenticated_time`, `previous_authenticated_time`.
- A **persistent notification** when a login comes from a new IP (unless excluded).
- A cache file `.ip_authenticated.yaml` in your config directory, recording every known IP and its details.

## Credits

Originally created by [@ludeeus](https://github.com/ludeeus), forked by [@rarosalion](https://github.com/rarosalion), and maintained here by [@rjullien](https://github.com/rjullien).

## License

MIT — see <LICENSE>.