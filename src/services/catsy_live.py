"""Live Catsy PIM API integration.

Connects to the Catsy REST API v4 using Bearer Token authentication.
API docs: https://api-docs.catsy.com/
"""
import logging
import time
from typing import List, Optional

import requests

from src.services.data_source import (
    DataSource, SEARCH_CONTAINS, SEARCH_EXACT, SEARCH_STARTS_WITH,
)

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_BACKOFF = 1.5


class LiveCatsyService(DataSource):
    """Catsy PIM REST API v4 client.

    Auth: Bearer Token in Authorization header.
    Rate limit: 2 req/sec, burst 10. Handles 429 with exponential backoff.
    """

    XREF_KEYS = [
        "parker_part_number", "swagelok_part_number", "parker_tfd_part_number",
        "aeroquip_part_number", "adaptall_part_number", "danfoss_part_number",
        "cast_part_number", "eu_part_number", "voss_part_number",
        "stauff_part_number", "ssp_part_number", "smc_part_number",
        "gates_part_number", "weatherhead_part_number",
        "fittings_unlimited_part_number", "tompkins_part_number",
        "pressure_connections_part_number", "airway_part_number",
    ]

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

    def _filter_products(self, filters: list, max_results: int = 100) -> List[dict]:
        """Run a POST /products/filter and return raw product list."""
        resp = self._request(
            "POST",
            f"{self.api_url}/products/filter?page=1&resultsPerPage={max_results}",
            json={"filters": filters},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("products", [])

    # ── Public DataSource interface ──────────────────────────────

    def search_parts(self, query: str, mode: str = SEARCH_CONTAINS) -> List[dict]:
        query = query.strip()
        if not query:
            return []

        try:
            if mode == SEARCH_EXACT:
                products = self._filter_products(
                    [{"attributeKey": "number", "operator": "is", "value": query}]
                )
            else:
                # Both "contains" and "starts_with" use the API's "contains" operator
                products = self._filter_products(
                    [{"attributeKey": "number", "operator": "contains", "value": query}]
                )

            # Client-side filter for starts_with (API doesn't support it natively)
            if mode == SEARCH_STARTS_WITH and products:
                query_lower = query.lower()
                products = [p for p in products if
                            p.get("number", "").lower().startswith(query_lower)]

            if products:
                return [self._map_product(p) for p in products]
        except requests.RequestException as e:
            logger.warning("Filter by number failed: %s", e)

        # Fallback: search by description (only for contains mode)
        if mode == SEARCH_CONTAINS:
            try:
                products = self._filter_products(
                    [{"attributeKey": "description", "operator": "contains", "value": query}],
                    max_results=50,
                )
                return [self._map_product(p) for p in products]
            except requests.RequestException as e:
                logger.error("Description search failed: %s", e)

        return []

    def get_part_details(self, part_number: str) -> Optional[dict]:
        part_number = part_number.strip()
        if not part_number:
            return None

        try:
            products = self._filter_products(
                [{"attributeKey": "number", "operator": "is", "value": part_number}],
                max_results=1,
            )
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

        # Full description includes material + sizes (best for bin labels)
        # e.g. "Steel, SAE J1453 O-Ring Face Seal Male Connector, 1/4" Male ORFS x 1/8" Male NPTF 30°"
        description = p.get("description") or ""
        short_description = p.get("short_description") or ""

        # Collect all cross-reference part numbers
        xrefs = {}
        for key in self.XREF_KEYS:
            val = p.get(key)
            if val:
                xrefs[key] = str(val).strip()

        return {
            "brennan_part_number": p.get("number", ""),
            "customer_part_number": "",  # filled by caller based on xref_key selection
            "description": description,
            "short_description": short_description,
            "series": ", ".join(p.get("series", []) or []),
            "shape_type": p.get("shape_type", ""),
            "material": p.get("primary_material", ""),
            "image_url": image_url,
            "xrefs": xrefs,
        }

    def _extract_image_url(self, p: dict) -> Optional[str]:
        """Get the best product image URL from assets or main_image field."""
        assets = p.get("assets", [])
        main_image_id = p.get("main_image")

        if main_image_id and assets:
            for a in assets:
                if isinstance(a, dict) and a.get("id") == main_image_id:
                    return a.get("url") or a.get("large_url") or a.get("thumbnail_url")

        for a in assets:
            if isinstance(a, dict) and a.get("asset_type") == "IMAGE":
                return a.get("url") or a.get("large_url") or a.get("thumbnail_url")

        return None

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
                data = resp.json()
                total = data.get("pagination", {}).get("total_results", "?")
                return True, f"Connected — {total} products in catalog"
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
