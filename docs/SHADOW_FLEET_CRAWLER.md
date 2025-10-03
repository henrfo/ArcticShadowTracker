# Shadow Fleet Crawler

This crawler extracts suspected Russian shadow fleet vessel data from multiple open-source intelligence sources and converts IMO numbers to MMSI for AIS tracking.

## Data Sources

1. **Greenpeace Baltic Tankers PDF** - Comprehensive list of shadow fleet tankers
2. **Ukrainian GUR Database** - Military intelligence vessel tracking
3. **2025 EU/UK/US Sanctions Lists** - Sanctioned vessels
4. **News reports** - Cable sabotage incidents (EAGLE S, KIWALA, etc.)

## Features

- ✅ PDF table extraction using pdfplumber
- ✅ IMO to MMSI conversion via VesselFinder web scraping
- ✅ Intelligent caching to avoid re-scraping
- ✅ Rate limiting (2 seconds between requests)
- ✅ Deduplication by IMO number and vessel name
- ✅ Command-line arguments for flexible scraping

## Usage

### Full run (scrape all vessels)
```bash
python src/shadow_fleet_crawler.py
```

This will:
- Extract ~187 vessels from Greenpeace PDF
- Add 14 manually curated 2025 vessels
- Scrape VesselFinder for MMSI numbers (~6-10 minutes)
- Save to `src/shadow_fleet.json`

### Skip MMSI scraping (names/IMOs only)
```bash
python src/shadow_fleet_crawler.py --no-scrape-mmsi
```

### Limit scraping for testing
```bash
python src/shadow_fleet_crawler.py --max-scrapes 10
```

## Output

The crawler generates `src/shadow_fleet.json` with:

```json
{
  "shadow_fleet_mmsi": ["273264690", "610000033", ...],
  "shadow_fleet_names": ["AKAR WEST", "EAGLE S", ...],
  "shadow_fleet_imo": ["9270529", "9329655", ...],
  "metadata": {
    "last_updated": "2025-10-03 23:37:46 UTC",
    "vessel_count": 198,
    "unique_names": 198,
    "unique_imo": 187,
    "unique_mmsi": 142
  },
  "vessels": [...]
}
```

## Caching

MMSI lookups are cached in `src/.mmsi_cache/` to avoid re-scraping:
- Each IMO gets a JSON file: `{imo}.json`
- Cache includes MMSI number and timestamp
- Cache persists across runs for faster updates

## Automation

The crawler runs automatically via GitHub Actions:
- **Schedule**: Weekly on Sundays at midnight UTC
- **Workflow**: `.github/workflows/shadow-fleet-update.yml`
- **Manual trigger**: Available via workflow_dispatch

## Rate Limiting

- **Delay**: 2 seconds between VesselFinder requests
- **Total time**: ~6-10 minutes for 187 vessels
- **Respectful scraping**: User-Agent header, caching, and delays

## Next Steps

1. Run the crawler to populate MMSI numbers
2. Restart AIS collection: `python scripts/collect_ais.py`
3. Check dashboard for "Shadow Fleet" category
4. Monitor Arctic movements of tracked vessels

## Known Vessels

High-priority shadow fleet vessels include:
- **EAGLE S** - Cable sabotage suspect (Finnish Customs)
- **KIWALA** - Seized by Estonia (2025)
- **PROXIMA**, **KALININGRAD**, **KRYMSK** - Ukrainian GUR database
- 187+ additional vessels from Greenpeace research
