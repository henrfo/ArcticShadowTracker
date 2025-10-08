#!/usr/bin/env python3
"""
Convert Norwegian Maritime Zone Layers from GML to GeoJSON
Reprojects from EPSG:25833 (UTM Zone 33N) to EPSG:4326 (WGS84)
"""

import fiona
from fiona.transform import transform_geom
from shapely.geometry import mapping
import json
from pathlib import Path

def convert_maritime_zones():
    """Convert Norwegian maritime zone layers to separate GeoJSON files"""

    base_dir = Path(__file__).parent.parent
    gml_file = base_dir / 'src' / 'marine_border' / 'Basisdata_0000_Norge_25833_NorgesMaritimeGrenser_GML.gml'

    # Define the maritime zone layers to extract
    zones = {
        '200nm_boundary': 'Grense200NautiskeMil',      # 200 nautical mile boundary
        'eez': 'NorgesØkonomiskeSone',                  # Norwegian Economic Zone
        'territorial_waters': 'Territorialfarvann'      # Territorial waters (12nm)
    }

    print(f"Reading GML file: {gml_file}\n")

    for output_name, layer_name in zones.items():
        output_file = base_dir / 'src' / 'marine_border' / f'norway_{output_name}.json'

        print(f"Converting layer: {layer_name}")

        try:
            with fiona.open(str(gml_file), layer=layer_name) as src:
                print(f"  Source CRS: {src.crs}")
                print(f"  Features: {len(src)}")

                features = []
                for i, feature in enumerate(src):
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
                with open(output_file, 'w') as f:
                    json.dump(geojson, f)

                file_size = output_file.stat().st_size / 1024
                print(f"  ✓ Saved {len(features)} features to {output_file.name} ({file_size:.1f} KB)\n")

        except Exception as e:
            print(f"  ✗ Error converting {layer_name}: {e}\n")

    print("Conversion complete!")

if __name__ == '__main__':
    convert_maritime_zones()
