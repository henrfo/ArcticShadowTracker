#!/usr/bin/env python3
"""
Shadow Fleet Crawler - Arctic Shadow Tracker
Extracts Russian shadow fleet vessel data from multiple sources
"""

import json
import pdfplumber
import re
import time
import requests
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup

# Project directories
BASE_DIR = Path(__file__).parent.parent
SRC_DIR = BASE_DIR / 'src'
CACHE_DIR = SRC_DIR / '.mmsi_cache'
CACHE_DIR.mkdir(exist_ok=True)

# Rate limiting for VesselFinder scraping
SCRAPE_DELAY = 2  # seconds between requests

def is_valid_vessel_name(name):
    """
    Validate if a string is a legitimate vessel name

    Rules:
    - Must be at least 3 characters
    - Must contain at least one letter
    - Cannot be pure numbers
    - Cannot have newlines or excessive whitespace
    - Cannot be common PDF artifacts

    Args:
        name: Vessel name to validate

    Returns:
        bool: True if valid vessel name
    """
    if not name or len(name) < 3:
        return False

    # Reject if contains newlines (PDF parsing artifact)
    if '\n' in name or '\r' in name or '\t' in name:
        return False

    # Clean and check length again
    cleaned = name.strip()
    if len(cleaned) < 3:
        return False

    # Reject pure numbers (even with spaces/dashes)
    if name.replace(' ', '').replace('-', '').isdigit():
        return False

    # Must contain at least one letter
    if not any(c.isalpha() for c in name):
        return False

    # Reject common PDF artifacts and navigation terms
    invalid_patterns = ['page', 'table', 'source', 'list', 'annex', 'appendix', 'punkte', 'conspicious']
    name_lower = name.lower()
    if any(pattern in name_lower for pattern in invalid_patterns):
        return False

    return True

def fetch_opensanctions_vessels():
    """
    Fetch sanctioned vessel entities from OpenSanctions bulk dataset.
    Streams the NDJSON entities file (no API key required) and filters
    for schema=Vessel. Returns list of vessel dicts.
    """
    vessels = []
    url = "https://data.opensanctions.org/datasets/latest/default/entities.ftm.json"

    try:
        print("   Streaming OpenSanctions bulk dataset for vessels...")
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()

        scanned = 0
        for line in resp.iter_lines():
            if not line:
                continue
            scanned += 1
            try:
                entity = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entity.get('schema') != 'Vessel':
                continue

            props = entity.get('properties', {})
            name = (props.get('name', [None])[0] or '').strip().upper()
            if not name or not is_valid_vessel_name(name):
                continue

            imo_raw = props.get('imoNumber', ['Unknown'])[0] or 'Unknown'
            imo = re.sub(r'^IMO', '', imo_raw).strip()
            mmsi_list = props.get('mmsiNumber', [])
            flag = (props.get('flag', [None])[0] or '')
            datasets = entity.get('datasets', [])
            sanctions_programs = [d for d in datasets if d not in ('default', 'sanctions')]

            vessels.append({
                'vessel_name': name,
                'imo': imo if imo else 'Unknown',
                'mmsi': mmsi_list[0] if mmsi_list else None,
                'source': 'OpenSanctions',
                'sanctions_programs': sanctions_programs,
                'flag_state': flag,
                'reason': f"Sanctioned vessel ({', '.join(sanctions_programs[:3])})" if sanctions_programs else "Sanctioned vessel",
                'confidence': 'confirmed',
            })

        print(f"   Scanned {scanned} entities, extracted {len(vessels)} vessels")
    except Exception as e:
        print(f"   Warning: OpenSanctions fetch failed: {e}")

    return vessels


def fetch_crea_shadow_fleet():
    """
    Fetch shadow fleet data from CREA (Centre for Research on Energy and Clean Air).
    CREA publishes Russian oil tanker shadow fleet data.
    Returns list of vessel dicts.
    """
    vessels = []
    # CREA Russian oil tracker API — shadow fleet vessel list
    url = "https://api.russiafossiltracker.com/v0/voyage?shadow_fleet=true&format=json&limit=500"

    try:
        print("   Querying CREA Russian Fossil Tracker for shadow fleet...")
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        records = data if isinstance(data, list) else data.get('data', data.get('results', []))

        seen_names = set()
        for record in records:
            name = (record.get('ship_name') or record.get('vessel_name') or '').strip().upper()
            if not name or name in seen_names or not is_valid_vessel_name(name):
                continue
            seen_names.add(name)

            imo = str(record.get('ship_imo') or record.get('imo') or 'Unknown')
            mmsi = str(record.get('ship_mmsi') or record.get('mmsi') or '')

            vessels.append({
                'vessel_name': name,
                'imo': imo if imo != 'None' else 'Unknown',
                'mmsi': mmsi if mmsi and mmsi != 'None' else None,
                'source': 'CREA Russian Fossil Tracker',
                'reason': 'Russian oil shadow fleet (CREA)',
                'confidence': 'confirmed',
            })

        print(f"   Extracted {len(vessels)} unique vessels from CREA")
    except Exception as e:
        print(f"   Warning: CREA fetch failed: {e}")

    return vessels


