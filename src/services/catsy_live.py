"""Live Catsy PIM API integration.

Connects to the Catsy REST API v4 using Bearer Token authentication.
API docs: https://api-docs.catsy.com/
"""
import logging
import time
from typing import List, Optional

import requests

from src.services.data_source import DataSource

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_BACKOFF = 1.5


class LiveCatsyService(DataSource):
    """Catsy PIM REST API v4 client.

    Auth: Bearer Token in Authorization header.
    Rate limit: 2 req/sec, burst 10. Handles 429 with exponential backoff.
    """

    def __init__(self, api_url: str, bearer_token: str):
        self.api_url = api_url.rstrip("/")
        self.bearer_token = bearer_token
        self._session: Optional[requests.Session] = None

    def _get_session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                "Authorization": f"Bearer {self.bearer_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            })
        return self._session

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        session = self._get_session()
        delay = _RETRY_BACKOFF
        resp = None
        for attempt in range(_MAX_RETRIES + 1):
            resp = session.request(method, url, **kwargs)
            if resp.status_code == 429:
                if attempt < _MAX_RETRIES:
                    logger.warning("Rate limited (429), retrying in %.1fs...", delay)
                    time.sleep(delay)
                    delay *= 2
                    continue
                logger.error("Rate limited after %d retries", _MAX_RETRIES)
            return resp
        return resp

    # ── Public DataSource interface ──────────────────────────────

    def search_parts(self, query: str) -> List[dict]:
        query = query.strip()
        if not query:
            return []

        try:
            body = {
                "filters": [
                    {"attributeKey": "number", "operator": "contains", "value": query}
                ]
            }
            resp = self._request(
                "POST",
                f"{self.api_url}/products/filter?page=1&resultsPerPage=50",
                json=body,
                timeout=30,
            )
            resp.raise_for_status()
            products = resp.json().get("products", [])
            if products:
                return [self._map_product(p) for p in products]
        except requests.RequestException as e:
            logger.warning("Filter by number failed: %s", e)

        # Fallback: search by description
        try:
            body = {
                "filters": [
                    {"attributeKey": "description", "operator": "contains", "value": query}
                ]
            }
            resp = self._request(
                "POST",
                f"{self.api_url}/products/filter?page=1&resultsPerPage=50",
                json=body,
                timeout=30,
            )
            resp.raise_for_status()
            products = resp.json().get("products", [])
            return [self._map_product(p) for p in products]
        except requests.RequestException as e:
            logger.error("Search failed: %s", e)
            return []

    def get_part_details(self, part_number: str) -> Optional[dict]:
        part_number = part_number.strip()
        if not part_number:
            return None

        try:
            body = {
                "filters": [
                    {"attributeKey": "number", "operator": "is", "value": part_number}
                ]
            }
            resp = self._request(
                "POST",
                f"{self.api_url}/products/filter?page=1&resultsPerPage=1",
                json=body,
                timeout=30,
            )
            resp.raise_for_status()
            products = resp.json().get("products", [])
            if products:
                return self._map_product(products[0])
        except requests.RequestException as e:
            logger.error("Failed to get part details for %s: %s", part_number, e)

        return None

    def get_part_image(self, part_number: str) -> Optional[bytes]:
        details = self.get_part_details(part_number)
        if not details:
            return None

        image_url = details.get("image_url")
        if not image_url:
            return None

        try:
            resp = self._request("GET", image_url, timeout=30)
            resp.raise_for_status()
            return resp.content
        except requests.RequestException as e:
            logger.error("Failed to download image for %s: %s", part_number, e)
            return None

    # ── Mapping ──────────────────────────────────────────────────

    def _map_product(self, p: dict) -> dict:
        """Map a Catsy v4 product to our standard label dict."""
        image_url = self._extract_image_url(p)

        return {
            "brennan_part_number": p.get("number", ""),
            "customer_part_number": self._extract_customer_pn(p),
            "description": p.get("description", "") or p.get("short_description", ""),
            "image_url": image_url,
        }

    def _extract_image_url(self, p: dict) -> Optional[str]:
        """Get the best product image URL from assets or main_image field."""
        assets = p.get("assets", [])
        main_image_id = p.get("main_image")

        # Try to find the main_image asset by ID
        if main_image_id and assets:
            for a in assets:
                if isinstance(a, dict) and a.get("id") == main_image_id:
                    return a.get("url") or a.get("large_url") or a.get("thumbnail_url")

        # Fall back to first IMAGE asset
        for a in assets:
            if isinstance(a, dict) and a.get("asset_type") == "IMAGE":
                return a.get("url") or a.get("large_url") or a.get("thumbnail_url")

        return None

    def _extract_customer_pn(self, p: dict) -> str:
        """Extract the first non-empty customer cross-reference part number."""
        xref_keys = [
            "parker_part_number", "swagelok_part_number", "parker_tfd_part_number",
            "aeroquip_part_number", "adaptall_part_number", "danfoss_part_number",
            "cast_part_number", "eu_part_number", "voss_part_number",
            "stauff_part_number", "ssp_part_number", "smc_part_number",
            "gates_part_number", "weatherhead_part_number",
            "fittings_unlimited_part_number", "tompkins_part_number",
            "pressure_connections_part_number", "airway_part_number",
        ]
        for key in xref_keys:
            val = p.get(key)
            if val:
                return str(val).strip()
        return ""

    # ── Connection test ──────────────────────────────────────────

    def test_connection(self) -> tuple:
        try:
            resp = self._request(
                "POST",
                f"{self.api_url}/products/filter?page=1&resultsPerPage=1",
                json={"filters": []},
                timeout=15,
            )
            if resp.status_code == 200:
                products = resp.json().get("products", [])
                return True, f"Connected! Found products ({len(products)} returned)"
            elif resp.status_code == 401:
                return False, "Authentication failed (401). Check your Bearer Token."
            elif resp.status_code == 403:
                return False, "Access denied (403). Token may lack required permissions."
            else:
                return False, f"Unexpected status {resp.status_code}: {resp.text[:200]}"
        except requests.ConnectionError:
            return False, f"Cannot connect to {self.api_url}. Check the URL."
        except requests.Timeout:
            return False, "Connection timed out. Server may be unreachable."
        except Exception as e:
            return False, f"Error: {e}"
