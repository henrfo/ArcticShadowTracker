#!/usr/bin/env python3
"""
Simple Weekly Arctic Intelligence Report Generator
Uses Pydantic AI + Ollama (local LLM) to analyze vessel tracking data
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from pydantic import BaseModel
from pydantic_ai import Agent

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Data directories
BASE_DIR = Path(__file__).parent.parent
SNAPSHOTS_DIR = BASE_DIR / 'data' / 'snapshots'
REPORTS_DIR = BASE_DIR / 'reports'
REPORTS_DIR.mkdir(exist_ok=True)

# Define structured output
class WeeklyReport(BaseModel):
    """Structured weekly intelligence report"""
    week_start: str
    week_end: str
    total_vessels: int
    russian_count: int
    chinese_count: int
    norwegian_count: int
    norwegian_military_count: int
    summary: str
    key_observations: list[str]
    trends: str

# Create agent with Ollama
import os
os.environ['OPENAI_API_KEY'] = 'fake-key'  # Ollama doesn't need a real key
os.environ['OPENAI_BASE_URL'] = 'http://localhost:11434/v1'

agent = Agent(
    'openai:llama3.2',
    system_prompt="""You are an Arctic maritime intelligence analyst.
    Analyze ONLY the vessel data provided - do not infer or guess locations/activities.
    Use specific vessel names, coordinates, and timestamps from the data.
    Focus on observable patterns in Russian/Chinese vessel movements.
    Be factual and data-driven - only report what is explicitly in the data."""
)

def load_last_week_snapshots():
    """Load all snapshots from the last 7 days"""
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    snapshots = []
    for snapshot_file in sorted(SNAPSHOTS_DIR.glob('*.json')):
        # Parse timestamp from filename (YYYYMMDD_HHMM.json)
        timestamp_str = snapshot_file.stem
        try:
            snapshot_time = datetime.strptime(timestamp_str, '%Y%m%d_%H%M').replace(tzinfo=timezone.utc)
            if snapshot_time >= week_ago:
                with open(snapshot_file, 'r') as f:
                    snapshots.append(json.load(f))
        except ValueError:
            continue

    return snapshots

def analyze_snapshots(snapshots):
    """Extract statistics and patterns from snapshots"""
    if not snapshots:
        return None

    # Get all unique vessels and track their positions over time
    all_vessels = {}
    russian_positions = []
    chinese_positions = []

    for snapshot in snapshots:
        timestamp = snapshot['timestamp']
        for vessel in snapshot.get('vessels', []):
            mmsi = vessel['mmsi']
            country = vessel.get('country')

            if mmsi not in all_vessels:
                all_vessels[mmsi] = vessel

            # Track Russian/Chinese positions with timestamps
            if country == 'Russia':
                russian_positions.append({
                    'time': timestamp,
                    'lat': vessel.get('latitude'),
                    'lon': vessel.get('longitude'),
                    'name': vessel.get('name'),
                    'ship_type': vessel.get('ship_type')
                })
            elif country == 'China':
                chinese_positions.append({
                    'time': timestamp,
                    'lat': vessel.get('latitude'),
                    'lon': vessel.get('longitude'),
                    'name': vessel.get('name'),
                    'ship_type': vessel.get('ship_type')
                })

    # Count by country
    russian = sum(1 for v in all_vessels.values() if v.get('country') == 'Russia')
    chinese = sum(1 for v in all_vessels.values() if v.get('country') == 'China')
    norwegian_military = sum(1 for v in all_vessels.values()
                            if v.get('country') == 'Norway' and
                            ('military' in v.get('ship_type', '').lower() or
                             'law enforcement' in v.get('ship_type', '').lower()))

    return {
        'russian': russian,
        'chinese': chinese,
        'norwegian_military': norwegian_military,
        'russian_positions': russian_positions,
        'chinese_positions': chinese_positions,
        'snapshots_count': len(snapshots),
        'week_start': snapshots[0]['timestamp'],
        'week_end': snapshots[-1]['timestamp']
    }

async def generate_report():
    """Generate weekly report using AI agent"""
    print("Loading last 7 days of snapshot data...")
    snapshots = load_last_week_snapshots()

    if not snapshots:
        print("No snapshot data found for the last 7 days.")
        return None

    print(f"Found {len(snapshots)} snapshots")

    # Analyze data
    stats = analyze_snapshots(snapshots)
    print(f"Found {stats['russian']} Russian, {stats['chinese']} Chinese vessels")

    # Build detailed position summary for Russian/Chinese vessels
    russian_summary = []
    for pos in stats['russian_positions']:  # Include all positions
        russian_summary.append(f"  - {pos['name']} ({pos['ship_type']}) at lat {pos['lat']:.2f}, lon {pos['lon']:.2f} on {pos['time']}")

    chinese_summary = []
    for pos in stats['chinese_positions']:  # Include all positions
        chinese_summary.append(f"  - {pos['name']} ({pos['ship_type']}) at lat {pos['lat']:.2f}, lon {pos['lon']:.2f} on {pos['time']}")

    # Prepare prompt for agent
    prompt = f"""List Russian and Chinese vessel detections from this data.