def extract_greenpeace_pdf():
    """
    Extract vessel names and IMO numbers from Greenpeace Baltic tankers PDF

    Returns:
        list: List of dict with vessel_name and imo_number
    """
    pdf_path = SRC_DIR / 'fb3d5709-greenpeace-shadow-fleet-baltic-tankers-list.pdf'
    vessels = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"📄 Processing Greenpeace PDF: {pdf_path.name}")
            print(f"   Pages: {len(pdf.pages)}")

            for page_num, page in enumerate(pdf.pages, 1):
                # Extract tables from the page
                tables = page.extract_tables()

                if tables:
                    for table in tables:
                        for row in table:
                            if row and len(row) >= 2:
                                # Look for vessel name and IMO number patterns
                                for cell in row:
                                    if cell and isinstance(cell, str):
                                        # Look for IMO number pattern: IMO followed by 7 digits
                                        imo_match = re.search(r'IMO\s*(\d{7})', cell, re.IGNORECASE)
                                        if imo_match:
                                            imo = imo_match.group(1)
                                            # Try to find vessel name in same or adjacent cells
                                            vessel_name = None
                                            for name_cell in row:
                                                if name_cell and isinstance(name_cell, str) and 'IMO' not in name_cell:
                                                    # Clean up vessel name
                                                    vessel_name = name_cell.strip()
                                                    if vessel_name and len(vessel_name) > 2:
                                                        break

                                            if vessel_name and is_valid_vessel_name(vessel_name):
                                                vessels.append({
                                                    'vessel_name': vessel_name.upper(),
                                                    'imo': imo,
                                                    'source': 'Greenpeace Baltic Tankers List'
                                                })

                # Also extract text for vessel names mentioned outside tables
                text = page.extract_text()
                if text:
                    # Find IMO numbers in text
                    imo_matches = re.finditer(r'(\w+[\w\s-]+?)\s+(?:IMO\s*)?(\d{7})', text, re.IGNORECASE)
                    for match in imo_matches:
                        potential_name = match.group(1).strip()
                        imo = match.group(2)

                        # Validate vessel name
                        if is_valid_vessel_name(potential_name):
                            vessels.append({
                                'vessel_name': potential_name.upper(),
                                'imo': imo,
                                'source': 'Greenpeace Baltic Tankers List (text)'
                            })

            print(f"   ✓ Extracted {len(vessels)} vessels from PDF")

    except Exception as e:
        print(f"   ⚠️ Error reading PDF: {e}")

    return vessels

def get_known_2025_vessels():
    """
    Add manually curated list of known shadow fleet vessels from 2025 research

    Returns:
        list: List of dict with vessel_name, imo_number, and notes
    """
    known_vessels = [
        # From Ukrainian Intelligence GUR database
        {'vessel_name': 'PROXIMA', 'imo': '9329655', 'source': 'Ukrainian GUR Database'},
        {'vessel_name': 'KALININGRAD', 'imo': '9341067', 'source': 'Ukrainian GUR Database'},
        {'vessel_name': 'KRYMSK', 'imo': '9270529', 'source': 'Ukrainian GUR Database'},

        # From 2025 news reports and sanctions lists
        {'vessel_name': 'KIWALA', 'imo': 'Unknown', 'source': '2025 EU/UK Sanctions - Seized by Estonia', 'aka': 'PUSHPA, BORACAY'},
        {'vessel_name': 'EAGLE S', 'imo': 'Unknown', 'source': '2025 Finnish Customs - Cable sabotage'},
        {'vessel_name': 'EVENTIN', 'imo': 'Unknown', 'source': '2025 EU Sanctions List - Panama flag', 'port': 'Ust-Luga'},
        {'vessel_name': 'LUGA', 'imo': 'Unknown', 'source': '2025 Belgian Search - Russian crew'},
        {'vessel_name': 'DOLPHIN', 'imo': 'Unknown', 'source': '2025 Dutch Search - Antigua flag, Russian crew'},
        {'vessel_name': 'SUN', 'imo': 'Unknown', 'source': '2025 Spotted near Sweden-Poland cable - Antigua flag'},
        {'vessel_name': 'SELVA', 'imo': 'Unknown', 'source': '2025 UK/EU Sanctions - Russian Navy escort'},
        {'vessel_name': 'SIERRA', 'imo': 'Unknown', 'source': '2025 UK/EU Sanctions - Russian Navy escort'},

        # Additional known shadow fleet vessels
        {'vessel_name': 'THEMIS', 'imo': 'Unknown', 'source': 'Ukrainian GUR Database'},
        {'vessel_name': 'VIRAT', 'imo': 'Unknown', 'source': 'Ukrainian GUR Database'},
        {'vessel_name': 'AKAR WEST', 'imo': 'Unknown', 'source': 'Ukrainian GUR Database'},
    ]

    print(f"📋 Adding {len(known_vessels)} manually curated vessels from 2025 research")
    return known_vessels

