"""Shared pytest fixtures for the authenticated integration tests."""

import json
import os
import sys

import pytest

# Make the repository root importable so `custom_components.authenticated` resolves.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def sample_auth_data():
    """Return a representative `.storage/auth` payload.

    Covers: two users, IP de-duplication (keeping the most recent token),
    a token whose `last_used_at` is null (must be skipped), and a couple of
    distinct client_ids so the mobile-app vs browser distinction is testable.
    """
    return {
        "version": 1,
        "key": "auth",
        "data": {
            "users": [
                {"id": "user1", "name": "Alice"},
                {"id": "user2", "name": "Bob"},
            ],
            "refresh_tokens": [
                # 8.8.8.8 -> two tokens, same user; newest must win.
                {
                    "user_id": "user1",
                    "client_id": "https://home-assistant.io/iOS",
                    "last_used_ip": "8.8.8.8",
                    "last_used_at": "2024-01-10T09:00:00.000000+00:00",
                },
                {
                    "user_id": "user1",
                    "client_id": "https://home-assistant.io/iOS",
                    "last_used_ip": "8.8.8.8",
                    "last_used_at": "2024-01-15T12:00:00.000000+00:00",
                },
                # 192.168.1.50 -> used for the CIDR-exclusion test.
                {
                    "user_id": "user2",
                    "client_id": "http://192.168.1.50:8123/",
                    "last_used_ip": "192.168.1.50",
                    "last_used_at": "2024-01-12T08:00:00.000000+00:00",
                },
                # No last_used_at -> must be skipped entirely.
                {
                    "user_id": "user2",
                    "client_id": "https://home-assistant.io/android",
                    "last_used_ip": "203.0.113.7",
                    "last_used_at": None,
                },
                # 198.51.100.4 -> used for the exclude_clients test.
                {
                    "user_id": "user1",
                    "client_id": "https://example.com/blocked",
                    "last_used_ip": "198.51.100.4",
                    "last_used_at": "2024-01-11T07:00:00.000000+00:00",
                },
                # 8.8.4.4 -> two tokens, DIFFERENT users; newest must win for
                # both user_id and client_id (proves de-dup updates both).
                {
                    "user_id": "user1",
                    "client_id": "https://home-assistant.io/iOS",
                    "last_used_ip": "8.8.4.4",
                    "last_used_at": "2024-01-05T05:00:00.000000+00:00",
                },
                {
                    "user_id": "user2",
                    "client_id": "https://home-assistant.io/android",
                    "last_used_ip": "8.8.4.4",
                    "last_used_at": "2024-01-18T18:00:00.000000+00:00",
                },
            ],
        },
    }


@pytest.fixture
def auth_file(tmp_path, sample_auth_data):
    """Write the sample auth payload to a temp file and return its path."""
    path = tmp_path / "auth"
    path.write_text(json.dumps(sample_auth_data), encoding="utf-8")
    return str(path)
