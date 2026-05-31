"""Constants for authenticated."""

DOMAIN = "authenticated"
INTEGRATION_VERSION = "0.3.0"
ISSUE_URL = "https://github.com/rjullien/ha-authenticated/issues"

STARTUP = f"""
-------------------------------------------------------------------
{DOMAIN}
Version: {INTEGRATION_VERSION}
This is a custom component
If you have any issues with this you need to open an issue here:
https://github.com/rjullien/ha-authenticated/issues
-------------------------------------------------------------------
"""


CONF_NOTIFY = "enable_notification"
CONF_NOTIFY_EXCLUDE_ASN = "notify_exclude_asns"
CONF_NOTIFY_EXCLUDE_HOSTNAMES = "notify_exclude_hostnames"
CONF_EXCLUDE = "exclude"
CONF_EXCLUDE_CLIENTS = "exclude_clients"
CONF_PROVIDER = "provider"

OUTFILE = ".ip_authenticated.yaml"