def mmsi_from_imo(imo):
    """
    Convert IMO to MMSI using VesselFinder web scraping with caching

    Args:
        imo: IMO number (7 digits)

    Returns:
        str: MMSI number (9 digits) or None
    """
    if not imo or imo == 'Unknown':
        return None

    # Check cache first
    cache_file = CACHE_DIR / f"{imo}.json"
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                cached = json.load(f)
                return cached.get('mmsi')
        except Exception:
            pass

    # Scrape VesselFinder with retry logic
    max_retries = 2
    for attempt in range(max_retries):
        try:
            url = f"https://www.vesselfinder.com/vessels/details/{imo}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }

            time.sleep(SCRAPE_DELAY)  # Rate limiting
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Method 1: Look for "IMO / MMSI" pattern in text
                # VesselFinder shows: "IMO / MMSI9329655 / 273264690"
                page_text = soup.get_text()
                imo_mmsi_match = re.search(rf'IMO\s*/\s*MMSI\s*{imo}\s*/\s*(\d{{9}})', page_text)
                if imo_mmsi_match:
                    mmsi = imo_mmsi_match.group(1)
                    # Cache result
                    with open(cache_file, 'w') as f:
                        json.dump({'imo': imo, 'mmsi': mmsi, 'cached_at': datetime.now().isoformat()}, f)
                    return mmsi

                # Method 2: Look for MMSI in vessel description
                # Format: "(IMO 9329655, MMSI 273264690)"
                desc_match = re.search(rf'\(IMO\s+{imo},\s*MMSI\s+(\d{{9}})\)', page_text)
                if desc_match:
                    mmsi = desc_match.group(1)
                    with open(cache_file, 'w') as f:
                        json.dump({'imo': imo, 'mmsi': mmsi, 'cached_at': datetime.now().isoformat()}, f)
                    return mmsi

                # Method 3: Look in table rows for MMSI
                for td in soup.find_all('td'):
                    text = td.get_text(strip=True)
                    if 'MMSI' in text or 'mmsi' in text.lower():
                        mmsi_match = re.search(r'\b(\d{9})\b', text)
                        if mmsi_match:
                            mmsi = mmsi_match.group(1)
                            with open(cache_file, 'w') as f:
                                json.dump({'imo': imo, 'mmsi': mmsi, 'cached_at': datetime.now().isoformat()}, f)
                            return mmsi

            # Cache negative result to avoid re-scraping
            with open(cache_file, 'w') as f:
                json.dump({'imo': imo, 'mmsi': None, 'cached_at': datetime.now().isoformat()}, f)

            return None

        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                print(f"      ⚠️ Timeout, retrying... (attempt {attempt + 2}/{max_retries})")
                time.sleep(SCRAPE_DELAY * 2)  # Longer delay before retry
                continue
            else:
                print(f"      ⚠️ Timeout after {max_retries} attempts")
                return None
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"      ⚠️ Error, retrying: {e}")
                time.sleep(SCRAPE_DELAY)
                continue
            else:
                print(f"      ⚠️ Error scraping VesselFinder for IMO {imo}: {e}")
                return None

    return None

