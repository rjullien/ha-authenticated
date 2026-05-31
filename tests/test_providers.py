"""Tests for the geolocation providers.

The HTTP layer (`requests.get`) is mocked, so these run offline and don't
depend on ipinfo.io / ipapi.co being reachable or rate-limiting.
"""

from unittest.mock import MagicMock, patch

import requests

from custom_components.authenticated.providers import PROVIDERS, IPApi, IPInfo


def _mock_response(payload):
    resp = MagicMock()
    resp.json.return_value = payload
    return resp


def test_registry_contains_both_providers():
    assert set(PROVIDERS) == {"ipinfo", "ipapi"}


class TestIPInfo:
    def test_parses_and_splits_org_into_asn(self):
        payload = {
            "country": "US",
            "region": "California",
            "city": "Mountain View",
            "org": "AS15169 Google LLC",
        }
        with patch(
            "custom_components.authenticated.providers.requests.get",
            return_value=_mock_response(payload),
        ):
            provider = IPInfo("8.8.8.8")
            provider.update_geo_info()

        assert provider.country == "US"
        assert provider.region == "California"
        assert provider.city == "Mountain View"
        assert provider.asn == "AS15169"
        assert provider.org == "Google LLC"
        assert provider.computed_result == {
            "country": "US",
            "region": "California",
            "city": "Mountain View",
            "asn": "AS15169",
            "org": "Google LLC",
        }

    def test_missing_org_yields_none_asn_and_org(self):
        payload = {"country": "US", "city": "Mountain View"}
        with patch(
            "custom_components.authenticated.providers.requests.get",
            return_value=_mock_response(payload),
        ):
            provider = IPInfo("8.8.8.8")
            provider.update_geo_info()

        assert provider.asn is None
        assert provider.org is None
        assert provider.country == "US"


class TestIPApi:
    def test_uses_country_name_field(self):
        payload = {
            "country_name": "United States",
            "region": "California",
            "city": "Mountain View",
            "asn": "AS15169",
            "org": "Google LLC",
        }
        with patch(
            "custom_components.authenticated.providers.requests.get",
            return_value=_mock_response(payload),
        ):
            provider = IPApi("8.8.8.8")
            provider.update_geo_info()

        assert provider.country == "United States"
        assert provider.asn == "AS15169"
        assert provider.org == "Google LLC"


class TestErrorHandling:
    def test_rate_limited_is_handled_gracefully(self):
        payload = {"error": True, "reason": "RateLimited"}
        with patch(
            "custom_components.authenticated.providers.requests.get",
            return_value=_mock_response(payload),
        ):
            provider = IPInfo("8.8.8.8")
            provider.update_geo_info()
        # No exception escapes; result stays empty.
        assert provider.country is None
        assert provider.org is None

    def test_reserved_ip_returns_early(self):
        payload = {"reserved": True}
        with patch(
            "custom_components.authenticated.providers.requests.get",
            return_value=_mock_response(payload),
        ):
            provider = IPInfo("10.0.0.1")
            provider.update_geo_info()
        assert provider.computed_result == {
            "country": None,
            "region": None,
            "city": None,
            "asn": None,
            "org": None,
        }

    def test_connection_error_is_swallowed(self):
        with patch(
            "custom_components.authenticated.providers.requests.get",
            side_effect=requests.exceptions.ConnectionError,
        ):
            provider = IPInfo("8.8.8.8")
            provider.update_geo_info()  # must not raise
        assert provider.country is None
