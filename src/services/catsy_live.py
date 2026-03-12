"""Live Catsy PIM API integration (Phase 2).

Requires:
    - API credentials (Bearer Token)
    - API documentation at https://api-docs.catsy.com/

Connect by replacing MockCatsyService with LiveCatsyService in bootstrap.py.
"""
import logging
from typing import List, Optional

from src.services.data_source import DataSource

logger = logging.getLogger(__name__)


class LiveCatsyService(DataSource):
    """Catsy PIM REST API client.

    TODO: Implement when API credentials are available.
    API base: https://api-docs.catsy.com/
    Auth: Bearer Token in Authorization header
    """

    def __init__(self, api_url: str, bearer_token: str):
        self.api_url = api_url.rstrip("/")
        self.bearer_token = bearer_token
        self._session = None

    def _get_session(self):
        if self._session is None:
            import requests
            self._session = requests.Session()
            self._session.headers["Authorization"] = f"Bearer {self.bearer_token}"
            self._session.headers["Accept"] = "application/json"
        return self._session

    def search_parts(self, query: str) -> List[dict]:
        # TODO: Implement with actual Catsy API endpoint
        # Example pattern:
        # session = self._get_session()
        # resp = session.get(f"{self.api_url}/products", params={"search": query})
        # resp.raise_for_status()
        # return [self._map_product(p) for p in resp.json().get("data", [])]
        logger.warning("LiveCatsyService.search_parts not yet implemented")
        return []

    def get_part_details(self, part_number: str) -> Optional[dict]:
        # TODO: Implement with actual Catsy API endpoint
        # Example pattern:
        # session = self._get_session()
        # resp = session.get(f"{self.api_url}/products/{part_number}")
        # if resp.status_code == 404:
        #     return None
        # resp.raise_for_status()
        # return self._map_product(resp.json())
        logger.warning("LiveCatsyService.get_part_details not yet implemented")
        return None

    def get_part_image(self, part_number: str) -> Optional[bytes]:
        # TODO: Implement — fetch image from Catsy DAM
        # Example pattern:
        # details = self.get_part_details(part_number)
        # if not details or not details.get("image_url"):
        #     return None
        # session = self._get_session()
        # resp = session.get(details["image_url"])
        # resp.raise_for_status()
        # return resp.content
        logger.warning("LiveCatsyService.get_part_image not yet implemented")
        return None

    def _map_product(self, api_product: dict) -> dict:
        """Map Catsy API response to our standard dict format.

        TODO: Adjust field names to match actual Catsy API response structure.
        """
        return {
            "brennan_part_number": api_product.get("sku", ""),
            "customer_part_number": api_product.get("customer_sku", ""),
            "description": api_product.get("description", ""),
            "image_url": api_product.get("primary_image_url"),
        }