def deduplicate_vessels(vessels):
    """
    Merge duplicate vessels by IMO or name, combining sources.
    Confidence: confirmed if >=2 sources or any sanctions list, else suspected.
    """
    by_imo = {}   # imo -> merged vessel
    by_name = {}  # name -> merged vessel

    for vessel in vessels:
        imo = vessel.get('imo', '').strip()
        name = vessel.get('vessel_name', '').strip().upper()
        source = vessel.get('source', 'unknown')

        # Find existing entry by IMO or name
        existing = None
        if imo and imo != 'Unknown':
            existing = by_imo.get(imo)
        if not existing and name:
            existing = by_name.get(name)

        if existing:
            # Merge: add source, update fields
            sources = existing.setdefault('sources', [existing.get('source', 'unknown')])
            if source not in sources:
                sources.append(source)
            # Keep non-None values
            if vessel.get('mmsi') and not existing.get('mmsi'):
                existing['mmsi'] = vessel['mmsi']
            if vessel.get('imo', 'Unknown') != 'Unknown' and existing.get('imo', 'Unknown') == 'Unknown':
                existing['imo'] = vessel['imo']
            if vessel.get('sanctions_programs'):
                existing.setdefault('sanctions_programs', []).extend(vessel['sanctions_programs'])
            if vessel.get('reason') and not existing.get('reason'):
                existing['reason'] = vessel['reason']
        else:
            # New entry
            vessel['sources'] = [source]
            if imo and imo != 'Unknown':
                by_imo[imo] = vessel
            if name:
                by_name[name] = vessel
                if imo and imo != 'Unknown':
                    by_name[name] = by_imo[imo]  # point to same dict

    # Collect unique vessels
    seen = set()
    unique = []
    for v in list(by_imo.values()) + list(by_name.values()):
        key = id(v)
        if key in seen:
            continue
        seen.add(key)

        # Compute confidence: confirmed if >=2 sources or sanctions list
        sources = v.get('sources', [])
        has_sanctions = any(s in ('OpenSanctions',) for s in sources)
        v['confidence'] = 'confirmed' if (len(sources) >= 2 or has_sanctions) else 'suspected'
        v['source'] = ', '.join(sources)  # flatten for backward compat
        unique.append(v)

    return unique

def update_shadow_fleet_json(vessels, scrape_mmsi=True, max_scrapes=0):
    """
    Update shadow_fleet.json with extracted vessel data

    Args:
        vessels: List of vessel dicts with vessel_name, imo, etc.
        scrape_mmsi: Whether to scrape VesselFinder for MMSI (default True)
        max_scrapes: Maximum number of vessels to scrape (0 = all, default 0)
    """
    shadow_fleet_file = SRC_DIR / 'shadow_fleet.json'

    # Extract vessel names for the shadow_fleet_names array
    vessel_names = []
    vessel_imos = []
    mmsi_numbers = []

    if scrape_mmsi:
        print(f"🔍 Converting IMO numbers to MMSI (VesselFinder scraping, max {max_scrapes if max_scrapes > 0 else 'all'})...")
        mmsi_success = 0
        scraped_count = 0

        for i, vessel in enumerate(vessels, 1):
            name = vessel.get('vessel_name', '').strip().upper()
            imo = vessel.get('imo', '').strip()

            if name:
                vessel_names.append(name)

            if imo and imo != 'Unknown':
                vessel_imos.append(imo)

                # Check scraping limit
                if max_scrapes > 0 and scraped_count >= max_scrapes:
                    # Use cached value only
                    cache_file = CACHE_DIR / f"{imo}.json"
                    if cache_file.exists():
                        try:
                            with open(cache_file, 'r') as f:
                                cached = json.load(f)
                                mmsi = cached.get('mmsi')
                                if mmsi:
                                    mmsi_numbers.append(mmsi)
                                    vessel['mmsi'] = mmsi
                        except Exception:
                            pass
                    continue

                # Try to convert IMO to MMSI using VesselFinder scraping
                print(f"  [{scraped_count+1}/{min(max_scrapes if max_scrapes > 0 else len(vessel_imos), len(vessel_imos))}] {name} (IMO {imo})...", end=' ')
                mmsi = mmsi_from_imo(imo)
                scraped_count += 1

                if mmsi:
                    mmsi_numbers.append(mmsi)
                    vessel['mmsi'] = mmsi  # Add MMSI to vessel dict
                    mmsi_success += 1
                    print(f"✓ MMSI {mmsi}")
                else:
                    print("✗ Not found")

        print(f"  ✓ Converted {mmsi_success}/{scraped_count} IMO numbers to MMSI (scraped {scraped_count} vessels)")
    else:
        # Just collect names and IMOs without scraping
        for vessel in vessels:
            name = vessel.get('vessel_name', '').strip().upper()
            imo = vessel.get('imo', '').strip()

            if name:
                vessel_names.append(name)
            if imo and imo != 'Unknown':
                vessel_imos.append(imo)

    # Create updated JSON structure
    shadow_fleet_data = {
        "shadow_fleet_mmsi": mmsi_numbers,
        "shadow_fleet_names": sorted(set(vessel_names)),  # Unique, sorted names
        "shadow_fleet_imo": sorted(set(vessel_imos)),     # NEW: Store IMO numbers too
        "metadata": {
            "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
            "vessel_count": len(vessels),
            "unique_names": len(set(vessel_names)),
            "unique_imo": len(set(vessel_imos)),
            "unique_mmsi": len(set(mmsi_numbers)),
            "sources": [
                "OpenSanctions (sanctioned vessels)",
                "CREA Russian Fossil Tracker",
                "Greenpeace Baltic Tankers List (PDF)",
                "Ukrainian Military Intelligence (GUR) Database",
                "2025 EU/UK/US Sanctions Lists",
                "News reports and maritime incidents",
                "VesselFinder (IMO to MMSI conversion)"
            ]
        },
        "vessels": vessels,  # Store full vessel data for reference
        "notes": "Suspected Russian shadow fleet vessels compiled from multiple open-source intelligence sources. These vessels are tracked for Arctic surveillance purposes."
    }

    # Write to file
    with open(shadow_fleet_file, 'w') as f:
        json.dump(shadow_fleet_data, f, indent=2)

    print(f"\n✅ Updated {shadow_fleet_file}")
    print(f"   Vessels: {len(vessels)}")
    print(f"   Unique names: {len(set(vessel_names))}")
    print(f"   IMO numbers: {len(set(vessel_imos))}")
    print(f"   MMSI numbers: {len(set(mmsi_numbers))}")

