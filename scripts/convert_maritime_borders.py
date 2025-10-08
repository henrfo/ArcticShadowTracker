#!/usr/bin/env python3
"""
Convert Norwegian Maritime Borders GML to GeoJSON
Reprojects from EPSG:25833 (UTM Zone 33N) to EPSG:4326 (WGS84)
"""

import fiona
from fiona.transform import transform_geom
from shapely.geometry import mapping
import json
from pathlib import Path

def convert_gml_to_geojson():
    """Convert Kartverket maritime borders GML to GeoJSON"""

    base_dir = Path(__file__).parent.parent
    gml_file = base_dir / 'src' / 'marine_border' / 'Basisdata_0000_Norge_25833_NorgesMaritimeGrenser_GML.gml'
    output_file = base_dir / 'src' / 'marine_border' / 'norway_maritime_borders.json'

    print(f"Reading GML file: {gml_file}")

    # Read GML (EPSG:25833)
    with fiona.open(str(gml_file)) as src:
        print(f"Source CRS: {src.crs}")
        print(f"Features found: {len(src)}")

        # Reproject to WGS84 (EPSG:4326)
        features = []
        for i, feature in enumerate(src):
            if i % 100 == 0:
                print(f"  Processing feature {i}...")

            # Transform geometry from EPSG:25833 to EPSG:4326
            geom_wgs84 = transform_geom(
                src.crs,
                'EPSG:4326',
                feature['geometry']
            )

            # Ensure geometry is a dict (GeoJSON format)
            if hasattr(geom_wgs84, '__geo_interface__'):
                geom_dict = geom_wgs84.__geo_interface__
            elif isinstance(geom_wgs84, dict):
                geom_dict = geom_wgs84
            else:
                geom_dict = mapping(geom_wgs84)

            # Convert properties to dict
            props = dict(feature['properties']) if feature['properties'] else {}

            features.append({
                'type': 'Feature',
                'geometry': geom_dict,
                'properties': props
            })

        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }

    # Save as GeoJSON
    print(f"\nWriting GeoJSON file: {output_file}")
    with open(output_file, 'w') as f:
        json.dump(geojson, f)

    print(f"✓ Converted {len(features)} features to GeoJSON")
    print(f"✓ File size: {output_file.stat().st_size / 1024 / 1024:.1f} MB")

if __name__ == '__main__':
    convert_gml_to_geojson()
