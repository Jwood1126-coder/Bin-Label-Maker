"""Mock DataSource with sample Brennan fittings data for development."""
from typing import List, Optional

from src.services.data_source import DataSource

# Sample catalog of Brennan hydraulic fittings
_SAMPLE_PARTS = [
    {"brennan_part_number": "2404-04-02", "customer_part_number": "2021-2-4S", "description": "04MJ-02MP Straight"},
    {"brennan_part_number": "2404-04-04", "customer_part_number": "2021-4-4S", "description": "04MJ-04MP Straight"},
    {"brennan_part_number": "2404-06-04", "customer_part_number": "2021-4-6S", "description": "06MJ-04MP Straight"},
    {"brennan_part_number": "2404-04-06", "customer_part_number": "2021-6-4S", "description": "04MJ-06MP Straight"},
    {"brennan_part_number": "2404-06-06", "customer_part_number": "2021-6-6S", "description": "06MJ-06MP Straight"},
    {"brennan_part_number": "2404-06-08", "customer_part_number": "2021-8-6S", "description": "06MJ-08MP Straight"},
    {"brennan_part_number": "2404-08-08", "customer_part_number": "2021-8-8S", "description": "08MJ-08MP Straight"},
    {"brennan_part_number": "2404-10-08", "customer_part_number": "2021-8-10S", "description": "10MJ-08MP Straight"},
    {"brennan_part_number": "2404-12-08", "customer_part_number": "2021-8-12S", "description": "12MJ-08MP Straight"},
    {"brennan_part_number": "2404-06-12", "customer_part_number": "2021-12-6S", "description": "06MJ-12MP Straight"},
    {"brennan_part_number": "2404-10-12", "customer_part_number": "2021-12-10S", "description": "10MJ-12MP Straight"},
    {"brennan_part_number": "2404-12-12", "customer_part_number": "2021-12-12S", "description": "12MJ-12MP Straight"},
    {"brennan_part_number": "2404-12-16", "customer_part_number": "2021-16-12S", "description": "12MJ-16MP Straight"},
    {"brennan_part_number": "2404-16-16", "customer_part_number": "2021-16-16S", "description": "16MJ-16MP Straight"},
    {"brennan_part_number": "2404-16-20", "customer_part_number": "2021-20-16S", "description": "16MJ-20MP Straight"},
    {"brennan_part_number": "2404-20-20", "customer_part_number": "2021-20-20S", "description": "20MJ-20MP Straight"},
    {"brennan_part_number": "2404-24-24", "customer_part_number": "2021-24-24S", "description": "24MJ-24MP Straight"},
    {"brennan_part_number": "2404-32-32", "customer_part_number": "2021-32-32S", "description": "32MJ-32MP Straight"},
    {"brennan_part_number": "2404-08-12", "customer_part_number": "2021-12-8S", "description": "08MJ-12MP Straight"},
    {"brennan_part_number": "2404-20-16", "customer_part_number": "2021-16-20S", "description": "20MJ-16MP Straight"},
    {"brennan_part_number": "2404-24-20", "customer_part_number": "2021-20-24S", "description": "24MJ-20MP Straight"},
    {"brennan_part_number": "2404-16-12", "customer_part_number": "2021-12-16S", "description": "16MJ-12MP Straight"},
    {"brennan_part_number": "2408-04", "customer_part_number": "900599-4S", "description": "04MJ Plug"},
    {"brennan_part_number": "2408-06", "customer_part_number": "900599-6S", "description": "06MJ Plug"},
    {"brennan_part_number": "2408-08", "customer_part_number": "900599-8S", "description": "08MJ Plug"},
    {"brennan_part_number": "2408-10", "customer_part_number": "900599-10S", "description": "10MJ Plug"},
    {"brennan_part_number": "2408-12", "customer_part_number": "900599-12S", "description": "12MJ Plug"},
    {"brennan_part_number": "2408-16", "customer_part_number": "900599-16S", "description": "16MJ Plug"},
    {"brennan_part_number": "2408-20", "customer_part_number": "900599-20S", "description": "20MJ Plug"},
]


class MockCatsyService(DataSource):
    """Mock implementation for development and testing.

    Replace with LiveCatsyService when API credentials are available.
    """

    def search_parts(self, query: str) -> List[dict]:
        query_lower = query.lower()
        return [
            p for p in _SAMPLE_PARTS
            if query_lower in p["brennan_part_number"].lower()
            or query_lower in p["customer_part_number"].lower()
            or query_lower in p["description"].lower()
        ]

    def get_part_details(self, part_number: str) -> Optional[dict]:
        for p in _SAMPLE_PARTS:
            if p["brennan_part_number"] == part_number:
                return {**p, "image_url": None}
        return None

    def get_part_image(self, part_number: str) -> Optional[bytes]:
        # No images in mock — return None
        return None