def main():
    """Main crawler function"""
    import argparse

    parser = argparse.ArgumentParser(description='Shadow Fleet Crawler - Arctic Shadow Tracker')
    parser.add_argument('--scrape-mmsi', action='store_true', default=True,
                       help='Enable VesselFinder scraping for MMSI conversion (default: True)')
    parser.add_argument('--no-scrape-mmsi', action='store_false', dest='scrape_mmsi',
                       help='Disable VesselFinder scraping')
    parser.add_argument('--max-scrapes', type=int, default=0,
                       help='Maximum vessels to scrape (0 = all, default: 0 for full run)')
    args = parser.parse_args()

    print("=" * 60)
    print("Shadow Fleet Crawler - Arctic Shadow Tracker")
    print("=" * 60)
    print()

    all_vessels = []

    # Source 1: OpenSanctions (sanctioned vessels — highest authority)
    print("Source 1: OpenSanctions (sanctioned vessels)")
    opensanctions_vessels = fetch_opensanctions_vessels()
    all_vessels.extend(opensanctions_vessels)
    print()

    # Source 2: CREA Russian Fossil Tracker (shadow fleet specific)
    print("Source 2: CREA Russian Fossil Tracker")
    crea_vessels = fetch_crea_shadow_fleet()
    all_vessels.extend(crea_vessels)
    print()

    # Source 3: Greenpeace Baltic Tankers PDF
    print("Source 3: Greenpeace Baltic Tankers PDF")
    pdf_vessels = extract_greenpeace_pdf()
    all_vessels.extend(pdf_vessels)
    print()

    # Source 4: Known 2025 vessels (manual curation)
    print("Source 4: Known 2025 Shadow Fleet Vessels")
    known_vessels = get_known_2025_vessels()
    all_vessels.extend(known_vessels)
    print()

    # Deduplicate
    print("🔄 Deduplicating vessels...")
    unique_vessels = deduplicate_vessels(all_vessels)
    print(f"   Before: {len(all_vessels)} vessels")
    print(f"   After: {len(unique_vessels)} unique vessels")
    print()

    # Update JSON file
    print("💾 Saving to shadow_fleet.json...")
    update_shadow_fleet_json(unique_vessels, scrape_mmsi=args.scrape_mmsi, max_scrapes=args.max_scrapes)
    print()

    print("=" * 60)
    print("✅ Shadow Fleet Crawler Complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Review the vessels in src/shadow_fleet.json")
    print("2. Run the AIS collector to fetch vessel positions")
    print("3. Check the dashboard for 'Shadow Fleet' category")
    print()

if __name__ == '__main__':
    main()
