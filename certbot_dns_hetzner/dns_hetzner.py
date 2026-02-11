"""DNS Authenticator for Hetzner DNS (Hetzner Console / Cloud API)."""

from __future__ import annotations

import time
import urllib.parse
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests
import tldextract

from certbot.errors import PluginError
from certbot.plugins import dns_common

TTL = 60
HCLOUD_DNS_API = "https://api.hetzner.cloud/v1"


@dataclass
class _HetznerCloudClient:
    """Minimal client for Hetzner Cloud DNS RRset actions."""
    token: str
    zone_name: str
    api_base: str = HCLOUD_DNS_API
    timeout: int = 20

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.api_base}{path}"
        r = requests.request(method, url, headers=self._headers(), json=json, timeout=self.timeout)
        if r.status_code >= 400:
            # Surface the useful error body (Hetzner returns JSON with "error" / "message")
            raise PluginError(f"Hetzner Cloud DNS API error {r.status_code}: {r.text}")
        if not r.text.strip():
            return {}
        return r.json()

    def _zone_id_or_name(self) -> str:
        # API supports $ID_OR_NAME in many DNS endpoints; to be safe, resolve name -> ID once.
        # GET /zones?name=<zone_name>
        q = urllib.parse.quote(self.zone_name, safe="")
        data = self._request("GET", f"/zones?name={q}")
        zones = data.get("zones", [])
        for z in zones:
            if z.get("name") == self.zone_name:
                return str(z.get("id"))
        # If not found by name (rare), fallback to using the name directly:
        return self.zone_name

    @staticmethod
    def _relative_rr_name(validation_name_fqdn: str, zone_name: str) -> str:
        """
        Convert FQDN like _acme-challenge.sub.example.com. to relative name like _acme-challenge.sub
        for the given zone example.com
        """
        name = validation_name_fqdn.rstrip(".")
        suffix = "." + zone_name.rstrip(".")
        if name == zone_name.rstrip("."):
            return "@"
        if name.endswith(suffix):
            rel = name[: -len(suffix)]
            return rel.rstrip(".") or "@"
        # If certbot gives something unexpected, send as-is (better than crashing)
        return name

    @staticmethod
    def _txt_value_for_api(validation: str) -> str:
        """
        Hetzner Cloud DNS expects TXT record values to include surrounding quotes.
        That means the actual JSON string should be: "\"<token>\""
        """
        return f"\"{validation}\""

    def create_record(self, rtype: str, fqdn: str, value: str, ttl: int = TTL) -> None:
        if rtype.upper() != "TXT":
            raise PluginError("This plugin only supports TXT records for DNS-01 challenges.")

        zone_id = self._zone_id_or_name()
        rr_name = self._relative_rr_name(fqdn, self.zone_name)

        # RRset actions endpoint:
        # POST /v1/zones/{ID_OR_NAME}/rrsets/{RR_NAME}/{RR_TYPE}/actions/add_records
        # Body includes records and optionally ttl.
        # (Hetzner DNS is RRset-based; actions exist to add/remove individual records.)  :contentReference[oaicite:2]{index=2}
        path = f"/zones/{zone_id}/rrsets/{urllib.parse.quote(rr_name, safe='')}/TXT/actions/add_records"
        body = {"ttl": int(ttl), "records": [{"value": self._txt_value_for_api(value)}]}
        self._request("POST", path, json=body)

    def delete_record(self, _unused_id: Any, rtype: str, fqdn: str, value: str) -> None:
        if rtype.upper() != "TXT":
            raise PluginError("This plugin only supports TXT records for DNS-01 challenges.")

        zone_id = self._zone_id_or_name()
        rr_name = self._relative_rr_name(fqdn, self.zone_name)

        # POST /v1/zones/{ID_OR_NAME}/rrsets/{RR_NAME}/{RR_TYPE}/actions/remove_records
        path = f"/zones/{zone_id}/rrsets/{urllib.parse.quote(rr_name, safe='')}/TXT/actions/remove_records"
        body = {"records": [{"value": self._txt_value_for_api(value)}]}
        self._request("POST", path, json=body)


class _ClientContext:
    """Simple context manager to match your existing 'with client as ...' usage."""
    def __init__(self, client: _HetznerCloudClient):
        self._client = client

    def __enter__(self) -> _HetznerCloudClient:
        return self._client

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class Authenticator(dns_common.DNSAuthenticator):
    """DNS Authenticator for Hetzner Console DNS (Cloud API)."""

    description = (
        "Obtain certificates using a DNS TXT record (Hetzner Console DNS / Cloud API)."
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.credentials = None

    @classmethod
    def add_parser_arguments(cls, add, default_propagation_seconds=60):
        super(Authenticator, cls).add_parser_arguments(
            add, default_propagation_seconds=default_propagation_seconds
        )
        add("credentials", help="Hetzner credentials INI file.")

    def more_info(self):
        return (
            "This plugin configures DNS TXT records for dns-01 challenges using "
            "Hetzner Console DNS (Cloud API / RRset actions)."
        )

    def _setup_credentials(self):
        self.credentials = self._configure_credentials(
            "credentials",
            "Hetzner credentials INI file",
            {
                # accept both names to avoid breaking existing installs
                "api_token": "Hetzner Console (Cloud API) token",
            },
        )

    @staticmethod
    def _get_zone(domain: str) -> str:
        extract = tldextract.TLDExtract()
        zone_name = extract(domain, include_psl_private_domains=True)
        return ".".join([zone_name.domain, zone_name.suffix])

    def _perform(self, domain: str, validation_name: str, validation: str):
        with self._get_hetzner_client(domain) as client:
            client.create_record("TXT", self._fqdn_format(validation_name), validation, ttl=TTL)

    def _cleanup(self, domain: str, validation_name: str, validation: str):
        with self._get_hetzner_client(domain) as client:
            client.delete_record(None, "TXT", self._fqdn_format(validation_name), validation)

    def _get_hetzner_client(self, domain: str):
        token = None
        # Support both keys without forcing your tests/ini to change
        try:
            token = self.credentials.conf("api_token")
        except Exception:
            pass
        if not token:
            try:
                token = self.credentials.conf("hetzner_api_token")
            except Exception:
                pass
        if not token:
            raise PluginError("Missing Hetzner Cloud API token in credentials file (api_token).")

        zone = self._get_zone(domain)
        return _ClientContext(_HetznerCloudClient(token=token, zone_name=zone))

    @staticmethod
    def _fqdn_format(name: str) -> str:
        if not name.endswith("."):
            return f"{name}."
        return name

