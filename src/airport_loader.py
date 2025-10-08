"""
Airport Data Loader
Loads Norwegian airport data and filters for Arctic/Norwegian coverage area
"""

import csv
from pathlib import Path
from typing import Dict, List


def load_norwegian_airports() -> List[Dict]:
    """
    Load Norwegian airports from CSV and filter for Norwegian coverage area

    Coverage area: 57-82°N, 4-32°E (matching vessel tracking area)

    Returns:
        List of airport dicts with type, name, coordinates, icao_code, etc.
    """
    airports_file = Path(__file__).parent / 'airports' / 'norwegian_airports.csv'

    if not airports_file.exists():
        print(f"Warning: Airport data file not found: {airports_file}")
        return []

    airports = []

    try:
        with open(airports_file, 'r', encoding='utf-8') as f:
            # Skip the first line (Table 1 header)
            next(f)

            reader = csv.DictReader(f, delimiter=';')

            for row in reader:
                try:
                    lat = float(row['latitude_deg'])
                    lon = float(row['longitude_deg'])

                    # Filter for Norwegian coverage area (57-82°N, 4-32°E)
                    if 57 <= lat <= 82 and 4 <= lon <= 32:
                        airports.append({
                            'type': row['type'],
                            'name': row['name'],
                            'latitude': lat,
                            'longitude': lon,
                            'icao_code': row.get('icao_code', ''),
                            'iata_code': row.get('iata_code', ''),
                            'municipality': row.get('municipality', ''),
                            'elevation_ft': row.get('elevation_ft', '')
                        })
                except (ValueError, KeyError) as e:
                    # Skip rows with invalid data
                    continue

    except Exception as e:
        print(f"Error loading airports: {e}")
        return []

    print(f"Loaded {len(airports)} airports in Norwegian coverage area")
    return airports


def get_airport_statistics(airports: List[Dict]) -> Dict:
    """
    Calculate statistics about airport types

    Args:
        airports: List of airport dicts

    Returns:
        Dict with counts by type
    """
    stats = {
        'total': len(airports),
        'large_airport': 0,
        'medium_airport': 0,
        'small_airport': 0,
        'heliport': 0,
        'seaplane_base': 0,
        'other': 0
    }

    for airport in airports:
        airport_type = airport['type']
        if airport_type in stats:
            stats[airport_type] += 1
        else:
            stats['other'] += 1

    return stats


if __name__ == '__main__':
    # Test the loader
    airports = load_norwegian_airports()
    stats = get_airport_statistics(airports)

    print("\nAirport Statistics:")
    print(f"Total: {stats['total']}")
    print(f"Large airports: {stats['large_airport']}")
    print(f"Medium airports: {stats['medium_airport']}")
    print(f"Small airports: {stats['small_airport']}")
    print(f"Heliports: {stats['heliport']}")
    print(f"Seaplane bases: {stats['seaplane_base']}")
    print(f"Other: {stats['other']}")