RUSSIAN VESSELS ({stats['russian']} total):
{chr(10).join(russian_summary) if russian_summary else '  - None detected'}

CHINESE VESSELS ({stats['chinese']} total):
{chr(10).join(chinese_summary) if chinese_summary else '  - None detected'}

Write a brief report with:

Summary: List the Russian and Chinese vessels detected this week with their names.

Key Observations: For each unique vessel, state:
- Vessel name and type
- Coordinate range (min/max lat, lon)
- Number of detections

Trends: State if vessels appeared multiple times or moved between coordinates.

Use ONLY vessel names and coordinates from the data above. Do not infer locations."""

    print("\nGenerating report with AI agent...")

    # Run AI agent to generate text
    result = await agent.run(prompt)

    # Extract text from ModelResponse
    last_message = result.all_messages()[-1]
    ai_text = last_message.parts[0].content if hasattr(last_message, 'parts') else str(last_message)

    print(f"AI Response: {ai_text[:200]}...")  # Preview

    # Extract sections from AI response (improved parsing)
    lines = ai_text.split('\n')
    summary_lines = []
    observations = []
    trends_lines = []

    current_section = None
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('**Weekly'):
            continue

        # Detect section headers
        lower_line = line.lower()
        if 'summary' in lower_line and ':' in line:
            current_section = 'summary'
            # Extract text after colon
            if ':' in line:
                summary_lines.append(line.split(':', 1)[1].strip())
            continue
        elif 'observation' in lower_line or 'key' in lower_line:
            current_section = 'observations'
            continue
        elif 'trend' in lower_line:
            current_section = 'trends'
            continue

        # Add content to current section
        if current_section == 'summary' and line:
            summary_lines.append(line)
        elif current_section == 'observations' and (line.startswith('-') or line.startswith('•') or line[0].isdigit()):
            observations.append(line.lstrip('-•0123456789. ').strip())
        elif current_section == 'trends' and line:
            trends_lines.append(line)

    # Build report with AI-generated content
    total_tracked = stats['russian'] + stats['chinese'] + stats['norwegian_military']

    report = WeeklyReport(
        week_start=stats['week_start'],
        week_end=stats['week_end'],
        total_vessels=total_tracked,
        russian_count=stats['russian'],
        chinese_count=stats['chinese'],
        norwegian_count=0,
        norwegian_military_count=stats['norwegian_military'],
        summary=' '.join(summary_lines) if summary_lines else ai_text[:300],
        key_observations=observations if observations else ["Data analysis in progress"],
        trends=' '.join(trends_lines) if trends_lines else "Weekly tracking continues for priority vessels."
    )

    return report

def save_report(report: WeeklyReport):
    """Save report to markdown file"""
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d')
    report_file = REPORTS_DIR / f'weekly_{timestamp}.md'

    markdown = f"""# Arctic Intelligence Weekly Report
**Week of {report.week_start} to {report.week_end}**

## Vessel Summary
- **Total Tracked**: {report.total_vessels}
- **Russian**: {report.russian_count}
- **Chinese**: {report.chinese_count}
- **Norwegian**: {report.norwegian_count}
- **Norwegian Military/Law**: {report.norwegian_military_count}

## Summary
{report.summary}

## Key Observations
"""
    for obs in report.key_observations:
        markdown += f"- {obs}\n"

    markdown += f"\n## Trends\n{report.trends}\n"
    markdown += f"\n---\n*Generated on {datetime.now(ZoneInfo('Europe/Oslo')).strftime('%Y-%m-%d %H:%M %Z')} using Pydantic AI + Ollama*\n"

    with open(report_file, 'w') as f:
        f.write(markdown)

    return report_file

async def main():
    """Main execution"""
    print("=" * 60)
    print("Arctic Shadow Tracker - Weekly Intelligence Report")
    print("=" * 60)

    report = await generate_report()

    if report:
        report_file = save_report(report)
        print(f"\n✓ Report saved to: {report_file}")
        print("\nReport Preview:")
        print("-" * 60)
        print(f"Summary: {report.summary}")
        print(f"Observations: {len(report.key_observations)} items")
    else:
        print("\n✗ Could not generate report (no data)")

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
