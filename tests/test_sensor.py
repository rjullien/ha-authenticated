"""Tests for the authenticated sensor logic.

These exercise the data-processing parts of the integration directly
(parsing, de-duplication, filtering, data classes, the cache file and the
notification message), with a mocked Home Assistant object where one is
needed. The emphasis is on `load_authentications` and on the new `client_id`
feature, which is the most logic-heavy / most easily broken behaviour.
"""

import asyncio
import datetime
from unittest.mock import MagicMock


from custom_components.authenticated.sensor import (
    PLATFORM_NAME,
    AuthenticatedData,
    AuthenticatedSensor,
    IPData,
    get_outfile_content,
    humanize_time,
    load_authentications,
)


# --------------------------------------------------------------------------- #
# load_authentications
# --------------------------------------------------------------------------- #
class TestLoadAuthentications:
    def test_users_are_parsed(self, auth_file):
        users, _ = load_authentications(auth_file, [], [])
        assert users == {"user1": "Alice", "user2": "Bob"}

    def test_missing_file_returns_false(self, tmp_path):
        result = load_authentications(str(tmp_path / "does-not-exist"), [], [])
        assert result is False

    def test_deduplicates_keeping_latest(self, auth_file):
        _, tokens = load_authentications(auth_file, [], [])
        # 8.8.8.8 appears twice; the 2024-01-15 token must win over 2024-01-10.
        assert tokens["8.8.8.8"]["last_used_at"] == "2024-01-15T12:00:00.000000+00:00"
        assert tokens["8.8.8.8"]["user_id"] == "user1"

    def test_dedup_updates_user_and_client_to_latest(self, auth_file):
        _, tokens = load_authentications(auth_file, [], [])
        # 8.8.4.4 has two tokens from different users; the newest (user2) wins
        # for BOTH user_id and client_id.
        assert tokens["8.8.4.4"]["user_id"] == "user2"
        assert tokens["8.8.4.4"]["client_id"] == "https://home-assistant.io/android"

    def test_skips_tokens_without_last_used_at(self, auth_file):
        _, tokens = load_authentications(auth_file, [], [])
        assert "203.0.113.7" not in tokens

    def test_exclude_cidr_range(self, auth_file):
        _, tokens = load_authentications(auth_file, ["192.168.0.0/16"], [])
        assert "192.168.1.50" not in tokens
        # Non-excluded entries are still present.
        assert "8.8.8.8" in tokens

    def test_exclude_clients(self, auth_file):
        _, tokens = load_authentications(auth_file, [], ["https://example.com/blocked"])
        assert "198.51.100.4" not in tokens
        assert "8.8.8.8" in tokens

    def test_client_id_is_captured(self, auth_file):
        """The new feature: client_id must be carried through, per IP."""
        _, tokens = load_authentications(auth_file, [], [])
        assert tokens["8.8.8.8"]["client_id"] == "https://home-assistant.io/iOS"
        assert tokens["192.168.1.50"]["client_id"] == "http://192.168.1.50:8123/"


# --------------------------------------------------------------------------- #
# humanize_time
# --------------------------------------------------------------------------- #
def test_humanize_time_parses_to_seconds():
    result = humanize_time("2024-01-15T12:34:56.789000+00:00")
    assert result == datetime.datetime(2024, 1, 15, 12, 34, 56)


# --------------------------------------------------------------------------- #
# Data classes
# --------------------------------------------------------------------------- #
class TestDataClasses:
    def test_authenticated_data_reads_client_id(self):
        data = AuthenticatedData(
            "8.8.8.8",
            {
                "user_id": "user1",
                "client_id": "https://home-assistant.io/iOS",
                "last_used_at": "2024-01-15T12:00:00+00:00",
            },
        )
        assert data.client_id == "https://home-assistant.io/iOS"
        assert data.user_id == "user1"

    def test_authenticated_data_client_id_defaults_none(self):
        data = AuthenticatedData("8.8.8.8", {})
        assert data.client_id is None

    def test_ipdata_carries_client_id(self):
        data = AuthenticatedData(
            "8.8.8.8", {"client_id": "https://home-assistant.io/android"}
        )
        ip = IPData(data, {}, "ipinfo")
        assert ip.client_id == "https://home-assistant.io/android"

    def test_username_known_user(self):
        data = AuthenticatedData("8.8.8.8", {"user_id": "user1"})
        ip = IPData(data, {"user1": "Alice"}, "ipinfo")
        assert ip.username == "Alice"

    def test_username_unknown_user(self):
        data = AuthenticatedData("8.8.8.8", {"user_id": "ghost"})
        ip = IPData(data, {"user1": "Alice"}, "ipinfo")
        assert ip.username == "Unknown"

    def test_username_none_user(self):
        data = AuthenticatedData("8.8.8.8", {})
        ip = IPData(data, {"user1": "Alice"}, "ipinfo")
        assert ip.username == "Unknown"


