# Tests

Unit tests for the `authenticated` integration. They focus on the
data-processing logic (parsing `.storage/auth`, de-duplication, filtering,
the geo providers, the cache file and the notification message), with a
mocked Home Assistant object where one is needed. The HTTP layer is mocked,
so the suite runs offline and fast.

## Running

From the repository root:

```bash
# one-time: install Home Assistant (to import the integration) + pytest
pip install -r requirements.txt -r requirements_test.txt

# run the suite
pytest -v
```

## What's covered

**`test_sensor.py`**
- `load_authentications`: user parsing, missing-file handling, IP
  de-duplication (newest token wins, including user_id/client_id), skipping
  tokens without `last_used_at`, CIDR exclusion, client exclusion, and
  `client_id` capture.
- `humanize_time`, the `AuthenticatedData` / `IPData` data classes and the
  `username` property.
- `get_outfile_content` (valid YAML and empty file).
- The sensor's `extra_state_attributes`, `write_to_file` (round-trip,
  including `client_id`), and the notification message (asserts the new
  **Client** line is present).

**`test_providers.py`**
- `IPInfo` parsing (splitting `org` into ASN + organisation), `IPApi`
  parsing (`country_name`), and graceful handling of rate-limiting,
  reserved IPs and connection errors — all with `requests.get` mocked.

## Notes

- The tests import the integration as a package, so they need Home Assistant
  importable (provided by `requirements.txt`). They do **not** require
  `pytest-homeassistant-custom-component`; if you later want full
  integration-level tests (real `hass`, entity setup via `async_setup_platform`),
  add that harness as a follow-up.
- `tests/**` is exempted from the docstring lint rules in `.ruff.toml`.
