"""Mock DataSource with sample Brennan fittings data for development."""
from typing import List, Optional

from src.services.data_source import (
    DataSource, SEARCH_CONTAINS, SEARCH_EXACT, SEARCH_STARTS_WITH,
)

# Sample catalog of Brennan hydraulic fittings
_SAMPLE_PARTS = [
    {"brennan_part_number": "2404-04-02", "description": "Steel, SAE J514 37° Flare Male Connector, 1/4\" Male JIC x 1/8\" Male NPTF 30°", "short_description": "04MJ x 02MP Steel", "series": "2404", "material": "Steel", "xrefs": {"aeroquip_part_number": "2021-2-4S"}, "image_url": None},
    {"brennan_part_number": "2404-04-04", "description": "Steel, SAE J514 37° Flare Male Connector, 1/4\" Male JIC x 1/4\" Male NPTF 30°", "short_description": "04MJ x 04MP Steel", "series": "2404", "material": "Steel", "xrefs": {"aeroquip_part_number": "2021-4-4S"}, "image_url": None},
    {"brennan_part_number": "2404-06-04", "description": "Steel, SAE J514 37° Flare Male Connector, 3/8\" Male JIC x 1/4\" Male NPTF 30°", "short_description": "06MJ x 04MP Steel", "series": "2404", "material": "Steel", "xrefs": {"aeroquip_part_number": "2021-4-6S"}, "image_url": None},
    {"brennan_part_number": "2404-06-06", "description": "Steel, SAE J514 37° Flare Male Connector, 3/8\" Male JIC x 3/8\" Male NPTF 30°", "short_description": "06MJ x 06MP Steel", "series": "2404", "material": "Steel", "xrefs": {"aeroquip_part_number": "2021-6-6S"}, "image_url": None},
    {"brennan_part_number": "2404-08-08", "description": "Steel, SAE J514 37° Flare Male Connector, 1/2\" Male JIC x 1/2\" Male NPTF 30°", "short_description": "08MJ x 08MP Steel", "series": "2404", "material": "Steel", "xrefs": {"aeroquip_part_number": "2021-8-8S"}, "image_url": None},
    {"brennan_part_number": "2408-04", "description": "Steel, SAE J514 37° Flare Plug, 1/4\" Male JIC", "short_description": "04MJ Plug Steel", "series": "2408", "material": "Steel", "xrefs": {"aeroquip_part_number": "900599-4S"}, "image_url": None},
    {"brennan_part_number": "2408-06", "description": "Steel, SAE J514 37° Flare Plug, 3/8\" Male JIC", "short_description": "06MJ Plug Steel", "series": "2408", "material": "Steel", "xrefs": {"aeroquip_part_number": "900599-6S"}, "image_url": None},
    {"brennan_part_number": "2408-08", "description": "Steel, SAE J514 37° Flare Plug, 1/2\" Male JIC", "short_description": "08MJ Plug Steel", "series": "2408", "material": "Steel", "xrefs": {"aeroquip_part_number": "900599-8S"}, "image_url": None},
]


class MockCatsyService(DataSource):
    """Mock implementation for development and testing."""

    def search_parts(self, query: str, mode: str = SEARCH_CONTAINS) -> List[dict]:
        query_lower = query.lower()
        results = []
        for p in _SAMPLE_PARTS:
            pn = p["brennan_part_number"].lower()
            if mode == SEARCH_EXACT:
                if pn == query_lower:
                    results.append(p)
            elif mode == SEARCH_STARTS_WITH:
                if pn.startswith(query_lower):
                    results.append(p)
            else:  # contains
                if (query_lower in pn
                        or query_lower in p.get("description", "").lower()
                        or query_lower in p.get("short_description", "").lower()):
                    results.append(p)
        return results

    def get_part_details(self, part_number: str) -> Optional[dict]:
        for p in _SAMPLE_PARTS:
            if p["brennan_part_number"] == part_number:
                return p
        return None

    def get_part_image(self, part_number: str) -> Optional[bytes]:
        return None