# --------------------------------------------------------------------------- #
# get_outfile_content
# --------------------------------------------------------------------------- #
class TestOutfileContent:
    def test_reads_yaml_dict(self, tmp_path):
        f = tmp_path / "out.yaml"
        f.write_text("8.8.8.8:\n  username: Alice\n", encoding="utf-8")
        assert get_outfile_content(str(f)) == {"8.8.8.8": {"username": "Alice"}}

    def test_empty_file_returns_empty_dict(self, tmp_path):
        f = tmp_path / "out.yaml"
        f.write_text("", encoding="utf-8")
        assert get_outfile_content(str(f)) == {}


# --------------------------------------------------------------------------- #
# Sensor: attributes, cache file and notification
# --------------------------------------------------------------------------- #
def _make_sensor(out_path):
    """Build a sensor with a mocked hass (only .data and .out are touched)."""
    sensor = AuthenticatedSensor(
        MagicMock(),  # hass
        True,  # notify
        out_path,  # out
        [],  # exclude
        [],  # exclude_clients
        [],  # notify_exclude_asn
        [],  # notify_exclude_hostnames
        "ipinfo",  # provider
    )
    return sensor


def _make_ipdata(ip="8.8.8.8", client_id="https://home-assistant.io/iOS"):
    data = AuthenticatedData(
        ip,
        {
            "user_id": "user1",
            "client_id": client_id,
            "last_used_at": "2024-01-15T12:00:00.000000+00:00",
            "country": "US",
            "city": "Mountain View",
            "region": "California",
            "asn": "AS15169",
            "org": "Google LLC",
            "hostname": "dns.google",
        },
    )
    return IPData(data, {"user1": "Alice"}, "ipinfo")


def test_extra_state_attributes_includes_client_id(tmp_path):
    sensor = _make_sensor(str(tmp_path / "out.yaml"))
    sensor.last_ip = _make_ipdata()
    attrs = sensor.extra_state_attributes
    assert attrs["client_id"] == "https://home-assistant.io/iOS"
    assert attrs["username"] == "Alice"
    assert attrs["country"] == "US"


def test_extra_state_attributes_none_when_no_ip(tmp_path):
    sensor = _make_sensor(str(tmp_path / "out.yaml"))
    assert sensor.extra_state_attributes is None


def test_write_to_file_persists_client_id(tmp_path):
    out_path = str(tmp_path / "out.yaml")
    sensor = _make_sensor(out_path)
    sensor.hass.data = {PLATFORM_NAME: {"8.8.8.8": _make_ipdata()}}

    sensor.write_to_file()

    written = get_outfile_content(out_path)
    assert written["8.8.8.8"]["client_id"] == "https://home-assistant.io/iOS"
    assert written["8.8.8.8"]["username"] == "Alice"


def test_notification_message_contains_client(tmp_path):
    """The notification body must include the Client line we added."""
    ip = _make_ipdata(client_id="https://home-assistant.io/iOS")

    hass = MagicMock()
    captured = {}

    async def fake_async_call(domain, service, data):
        captured["domain"] = domain
        captured["service"] = service
        captured["data"] = data

    # call_soon_threadsafe receives (hass.async_create_task, coro); grab the coro.
    def fake_call_soon_threadsafe(callback, *args):
        captured["coro"] = args[0]

    hass.services.async_call = fake_async_call
    hass.loop.call_soon_threadsafe = fake_call_soon_threadsafe

    ip.notify(hass)

    # Run the coroutine that notify() scheduled, then inspect the payload.
    assert "coro" in captured, "notify() did not schedule a coroutine"
    asyncio.run(captured["coro"])

    assert captured["domain"] == "persistent_notification"
    assert captured["service"] == "create"
    assert "Client" in captured["data"]["message"]
    assert "https://home-assistant.io/iOS" in captured["data"]["message"]
    assert captured["data"]["notification_id"] == "8.8.8.8"
