"""Abstract interface for part data sources (Catsy, CSV, etc.)."""
from abc import ABC, abstractmethod
from typing import List, Optional


# Search mode constants
SEARCH_CONTAINS = "contains"
SEARCH_EXACT = "exact"
SEARCH_STARTS_WITH = "starts_with"


class DataSource(ABC):
    """Interface for fetching part data from external systems.

    Implementations can connect to Catsy PIM, read from CSV/Excel,
    or provide mock data for testing.
    """

    @abstractmethod
    def search_parts(self, query: str, mode: str = SEARCH_CONTAINS) -> List[dict]:
        """Search for parts matching the query string.

        Args:
            query: Search term.
            mode: One of SEARCH_CONTAINS, SEARCH_EXACT, SEARCH_STARTS_WITH.

        Returns a list of dicts with keys:
            brennan_part_number, customer_part_number, description,
            series_description, image_url
        """
        ...

    @abstractmethod
    def get_part_details(self, part_number: str) -> Optional[dict]:
        """Get full details for a specific Brennan part number.

        Returns a dict with keys:
            brennan_part_number, customer_part_number, description,
            series_description, image_url
        Or None if not found.
        """
        ...

    @abstractmethod
    def get_part_image(self, part_number: str) -> Optional[bytes]:
        """Download the product image for a part number.

        Returns raw image bytes (PNG/JPG) or None if unavailable.
        """
        ...
