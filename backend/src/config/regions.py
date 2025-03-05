REGION_MAPPING = {
    "USA": ["United States"],
    "EU": [ "Ireland", "Romania"]  # Can easily add more countries later
}

def get_countries_for_region(region: str) -> list[str]:
    """Get list of countries to search for a given region"""
    return REGION_MAPPING.get(region, []) 